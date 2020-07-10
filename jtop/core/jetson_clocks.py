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
import logging
import sys
# Launch command
from datetime import timedelta
from threading import Thread
# Local functions and classes
from .command import Command
from .common import get_uptime, locate_commands
# Import exceptions
from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 3.0
CONFIG_DEFAULT_BOOT = False
CONFIG_DEFAULT_DELAY = 60  # In seconds
CONFIG_DEFAULT_L4T_FILE = "l4t_dfs.conf"

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
# NVP Model
# NV Power Mode: MAXN
NVP_REGEXP = re.compile(r'NV Power Mode: ((.*))')


def decode_show_message(lines):
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
                "IdleStates": {str(state.split("=")[0]): int(state.split("=")[1]) for state in match.group(7).split()}}
            # Store in CPU list
            idx_cpu = int(match.group(1)) + 1
            status["CPU"]["CPU{num}".format(num=idx_cpu)] = cpu
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


def jetson_clocks_alive(show):
    # Make statistics
    stat = []
    if 'CPU' in show:
        for cpu in show['CPU'].values():
            # Check status CPU
            stat += [cpu['max_freq'] == cpu['min_freq']]
            stat += [cpu['max_freq'] == cpu['current_freq']]
    # Check status GPU
    if 'GPU' in show:
        gpu = show['GPU']
        stat += [gpu['max_freq'] == gpu['min_freq']]
        stat += [gpu['max_freq'] == gpu['current_freq']]
    # Don't need to check EMC frequency
    # Check status EMC
    # if 'EMC' in show:
    #     emc = show['EMC']
    #     stat += [emc['max_freq'] == emc['min_freq']]
    #     stat += [emc['max_freq'] == emc['current_freq']]
    return all(stat)


