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
from threading import Thread
from .service import CtrlManager, StatsManager
from .core import import_os_variables
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

    def __init__(self, interval=500):
        Thread.__init__(self)
        self._running = False
        # Load interval
        self.interval = interval
        # Stats read from service
        self._stats = {}
        # Open socket
        CtrlManager.register('get_queue')
        manager = CtrlManager()
        try:
            manager.connect()
        except FileNotFoundError as e:
            if e.errno == 2: #Message error: 'No such file or directory'
                raise jtop.JtopException("jetson_stats service not active, please run sudo ... ")
            elif e.errno == 13: #Message error: 'Permission denied'
                raise jtop.JtopException("I can't access to server, check group ")
            else:
                raise FileNotFoundError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise jtop.JtopException("mismatch python version between library and service")
        self.controller = manager.get_queue()
        # Read stats
        StatsManager.register("sync_data")
        StatsManager.register('sync_condition')
        self.broadcaster = StatsManager()

    @property
    def stats(self):
        """
            A dictionary with the status of the board
        """
        return self._stats

    @property
    def ram(self):
        return {}

    def decode(self, data):
        self._stats = data

    def run(self):
        # Acquire condition
        self.sync_cond.acquire()
        while self._running:
            # Send alive message
            self.controller.put({})
            try:
                self.sync_cond.wait()
            except EOFError:
                logger.error("wait error")
                break
            # Read stats from jtop service
            data = self.sync_data.copy()
            # Decode and update all jtop data
            self.decode(data)
        try:
            self.sync_cond.release()
        except IOError:
            logger.error("Release error")
            raise jtop.JtopException("Lost connection to server")
        # Release condition
        print("exit read")

    def start(self):
        # Connected to broadcaster
        self.broadcaster.connect()
        # Initialize syncronized data and condition
        self.sync_data = self.broadcaster.sync_data()
        self.sync_cond = self.broadcaster.sync_condition()
        # Send alive message
        self.controller.put({'interval': self.interval})
        # Wait first value
        try:
            self.sync_cond.acquire()
            self.sync_cond.wait()
            self.decode(self.sync_data.copy())
            self.sync_cond.release()
        except (IOError, EOFError):
            logger.error("Release error")
            raise jtop.JtopException("Lost connection to server")
        # Run thread reader
        self._running = True
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
