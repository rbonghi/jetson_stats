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
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager
from  grp import getgrnam
from .core import Tegrastats


class QueueManager(BaseManager):
    
    def get_queue(self):
        pass

class MyListManager(BaseManager):

    def read_data(self):
        pass

# https://stackoverflow.com/questions/9361625/how-to-make-a-socket-server-listen-on-local-file
# https://stackoverflow.com/questions/34249188/oserror-errno-107-transport-endpoint-is-not-connected
class JtopServer(Process):

    PIPE_JTOP_CTRL = '/tmp/jtop_ctrl'
    PIPE_JTOP_STATS = '/tmp/jtop_stats'
    PIPE_JTOP_USER = 'jetson_stats'

    def __init__(self, timeout=1):
        self.q = Queue()
        super(JtopServer, self).__init__()
        
        #try:
        #    gid = getgrnam(JtopServer.PIPE_JTOP_USER).gr_gid
        #except KeyError:
            # TODO: Check how to be writeable only from same group
            # raise Exception("Group jetson_stats does not exist!")
        #    print("Check how to be writeable only from same group")
        #    gid = os.getgid()
        # Remove old pipes if exists
        if os.path.exists(JtopServer.PIPE_JTOP_CTRL):
            print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_CTRL))
            os.remove(JtopServer.PIPE_JTOP_CTRL)
        if os.path.exists(JtopServer.PIPE_JTOP_STATS):
            print("Remove old pipe {pipe}".format(pipe=JtopServer.PIPE_JTOP_STATS))
            os.remove(JtopServer.PIPE_JTOP_STATS)
        # Register queue manager
        QueueManager.register('get_queue', callable=lambda: self.q)
        self.manager = QueueManager(address=(JtopServer.PIPE_JTOP_CTRL), authkey='abracadabra')
        #os.chown(JtopServer.PIPE_JTOP_CTRL, os.getuid(), gid)
        # Set mode
        # https://www.tutorialspoint.com/python/os_chmod.htm
        #os.chmod(JtopServer.PIPE_JTOP_CTRL, stat.S_IWOTH)
        self.stats = {}
        # Register stats
        #MyListManager.register("service", self.read_data, exposed=['__getitem__', '__setitem__', '__str__', 'append', 'count', 'extend', 'index', 'insert', 'pop', 'remove', 'reverse', 'sort'])
        MyListManager.register("service", self.read_data)
        self.broadcaster = MyListManager(address=(JtopServer.PIPE_JTOP_STATS), authkey='')
        self.broadcaster.start()
        # Set mode
        # TODO: Set mode is only readable from all
        # os.chmod(JtopServer.PIPE_JTOP_CTRL, stat.S_IWOTH)
        # Setup tegrastats
        self.tegra = Tegrastats('/usr/bin/tegrastats')
        self.tegra.attach(self.tegra_stats)
        self.counter = 0
        self.start()

    def __call__(self):
        return self

    def run(self):
        while True:
            out = self.q.get()
            self.stats_sync = self.broadcaster.service()
            self.stats_sync.update({'a': self.counter})
            print(out, self.stats_sync)
            self.counter += 1

    def open(self):
        s = self.manager.get_server()
        s.serve_forever()

    def close(self):
        print("End Server")
        self.broadcaster.shutdown()

    def tegra_stats(self, stats):
        print("stats")
        #self.counter += 1

    def read_data(self):
        return self.stats
# EOF
