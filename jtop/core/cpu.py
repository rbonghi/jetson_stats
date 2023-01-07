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
REGEXP = re.compile(r'(.+?): ((.*))')
CPU_REG = re.compile(r'cpu[0-9]')
CPU_STATE_REG = re.compile(r'state[0-9]')


def cpu_info():
    list_cpu = {}
    with open("/proc/cpuinfo", "r") as fp:
        for line in fp:
            # Search line
            match = REGEXP.search(line)
            if match:
                key = match.group(1).rstrip()
                value = match.group(2).rstrip()
                # Load value or if it is a new processor initialize a new field
                if key == "processor":
                    idx = int(value) + 1
                    # name = "CPU{idx}".format(idx=idx)
                    list_cpu[idx] = {}
                else:
                    # Load cpu info
                    list_cpu[idx][key] = value
    return list_cpu


def cpu_models():
    # Load cpuinfo
    list_cpu = cpu_info()
    models = {}
    # Find all models
    for name, info in list_cpu.items():
        models[name] = info.get("model name", "")
    return models


def read_idle(path):
    # https://docs.kernel.org/admin-guide/pm/cpuidle.html
    states = [item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item)) and CPU_STATE_REG.search(item)]
    idle = {}
    for state in sorted(states):
        with open("{path}/{state}/name".format(path=path, state=state), 'r') as f:
            name = f.read().strip()
        with open("{path}/{state}/disable".format(path=path, state=state), 'r') as f:
            disable = int(f.read())
        idle[name] = disable
    return idle


def read_sys_cpu(path, cpu_status={}):
    # Online status
    if os.path.isfile(path + "/online"):
        with open(path + "/online", 'r') as f:
            cpu_status['online'] = f.read().strip()
    # Read governor
    with open(path + "/cpufreq/scaling_governor", 'r') as f:
        cpu_status['governor'] = f.read().strip()
    # Min frequency
    with open(path + "/cpufreq/scaling_min_freq", 'r') as f:
        cpu_status['min'] = int(f.read())
    # Max frequency
    with open(path + "/cpufreq/scaling_max_freq", 'r') as f:
        cpu_status['max'] = int(f.read())
    # Current frequency
    with open(path + "/cpufreq/scaling_cur_freq", 'r') as f:
        cpu_status['cur'] = int(f.read())
    # Read idle CPU
    cpu_status['idle_state'] = read_idle(path + "/cpuidle")
    return cpu_status


class CPUService(object):

    def __init__(self, path):
        # List all CPU available
        self._cpu = {int(item[3:]): "{path}/{item}".format(path=path, item=item)
                     for item in os.listdir(path) if os.path.isdir(os.path.join(path, item)) and CPU_REG.search(item)}
        # TEST
        self.get_status()

    def get_status(self):
        status = {}
        # Read status CPU
        for cpu, path in sorted(self._cpu.items()):
            # Usage CPU
            # https://stackoverflow.com/questions/8952462/cpu-usage-from-a-file-on-linux
            # https://stackoverflow.com/questions/9229333/how-to-get-overall-cpu-usage-e-g-57-on-linux
            # https://www.linuxhowtos.org/System/procstat.htm
            # https://stackoverflow.com/questions/9229333/how-to-get-overall-cpu-usage-e-g-57-on-linux
            # TODO
            # frequency and status
            cpu_status = read_sys_cpu(path)
            print(cpu_status)
            status[cpu] = cpu_status
        return status
# EOF
