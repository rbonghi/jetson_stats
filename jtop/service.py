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
import socket
from .core import Tegrastats


class JtopServer:

    PIPE_JTOP_CTRL = '/tmp/jtop_ctrl'
    PIPE_JTOP_STATS = '/tmp/jtop_stats'

    def __init__(self):
        if os.path.exists(JtopServer.PIPE_JTOP_STATS):
            print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_STATS))
            os.remove(JtopServer.PIPE_JTOP_STATS)
        # Initialize socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(JtopServer.PIPE_JTOP_STATS)
        # Set ownership file
        os.chown(JtopServer.PIPE_JTOP_STATS, 1000, 1000)
        # Setup tegrastats
        self.tegra = Tegrastats('/usr/bin/tegrastats', 500)
        self.tegra.attach(self.tegra_stats)

    def loop(self):
        pass

    def close(self):
        print("End Server")
        self.socket.close()
        os.remove(JtopServer.PIPE_JTOP_STATS)

    def tegra_stats(self, stats):
        print("Stats")
        self.socket.sendto("stats", JtopServer.PIPE_JTOP_STATS)



# EOF
