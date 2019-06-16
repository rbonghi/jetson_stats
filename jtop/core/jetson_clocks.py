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
