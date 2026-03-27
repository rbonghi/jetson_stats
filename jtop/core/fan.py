# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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

# Jetson Thor note:
# The fan is split across multiple hwmon nodes rather than exposed
# entirely under one directory. For example, one hwmon node (often "pwmfan")
# can provide pwm1 / pwm1_enable, while a separate node (often "pwm_tach")
# provides the RPM tachometer. We treat these as one logical fan when pairing
# PWM control with RPM reporting.

import re
import os
# Logging
import logging
# Launch command
from .command import Command
from .common import cat, GenericInterface
from .exceptions import JtopException
from .hw_detect import is_thor
# Create logger
logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 4.0
FAN_MANUAL_NAME = 'manual'
FAN_TEMP_CONTROL_NAME = 'temp_control'
FAN_PWM_RE = re.compile(r'^pwm\d+$')
FAN_PWM_ENABLE_RE = re.compile(r'^pwm\d+_enable$')
FAN_NVFAN_NAME_RE = re.compile(r'^<FAN (?P<num>\d+)>$')
FAN_NVFAN_OPTIONS_RE = re.compile(r'FAN_(?P<type>\w+) (?P<value>\w+) {$')
FAN_NVFAN_DEFAULT_RE = re.compile(r'FAN_DEFAULT_(?P<type>\w+) (?P<value>\w+)')
FAN_KICKSTART_RE = re.compile(r'^KICKSTART_PWM (?P<value>\d+)$')
# Fan configurations
FAN_PWM_CAP = 255


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    return int(value * pwm_cap / 100)


def PWMtoValue(value, pwm_cap=FAN_PWM_CAP):
    return float(value * 100 / pwm_cap)


def _read_name(full_path, fallback):
    name_file = os.path.join(full_path, 'name')
    return cat(name_file).strip() if os.path.isfile(name_file) else fallback


def _readlink_safe(path):
    try:
        if os.path.islink(path):
            return os.path.realpath(path)
    except OSError:
        pass
    return ''


def _collect_hwmon_fans(root_dir):
    pwm_files = {}
    rpm_only = {}

    try:
        entries = sorted(os.listdir(root_dir))
    except OSError as e:
        logger.warning("Unable to read hwmon root %s: %s", root_dir, e)
        return {}, {}

    for entry in entries:
        full_path = os.path.join(root_dir, entry)
        if not os.path.isdir(full_path):
            continue

        try:
            files = sorted(os.listdir(full_path))
        except OSError as e:
            logger.warning("Unable to read hwmon node %s: %s", full_path, e)
            continue

        name = _read_name(full_path, entry)

        fan_device_paths = []
        fan_enable_paths = []
        fan_rpm_path = []

        for file in files:
            file_path = os.path.join(full_path, file)

            if FAN_PWM_RE.match(file) or file == 'target_pwm':
                fan_device_paths.append(file_path)
            elif FAN_PWM_ENABLE_RE.match(file):
                fan_enable_paths.append(file_path)
            elif file in ('rpm', 'rpm_measured', 'fan1_input'):
                fan_rpm_path.append(file_path)

        if fan_device_paths:
            pwm_files[name] = {
                'path': full_path,
                'pwm': fan_device_paths,
                'hwmon_name': name,
                'of_node': _readlink_safe(os.path.join(full_path, 'of_node')),
                'device': _readlink_safe(os.path.join(full_path, 'device')),
            }
            if fan_enable_paths:
                pwm_files[name]['pwm_enable'] = fan_enable_paths
            if fan_rpm_path:
                pwm_files[name]['rpm'] = fan_rpm_path

            logger.info("Fan %s(%d) found in %s", name, len(fan_device_paths), full_path)
            if fan_rpm_path:
                logger.info("RPM %s(%d) found in %s", name, len(fan_rpm_path), full_path)

        elif fan_rpm_path:
            rpm_only[name] = {
                'path': full_path,
                'rpm': fan_rpm_path,
                'hwmon_name': name,
                'of_node': _readlink_safe(os.path.join(full_path, 'of_node')),
                'device': _readlink_safe(os.path.join(full_path, 'device')),
            }
            logger.info("Standalone RPM %s(%d) found in %s", name, len(fan_rpm_path), full_path)

    return pwm_files, rpm_only


