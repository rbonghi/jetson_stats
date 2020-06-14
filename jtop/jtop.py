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
import copy
from threading import Thread
from .service import CtrlManager, StatsManager
from .core import (import_os_variables,
                   get_uptime,
                   status_disk,
                   get_local_interfaces)
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
        self._running = False
        # Load interval
        self._interval = float(interval)
        # Initialize observer
        self._observers = set()
        # Stats read from service
        self._stats = {}
        # Open socket
        CtrlManager.register('get_queue')
        manager = CtrlManager()
        try:
            manager.connect()
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
        self._controller = manager.get_queue()
        # Read stats
        StatsManager.register("sync_data")
        StatsManager.register('sync_event')
        self._broadcaster = StatsManager()
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
    def stats(self):
        """
        A dictionary with the status of the board

        :return: Compacts jetson statistics
        :rtype: dict
        """
        return self._stats

    @property
    def ram(self):
        return {}

    @property
    def cpu(self):
        if 'CPU' not in self._stats:
            return {}
        # Extract CPU
        cpus = copy.copy(self._stats['CPU'])
        return cpus

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
        if 'WATT' in data:
            # Refactor names
            data['WATT'] = {str(k.replace("VDD_", "").replace("POM_", "").replace("_", " ")): v for k, v in data['WATT'].items()}
        if 'TEMP' in data:
            # Remove PMIC temperature
            if 'PMIC' in data['TEMP']:
                del data['TEMP']['PMIC']
            # TODO: Decode all field to string
        # Store data in stats
        self._stats = data
        # TODO: Store nvpmode and jetson_clocks
        # ...
        # Notifiy all observers
        for observer in self._observers:
            # Call all observer in list
            observer(self._stats)

    def run(self):
        while self._running:
            # Send alive message
            self._controller.put({})
            # Read stats from jtop service
            data = self._get_data()
            # Decode and update all jtop data
            self._decode(data)
        # Release condition
        print("exit read")

    def _get_data(self):
        # Check if is not set event otherwise wait
        if not self._sync_event.is_set():
            self._sync_event.wait()
        # Read stats from jtop service
        data = self._sync_data.copy()
        # Clear event
        self._sync_event.clear()
        return data

    def start(self):
        # Connected to broadcaster
        self._broadcaster.connect()
        # Initialize syncronized data and condition
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

    def open(self):
        self.start()

    def close(self):
        # Switch off broadcaster thread
        self._running = False
        print("Close library")

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
# EOF
