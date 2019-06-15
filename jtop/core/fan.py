# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
# Logging
import logging
# Launch command
import subprocess as sp
from collections import deque

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class Fan(object):

    class FanException(Exception):
        pass

    def __init__(self, path, interval, time):
        # Initialize number max records to record
        self.path = path
        # Check exist path
        if not os.path.isdir(path):
            raise Fan.FanException("Fan does not exist")
        # Init variables
        max_record = int(float(time) * (float(1 / float(interval)) * 1000.0))
        self.fan_ctrl = deque(max_record * [0], maxlen=max_record)
        self.fan_read = deque(max_record * [0], maxlen=max_record)
        self.rpm = deque(max_record * [0], maxlen=max_record)
        self.with_rpm = os.path.isfile(self.path + "rpm_measured")
        self.with_curr = os.path.isfile(self.path + "cur_pwm")
        self.with_target = os.path.isfile(self.path + "target_pwm")
        # Max value PWM
        if os.path.isfile(self.path + "pwm_cap"):
            self.pwm_max = int(self.read_status("pwm_cap"))
        else:
            self.pwm_max = 255
        # PWM RPM table
        if os.path.isfile(self.path + "pwm_rpm_table"):
            pwm_rpm_table = self.read_status("pwm_rpm_table")
            for line in pwm_rpm_table.split("\n"):
                line = [val.strip() for val in line.split(",")]
                # print(line)
        # Step time
        if os.path.isfile(self.path + "step_time"):
            self.step_time = int(self.read_status("step_time"))
        else:
            self.step_time = 0
        # Control temperature
        if os.path.isfile(self.path + "temp_control"):
            self.temp_control = int(self.read_status("temp_control"))
        # Status FAN
        if os.getuid() == 0:
            self.qstatus = 'ON' if os.path.isfile(self.path + "target_pwm") else 'OFF'
        else:
            self.qstatus = 'REQUIRE SUDO'

    def read_status(self, file_read):
        status = sp.Popen(['cat', self.path + file_read], stdout=sp.PIPE)
        query, _ = status.communicate()
        return query

    def update(self):
        # Read PWM
        if self.with_target:
            fan_level = float(self.read_status("target_pwm")) / 255.0 * 100.0
            logger.debug('{} status PWM CTRL {}'.format(self.path, fan_level))
            self.fan_ctrl.append(int(fan_level))
        # Read current
        if self.with_curr:
            fan_level = float(self.read_status("cur_pwm")) / 255.0 * 100.0
            logger.debug('{} status PWM CUR {}'.format(self.path, fan_level))
            self.fan_read.append(int(fan_level))
        # Read RPM fan
        # if self.with_rpm:
        #     rpm_measured = int(self.read_status("rpm_measured"))
        #     logger.debug('{} status RPM {}'.format(self.path, rpm_measured))
        #     self.rpm.append(rpm_measured)

    @property
    def status(self):
        fan = {'name': 'FAN',
               'status': self.qstatus
               }
        if self.with_curr:
            fan['value'] = list(self.fan_read)
            fan['percent'] = str(self.fan_read[-1]) + "/" + str(self.fan_ctrl[-1]) + "%"
        elif self.with_target:
            fan['value'] = list(self.fan_ctrl)
        # TODO Improve RPM read
        # if self.with_rpm and self.rpm[-1] != 0:
        #     fan['label'] = str(self.rpm[-1]) + "RPM"
        return fan
