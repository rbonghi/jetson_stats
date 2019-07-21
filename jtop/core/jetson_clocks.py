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

# Logging
import logging
# Launch command
import subprocess as sp

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class JetsonClocks(object):

    def __init__(self, service='jetson_performance'):
        self.service = service
        self.last_status = ""

    @property
    def status(self):
        p = sp.Popen(['systemctl', 'is-active', self.service + '.service'], stdout=sp.PIPE)
        out, _ = p.communicate()
        return str(out.decode("utf-8")).strip()

    @property
    def start(self):
        start_val = True if self.status == "active" else False
        return start_val

    @start.setter
    def start(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        start_val = "start" if value else "stop"
        p = sp.Popen(['systemctl', start_val, self.service + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        _, err = p.communicate()
        self.last_status = err.decode("utf-8")

    @property
    def enable(self):
        p = sp.Popen(['systemctl', 'is-enabled', self.service + '.service'], stdout=sp.PIPE)
        out, _ = p.communicate()
        enable_val = True if str(out.decode("utf-8")).strip() == "enabled" else False
        return enable_val

    @enable.setter
    def enable(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        enable_val = "enable" if value else "disable"
        p = sp.Popen(['systemctl', enable_val, self.service + '.service'], stdout=sp.PIPE, stderr=sp.PIPE)
        _, err = p.communicate()
        self.last_status = err.decode("utf-8")

# EOF
