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
FAN_MANUAL_NAME = 'manual'
FAN_TEMP_CONTROL_NAME = 'temp_control'
FAN_PWM_RE = re.compile(r'^pwm\d+$')
FAN_NVFAN_NAME_RE = re.compile(r'^<FAN (?P<num>\d+)>$')
FAN_NVFAN_OPTIONS_RE = re.compile(r'FAN_(?P<type>\w+) (?P<value>\w+) {$')
FAN_NVFAN_DEFAULT_RE = re.compile(r'FAN_DEFAULT_(?P<type>\w+) (?P<value>\w+)')
# Fan configurations
FAN_PWM_CAP = 255


def PWMtoValue(pwm, pwm_cap=FAN_PWM_CAP):
    return float(pwm) * 100.0 / (pwm_cap)


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    return int(ceil((pwm_cap) * value / 100.0))


def get_all_rpm_system():
    pwm_files = {}
    path = "/sys/class/hwmon"
    for dir in os.listdir(path):
        full_path = os.path.join(path, dir)
        if os.path.isdir(full_path):
            # Find all pwm in folder
            for file in os.listdir(full_path):
                if 'rpm' == file:
                    name_file = os.path.join(full_path, 'name')
                    name = cat(name_file).strip() if os.path.isfile(name_file) else dir
                    pwm_files[name] = os.path.join(full_path, file)
                    logger.info("RPM {name} found in {root_path}".format(name=name, root_path=full_path))
    return pwm_files


def get_all_cooling_system():
    pwm_files = {}
    path = "/sys/class/hwmon"
    for dir in os.listdir(path):
        full_path = os.path.join(path, dir)
        if os.path.isdir(full_path):
            fan_device_paths = []
            fan_rpm_path = []
            # Find all pwm in folder
            for file in os.listdir(full_path):
                if FAN_PWM_RE.match(file) or file == 'target_pwm':
                    fan_device_paths += [os.path.join(full_path, file)]
                # Check if there are rpm values
                if file == 'rpm_measured':
                    fan_rpm_path += [os.path.join(full_path, file)]
            # If there are pwm is added in list
            if fan_device_paths:
                name_file = os.path.join(full_path, 'name')
                name = cat(name_file).strip() if os.path.isfile(name_file) else dir
                pwm_files[name] = {'path': full_path, 'pwm': fan_device_paths}
                logger.info("Fan {name}({num}) found in {root_path}".format(name=name, root_path=full_path, num=len(fan_device_paths)))
            if fan_rpm_path:
                pwm_files[name]['rpm'] = fan_rpm_path
                logger.info("RPM {name}({num}) found in {root_path}".format(name=name, root_path=full_path, num=len(fan_device_paths)))
    # Find all rpm systems
    rpm_list = get_all_rpm_system()
    for fan, rpm in zip(pwm_files, rpm_list):
        pwm_files[fan]['rpm'] = [rpm_list[rpm]]
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

    def __init__(self):
        self._controller = None
        self._info = {}
        self._data = {}

    def _initialize(self, controller, info):
        self._controller = controller
        self._info = info

    def _update(self, data):
        self._data = data

    def items(self):
        return self._data.items()

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __next__(self):
        return next(self._data)

    def __str__(self):
        return str(self._data)


