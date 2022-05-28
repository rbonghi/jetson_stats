# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2022 Raffaello Bonghi.
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
from math import ceil
from .common import locate_commands
from .exceptions import JtopException
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)
# Fan configurations
CONFIG_DEFAULT_FAN_SPEED = 0.0
FAN_PWM_CAP = 255

def get_all_fans(root_path):
    paths = {}
    # Reference folders "/sys/devices/platform/pwm-fan*/hwmon/hwmon*/pwm*"
    for item in os.listdir(root_path):
        # Search alll pwm-fan that have hwmon folder
        path = os.path.join(root_path, item)
        if os.path.isdir(path) and item.startswith("pwm-fan"):
            path = os.path.join(path, "hwmon")
            if os.path.isdir(path):
                for item in os.listdir(path):
                    path = os.path.join(path, item)
                    # Get all files and add only pwm fan
                    files = [file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))]
                    for file in files:
                        if file.startswith("pwm"):
                            paths[file] = os.path.join(path, file)
    return paths


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
        return self._status[0]

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
        return self._status['speed']

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
            root_path = locate_commands("fan", fan_path)
        except JtopException as error:
            logger.warning("{error} in paths {path}".format(error=error, path=fan_path))
        # Set list configurations
        self.CONFIGS = ['system', 'manual']
        # Get list all pwm_fan
        self._fans = get_all_fans(root_path)
        self._status['mode'] = 'system'
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
        
    @property
    def speed(self):
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
        #if os.access(self.path + '/target_pwm', os.W_OK):
        #    with open(self.path + '/target_pwm', 'w') as f:
        #        f.write(str(pwm))
                    
    def _PWMtoValue(self, pwm):
        pwm = int(pwm)
        return float(pwm) * 100.0 / FAN_PWM_CAP

    def _ValueToPWM(self, value):
        return int(ceil(FAN_PWM_CAP * value / 100.0))
    
    def update(self):
        fan_speed = {}
        for fan in self._fans:
            path = self._fans[fan]
            fan_speed[fan] = self._PWMtoValue(self._read_status(path))
        self._status['speed'] = fan_speed
        return self._status
    
    def _read_status(self, file_read):
        with open(file_read, 'r') as f:
            return f.read()
        return None
# EOF
