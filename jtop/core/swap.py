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

JETSON_SWAP_PATH = '/usr/local/bin/jetson_swap'
SWAP_MAX_SIZE = 15
SWAP_MIN_SIZE = 2


def list_swaps():
    swap_status = sp.Popen(['swapon', '--show', '--raw', '--byte'], stdout=sp.PIPE, stderr=sp.PIPE)
    out, _ = swap_status.communicate()
    swaps = {}
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
            if not datas:
                continue
            # Decode swap info
            info = {}
            n_swap = ''
            for name, data in zip(names, datas):
                name = name.lower()
                if name != 'name':
                    info[name] = int(data) if data.isdigit() else data
                else:
                    n_swap = data
            # Add swap in list
            swaps[n_swap] = info
    return swaps


class Swap(object):

    def __init__(self):
        pass

    def __repr__(self):
        return str(list_swaps())


class SwapService(object):

    def __init__(self, config):
        self.config = config
        # Set default folder swap
        self.dir = "dir_swap"
        self.swap_name = "swap_name"
        self.swap_info = {}
        # Define actual size and new size variable
        self.actual_size = 0
        # Initialize auto mount
        self.auto = True
        # Load swap information
        # self.update()

    def _update(self):
        swap_status = sp.Popen([JETSON_SWAP_PATH, '--status', '--dir', self.dir, '--name', self.swap_name], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = swap_status.communicate()
        if out:
            swap_data = out.decode("utf-8")
            swap_data = swap_data.split("\t")
            # Load swap information
            self.swap_info['file'] = str(swap_data[0].strip())
            self.swap_info['type'] = str(swap_data[1].strip())
            self.swap_info['size'] = int(swap_data[2].strip()) / 1000000.0
            self.swap_info['used'] = int(swap_data[3].strip()) / 1000.0
            self.swap_info['priority'] = int(swap_data[4].strip())
            # Update size
            self.actual_size = int(self.swap_info['size'])
        else:
            self.swap_info = {}

    def set(self, value, on_boot=False):
        if not isinstance(value, (int, float)):
            raise ValueError("Need a Number")
        # List swap command
        swap_cmd = [JETSON_SWAP_PATH, '--size', str(value), '--dir', self.dir, '--name', self.swap_name]
        # Add auto command if request
        if on_boot:
            swap_cmd += ['--auto']
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

    def deactivate(self):
        # List swap command
        swap_cmd = [JETSON_SWAP_PATH, '--off', '--dir', self.dir, '--name', self.swap_name]
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        # Remove swapfile if exist
# EOF
