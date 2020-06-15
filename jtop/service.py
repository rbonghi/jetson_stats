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
import sys
import stat
import json
import time
import traceback
from grp import getgrnam
from multiprocessing import Process, Queue, Event
from multiprocessing.managers import SyncManager
# jetson_stats imports
from .core import Tegrastats, JetsonClocks, get_uptime
# Create logger for tegrastats
logger = logging.getLogger(__name__)
# Load queue library for python 2 and python 3
try:
    import queue
except ImportError:
    import Queue as queue

# Pipe configuration
PATH_FOLDER = '/local/jetson_stats'
PIPE_JTOP = '/tmp/jtop'
PIPE_JTOP_USER = 'jetson_stats'
AUTHKEY = 'aaabbcc'
# Service configuration
CONFIG_JTOP = "config.json"


class JtopManager(SyncManager):

    def __init__(self, authkey=AUTHKEY):
        super(JtopManager, self).__init__(address=(PIPE_JTOP), authkey=authkey.encode("utf-8"))

    def get_queue(self):
        pass

    def sync_data(self):
        pass

    def sync_event(self):
        pass


class JtopServer(Process):
    """
        - https://pymotw.com/2/multiprocessing/basics.html
        - https://pymotw.com/2/multiprocessing/communication.html
        - https://stackoverflow.com/questions/1829116/how-to-share-variables-across-scripts-in-python
        - https://stackoverflow.com/questions/45342200/how-to-use-syncmanager-lock-or-event-correctly
        - https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
    """
    class Exception(Exception):
        """ Jtop general exception """
        pass

    def __init__(self, path, gain_timeout=2):
        # Configuration dictionary
        self.config = {}
        # Load configuration path
        config_path = path + PATH_FOLDER
        config_file = config_path + '/' + CONFIG_JTOP
        # Load configuration if exist
        if os.path.isfile(config_file):
            logger.info("Load config from {path}".format(path=config_file))
            with open(config_file) as json_file:
                self.config = json.load(json_file)
        # Error queue
        self._error = Queue()
        # Timeout control command
        self.gain_timeout = gain_timeout
        # Command queue
        self.q = Queue()
        # Dictionary to sync
        self.data = {}
        # Event lock
        self.event = Event()
        # Load super Thread constructor
        super(JtopServer, self).__init__()
        # Register stats
        # https://docs.python.org/2/library/multiprocessing.html#using-a-remote-manager
        JtopManager.register('get_queue', callable=lambda: self.q)
        JtopManager.register("sync_data", callable=lambda: self.data)
        JtopManager.register('sync_event', callable=lambda: self.event)
        self.broadcaster = JtopManager()
        # Initialize jetson_clocks controller
        self.jetson_clocks = JetsonClocks(config_path, self.config)
        # Run setup
        self.jetson_clocks.initialization()
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats)

    def run(self):
        timeout = None
        local_timeout = 1
        try:
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
                        self.sync_event.clear()
                    # Disable timeout
                    timeout = None
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception:
            # Close tegra
            if self.tegra.close():
                print("tegrastats close")
            # Catch exception
            ex_type, ex_value, tb = sys.exc_info()
            error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
            # Write error message
            self._error.put(error)

    def start(self, force=False):
        try:
            gid = getgrnam(PIPE_JTOP_USER).gr_gid
        except KeyError:
            # User does not exist
            raise Exception("Group {jtop_user} does not exist!".format(jtop_user=PIPE_JTOP_USER))
        # Remove old pipes if exists
        if force and os.path.exists(PIPE_JTOP):
            print("Remove pipe {pipe}".format(pipe=PIPE_JTOP))
            os.remove(PIPE_JTOP)
        # Start broadcaster
        try:
            self.broadcaster.start()
        except EOFError:
            raise JtopServer.Exception("Server already alive")
        # Initialize syncronized data and conditional
        self.sync_data = self.broadcaster.sync_data()
        self.sync_event = self.broadcaster.sync_event()
        # Change owner
        os.chown(PIPE_JTOP, os.getuid(), gid)
        # Change mode cotroller and stats
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # Equivalent permission 660 srw-rw----
        os.chmod(PIPE_JTOP, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP)
        # Run the Control server
        self.daemon = True
        super(JtopServer, self).start()

    def loop_for_ever(self):
        try:
            self.start()
            # Get exception
            error = self._error.get()
            self.join()
            # Raise error if exist
            if error:
                ex_type, ex_value, tb_str = error
                message = '%s (in subprocess)\n%s' % (ex_value.message, tb_str)
                raise ex_type(message)
        except (KeyboardInterrupt, SystemExit):
            pass
        # Close communitication
        self.close()

    def close(self):
        self.broadcaster.shutdown()

    def tegra_stats(self, stats):
        print("tegrastats read")
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(stats)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()

    def __del__(self):
        self.close()
# EOF
