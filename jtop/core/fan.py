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
# Logging
import logging
# Launch command
from .command import Command
from .common import cat, GenericInterface
from .exceptions import JtopException
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


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    return int(value * pwm_cap / 100)


def PWMtoValue(value, pwm_cap=FAN_PWM_CAP):
    return float(value * 100 / pwm_cap)


def get_all_rpm_system(root_dir):
    pwm_files = {}
    for dir in os.listdir(root_dir):
        full_path = os.path.join(root_dir, dir)
        if os.path.isdir(full_path):
            # Find all pwm in folder
            for file in os.listdir(full_path):
                if 'rpm' == file:
                    name_file = os.path.join(full_path, 'name')
                    name = cat(name_file).strip() if os.path.isfile(name_file) else dir
                    pwm_files[name] = os.path.join(full_path, file)
                    logger.info("RPM {name} found in {root_path}".format(name=name, root_path=full_path))
    return pwm_files


def get_all_cooling_system(root_dir):
    pwm_files = {}
    if not os.path.isdir(root_dir):
        logger.error("Folder {root_dir} doesn't exist".format(root_dir=root_dir))
        return pwm_files
    # Fin all fans
    for dir in os.listdir(root_dir):
        full_path = os.path.join(root_dir, dir)
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
    rpm_list = get_all_rpm_system(root_dir)
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
    # Find all commands
    fan_device_paths = []
    fan_rpm_path = []
    for file in os.listdir(root_path):
        if file == 'target_pwm':
            fan_device_paths += [os.path.join(root_path, file)]
        # Check if there are rpm values
        elif file == 'rpm_measured':
            fan_rpm_path += [os.path.join(root_path, file)]
    # If there are pwm is added in list
    if fan_device_paths:
        pwm_files[name] = {'path': root_path, 'pwm': fan_device_paths}
        logger.info("Found legacy FAN {name}({num}) found in {root_path}".format(name=name, root_path=root_path, num=len(fan_device_paths)))
    if fan_rpm_path:
        pwm_files[name]['rpm'] = fan_rpm_path
        logger.info("Legacy RPM {name}({num}) found in {root_path}".format(name=name, root_path=root_path, num=len(fan_device_paths)))
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


def nvfancontrol_is_active():
    try:
        output = Command.run_command(['systemctl', 'status', 'nvfancontrol.service'])
        return 'Active: active' in '\n'.join(output)
    except Command.CommandException:
        return False


