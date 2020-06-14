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
import stat
from multiprocessing import Process, Queue, Condition
from multiprocessing.managers import BaseManager, SyncManager
from grp import getgrnam
from .core import Tegrastats
from .core import JetsonClocks
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
        super(CtrlManager, self).__init__(address=(PIPE_JTOP_CTRL), authkey=authkey.encode("utf-8"))

    def get_queue(self):
        pass


class StatsManager(SyncManager):

    def __init__(self, authkey=AUTHKEY):
        super(StatsManager, self).__init__(address=(PIPE_JTOP_STATS), authkey=authkey.encode("utf-8"))

    def sync_data(self):
        pass

    def sync_condition(self):
        pass


class JtopServer(Process):
    """
        - https://pymotw.com/2/multiprocessing/basics.html
        - https://pymotw.com/2/multiprocessing/communication.html
        - https://stackoverflow.com/questions/1829116/how-to-share-variables-across-scripts-in-python
        - https://stackoverflow.com/questions/45342200/how-to-use-syncmanager-lock-or-event-correctly
        - https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
    """

    def __init__(self, path, gain_timeout=2):
        config_file = path
        # Timeout control command
        self.gain_timeout = gain_timeout
        # Command queue
        self.q = Queue()
        # Dictionary to sync
        self.data = {}
        # Conditional to lock
        # TODO: Check adding an RLock
        # https://docs.python.org/2.0/lib/condition-objects.html
        # https://docs.python.org/2.7/library/threading.html#condition-objects
        self.cond = Condition()
        # Load super Thread constructor
        super(JtopServer, self).__init__()
        # Remove old pipes if exists
        # TODO: Raise if pipe exists otherwise with force to close
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
        StatsManager.register("sync_data", callable=lambda: self.data)
        StatsManager.register('sync_condition', callable=lambda: self.cond)
        self.broadcaster = StatsManager()
        # Initialize jetson_clocks controller
        self.jc = JetsonClocks(config_file)
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats)

    def run(self):
        timeout = None
        local_timeout = 1
        while True:
            try:
                # Decode control message
                control = self.q.get(timeout=timeout)
                # Check if control is not empty
                if not control:
                    continue
                # Initialize tegrastats speed
                if 'interval' in control:
                    local_timeout = control['interval']
                    # Set timeout
                    interval = int(local_timeout * 1000)
                    # Run stats
                    if self.tegra.open(interval=interval):
                        # Status start tegrastats
                        print("tegrastats started {interval}ms".format(interval=interval))
                # Update timeout interval
                timeout = local_timeout * self.gain_timeout
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
            # User does not exist
            raise Exception("Group {jtop_user} does not exist!".format(jtop_user=PIPE_JTOP_USER))
        # Start broadcaster
        self.broadcaster.start()
        # Initialize syncronized data and conditional
        self.sync_data = self.broadcaster.sync_data()
        self.sync_cond = self.broadcaster.sync_condition()
        # Run the Control server
        super(JtopServer, self).start()
        # Get control server
        ctrl_server = self.controller.get_server()
        # Change owner
        os.chown(PIPE_JTOP_CTRL, os.getuid(), gid)
        os.chown(PIPE_JTOP_STATS, os.getuid(), gid)
        # Change mode cotroller and stats
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # Equivalent permission 660 srw-rw----
        os.chmod(PIPE_JTOP_CTRL, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP)
        os.chmod(PIPE_JTOP_STATS, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP)
        # Run server forever
        ctrl_server.serve_forever()

    def close(self):
        print("End Server")
        self.broadcaster.shutdown()

    def tegra_stats(self, stats):
        print("tegrastats read")
        # Update stats
        self.sync_cond.acquire()
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(stats)
        # Notify and release token
        self.sync_cond.notify_all()
        self.sync_cond.release()

    def __del__(self):
        print("On delete")
        self.close()
# EOF
