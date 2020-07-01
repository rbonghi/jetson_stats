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
# from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)


class Memory(object):

    def __init__(self, controller):
        self._controller = controller
        self._ram = {}

    def clear_cache(self):
        # Set new swap size configuration
        self._controller.put({'memory': ''})

    def _update(self, ram):
        self._ram = ram

    def get(self, name, value):
        if name in self._ram:
            return self._ram[name]
        else:
            return value

    def items(self):
        return self._ram.items()

    def __getitem__(self, name):
        return self._ram[name]

    def __iter__(self):
        return iter(self._ram)

    def __next__(self):
        return next(self._ram)

    def __len__(self):
        return len(self._ram)

    def __repr__(self):
        return str(self._ram)


class MemoryService(object):

    def __init__(self):
        pass

    def clear_cache(self):
        """
        Clear cache following https://coderwall.com/p/ef1gcw/managing-ram-and-swap
        """
        clear_cache = sp.Popen(['sysctl', 'vm.drop_caches=3'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = clear_cache.communicate()
        return True if out else False
# EOF
