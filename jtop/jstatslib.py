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

import re, os

def get_SWAP_status(text):
    # SWAP X/Y (cached Z)
    # X = Amount of SWAP in use in megabytes.
    # Y = Total amount of SWAP available for applications.
    # Z = Amount of SWAP cached in megabytes.
    find_swap = re.search('SWAP (.+?)B \(cached (.+?)B\)', text)    
    if find_swap is not None:
        swap_string = find_swap.group()
        swap_stat = re.findall("\d+", swap_string)
        text = re.sub('SWAP (.+?)B \(cached (.+?)B\) ', '', text)
        return {'used': float(swap_stat[0]), 
                'total': float(swap_stat[1]),
                'cached': int(swap_stat[2])
               }, text
    else:
        return {}, text

def get_IRAM_status(text):
    # IRAM X/Y (lfb Z)
    # IRAM is memory local to the video hardware engine.
    # X = Amount of IRAM memory in use, in kilobytes.
    # Y = Total amount of IRAM memory available.
    # Z = Size of the largest free block.
    find_iram = re.search('IRAM (.+?)B\(lfb (.+?)B\)', text)
    # Find if IRAM is inside
    if find_iram is not None:
        iram_lfb_string = find_iram.group()
        iram_stat = re.findall("\d+", iram_lfb_string)
        text = re.sub('IRAM (.+?)B\(lfb (.+?)B\) ', '', text)
        return {'used': float(iram_stat[0]), 
                'total': float(iram_stat[1]),
                'size': int(iram_stat[2])
               }, text
    else:
        return {}, text
    
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
            cpu_status = get_value_processor("CPU" + str(idx+1), cpu)
            f = open('/sys/devices/system/cpu/cpu'+ str(idx) + '/cpufreq/scaling_governor','r')
            cpu_status['governor'] = f.read()[:-1]
            f.close()
            cpus.append(cpu_status)
    
    return cpus, text

def get_status_disk():
    disk = os.statvfs("/var/")
    # Evaluate the total space in GB
    totalSpace = float(disk.f_bsize*disk.f_blocks)/1024/1024/1024
    # Evaluate total used space in GB
    totalUsedSpace = float(disk.f_bsize*(disk.f_blocks-disk.f_bfree))/1024/1024/1024
    # Evaluate total available space in GB
    totalAvailSpace = float(disk.f_bsize*disk.f_bfree)/1024/1024/1024
    # Evaluate total non super-user space in GB
    totalAvailSpaceNonRoot = float(disk.f_bsize*disk.f_bavail)/1024/1024/1024
    return {'total'             : totalSpace,
            'used'              : totalUsedSpace,
            'available'         : totalAvailSpace,
            'available_no_root' : totalAvailSpaceNonRoot
           }
    

def get_status(text, fan_level=None, nvpmodel=""):
    jetsonstats = {}
    # Read status disk
    jetsonstats['DISK'] = get_status_disk()
    # Extract nvpmodel
    if nvpmodel:
        lines = nvpmodel.split("\n")
        jetsonstats['NVPMODEL'] = {'name': lines[0].split(": ")[1], 'mode': int(lines[1])}
    # Read status fan
    if fan_level is not None:
        jetsonstats['FAN'] = float(fan_level)/255.0 * 100.0
    # Read SWAP status
    swap_status, text = get_SWAP_status(text)
    jetsonstats['SWAP'] = swap_status
    # Read IRAM status
    iram_status, text = get_IRAM_status(text)
    jetsonstats['IRAM'] = iram_status
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
            fg = float(other_values[idx+2].split("%")[0])
            bg = float(other_values[idx+4].split("%")[0])
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
            temperatures[name] = { 'value': float(value.split("C")[0]), 'unit': 'C', 'text': value }
        else:
            # [VDD_name] X/Y
            # X = Current power consumption in milliwatts.
            # Y = Average power consumption in milliwatts.
            value = other_values[idx+1].split("/")
            voltages[data] = {'current': int(value[0]), 'average': int(value[1]), 'unit': 'mW', 'text': other_values[idx+1].rstrip()+"mW"}
            # extra increase counter
            idx += 1
        # Update counter
        idx +=1
    
    # Add Temperatures and voltages
    jetsonstats['temperatures'] = temperatures
    jetsonstats['voltages'] = voltages
    
    return jetsonstats
