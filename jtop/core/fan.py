# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
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
# Logging
import logging
# Compile decoder PWM table
FAN_PWM_TABLE_RE = re.compile(r'\((.*?)\)')

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def load_table(path):
    table = []
    with open(path + "pwm_rpm_table", 'r') as fp:
        title = []
        for line in fp.readlines():
            match = FAN_PWM_TABLE_RE.search(line)
            line = [l.strip() for l in match.group(1).split(",")]
            if title:
                table += [{title[idx]: val for idx, val in enumerate(line) if idx > 0}]
            else:
                title = line
    return table


class Fan(object):

    class FanException(Exception):
        pass

    def __init__(self, path):
        # Initialize number max records to record
        self.path = path
        # Check exist path
        if not os.path.isdir(path):
            raise Fan.FanException("Fan does not exist")
        # Init status fan
        self._status = {}
        self.isRPM = os.path.isfile(self.path + "rpm_measured")
        self.isCPWM = os.path.isfile(self.path + "cur_pwm")
        self.isTPWM = os.path.isfile(self.path + "target_pwm")
        # Max value PWM
        self._status["cap"] = int(self.read_status("pwm_cap")) if os.path.isfile(self.path + "pwm_cap") else 255
        # PWM RPM table
        self.table = load_table(self.path) if os.path.isfile(self.path + "pwm_rpm_table") else {}
        # Step time
        self._status["step"] = int(self.read_status("step_time")) if os.path.isfile(self.path + "step_time") else 0
        # Control temperature
        self._status["temp"] = int(self.read_status("temp_control")) if os.path.isfile(self.path + "temp_control") else 0
        # Status FAN
        if os.path.isfile(self.path + "target_pwm"):
            self._status["status"] = 'ON'
        elif os.getuid() != 0:
            self._status["status"] = 'REQUIRE SUDO'
        else:
            self._status["status"] = 'OFF'
        # Run first time update status fan
        self.update()

    @property
    def speed(self):
        return self._status.get("tpwm", 0)

    @speed.setter
    def speed(self, value):
        # Check limit speed
        if os.access(self.path + "target_pwm", os.W_OK):
            value = 100.0 if value > 100.0 else value
            value = 0 if value < 0 else value
            # Convert in PWM value
            pwm = ceil(self._status["cap"] * value / 100.0)
            # Write PWM value
            with open(self.path + "target_pwm", 'w') as f:
                f.write(str(pwm))

    def increase(self, step=10):
        if self.speed + step <= 100:
            self.speed += step

    def decrease(self, step=10):
        if self.speed - step >= 0:
            self.speed -= step

    def read_status(self, file_read):
        with open(self.path + file_read, 'r') as f:
            return f.read()
        return None

    def update(self):
        # Read PWM
        if self.isTPWM:
            fan_level = float(self.read_status("target_pwm")) / 255.0 * 100.0
            logger.debug('{} status PWM CTRL {}'.format(self.path, fan_level))
            self._status["tpwm"] = int(fan_level)
        # Read current
        if self.isCPWM:
            fan_level = float(self.read_status("cur_pwm")) / 255.0 * 100.0
            logger.debug('{} status PWM CUR {}'.format(self.path, fan_level))
            self._status["cpwm"] = int(fan_level)
        # Read RPM fan
        # if self.with_rpm:
        #     rpm_measured = int(self.read_status("rpm_measured"))
        #     logger.debug('{} status RPM {}'.format(self.path, rpm_measured))
        #     self._status["rpm"] = rpm_measured

    @property
    def status(self):
        # TODO Improve RPM read
        # if self.with_rpm and self.rpm[-1] != 0:
        #     fan['label'] = str(self.rpm[-1]) + "RPM"
        return self._status
# EOF
