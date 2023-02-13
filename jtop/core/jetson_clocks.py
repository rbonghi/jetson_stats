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

import re
import os
import time
import logging
# Launch command
from datetime import timedelta
from threading import Thread, Event
# Local functions and classes
from .command import Command
from .common import get_uptime, locate_commands
# Create logger
logger = logging.getLogger(__name__)

PATH_JETSON_CLOCKS = ['/usr/bin/jetson_clocks', '/home/nvidia/jetson_clocks.sh']
COMMAND_TIMEOUT = 3.0
CONFIG_DEFAULT_BOOT = False
CONFIG_DEFAULT_DELAY = 60  # In seconds
CONFIG_DEFAULT_L4T_FILE = "l4t_dfs.conf"
JC_MIN_SLEEP = 0.05

# CPU Cluster regex
# CPU Cluster Switching: Disabled
CPU_CLUSTER_REGEXP = re.compile(r'CPU Cluster Switching: ((.*))')
# CPU regex
# NANO: cpu0: Online=1 Governor=schedutil MinFreq=102000 MaxFreq=1428000 CurrentFreq=1428000 IdleStates: WFI=1 c7=1
# Xavier: cpu0: Online=1 Governor=schedutil MinFreq=1190400 MaxFreq=2265600 CurrentFreq=1574400 IdleStates: C1=1 c6=1
# cpu0: Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=1510400 IdleStates: (Fixed insidious bug)
CPU_REGEXP = re.compile(r'cpu(.+?): Online=(.+?) Governor=(.+?) MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=(.+?) IdleStates:((.*))')
# TX1 cpu0: Gonvernor=interactive MinFreq=102000 MaxFreq=1734000 CurrentFreq=510000
CPUTX1_REGEXP = re.compile(r'cpu(.+?): Gonvernor=(.+?) MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=((.*))')
# GPU regex
# GPU MinFreq=76800000 MaxFreq=921600000 CurrentFreq=384000000
GPU_REGEXP = re.compile(r'GPU MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=((.*))')
# EMC regex
# EMC MinFreq=204000000 MaxFreq=1600000000 CurrentFreq=1600000000 FreqOverride=0
EMC_REGEXP = re.compile(r'EMC MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=(.+?) FreqOverride=((.*))')
# DLA regex
# DLA0_CORE MinFreq=0 MaxFreq=1600000000 CurrentFreq=1600000000
# DLA0_FALCON MinFreq=0 MaxFreq=844800000 CurrentFreq=844800000
# DLA1_CORE MinFreq=0 MaxFreq=1600000000 CurrentFreq=1600000000
# DLA1_FALCON MinFreq=0 MaxFreq=844800000 CurrentFreq=844800000
DLA_REGEXP = re.compile(r'DLA(.+?)_(.+?) MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=((.*))')
# PVA regex
# PVA0_VPS0 MinFreq=0 MaxFreq=1152000000 CurrentFreq=1152000000
# PVA0_AXI MinFreq=0 MaxFreq=832000000 CurrentFreq=832000000
PVA_REGEXP = re.compile(r'PVA(.+?)_(.+?) MinFreq=(.+?) MaxFreq=(.+?) CurrentFreq=((.*))')
# NVP Model
# NV Power Mode: MAXN
NVP_REGEXP = re.compile(r'NV Power Mode: ((.*))')
# Type Engine
JC_ENGINES = re.compile(r'^(?P<name>[^ ]+) .* MaxFreq=(?P<frq>[^ ]+) .*')


def decode_show_message(lines):
    status = {}
    for line in lines:
        # Search configuration CPU config
        match = JC_ENGINES.search(line)
        if match:
            parsed_line = match.groupdict()
            # Extract name
            name = 'CPU' if 'cpu' in parsed_line['name'] else parsed_line['name']
            # Extrac max frequency
            freq = int(parsed_line['frq'])
            # add engine
            status[name] = freq
    return status


