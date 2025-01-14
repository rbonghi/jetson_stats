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
from threading import Thread
# Local functions and classes
from .command import Command
from .common import get_uptime
from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)

PATH_JETSON_CLOCKS = ['/usr/bin/jetson_clocks', '/home/nvidia/jetson_clocks.sh']
COMMAND_TIMEOUT = 3.0
CONFIG_DEFAULT_BOOT = False
CONFIG_DEFAULT_DELAY = 60  # In seconds
CONFIG_DEFAULT_L4T_FILE = "l4t_dfs.conf"
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


def jetson_clocks_alive(engines, data):
    for engine in engines:
        if engine == 'CPU':
            # Check minum and max frequency
            for cpu in data['cpu']['cpu']:
                if not cpu['online']:
                    continue
                cpu_frqs = cpu['freq']
                if cpu_frqs['max'] != cpu_frqs['min']:
                    return False
        elif engine == 'GPU':
            # Check minum and max frequency
            for _, gpu in data['gpu'].items():
                gpu_freqs = gpu['freq']
                if gpu_freqs['max'] != gpu_freqs['min']:
                    return False
        elif engine == 'EMC':
            # Check minum and max frequency
            # EMC check only if current frequency is the same of max
            emc = data['mem']['EMC']
            if 'max' not in emc:
                continue
            if emc['max'] != emc['cur']:
                return False
        else:
            # Find enging and check frequencies
            for _, engines_group in data['engines'].items():
                for name, engine_data in engines_group.items():
                    if engine == name and 'max' in engine_data:
                        # for all Engines check only if current frequency is the same of max
                        if engine_data['max'] != engine_data['cur']:
                            return False
    return True


class JetsonClocks(object):
    """
    jetson_clocks is a tool provided for all NVIDIA Jetson to maximize all performance, read reference for more information.

    With this class you can control when activate, deactivate or enable on boot.
    You can use in a simple way like a jtop attribute :py:attr:`~jtop.jtop.jetson_clocks`

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                # Change status jetson_clocks
                jetson.jetson_clocks = not jetson.jetson_clocks
                # Set on board boot
                jetson.jetson_clocks.boot = True
                # Read status jetson_clocks service
                print(jetson.jetson_clocks.status)

    .. admonition:: Reference

        #. `jetson_clocks - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/index.html#page/Tegra%2520Linux%2520Driver%2520Package%2520Development%2520Guide%2Fpower_management_tx2.html%23>`_
        #. `jetson_clocks - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html>`_
        #. `jetson_clocks - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#maximizing-jetson-orin-performance>`_

    """  # noqa

    def __init__(self, controller):
        self._controller = controller
        self._enable = False
        self._thread = ''
        self._boot = False
        self._config = False

    def _update(self, jc_status):
        self._enable = jc_status['enable']
        self._thread = jc_status['thread']
        self._config = jc_status['config']
        self._boot = jc_status['boot']

    def set_enable(self, enable):
        """
        Enable jetson_clocks on your board. This method is equivalent to:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Set a new state for jetson_clocks
                    jetson.jetson_clocks.set_enable(True)
                    # same of
                    jetson.jetson_clocks = True

        :param enable: Boolean status for enable and disable
        :type enable: bool
        :raises ValueError: if enable is not a boolean
        :raises JtopException: if jetson_clocks is in uncontrolled status
        """
        if not isinstance(enable, bool):
            raise ValueError("Use a boolean")
        if not self._config and not enable:
            raise JtopException("I cannot set jetson_clocks.\nPlease shutdown manually jetson_clocks")
        # Check if service is not started otherwise skip
        if self._thread in ['booting', 'activating', 'deactivating', 'uncontrolled']:
            return
        # Set new jetson_clocks configuration
        if enable is not self._enable:
            self._controller.put({'jc': {'enable': enable}})

    def get_enable(self):
        """
        Return current jetson_clocks status. This method is equivalent to:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read jetson_clocks status
                    print(jetson.jetson_clocks.get_enable())
                    # same of
                    print(jetson.jetson_clocks)

        :return: Status jetson_clocks
        :rtype: bool
        """
        return self._enable

    def set_boot(self, value):
        """
        Enable jetson_clocks on board boot. This method is equivalent to:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Set a new state for jetson_clocks
                    jetson.jetson_clocks.set_boot(True)
                    # same of
                    jetson.jetson_clocks.boot = True

        :param value: Boolean status for enable and disable jetson_clocks on boot
        :type value: bool
        :raises ValueError: if value is not a boolean
        """
        if not isinstance(value, bool):
            raise ValueError("Use a boolean")
        # Don't send a message if value is the same
        if value is self._boot:
            return
        # Set new jetson_clocks configuration
        self._controller.put({'jc': {'boot': value}})

    def get_boot(self):
        """
        Return if jetson_clocks start of board boot. This method is equivalent to:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read jetson_clocks status
                    print(jetson.jetson_clocks.get_boot())
                    # same of
                    print(jetson.jetson_clocks.boot)

        :return: Status jetson_clocks on boot
        :rtype: bool
        """
        return self._boot

    @property
    def boot(self):
        """
        Same of :py:class:`~set_boot` and :py:class:`~get_boot` you can quickly enable and disable jetson_clocks.

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read jetson_clocks status
                    print(jetson.jetson_clocks.boot)
                    # Set a new state for jetson_clocks
                    jetson.jetson_clocks.boot = True

        :return: Status jetson_clocks on boot
        :rtype: bool
        """
        return self._boot

    @boot.setter
    def boot(self, value):
        self.set_boot(value)

    def is_config(self):
        """
        Return the jetson_clocks configuration status. If true jtop has stored a configuration file with all data

        :return: configuration stored
        :rtype: bool
        """
        return self._config

    def get_status(self):
        """
        Return the jetson_clocks service status:

        There are **six** options:

        ============== =============================================
        Status         Description
        ============== =============================================
        running        jetson_clocks is currently running
        booting        jetson_clocks is booting. This status appears in the first 60s when your board is started
        activating     jtop is running the service to activating jetson_clocks
        deactivating   jtop is running the service to deactivating jetson_clocks
        uncontrolled   jtop is not able to setup jetson_clocks. This message can appears if jetson_clocks was already running before jtop service started
        inactive       jetson_clocks is inactive
        ============== =============================================

        :return: status jetson_clocks service
        :rtype: str
        """
        # Check if is alive jetson_clocks
        if self._enable:
            return 'running'
        # Otherwise check status thread jetson_clocks
        return self._thread

    @property
    def status(self):
        """
        This property return the same output of :py:class:`~get_status`

        :return: status jetson_clocks service
        :rtype: str
        """
        return self.get_status()

    def clear_config(self):
        """
        This method clear the jetson_clocks configuration that use jtop.
        """
        # Clear jetson_clocks configuration
        self._controller.put({'jc': {'clear': True}})

    def __nonzero__(self):
        return self._enable

    def __bool__(self):
        return self._enable

    def __and__(self, other):
        return self._enable & bool(other)

    def __or__(self, other):
        return self._enable | bool(other)

    def __xor__(self, other):
        return self._enable ^ bool(other)

    def __int__(self):
        return int(self._enable)

    def __index__(self):
        return int(self._enable)

    def __eq__(self, other):
        if isinstance(other, bool):
            return self._enable == other
        elif isinstance(other, JetsonClocks):
            return self._enable == other._enable
        else:
            return False

    def __repr__(self):
        return str(self._enable)


