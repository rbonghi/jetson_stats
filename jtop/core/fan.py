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
from .exceptions import JtopException
# Logging
import logging
# Compile decoder PWM table
FAN_PWM_TABLE_RE = re.compile(r'\((.*?)\)')
# Create logger
logger = logging.getLogger(__name__)


def load_table(path):
    table = []
    with open(path + "pwm_rpm_table", 'r') as fp:
        title = []
        for line in fp.readlines():
            match = FAN_PWM_TABLE_RE.search(line)
            line = [tab.strip() for tab in match.group(1).split(",")]
            if title:
                table += [{title[idx]: val for idx, val in enumerate(line) if idx > 0}]
            else:
                title = line
    return table


def locate_fan():
    for fan in ['/sys/kernel/debug/tegra_fan/', '/sys/devices/pwm-fan/']:
        if os.path.isdir(fan):
            logger.info("Fan folder in {}".format(fan))
            return fan
    raise JtopException("No Fans availabe on this board")


# Fan configurations
CONFIGS = ["jetson_clocks", "manual", "system"]


class Fan(object):

    def __init__(self, controller):
        self._controller = controller
        self._status = {}

    def set(self, value):
        if not self._status["status"]:
            raise JtopException("Fan does not exist")

    def mode(self, mode):
        if mode not in CONFIGS:
            raise JtopException("Control does not available")

    def _update(self, status):
        self._status = status
        # Load status as a dictionary
        self.__dict__.update(**self._status)

    def _init(self, controller):
        self._controller = controller

    def __repr__(self):
        return str(self._status)


class FanService(object):

    def __init__(self, config):
        # Configuration
        self.config = config
        # Initialize number max records to record
        self.path = locate_fan()
        # Init status fan
        self.isRPM = os.path.isfile(self.path + "rpm_measured")
        self.isCPWM = os.path.isfile(self.path + "cur_pwm")
        self.isTPWM = os.path.isfile(self.path + "target_pwm")
        self.isCTRL = os.path.isfile(self.path + "temp_control")
        # Initialize dictionary status
        self._status = {}
        # Max value PWM
        self._pwm_cap = float(self.read_status("pwm_cap")) if os.path.isfile(self.path + "pwm_cap") else 255
        # PWM RPM table
        self.table = load_table(self.path) if os.path.isfile(self.path + "pwm_rpm_table") else {}
        # Step time
        self._status["step"] = int(self.read_status("step_time")) if os.path.isfile(self.path + "step_time") else 0
        # Status FAN
        self._status["status"] = os.path.isfile(self.path + "target_pwm")

    @property
    def speed(self):
        return self._status.get("tpwm", 0)

    @speed.setter
    def speed(self, value):
        if not isinstance(value, float):
            raise ValueError("Need a float number")
        # Check limit speed
        if value < 0.0 or value > 1.0:
            raise ValueError("Wrong speed, number between [0, 1]")
        # Convert in PWM
        pwm = self._ValueToPWM(value)
        # Write PWM value
        with open(self.path + "target_pwm", 'w') as f:
            f.write(str(pwm))

    @property
    def auto(self):
        return self._status.get("ctrl", False)

    @auto.setter
    def auto(self, value):
        if not isinstance(value, bool):
            raise ValueError("Need a boolean")
        # Check limit speed
        value = 1 if value else 0
        # Write status control value
        with open(self.path + "temp_control", 'w') as f:
            f.write(str(value))

    def _PWMtoValue(self, pwm):
        return pwm / self._pwm_cap

    def _ValueToPWM(self, value):
        return ceil(self._pwm_cap * value)

    def update(self):
        # Control temperature
        if self.isCTRL:
            temperature_control = self.read_status("temp_control")
            logger.debug('{} status temperature_control {}'.format(self.path, temperature_control))
            self._status["ctrl"] = bool(temperature_control)
        # Read PWM
        if self.isTPWM:
            fan_level = self._PWMtoValue(self.read_status("target_pwm"))
            logger.debug('{} status PWM CTRL {}'.format(self.path, fan_level))
            self._status["tpwm"] = fan_level
        # Read current
        if self.isCPWM:
            fan_level = self._PWMtoValue(self.read_status("cur_pwm"))
            logger.debug('{} status PWM CUR {}'.format(self.path, fan_level))
            self._status["cpwm"] = fan_level
        # Read RPM fan
        if self.isRPM:
            rpm_measured = self.read_status("rpm_measured")
            logger.debug('{} status RPM {}'.format(self.path, rpm_measured))
            self._status["rpm"] = int(rpm_measured)
        return self._status

    def read_status(self, file_read):
        with open(self.path + file_read, 'r') as f:
            return f.read()
        return None
# EOF