def _merge_split_fans(pwm_files, rpm_only):
    if not pwm_files or not rpm_only:
        return pwm_files

    unmatched_rpm = dict(rpm_only)

    # First try to match by shared of_node or device path.
    for fan_name, fan_data in pwm_files.items():
        if 'rpm' in fan_data:
            continue

        best_match = None
        fan_of_node = fan_data.get('of_node', '')
        fan_device = fan_data.get('device', '')

        for rpm_name, rpm_data in unmatched_rpm.items():
            rpm_of_node = rpm_data.get('of_node', '')
            rpm_device = rpm_data.get('device', '')

            if fan_of_node and rpm_of_node and fan_of_node == rpm_of_node:
                best_match = rpm_name
                break
            if fan_device and rpm_device and fan_device == rpm_device:
                best_match = rpm_name
                break

        if best_match is not None:
            fan_data['rpm'] = unmatched_rpm[best_match]['rpm']
            fan_data['rpm_path'] = unmatched_rpm[best_match]['path']
            logger.info("Matched split RPM node %s -> fan %s by topology", best_match, fan_name)
            del unmatched_rpm[best_match]

    # Thor fallback: one PWM fan and one standalone RPM node.
    if is_thor() and len(pwm_files) == 1 and len(unmatched_rpm) == 1:
        fan_name = next(iter(pwm_files))
        rpm_name = next(iter(unmatched_rpm))
        if 'rpm' not in pwm_files[fan_name]:
            pwm_files[fan_name]['rpm'] = unmatched_rpm[rpm_name]['rpm']
            pwm_files[fan_name]['rpm_path'] = unmatched_rpm[rpm_name]['path']
            logger.info("Matched Thor split RPM node %s -> fan %s", rpm_name, fan_name)
            del unmatched_rpm[rpm_name]

    # Generic fallback: if still exactly one of each, merge them.
    if len(pwm_files) == 1 and len(unmatched_rpm) == 1:
        fan_name = next(iter(pwm_files))
        rpm_name = next(iter(unmatched_rpm))
        if 'rpm' not in pwm_files[fan_name]:
            pwm_files[fan_name]['rpm'] = unmatched_rpm[rpm_name]['rpm']
            pwm_files[fan_name]['rpm_path'] = unmatched_rpm[rpm_name]['path']

def _merge_split_fans(pwm_files, rpm_only):
    if not pwm_files or not rpm_only:
        return pwm_files

    unmatched_rpm = dict(rpm_only)

    # First try to match by shared of_node or device path.
    for fan_name, fan_data in pwm_files.items():
        if 'rpm' in fan_data:
            continue

        best_match = None
        fan_of_node = fan_data.get('of_node', '')
        fan_device = fan_data.get('device', '')

        for rpm_name, rpm_data in unmatched_rpm.items():
            rpm_of_node = rpm_data.get('of_node', '')
            rpm_device = rpm_data.get('device', '')

            if fan_of_node and rpm_of_node and fan_of_node == rpm_of_node:
                best_match = rpm_name
                break
            if fan_device and rpm_device and fan_device == rpm_device:
                best_match = rpm_name
                break

        if best_match is not None:
            fan_data['rpm'] = unmatched_rpm[best_match]['rpm']
            fan_data['rpm_path'] = unmatched_rpm[best_match]['path']
            logger.info("Matched split RPM node %s -> fan %s by topology", best_match, fan_name)
            del unmatched_rpm[best_match]

    # Thor fallback: one PWM fan and one standalone RPM node.
    if is_thor() and len(pwm_files) == 1 and len(unmatched_rpm) == 1:
        fan_name = next(iter(pwm_files))
        rpm_name = next(iter(unmatched_rpm))
        if 'rpm' not in pwm_files[fan_name]:
            pwm_files[fan_name]['rpm'] = unmatched_rpm[rpm_name]['rpm']
            pwm_files[fan_name]['rpm_path'] = unmatched_rpm[rpm_name]['path']
            logger.info("Matched Thor split RPM node %s -> fan %s", rpm_name, fan_name)
            del unmatched_rpm[rpm_name]

    # Generic fallback: if still exactly one of each, merge them.
    if len(pwm_files) == 1 and len(unmatched_rpm) == 1:
        fan_name = next(iter(pwm_files))
        rpm_name = next(iter(unmatched_rpm))
        if 'rpm' not in pwm_files[fan_name]:
            pwm_files[fan_name]['rpm'] = unmatched_rpm[rpm_name]['rpm']
            pwm_files[fan_name]['rpm_path'] = unmatched_rpm[rpm_name]['path']
            logger.info("Matched split RPM node %s -> fan %s by single-device fallback", rpm_name, fan_name)
            del unmatched_rpm[rpm_name]

    for rpm_name, rpm_data in unmatched_rpm.items():
        logger.warning(
            "Unmatched RPM-only hwmon node %s at %s",
            rpm_name,
            rpm_data.get('path', '<unknown>'),
        )

    return pwm_files