class FanService(object):

    def __init__(self, config):
        # Load configuration
        self._config = config
        # Fin all fan available
        self._fan_list = get_all_cooling_system()
        self._fan_list.update(get_all_legacy_fan())
        # Check if there is nvfan control
        self._nvfancontrol = os.path.isfile('/etc/systemd/system/nvfancontrol.service') or os.path.islink('/etc/systemd/system/nvfancontrol.service')
        # Initialize controller
        if self._nvfancontrol:
            logger.info("Found nvfancontrol.service")
            nv_fan_modes = decode_nvfancontrol()
            # Add all nvfan profiles
            for fan, nvfan in zip(self._fan_list, nv_fan_modes):
                self._fan_list[fan].update(nv_fan_modes[nvfan])
                # Add extra profile for disabled service
                if 'profile' in self._fan_list[fan]:
                    self._fan_list[fan]['profile'] += [FAN_MANUAL_NAME]
        else:
            for name, fan in self._fan_list.items():
                # Initialize profile list
                self._fan_list[name]['profile'] = []
                # Find temp controller
                control = os.path.join(fan['path'], FAN_TEMP_CONTROL_NAME)
                if os.path.isfile(control):
                    # Add control path
                    self._fan_list[name]['control'] = control
                    # Add profiles
                    self._fan_list[name]['profile'] += [FAN_TEMP_CONTROL_NAME]
                    logger.info("Fan temp controller {name} found in {root_path}".format(name=name, root_path=control))
                # Add default profile
                self._fan_list[name]['profile'] += [FAN_MANUAL_NAME]
        if not self._fan_list:
            logger.info("No fan found")

    def initialization(self):
        # Load configuration
        fan_config = self._config.get('fan', {})
        for name, fan in fan_config.items():
            if 'profile' in fan:
                profile = fan['profile']
                logger.info("Initialization {name}".format(name=name))
                self.set_profile(name, profile)
                if profile == FAN_MANUAL_NAME and 'speed' in fan:
                    speed, index = fan['speed']
                    self.set_speed(name, speed, index)
                    logger.info("Initialization {name} {index} speed {speed}%".format(name=name, index=index, speed=speed))

    def get_configs(self):
        governors = {}
        for fan, data in self._fan_list.items():
            governors[fan] = data['profile']
        return governors

    def get_profile(self, name):
        profile = FAN_MANUAL_NAME
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            if nvfancontrol_is_active:
                nvfan_query = nvfancontrol_query()
                for fan_list_name, nvfan in zip(self._fan_list, nvfan_query):
                    if fan_list_name == name:
                        return nvfan_query[nvfan]['profile']
        else:
            if 'control' in self._fan_list[name]:
                control_value = int(cat(self._fan_list[name]['control'])) == 1
                return FAN_TEMP_CONTROL_NAME if control_value else FAN_MANUAL_NAME
        return profile

    def set_profile(self, name, profile):
        # Check current status before change
        if profile == self.get_profile(name):
            logger.warning("Fan {name} profile {profile} already active".format(name=name, profile=profile))
            return True
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            # Check first if the fan control is active and after enable the service
            if profile in self._fan_list[name]['profile']:
                if profile == FAN_MANUAL_NAME:
                    if nvfancontrol_is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Profile set {profile}".format(profile=profile))
                else:
                    # Check if active and stop
                    if nvfancontrol_is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Stop nvfancontrol service")
                    # Update nvfile
                    change_nvfancontrol_default('profile', profile)
                    logger.info("Change /etc/nvfancontrol.conf profile in {profile}".format(profile=profile))
                    # Remove nvfancontrol status file
                    if os.path.isfile("/var/lib/nvfancontrol/status"):
                        os.remove("/var/lib/nvfancontrol/status")
                        logger.info("Removed /var/lib/nvfancontrol/status")
                    # Restart service
                    os.system('systemctl start nvfancontrol')
                    logger.info("Profile set {profile}".format(profile=profile))
            else:
                logger.error("Profile {profile} doesn't exist".format(profile=profile))
                return False
        else:
            if profile in self._fan_list[name]['profile']:
                control_value = "0" if FAN_MANUAL_NAME else "1"
                # Write control if exist
                if 'control' in self._fan_list[name]:
                    control = self._fan_list[name]['control']
                    # Set for all pwm the same speed value
                    if os.access(control, os.W_OK):
                        with open(control, 'w') as f:
                            f.write(control_value)
                    logger.info("Profile set {profile}".format(profile=profile))
            else:
                logger.error("Profile {profile} doesn't exist".format(profile=profile))
                return False
        # Update configuration on board
        fan_config = self._config.get('fan', {})
        # Set new profile
        if name not in fan_config:
            fan_config[name] = {}
        fan_config[name]['profile'] = profile
        # Set new jetson_clocks configuration
        self._config.set('fan', fan_config)
        return True

    def set_speed(self, name, speed, index):
        if name not in self._fan_list:
            logger.error("This fan {name} doesn't exist".format(name=name))
            return
        if index >= len(self._fan_list[name]['pwm']):
            logger.error("Wrong index {index} for {name}".format(index=index, name=name))
            return
        # Check constraints
        if speed > 100:
            speed = 100
        if speed < 0:
            speed = 0
        # Update configuration on board
        fan_config = self._config.get('fan', {})
        # Set new profile
        if name not in fan_config:
            fan_config[name] = {}
        fan_config[name]['speed'] = (speed, index)
        # Set new jetson_clocks configuration
        self._config.set('fan', fan_config)
        # Convert in PWM
        pwm = str(ValueToPWM(speed))
        # Set for all pwm the same speed value
        pwm_path = self._fan_list[name]['pwm'][index]
        if os.access(pwm_path, os.W_OK):
            with open(pwm_path, 'w') as f:
                f.write(pwm)

    def get_status(self):
        fan_status = {}
        # Read all fan status
        for name, data in self._fan_list.items():
            # Read pwm from all fan
            fan_status[name] = {
                'speed': [PWMtoValue(cat(pwm)) for pwm in data['pwm']],
            }
            if 'rpm' in data:
                fan_status[name]['rpm'] = [int(cat(rpm)) for rpm in data['rpm']]
        # Check status fan control
        if self._nvfancontrol:
            nvfancontrol_is_active = os.system('systemctl is-active --quiet nvfancontrol') == 0
            if nvfancontrol_is_active:
                nvfan_query = nvfancontrol_query()
                for fan, nvfan in zip(fan_status, nvfan_query):
                    fan_status[fan].update(nvfan_query[nvfan])
            else:
                for fan in fan_status:
                    fan_status[fan]['profile'] = FAN_MANUAL_NAME
        else:
            for name, data in self._fan_list.items():
                if 'control' in data:
                    control_value = int(cat(data['control'])) == 1
                    fan_status[name]['profile'] = FAN_TEMP_CONTROL_NAME if control_value else FAN_MANUAL_NAME
        return fan_status
# EOF
