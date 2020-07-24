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
from math import ceil
from .common import locate_commands
from .exceptions import JtopException
# Logging
import logging
# Compile decoder PWM table
FAN_PWM_TABLE_RE = re.compile(r'\((.*?)\)')
# Create logger
logger = logging.getLogger(__name__)
# Fan configurations
CONFIG_DEFAULT_FAN_SPEED = 0.0


def load_table(path):
    table = []
    with open(path, 'r') as fp:
        title = []
        for line in fp.readlines():
            match = FAN_PWM_TABLE_RE.search(line)
            line = [tab.strip() for tab in match.group(1).split(",")]
            if title:
                table += [{title[idx]: val for idx, val in enumerate(line) if idx > 0}]
            else:
                title = line
    return table


class Fan(object):

    def __init__(self, controller, CONFIGS):
        self._controller = controller
        self._CONFIGS = CONFIGS
        # Initialize fan
        self._status = {}

    @property
    def rpm(self):
        return self._status.get('rpm', None)

    @property
    def measure(self):
        return self._status.get('measure', None)

    @property
    def auto(self):
        return self._status.get('auto', None)

    @property
    def mode(self):
        return self._status.get('mode', None)

    @mode.setter
    def mode(self, value):
        if value not in self._CONFIGS:
            raise JtopException('Control does not available')
        # If value is the same do not do nothing
        if self.mode == value:
            return
        # Set new jetson_clocks configuration
        self._controller.put({'fan': {'mode': value}})

    @property
    def speed(self):
        return self._status.get('speed', None)

    @speed.setter
    def speed(self, value):
        if 'speed' not in self._status:
            raise JtopException('You can not set a speed for this fan')
        if not isinstance(value, (int, float)):
            raise ValueError("Use a number")
        # Check limit speed
        if value < 0.0 or value > 100.0:
            raise ValueError('Wrong speed. Number between [0, 100]')
        # If value is the same do not do nothing
        if self.speed == value:
            return
        # Set new jetson_clocks configuration
        self._controller.put({'fan': {'speed': value}})

    @property
    def configs(self):
        return self._CONFIGS

    def _update(self, status):
        self._status = status

    def get(self, key, value=None):
        return self._status[key] if key in self._status else value

    def __getitem__(self, key):
        return self._status[key]

    def __len__(self):
        return len(self._status)

    def __repr__(self):
        return str(self._status)


