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

import logging
import threading
# Launch command
import subprocess as sp
# Load queue library for python 2 and python 3
try:
    import queue
except ImportError:
    import Queue as queue
# Create logger
logger = logging.getLogger(__name__)


class Command(object):

    class TimeoutException(Exception):

        def __init__(self, message, errno=-1):
            self.message = message
            self.errno = errno

        def __str__(self):
            return "[errno:{errno}] {message}".format(message=self.message, errno=self.errno)

    def __init__(self, command):
        self.process = None
        self.command = command

    def __call__(self, timeout=None):
        def target(out_queue):
            # Run process
            self.process = sp.Popen(self.command, stdout=sp.PIPE, stderr=sp.PIPE)
            # Read lines output
            for line in iter(self.process.stdout.readline, b''):
                line = line.decode('utf-8')
                line = str(line.strip())
                out_queue.put(line)
            # Close and terminate
            self.process.stdout.close()
            self.process.wait()
        # Initialize lists
        out_queue = queue.Queue()
        thread = threading.Thread(target=target, args=(out_queue, ))
        thread.start()
        # Wait timeout process
        thread.join(timeout)
        if thread.is_alive():
            logger.error('Terminating process')
            self.process.terminate()
            thread.join()
        # Read the output
        if not out_queue.queue and self.process.returncode != 0:
            raise Command.TimeoutException('Process does not replied in time', self.process.returncode)
        return list(out_queue.queue)

    def communicate(self, timeout=None):
        self.__call__(timeout=timeout)
# EOF
