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
# Launch command
import subprocess as sp
# Threading
from threading import Thread
# Tegrastats parser
from .tegra_parse import VALS, MTS, RAM, SWAP, IRAM, CPUS, TEMPS, WATTS
# Create logger for tegrastats
logger = logging.getLogger(__name__)


class Tegrastats:
    """
        - Subprocess read:
        https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        - Property
        https://www.programiz.com/python-programming/property
    """

    class TegrastatsException(Exception):
        pass

    def __init__(self, path):
        # Initialize jetson stats
        self._stats = {}
        # Start process tegrastats
        self.path = path
        # Define Tegrastats process
        self.p = None
        # Initialize observer
        self._observers = set()

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

    def _read_tegrastats(self):
        try:
            while self.p.poll() is None:
                out = self.p.stdout
                if out is not None:
                    # Read line process output
                    line = out.readline()
                    # Decode line in UTF-8
                    tegrastats_data = line.decode("utf-8")
                    # Decode and store
                    self._stats = self._decode(tegrastats_data)
                    # Notifiy all observers
                    for observer in self._observers:
                        observer(self._stats)
        except SystemExit:
            logger.error("System exit", exc_info=True)
        except AttributeError:
            logger.error("Attribute error", exc_info=True)

    def attach(self, observer):
        self._observers.add(observer)

    def detach(self, observer):
        self._observers.discard(observer)

    def open(self, interval=500):
        try:
            # Launch subprocess or raise and exception
            self.p = sp.Popen([self.path, '--interval', str(interval)], stdout=sp.PIPE)
            # Start thread Service client
            self._thread = Thread(target=self._read_tegrastats, args=[])
            self._thread.setDaemon = True
            self._thread.start()
            return True
        except OSError:
            logger.error("Tegrastats not in list!")
            raise Tegrastats.TegrastatsException("Tegrastats is not available on this hardware")
        return False

    def close(self):
        if self.p is not None:
            try:
                self.p.kill()
                return True
            except OSError:
                pass
        return False
# EOF
