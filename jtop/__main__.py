#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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
import socket
# Jtop server
from .service import JtopServer

PIPE_JTOP_CTRL = '/tmp/jtop_ctrl'
PIPE_JTOP_STATS = '/tmp/jtop_stats'


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def ok(message="OK"):
        return bcolors.OKGREEN + message + bcolors.ENDC

    @staticmethod
    def warning(message="WARN"):
        return bcolors.WARNING + message + bcolors.ENDC

    @staticmethod
    def fail(message="ERR"):
        return bcolors.FAIL + message + bcolors.ENDC


def main():
    if os.path.exists(PIPE_JTOP_CTRL):
        print("Remove old pipe {pipe}".format(pipe=PIPE_JTOP_CTRL))
        os.remove(PIPE_JTOP_CTRL)
    # bind socket
    sock_in = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_in.bind(PIPE_JTOP_CTRL)
    os.chown(PIPE_JTOP_CTRL, 1000, 1000)
    sock_in.settimeout(1)
    # jtop service
    server = JtopServer(PIPE_JTOP_STATS)

    # Close stats server
    server.close()
    print("Close service")
    sock_in.close()
    os.remove(PIPE_JTOP_CTRL)



if __name__ == "__main__":
    main()
# EOF
