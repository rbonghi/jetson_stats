# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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

import sys
import time
from threading import Thread, Event
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)

TIMER_READER_MIN_SLEEP = 0.05


class TimerReader:

    def __init__(self, callback):
        self._stop_event = Event()
        # Initialize callback
        self._callback = callback
        # Error message from thread
        self._error = None
        # Define Thread
        self._thread = None

    def _timer_callback(self, interval, stop_event):
        logger.debug("jtop timer start at {interval}s".format(interval=interval))
        try:
            while stop_event.is_set():
                start = time.time()
                # Callback function
                self._callback()
                # Measure timer_callback sleep time
                delta = time.time() - start
                # Start to sleep
                if interval > delta:
                    time.sleep(interval - delta)
        except (KeyboardInterrupt, SystemExit):
            logger.info("KeyboardInterrupt or SystemExit, exit timer_reader thread")
        except Exception as e:
            logger.fatal("Exception in 'timer_reader thread': {}".format(e))
            # Store error message
            self._error = sys.exc_info()
        logger.debug("jtop timer stopped")

    def open(self, interval=0.5):
        # Catch exception if exist
        self._error_status()
        # Check if not running
        if self._thread is not None:
            return False
        # Check if thread or process exist
        self._stop_event.set()
        # Start thread Service client
        self._thread = Thread(target=self._timer_callback, args=(interval, self._stop_event, ))
        self._thread.start()
        return True

    def close(self, timeout=None):
        # Catch exception if exist
        self._error_status()
        # Check if thread and process are already empty
        self._stop_event.clear()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        return True

    def _error_status(self):
        # Catch exception if exist
        if not self._error:
            return
        # Extract exception and raise
        ex_type, ex_value, tb_str = self._error
        ex_value.__traceback__ = tb_str
        raise ex_value
# EOF
