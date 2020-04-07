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
# Logging
import logging
# Launch command
import subprocess as sp

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class JetsonClocks(object):
    """
        This controller manage the jetson_clocks service.
    """
    # CPU Cluster regex
    # CPU Cluster Switching: Disabled
    CPU_CLUSTER_REGEXP = re.compile(r'CPU Cluster Switching: ((.*))')
    # CPU regex
    # NANO: cpu0: Online=1 Governor=schedutil MinFreq=102000 MaxFreq=1428000 CurrentFreq=1428000 IdleStates: WFI=1 c7=1
    # Xavier: cpu0: Online=1 Governor=schedutil MinFreq=1190400 MaxFreq=2265600 CurrentFreq=1574400 IdleStates: C1=1 c6=1
    CPU_REGEXP = re.compile(r'cpu(.+?): Online=(.+?) Governor=(.+?) MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=(.+?) IdleStates: ((.*))')
    # GPU regex
    # GPU MinFreq=76800000 MaxFreq=921600000 CurrentFreq=384000000
    GPU_REGEXP = re.compile(r'GPU MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=((.*))')
    # EMC regex
    # EMC MinFreq=204000000 MaxFreq=1600000000 CurrentFreq=1600000000 FreqOverride=0
    EMC_REGEXP = re.compile(r'EMC MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=(.+?) FreqOverride=((.*))')

    class JCException(Exception):
        pass

    def __init__(self, config_file, service_name='jetson_performance'):
        # Config file
        self.config_file = config_file + "/l4t_dfs.conf"
        # Service
        self.service_name = service_name
        self.last_status = ""
        # Jetson Clocks path
        if os.path.isfile("/usr/bin/jetson_clocks"):
            self.jc_bin = "/usr/bin/jetson_clocks"
        elif os.path.isfile("/home/nvidia/jetson_clocks.sh"):
            self.jc_bin = "/home/nvidia/jetson_clocks.sh"
        else:
            raise JetsonClocks.JCException("No jetson_clock script is availble in this board")
        # Store configuration if does not exist
        self.store()

    def show(self):
        p = sp.Popen([self.jc_bin, '--show'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        # Decode lines
        lines = out.decode("utf-8")
        # Load lines
        status = {"cpu": {}}
        for line in lines.split("\n"):
            # Search configuration CPU config
            match = JetsonClocks.CPU_REGEXP.search(line)
            # if match extract name and number
            if match:
                # Load CPU information
                cpu = {"Online": True if int(match.group(2)) == 1 else False,
                       "Governor": str(match.group(3)),
                       "MinFreq": int(match.group(4)),
                       "MaxFreq": int(match.group(5)),
                       "CurrentFreq": int(match.group(6)),
                       "IdleStates": {str(state.split("=")[0]): int(state.split("=")[1]) for state in match.group(7).split()}}
                # Store in CPU list
                status["cpu"]["cpu{num}".format(num=match.group(1))] = cpu
                continue
            # Search configuration GPU config
            match = JetsonClocks.GPU_REGEXP.search(line)
            # Load GPU match
            if match:
                status["gpu"] = {"MinFreq": int(match.group(1)),
                                 "MaxFreq": int(match.group(2)),
                                 "CurrentFreq": int(match.group(3))}
                continue
            # Search configuration EMC config
            match = JetsonClocks.EMC_REGEXP.search(line)
            # Load EMC match
            if match:
                status["emc"] = {"MinFreq": int(match.group(1)),
                                 "MaxFreq": int(match.group(2)),
                                 "CurrentFreq": int(match.group(3)),
                                 "FreqOverride": int(match.group(4))}
                continue
            # Search configuration CPU Cluster config
            match = JetsonClocks.CPU_CLUSTER_REGEXP.search(line)
            # Load EMC match
            if match:
                status["cluster"] = str(match.group(1))
                continue
            # All other lines of jetson_clocks show are skipped
            # SOC family:tegra210  Machine:NVIDIA Jetson Nano Developer Kit
            # Online CPUs: 0-3
            # Fan: speed=0
            # NV Power Mode: MAXN
        return status

    @property
    def service(self):
        p = sp.Popen(['systemctl', 'is-active', self.service_name + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        return str(out.decode("utf-8")).strip()

    @property
    def status(self):
        # Load jetson_clocks show
        show = self.show()
        # Make statistics
        stat = []
        if 'cpu' in show:
            for cpu in show['cpu'].values():
                # Check status CPUs
                stat += [cpu['MaxFreq'] == cpu['MinFreq']]
                stat += [cpu['MaxFreq'] == cpu['CurrentFreq']]
        # Check status GPU
        if 'gpu' in show:
            gpu = show['gpu']
            stat += [gpu['MaxFreq'] == gpu['MinFreq']]
            stat += [gpu['MaxFreq'] == gpu['CurrentFreq']]
        # Don't need to check EMC frequency
        # Check status EMC
        # if 'emc' in show:
        #     emc = show['emc']
        #     stat += [emc['MaxFreq'] == emc['MinFreq']]
        #     stat += [emc['MaxFreq'] == emc['CurrentFreq']]
        if not stat:
            raise JetsonClocks.JCException("Require super user")
        return all(stat)

    @property
    def start(self):
        start_val = True if self.service == "active" else False
        return start_val

    @start.setter
    def start(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        # Do not run if jetson_clocks as already running
        if self.status and value:
            return
        # make service script
        start_val = "start" if value else "stop"
        p = sp.Popen(['systemctl', start_val, self.service_name + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        _, err = p.communicate()
        self.last_status = err.decode("utf-8")

    @property
    def enable(self):
        p = sp.Popen(['systemctl', 'is-enabled', self.service_name + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        enable_val = True if str(out.decode("utf-8")).strip() == "enabled" else False
        return enable_val

    @enable.setter
    def enable(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        enable_val = "enable" if value else "disable"
        p = sp.Popen(['systemctl', enable_val, self.service_name + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        _, err = p.communicate()
        self.last_status = err.decode("utf-8")

    def store(self):
        if not os.path.isfile(self.config_file):
            p = sp.Popen([self.jc_bin, '--store', self.config_file], stdout=sp.PIPE)
            out, _ = p.communicate()
            # Extract result
            if out.decode("utf-8"):
                return True
            else:
                return False
        else:
            return False

    def clear(self):
        if os.path.isfile(self.config_file):
            # Remove configuration file
            os.remove(self.config_file)
            return True
        else:
            return False

# EOF
