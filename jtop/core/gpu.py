# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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

import os
# Logging
import logging
from .common import cat
from .command import Command
# Create logger
logger = logging.getLogger(__name__)


def gpu_detect():
    if os.path.exists("/dev/nvhost-gpu"):
        return 'integrated'
    return ''


def check_nvidia_smi():
    cmd = Command(['nvidia-smi'])
    try:
        cmd()
        return True
    except (OSError, Command.CommandException):
        pass
    return False


def read_igpu(path):
    # Read status online
    gpu = {}
    gpu['unit'] = 'k'
    # Check if access to this file
    if os.access(path + "/cur_freq", os.R_OK):
        with open(path + "/cur_freq", 'r') as f:
            # Write current engine
            gpu['cur'] = int(f.read()) // 1000
    # Decode clock rate
    if os.access(path + "/max_freq", os.R_OK):
        with open(path + "/max_freq", 'r') as f:
            # Write status engine
            gpu['max'] = int(f.read()) // 1000
    if os.access(path + "/min_freq", os.R_OK):
        with open(path + "/min_freq", 'r') as f:
            # Write status engine
            gpu['min'] = int(f.read()) // 1000
    if os.access(path + "/device/railgate_enable", os.R_OK):
        with open(path + "/device/railgate_enable", 'r') as f:
            # Write status engine
            gpu['railgate'] = int(f.read()) // 1000
    return gpu


def find_igpu():
    igpu = {}
    igpu_path = "/sys/class/devfreq/"
    for item in os.listdir(igpu_path):
        item_path = os.path.join(igpu_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            # Check name device
            name_path = "{item}/device/of_node/name".format(item=item_path)
            if os.path.isfile(name_path):
                # Decode name
                name = cat(name_path)
                # Check if gpu
                if name in ['gv11b', 'gp10b', 'gpu']:
                    igpu[name] = item_path
    return igpu


class GPUService(object):

    def __init__(self):
        # Detect wich GPU is running
        self._gpu_type = gpu_detect()
        # Search gpu path
        logger.info("Gpu Detected type: {type}".format(type=self._gpu_type))
        if self._gpu_type == 'integrated':
            igpu = find_igpu()
            print(igpu)
            status = read_igpu(igpu['gpu'])
            print(status)

    def get_status(self):
        status = {}
        if self._gpu_type == 'integraged':
            status = read_igpu()
        return status
# EOF
