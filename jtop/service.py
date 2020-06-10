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
import stat
import socket
from  grp import getgrnam
from .core import Tegrastats


class JtopServer:

    PIPE_JTOP_CTRL = '/tmp/jtop_ctrl'
    PIPE_JTOP_STATS = '/tmp/jtop_stats'
    PIPE_JTOP_USER = 'jetson_stats'

    def __init__(self, timeout=1):
        try:
            gid = getgrnam(JtopServer.PIPE_JTOP_USER).gr_gid
        except KeyError:
            # TODO: Check how to be writeable only from same group
            # raise Exception("Group jetson_stats does not exist!")
            print("Check how to be writeable only from same group")
            gid = os.getgid()
        # Remove old pipes if exists
        if os.path.exists(JtopServer.PIPE_JTOP_CTRL):
            print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_CTRL))
            os.remove(JtopServer.PIPE_JTOP_CTRL)
        if os.path.exists(JtopServer.PIPE_JTOP_STATS):
            print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_STATS))
            os.remove(JtopServer.PIPE_JTOP_STATS)
        # Initialize and bind control socket
        self.sock_ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock_ctrl.bind(JtopServer.PIPE_JTOP_CTRL)
        self.sock_ctrl.settimeout(timeout)
        os.chown(JtopServer.PIPE_JTOP_CTRL, os.getuid(), gid)
        # Set mode
        # https://www.tutorialspoint.com/python/os_chmod.htm
        os.chmod(JtopServer.PIPE_JTOP_CTRL, stat.S_IWOTH)
        # Initialize and bind statistics socket
        self.socket_stats = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket_stats.bind(JtopServer.PIPE_JTOP_STATS)
        # Set ownership file
        os.chown(JtopServer.PIPE_JTOP_STATS, os.getuid(), gid)
        # Set mode
        # TODO: Set mode is only readable from all
        # os.chmod(JtopServer.PIPE_JTOP_CTRL, stat.S_IWOTH)
        # Setup tegrastats
        self.tegra = Tegrastats('/usr/bin/tegrastats')
        self.tegra.attach(self.tegra_stats)

    def loop(self):
        while True:
            try:
                datagram = self.sock_ctrl.recv(1024)
                print("Datagram: {datagram}".format(datagram=datagram))
                # Run tegrastats
                if datagram == "start":
                    self.tegra.open(interval=500)
                elif datagram == "stop":
                    self.tegra.close()
            except socket.timeout:
                #print("Timeout!")
                pass

    def close(self):
        print("End Server")
        self.sock_ctrl.close()
        os.remove(JtopServer.PIPE_JTOP_CTRL)
        self.socket_stats.close()
        os.remove(JtopServer.PIPE_JTOP_STATS)

    def tegra_stats(self, stats):
        print(stats)
        self.socket_stats.sendto("stats", JtopServer.PIPE_JTOP_STATS)
# EOF
