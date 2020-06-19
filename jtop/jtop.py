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
import traceback
from threading import Thread
from .service import JtopManager
from .core import (CPU,
                   Fan,
                   NVPModel,
                   import_os_variables,
                   get_uptime,
                   status_disk,
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


def import_jetson_variables():
    JTOP_FOLDER, _ = os.path.split(__file__)
    return import_os_variables(JTOP_FOLDER + "/jetson_variables", "JETSON_")


def get_version():
    """
    Show the version of this package

    :return: Version number
    :rtype: string
    """
    # Load version package
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "__init__.py")) as fp:
        VERSION = VERSION_RE.match(fp.read()).group(1)
    return VERSION


class jtop(Thread):
    """
    jtop library is the reference to control your NVIDIA Jetson board with python.
    This object can be open like a file, or you can use a with callback function

    :param interval: Interval update tegrastats and other statistic function
    :type interval: float
    """

    def __init__(self, interval=0.5):
        Thread.__init__(self)
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
        self._broadcaster = JtopManager()
        # Initialize fan
        self._fan = Fan()
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
            self._controller.put({'jc': value})

    @property
    def stats(self):
        """
        A dictionary with the status of the board

        :return: Compacts jetson statistics
        :rtype: dict
        """
        return self._stats

    @property
    def ram(self):
        if 'RAM' not in self._stats:
            return {}
        # Extract RAM
        ram = copy.copy(self._stats['RAM'])
        return ram

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
            if "_IN" in val:
                total_name = val
                break
        # Extract the total from list
        # Otherwise sum all values
        # Example for Jetson Xavier
        # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
        if total_name:
            total = power[total_name]
            del power[total_name]
            return {'Total': total}, power
        # Otherwise measure all total power
        total = {'cur': 0, 'avg': 0}
        for power in power.values():
            total['cur'] += power['cur']
            total['avg'] += power['avg']
        return {'Total': total}, power

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
        # Add total power
        power.update(total)
        return power

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
        self._server_interval = data['speed']
        # Read tegrastats
        tegrastats = data['stats']
        if 'WATT' in tegrastats:
            # Refactor names
            tegrastats['WATT'] = {k.replace("VDD_", "").replace("POM_", "").replace("_", " "): v for k, v in tegrastats['WATT'].items()}
        if 'TEMP' in tegrastats:
            # Remove PMIC temperature
            if 'PMIC' in tegrastats['TEMP']:
                del tegrastats['TEMP']['PMIC']
        # Load jetson_clocks data
        jc_show = data['jc']
        # Update status
        self._jc._update(jc_show)
        # Store data in stats
        self._cpu._update(tegrastats['CPU'], jc_show)
        # Update GPU status
        if 'GPU' in jc_show:
            tegrastats['GR3D'].update(jc_show['GPU'])
        # Store the updated stats from tegrastats
        self._stats = tegrastats
        # Update NVIDIA Power mode
        self._nvp._update(jc_show.get('NVP', ''))
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
            # Run close loop
            self._running = False
            ex_type, ex_value, tb = sys.exc_info()
            error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
            # Write error message
            self._error = error

    def _get_data(self):
        try:
            # Check if is not set event otherwise wait
            if not self._sync_event.is_set():
                self._sync_event.wait(self._interval * 2)
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
                # TODO: Fixe message error
                raise JtopException("jetson_stats service not active, please run sudo ... ")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise JtopException("I can't access to server, check group ")
            else:
                raise FileNotFoundError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise JtopException("mismatch python version between library and service")
        # Initialize synchronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Send alive message
        self._controller.put({'interval': self._interval})
        # Initialize jetson_clocks sender
        self._jc._init(self._controller)
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

    def loop_for_ever(self):
        self.start()
        # Blocking function to catch exceptions
        while self.ok():
            try:
                self.join(timeout=0.1)
            except (KeyboardInterrupt, SystemExit):
                break
        # Close jtop
        self.close()

    def ok(self):
        # Catch exception if exist
        if self._error:
            ex_type, ex_value, tb_str = self._error
            message = '%s (in subprocess)\n%s' % (ex_value.message, tb_str)
            raise ex_type(message)
        # Return the status
        return self._running

    def close(self):
        # Check exceptions
        self.ok()
        # Switch off broadcaster thread
        self._running = False

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
        return True
# EOF