class Fan(GenericInterface):
    """
    This class enable to control your fan or set of fan.
    Please read the documentation on :py:attr:`~jtop.jtop.fan`

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                jetson.fan.set_profile("tegra_fan", "manual")

    Below all methods available using the :py:attr:`~jtop.jtop.fan` attribute
    """

    def __init__(self):
        super(Fan, self).__init__()
        # list of all profiles in self._init (check services)

    def all_profiles(self, name):
        """
        Return a list of all profiles available for a fan.

        * **Before** Jetpack 5
            * temp_control
            * manual
        * **After** Jetpack 5  jtop map `nvfancontrol <https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#fan-profile-control>`_
            * Quiet
            * Cool
            * Manual (Stop nvfancontrol service)

        All fan are always with `Manual` profile option.

        :param name: Name of Fan
        :type name: str
        :raises JtopException: Fan name doesn't exist
        :return: List of all profiles available
        :rtype: list
        """  # noqa
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._init[name]

    def set_profile(self, name, profile):
        """
        Set a new profile for a fan.
        Check which profile is available with :py:func:`~all_profiles`.

        :param name: Name of Fan
        :type name: str
        :param profile: Profile name
        :type profile: str
        :raises JtopException: Fan name doesn't exist or wrong profile
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if profile not in self.all_profiles(name):
            all_profiles = ' '.join(self.all_profiles(name))
            raise JtopException("Profile \"{profile}\" does not exist for Fan \"{name}\". Available: {all_profiles}".format(
                profile=profile, name=name, all_profiles=all_profiles))
        # Skip if the new profile is the same of the previous
        if profile == self._data[name]['profile']:
            return
        # Set new fan profile
        self._controller.put({'fan': {'command': 'profile', 'name': name, 'profile': profile}})

    def get_profile(self, name):
        """
        Return the current profile is enabled on fan. This value is also readable from :py:attr:`~jtop.jtop.fan`.

        :param name: Name of Fan
        :type name: str
        :raises JtopException: Fan name doesn't exist
        :return: fan profile name
        :rtype: str
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._data[name]['profile']

    def get_profile_default(self, name):
        """
        Get the default profile for this fan. Usually is the first profile listed in :py:func:`~all_profiles`

        :param name: Name of Fan
        :type name: str
        :raises JtopException: Fan name doesn't exist
        :return: profile default name
        :rtype: str
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        return self._init[name][0]

    @property
    def profile(self):
        """
        This property show the current profile selected on first fan on your board.
        This is a simplified version of :py:func:`~set_profile` where *name* is the first fan listed.

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Print profile
                    print(jetson.fan.profile)
                    # Set new profile
                    jetson.fan.profile = 'quiet'

        :return: current profile in fan
        :rtype: str
        """
        # Return first fan name and get speed
        if len(self._data) > 0:
            # Extract first name
            name = list(self._data.keys())[0]
            # Get profile
            return self.get_profile(name)
        return None

    @profile.setter
    def profile(self, value):
        if len(self._data) > 0:
            # Extract first name
            name = list(self._data.keys())[0]
            # Set speed for first fan
            self.set_profile(name, value)

    def set_speed(self, name, speed, idx=0):
        """
        Set a new speed for a selected fan.

        :param name: Name of Fan
        :type name: str
        :param speed: New speed value, a number between [0, 100]
        :type speed: float
        :param idx: Index fan, defaults to 0
        :type idx: int, optional
        :raises JtopException: Fan name doesn't exist or wrong index
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if idx >= len(self._data[name]['speed']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['speed'])))
        # Skip if the new profile is the same of the previous
        if speed == self._data[name]['speed'][idx]:
            return
        # Set new fan speed
        self._controller.put({'fan': {'command': 'speed', 'name': name, 'speed': speed, 'idx': idx}})

    def get_speed(self, name, idx=0):
        """
        Return for a selected Fan and index the current speed.
        This value is also readable from :py:attr:`~jtop.jtop.fan`.

        :param name: Name of Fan
        :type name: str
        :param idx: Index fan, defaults to 0
        :type idx: int, optional
        :raises JtopException: Fan name doesn't exist or wrong index
        :return: fan speed a number between [0, 100]
        :rtype: int
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if idx >= len(self._data[name]['speed']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['speed'])))
        return self._data[name]['speed'][idx]

    @property
    def speed(self):
        """
        This property show the current speed between [0, 100] on first fan on your board.
        This is a simplified version of :py:func:`~set_speed` where *name* is the first fan listed.

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read speed
                    print(jetson.fan.speed)
                    # Set new speed
                    jetson.fan.speed = 90

        :return: current fan speed
        :rtype: float
        """
        # Return first fan name and get speed
        if len(self._data) > 0:
            # Extract first name
            name = list(self._data.keys())[0]
            return_value = self.get_speed(name)
            # Return first speed
            return return_value
        return None

    @speed.setter
    def speed(self, value):
        if len(self._data) > 0:
            # Extract first name
            name = list(self._data.keys())[0]
            # Set speed for first fan
            self.set_speed(name, value)

    def get_rpm(self, name, idx=0):
        """
        This method return RPM fan. This output is always available on all Jetson.
        This value is also readable from :py:attr:`~jtop.jtop.fan`.

        :param name: Name of Fan
        :type name: str
        :param idx: Index fan, defaults to 0
        :type idx: int, optional
        :raises JtopException: Fan name doesn't exist, rpm doesn't exist or wrong index
        :return: RPM value
        :rtype: int
        """
        if name not in self._data:
            raise JtopException("Fan \"{name}\" does not exist".format(name=name))
        if 'rpm' not in self._data[name]:
            raise JtopException("Fan \"{name}\" doesn't have RPM".format(name=name))
        if idx >= len(self._data[name]['rpm']) or idx < 0:
            raise JtopException("Fan \"{name}\" have only {len} fans".format(name=name, len=len(self._data[name]['rpm'])))
        return self._data[name]['rpm'][idx]

    @property
    def rpm(self):
        """
        This property show the current fan selected on first fan on your board.

        .. note::

            You can only read RPM, but **not** set a new speed

        You cannot set a new RPM value

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read RPM
                    print(jetson.fan.rpm)

        :return: rpm first fan
        :rtype: int
        """
        # Return first fan name and get speed
        if len(self._data) > 0:
            # Extract first name
            name = list(self._data.keys())[0]
            # Return first speed
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
        # Load configuration
        self._config = config
        # Check consistency fan
        check_config(config)
        # Load base hwmon folder
        root_dir = "/sys/class/hwmon"
        if os.getenv('JTOP_TESTING', False):
            root_dir = "/fake_sys/class/hwmon"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=root_dir))
        # Find all fan available
        self._fan_list = get_all_cooling_system(root_dir)
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
            logger.warning("No fan found")

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
        if name not in self._fan_list:
            logger.error("Fan \"{name}\" does not exist".format(name=name))
            return ""
        profile = FAN_MANUAL_NAME
        if self._nvfancontrol:
            if nvfancontrol_is_active():
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
        if name not in self._fan_list:
            logger.error("Fan \"{name}\" does not exist".format(name=name))
            return False
        # Check current status before change
        if profile == self.get_profile(name):
            logger.warning("Fan {name} profile {profile} already active".format(name=name, profile=profile))
            return True
        if self._nvfancontrol:
            is_active = nvfancontrol_is_active()
            # Check first if the fan control is active and after enable the service
            if profile in self._fan_list[name]['profile']:
                if profile == FAN_MANUAL_NAME:
                    if is_active:
                        os.system('systemctl stop nvfancontrol')
                        logger.info("Profile set {profile}".format(profile=profile))
                else:
                    # Check if active and stop
                    if is_active:
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
                    logger.info("Restart nvfancontrol With profile: \"{profile}\"".format(profile=profile))
            else:
                logger.error("Profile {profile} doesn't exist".format(profile=profile))
                return False
        else:
            if profile in self._fan_list[name]['profile']:
                control_value = "0" if profile == FAN_MANUAL_NAME else "1"
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
        # Update configuration on board
        fan_config = self._config.get('fan', {})
        # Set new profile
        if name not in fan_config:
            fan_config[name] = {}
        fan_config[name]['speed'] = (speed, index)
        # Set new jetson_clocks configuration
        self._config.set('fan', fan_config)
        # Convert in PWM
        pwm = ValueToPWM(speed)
        # Set for all pwm the same speed value
        pwm_path = self._fan_list[name]['pwm'][index]
        try:
            if os.access(pwm_path, os.W_OK):
                with open(pwm_path, 'w') as f:
                    f.write(str(pwm))
        except OSError as e:
            logger.error("I cannot set fan speed: {speed} - error {e}".format(speed=speed, e=e))

    def get_status(self):
        fan_status = {}
        # Read all fan status
        for name, data in self._fan_list.items():
            # Read pwm from all fan
            fan_status[name] = {
                'speed': [PWMtoValue(float(cat(pwm))) for pwm in data['pwm']],
            }
            if 'rpm' in data:
                fan_status[name]['rpm'] = [int(cat(rpm)) for rpm in data['rpm']]
        # Check status fan control
        if self._nvfancontrol:
            nvfan_query = {}
            if nvfancontrol_is_active():
                nvfan_query = nvfancontrol_query()
            if nvfan_query:
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
                else:
                    fan_status[name]['profile'] = FAN_MANUAL_NAME
        return fan_status
# EOF
