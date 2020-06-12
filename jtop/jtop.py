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

import os
import re
from threading import Thread
from .service import CtrlManager, StatsManager
from .core import import_os_variables
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
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
        # Load interval
        self.interval = interval
        # Stats read from service
        self._stats = {}
        # Initialize daemon
        self.daemon = True
        # Open socket
        CtrlManager.register('get_queue')
        manager = CtrlManager()
        try:
            manager.connect()
        except FileNotFoundError:
            raise jtop.JtopException("jetson_stats service not active, please run sudo ... ")
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise jtop.JtopException("mismatch python version between library and service")
        self.controller = manager.get_queue()
        # Read stats
        StatsManager.register("status")
        self.receiver = StatsManager()
        self.receiver.connect()

    @property
    def stats(self):
        """
            A dictionary with the status of the board
        """
        return self._stats

    def ram(self):
        return {}

    def run(self):
        while True:
            # Read stats from jtop service
            status = dict(self.receiver.status())
            # Update only if differents
            if self._stats != status:
                self._stats = status
                # Send alive message
                self.controller.put({})

    def open(self):
        # Send alive message
        self.controller.put({'interval': self.interval})
        # Read stats from jtop service
        while not dict(self.receiver.status()):
            pass
        # Save and convert first value
        self._stats = dict(self.receiver.status())
        # Run thread reader
        self.start()

    def close(self):
        print("Close library")

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
# EOF
