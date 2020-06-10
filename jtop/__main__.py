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
import grp
# Jtop server
from .service import JtopServer


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

    try:
        gid = grp.getgrnam("jetson_stats").gr_gid
        print(gid)
    except KeyError:
        print("jetson_stats group does not exist!")

    if os.path.exists(JtopServer.PIPE_JTOP_CTRL):
        print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_CTRL))
        os.remove(JtopServer.PIPE_JTOP_CTRL)
    # bind socket
    sock_in = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock_in.bind(JtopServer.PIPE_JTOP_CTRL)
    os.chown(JtopServer.PIPE_JTOP_CTRL, 1000, 1000)
    sock_in.settimeout(1)
    # jtop service
    server = JtopServer()

    print("Service started")
    while True:
        try:
            datagram = sock_in.recv(1024)
            print("Datagram: {datagram}".format(datagram=datagram))
            # Run tegrastats
            if datagram == "start":
                server.tegra.open()
            elif datagram == "stop":
                server.tegra.close()
        except socket.timeout:
            #print("Timeout!")
            pass
        except KeyboardInterrupt:
            break

    # Close stats server
    server.close()
    print("Close service")
    sock_in.close()
    os.remove(JtopServer.PIPE_JTOP_CTRL)



if __name__ == "__main__":
    main()
# EOF
