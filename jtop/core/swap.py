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

SWAP_MAX_SIZE = 15
SWAP_MIN_SIZE = 2


class Swap(object):

    class SwapException(Exception):
        pass

    def __init__(self, dir_swap="", default=8, swap_name="swfile"):
        # Set default folder swap
        self.dir = dir_swap
        self.swap_name = swap_name
        self.swap_info = {}
        # Define actual size and new size variable
        self.actual_size = 0
        self.new_size = default
        # Initialize auto mount
        self.auto = True
        # Check if exist jetson_swap
        exist = sp.call('command -v jetson_swap >> /dev/null', shell=True)
        if exist != 0:
            raise Swap.SwapException("jetson_swap does not exist!")
        # Load swap information
        self.update()

    def update(self):
        swap_status = sp.Popen(['jetson_swap', '--status', '--dir', self.dir, '--name', self.swap_name], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = swap_status.communicate()
        if out:
            swap_data = out.decode("utf-8")
            swap_data = swap_data.split("\t")
            # Load swap informations
            self.swap_info['file'] = swap_data[0].strip()
            self.swap_info['type'] = swap_data[1].strip()
            self.swap_info['size'] = int(swap_data[2].strip()) / 1000000.0
            self.swap_info['used'] = int(swap_data[3].strip()) / 1000.0
            self.swap_info['priority'] = int(swap_data[4].strip())
            # Update size
            self.actual_size = int(self.swap_info['size'])
        else:
            self.swap_info = {}

    def swaps(self):
        swap_status = sp.Popen(['swapon', '--show', '--raw', '--byte'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = swap_status.communicate()
        swaps = []
        if out:
            swap_data = out.decode("utf-8")
            # Read all data
            names = []
            for line in swap_data.split("\n"):
                # Extract names
                # The names are: name, type, size, used, prio
                if not names:
                    names = line.split()
                    continue
                # Extract data
                datas = line.split()
                if datas:
                    swaps += [{name.lower(): int(data) if data.isdigit() else data for name, data in zip(names, datas)}]
        return swaps

    def increase(self):
        if self.size + 1 <= SWAP_MAX_SIZE:
            self.size += 1
            return True
        else:
            return False

    def decrease(self):
        if self.size - 1 >= SWAP_MIN_SIZE:
            self.size -= 1
            return True
        else:
            return False

    @property
    def file(self):
        return self.dir + "/" + self.swap_name

    @property
    def size(self):
        return self.new_size

    @size.setter
    def size(self, val):
        self.new_size = val

    def __len__(self):
        return self.actual_size

    def clearCache(self):
        """
        Clear cache following https://coderwall.com/p/ef1gcw/managing-ram-and-swap
        """
        clear_cache = sp.Popen(['sysctl', 'vm.drop_caches=3'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = clear_cache.communicate()
        return True if out else False

    @property
    def enable(self):
        self.update()
        return True if self.swap_info else False

    @enable.setter
    def enable(self, value):
        if not isinstance(value, bool):
            raise Exception("Use a boolean")
        # Enable or disable swap
        if value:
            self._enable()
        else:
            self._disable()

    def _enable(self):
        # List swap command
        swap_cmd = ['jetson_swap', '--size', str(self.new_size), '--dir', self.dir, '--name', self.swap_name]
        # Add auto command if request
        if self.auto:
            swap_cmd += ['--auto']
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

    def _disable(self):
        # List swap command
        swap_cmd = ['jetson_swap', '--off', '--dir', self.dir, '--name', self.swap_name]
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        # Remove swapfile if exist
# EOF
