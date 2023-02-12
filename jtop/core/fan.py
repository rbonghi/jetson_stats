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
FAN_NVFAN_NAME_RE = re.compile(r'^<FAN (?P<num>\d+)>$')
FAN_NVFAN_OPTIONS_RE = re.compile(r'FAN_(?P<type>\w+) (?P<value>\w+) {$')
FAN_NVFAN_DEFAULT_RE = re.compile(r'FAN_DEFAULT_(?P<type>\w+) (?P<value>\w+)')


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
                pwm_files[name] = {'path': fan_device_paths}
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


def nvfancontrol_query():
    status = {}
    try:
        nvpmodel_p = Command(['nvfancontrol', '-q'])
        lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
        for line in lines:
            values = line.split(':')
            fan_name = values[0].lower()
            query = values[1].replace("FAN_", "").lower()
            if fan_name not in status:
                status[fan_name] = {}
            status[fan_name][query] = values[2]
    except (OSError, Command.CommandException):
        pass
    return status


def decode_nvfancontrol():
    nvfan = {}
    current_fan = ''
    if os.path.isfile("/etc/nvfancontrol.conf"):
        with open("/etc/nvfancontrol.conf", 'r') as fp:
            for line in fp:
                match_name = re.search(FAN_NVFAN_NAME_RE, line.strip())
                match_values = re.search(FAN_NVFAN_OPTIONS_RE, line.strip())
                # match_defaults = re.search(FAN_NVFAN_DEFAULT_RE, line.strip())
                if match_name:
                    parsed_line = match_name.groupdict()
                    current_fan = 'fan{num}'.format(num=parsed_line['num'])
                    nvfan[current_fan] = {}
                elif match_values:
                    parsed_line = match_values.groupdict()
                    type_name = parsed_line['type'].lower()
                    if type_name not in nvfan[current_fan]:
                        nvfan[current_fan][type_name] = []
                    nvfan[current_fan][type_name] += [parsed_line['value']]
                # elif match_defaults:
                #    parsed_line = match_defaults.groupdict()
                #    type_name = parsed_line['type'].lower()
                #    nvfan[current_fan]['default_{name}'.format(name=type_name)] = parsed_line['value']
    return nvfan


def change_nvfancontrol_default(name, value):
    with open("/etc/nvfancontrol.conf", "r") as f:
        lines = f.readlines()
    with open("/etc/nvfancontrol.conf", "w") as f:
        for line in lines:
            match_defaults = re.search(FAN_NVFAN_DEFAULT_RE, line.strip())
            if match_defaults:
                parsed_line = match_defaults.groupdict()
                if name.upper() == parsed_line['type']:
                    # Override line with new value
                    line = line.replace(parsed_line['value'], value)
            # Print line
            f.write(line)


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
            nv_fan_modes = decode_nvfancontrol()
            # Add all nvfanmodes
            for fan, nvfan in zip(self._fan_list, nv_fan_modes):
                self._fan_list[fan].update(nv_fan_modes[nvfan])
                # Add extra profile for disabled service
                if 'profile' in self._fan_list[fan]:
                    self._fan_list[fan]['profile'] += ['manual']

    def initialization(self):
        pass

    def get_profiles(self):
        governors = {}
        for fan, data in self._fan_list.items():
            governors[fan] = data['profile']
        return governors

    def get_profile(self, fan):
        profile = "manual"
        nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
        if nvfancontrol_is_active:
            nvfan_query = nvfancontrol_query()
            for fan_list_name, nvfan in zip(self._fan_list, nvfan_query):
                if fan_list_name == fan:
                    return nvfan_query[nvfan]['profile']
        return profile

    def set_profile(self, fan, profile):
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            # Check first if the fan control is active and after enable the service
            if profile in self._fan_list[fan]['profile']:
                if profile == 'manual':
                    if nvfancontrol_is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Profile set {profile}".format(profile=profile))
                    else:
                        logger.info("Profile {profile} already active".format(profile=profile))
                else:
                    # Check current status before change
                    if profile == self.get_profile(fan):
                        logger.info("Profile {profile} already active".format(profile=profile))
                        return True
                    # Check if active and stop
                    if nvfancontrol_is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Stop nvfancontrol service")
                    # Update nvfile
                    change_nvfancontrol_default('profile', profile)
                    logger.info("Change /etc/nvfancontrol.conf profile in {profile}".format(profile=profile))
                    # Remove nvfancontrol staus file
                    if os.path.isfile("/var/lib/nvfancontrol/status"):
                        os.remove("/var/lib/nvfancontrol/status")
                        logger.info("Removed /var/lib/nvfancontrol/status")
                    # Restart service
                    os.system('systemctl start nvfancontrol')
                    logger.info("Profile set {profile}".format(profile=profile))
            else:
                logger.error("Profile {mode} doesn't exist")
        else:
            print("TODO SET PROFILE")
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
        for pwm_path in self._fan_list[name]['path']:
            if os.access(pwm_path, os.W_OK):
                with open(pwm_path, 'w') as f:
                    f.write(pwm)

    def get_status(self):
        fan_status = {}
        # Read all fan status
        for name, data in self._fan_list.items():
            list_pwm = data['path']
            # Read pwm from all fan
            fan_status[name] = {'speed': [PWMtoValue(cat(pwm)) for pwm in list_pwm]}
        # Check status fan control
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            nvfan_query = nvfancontrol_query()
            if nvfancontrol_is_active:
                for fan, nvfan in zip(fan_status, nvfan_query):
                    fan_status[fan].update(nvfan_query[nvfan])
            else:
                for fan in fan_status:
                    fan_status[fan]['profile'] = 'manual'
        return fan_status
# EOF
