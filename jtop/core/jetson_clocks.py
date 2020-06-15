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
import time
# Logging
import logging
# Launch command
import subprocess as sp
from datetime import timedelta
from threading import Thread
# Get uptime
from .common import get_uptime
# Create logger for jplotlib
logger = logging.getLogger(__name__)

CONFIG_DEFAULT_BOOT = False
CONFIG_DEFAULT_DELAY = 60  # In seconds
CONFIG_DEFAULT_L4T_FILE = "l4t_dfs.conf"


def jetson_clocks_alive(show):
    # Make statistics
    stat = []
    if 'CPU' in show:
        for cpu in show['CPU'].values():
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


def locate_jetson_clocks():
    for f_fc in ['/usr/bin/jetson_clocks', '/home/nvidia/jetson_clocks.sh']:
        if os.path.isfile(f_fc):
            logger.info("Load jetson_clocks {}".format(f_fc))
            return f_fc
    raise JetsonClocks.JCException("Tegrastats is not availabe on this board")


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

    def __init__(self, path, config):
        # Load configuration
        self.config = config.get('jetson_clocks', {})
        jetson_clocks_file = self.config.get('l4t_file', CONFIG_DEFAULT_L4T_FILE)
        # Config file
        self.config_l4t = path + "/" + jetson_clocks_file
        # Jetson Clocks path
        self.jc_bin = locate_jetson_clocks()
        # Check if running a root
        if os.getuid() != 0:
            raise JetsonClocks.JCException("Need sudo")

    def _jetson_clocks_boot(self, boot_time):
        # Measure remaining time from boot
        boot_time = timedelta(seconds=boot_time)
        up_time = timedelta(seconds=get_uptime())
        # If needtime make a sleep
        if up_time < boot_time:
            delta = (boot_time - up_time).total_seconds()
            logger.info("Starting jetson_clocks in: {delta}s".format(delta=delta))
            time.sleep(delta)
        # Start jetson_clocks
        self.start()
        logger.info("jetson_clocks running")

    def initialization(self):
        # Load jetson_clocks start up information
        jetson_clocks_boot = self.config.get('boot', CONFIG_DEFAULT_BOOT)
        jetson_clocks_start = self.config.get('wait', CONFIG_DEFAULT_DELAY)
        # Check if exist configuration file
        if not os.path.isfile(self.config_l4t):
            if self.is_alive:
                logger.warning("I can't store jetson_clocks is already running")
            else:
                logger.info("Store jetson_clocks configuration in {file}".format(file=self.config_l4t))
                self.store()
        # Check which version is L4T is loaded
        # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
        # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
        # Temporary disabled to find a best way to start this service.
        # The service ondemand disabled doesn't improve the performance of the start-up
        # If jetson_clocks on boot run a thread
        if jetson_clocks_boot and not self.is_alive:
            # Start thread Service client
            self._thread = Thread(target=self._jetson_clocks_boot, args=[jetson_clocks_start])
            self._thread.start()

    def show(self):
        p = sp.Popen([self.jc_bin, '--show'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        # Decode lines
        lines = out.decode("utf-8")
        # Load lines
        status = {"CPU": {}}
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
                status["CPU"]["CPU{num}".format(num=match.group(1))] = cpu
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
    def is_alive(self):
        # Load status jetson_clocks
        show = self.show()
        # Make statistics
        return jetson_clocks_alive(show)

    def start(self):
        # Run jetson_clocks
        p = sp.Popen([self.jc_bin], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        # Extract result
        message = out.decode("utf-8")
        if message:
            raise JetsonClocks.JCException("Error to start jetson_clocks: {message}".format(message=message))
        return True

    def stop(self):
        # Run jetson_clocks
        p = sp.Popen([self.jc_bin, '--restore', self.config_l4t], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        # Extract result
        message = out.decode("utf-8")
        if message:
            raise JetsonClocks.JCException("Error to start jetson_clocks: {message}".format(message=message))
        return True

    def store(self):
        # Store configuration jetson_clocks
        p = sp.Popen([self.jc_bin, '--store', self.config_l4t], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = p.communicate()
        # Extract result
        if out.decode("utf-8"):
            return True
        else:
            return False

    def clear(self):
        if os.path.isfile(self.config_l4t):
            # Remove configuration file
            os.remove(self.config_l4t)
            return True
        else:
            return False
# EOF