def run_command(cmd, repeat=5):
    for idx in range(repeat):
        try:
            message = cmd(timeout=COMMAND_TIMEOUT)
            return True, message
        except Command.TimeoutException as error:
            logger.error("[{idx}] {error}".format(idx=idx, error=error))
    return False, ''


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

    def __init__(self, config, fan, jetson_clocks_path):
        self._thread_start = None
        self._thread_stop = None
        self._thread_show = None
        self._error = None
        self._show = {}
        self._thread_show_running = False
        # nvpmodel
        self.nvpmodel = None
        # Load configuration
        self._config = config
        jetson_clocks_file = config.get('jetson_clocks', {}).get('l4t_file', CONFIG_DEFAULT_L4T_FILE)
        # Config file
        self.config_l4t = config.path + "/" + jetson_clocks_file
        # Jetson Clocks path
        self.jc_bin = locate_commands("jetson_clocks", jetson_clocks_path)
        # Fan configuration
        self.fan = fan
        # Update status jetson_clocks
        cmd = Command([self.jc_bin, '--show'])
        lines = cmd(timeout=COMMAND_TIMEOUT)
        self._show = decode_show_message(lines)

    def set_nvpmodel(self, nvpmodel):
        self.nvpmodel = nvpmodel

    def initialization(self):
        status = True
        # Check if exist configuration file
        if not os.path.isfile(self.config_l4t):
            if self.is_alive:
                logger.warning("I can't store jetson_clocks is already running")
                status = False
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
            # Start thread Service client
            self.start()
        return status

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

    def show(self):
        return self._show

    def _thread_jetson_clocks_loop(self):
        cmd = Command([self.jc_bin, '--show'])
        try:
            while self._thread_show_running:
                try:
                    lines = cmd(timeout=COMMAND_TIMEOUT)
                    self._show = decode_show_message(lines)
                except Command.TimeoutException as e:
                    logger.warning("Timeout {}".format(e))
        except Exception as e:
            logger.error("Exception jetson_clocks_show {}".format(e))
            # Store error message
            self._error = sys.exc_info()
        # Reset running boolean
        self._thread_show_running = False

    def show_running(self):
        if self._thread_show is None:
            return False
        return self._thread_show.isAlive()

    def show_start(self):
        # If there are exception raise
        self._error_status()
        # Check if thread show is running or not
        if not self.show_running():
            self._thread_show_running = True
            # Start thread Service client
            self._thread_show = Thread(target=self._thread_jetson_clocks_loop)
            self._thread_show.start()
            return True
        return False

    def show_stop(self):
        # If there are exception raise
        self._error_status()
        # Check if thread show is running or not
        if self.show_running():
            # Stop service
            self._thread_show_running = False
        return True

    @property
    def is_alive(self):
        # Make statistics
        return jetson_clocks_alive(self._show)

    @property
    def is_running(self):
        # Check status thread
        if self._thread_start is not None:
            if self._thread_start.isAlive():
                return 'activating'
        if self._thread_stop is not None:
            if self._thread_stop.isAlive():
                return 'deactivating'
        return 'inactive'

    def _fix_fan(self, speed):
        logger.info("fan mode: {mode} - speed {speed}".format(mode=self.fan.mode, speed=self.fan.speed))
        # Configure fan
        if self.fan.mode == 'system':
            # Read status
            if self.fan.is_speed:
                self.fan.speed = speed
            # Set mode
            self.fan.auto = True
        elif self.fan.mode == 'manual':
            # Read status
            if self.fan.is_speed:
                self.fan.speed = speed
            # Set mode
            self.fan.auto = False
        elif self.fan.mode == 'default':
            self.fan.mode = 'default'

    def _jetson_clocks_boot(self, boot_time, reset):
        # Measure remaining time from boot
        boot_time = timedelta(seconds=boot_time)
        up_time = timedelta(seconds=get_uptime())
        # If needtime make a sleep
        if up_time < boot_time:
            delta = (boot_time - up_time).total_seconds()
            logger.info("Starting jetson_clocks in: {delta}s".format(delta=delta))
            time.sleep(delta)
        try:
            if self.fan is not None:
                if self.fan.is_speed:
                    speed = self.fan.speed
                else:
                    speed = 0
            # Start jetson_clocks
            cmd = Command([self.jc_bin])
            status, message = run_command(cmd, repeat=5)
            if not status:
                raise JtopException("Error to start jetson_clocks: {message}".format(message=message))
            # Check if jetson_clocks is running
            while not self.is_alive:
                pass
            # Fix fan speed
            if self.fan is not None:
                self._fix_fan(speed)
            # Reset nvpmodel
            if reset and self.nvpmodel is not None:
                self.nvpmodel.reset()
        except Exception:
            # Store error message
            self._error = sys.exc_info()

    def start(self, reset=False):
        # If there are exception raise
        self._error_status()
        # Check which version is L4T is loaded
        # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
        # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
        # Temporary disabled to find a best way to start this service.
        # The service on demand disabled doesn't improve the performance of the start-up
        # If jetson_clocks on boot run a thread
        if self.is_alive:
            return True
        # Check if restore config exist
        if not self.is_config():
            self.store()
        if self.is_running == 'inactive':
            # Load jetson_clocks start up information
            jetson_clocks_start = self._config.get('wait', CONFIG_DEFAULT_DELAY)
            # Start thread Service client
            self._thread_start = Thread(target=self._jetson_clocks_boot, args=(jetson_clocks_start, reset, ))
            # self._thread_start.daemon = True
            self._thread_start.start()
            return True
        return False

    def _thread_jetson_clocks_stop(self, reset):
        try:
            # Read fan speed
            if self.fan is not None:
                if self.fan.is_speed:
                    speed = self.fan.speed
                else:
                    speed = 0
            # Run jetson_clocks
            cmd = Command([self.jc_bin, '--restore', self.config_l4t])
            status, message = run_command(cmd, repeat=5)
            if not status:
                raise JtopException("Error to start jetson_clocks: {message}".format(message=message))
            # Check if jetson_clocks is running
            while self.is_alive:
                pass
            # Fix fan speed
            if self.fan is not None:
                self._fix_fan(speed)
            # Reset nvpmodel
            if reset and self.nvpmodel is not None:
                self.nvpmodel.reset()
        except Exception:
            # Store error message
            self._error = sys.exc_info()

    def stop(self, reset=False):
        # If there are exception raise
        self._error_status()
        # Check if restore config exist
        if not self.is_config():
            return False
        # Check if jetson_clocks is already running
        if not self.is_alive:
            return True
        if self.is_running == 'inactive':
            # Start thread Service client
            self._thread_stop = Thread(target=self._thread_jetson_clocks_stop, args=(reset, ))
            # self._thread_stop.daemon = True
            self._thread_stop.start()
            return True
        return False

    def _error_status(self):
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value

    def close(self):
        # Check start jetson_clocks
        if self._thread_start is not None:
            if self._thread_start.isAlive():
                self._thread_start.join()
        # Check stop jetson_clocks
        if self._thread_stop is not None:
            if self._thread_stop.isAlive():
                self._thread_stop.join()
        # Close show
        if self._thread_show is not None:
            self.show_stop()
            if self._thread_show.isAlive():
                self._thread_show.join()

    def is_config(self):
        return os.path.isfile(self.config_l4t)

    def store(self):
        # Store configuration jetson_clocks
        cmd = Command([self.jc_bin, '--store', self.config_l4t])
        try:
            message = cmd(timeout=COMMAND_TIMEOUT)
        except Command.TimeoutException:
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