def get_all_cooling_system(root_dir):
    if not os.path.isdir(root_dir):
        logger.error("Folder %s doesn't exist", root_dir)
        return {}

    pwm_files, rpm_only = _collect_hwmon_fans(root_dir)
    pwm_files = _merge_split_fans(pwm_files, rpm_only)
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
    # Find all commands
    fan_device_paths = []
    fan_rpm_path = []
    for file in os.listdir(root_path):
        if file == 'target_pwm':
            fan_device_paths += [os.path.join(root_path, file)]
        elif file in ('rpm', 'rpm_measured', 'fan1_input'):
            fan_rpm_path += [os.path.join(root_path, file)]
    if fan_device_paths:
        pwm_files[name] = {'path': root_path, 'pwm': fan_device_paths}
        logger.info("Found legacy FAN %s(%d) found in %s", name, len(fan_device_paths), root_path)
    if fan_rpm_path and name in pwm_files:
        pwm_files[name]['rpm'] = fan_rpm_path
        logger.info("Legacy RPM %s(%d) found in %s", name, len(fan_rpm_path), root_path)
    return pwm_files


def nvfancontrol_query():
    status = {}
    try:
        nvpmodel_p = Command(['nvfancontrol', '-q'])
        lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
        for line in lines:
            values = [v.strip() for v in line.split(':')]
            if len(values) < 3:
                continue
            fan_name = values[0].lower()
            query = values[1].replace("FAN_", "").lower()
            if fan_name not in status:
                status[fan_name] = {}
            status[fan_name][query] = values[2]
    except (OSError, Command.CommandException):
        pass
    return status


def _nvfancontrol_paths():
    path = "/etc/nvfancontrol.conf"
    return path if os.path.isfile(path) else ""


def decode_nvfancontrol():
    nvfan = {}
    current_fan = ''
    conf_path = _nvfancontrol_paths()
    if conf_path:
        with open(conf_path, 'r') as fp:
            for line in fp:
                stripped = line.strip()
                match_name = re.search(FAN_NVFAN_NAME_RE, stripped)
                match_values = re.search(FAN_NVFAN_OPTIONS_RE, stripped)
                match_kickstart = re.search(FAN_KICKSTART_RE, stripped)

                if match_name:
                    parsed_line = match_name.groupdict()
                    current_fan = 'fan{num}'.format(num=parsed_line['num'])
                    nvfan[current_fan] = {}
                elif current_fan and match_values:
                    parsed_line = match_values.groupdict()
                    type_name = parsed_line['type'].lower()
                    if type_name not in nvfan[current_fan]:
                        nvfan[current_fan][type_name] = []
                    nvfan[current_fan][type_name] += [parsed_line['value']]
                elif current_fan and match_kickstart:
                    nvfan[current_fan]['kickstart_pwm'] = int(match_kickstart.group('value'))
    return nvfan


