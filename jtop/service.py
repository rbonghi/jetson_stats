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
import traceback
from grp import getgrnam
from multiprocessing import Process, Queue, Event, Value
from multiprocessing.managers import SyncManager
# jetson_stats imports
from .core import Tegrastats, JetsonClocksService, Config, NVPModelService, JtopException
# Create logger for tegrastats
logger = logging.getLogger(__name__)
# Load queue library for python 2 and python 3
try:
    import queue
except ImportError:
    import Queue as queue

# Pipe configuration
# https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s13.html
# https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard
JTOP_PIPE = '/run/jtop.socket'
JTOP_USER = 'jetson_stats'
AUTHKEY = 'aaabbcc'


class JtopManager(SyncManager):

    def __init__(self, authkey=AUTHKEY):
        super(JtopManager, self).__init__(address=(JTOP_PIPE), authkey=authkey.encode("utf-8"))

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
        - https://docs.python.org/2.7/reference/datamodel.html
    """

    def __init__(self, gain_timeout=2):
        # Load configuration
        self.config = Config()
        # Error queue
        self._error = Queue()
        # Timeout control command
        self.gain_timeout = gain_timeout
        # Command queue
        self.q = Queue()
        # Speed interval
        self.interval = Value('d', 0.0)
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
        self.jetson_clocks = JetsonClocksService(self.config)
        # Initialize nvpmodel controller
        try:
            self._nvp = NVPModelService()
        except JtopException:
            self._nvp = None
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats)

    def run(self):
        timeout = None
        interval = 1
        try:
            while True:
                try:
                    # Decode control message
                    control = self.q.get(timeout=timeout)
                    # Check if control is not empty
                    if not control:
                        continue
                    # Manage jetson_clocks
                    if 'jc' in control:
                        # Enable or disable
                        if control['jc']:
                            if self.jetson_clocks.start():
                                logger.info("jetson_clocks stared")
                            else:
                                logger.warning("jetson_clocks already running")
                        else:
                            if self.jetson_clocks.stop():
                                logger.info("jetson_clocks stopped")
                            else:
                                logger.info("jetson_clocks already stopped")
                    # Decode nvp model
                    if 'nvp' in control:
                        mode = control['nvp']
                        logger.info("Set new NV Power Mode {mode}".format(mode=mode))
                        # Set new NV Power Mode
                        self._nvp.set(mode)
                    if 'config' in control:
                        config = control['config']
                        if 'jc' in config:
                            print(config['jc'])
                            self.jetson_clocks.boot = config['jc']
                    # Initialize tegrastats speed
                    if 'interval' in control:
                        interval = control['interval']
                        # Run stats
                        if self.tegra.open(interval=interval):
                            # Set interval value
                            self.interval.value = interval
                            # Status start tegrastats
                            logger.info("tegrastats started {interval}ms".format(interval=int(interval * 1000)))
                    # Update timeout interval
                    timeout = interval * self.gain_timeout
                except queue.Empty:
                    # Close and log status
                    if self.tegra.close():
                        logger.info("tegrastats close")
                        self.sync_event.clear()
                    # Disable timeout
                    timeout = None
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception:
            # Close tegra
            if self.tegra.close():
                logger.info("tegrastats close")
            # Catch exception
            ex_type, ex_value, tb = sys.exc_info()
            error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
            # Write error message
            self._error.put(error)

    def start(self, force=False):
        # Run setup
        self.jetson_clocks.initialization()
        # Initialize socket
        try:
            gid = getgrnam(JTOP_USER).gr_gid
        except KeyError:
            # User does not exist
            raise JtopException("Group {jtop_user} does not exist!".format(jtop_user=JTOP_USER))
        # Remove old pipes if exists
        if force and os.path.exists(JTOP_PIPE):
            logger.info("Remove pipe {pipe}".format(pipe=JTOP_PIPE))
            os.remove(JTOP_PIPE)
        # Start broadcaster
        try:
            self.broadcaster.start()
        except EOFError:
            raise JtopException("Server already alive")
        # Initialize synchronized data and conditional
        self.sync_data = self.broadcaster.sync_data()
        self.sync_event = self.broadcaster.sync_event()
        # Change owner
        os.chown(JTOP_PIPE, os.getuid(), gid)
        # Change mode cotroller and stats
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # Equivalent permission 660 srw-rw----
        os.chmod(JTOP_PIPE, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP)
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
        # Close communication
        self.close()

    def close(self):
        self.broadcaster.shutdown()

    def tegra_stats(self, stats):
        # Make configuration dict
        data = {'speed': self.interval.value}
        logger.debug("tegrastats read")
        # Load data stats
        data['stats'] = stats
        # Load status jetson_clocks
        data['jc'] = self.jetson_clocks.show()
        data['jc'].update({'thread': self.jetson_clocks.is_running, 'boot': self.jetson_clocks.boot})
        # Pack and send all data
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(data)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()

    def __del__(self):
        self.close()
# EOF
