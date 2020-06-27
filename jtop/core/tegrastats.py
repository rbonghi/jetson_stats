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
import os
import sys
# Launch command
import subprocess as sp
# Threading
from threading import Thread
# Exceptions
from .exceptions import JtopException
# Tegrastats parser
from .tegra_parse import VALS, MTS, RAM, SWAP, IRAM, CPUS, TEMPS, WATTS
# Create logger for tegrastats
logger = logging.getLogger(__name__)


def locate_tegrastats():
    for f_tegra in ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']:
        if os.path.isfile(f_tegra):
            logger.info("Load tegrastats {}".format(f_tegra))
            return f_tegra
    raise JtopException("Tegrastats is not availabe on this board")


class Tegrastats:
    """
        - Subprocess read:
        https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        - Property
        https://www.programiz.com/python-programming/property
    """

    def __init__(self, callback):
        # Error message from thread
        self._error = None
        # Initialize jetson stats
        self._stats = {}
        # Start process tegrastats
        self.path = locate_tegrastats()
        # Define Tegrastats process
        self._thread = None
        self.p = None
        # Initialize callback
        self.callback = callback

    def _decode(self, text):
        # Find and parse all single values
        stats = VALS(text)
        # Parse if exist MTS
        mts = MTS(text)
        if mts:
            stats['MTS'] = mts
        # Parse RAM
        stats['RAM'] = RAM(text)
        # If exists parse SWAP
        swap = SWAP(text)
        if swap:
            stats['SWAP'] = swap
        # If exists parse IRAM
        iram = IRAM(text)
        if iram:
            stats['IRAM'] = iram
        # Parse CPU status
        stats['CPU'] = CPUS(text)
        # Parse temperatures
        stats['TEMP'] = TEMPS(text)
        # Parse Watts
        stats['WATT'] = WATTS(text)
        return stats

    def _read_tegrastats(self, interval):
        try:
            # Reading loop
            while self.p.poll() is None:
                out = self.p.stdout
                if out is not None:
                    # Read line process output
                    line = out.readline()
                    # Decode line in UTF-8
                    tegrastats_data = line.decode("utf-8")
                    # Decode and store
                    self._stats = self._decode(tegrastats_data)
                    # Launch callback
                    if self.p is not None:
                        self.callback(self._stats)
        except AttributeError:
            # Error when is close the process
            pass
        except Exception:
            # Write error message
            self._error = sys.exc_info()
        # Kill process if alive
        if self.p is not None:
            # Kill
            try:
                self.p.kill()
            except OSError:
                pass
            # Reset variable
            self.p = None

    def open(self, interval=0.5):
        # Set timeout
        interval = int(interval * 1000)
        # Check if thread or process exist
        if self.p is not None:
            return False
        # Launch subprocess or raise and exception
        self.p = sp.Popen([self.path, '--interval', str(interval)], stdout=sp.PIPE)
        # Start thread Service client
        self._thread = Thread(target=self._read_tegrastats, args=[interval])
        self._thread.start()
        return True

    def close(self):
        self._thread = None
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value
        # Check if thread and process are already empty
        if self.p is None:
            return False
        try:
            self.p.kill()
        except OSError:
            pass
        # Clean process variable
        self.p = None
        return True
# EOF
