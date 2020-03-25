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

import re
import os
# All regular expressions
SWAP_RE = re.compile(r'SWAP (\d+)\/(\d+)(\w)B( ?)\(cached (\d+)(\w)B\)')
IRAM_RE = re.compile(r'IRAM (\d+)\/(\d+)(\w)B( ?)\(lfb (\d+)(\w)B\)')
RAM_RE = re.compile(r'RAM (\d+)\/(\d+)(\w)B( ?)\(lfb (\d+)x(\d+)(\w)B\)')
MTS_RE = re.compile(r'MTS fg (\d+)% bg (\d+)%')
VALS_RE = re.compile(r'\b([A-Z0-9_]+) ([0-9%@]+)(?=[^/])\b')
VAL_FRE_RE = re.compile(r'\b(\d+)%@(\d+)')
CPU_RE = re.compile(r'CPU \[(.*?)\]')
WATT_RE = re.compile(r'\b(\w+) ([0-9.]+)\/([0-9.]+)\b')
TEMP_RE = re.compile(r'\b(\w+)@(-?[0-9.]+)C\b')


def val_freq(val):
    if '@' in val:
        match = VAL_FRE_RE.search(val)
        return {'val': int(match.group(1)), 'frq': int(match.group(2))}
    else:
        return {'val': int(val)}


def SWAP(text):
    """
        SWAP X/Y (cached Z)
        X = Amount of SWAP in use in megabytes.
        Y = Total amount of SWAP available for applications.
        Z = Amount of SWAP cached in megabytes.
    """
    match = SWAP_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'cached': {'size': int(match.group(5)),
                           'unit': match.group(6)}}
    else:
        return {}


def IRAM(text):
    """
        IRAM X/Y (lfb Z)
        IRAM is memory local to the video hardware engine.
        X = Amount of IRAM memory in use, in kilobytes.
        Y = Total amount of IRAM memory available.
        Z = Size of the largest free block.
    """
    match = IRAM_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'lfb': {'size': int(match.group(5)),
                        'unit': match.group(6)}}
    else:
        return {}


def RAM(text):
    """
        RAM X/Y (lfb NxZ)
        Largest Free Block (lfb) is a statistic about the memory allocator.
        It refers to the largest contiguous block of physical memory
        that can currently be allocated: at most 4 MB.
        It can become smaller with memory fragmentation.
        The physical allocations in virtual memory can be bigger.
        X = Amount of RAM in use in MB.
        Y = Total amount of RAM available for applications.
        N = The number of free blocks of this size.
        Z = is the size of the largest free block.
    """
    match = RAM_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'lfb': {'nblock': int(match.group(5)),
                        'size': int(match.group(6)),
                        'unit': match.group(7)}
                }
    else:
        return {}


def MTS(text):
    """ Parse MTS

        MTS fg X% bg Y%
        X = Time spent in foreground tasks.
        Y = Time spent in background tasks.
    """
    match = MTS_RE.search(text)
    if match:
        return {'fg': int(match.group(1)), 'bg': int(match.group(1))}
    else:
        return {}


def VALS(text):
    """ Add all values

        Parse all type of vals:
        - EMC X%@Y
          EMC is the external memory controller,
          through which all sysmem/carve-out/GART memory accesses go.
          X = Percent of EMC memory bandwidth being used, relative to the current running frequency.
          Y = EMC frequency in megahertz.
        - APE Y
          APE is the audio processing engine.
          The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
          Y = APE frequency in megahertz.
        - GR3D X%@Y
          GR3D is the GPU engine.
          X = Percent of the GR3D that is being used, relative to the current running frequency.
          Y = GR3D frequency in megahertz
        - MSENC Y
          Y = MSENC frequency in megahertz.
          MSENC is the video hardware encoding engine.
        - NVENC Y
          Y = NVENC frequency in megahertz.
          NVENC is the video hardware encoding engine.
        - NVDEC Y
          Y = NVDEC frequency in megahertz.
          NVDEC is the video hardware decoding engine.
          It is shown only when hardware decoder/encoder engine is used.
    """
    vals = {}
    for name, val in re.findall(VALS_RE, text):
        # Remove from name "FREQ" name
        name = name.split('_')[0] if "FREQ" in name else name
        # Export value
        vals[name] = val_freq(val)
    return vals


def CPUS(text):
    """ Parse CPU information and extract status

        CPU [X%,Y%, , ]@Z or CPU [X%@Z, Y%@Z,...]
        X and Y are rough approximations based on time spent
        in the system idle process as reported by the Linux kernel in /proc/stat.
        X = Load statistics for each of the CPU cores relative to the
            current running frequency Z, or 'off' in case a core is currently powered down.
        Y = Load statistics for each of the CPU cores relative to the
            current running frequency Z, or 'off' in case a core is currently powered down.
        Z = CPU frequency in megahertz. Goes up or down dynamically depending on the CPU workload.
    """
    match = CPU_RE.search(text)
    cpus = []
    if match:
        # Extract
        cpus_list = match.group(1).split(',')
        for idx, cpu_str in enumerate(cpus_list):
            # Set name CPU
            cpu = {'name': 'CPU' + str(idx + 1)}
            # status
            if 'off' == cpu_str:
                cpu['status'] = "OFF"
            else:
                cpu['status'] = "ON"
                val = val_freq(cpu_str)
                cpu.update(val)
                # Update status governor
                governor_name = '/sys/devices/system/cpu/cpu' + str(idx) + '/cpufreq/scaling_governor'
                # Add governor CPU if only exist
                if os.path.isfile(governor_name):
                    with open(governor_name, 'r') as f:
                        cpu['governor'] = f.read()[:-1]
            # Add in list
            cpus += [cpu]
    return cpus


def TEMPS(text):
    """ Parse all temperatures in tegrastats output

        [temp name]@XC
        [temp name] is one of the names under the nodes
        X = Current temperature
        /sys/devices/virtual/thermal/thermal_zoneX/type.
    """
    return {name: float(val) for name, val in re.findall(TEMP_RE, text)}


def WATTS(text):
    """ Parse all milliwats in tegrastats output

        [VDD_name] X/Y
        X = Current power consumption in milliwatts.
        Y = Average power consumption in milliwatts.
    """
    return {name: {'cur': int(cur), 'avg': int(avg)} for name, cur, avg in re.findall(WATT_RE, text)}
# EOF
