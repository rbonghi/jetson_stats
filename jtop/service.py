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
from grp import getgrnam
from base64 import b64decode
from multiprocessing import Process, Queue, Event, Value
from multiprocessing.managers import SyncManager
# jetson_stats imports
from .core import (
    nvjpg,
    JtopException,
    Tegrastats,
    JetsonClocksService,
    Config,
    NVPModelService,
    FanService,
    SwapService,
    key_generator,
    get_var)
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
AUTH_PATH = '/run/jtop.auth'
JTOP_USER = 'jetson_stats'
# Gain timeout lost connection
TIMEOUT_GAIN = 3


class JtopManager(SyncManager):

    def __init__(self, authkey):
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

    def __init__(self):
        # Check if running a root
        if os.getuid() != 0:
            raise JtopException("jetson_clocks need sudo to work")
        # Load configuration
        self.config = Config()
        # Error queue
        self._error = Queue()
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
        # Generate key and open broadcaster
        key = key_generator(AUTH_PATH)
        self.broadcaster = JtopManager(key)
        # Initialize Fan
        try:
            self.fan = FanService(self.config)
        except JtopException:
            self.fan = None
        # Initialize jetson_clocks controller
        self.jetson_clocks = JetsonClocksService(self.config, self.fan)
        # Initialize jetson_fan
        if self.fan is not None:
            self.fan.initialization(self.jetson_clocks)
        # Initialize nvpmodel controller
        try:
            self.nvpmodel = NVPModelService(self.jetson_clocks)
        except JtopException:
            self.nvpmodel = None
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats)
        # Swap manager
        self.swap = SwapService(self.config)

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
                    # Manage swap
                    if 'swap' in control:
                        swap = control['swap']
                        if swap:
                            self.swap.set(swap['size'], swap['boot'])
                        else:
                            self.swap.deactivate()
                    # Manage jetson_clocks
                    if 'jc' in control:
                        jc = control['jc']
                        # Enable / disable jetson_clocks
                        if 'enable' in jc:
                            if jc['enable']:
                                if self.jetson_clocks.start():
                                    logger.info("jetson_clocks started")
                                else:
                                    logger.warning("jetson_clocks already running")
                            else:
                                if self.jetson_clocks.stop():
                                    logger.info("jetson_clocks stopped")
                                else:
                                    logger.info("jetson_clocks already stopped")
                        # Update jetson_clocks configuration
                        if 'boot' in jc:
                            self.jetson_clocks.boot = jc['boot']
                    # Speed Fan and configuration
                    if 'fan' in control:
                        fan = control['fan']
                        for key, value in fan.items():
                            logger.info('Fan config {} {}'.format(key, value))
                            if key == 'mode':
                                self.fan.mode = value
                            elif key == 'speed':
                                self.fan.speed = value
                    # Decode nvp model
                    if 'nvp' in control:
                        mode = control['nvp']
                        logger.info("Set new NV Power Mode {mode}".format(mode=mode))
                        # Set new NV Power Mode
                        self.nvpmodel.set(mode)
                    # Initialize tegrastats speed
                    if 'interval' in control:
                        interval = control['interval']
                        # Run stats
                        if self.tegra.open(interval=interval):
                            # Start jetson_clocks
                            self.jetson_clocks.show_start()
                            # Set interval value
                            self.interval.value = interval
                            # Status start tegrastats
                            logger.info("tegrastats started {interval}ms".format(interval=int(interval * 1000)))
                    # Update timeout interval
                    timeout = interval * TIMEOUT_GAIN
                except queue.Empty:
                    # Close and log status
                    if self.tegra.close():
                        self.sync_event.clear()
                        # Start jetson_clocks
                        status_jc = self.jetson_clocks.show_stop()
                        logger.info("tegrastats close {}".format(status_jc))
                    # Disable timeout
                    timeout = None
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception:
            # Close tegra
            if self.tegra.close():
                self.sync_event.clear()
                # Start jetson_clocks
                status_jc = self.jetson_clocks.show_stop()
                logger.info("tegrastats close {}".format(status_jc))
            # Write error message
            self._error.put(sys.exc_info())

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
            self.start(force=True)
            # Get exception
            error = self._error.get()
            self.join()
            # Raise error if exist
            if error:
                ex_type, ex_value, tb_str = error
                ex_value.__traceback__ = tb_str
                raise ex_value
        except (KeyboardInterrupt, SystemExit):
            pass
        # Close communication
        self.close()

    def close(self):
        self.broadcaster.shutdown()
        # Close tegrastats
        if self.tegra.close():
            # Start jetson_clocks
            status_jc = self.jetson_clocks.show_stop()
            logger.info("tegrastats close {}".format(status_jc))
        # Remove authentication file
        if os.path.exists(AUTH_PATH):
            logger.info("Remove authentication {auth}".format(auth=AUTH_PATH))
            os.remove(AUTH_PATH)

    def tegra_stats(self, stats):
        # Make configuration dict
        data = {'interval': self.interval.value}
        logger.debug("tegrastats read")
        # Load data stats
        data['stats'] = stats
        # Add NVJPG engine
        data['stats']['NVJPG'] = nvjpg()
        # Load status jetson_clocks
        data['jc'] = self.jetson_clocks.show()
        data['jc'].update({'thread': self.jetson_clocks.is_running, 'boot': self.jetson_clocks.boot})
        # Read status NVPmodel
        if self.nvpmodel is not None:
            data['nvp'] = self.nvpmodel.modes()
        # Update status fan speed
        if self.fan is not None:
            data['fan'] = self.fan.update()
        # Swap status
        data['swap'] = self.swap.all()
        # Pack and send all data
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(data)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()

    def __del__(self):
        self.close()


def key_reader(AUTH_RE):
    with open(AUTH_PATH, 'r') as f:
        key = b64decode(f.readline()).decode('utf-8').replace(get_var(AUTH_RE), '')
    return key
# EOF