def change_nvfancontrol_default(name, value):
    conf_path = _nvfancontrol_paths()
    if not conf_path:
        return
    with open(conf_path, "r") as f:
        lines = f.readlines()
    with open(conf_path, "w") as f:
        for line in lines:
            match_defaults = re.search(FAN_NVFAN_DEFAULT_RE, line.strip())
            if match_defaults:
                parsed_line = match_defaults.groupdict()
                if name.upper() == parsed_line['type']:
                    line = line.replace(parsed_line['value'], value)
            f.write(line)


def nvfancontrol_is_active():
    try:
        output = Command.run_command(['systemctl', 'status', 'nvfancontrol.service'])
        return 'Active: active' in '\n'.join(output)
    except Command.CommandException:
        return False


def _merge_nvfan_metadata(fan_list, nv_fan_modes):
    if not fan_list or not nv_fan_modes:
        return

    # If there is only one discovered fan and one nvfancontrol fan, pair directly.
    if len(fan_list) == 1 and len(nv_fan_modes) == 1:
        fan_name = next(iter(fan_list))
        nv_name = next(iter(nv_fan_modes))
        fan_list[fan_name].update(nv_fan_modes[nv_name])
        if 'profile' in fan_list[fan_name] and FAN_MANUAL_NAME not in fan_list[fan_name]['profile']:
            fan_list[fan_name]['profile'] += [FAN_MANUAL_NAME]
        return

    # Prefer exact key matches if names line up.
    for fan_name in fan_list:
        if fan_name in nv_fan_modes:
            fan_list[fan_name].update(nv_fan_modes[fan_name])
            if 'profile' in fan_list[fan_name] and FAN_MANUAL_NAME not in fan_list[fan_name]['profile']:
                fan_list[fan_name]['profile'] += [FAN_MANUAL_NAME]

    # Fallback to positional pairing only for any still-unmatched fans.
    remaining_fans = [f for f in fan_list if 'profile' not in fan_list[f]]
    remaining_nv = [n for n in nv_fan_modes if n not in fan_list]
    for fan_name, nv_name in zip(remaining_fans, remaining_nv):
        fan_list[fan_name].update(nv_fan_modes[nv_name])
        if 'profile' in fan_list[fan_name] and FAN_MANUAL_NAME not in fan_list[fan_name]['profile']:
            fan_list[fan_name]['profile'] += [FAN_MANUAL_NAME]


class Fan(GenericInterface):
    """
    This class enable to control your fan or set of fan.
    Please read the documentation on :py:attr:`~jtop.jtop.fan`
    """

    def __init__(self):
        super(Fan, self).__init__()

    def all_profiles(self, name):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._init[name]

    def set_profile(self, name, profile):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if profile not in self.all_profiles(name):
            all_profiles = ' '.join(self.all_profiles(name))
            raise JtopException("Profile \"{profile}\" does not exist for Fan \"{name}\". Available: {all_profiles}".format(
                profile=profile, name=name, all_profiles=all_profiles))
        if profile == self._data[name]['profile']:
            return
        self._controller.put({'fan': {'command': 'profile', 'name': name, 'profile': profile}})

    def get_profile(self, name):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._data[name]['profile']

    def get_profile_default(self, name):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._init[name][0]

    @property
    def profile(self):
        if len(self._data) > 0:
            name = list(self._data.keys())[0]
            return self.get_profile(name)
        return None

    @profile.setter
    def profile(self, value):
        if len(self._data) > 0:
            name = list(self._data.keys())[0]
            self.set_profile(name, value)

    def set_speed(self, name, speed, idx=0):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if idx >= len(self._data[name]['speed']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['speed'])))
        if speed == self._data[name]['speed'][idx]:
            return
        self._controller.put({'fan': {'command': 'speed', 'name': name, 'speed': speed, 'idx': idx}})

    def get_speed(self, name, idx=0):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if idx >= len(self._data[name]['speed']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['speed'])))
        return self._data[name]['speed'][idx]

    @property
    def speed(self):
        if len(self._data) > 0:
            name = list(self._data.keys())[0]
            return_value = self.get_speed(name)
            return return_value
        return None

    @speed.setter
    def speed(self, value):
        if len(self._data) > 0:
            name = list(self._data.keys())[0]
            self.set_speed(name, value)

    def get_rpm(self, name, idx=0):
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if 'rpm' not in self._data[name]:
            raise JtopException("Fan \"{name}\" doesn't have RPM".format(name=name))
        if idx >= len(self._data[name]['rpm']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['rpm'])))
        return self._data[name]['rpm'][idx]

    @property
    def rpm(self):
        if len(self._data) > 0:
            name = list(self._data.keys())[0]
            return self.get_rpm(name)
        return None


