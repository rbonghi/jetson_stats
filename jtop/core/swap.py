# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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


class Swap:

    def __init__(self):
        self.path = "jetson_swap"
        self._size = 8
        self.dir = "/opt/"
        self.auto = False
        self.swap_status = {}

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, val):
        self._size = val

    def __sizeof__(self):
        return self.size

    @property
    def enable(self):
        return True if self.swap_status else False

    @enable.setter
    def enable(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        # Enable or disable swap
        if value:
            self._enable()

    def _enable(self):
        # List swap command
        swap_cmd = [self.path, '--size', str(self._size)]
        # Add auto command if request
        if self.auto:
            swap_cmd += ['--auto']
        # Set different folder
        if self.dir:
            swap_cmd += ['--dir', str(self.dir)]
        # Run script
        self.p = sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

    def update(self, stats):
        self.swap_status = stats.get('SWAP', {})
        # Update size status if swap is enable
        if self.swap_status:
            tot = self.swap_status.get('tot', 0)
            self.size = tot / 1000.0

    