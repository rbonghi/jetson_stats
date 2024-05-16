# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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
    if delta[-1] == 0:
        return {'user': 0, 'nice': 0, 'system': 0, 'idle': 0}
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


def read_freq_cpu(path, type_freq):
    # build dict freq
    freq = {}
    # Min frequency
    with open("{path}/cpufreq/{type_freq}_min_freq".format(path=path, type_freq=type_freq), 'r') as f:
        freq['min'] = int(f.read())
    # Max frequency
    with open("{path}/cpufreq/{type_freq}_max_freq".format(path=path, type_freq=type_freq), 'r') as f:
        freq['max'] = int(f.read())
    # Current frequency
    current_path = "{path}/cpufreq/{type_freq}_cur_freq".format(path=path, type_freq=type_freq)
    if os.path.isfile(current_path):
        with open(current_path, 'r') as f:
            data = f.read().strip()
            if data.isdigit():
                freq['cur'] = int(data)
    return freq


def read_system_cpu(path, cpu_status={}):
    # Online status
    cpu_status['online'] = True
    if os.path.isfile(path + "/online"):
        with open(path + "/online", 'r') as f:
            cpu_status['online'] = f.read().strip() == '1'
    # Read governor only if CPU is online
    if cpu_status['online']:
        if os.path.isdir(path + "/cpufreq"):
            with open(path + "/cpufreq/scaling_governor", 'r') as f:
                cpu_status['governor'] = f.read().strip()
            # Store values
            cpu_status['freq'] = read_freq_cpu(path, 'scaling')
            cpu_status['info_freq'] = read_freq_cpu(path, 'cpuinfo')
        # Read idle CPU
        if os.path.isdir(path + "/cpuidle"):
            cpu_status['idle_state'] = read_idle(path + "/cpuidle")
    return cpu_status


class CPUService(object):

    def __init__(self):
        self._cpu_online = []
        # Load cpuinfo
        self._list_cpu = cpu_info()
        # List all CPU available
        self._proc_stat = "/proc/stat"
        path_system_cpu = "/sys/devices/system/cpu"
        if os.getenv('JTOP_TESTING', False):
            self._proc_stat = "/fake_sys/stat"
            path_system_cpu = "/fake_sys/devices/system/cpu"
            logger.warning("Running in JTOP_TESTING file={root_dir}".format(root_dir=self._proc_stat))
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=path_system_cpu))
        if not os.path.isdir("/sys/devices/system/cpu"):
            raise Exception("Doesn't exist any CPU!")
        # Build a CPU list
        cpu_list = {int(item[3:]): {'path': "{path}/{item}".format(path=path_system_cpu, item=item),
                                    'last_cpu': [0.0] * len(CPU_STAT_LABEL),
                                    }
                    for item in os.listdir(path_system_cpu) if os.path.isdir(os.path.join(path_system_cpu, item)) and CPU_SYS_REG.search(item)}
        # Sort CPU list in a list by CPU name
        self._cpu = [cpu_list[i] for i in sorted(cpu_list)]
        # Status CPU service at start
        logger.info("Found {cpu} CPU".format(cpu=len(cpu_list)))
        # Build CPU total info
        self._cpu_total = {'last_cpu': [0.0] * len(CPU_STAT_LABEL)}
        # Check available cpufreq and cpuidle
        if not os.path.isdir(path_system_cpu + "/cpu0/cpufreq"):
            logger.warning("cpufreq folder not available on this device!")
        if not os.path.isdir(path_system_cpu + "/cpu0/cpuidle"):
            logger.warning("cpuidle folder not available on this device!")

    def reset_estimation(self):
        # reset estimation status cpu
        for cpu in self._cpu:
            cpu['last_cpu'] = [0.0] * len(CPU_STAT_LABEL)
        # Build CPU total info
        self._cpu_total = {'last_cpu': [0.0] * len(CPU_STAT_LABEL)}

    def get_cpu_info(self):
        # Load cpuinfo
        list_cpu = cpu_info()
        return [{'model': list_cpu.get(cpu, {}).get("model name", "")} for cpu in range(len(self._cpu))]

    def get_utilization(self, cpu_out):
        # CPU lines
        # - user: normal processes executing in user mode
        # - nice: niced processes executing in user mode
        # - system: processes executing in kernel mode
        # - idle: twiddling thumbs
        # - iowait: waiting for I/O to complete
        # - irq: servicing interrupts
        # - softirq: servicing softirqs
        total = {}
        with open(self._proc_stat, 'r') as f:
            for line in f:
                match = CPU_PROG_REG.search(line)
                if match:
                    # Get all fields
                    # 7 is equal to len(CPU_STAT_LABEL) - 1 (no total)
                    fields = [float(column) for column in match.group(2).strip().split()[:7]]
                    # Add total in last field
                    fields += [sum(fields)]
                    if match.group(1).isdigit():
                        num_cpu = int(match.group(1))
                        # Evaluate delta all values
                        # https://rosettacode.org/wiki/Linux_CPU_utilization
                        delta = [now - last for now, last in zip(fields, self._cpu[num_cpu]['last_cpu'])]
                        # Update last value
                        self._cpu[num_cpu]['last_cpu'] = deepcopy(fields)
                        # Store utilization
                        cpu_out[num_cpu].update(get_utilization(delta))
                    else:
                        # Evaluate delta all values
                        # https://rosettacode.org/wiki/Linux_CPU_utilization
                        delta = [now - last for now, last in zip(fields, self._cpu_total['last_cpu'])]
                        # Update last value
                        self._cpu_total['last_cpu'] = deepcopy(delta)
                        # Store utilization
                        total = get_utilization(delta)
                else:
                    # All CPU are in order on this file, if don't match we can skip it
                    break
        return total, cpu_out

    def get_status(self):
        # Status CPU
        cpu_list = [{} for i in range(len(self._cpu))]
        cpu_online = []
        # Add cpu status with frequency and idle config
        for cpu, data in enumerate(self._cpu):
            # store all data
            cpu_list[cpu] = read_system_cpu(data['path'], cpu_list[cpu])
            # Add model in CPU output
            cpu_list[cpu]['model'] = self._list_cpu.get(cpu, {}).get("model name", "")
            # Check status CPU
            cpu_online += [cpu_list[cpu]['online']]
        # Status number CPU changed if changed reset esimators
        # Fix weird TOTAL status when the number of CPU are changed (Numbers negative)
        for new, old in zip(cpu_online, self._cpu_online):
            if new != old:
                logger.info("Number of CPU online changed, reset estimators")
                self.reset_estimation()
                # reload cpuinfo
                self._list_cpu = cpu_info()
                break
        self._cpu_online = cpu_online
        # Usage CPU
        # https://stackoverflow.com/questions/8952462/cpu-usage-from-a-file-on-linux
        # https://www.linuxhowtos.org/System/procstat.htm
        # https://stackoverflow.com/questions/9229333/how-to-get-overall-cpu-usage-e-g-57-on-linux
        total, cpu_list = self.get_utilization(cpu_list)
        return {'total': total, 'cpu': cpu_list}
# EOF
