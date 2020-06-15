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
from .core import (import_os_variables,
                   get_uptime,
                   status_disk,
                   get_local_interfaces,
                   jetson_clocks_alive)
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
# Create logger for tegrastats
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
    class JtopException(Exception):
        """ Jtop general exception """
        pass

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
        # Version package
        self.version = get_version()

    def attach(self, observer):
        """
        Attach an obserber to read the status of jtop

        :param observer: The function to call
        :type observer: function
        """
        self._observers.add(observer)

    def detach(self, observer):
        """
        Detach an obserber from jtop

        :param observer:  The function to detach
        :type observer: function
        """
        self._observers.discard(observer)

    @property
    def jetson_clocks(self):
        """
        Status jetson_clocks

        :return: true if jetson_clocks is running otherwise false
        :rtype: bool
        """
        return jetson_clocks_alive(self._jc_show)

    @jetson_clocks.setter
    def jetson_clocks(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
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
        if 'CPU' not in self._stats:
            return {}
        # Extract CPU
        cpus = copy.copy(self._stats['CPU'])
        return cpus

    @property
    def gpu(self):
        if 'GR3D' not in self._stats:
            return {}
        # Extract GPU
        gpu = copy.copy(self._stats['GR3D'])
        return gpu

    def _total_power(self, dpower):
        """
        Private function to measure the total watt

        :return: Total power and a second dictionary with all other measures
        :rtype: dict, dict
        """
        # In according with:
        # https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8
        # https://github.com/rbonghi/jetson_stats/issues/51
        total_name = ""
        for val in dpower:
            if "_IN" in val:
                total_name = val
                break
        # Extract the total from list
        # Otherwise sum all values
        # Example for Jetson Xavier
        # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
        if total_name:
            total = dpower[total_name]
            del dpower[total_name]
            return {'Total': total}, dpower
        # Otherwise measure all total power
        total = {'cur': 0, 'avg': 0}
        for power in dpower.values():
            total['cur'] += power['cur']
            total['avg'] += power['avg']
        return {'Total': total}, dpower

    @property
    def power(self):
        """
        A dictionary with all power consumption

        :return: Detailed information about power consumption
        :rtype: dict
        """
        if 'WATT' not in self._stats:
            return {}
        dpower = copy.copy(self._stats['WATT'])
        # Measure total power
        total, dpower = self._total_power(dpower)
        # Add total power
        dpower.update(total)
        return dpower

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
        # Read tegrastat
        tegrastats = data['stats']
        if 'WATT' in tegrastats:
            # Refactor names
            tegrastats['WATT'] = {str(k.replace("VDD_", "").replace("POM_", "").replace("_", " ")): v for k, v in tegrastats['WATT'].items()}
        if 'TEMP' in tegrastats:
            # Remove PMIC temperature
            if 'PMIC' in tegrastats['TEMP']:
                del tegrastats['TEMP']['PMIC']
        # Load jetson_clocks data
        self._jc_show = data['jc']
        # Store data in stats
        if 'CPU' in self._jc_show:
            for k, v in tegrastats['CPU'].items():
                # Extract jc_cpu info
                jc_cpu = self._jc_show['CPU'].get(k, {})
                # Update CPU information
                v.update(jc_cpu)
                tegrastats['CPU'][k] = v
        # Store the updated stats from tegrastats
        self._stats = tegrastats
        # Notifiy all observers
        for observer in self._observers:
            # Call all observer in list
            observer(self)

    @property
    def is_alive(self):
        return self._running

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
                raise jtop.JtopException("Error connection")
            # Clear event
            self._sync_event.clear()
        except EOFError:
            # Raise jtop exception
            raise jtop.JtopException("Lost connection with jtop server")
        return data

    def start(self):
        # Connected to broadcaster
        try:
            self._broadcaster.connect()
        except FileNotFoundError as e:
            if e.errno == 2:  # Message error: 'No such file or directory'
                # TODO: Fixe message error
                raise jtop.JtopException("jetson_stats service not active, please run sudo ... ")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise jtop.JtopException("I can't access to server, check group ")
            else:
                raise FileNotFoundError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise jtop.JtopException("mismatch python version between library and service")
        # Initialize syncronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Send alive message
        self._controller.put({'interval': self._interval})
        # Wait first value
        data = self._get_data()
        # Decode and update all jtop data
        self._decode(data)
        # Run thread reader
        self._running = True
        self.daemon = True
        super(jtop, self).start()

    def loop_for_ever(self):
        self.start()
        # Blocking function to catch exceptions
        while self._running:
            try:
                self.join(timeout=0.1)
            except (KeyboardInterrupt, SystemExit):
                break
        # Close jtop
        self.close()

    def close(self):
        # Switch off broadcaster thread
        self._running = False
        # Catch exception if exist
        if self._error:
            ex_type, ex_value, tb_str = self._error
            message = '%s (in subprocess)\n%s' % (ex_value.message, tb_str)
            raise ex_type(message)

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
        return True
# EOF
