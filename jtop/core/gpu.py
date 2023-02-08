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
    if os.path.exists("/dev/nvhost-gpu") or os.path.exists("/dev/nvhost-power-gpu"):
        return 'integrated'
    elif os.path.exists("/dev/nvidiactl") or os.path.isdir("/dev/nvgpu-pci"):
        return 'discrete'
    return ''


def check_nvidia_smi():
    cmd = Command(['nvidia-smi'])
    try:
        cmd()
        return True
    except (OSError, Command.CommandException):
        pass
    return False


def igpu_read_load():
    load = []
    # From JP5.1
    # https://forums.developer.nvidia.com/t/how-to-programmatically-query-igpu-load/237266
    if os.path.isfile("/sys/devices/platform/gpu.0/load"):
        load += [int(cat("/sys/devices/platform/gpu.0/load"))]
    elif os.path.isfile("/sys/devices/gpu.0/load"):
        load += [int(cat("/sys/devices/gpu.0/load"))]
    return load


def igpu_read_freq(path):
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
    igpu = []
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
                if name in ['gv11b', 'gp10b', 'ga10b', 'gpu']:
                    igpu += [{'name': name, 'path': item_path}]
                    logger.info("GPU found {name} in {path}".format(name=name, path=item_path))
                else:
                    logger.info("Skipped {name}".format(name=name))
    return igpu


class GPUService(object):

    def __init__(self):
        self._gpu_list = []
        # self._architecture = architecture
        # Detect which GPU is running
        self._gpu_type = gpu_detect()
        # Search gpu path
        logger.info("Gpu Detected type: {type}".format(type=self._gpu_type))
        # Detect GPU folder
        if self._gpu_type == 'integrated':
            self._gpu_list = find_igpu()
        elif self._gpu_type == 'discrete':
            print("TODO discrete GPU")
        else:
            logger.info("No NVIDIA GPU available")
        # TEMP
        status = self.get_status()
        print(status)

    def get_status(self):
        status = {'type': self._gpu_type}
        # Detect frequency and load
        if self._gpu_type == 'integrated':
            # Read iGPU frequency
            status['gpu'] = []
            for data in self._gpu_list:
                # Read frequency
                gpu = {'freq': igpu_read_freq(data['path'])}
                # Read GPU load
                gpu['load'] = igpu_read_load()
                # Read also
                # TPC_POWER_GATING: /sys/devices/gpu.0/tpc_pg_mask
                # GPU_POWER_CONTROL_ENABLE: /sys/devices/gpu.0/power/control
                status['gpu'] += [gpu]
        elif self._gpu_type == 'discrete':
            # TODO
            pass
        return status
# EOF