def _decode_show_message(lines):
    # Load lines
    status = {"CPU": {}}
    for line in lines:
        # Search configuration CPU config
        match = CPU_REGEXP.search(line)
        # if match extract name and number
        if match:
            # Load CPU information
            cpu = {
                "Online": int(match.group(2)) == 1,
                "governor": str(match.group(3)),
                "min_freq": int(match.group(4)),
                "max_freq": int(match.group(5)),
                "current_freq": int(match.group(6)),
                "IdleStates": {str(state.split("=")[0]): int(state.split("=")[1]) for state in match.group(7).strip().split()}
            }
            # Store in CPU list
            idx_cpu = int(match.group(1)) + 1
            status["CPU"][idx_cpu] = cpu
            continue
        # Search CPU for TX1
        match = CPUTX1_REGEXP.search(line)
        # if match extract name and number
        if match:
            # Load CPU information
            cpu = {
                "governor": str(match.group(2)),
                "min_freq": int(match.group(3)),
                "max_freq": int(match.group(4)),
                "current_freq": int(match.group(5))}
            # Store in CPU list
            idx_cpu = int(match.group(1)) + 1
            status["CPU"][idx_cpu] = cpu
            continue
        # Search configuration GPU config
        match = GPU_REGEXP.search(line)
        # Load GPU match
        if match:
            status["GPU"] = {
                "min_freq": int(match.group(1)),
                "max_freq": int(match.group(2)),
                "current_freq": int(match.group(3))}
            continue
        # Search configuration EMC config
        match = EMC_REGEXP.search(line)
        # Load EMC match
        if match:
            status["EMC"] = {
                "min_freq": int(match.group(1)),
                "max_freq": int(match.group(2)),
                "current_freq": int(match.group(3)),
                "FreqOverride": int(match.group(4))}
            continue
        # Search configuration DLA config
        match = DLA_REGEXP.search(line)
        # Load DLA match
        if match:
            if "DLA" not in status:
                status["DLA"] = {}
            dla_number = int(match.group(1))
            if dla_number not in status["DLA"]:
                status["DLA"][dla_number] = {}
            dla_type = str(match.group(2)).lower()
            status["DLA"][dla_number][dla_type] = {
                "min_freq": int(match.group(3)) // 1000000,
                "max_freq": int(match.group(4)) // 1000000,
                "current_freq": int(match.group(5)) // 1000000}
        # Search configuration PVA config
        match = PVA_REGEXP.search(line)
        # Load PVA match
        if match:
            if "PVA" not in status:
                status["PVA"] = {}
            pva_number = int(match.group(1))
            if pva_number not in status["PVA"]:
                status["PVA"][pva_number] = {}
            pva_type = str(match.group(2)).lower()
            status["PVA"][pva_number][pva_type] = {
                "min_freq": int(match.group(3)) // 1000000,
                "max_freq": int(match.group(4)) // 1000000,
                "current_freq": int(match.group(5)) // 1000000}
        # Search configuration NV Power Model
        match = NVP_REGEXP.search(line)
        # Load NV Power Model
        if match:
            status["NVP"] = str(match.group(1))
            continue
        # Search configuration CPU Cluster config
        match = CPU_CLUSTER_REGEXP.search(line)
        # Load EMC match
        if match:
            status["cluster"] = str(match.group(1))
            continue
        # All other lines of jetson_clocks show are skipped
        # SOC family:tegra210  Machine:NVIDIA Jetson Nano Developer Kit
        # Online CPUs: 0-3
        # Fan: speed=0
    return status


def jetson_clocks_alive(engines, data):
    for engine, frq in engines.items():
        if engine == 'CPU':
            # Check minum and max frequency
            for cpu in data['cpu']['cpu']:
                cpu_frqs = cpu['freq']
                if not all([cpu_frqs['max'] == frq, cpu_frqs['min'] == frq]):
                    return False
        elif engine == 'GPU':
            # Check minum and max frequency
            for gpu in data['gpu']:
                gpu_freqs = gpu['freq']
                if not all([gpu_freqs['max'] == frq // 1000, gpu_freqs['min'] == frq // 1000]):
                    return False
        elif engine == 'EMC':
            # Check minum and max frequency
            # EMC check only if current frequency is the same of max
            emc = data['mem']['EMC']
            if not all([emc['max'] == frq // 1000, emc['cur'] == frq // 1000]):
                return False
        else:
            # Find enging and check frequencies
            for _, engines_group in data['engines'].items():
                for name, engine_data in engines_group.items():
                    if engine == name:
                        # for all Engines check only if current frequency is the same of max
                        if not all([engine_data['max'] == frq // 1000, engine_data['cur'] == frq // 1000]):
                            return False
    return True


class JetsonClocks(object):
    """
        Reference:
        - https://docs.python.org/2.7/reference/datamodel.html
    """

    def __init__(self, controller):
        self._alive = False
        self._boot = False
        self._thread = ''
        self._controller = controller

    @property
    def status(self):
        # Check if is alive jetson_clocks
        if self.is_alive:
            return 'running'
        # Otherwise check status thread jetson_clocks
        return self._thread

    @property
    def is_config(self):
        return self._config

    @property
    def boot(self):
        return self._boot

    @boot.setter
    def boot(self, value):
        if not isinstance(value, bool):
            raise ValueError("Use a boolean")
        # Don't send a message if value is the same
        if value == self._boot:
            return
        # Set new jetson_clocks configuration
        self._controller.put({'jc': {'boot': value}})

    @property
    def is_alive(self):
        return self._alive

    def __nonzero__(self):
        return self._alive

    def __bool__(self):
        return self._alive

    def __repr__(self):
        return str(self._alive)

    def _update(self, jc_status):
        self._config = jc_status['config']
        self._alive = jc_status['status']
        self._boot = jc_status['boot']
        self._thread = jc_status['thread']


class JetsonClocksService(object):
    """
        This controller manage the jetson_clocks service.
    """

    set_status = 'inactive'

    def __init__(self, config, fan):
        # Thread event show
        self.event_show = Event()
        # Thread event jetson_clocks set
        self._set_jc = None
        # nvpmodel
        self.nvpmodel = None
        # Load configuration
        self._config = config
        jetson_clocks_file = config.get('jetson_clocks', {}).get('l4t_file', CONFIG_DEFAULT_L4T_FILE)
        # Config file
        self.config_l4t = config.path + "/" + jetson_clocks_file
        # Error message
        self._error = None
        # Fan configuration
        self.fan = fan
        # Jetson Clocks path
        self._jc_bin = locate_commands("jetson_clocks", PATH_JETSON_CLOCKS)
        if not self._jc_bin:
            logger.warning("jetson_clocks not available")
            return
        logger.info("jetson_clocks found in {cmd}".format(cmd=self._jc_bin))
        # List of all engines required
        self._engines_list = self.show()

    def exists(self):
        return True if self._jc_bin else False

    def initialization(self, nvpmodel):
        if not self.exists():
            return
        self.nvpmodel = nvpmodel
        # Check if exist configuration file
        if not os.path.isfile(self.config_l4t):
            if self.alive(wait=False):
                logger.warning("I can't store jetson_clocks is already running")
            else:
                self.store()
        # Check which version is L4T is loaded
        # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
        # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
        # Temporary disabled to find a best way to start this service.
        # The service on demand disabled doesn't improve the performance of the start-up
        # If jetson_clocks on boot run a thread
        config = self._config.get('jetson_clocks', {})
        if config.get('boot', CONFIG_DEFAULT_BOOT):
            logger.info("Starting jetson_clocks on boot")
            # Start thread Service client
            self._set_jc = Thread(target=self._th_start, args=(False, ))
            self._set_jc.start()

    def get_status(self, data):
        # Get status jetson_clocks
        status = {
            'status': self.alive(data, wait=False),
            'thread': self.is_running(),
            'config': self.is_config(),
            'boot': self.boot,
        }
        return status

    def _fix_fan(self, speed, status):
        logger.debug("fan mode: {mode}".format(mode=self.fan.mode))
        # Configure fan
        if self.fan.mode == 'system':
            # Read status
            if self.fan.is_speed():
                self.fan.set_speed(speed)
            # Set mode
            self.fan.auto = True
        elif self.fan.mode == 'manual':
            # Read status
            if self.fan.is_speed():
                self.fan.set_speed(speed)
            # Set mode
            self.fan.auto = False
        elif self.fan.mode == 'default':
            self.fan.set_mode('default', status)

    def _th_start(self, reset):
        JetsonClocksService.set_status = 'activating'
        # Check which version is L4T is loaded
        # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
        # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
        # Temporary disabled to find a best way to start this service.
        # The service on demand disabled doesn't improve the performance of the start-up
        # Measure remaining time from boot
        boot_time = timedelta(seconds=self._config.get('wait', CONFIG_DEFAULT_DELAY))
        up_time = timedelta(seconds=get_uptime())
        # If need time make a sleep
        if up_time < boot_time:
            JetsonClocksService.set_status = 'booting'
            delta = (boot_time - up_time).total_seconds()
            logger.info("Starting jetson_clocks in: {delta}s".format(delta=delta))
        # Status jetson_clocks
        logger.info("Start jetson_clocks with {status}".format(status=JetsonClocksService.set_status))
        if up_time < boot_time:
            time.sleep(delta)
        # Read fan speed
        # speed = self.fan.speed if self.fan.is_speed() else 0
        # Start jetson_clocks
        Command.run_command([self._jc_bin], repeat=5, timeout=COMMAND_TIMEOUT)
        # Fix fan speed
        # ----------------------------------------------- self._fix_fan(speed, True)
        # Reset nvpmodel
        if reset and self.nvpmodel is not None:
            self.nvpmodel.reset()
        logger.info("jetson_clocks started")

    def _th_stop(self, reset):
        JetsonClocksService.set_status = 'deactivating'
        logger.debug("Start jetson_clocks with {status}".format(status=JetsonClocksService.set_status))
        # Read fan speed
        # speed = self.fan.speed if self.fan.is_speed() else 0
        # Run jetson_clocks
        Command.run_command([self._jc_bin, '--restore', self.config_l4t], repeat=5, timeout=COMMAND_TIMEOUT)
        # Fix fan speed
        # ----------------------------------------------- self._fix_fan(speed, False)
        # Reset nvpmodel
        if reset and self.nvpmodel is not None:
            self.nvpmodel.reset()
        logger.info("jetson_clocks stopped")

    def is_running(self):
        if self._set_jc is not None:
            if not self._set_jc.is_alive():
                JetsonClocksService.set_status = 'inactive'
        return JetsonClocksService.set_status

    def set(self, status, reset=False):
        # If there are exception raise
        self._error_status()
        # Check status jetson_clocks
        running_status = self.is_running()
        if running_status != 'inactive':
            logger.warning("jetson_clocks is {status}".format(status=running_status))
            return False
        # logger.debug("Set jetson_clocks {status}".format(status=status))
        if status:
            # Start thread Service client
            self._set_jc = Thread(target=self._th_start, args=(reset, ))
            self._set_jc.start()
        else:
            reset = False
            # Start thread Service client
            self._set_jc = Thread(target=self._th_stop, args=(reset, ))
            self._set_jc.start()
        return True

    @property
    def boot(self):
        config = self._config.get('jetson_clocks', {})
        return config.get('boot', CONFIG_DEFAULT_BOOT)

    @boot.setter
    def boot(self, value):
        if not isinstance(value, bool):
            raise ValueError("Use a boolean")
        # Extract configuration
        config = self._config.get('jetson_clocks', {})
        # Add new value
        config['boot'] = value
        # Set new jetson_clocks configuration
        self._config.set('jetson_clocks', config)

    def alive(self, data, wait=True):
        if wait and not self.event_show.is_set():
            logger.info("Wait from jetson_clocks show")
            if not self.event_show.wait(timeout=COMMAND_TIMEOUT):
                logger.error("Lost connection from jtop")
                return False
        self.event_show.clear()
        # Return status jetson_clocks
        return jetson_clocks_alive(self._engines_list, data)

    def show(self):
        cmd = Command([self._jc_bin, '--show'])
        list_engines = {}
        try:
            lines = cmd(timeout=COMMAND_TIMEOUT)
            list_engines = decode_show_message(lines)
        except Command.TimeoutException as e:
            logger.warning("Timeout {}".format(e))
        return list_engines

    def close(self):
        # Switch off thread jetson clocks
        self._running = False
        if self._thread.is_alive():
            logger.warning("Wait switch off set jetson_clocks --show")
            self._thread.join(COMMAND_TIMEOUT)
        if self._set_jc is not None:
            if self._set_jc.is_alive():
                logger.warning("Wait switch off set jetson_clocks")
                self._set_jc.join(COMMAND_TIMEOUT)

    def _error_status(self):
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value

    def is_config(self):
        return os.path.isfile(self.config_l4t)

    def store(self):
        # Store configuration jetson_clocks
        cmd = Command([self.jc_bin, '--store', self.config_l4t])
        try:
            message = cmd(timeout=COMMAND_TIMEOUT)
        except Command.CommandException:
            return False
        logger.info("Store jetson_clocks configuration in {file}".format(file=self.config_l4t))
        # Extract result
        return True if message else False

    def clear(self):
        if os.path.isfile(self.config_l4t):
            logger.info("Clear jetson_clocks config in {path}".format(path=self.config_l4t))
            # Remove configuration file
            os.remove(self.config_l4t)
            return True
        return False
# EOF
