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
import re
from copy import deepcopy
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)
# All regular exceptions
REGEXP = re.compile(r'(.+?): ((.*))')
CPU_SYS_REG = re.compile(r'cpu[0-9]')
CPU_SYS_STATE_REG = re.compile(r'state[0-9]')
# Proc stat CPU usage
# https://www.linuxhowtos.org/System/procstat.htm
# cpu0 793125 280 352516 16192366 50291 0 2012 0 0 0
CPU_PROG_REG = re.compile(r'cpu(.+?) ((.*))')


def cpu_info():
    list_cpu = {}
    num_cpu = 0
    with open("/proc/cpuinfo", "r") as fp:
        for line in fp:
            # Search line
            match = REGEXP.search(line)
            if match:
                key = match.group(1).rstrip()
                value = match.group(2).rstrip()
                # Load value or if it is a new processor initialize a new field
                if key == "processor":
                    num_cpu = int(value)
                    list_cpu[num_cpu] = {}
                    continue
                # Load cpu info
                list_cpu[num_cpu][key] = value
    return list_cpu


# CPU lines
# - user: normal processes executing in user mode
# - nice: niced processes executing in user mode
# - system: processes executing in kernel mode
# - idle: twiddling thumbs
# - iowait: waiting for I/O to complete
# - irq: servicing interrupts
# - softirq: servicing softirqs
CPU_STAT_LABEL = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'total']


def get_utilization(delta):
    # Return major outputs
    return {'user': 100.0 * (delta[0] / delta[-1]),
            'nice': 100.0 * (delta[1] / delta[-1]),
            'system': 100.0 * (delta[2] / delta[-1]),
            'idle': 100.0 * (delta[3] / delta[-1])
            }


def read_idle(path):
    # https://docs.kernel.org/admin-guide/pm/cpuidle.html
    states = [item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item)) and CPU_SYS_STATE_REG.search(item)]
    idle = {}
    for state in sorted(states):
        with open("{path}/{state}/name".format(path=path, state=state), 'r') as f:
            name = f.read().strip()
        with open("{path}/{state}/disable".format(path=path, state=state), 'r') as f:
            disable = int(f.read())
        idle[name] = disable
    return idle


def read_system_cpu(path, cpu_status={}):
    # Online status
    if os.path.isfile(path + "/online"):
        with open(path + "/online", 'r') as f:
            cpu_status['online'] = f.read().strip()
    # Read governor
    if os.path.isdir(path + "/cpufreq"):
        with open(path + "/cpufreq/scaling_governor", 'r') as f:
            cpu_status['governor'] = f.read().strip()
        # build dict freq
        freq = {}
        # Min frequency
        with open(path + "/cpufreq/scaling_min_freq", 'r') as f:
            freq['min'] = int(f.read())
        # Max frequency
        with open(path + "/cpufreq/scaling_max_freq", 'r') as f:
            freq['max'] = int(f.read())
        # Current frequency
        with open(path + "/cpufreq/scaling_cur_freq", 'r') as f:
            freq['cur'] = int(f.read())
        # Store values
        cpu_status['freq'] = freq
    # Read idle CPU
    if os.path.isdir(path + "/cpuidle"):
        cpu_status['idle_state'] = read_idle(path + "/cpuidle")
    return cpu_status


class CPUService(object):

    def __init__(self):
        # Load cpuinfo
        list_cpu = cpu_info()
        # List all CPU available
        path_system_cpu = "/sys/devices/system/cpu"
        self._cpu = {int(item[3:]): {'path': "{path}/{item}".format(path=path_system_cpu, item=item),
                                     'last_cpu': [0.0] * len(CPU_STAT_LABEL),
                                     'model': list_cpu.get(int(item[3:]), {}).get("model name", "")
                                     }
                     for item in os.listdir(path_system_cpu) if os.path.isdir(os.path.join(path_system_cpu, item)) and CPU_SYS_REG.search(item)}
        self._cpu_total = {'last_cpu': [0.0] * len(CPU_STAT_LABEL)}
        # Check available cpufreq and cpuidle
        if not os.path.isdir(path_system_cpu + "/cpu0/cpufreq"):
            logger.warning("cpufreq folder not available on this device!")
        if not os.path.isdir(path_system_cpu + "/cpu0/cpuidle"):
            logger.warning("cpuidle folder not available on this device!")

    def get_utilization(self):
        # CPU lines
        # - user: normal processes executing in user mode
        # - nice: niced processes executing in user mode
        # - system: processes executing in kernel mode
        # - idle: twiddling thumbs
        # - iowait: waiting for I/O to complete
        # - irq: servicing interrupts
        # - softirq: servicing softirqs
        cpu_out = {}
        total = {}
        with open("/proc/stat", 'r') as f:
            for line in f:
                match = CPU_PROG_REG.search(line)
                if match:
                    # Get all fields
                    fields = [float(column) for column in match.group(2).strip().split()[:7]]
                    # Add total in last field
                    fields += [sum(fields)]
                    if match.group(1).isdigit():
                        num_cpu = int(match.group(1))
                        # Evaluate delta all values
                        # https://rosettacode.org/wiki/Linux_CPU_utilization
                        delta = [now - last for now, last in zip(fields, self._cpu[num_cpu]['last_cpu'])]
                        # Update last value
                        self._cpu[num_cpu]['last_cpu'] = deepcopy(delta)
                        # Store utilization
                        cpu_out[num_cpu] = get_utilization(delta)
                    else:
                        # Evaluate delta all values
                        # https://rosettacode.org/wiki/Linux_CPU_utilization
                        delta = [now - last for now, last in zip(fields, self._cpu_total['last_cpu'])]
                        # Update last value
                        self._cpu_total['last_cpu'] = deepcopy(delta)
                        # Store utilization
                        total = get_utilization(delta)
        return total, cpu_out

    def read_sys_cpu(self, cpu_data={}):
        for cpu, data in sorted(self._cpu.items()):
            # store all data
            cpu_data[cpu] = read_system_cpu(data['path'], cpu_data[cpu])
            # add model
            cpu_data[cpu]['model'] = data['model']
        return cpu_data

    def get_status(self):
        # Usage CPU
        # https://stackoverflow.com/questions/8952462/cpu-usage-from-a-file-on-linux
        # https://www.linuxhowtos.org/System/procstat.htm
        # https://stackoverflow.com/questions/9229333/how-to-get-overall-cpu-usage-e-g-57-on-linux
        total, cpu_list = self.get_utilization()
        # Frequency and idle
        cpu_list = self.read_sys_cpu(cpu_list)
        return {'total': total, 'cpu': cpu_list}
# EOF