class FanService(object):
    """
    Fan controller

    Unused variables:
     - table
     - step
    """
    def __init__(self, config, fan_path):
        # Configuration
        self._config = config
        # Initialize dictionary status
        self._status = {}
        # Initialize number max records to record
        try:
            self.path = locate_commands("fan", fan_path)
        except JtopException as error:
            logger.warning("{error} in paths {path}".format(error=error, path=fan_path))
            self.path = None
        # Configs
        self.is_debug = 'debug' in self.path if self.path is not None else False
        # Set list configurations
        if self.path is None:
            self.CONFIGS = ['default']
        elif self.is_debug:
            self.CONFIGS = ['default', 'manual']
        else:
            self.CONFIGS = ['default', 'system', 'manual']
        # Init status fan
        self.isRPM = os.path.isfile(self.path + '/rpm_measured') if self.path is not None else False
        self.isCPWM = os.path.isfile(self.path + '/cur_pwm') if self.path is not None else False
        self.isTPWM = os.path.isfile(self.path + '/target_pwm') if self.path is not None else False
        self.isCTRL = os.path.isfile(self.path + '/temp_control') if self.path is not None else False
        self._allFiles = any([self.isRPM, self.isCPWM, self.isTPWM, self.isCTRL])
        if not self._allFiles and self.path is not None:
            logger.warning("No access to fan files: rpm_measured, cur_pwm, target_pwm, temp_control")
        # Max value PWM
        self._pwm_cap = 255
        if self.path is not None:
            if os.path.isfile(self.path + '/pwm_cap'):
                self._pwm_cap = float(self._read_status('/pwm_cap'))
        # PWM RPM table
        self.table = {}
        if self.path is not None:
            if os.path.isfile(self.path + '/pwm_rpm_table'):
                self.table = load_table(self.path + '/pwm_rpm_table')
        # Step time
        self.step = 0
        if self.path is not None:
            if os.path.isfile(self.path + '/step_time'):
                self.step = int(self._read_status('/step_time'))
        # Update variables
        self.update()

    def initialization(self, jc):
        self._jc = jc
        # Load configuration
        config_fan = self._config.get('fan', {})
        # Set default speed
        self._speed = config_fan.get('speed', CONFIG_DEFAULT_FAN_SPEED)
        # Set default mode
        mode = config_fan.get('mode', self.CONFIGS[0] if self.CONFIGS else '')
        self.set_mode(mode, False)

    def get_configs(self):
        return self.CONFIGS

    @property
    def mode(self):
        config_fan = self._config.get('fan', {})
        return config_fan.get('mode', self.CONFIGS[0] if self.CONFIGS else '')

    @mode.setter
    def mode(self, value):
        if value not in self.CONFIGS:
            raise JtopException('This control does not available')
        jc_status = self._jc.alive(wait=False) if self._jc is not None else False
        self.set_mode(value, jc_status)

    def set_mode(self, value, status):
        logger.info("Mode set {mode} status={status}".format(mode=value, status=status))
        # Set mode fan
        if value == 'system':
            self.auto = True
        if value == 'default':
            # Set in auto only if jetson_clocks in not active
            if self._jc is not None:
                if self.is_speed:
                    # Only if jetson_clocks is alive set max speed for fan
                    self.set_speed(100 if status else 0)
                # Set automatic mode:
                # - True if jetson_clocks is off
                # - False if jetson_clocks is running
                self.auto = not status
        if value == 'manual':
            # Switch off speed
            self.auto = False
            # Initialize default speed
            if self.is_speed:
                self.speed = self._speed
        # Store mode
        self._status['mode'] = value
        # Store only if value is different
        if self.mode != value:
            # Extract configuration
            config = self._config.get('fan', {})
            # Add new value
            config['mode'] = value
            # Set new jetson_clocks configuration
            self._config.set('fan', config)
            # Fan setting
            logger.debug("Config {config}".format(config=config))

    @property
    def is_speed(self):
        return self.isTPWM

    @property
    def speed(self):
        if not self.isTPWM:
            raise JtopException('You can not set a speed for this fan')
        return self._status['speed']

    @speed.setter
    def speed(self, value):
        self.set_speed(value)
        # Extract configuration
        config = self._config.get('fan', {})
        # Add new value
        config['speed'] = value
        # Update speed status
        self._speed = value
        # Set new jetson_clocks configuration
        self._config.set('fan', config)
        # Fan setting
        logger.debug("Config {config}".format(config=config))

    def set_speed(self, value):
        # Check type
        if not isinstance(value, (int, float)):
            raise ValueError('Need a number')
        # Check limit speed
        if value < 0.0 or value > 100.0:
            raise ValueError('Wrong speed. Number between [0, 100]')
        # Convert in PWM
        pwm = self._ValueToPWM(value)
        # Write PWM value
        if self.isTPWM:
            if os.access(self.path + '/target_pwm', os.W_OK):
                with open(self.path + '/target_pwm', 'w') as f:
                    f.write(str(pwm))

    @property
    def auto(self):
        return self._status.get('auto', False)

    @auto.setter
    def auto(self, value):
        if not isinstance(value, bool):
            raise ValueError('Need a boolean')
        # Override if fan is in debug folder
        value = True if self.is_debug else value
        # Check limit speed
        value = 1 if value else 0
        # Write status control value
        if self.isCTRL:
            if os.access(self.path + '/temp_control', os.W_OK):
                with open(self.path + '/temp_control', 'w') as f:
                    f.write(str(value))

    def _PWMtoValue(self, pwm):
        pwm = int(pwm)
        return float(pwm) * 100.0 / (self._pwm_cap)

    def _ValueToPWM(self, value):
        return int(ceil((self._pwm_cap) * value / 100.0))

    def update(self):
        if not self._allFiles:
            return {}
        # Control temperature
        self._status['auto'] = bool(int(self._read_status('/temp_control')) == 1) if self.isCTRL else None
        # Read PWM
        self._status['speed'] = self._PWMtoValue(self._read_status('/target_pwm')) if self.isTPWM else None
        # Read current
        self._status['measure'] = self._PWMtoValue(self._read_status('/cur_pwm')) if self.isCPWM else None
        # Read RPM fan
        self._status['rpm'] = int(self._read_status('/rpm_measured')) if self.isRPM else None
        return self._status

    def _read_status(self, file_read):
        with open(self.path + file_read, 'r') as f:
            return f.read()
        return None
# EOF
