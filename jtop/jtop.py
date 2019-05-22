#!/usr/bin/env python
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
from collections import deque

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def import_os_variables(SOURCE, PATTERN="JETSON_"):
    if os.path.isfile(SOURCE):
        proc = sp.Popen(['bash', '-c', 'source {} && env'.format(SOURCE)], stdout=sp.PIPE)
        # Load variables
        source_env = {}
        for tup in map(lambda s: s.decode("utf-8").strip().split('=', 1), proc.stdout):
            name = tup[0].strip()
            value = tup[1].strip()
            if PATTERN in name:
                source_env[name] = value
        return source_env
    else:
        logging.error("File does not exist")
        return {}


def get_nvpmodel():
    # Read nvpmodel to know the status of the board
    try:
        nvpmodel_p = sp.Popen(['nvpmodel', '-q'], stdout=sp.PIPE)
        query = nvpmodel_p.communicate()[0]
        # Log value
        logger.debug('nvqmodel status %s', query)
        # Decode lines and split
        lines = query.decode("utf-8").split("\n")
        return {'name': lines[0].split(": ")[1], 'mode': int(lines[1])}
    except Exception:
        logger.error("Exception occurred", exc_info=True)
        return {}


class Tegrastats(Thread):
    """
        - Subprocess read:
        https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        - Property
        https://www.programiz.com/python-programming/property
    """
    # List of available fan
    LIST_FANS = ['/sys/kernel/debug/tegra_fan/target_pwm', '/sys/devices/pwm-fan/target_pwm']
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']

    class TegrastatsException(Exception):
        pass

    def __init__(self, interval=500, time=10.0):
        Thread.__init__(self)
        # Initialize number max records to record
        max_record = int(float(time) * (float(1 / float(interval)) * 1000.0))
        self.max_record = max_record
        # Sensors deque list
        self.swap = deque(max_record * [0], maxlen=max_record)
        self.iram = deque(max_record * [0], maxlen=max_record)
        self.ram = deque(max_record * [0], maxlen=max_record)
        self.cpus = {}
        self.emc = Tegrastats.initProcess("EMC", max_record)
        self.gpu = Tegrastats.initProcess("GPU", max_record)
        self.temperatures = {}
        self.voltages = {}
        # Find all fans availables
        self.fans = {}
        for fan in Tegrastats.LIST_FANS:
            if os.path.isfile(fan):
                self.fans[fan] = deque(max_record * [0], maxlen=max_record)
        # Initialize jetson stats
        self._jetsonstats = {}
        # Start process tegrastats
        tegrastats_file = ""
        for f_tegra in Tegrastats.TEGRASTATS:
            if os.path.isfile(f_tegra):
                logger.info("Load tegrastats {}".format(f_tegra))
                tegrastats_file = f_tegra
                break
        # Launch subprocess or raise and exception
        if tegrastats_file:
            self.p = sp.Popen([tegrastats_file, '--interval', str(interval)], stdout=sp.PIPE)
        else:
            logger.error("Tegrastats not in list!")
            raise Tegrastats.TegrastatsException("Tegrastats is not available on this hardware")

    def run(self):
        try:
            while self.p.poll() is None:
                # Read line process output
                line = self.p.stdout.readline()
                # Decode line in UTF-8
                tegrastats_data = line.decode("utf-8")
                # Decode and store
                self._jetsonstats = self.decode(tegrastats_data)
        except SystemExit:
            logger.error("System exit", exc_info=True)
        except AttributeError:
            logger.error("Attribute error", exc_info=True)

    @property
    def read(self):
        # Wait the deque not empty
        while not self._jetsonstats:
            pass
        # Return dictionary parsed
        return self._jetsonstats

    def open(self):
        # Start himself like file
        self.daemon = True
        self.start()

    def close(self):
        self.p.kill()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def updateProcess(text, status):
        status['idle'].pop(0)
        status['frequency'].pop(0)
        if 'off' in text:
            status['idle'].append(0.0)
            status['frequency'].append(0.0)
            status['status'] = "OFF"
        elif '@' in text:
            info = re.findall(r"\d+", text)
            status['idle'].append(float(info[0]))
            status['frequency'].append(float(info[1]))
            status['status'] = "ON"
        else:
            info = re.findall(r"\d+", text)
            status['idle'].append(float(info[0]))
            status['frequency'].append(0.0)
            status['status'] = "ON-SIMPLE"
        return status

    @staticmethod
    def initProcess(name, max_record):
        return {'name': name,
                'idle': max_record * [0.0],
                'frequency': max_record * [0.0],
                'status': "OFF",
                }

    def SWAP(self, text):
        # SWAP X/Y (cached Z)
        # X = Amount of SWAP in use in megabytes.
        # Y = Total amount of SWAP available for applications.
        # Z = Amount of SWAP cached in megabytes.
        find_swap = re.search(r'SWAP (.+?)B \(cached (.+?)B\)', text)
        if find_swap is not None:
            swap_string = find_swap.group()
            swap_stat = re.findall(r"\d+", swap_string)
            text = re.sub(r'SWAP (.+?)B \(cached (.+?)B\) ', '', text)
            self.swap.append(float(swap_stat[0]))
            return {'used': list(self.swap),
                    'total': float(swap_stat[1]),
                    'cached': int(swap_stat[2])
                    }, text
        else:
            return {}, text

    def IRAM(self, text):
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
            self.iram.append(float(iram_stat[0]))
            return {'used': list(self.iram),
                    'total': float(iram_stat[1]),
                    'size': int(iram_stat[2])
                    }, text
        else:
            return {}, text

    def RAM(self, text):
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
        ram_string = re.search(r'RAM (.+?)B', text).group()
        lfb_string = re.search(r'\(lfb (.+?)\)', text).group()
        ram_stat = re.findall(r"\d+", ram_string)
        lfb_stat = re.findall(r"\d+", lfb_string)
        text = re.sub(r'RAM (.+?)\) ', '', text)
        self.ram.append(float(ram_stat[0]))
        return {'RAM': {'used': list(self.ram), 'total': float(ram_stat[1])},
                'lfb': {'nblock': lfb_stat[0], 'size': lfb_stat[1]},
                }, text

    def CPU(self, text):
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
        cpu_string = re.search(r'CPU (.+?)\]', text).group()
        cpu_string = cpu_string[cpu_string.find("[") + 1:cpu_string.find("]")]
        text = re.sub(r'CPU (.+?)\] ', '', text)
        for idx, cpu in enumerate(cpu_string.split(",")):
            name = "CPU" + str(idx + 1)
            if idx in self.cpus:
                cpu_status = self.cpus[idx]
            else:
                cpu_status = Tegrastats.initProcess(name, self.max_record)
            cpu_status = Tegrastats.updateProcess(cpu, cpu_status)
            # Update status governor
            governor_name = '/sys/devices/system/cpu/cpu' + str(idx) + '/cpufreq/scaling_governor'
            if os.path.isfile(governor_name):
                with open(governor_name, 'r') as f:
                    cpu_status['governor'] = f.read()[:-1]
            else:
                cpu_status['governor'] = ""
            # Update status CPU
            self.cpus[idx] = cpu_status
        return text

    def getFans(self):
        # Read status from fan
        list_values = []
        for file_fan in self.fans:
            fan_status_p = sp.Popen(['cat', file_fan], stdout=sp.PIPE)
            query = fan_status_p.communicate()[0]
            logger.debug('{} status status {}'.format(file_fan, query))
            fan_level = int(query)
            self.fans[file_fan].append(float(fan_level) / 255.0 * 100.0)
            list_values += [list(self.fans[file_fan])]
        return list_values

    def decode(self, text):
        jetsonstats = {}
        # Read status disk
        jetsonstats['DISK'] = get_status_disk()
        # Extract nvpmodel
        nvpmodel = get_nvpmodel()
        if nvpmodel:
            jetsonstats['NVPMODEL'] = nvpmodel
        # Read status fan
        fans_level = self.getFans()
        if fans_level:
            jetsonstats['FAN'] = fans_level
        # Read SWAP status
        swap_status, text = self.SWAP(text)
        jetsonstats['SWAP'] = swap_status
        # Read IRAM status
        iram_status, text = self.IRAM(text)
        jetsonstats['IRAM'] = iram_status
        # Read RAM status
        ram_status, text = self.RAM(text)
        jetsonstats['RAM'] = ram_status
        # Read CPU status
        text = self.CPU(text)
        jetsonstats['CPU'] = list(self.cpus.values())
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
                self.emc = Tegrastats.updateProcess(other_values[idx + 1], self.emc)
                jetsonstats['EMC'] = self.emc
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
                self.gpu = Tegrastats.updateProcess(other_values[idx + 1], self.gpu)
                jetsonstats['GR3D'] = self.gpu
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
            elif '@' in data:
                # [temp name] C
                # [temp name] is one of the names under the nodes
                # /sys/devices/virtual/thermal/thermal_zoneX/type.
                info = data.split("@")
                name = info[0]
                value = info[1]
                # Read from dictionary temperature or initialize it
                if name in self.temperatures:
                    temp = self.temperatures[name]
                else:
                    temp = {'value': self.max_record * [0.0], 'unit': 'C'}
                # Remove last measured temp
                temp['value'].pop(0)
                # Add new value
                temp['value'].append(float(value.split("C")[0]))
                # Update text value
                temp['text'] = value
                # Store temperature value
                self.temperatures[name] = temp
            else:
                # [VDD_name] X/Y
                # X = Current power consumption in milliwatts.
                # Y = Average power consumption in milliwatts.
                value = other_values[idx + 1].split("/")
                # Read from dictionary temperature or initialize it
                if data in self.voltages:
                    volt = self.voltages[data]
                else:
                    volt = {'current': self.max_record * [0.0], 'average': self.max_record * [0.0], 'unit': 'mW'}
                # Remove last measure
                volt['current'].pop(0)
                volt['average'].pop(0)
                # Add new value
                volt['current'].append(float(value[0]))
                volt['average'].append(float(value[1]))
                # Update text value
                volt['text'] = other_values[idx + 1].rstrip() + "mW"
                # Store temperature value
                self.voltages[data] = volt
                # extra increase counter
                idx += 1
            # Update counter
            idx += 1
        # Add Temperatures and voltages
        jetsonstats['temperatures'] = self.temperatures
        jetsonstats['voltages'] = self.voltages
        return jetsonstats


def get_status_disk():
    disk = os.statvfs("/var/")
    # Evaluate the total space in GB
    totalSpace = float(disk.f_bsize * disk.f_blocks) / 1024 / 1024 / 1024
    # Evaluate total used space in GB
    totalUsedSpace = float(disk.f_bsize * (disk.f_blocks - disk.f_bfree)) / 1024 / 1024 / 1024
    # Evaluate total available space in GB
    totalAvailSpace = float(disk.f_bsize * disk.f_bfree) / 1024 / 1024 / 1024
    # Evaluate total non super-user space in GB
    totalAvailSpaceNonRoot = float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024
    return {'total': totalSpace,
            'used': totalUsedSpace,
            'available': totalAvailSpace,
            'available_no_root': totalAvailSpaceNonRoot
            }
# EOF
