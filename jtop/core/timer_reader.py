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

from threading import Thread, Event
import time
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)


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
                # Callback function
                self._callback()
                # Start to sleep
                time.sleep(interval)
        except (KeyboardInterrupt, SystemExit):
            pass
        except AttributeError:
            pass
        except IOError:
            pass
        logger.debug("jtop timer stopped")

    def open(self, interval=0.5):
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
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value
        # Check if thread and process are already empty
        self._stop_event.clear()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        return True
# EOF