class JetsonClocksService(object):
    """
        This controller manage the jetson_clocks service.
    """

    def __init__(self, config, fan):
        self._data = {}
        # Status thread enable/disable
        self._thread_status = 'inactive'
        # Initialization Jetson Clocks Object thread
        self._jetson_clocks_thread = None
        # List engines request
        self._engines_list = {}
        # Error message
        self._error = None
        # nvpmodel
        self._nvpmodel = None
        # Load configuration
        self._config = config
        # other modules
        self._fan = fan
        # Config file
        jetson_clocks_file = config.get('jetson_clocks', {}).get('l4t_file', CONFIG_DEFAULT_L4T_FILE)
        self._config_l4t = os.path.join(config.path, jetson_clocks_file)
        # Jetson Clocks path
        self._jetson_clocks_bin = ''
        for path in PATH_JETSON_CLOCKS:
            if os.path.exists(path):
                self._jetson_clocks_bin = path
                logger.info("jetson_clocks found in {cmd}".format(cmd=self._jetson_clocks_bin))
                break
        if not self._jetson_clocks_bin:
            logger.warning("jetson_clocks not available")

    def exists(self):
        return True if self._jetson_clocks_bin else False

    def initialization(self, nvpmodel, data):
        self._data = data
        self._nvpmodel = nvpmodel
        # List of all engines required
        self._engines_list = self.show()
        # Check if jetson_clocks is alive
        is_enabled = self.get_enable()
        # Check if exist configuration file
        if not os.path.isfile(self._config_l4t):
            if is_enabled:
                self._thread_status = 'uncontrolled'
                logger.warning("I can't store jetson_clocks configuration is already running!")
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
            self.set_enable(True)

    def set_enable(self, enable, reset_nvpmodel=False):
        # If there are exception raise
        self._error_status()
        # Check status jetson_clocks
        running_status = self.is_running()
        if running_status != 'inactive':
            logger.warning("jetson_clocks is {status}".format(status=running_status))
            return False
        if enable:
            # Check if the configuration exist
            if not self.is_config():
                if not self.store():
                    return False
            # Start thread Service client
            self._jetson_clocks_thread = Thread(target=self._th_start, args=(reset_nvpmodel, ))
            self._jetson_clocks_thread.start()
        else:
            # Start thread Service client
            self._jetson_clocks_thread = Thread(target=self._th_stop, args=(reset_nvpmodel, ))
            self._jetson_clocks_thread.start()
        return True

    def get_enable(self):
        return jetson_clocks_alive(self._engines_list, self._data)

    def set_boot(self, value):
        # Extract configuration
        config = self._config.get('jetson_clocks', {})
        # Add new value
        config['boot'] = value
        # Set new jetson_clocks configuration
        self._config.set('jetson_clocks', config)

    def get_boot(self):
        config = self._config.get('jetson_clocks', {})
        return config.get('boot', CONFIG_DEFAULT_BOOT)

    def is_config(self):
        return os.path.isfile(self._config_l4t)

    def is_running(self):
        if self._jetson_clocks_thread is not None:
            if not self._jetson_clocks_thread.is_alive():
                self._thread_status = 'inactive'
        return self._thread_status

    def _fix_fan(self, status_fan):
        # Fix fan speed
        for name in status_fan:
            profile = status_fan[name]['profile']
            self._fan.set_profile(name, profile)
            logger.debug("Fan \"{name}\" profile: {profile}".format(name=name, profile=profile))
            if profile == 'manual':
                for idx, speed in enumerate(status_fan[name]['speed']):
                    self._fan.set_speed(name, speed, idx)
                    logger.debug("fan \"{name}\"[{idx}]: {speed}".format(name=name, idx=idx, speed=speed))

    def _th_start(self, reset_nvpmodel):
        self._thread_status = 'activating'
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
            self._thread_status = 'booting'
            delta = (boot_time - up_time).total_seconds()
            logger.info("Starting jetson_clocks in: {delta}s".format(delta=delta))
        # Status jetson_clocks
        logger.info("Start jetson_clocks with {status}".format(status=self._thread_status))
        if up_time < boot_time:
            time.sleep(delta)
        # Read fan speed
        status_fan = self._fan.get_status()
        if reset_nvpmodel and self._nvpmodel.exists():
            nvpmodel_id = self._nvpmodel.get_nvpmodel_id()
        # Start jetson_clocks
        Command.run_command([self._jetson_clocks_bin], repeat=5, timeout=COMMAND_TIMEOUT)
        # Fix fan speed
        self._fix_fan(status_fan)
        # Reset nvpmodel
        if reset_nvpmodel and self._nvpmodel.exists():
            self._nvpmodel.set_nvpmodel_id(nvpmodel_id, False)
        logger.info("jetson_clocks started")

    def _th_stop(self, reset_nvpmodel):
        self._thread_status = 'deactivating'
        logger.debug("Start jetson_clocks with {status}".format(status=self._thread_status))
        # Read fan speed
        status_fan = self._fan.get_status()
        if reset_nvpmodel and self._nvpmodel.exists():
            nvpmodel_id = self._nvpmodel.get_nvpmodel_id()
        # Run jetson_clocks
        Command.run_command([self._jetson_clocks_bin, '--restore', self._config_l4t], repeat=5, timeout=COMMAND_TIMEOUT)
        # Fix fan speed
        self._fix_fan(status_fan)
        # Reset nvpmodel
        if reset_nvpmodel and self._nvpmodel.exists():
            self._nvpmodel.set_nvpmodel_id(nvpmodel_id, False)
        logger.info("jetson_clocks stopped")

    def _error_status(self):
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value

    def close(self):
        # Switch off thread jetson clocks
        self._running = False
        # If jetson_clocks doesn't exist skip
        if not self.exists():
            return
        # If there are no thread running skip
        if self._jetson_clocks_thread is None:
            return
        if self._jetson_clocks_thread.is_alive():
            logger.warning("Wait switch off jetson_clocks thread")
            self._jetson_clocks_thread.join(COMMAND_TIMEOUT)

    def show(self):
        cmd = Command([self._jetson_clocks_bin, '--show'])
        list_engines = {}
        try:
            lines = cmd(timeout=COMMAND_TIMEOUT)
            list_engines = decode_show_message(lines)
        except Command.TimeoutException as e:
            logger.warning("Timeout {}".format(e))
        return list_engines

    def store(self):
        if self.is_config():
            logger.error("Configuration already stored in {file}".format(file=self._config_l4t))
            return False
        if self.get_enable():
            self._thread_status = 'uncontrolled'
            logger.error("jetson_clocks is running. I cannot store configuration")
            return False
        # Store configuration jetson_clocks
        cmd = Command([self._jetson_clocks_bin, '--store', self._config_l4t])
        try:
            message = cmd(timeout=COMMAND_TIMEOUT)
        except Command.CommandException:
            return False
        logger.info("Store jetson_clocks configuration in {file}".format(file=self._config_l4t))
        # Extract result
        return True if message else False

    def clear(self):
        if os.path.isfile(self._config_l4t):
            logger.info("Clear jetson_clocks config in {path}".format(path=self._config_l4t))
            # Remove configuration file
            os.remove(self._config_l4t)
            return True
        return False

    def get_status(self, data):
        self._data = data
        return {
            'enable': self.get_enable(),
            'thread': self.is_running(),
            'config': self.is_config(),
            'boot': self.get_boot(),
        }
# EOF
