# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import re
import sys
from datetime import datetime, timedelta
from multiprocessing import Event, AuthenticationError
from threading import Thread
from .service import JtopManager
from .core import (
    Memory,
    Engine,
    Swap,
    CPU,
    Fan,
    NVPModel,
    get_var,
    get_uptime,
    status_disk,
    import_os_variables,
    get_local_interfaces,
    JetsonClocks,
    JtopException)
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
try:
    PermissionError
except NameError:
    PermissionError = OSError
if sys.version_info[0] == 2:
    from socket import error as ConnectionRefusedError
# Create logger
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
AUTH_RE = re.compile(r""".*__author__ = ["'](.*?)['"]""", re.S)
# Gain timeout lost connection
TIMEOUT_GAIN = 3


def import_jetson_libraries():
    JTOP_FOLDER, _ = os.path.split(__file__)
    return import_os_variables(JTOP_FOLDER + "/jetson_libraries", "JETSON_")


def get_version():
    """
    Show the version of this package

    :return: Version number
    :rtype: string
    """
    return get_var(VERSION_RE)


class Board:

    def __init__(self):
        self.info = {}
        self.hardware = {}
        self.libraries = {}


class jtop(Thread):
    """
    jtop library is the reference to control your NVIDIA Jetson board with python.
    This object can be open like a file, or you can use a with callback function

    :param interval: Interval update tegrastats and other statistic function
    :type interval: float
    """

    def __init__(self, interval=0.5):
        # Initialize Thread super class
        super(jtop, self).__init__()
        # Local Event thread
        self._trigger = Event()
        # Error message from thread
        self._error = None
        # Start server
        self._running = False
        # Load interval
        self._interval = float(interval)
        # Initialize observer
        self._observers = set()
        # Stats read from service
        self._stats = {}
        # Read stats
        JtopManager.register('get_queue')
        JtopManager.register("sync_data")
        JtopManager.register('sync_event')
        # Initialize broadcaster manager
        self._broadcaster = JtopManager()
        # Initialize board variable
        self._board = Board()
        self._thread_libraries = Thread(target=self._load_jetson_libraries, args=[])
        self._thread_libraries.daemon = True
        self._thread_libraries.start()
        # Initialize engines
        self._engine = Engine()
        # Initialize CPU
        self._cpu = CPU()
        # Initialize swap
        self._swap = None
        # Initialize Memory
        self._memory = None
        # Load jetson_clocks status
        self._jc = None
        # Initialize fan
        self._fan = None
        # Load NV Power Mode
        self._nvp = None

    def _load_jetson_libraries(self):
        try:
            env = {}
            for k, v in import_jetson_libraries().items():
                env[k] = str(v)
            # Make dictionaries
            self._board.libraries = {
                "CUDA": env["JETSON_CUDA"],
                "cuDNN": env["JETSON_CUDNN"],
                "TensorRT": env["JETSON_TENSORRT"],
                "VisionWorks": env["JETSON_VISIONWORKS"],
                "OpenCV": env["JETSON_OPENCV"],
                "OpenCV-Cuda": env["JETSON_OPENCV_CUDA"],
                "VPI": env["JETSON_VPI"],
                "Vulkan": env["JETSON_VULKAN_INFO"]}
            # Loaded from script
            logger.debug("Loaded jetson_variables variables")
        except Exception:
            # Write error message
            self._error = sys.exc_info()

    def attach(self, observer):
        """
        Attach an observer to read the status of jtop

        :param observer: The function to call
        :type observer: function
        """
        self._observers.add(observer)

    def detach(self, observer):
        """
        Detach an observer from jtop

        :param observer:  The function to detach
        :type observer: function
        """
        self._observers.discard(observer)

    def restore(self):
        status = {}
        # Reset jetson_clocks
        if self.jetson_clocks is not None:
            # Disable jetson_clocks
            self.jetson_clocks = False
            # Wait jetson_clocks boot
            while self.ok():
                if not self.jetson_clocks:
                    break
            status['jetson_clocks'] = bool(self.jetson_clocks)
            # Disable jetson_clocks on boot
            self.jetson_clocks.boot = False
            # Wait jetson_clocks boot
            while self.ok():
                if not self.jetson_clocks.boot:
                    break
            status['jetson_clocks boot'] = bool(self.jetson_clocks.boot)
        # Reset fan control
        if self.fan is not None:
            # Reset mode fan
            self.fan.mode = 'default'
            while self.ok():
                if self.fan.mode == 'default':
                    break
            status['fan mode'] = False
            # Reset speed to zero
            self.fan.speed = 0
            while self.ok():
                if self.fan.measure == 0:
                    break
            status['fan speed'] = False
        # Switch off swap
        if self.swap.is_enable:
            # Deactivate swap
            self.swap.deactivate()
            while self.ok():
                if not self.swap.is_enable:
                    break
            status['swap'] = bool(self.swap.is_enable)
        # Clear config file
        self._controller.put({'config': 'reset'})
        status['config'] = False
        return status

    @property
    def engine(self):
        return self._engine

    @property
    def board(self):
        # Wait thread end
        self._thread_libraries.join()
        # Return board status
        return self._board

    @property
    def fan(self):
        return self._fan

    @property
    def nvpmodel(self):
        """
        Status NV Power Mode

        :return: Return the name of NV Power Mode
        :rtype: string
        """
        return self._nvp

    @nvpmodel.setter
    def nvpmodel(self, value):
        if self._nvp is None:
            return
        mode = self._nvp.set(value)
        # Do not send messages if nvpmodel is the same
        if mode == self._nvp.id:
            return
        # Send new nvpmodel
        self._controller.put({'nvp': mode})

    @property
    def jetson_clocks(self):
        """
        Status jetson_clocks

        :return: true if jetson_clocks is running otherwise false
        :rtype: bool
        """
        return self._jc

    @jetson_clocks.setter
    def jetson_clocks(self, value):
        if not isinstance(value, bool):
            raise TypeError("Use a boolean")
        if not self._jc.is_config and not value:
            raise JtopException("I cannot set jetson_clocks.\nPlease shutdown manually jetson_clocks")
        # Check if service is not started otherwise skip
        if self._jc.status in ['activating', 'deactivating']:
            return
        if value != self._jc.is_alive:
            # Send status jetson_clocks
            self._controller.put({'jc': {'enable': value}})

    @property
    def stats(self):
        """
        A dictionary with the status of the board

        :return: Compacts jetson statistics
        :rtype: dict
        """
        stats = {'time': datetime.now(), 'uptime': self.uptime}
        # -- jetson_clocks --
        if self.jetson_clocks is not None:
            stats['jetson_clocks'] = 'ON' if self.jetson_clocks else 'OFF'
        # -- NV Power Model --
        if self.nvpmodel is not None:
            stats['nvp model'] = self.nvpmodel.name
        # -- CPU --
        for cpu in sorted(self.cpu):
            stats[cpu] = self.cpu[cpu].get('val', 'OFF')
        # -- GPU --
        stats['GPU'] = self.gpu['val']
        # -- MTS --
        if self.mts:
            stats['MTS FG'] = self.mts['fg']
            stats['MTS BG'] = self.mts['bg']
        # -- RAM --
        stats['RAM'] = self.ram['use']
        # -- EMC --
        if self.emc:
            stats['EMC'] = self.ram['use']
        # -- IRAM --
        if self.iram:
            stats['IRAM'] = self.ram['use']
        # -- SWAP --
        stats['SWAP'] = self.swap['use']
        # -- Engines --
        stats['APE'] = self.engine.ape['val']
        stats['NVENC'] = self.engine.nvenc['val'] if self.engine.nvenc else 'OFF'
        stats['NVDEC'] = self.engine.nvdec['val'] if self.engine.nvdec else 'OFF'
        stats['NVJPG'] = self.engine.nvjpg['rate'] if self.engine.nvjpg else 'OFF'
        if self.engine.nvdec:
            stats['MSENC'] = self.engine.msenc
        # -- FAN --
        if self.fan:
            stats['fan'] = self.fan.measure
        # -- Temperature --
        for temp in sorted(self.temperature):
            stats["Temp {name}".format(name=temp)] = self.temperature[temp]
        # -- Power --
        total, _ = self.power
        stats['power cur'] = total['cur']
        stats['power avg'] = total['avg']
        return stats

    @property
    def swap(self):
        return self._swap

    @property
    def emc(self):
        # Extract EMC
        return self._stats.get('emc', {})

    @property
    def iram(self):
        # Extract IRAM
        return self._stats.get('iram', {})

    @property
    def ram(self):
        return self._memory

    @property
    def mts(self):
        # Extract MTS
        return self._stats.get('mts', {})

    @property
    def cpu(self):
        # Return CPU status
        return self._cpu

    @property
    def gpu(self):
        # Extract GPU
        return self._stats['gpu']

    @property
    def power(self):
        """
        A dictionary with all power consumption

        :return: Detailed information about power consumption
        :rtype: dict
        """
        total = self._stats['power']['all']
        power = self._stats['power']['power']
        return total, power

    @property
    def temperature(self):
        """
        A dictionary with board temperatures

        :return: Detailed information about temperature
        :rtype: dict
        """
        return self._stats['temperature']

    @property
    def local_interfaces(self):
        """ Local interfaces information """
        return get_local_interfaces()

    @property
    def disk(self):
        """ Disk status properties """
        return status_disk()

    @property
    def uptime(self):
        """ Up time """
        return timedelta(seconds=get_uptime())

    def _decode(self, data):
        """
        Internal decode function to decode and refactoring data
        """
        self._stats = data
        # -- ENGINES --
        self._engine._update(data['engines'])
        # -- CPU --
        self._cpu._update(data['cpu'])
        # -- RAM --
        self._memory._update(data['ram'])
        # -- SWAP --
        self._swap._update(data['swap'])
        # -- FAN --
        if 'fan' in data:
            self._fan._update(data['fan'])
        # -- JETSON_CLOCKS --
        if 'jc' in data:
            self._jc._update(data['jc'])
        # -- NVP Model --
        if 'nvp' in data:
            self._nvp._update(data['nvp'])
        # Set trigger
        self._trigger.set()
        # Notify all observers
        for observer in self._observers:
            # Call all observer in list
            observer(self)

    def run(self):
        # https://gist.github.com/schlamar/2311116
        # https://stackoverflow.com/questions/13074847/catching-exception-in-context-manager-enter
        try:
            while self._running:
                # Send alive message
                if self._controller.empty():
                    self._controller.put({})
                # Read stats from jtop service
                data = self._get_data()
                # Decode and update all jtop data
                self._decode(data)
        except Exception:
            # Store error message
            self._error = sys.exc_info()

    def _get_data(self):
        try:
            # Check if is not set event otherwise wait
            if not self._sync_event.is_set():
                self._sync_event.wait(self._interval * TIMEOUT_GAIN)
            # Read stats from jtop service
            data = self._sync_data.copy()
            if not data:
                raise JtopException("Error connection")
            # Clear event
            self._sync_event.clear()
        except EOFError:
            # Raise jtop exception
            raise JtopException("Lost connection with jtop server")
        return data

    def _get_configuration(self):
        while True:
            # Send configuration connection
            self._controller.put({'interval': self._interval})
            # Return configuration
            data = self._controller.get(self._interval * TIMEOUT_GAIN)
            if 'init' in data:
                return data['init']

    def start(self):
        # Connected to broadcaster
        try:
            self._broadcaster.connect()
        except FileNotFoundError as e:
            if e.errno == 2 or e.errno == 111:  # Message error: 'No such file or directory' or 'Connection refused'
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl restart jetson_stats.service")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise JtopException("I can't access to jetson_stats.service.\nPlease logout or reboot this board.")
            else:
                raise FileNotFoundError(e)
        except ConnectionRefusedError as e:
            if e.errno == 111:  # Connection refused
                # When server is off but socket files exists in /run
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl restart jetson_stats.service")
            else:
                raise ConnectionRefusedError(e)
        except PermissionError as e:
            if e.errno == 13:  # Permission denied
                raise JtopException("I can't access to jetson_stats.service.\nPlease logout or reboot this board.")
            else:
                raise PermissionError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise JtopException("mismatch python version between library and service")
        except AuthenticationError:
            raise JtopException("Authentication mismatch with jetson-stats server")
        # Initialize synchronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Initialize connection
        init = self._get_configuration()
        # Load server speed
        self._server_interval = init['interval']
        # Load board information
        board = init['board']
        self._board.info = board['info']
        self._board.hardware = board['hardware']
        # Initialize jetson_clocks sender
        self._swap = Swap(self._controller, init['swap'])
        # Initialize jetson_clock
        if init['jc']:
            self._jc = JetsonClocks(self._controller)
        # Initialize Memory
        self._memory = Memory(self._controller)
        # Init FAN (If exist)
        if init['fan']:
            self._fan = Fan(self._controller)
        # Init NVP model (if exist)
        if init['nvpmodel']:
            self._nvp = NVPModel()
        # Wait first value
        data = self._get_data()
        # Decode and update all jtop data
        self._decode(data)
        # Run thread reader
        self._running = True
        self.daemon = True
        super(jtop, self).start()

    @property
    def interval(self):
        return self._server_interval

    @property
    def interval_user(self):
        return self._interval

    def loop_for_ever(self):
        self.start()
        # Blocking function to catch exceptions
        while self.ok():
            try:
                self.join(timeout=0.1)
            except (KeyboardInterrupt, SystemExit):
                # Close jtop
                self.close()

    def ok(self, spin=False):
        # Wait if trigger is set
        if not spin:
            try:
                if not self._trigger.is_set():
                    if not self._trigger.wait(self._interval * TIMEOUT_GAIN):
                        self._running = False
            except (KeyboardInterrupt, SystemExit):
                self._running = False
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value
        # If there are not errors clear the event
        if self._running:
            self._trigger.clear()
        # Return the status
        return self._running

    def close(self):
        # Switch off broadcaster thread
        self._running = False

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        if exc_tb is not None:
            return False
        return True
# EOF
