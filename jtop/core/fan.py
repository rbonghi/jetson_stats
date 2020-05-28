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
            line = [tab.strip() for tab in match.group(1).split(",")]
            if title:
                table += [{title[idx]: val for idx, val in enumerate(line) if idx > 0}]
            else:
                title = line
    return table


class Fan(object):

    class FanException(Exception):
        pass

    def __init__(self, path, jetson_clocks, config_file, temp_control=True):
        # Config file
        self.config_file = config_file + "/fan_config"
        self.jetson_clocks = jetson_clocks
        # Initialize number max records to record
        self.path = path
        self.temp_control = temp_control
        self.CONFIGS = ["jc", "manual"]
        self.old_speed = 0
        # Check exist path
        if not os.path.isdir(path):
            raise Fan.FanException("Fan does not exist")
        # Init status config with first config
        self.conf = self.CONFIGS[0]
        # Init status fan
        self._status = {}
        self.isRPM = os.path.isfile(self.path + "rpm_measured")
        self.isCPWM = os.path.isfile(self.path + "cur_pwm")
        self.isTPWM = os.path.isfile(self.path + "target_pwm")
        self.isCTRL = os.path.isfile(self.path + "temp_control")
        # Max value PWM
        self._status["cap"] = int(self.read_status("pwm_cap")) if os.path.isfile(self.path + "pwm_cap") else 255
        # PWM RPM table
        self.table = load_table(self.path) if os.path.isfile(self.path + "pwm_rpm_table") else {}
        # Step time
        self._status["step"] = int(self.read_status("step_time")) if os.path.isfile(self.path + "step_time") else 0
        # Status FAN
        if os.path.isfile(self.path + "target_pwm"):
            self._status["status"] = 'ON'
        elif os.getuid() != 0:
            self._status["status"] = 'SUDO SUGGESTED'
        else:
            self._status["status"] = 'OFF'
        # Load configuration if exist
        self.load()
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
            pwm = self.ValueToPWM(value)
            # Write PWM value
            with open(self.path + "target_pwm", 'w') as f:
                f.write(str(pwm))

    @property
    def control(self):
        return self._status.get("ctrl", False)

    @control.setter
    def control(self, value):
        # Check limit speed
        if os.access(self.path + "temp_control", os.W_OK) and self.temp_control:
            value = 1 if value else 0
            # Write status control value
            with open(self.path + "temp_control", 'w') as f:
                f.write(str(value))

    @property
    def config(self):
        return self.conf

    @config.setter
    def config(self, value):
        if self.temp_control:
            if value == "manual":
                self.control = True
                self.speed = self.old_speed
            elif value == "jc":
                if self.jetson_clocks.start:
                    self.control = False
                    # Store speed status
                    self.old_speed = self.speed
                    # Set max speed
                    self.speed = 100
                else:
                    self.speed = 0
        self.conf = value

    def conf_next(self):
        try:
            # Extract index  from name configuration
            idx = self.CONFIGS.index(self.conf)
            # Go to next index and normalize for size len
            idx = (idx + 1) % len(self.CONFIGS)
        except ValueError:
            idx = 0
        # Update with new config name
        self.config = self.CONFIGS[idx]

    def conf_prev(self):
        try:
            # Extract index  from name configuration
            idx = self.CONFIGS.index(self.conf)
            # Go to previous index and normalize for size len
            idx = (idx - 1) % len(self.CONFIGS)
        except ValueError:
            idx = 0
        # Update with new config name
        self.config = self.CONFIGS[idx]

    def increase(self, step=10):
        # Round speed
        spd = (self.speed // 10) * 10
        # Increase the speed
        if spd + step <= 100:
            self.speed = spd + step

    def decrease(self, step=10):
        # Round speed
        spd = (self.speed // 10) * 10
        # Increase the speed
        if spd - step >= 0:
            self.speed = spd - step
        if self.speed < step:
            self.speed = 0

    def clear(self):
        if os.path.isfile(self.config_file):
            # Remove configuration file
            try:
                os.remove(self.config_file)
            except OSError:
                return False
        return True

    def load(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, 'r') as f:
                line = f.readline()
                if line:
                    # Load configuration
                    self.conf = line.lower().strip()
                line = f.readline()
                if line:
                    # Load old speed
                    try:
                        speed = int(line.lower().strip())
                        self.old_speed = self.PWMtoValue(speed)
                    except ValueError:
                        pass

    def store(self):
        with open(self.config_file, 'w') as f:
            # Save actual configuration
            f.write(self.conf.upper() + '\n')
            if not self.jetson_clocks.start:
                # Save PWM defined
                f.write(self.read_status("target_pwm"))
            else:
                pwm = int(self.ValueToPWM(self.old_speed))
                f.write(str(pwm) + "\n")

    def read_status(self, file_read):
        with open(self.path + file_read, 'r') as f:
            return f.read()
        return None

    def PWMtoValue(self, pwm):
        return pwm * 100.0 / self._status["cap"]

    def ValueToPWM(self, value):
        return ceil(self._status["cap"] * value / 100.0)

    def update(self):
        # Control temperature
        if self.isCTRL:
            self._status["ctrl"] = True if int(self.read_status("temp_control")) == 1 else False
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
