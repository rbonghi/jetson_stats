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
import copy
from multiprocessing import Event, AuthenticationError
from threading import Thread
from .service import JtopManager, key_reader
from .core import (
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
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
# Create logger
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
AUTH_RE = re.compile(r""".*__author__ = ["'](.*?)['"]""", re.S)
# Gain timeout lost connection
TIMEOUT_GAIN = 3


def import_jetson_variables():
    JTOP_FOLDER, _ = os.path.split(__file__)
    return import_os_variables(JTOP_FOLDER + "/jetson_variables", "JETSON_")


def get_version():
    """
    Show the version of this package

    :return: Version number
    :rtype: string
    """
    return get_var(VERSION_RE)


class Board:

    def __init__(self, board):
        self.__dict__.update(**board)


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
        key = key_reader(AUTH_RE)
        self._broadcaster = JtopManager(key)
        # Initialize board variable
        self._board = None
        self._thread_libraries = Thread(target=self._load_jetson_variables, args=[])
        self._thread_libraries.daemon = True
        self._thread_libraries.start()
        # Initialize fan
        try:
            self._fan = Fan()
        except JtopException:
            self._fan = None
        # Load jetson_clocks status
        self._jc = JetsonClocks()
        # Load NV Power Mode
        try:
            self._nvp = NVPModel()
        except JtopException as e:
            print(e)
            self._nvp = None
        # Initialize CPU
        self._cpu = CPU()
        # Initialize swap
        self._swap = Swap()
        # Engines
        self._engine = Engine()

    def _load_jetson_variables(self):
        try:
            env = {}
            for k, v in import_jetson_variables().items():
                env[k] = str(v)
            # Make dictionaries
            info = {
                "machine": env["JETSON_MACHINE"],
                "jetpack": env["JETSON_JETPACK"],
                "L4T": env["JETSON_L4T"]}
            hardware = {
                "TYPE": env["JETSON_TYPE"],
                "CODENAME": env["JETSON_CODENAME"],
                "SOC": env["JETSON_SOC"],
                "CHIP_ID": env["JETSON_CHIP_ID"],
                "BOARDIDS": env["JETSON_BOARDIDS"],
                "MODULE": env["JETSON_MODULE"],
                "BOARD": env["JETSON_BOARD"],
                "CUDA_ARCH_BIN": env["JETSON_CUDA_ARCH_BIN"],
                "SERIAL_NUMBER": env["JETSON_SERIAL_NUMBER"].upper()}
            libraries = {
                "CUDA": env["JETSON_CUDA"],
                "cuDNN": env["JETSON_CUDNN"],
                "TensorRT": env["JETSON_TENSORRT"],
                "VisionWorks": env["JETSON_VISIONWORKS"],
                "OpenCV": env["JETSON_OPENCV"],
                "OpenCV-Cuda": env["JETSON_OPENCV_CUDA"],
                "VPI": env["JETSON_VPI"],
                "Vulkan": env["JETSON_VULKAN_INFO"]}
            # make board information
            self._board = Board({'info': info, 'hardware': hardware, 'libraries': libraries})
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
        # Check if service is not started otherwise skip
        if self._jc.status == 'activating':
            return
        if value != self._jc.is_alive:
            # Send status jetson_clocks
            self._controller.put({'jc': {'enable': value}})

    # @property
    # def stats(self):
        """
        A dictionary with the status of the board

        :return: Compacts jetson statistics
        :rtype: dict
        """
    #    return self._stats

    @property
    def swap(self):
        return self._swap

    @property
    def emc(self):
        if 'EMC' not in self._stats:
            return {}
        # Extract EMC
        emc = copy.copy(self._stats['EMC'])
        return emc

    @property
    def iram(self):
        if 'IRAM' not in self._stats:
            return {}
        # Extract IRAM
        iram = copy.copy(self._stats['IRAM'])
        return iram

    @property
    def ram(self):
        if 'RAM' not in self._stats:
            return {}
        # Extract RAM
        ram = copy.copy(self._stats['RAM'])
        return ram

    @property
    def mts(self):
        if 'MTS' not in self._stats:
            return {}
        # Extract MTS
        mts = copy.copy(self._stats['MTS'])
        return mts

    @property
    def cpu(self):
        # Return CPU status
        return self._cpu

    @property
    def gpu(self):
        if 'GR3D' not in self._stats:
            return {}
        # Extract GPU
        gpu = copy.copy(self._stats['GR3D'])
        return gpu

    def _total_power(self, power):
        """
        Private function to measure the total watt

        :return: Total power and a second dictionary with all other measures
        :rtype: dict, dict
        """
        # In according with:
        # https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8
        # https://github.com/rbonghi/jetson_stats/issues/51
        total_name = ""
        for val in power:
            if "IN" in val:
                total_name = val
                break
        # Extract the total from list
        # Otherwise sum all values
        # Example for Jetson Xavier
        # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
        if total_name:
            total = power[total_name]
            del power[total_name]
            return total, power
        # Otherwise measure all total power
        total = {'cur': 0, 'avg': 0}
        for value in power.values():
            total['cur'] += value['cur']
            total['avg'] += value['avg']
        return total, power

    @property
    def power(self):
        """
        A dictionary with all power consumption

        :return: Detailed information about power consumption
        :rtype: dict
        """
        if 'WATT' not in self._stats:
            return {}
        power = copy.copy(self._stats['WATT'])
        # Measure total power
        total, power = self._total_power(power)
        return total, power

    @property
    def temperature(self):
        """
        A dictionary with board temperatures

        :return: Detailed information about temperature
        :rtype: dict
        """
        if 'TEMP' not in self._stats:
            return {}
        # Extract temperatures
        temperatures = copy.copy(self._stats['TEMP'])
        return temperatures

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
        return get_uptime()

    def _decode(self, data):
        """
        Internal decode function to decode and refactoring data
        """
        # Update status fan
        if 'fan' in data:
            self._fan._update(data['fan'])
        # Extract configuration
        self._server_interval = data['interval']
        # Read tegrastats
        tegrastats = data['stats']
        if 'WATT' in tegrastats:
            # Refactor names
            tegrastats['WATT'] = {k.replace("VDD_", "").replace("POM_", "").replace("_", " "): v for k, v in tegrastats['WATT'].items()}
        if 'TEMP' in tegrastats:
            # Remove PMIC temperature
            if 'PMIC' in tegrastats['TEMP']:
                del tegrastats['TEMP']['PMIC']
        # Update swap status
        self._swap._update(tegrastats['SWAP'])
        # Load jetson_clocks data
        jc_show = data['jc']
        # Update status
        self._jc._update(jc_show)
        # Store data in stats
        self._cpu._update(tegrastats['CPU'], jc_show)
        # Update engines
        self._engine._update(tegrastats)
        # Update GPU status
        if 'GPU' in jc_show:
            tegrastats['GR3D'].update(jc_show['GPU'])
        # Store the updated stats from tegrastats
        self._stats = tegrastats
        # Update NVIDIA Power mode
        self._nvp._update(jc_show.get('NVP', ''))
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

    def start(self):
        # Connected to broadcaster
        try:
            self._broadcaster.connect()
        except FileNotFoundError as e:
            if e.errno == 2:  # Message error: 'No such file or directory'
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl start jetson_stats.service")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise JtopException("I can't access to server, check group")
            elif e.errno == 111:  # Connection refused
                # When server is off but socket files exists in /run
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl start jetson_stats.service")
            else:
                raise FileNotFoundError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise JtopException("mismatch python version between library and service")
        except AuthenticationError:
            raise JtopException("Authentication mismatch with jetson-stats server")
        # Initialize synchronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Send alive message
        self._controller.put({'interval': self._interval})
        # Initialize jetson_clocks sender
        self._swap._init(self._controller)
        self._jc._init(self._controller)
        if self._fan is not None:
            self._fan._init(self._controller)
        # Wait first value
        data = self._get_data()
        # Decode and update all jtop data
        self._decode(data)
        # Send a warning message if there is a mismatch between request speed and server speed
        if self._interval != self._server_interval:
            logger.warning("I can't set this speed. Another jtop set speed to {interval}s".format(interval=self._server_interval))
        # Run thread reader
        self._running = True
        self.daemon = True
        super(jtop, self).start()

    @property
    def interval(self):
        return self._server_interval

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
            print(self._error)
            raise (ex_type, ex_value, tb_str)
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
