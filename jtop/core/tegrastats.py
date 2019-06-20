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

import re
import os
# Logging
import logging
# Launch command
import subprocess as sp
# Threading
from threading import Thread

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def Parameter(name, text):
    status = {"name": name}
    if 'off' in text:
        status['status'] = "OFF"
    elif '@' in text:
        info = re.findall(r"\d+", text)
        status['value'] = int(info[0])
        status['frequency'] = int(info[1])
        status['status'] = "ON"
    else:
        info = re.findall(r"\d+", text)
        status['value'] = int(info[0])
        status['status'] = "ON-SIMPLE"
    return status


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
        self._jetsonstats = {}
        # Start process tegrastats
        self.path = path
        # Callback function
        self.callback = None
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
                    stats = self.decode(tegrastats_data)
                    # Update status jetson_stats
                    self._jetsonstats = stats
                    # Notifiy all observers
                    for observer in self._observers:
                        observer.update(stats)
        except SystemExit:
            logger.error("System exit", exc_info=True)
        except AttributeError:
            logger.error("Attribute error", exc_info=True)

    @property
    def stats(self):
        # Wait the deque not empty
        while not self._jetsonstats:
            pass
        # Return dictionary parsed
        return self._jetsonstats

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

    def decode(self, text):
        jetsonstats = {}
        # Read SWAP status
        swap_status, text = parse_SWAP(text)
        jetsonstats['SWAP'] = swap_status
        # Read IRAM status
        iram_status, text = parse_IRAM(text)
        jetsonstats['IRAM'] = iram_status
        # Read RAM status
        ram_status, text = parse_RAM(text)
        jetsonstats['RAM'] = ram_status
        # Read CPU status
        cpu, text = parse_CPU(text)
        jetsonstats['CPU'] = cpu
        # EMC status
        jetsonstats['EMC'] = {"name": "EMC", "status": "REQUIRE SUDO"}
        # Add GPU status
        jetsonstats['GR3D'] = {"name": "EMC", "status": "REQUIRE SUDO"}
        # Init dictionaries
        temperatures = {}
        voltages = {}
        # Start while loop to decode
        idx = 0
        other_values = text.split(" ")
        while idx < len(other_values):
            data = other_values[idx]
            if 'EMC' in data:
                # EMC X%@Y
                # EMC is the external memory controller,
                # through which all sysmem/carve-out/GART memory accesses go.
                # X = Percent of EMC memory bandwidth being used, relative to the current running frequency.
                # Y = EMC frequency in megahertz.
                jetsonstats['EMC'] = Parameter("EMC", other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif 'APE' in data:
                # APE Y
                # APE is the audio processing engine.
                # The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
                # Y = APE frequency in megahertz.
                jetsonstats['APE'] = other_values[idx + 1]
                # extra increase counter
                idx += 1
            elif 'GR3D' in data:
                # GR3D X%@Y
                # GR3D is the GPU engine.
                # X = Percent of the GR3D that is being used, relative to the current running frequency.
                # Y = GR3D frequency in megahertz
                jetsonstats['GR3D'] = Parameter("GR3D", other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif 'MTS' in data:
                # MTS fg X% bg Y%
                # X = Time spent in foreground tasks.
                # Y = Time spent in background tasks.
                fg = float(other_values[idx + 2].split("%")[0])
                bg = float(other_values[idx + 4].split("%")[0])
                jetsonstats['MTS'] = {'fg': fg, 'bg': bg}
                # extra increase counter
                idx += 4
            elif 'MSENC' in data:
                # MSENC Y
                # Y = MSENC frequency in megahertz.
                # MSENC is the video hardware encoding engine.
                jetsonstats['MSENC'] = int(other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif 'NVDEC' in data:
                # NVDEC Y
                # Y = NVDEC frequency in megahertz.
                # NVDEC is the video hardware decoding engine.
                # It is shown only when hardware decoder/encoder engine is used.
                jetsonstats['NVDEC'] = int(other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif '@' in data:
                # [temp name] C
                # [temp name] is one of the names under the nodes
                # /sys/devices/virtual/thermal/thermal_zoneX/type.
                info = data.split("@")
                name = info[0].strip()
                value = info[1]
                # Save temperature in dictionary
                temperatures[name] = {'value': float(value.split("C")[0]),
                                      'unit': 'C'}
            elif idx + 1 < len(other_values):
                # [VDD_name] X/Y
                # X = Current power consumption in milliwatts.
                # Y = Average power consumption in milliwatts.
                value = other_values[idx + 1].split("/")
                # Save voltages in dictionary
                voltages[data] = {'current': float(value[0]),
                                  'average': float(value[1]),
                                  'unit': 'mW'}
                # extra increase counter
                idx += 1
            # Update counter
            idx += 1
        # Add Temperatures and voltages
        jetsonstats['temperatures'] = temperatures
        jetsonstats['voltages'] = voltages
        return jetsonstats


def parse_SWAP(text):
    # SWAP X/Y (cached Z)
    # X = Amount of SWAP in use in megabytes.
    # Y = Total amount of SWAP available for applications.
    # Z = Amount of SWAP cached in megabytes.
    find_swap = re.search(r'SWAP (.+?)B \(cached (.+?)B\)', text)
    if find_swap is not None:
        swap_string = find_swap.group()
        swap_stat = re.findall(r"\d+", swap_string)
        text = re.sub(r'SWAP (.+?)B \(cached (.+?)B\) ', '', text)
        return {'used': int(swap_stat[0]),
                'total': int(swap_stat[1]),
                'cached': int(swap_stat[2])
                }, text
    else:
        return {}, text


def parse_IRAM(text):
    # IRAM X/Y (lfb Z)
    # IRAM is memory local to the video hardware engine.
    # X = Amount of IRAM memory in use, in kilobytes.
    # Y = Total amount of IRAM memory available.
    # Z = Size of the largest free block.
    find_iram = re.search(r'IRAM (.+?)B\(lfb (.+?)B\)', text)
    # Find if IRAM is inside
    if find_iram is not None:
        iram_lfb_string = find_iram.group()
        iram_stat = re.findall(r"\d+", iram_lfb_string)
        text = re.sub(r'IRAM (.+?)B\(lfb (.+?)B\) ', '', text)
        return {'used': int(iram_stat[0]),
                'total': int(iram_stat[1]),
                'size': int(iram_stat[2])
                }, text
    else:
        return {}, text


def parse_RAM(text):
    # RAM X/Y (lfb NxZ)
    # Largest Free Block (lfb) is a statistic about the memory allocator.
    # It refers to the largest contiguous block of physical memory
    # that can currently be allocated: at most 4 MB.
    # It can become smaller with memory fragmentation.
    # The physical allocations in virtual memory can be bigger.
    # X = Amount of RAM in use in MB.
    # Y = Total amount of RAM available for applications.
    # N = The number of free blocks of this size.
    # Z = is the size of the largest free block.
    ram_search = re.search(r'RAM (.+?)B', text)
    lfb_search = re.search(r'\(lfb (.+?)\)', text)
    if ram_search is not None and lfb_search is not None:
        ram_string = ram_search.group()
        lfb_string = lfb_search.group()
        ram_stat = re.findall(r"\d+", ram_string)
        lfb_stat = re.findall(r"\d+", lfb_string)
        text = re.sub(r'RAM (.+?)\) ', '', text)
        return {'RAM': {'used': int(ram_stat[0]), 'total': int(ram_stat[1])},
                'lfb': {'nblock': lfb_stat[0], 'size': lfb_stat[1]},
                }, text
    else:
        return {}, text


def parse_CPU(text):
    # CPU [X%,Y%, , ]@Z
    # or
    # CPU [X%@Z, Y%@Z,...]
    # X and Y are rough approximations based on time spent
    # in the system idle process as reported by the Linux kernel in /proc/stat.
    # X = Load statistics for each of the CPU cores relative to the
    #     current running frequency Z, or 'off' in case a core is currently powered down.
    # Y = Load statistics for each of the CPU cores relative to the
    #     current running frequency Z, or 'off' in case a core is currently powered down.
    # Z = CPU frequency in megahertz. Goes up or down dynamically depending on the CPU workload.
    cpu_search = re.search(r'CPU (.+?)\]', text)
    cpus = []
    if cpu_search is not None:
        cpu_string = cpu_search.group()
        cpu_string = cpu_string[cpu_string.find("[") + 1:cpu_string.find("]")]
        text = re.sub(r'CPU (.+?)\] ', '', text)
        for idx, cpu in enumerate(cpu_string.split(",")):
            name = "CPU" + str(idx + 1)
            # Make dictionary from CPU status
            cpu_status = Parameter(name, cpu)
            # Update status governor
            governor_name = '/sys/devices/system/cpu/cpu' + str(idx) + '/cpufreq/scaling_governor'
            # Add governor CPU if only exist
            if os.path.isfile(governor_name):
                with open(governor_name, 'r') as f:
                    cpu_status['governor'] = f.read()[:-1]
            # Update status CPU
            cpus += [cpu_status]
        return cpus, text
    else:
        return cpus, text
# EOF
