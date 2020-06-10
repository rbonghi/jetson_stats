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
import socket
from service import JtopServer
from .core import import_os_variables
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

class jtop:
    class JtopException(Exception):
        """ Jtop general exception """
        pass

    def __init__(self, interval=500):
        # Open socket
        self.sock_ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    def open(self):
        try:
            self.sock_ctrl.sendto("start", JtopServer.PIPE_JTOP_CTRL)
        except socket.error as e:
            print(e)
            raise jtop.JtopException("jtop server not available")
        print("Open library")

    def close(self):
        try:
            self.sock_ctrl.sendto("stop", JtopServer.PIPE_JTOP_CTRL)
        except socket.error:
            raise jtop.JtopException("jtop server not available")
        print("Close library")

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
# EOF
