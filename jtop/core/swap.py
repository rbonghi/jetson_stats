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

CONFIG_DEFAULT_SWAP_DIRECTORY = ''
CONFIG_DEFAULT_SWAP_NAME = 'swfile'
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
        self._controller = None
        self._list_swaps = list_swaps()

    def _init(self, controller):
        self._controller = controller

    def set(self, value, on_boot=False):
        if not isinstance(value, (int, float)):
            raise ValueError("Need a Number")
        # Set new swap size configuration
        self._controller.put({'swap': {'size': value, 'boot': on_boot}})

    def deactivate(self):
        # Set new swap size configuration
        self._controller.put({'swap': {}})

    def __repr__(self):
        self._list_swaps = list_swaps()
        return str(self._list_swaps)


class SwapService(object):

    def __init__(self, config):
        self._config = config
        # Load swap information
        # self.update()

    def _update(self):
        config = self._config.get('swap', {})
        directory = config.get('directory', CONFIG_DEFAULT_SWAP_DIRECTORY)
        swap_name = config.get('name', CONFIG_DEFAULT_SWAP_NAME)
        # Update swap
        swap_status = sp.Popen([JETSON_SWAP_PATH, '--status', '--dir', directory, '--name', swap_name], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = swap_status.communicate()
        swap_info = {}
        if out:
            swap_data = out.decode("utf-8")
            swap_data = swap_data.split("\t")
            # Load swap information
            swap_info['file'] = str(swap_data[0].strip())
            swap_info['type'] = str(swap_data[1].strip())
            swap_info['size'] = int(swap_data[2].strip()) / 1000000.0
            swap_info['used'] = int(swap_data[3].strip()) / 1000.0
            swap_info['priority'] = int(swap_data[4].strip())
            # Update size
            # self.actual_size = int(self.swap_info['size'])
        return swap_info

    def set(self, value, on_boot=False):
        if not isinstance(value, (int, float)):
            raise ValueError("Need a Number")
        # Load swap configuration
        config = self._config.get('swap', {})
        directory = config.get('directory', CONFIG_DEFAULT_SWAP_DIRECTORY)
        swap_name = config.get('name', CONFIG_DEFAULT_SWAP_NAME)
        # List swap command
        swap_cmd = [JETSON_SWAP_PATH, '--size', str(value), '--dir', directory, '--name', swap_name]
        # Add auto command if request
        if on_boot:
            swap_cmd += ['--auto']
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)

    def deactivate(self):
        # Load swap configuration
        config = self._config.get('swap', {})
        directory = config.get('directory', CONFIG_DEFAULT_SWAP_DIRECTORY)
        swap_name = config.get('name', CONFIG_DEFAULT_SWAP_NAME)
        # List swap command
        swap_cmd = [JETSON_SWAP_PATH, '--off', '--dir', directory, '--name', swap_name]
        # Run script
        sp.Popen(swap_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
# EOF
