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
from math import ceil
# Logging
import logging
# Launch command
from .command import Command
from .common import cat
# Create logger
logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 4.0
FAN_PWM_CAP = 255
FAN_PWM_RE = re.compile(r'^pwm\d+$')


def PWMtoValue(pwm, pwm_cap=FAN_PWM_CAP):
    return float(pwm) * 100.0 / (pwm_cap)


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    return int(ceil((pwm_cap) * value / 100.0))


def get_all_cooling_system():
    pwm_files = {}
    path = "/sys/class/hwmon"
    for dir in os.listdir(path):
        full_path = os.path.join(path, dir)
        if os.path.isdir(full_path):
            fan_device_paths = []
            # Find all pwm in folder
            for file in os.listdir(full_path):
                if FAN_PWM_RE.match(file) or file == 'target_pwm':
                    fan_device_paths += [os.path.join(full_path, file)]
            # If there are pwm is added in list
            if fan_device_paths:
                name_file = os.path.join(full_path, 'name')
                name = cat(name_file).strip() if os.path.isfile(name_file) else dir
                pwm_files[name] = fan_device_paths
                logger.info("Fan {name} found in {root_path}".format(name=name, root_path=full_path))
    return pwm_files


def get_all_legacy_fan():
    pwm_files = {}
    root_path = ""
    for path in ['/sys/kernel/debug/tegra_fan', '/sys/devices/pwm-fan']:
        if os.path.exists(path):
            root_path = path
            break
    if not root_path:
        return pwm_files
    # Check if this fan is already listed
    if os.path.isdir(os.path.join(root_path, 'hwmon')):
        return pwm_files
    # Otherwise add in list
    name = os.path.basename(root_path)
    logger.info("Found legacy Jetson {name} in {root_path}".format(name=name, root_path=root_path))
    return pwm_files


class Fan(object):

    def __init__(self, controller, CONFIGS):
        self._controller = controller
        self._CONFIGS = CONFIGS
        # Initialize fan
        self._status = {}


class FanService(object):

    def __init__(self, config):
        # Load configuration
        self._config = config
        # Fin all fan available
        self._fan_list = get_all_cooling_system()
        self._fan_list.update(get_all_legacy_fan())
        # Check if there is nvfan control
        nvfancontrol = "nvfancontrol.service"
        self._nvfancontrol = os.path.isfile('/etc/systemd/system/{name}'.format(name=nvfancontrol)
                                            ) or os.path.islink('/etc/systemd/system/{name}'.format(name=nvfancontrol))
        if nvfancontrol:
            logger.info("Found {service}".format(service=nvfancontrol))
        print(self.get_status())

    def initialization(self):
        pass

    def set_mode(self, mode):
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            # Check first if the fan control is active and after enable the service
            if mode == 'system':
                if not nvfancontrol_is_active:
                    os.system('systemctl start nvfancontrol')
                    logger.info("Mode set {mode}".format(mode=mode))
                else:
                    logger.info("Mode {mode} already active".format(mode=mode))
            elif mode == 'manual':
                if nvfancontrol_is_active:
                    os.system('systemctl stop nvfancontrol')
                    logger.info("Mode set {mode}".format(mode=mode))
                else:
                    logger.info("Mode {mode} already active".format(mode=mode))
            else:
                logger.error("Mode {mode} doesn't exist")
        return True

    def set_speed(self, name, speed):
        if name not in self._fan_list:
            return
        # Check constraints
        if speed > 100:
            speed = 100
        if speed < 0:
            speed = 0
        # Convert in PWM
        pwm = str(ValueToPWM(speed))
        # Set for all pwm the same speed value
        for pwm_path in self._fan_list[name]:
            if os.access(pwm_path, os.W_OK):
                with open(pwm_path, 'w') as f:
                    f.write(pwm)

    def nvfancontrol_query(self):
        status = {}
        try:
            nvpmodel_p = Command(['nvfancontrol', '-q'])
            lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
            for line in lines:
                print(line)

        except (OSError, Command.CommandException):
            pass
        return status

    def get_status(self):
        fan_status = {'fan': {}}
        # Read all fan status
        for name, list_pwm in self._fan_list.items():
            # Read pwm from all fan
            fan_status['fan'][name] = [PWMtoValue(cat(pwm)) for pwm in list_pwm]
        # Check status fan control
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            status = self.nvfancontrol_query()
            fan_status['mode'] = 'system' if nvfancontrol_is_active else 'manual'
            fan_status['auto'] = nvfancontrol_is_active
        return fan_status
# EOF
