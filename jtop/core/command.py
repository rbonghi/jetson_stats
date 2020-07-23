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
import sys
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
EXTRA_TIMEOUT = 1.0
# Reference:
# https://eli.thegreenplace.net/2017/interacting-with-a-long-running-child-process-in-python/
# https://stackoverflow.com/questions/37942022/returncode-of-popen-object-is-none-after-the-process-is-terminated/42376107
# https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
# https://docs.python.org/3/tutorial/errors.html
# https://stackoverflow.com/questions/10756383/timeout-on-subprocess-readline-in-python
# https://stackoverflow.com/questions/3733270/python-subprocess-timeout


class Command(object):

    class CommandException(Exception):

        def __init__(self, message, errno):
            self.message = message
            self.errno = errno

        def __str__(self):
            return "[errno:{errno}] {message}".format(message=self.message, errno=self.errno)

    class TimeoutException(CommandException):

        def __init__(self):
            super(Command.TimeoutException, self).__init__("Process does not replied in time", -1)

    @staticmethod
    def run_command(command, repeat=5, timeout=2):
        cmd = Command(command)
        for idx in range(repeat):
            try:
                return cmd(timeout=timeout)
            except Command.TimeoutException as error:
                logger.error("[{idx}] {error}".format(idx=idx, error=error))
        raise Command.CommandException("Error to start {command}".format(command=command), -2)

    def __init__(self, command):
        self.process = None
        self.command = command

    def __call__(self, timeout=None):
        def target(out_queue, err_queue):
            # Run process
            try:
                # https://stackoverflow.com/questions/33277452/prevent-unexpected-stdin-reads-and-lock-in-subprocess
                self.process = sp.Popen(self.command, stdout=sp.PIPE, stderr=sp.PIPE, stdin=open(os.devnull), preexec_fn=os.setsid)
                # Read lines output
                for line in iter(self.process.stdout.readline, b''):
                    line = line.decode('utf-8')
                    line = str(line.strip())
                    out_queue.put(line)
                # Close and terminate
                self.process.stdout.close()
                self.process.wait()
            except Exception:
                # Store error message
                err_queue.put(sys.exc_info())
        # Initialize lists
        is_timeout = False
        out_queue = queue.Queue()
        err_queue = queue.Queue()
        thread = threading.Thread(target=target, args=(out_queue, err_queue, ))
        thread.start()
        # Wait timeout process
        thread.join(timeout)
        if thread.is_alive():
            logger.error('Terminating process: {command}'.format(command=self.command))
            if self.process is not None:
                self.process.terminate()
            thread.join(timeout=EXTRA_TIMEOUT)
            logger.warning('Process terminated: {command}'.format(command=self.command))
            is_timeout = True
        # Read the output
        # Extract exception and raise
        if not err_queue.empty():
            ex_type, ex_value, tb_str = err_queue.get()
            ex_value.__traceback__ = tb_str
            raise ex_value
        if is_timeout:
            raise Command.TimeoutException()
        if self.process.returncode != 0:
            raise Command.CommandException('Error process:', self.process.returncode)
        return list(out_queue.queue)

    def communicate(self, timeout=None):
        self.__call__(timeout=timeout)
# EOF
