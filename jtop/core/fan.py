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

import abc
import os
import re
from math import ceil
from .common import locate_commands
from .exceptions import JtopException
# Logging
import logging
# Initialization abstract class
# In according with: https://gist.github.com/alanjcastonguay/25e4db0edd3534ab732d6ff615ca9fc1
ABC = abc.ABCMeta('ABC', (object,), {})
# Compile decoder PWM table
FAN_PWM_TABLE_RE = re.compile(r'\((.*?)\)')
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


def file_read_status(file_path):
    with open(file_path, 'r') as f:
        return f.read()


def file_write_status(file_path, data):
    if os.access(file_path, os.W_OK):
        with open(file_path, 'w') as f:
            f.write(data)
    return None


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

    def all_speed(self):
        return self._status.get('speed', {})

    @property
    def speed(self):
        speeds = self._status.get('speed', None)
        if isinstance(speeds, (dict)):
            return list(speeds.values())[0]
        return speeds

    def set_speed(self, value):
        if 'speed' not in self._status:
            raise JtopException('You can not set a speed for this fan')
        if not isinstance(value, (list)):
            raise ValueError("Use a list")
        if not all(isinstance(x, (int, float)) for x in value):
            raise ValueError("All elements must be numbers")
        # Read all speeds
        speeds = self.all_speed()
        if len(speeds) != len(value):
            raise IndexError("Value must be same length {len}".format(len=len(speeds)))
        # Check limit speed
        if value < 0.0 or value > 100.0:
            raise ValueError('Wrong speed. Number between [0, 100]')
        # If value is the same do not do nothing
        check = True
        for speed, new_speed in zip(speeds, value):
            check += speed == new_speed
        if check:
            return
        # Set new jetson_clocks configuration
        self._controller.put({'fan': {'speed': value}})

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


class ABCFanService(ABC):
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
        # PWM max capcity
        self._pwm_cap = FAN_PWM_CAP
        # Fan configurations
        self.CONFIGS = []

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

    @abc.abstractmethod
    def set_mode(self, value, status):
        pass

    @abc.abstractmethod
    def is_speed(self):
        pass

    @abc.abstractmethod
    def set_speed(self, value):
        pass

    @abc.abstractmethod
    def update(self):
        pass

    def _PWMtoValue(self, pwm):
        pwm = int(pwm)
        return float(pwm) * 100.0 / (self._pwm_cap)

    def _ValueToPWM(self, value):
        return int(ceil((self._pwm_cap) * value / 100.0))


class FanService(ABCFanService):

    def __init__(self, config, fan_path):
        super(FanService, self).__init__(config, fan_path)
        # Initialize number max records to record
        # raise jtop error if not available a fan
        root_path = locate_commands("fan", fan_path)
        # Set list configurations
        self.CONFIGS = ['system', 'manual']
        # Get list all pwm_fan
        self._fans = get_all_fans(root_path)
        if not self._fans:
            raise JtopException("Fan is not available on this board")
        # Check status nvfancontrol
        self.update()

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

    def set_mode(self, value, status):
        logger.info("Mode set {mode} status={status}".format(mode=value, status=status))
        nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
        # Check first if the fan control is active and after enable the service
        if value == 'system':
            if not nvfancontrol_is_active:
                os.system('systemctl start nvfancontrol')
        elif value == 'manual':
            if nvfancontrol_is_active:
                os.system('systemctl stop nvfancontrol')

    def is_speed(self):
        return True

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
        for fan in self._fans:
            file_write_status(self._fans[fan], str(pwm))

    def update(self):
        fan_speed = {}
        # Read all fan status
        for fan in self._fans:
            path = self._fans[fan]
            fan_speed[fan] = self._PWMtoValue(file_read_status(path))
        self._status['speed'] = fan_speed
        # Check status fan control
        nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
        self._status['mode'] = 'system' if nvfancontrol_is_active else 'manual'
        self._status['auto'] = nvfancontrol_is_active
        return self._status


class FanServiceLegacy(ABCFanService):

    def __init__(self, config, fan_path):
        super(FanServiceLegacy, self).__init__(config, fan_path)
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
        self._pwm_cap = FAN_PWM_CAP
        if self.path is not None:
            if os.path.isfile(self.path + '/pwm_cap'):
                self._pwm_cap = float(file_read_status(self.path + '/pwm_cap'))
        # PWM RPM table
        self.table = {}
        if self.path is not None:
            if os.path.isfile(self.path + '/pwm_rpm_table'):
                self.table = load_table(self.path + '/pwm_rpm_table')
        # Step time
        self.step = 0
        if self.path is not None:
            if os.path.isfile(self.path + '/step_time'):
                self.step = int(file_read_status(self.path + '/step_time'))
        # Update variables
        self.update()

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

    def set_mode(self, value, status):
        logger.info("Mode set {mode} status={status}".format(mode=value, status=status))
        # Set mode fan
        if value == 'system':
            self.auto = True
        if value == 'default':
            # Set in auto only if jetson_clocks in not active
            if self._jc is not None:
                if self.isTPWM:
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
            if self.isTPWM:
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

    def is_speed(self):
        return self.isTPWM

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

    def update(self):
        if not self._allFiles:
            return {}
        # Control temperature
        self._status['auto'] = bool(int(file_read_status(self.path + '/temp_control')) == 1) if self.isCTRL else None
        # Read PWM
        self._status['speed'] = {'FAN1': self._PWMtoValue(file_read_status(self.path + '/target_pwm'))} if self.isTPWM else None
        # Read current
        self._status['measure'] = self._PWMtoValue(file_read_status(self.path + '/cur_pwm')) if self.isCPWM else None
        # Read RPM fan
        self._status['rpm'] = int(file_read_status(self.path + '/rpm_measured')) if self.isRPM else None
        return self._status
# EOF
