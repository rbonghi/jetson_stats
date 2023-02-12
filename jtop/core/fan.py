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
from .common import cat
# Create logger
logger = logging.getLogger(__name__)

FAN_PWM_CAP = 255
FAN_PWM_RE = re.compile(r'^pwm\d+$')


def PWMtoValue(pwm, pwm_cap=FAN_PWM_CAP):
    return float(pwm) * 100.0 / (pwm_cap)


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    return int(ceil((pwm_cap) * value / 100.0))


def get_all_cooling_system():
    pwm_files = []
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
                pwm_file = {
                    'name': name,
                    'path': fan_device_paths
                }
                pwm_files += [pwm_file]
                logger.info("Fan {name} found in {root_path}".format(name=name, root_path=full_path))
    return pwm_files


def get_all_legay_fan():
    pwm_files = []
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


def check_nvfancontrol():
    name = "nvfancontrol.service"
    if os.path.isfile('/etc/systemd/system/{name}'.format(name=name)) or os.path.islink('/etc/systemd/system/{name}'.format(name=name)):
        print("AAA")
    return False

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
        # Fin all fan avaialable
        self._fan_list = get_all_cooling_system()
        self._fan_list += get_all_legay_fan()
        # Check if there is nvfan control
        self._nvfancontrol = check_nvfancontrol()
        
        print(self.get_status())

    def initialization(self):
        pass

    def get_status(self):
        fan_status = {'fan': []}
        # Read all fan status
        for fan in self._fan_list:
            # Read pwm from all fan
            speeds = []
            for pwm in fan['path']:
                speeds += [PWMtoValue(cat(pwm))]
            fan_status['fan'] += [{'name': fan['name'], 'speed': speeds}]
        # Check status fan control
        nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
        fan_status['mode'] = 'system' if nvfancontrol_is_active else 'manual'
        fan_status['auto'] = nvfancontrol_is_active
        return fan_status
# EOF
