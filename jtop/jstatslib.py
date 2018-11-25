#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (C) 2018, Raffaello Bonghi <raffaello@rnext.it>
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

def get_RAM_status(text):
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
    ram_string = re.search('RAM (.+?)B', text).group()
    lfb_string = re.search('\(lfb (.+?)\)', text).group()
    ram_stat = re.findall("\d+", ram_string)
    lfb_stat = re.findall("\d+", lfb_string)
    text = re.sub('RAM (.+?)\) ', '', text)
    return {
        'RAM' : {'used': float(ram_stat[0]), 'total': float(ram_stat[1])},
        'lfb' : {'nblock': lfb_stat[0], 'size': lfb_stat[1]},
    }, text

def get_value_processor(name, text):
    if 'off' in text:
        return {'name': name}
    elif '@' in text:
        info = re.findall("\d+", text)
        return {'name': name, 'idle': float(info[0]), 'frequency': float(info[1])}
    else:
        info = re.findall("\d+", text)
        return {'name': name, 'idle': info[0]}
    return text

def get_CPU_status(text):
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
    cpu_string = re.search('CPU (.+?)\]', text).group()
    cpu_string = cpu_string[cpu_string.find("[")+1:cpu_string.find("]")]
    text = re.sub('CPU (.+?)\] ', '', text)
    cpus = []
    for idx, cpu in enumerate(cpu_string.split(",")):
            cpus.append(get_value_processor("CPU" + str(idx+1), cpu))
    
    return cpus, text

def get_status(text, fan_level=0):
    jetsonstats = {}
    jetsonstats['FAN'] = float(fan_level)/255.0 * 100.0
    # Read RAM status
    ram_status, text = get_RAM_status(text)
    jetsonstats['RAM'] = ram_status
    # Read CPU status
    cpu_status, text = get_CPU_status(text)
    jetsonstats['CPU'] = cpu_status
    
    temperatures = {}
    voltages = {}
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
            jetsonstats['EMC'] = get_value_processor("EMC", other_values[idx+1])
            # extra increase counter
            idx += 1
        elif 'APE' in data:
            # APE Y
            # APE is the audio processing engine. 
            # The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
            # Y = APE frequency in megahertz.
            jetsonstats['APE'] = other_values[idx+1]
            # extra increase counter
            idx += 1
        elif 'GR3D' in data:
            # GR3D X%@Y
            # GR3D is the GPU engine.
            # X = Percent of the GR3D that is being used, relative to the current running frequency.
            # Y = GR3D frequency in megahertz
            jetsonstats['GR3D'] = get_value_processor("GPU", other_values[idx+1])
            # extra increase counter
            idx += 1
        elif 'MTS' in data:
            # MTS fg X% bg Y%
            # X = Time spent in foreground tasks.
            # Y = Time spent in background tasks.
            fg = other_values[idx+2]
            bg = other_values[idx+4]
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
            temperatures[name] = { 'value': value, 'unit': 'C', 'text': value }
        else:
            # [VDD_name] X/Y
            # X = Current power consumption in milliwatts.
            # Y = Average power consumption in milliwatts.
            value = other_values[idx+1].split("/")
            voltages[data] = {'current': value[0], 'average': value[1], 'text': other_values[idx+1].rstrip()+"mW", 'unit': 'mW'}
            # extra increase counter
            idx += 1
        # Update counter
        idx +=1
    
    jetsonstats['temperatures'] = temperatures
    jetsonstats['voltages'] = voltages
    jetsonstats['other'] = text
    
    return jetsonstats
