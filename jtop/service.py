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

# Logging
import logging
# Operative system
import os
# TODO temporary commented: import stat
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager
from grp import getgrnam
from .core import Tegrastats
# Create logger for tegrastats
logger = logging.getLogger(__name__)
# Load queue library for python 2 and python 3
try:
    import queue
except ImportError:
    import Queue as queue

PIPE_JTOP_STATS = '/tmp/jtop_stats'
PIPE_JTOP_CTRL = '/tmp/jtop_ctrl'
PIPE_JTOP_USER = 'jetson_stats'
AUTHKEY = 'aaabbcc'


class CtrlManager(BaseManager):

    def __init__(self, authkey=AUTHKEY):
        super(CtrlManager, self).__init__(address=(PIPE_JTOP_CTRL), authkey=authkey)

    def get_queue(self):
        pass


class StatsManager(BaseManager):

    def __init__(self, authkey=AUTHKEY):
        super(StatsManager, self).__init__(address=(PIPE_JTOP_STATS), authkey=authkey)

    def stats(self):
        pass


class JtopServer(Process):
    """
        - https://pymotw.com/2/multiprocessing/basics.html
        - https://stackoverflow.com/questions/1829116/how-to-share-variables-across-scripts-in-python
    """
    def __init__(self, timeout=1):
        self.q = Queue()
        self.stats = {}
        self.timeout = timeout
        super(JtopServer, self).__init__()
        # Remove old pipes if exists
        if os.path.exists(PIPE_JTOP_CTRL):
            print("Remove old pipe {pipe}".format(pipe=PIPE_JTOP_CTRL))
            os.remove(PIPE_JTOP_CTRL)
        if os.path.exists(PIPE_JTOP_STATS):
            print("Remove old pipe {pipe}".format(pipe=PIPE_JTOP_STATS))
            os.remove(PIPE_JTOP_STATS)
        # Register queue manager
        CtrlManager.register('get_queue', callable=lambda: self.q)
        self.controller = CtrlManager()
        # Register stats
        # https://docs.python.org/2/library/multiprocessing.html#using-a-remote-manager
        StatsManager.register("stats", self._read_data)
        self.broadcaster = StatsManager()
        self.broadcaster.start()
        # Setup tegrastats
        self.tegra = Tegrastats('/usr/bin/tegrastats')
        self.tegra.attach(self.tegra_stats)

    def run(self):
        timeout = None
        while True:
            try:
                # Decode control message
                control = self.q.get(timeout=timeout)
                timeout = self.timeout
                # Check if control is not empty
                if not control:
                    continue
                # Initialize tegrastats speed
                if 'interval' in control:
                    interval = control['interval']
                    # Run stats
                    if self.tegra.open(interval=interval):
                        print("tegrastats started")
            except queue.Empty:
                # Close and log status
                if self.tegra.close():
                    print("tegrastats close")
                # Disable timeout
                timeout = None
            except KeyboardInterrupt:
                break

    def start(self):
        try:
            gid = getgrnam(PIPE_JTOP_USER).gr_gid
        except KeyError:
            # TODO: Check how to be writeable only from same group
            raise Exception("Group jetson_stats does not exist!")
        else:
            gid = os.getgid()
            print("Check how to be writeable only from same group. Now use gid={gid}".format(gid=gid))
        # Run the Control server
        super(JtopServer, self).start()
        s = self.controller.get_server()
        # Change owner
        os.chown(PIPE_JTOP_CTRL, os.getuid(), gid)
        os.chown(PIPE_JTOP_STATS, os.getuid(), gid)
        # TODO: Change mode cotroller and stats
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # os.chmod(PIPE_JTOP_CTRL, stat.S_IWOTH)
        # os.chmod(PIPE_JTOP_STATS, stat.S_IWOTH)
        # Run server
        s.serve_forever()

    def close(self):
        print("End Server")
        self.broadcaster.shutdown()

    def tegra_stats(self, stats):
        print("stats")
        # Update stats
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        try:
            self.stats_sync = self.broadcaster.stats()
            self.stats_sync.update(stats)
        except Exception as e:
            print(e)

    def __del__(self):
        print("On delete")
        self.close()

    def _read_data(self):
        return self.stats

    def __call__(self):
        return self
# EOF