def check_config(config):
    if 'fan' not in config:
        return
    fans = config.get('fan')
    for fan in fans:
        if not isinstance(fans[fan], dict):
            logger.warning("Old fan configuration store. Cleaned")
            config.set('fan', {})
        else:
            if 'speed' in fans[fan]:
                if not isinstance(fans[fan]['speed'], list):
                    logger.warning("Old speed configuration store. Cleaned")
                    config.set('fan', {})


class FanService(object):

    def __init__(self, config):
        self._config = config
        check_config(config)

        root_dir = "/sys/class/hwmon"
        if os.getenv('JTOP_TESTING', False):
            root_dir = "/fake_sys/class/hwmon"
            logger.warning("Running in JTOP_TESTING folder=%s", root_dir)

        self._fan_list = get_all_cooling_system(root_dir)
        self._fan_list.update(get_all_legacy_fan())

        self._nvfancontrol = os.path.isfile('/etc/systemd/system/nvfancontrol.service') or os.path.islink('/etc/systemd/system/nvfancontrol.service')

        if self._nvfancontrol:
            logger.info("Found nvfancontrol.service")
            nv_fan_modes = decode_nvfancontrol()
            _merge_nvfan_metadata(self._fan_list, nv_fan_modes)
        else:
            for name, fan in self._fan_list.items():
                self._fan_list[name]['profile'] = []
                control = os.path.join(fan['path'], FAN_TEMP_CONTROL_NAME)
                if os.path.isfile(control):
                    self._fan_list[name]['control'] = control
                    self._fan_list[name]['profile'] += [FAN_TEMP_CONTROL_NAME]
                    logger.info("Fan temp controller %s found in %s", name, control)
                self._fan_list[name]['profile'] += [FAN_MANUAL_NAME]

        if not self._fan_list:
            logger.warning("No fan found")

    def initialization(self):
        fan_config = self._config.get('fan', {})
        for name, fan in fan_config.items():
            if 'profile' in fan:
                profile = fan['profile']
                logger.info("Initialization %s", name)
                self.set_profile(name, profile)
                if profile == FAN_MANUAL_NAME and 'speed' in fan:
                    speed, index = fan['speed']
                    self.set_speed(name, speed, index)
                    logger.info("Initialization %s %s speed %s%%", name, index, speed)

    def get_configs(self):
        governors = {}
        for fan, data in self._fan_list.items():
            governors[fan] = data['profile']
        return governors

    def get_profile(self, name):
        if name not in self._fan_list:
            logger.error("Fan \"%s\" does not exist", name)
            return ""
        profile = FAN_MANUAL_NAME
        if self._nvfancontrol:
            if nvfancontrol_is_active():
                nvfan_query = nvfancontrol_query()
                if len(self._fan_list) == 1 and len(nvfan_query) == 1:
                    only = next(iter(nvfan_query))
                    return nvfan_query[only].get('profile', FAN_MANUAL_NAME)
                if name in nvfan_query:
                    return nvfan_query[name].get('profile', FAN_MANUAL_NAME)
        else:
            if 'control' in self._fan_list[name]:
                control_value = int(cat(self._fan_list[name]['control'])) == 1
                return FAN_TEMP_CONTROL_NAME if control_value else FAN_MANUAL_NAME
        return profile

    def set_profile(self, name, profile):
        if name not in self._fan_list:
            logger.error("Fan \"%s\" does not exist", name)
            return False
        if profile == self.get_profile(name):
            logger.warning("Fan %s profile %s already active", name, profile)
            return True
        if self._nvfancontrol:
            is_active = nvfancontrol_is_active()
            if profile in self._fan_list[name]['profile']:
                if profile == FAN_MANUAL_NAME:
                    if is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Profile set %s", profile)
                else:
                    if is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Stop nvfancontrol service")
                    change_nvfancontrol_default('profile', profile)
                    logger.info("Change nvfancontrol profile to %s", profile)
                    if os.path.isfile("/var/lib/nvfancontrol/status"):
                        os.remove("/var/lib/nvfancontrol/status")
                        logger.info("Removed /var/lib/nvfancontrol/status")
                    os.system('systemctl start nvfancontrol')
                    logger.info("Restart nvfancontrol with profile \"%s\"", profile)
            else:
                logger.error("Profile %s doesn't exist", profile)
                return False
        else:
            if profile in self._fan_list[name]['profile']:
                control_value = "0" if profile == FAN_MANUAL_NAME else "1"
                if 'control' in self._fan_list[name]:
                    control = self._fan_list[name]['control']
                    if os.access(control, os.W_OK):
                        with open(control, 'w') as f:
                            f.write(control_value)
                    logger.info("Profile set %s", profile)
            else:
                logger.error("Profile %s doesn't exist", profile)
                return False

        fan_config = self._config.get('fan', {})
        if name not in fan_config:
            fan_config[name] = {}
        fan_config[name]['profile'] = profile
        self._config.set('fan', fan_config)
        return True

    def set_speed(self, name, speed, index):
        if name not in self._fan_list:
            logger.error("This fan %s doesn't exist", name)
            return
        if index >= len(self._fan_list[name]['pwm']):
            logger.error("Wrong index %s for %s", index, name)
            return

        fan_config = self._config.get('fan', {})
        if name not in fan_config:
            fan_config[name] = {}
        fan_config[name]['speed'] = (speed, index)
        self._config.set('fan', fan_config)

        pwm = ValueToPWM(speed)
        pwm_path = self._fan_list[name]['pwm'][index]
        try:
            if os.access(pwm_path, os.W_OK):
                with open(pwm_path, 'w') as f:
                    f.write(str(pwm))
        except OSError as e:
            logger.error("I cannot set fan speed: %s - error %s", speed, e)

    def get_status(self):
        fan_status = {}
        for name, data in self._fan_list.items():
            fan_status[name] = {
                'speed': [PWMtoValue(float(cat(pwm))) for pwm in data['pwm']],
            }
            if 'rpm' in data:
                fan_status[name]['rpm'] = [int(cat(rpm)) for rpm in data['rpm']]
            if 'pwm_enable' in data:
                try:
                    fan_status[name]['pwm_enable'] = [int(cat(p)) for p in data['pwm_enable']]
                except (TypeError, ValueError):
                    pass
            if 'kickstart_pwm' in data:
                fan_status[name]['kickstart_pwm'] = data['kickstart_pwm']

        if self._nvfancontrol:
            nvfan_query = {}
            if nvfancontrol_is_active():
                nvfan_query = nvfancontrol_query()

            if nvfan_query:
                if len(fan_status) == 1 and len(nvfan_query) == 1:
                    fan_name = next(iter(fan_status))
                    nv_name = next(iter(nvfan_query))
                    fan_status[fan_name].update(nvfan_query[nv_name])
                else:
                    for fan_name in fan_status:
                        if fan_name in nvfan_query:
                            fan_status[fan_name].update(nvfan_query[fan_name])
                        else:
                            fan_status[fan_name]['profile'] = FAN_MANUAL_NAME
            else:
                for fan in fan_status:
                    fan_status[fan]['profile'] = FAN_MANUAL_NAME
        else:
            for name, data in self._fan_list.items():
                if 'control' in data:
                    control_value = int(cat(data['control'])) == 1
                    fan_status[name]['profile'] = FAN_TEMP_CONTROL_NAME if control_value else FAN_MANUAL_NAME
                else:
                    fan_status[name]['profile'] = FAN_MANUAL_NAME
        return fan_status
