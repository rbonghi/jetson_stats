# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Logging
import logging
# Launch command
import subprocess as sp
# Threading
from threading import Thread
# Tegrastats parser
from .tegra_parse import VALS, MTS, RAM, SWAP, IRAM, CPUS, TEMPS, VOLTS

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class Tegrastats(Thread):
    """
        - Subprocess read:
        https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        - Property
        https://www.programiz.com/python-programming/property
    """

    class TegrastatsException(Exception):
        pass

    def __init__(self, path, interval):
        Thread.__init__(self)
        # Set interval tegrastats
        self.interval = interval
        # Initialize jetson stats
        self._stats = {}
        # Start process tegrastats
        self.path = path
        # Define Tegrastats process
        self.p = None
        # Initialize observer
        self._observers = set()

    def run(self):
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
                        observer.update(self._stats)
        except SystemExit:
            logger.error("System exit", exc_info=True)
        except AttributeError:
            logger.error("Attribute error", exc_info=True)

    @property
    def stats(self):
        # Return dictionary parsed
        return self._stats

    def attach(self, observer):
        self._observers.add(observer)

    def detach(self, observer):
        self._observers.discard(observer)

    def open(self, callback=None):
        try:
            # Launch subprocess or raise and exception
            self.p = sp.Popen([self.path, '--interval', str(self.interval)], stdout=sp.PIPE)
            # Start himself like file
            self.daemon = True
            self.start()
            # Wait first value not empty
            while not self._stats:
                pass
            # If callback is defined after each decode will be send the updates by function
            if callback is not None:
                self.attach(callback)
            return True
        except OSError:
            logger.error("Tegrastats not in list!")
            raise Tegrastats.TegrastatsException("Tegrastats is not available on this hardware")
        return False

    def close(self):
        if self.p is not None:
            self.p.kill()
            return True
        else:
            return False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

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
        # Parse voltages
        stats['VOLT'] = VOLTS(text)
        return stats
# EOF
