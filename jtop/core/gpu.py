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


def check_nvidia_smi():
    cmd = Command(['nvidia-smi'])
    try:
        cmd()
        return True
    except (OSError, Command.CommandException):
        pass
    return False


def igpu_read_freq(path):
    # Read status online
    gpu = {}
    gpu['unit'] = 'k'
    # Check if access to this file
    if os.access(path + "/governor", os.R_OK):
        with open(path + "/governor", 'r') as f:
            # Write current engine
            gpu['governor'] = f.read().strip()
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
    # Read GPC status
    for idx in range(2):
        # Read power control status
        path_gpc = "/sys/kernel/debug/bpmp/debug/clk/nafll_gpc{number}/pto_counter".format(number=idx)
        if os.access(path_gpc, os.R_OK):
            with open(path_gpc, 'r') as f:
                # List all frequencies
                if 'GPC' not in gpu:
                    gpu['GPC'] = []
                gpu['GPC'] += [int(f.read()) // 1000]
    return gpu


def igpu_read_status(path):
    gpu = {}
    # Railgate status
    if os.access(path + "/railgate_enable", os.R_OK):
        with open(path + "/railgate_enable", 'r') as f:
            # Write status engine
            gpu['railgate'] = int(f.read()) == 1
    # Mask status (Useful for nvpmodel)
    if os.access(path + "/tpc_pg_mask", os.R_OK):
        with open(path + "/tpc_pg_mask", 'r') as f:
            # Write status engine
            gpu['tpc_pg_mask'] = int(f.read()) == 1
    # Status 3D scaling
    if os.access(path + "/enable_3d_scaling", os.R_OK):
        with open(path + "/enable_3d_scaling", 'r') as f:
            # Write status engine
            gpu['3d_scaling'] = int(f.read()) == 1
    # Current load GPU
    if os.access(path + "/load", os.R_OK):
        with open(path + "/load", 'r') as f:
            # Write status engine
            gpu['load'] = float(f.read()) / 10.0
    return gpu


def find_igpu():
    # Check if exist a integrated gpu
    if not os.path.exists("/dev/nvhost-gpu") and not os.path.exists("/dev/nvhost-power-gpu"):
        return []
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
                    # Extract real path GPU device
                    path = os.path.realpath(os.path.join(item_path, "device"))
                    frq_path = os.path.realpath(item_path)
                    igpu += [{'name': name, 'type': 'integrated', 'path': path, 'frq_path': frq_path}]
                    logger.info("GPU found {name} in {path}".format(name=name, path=path))
                else:
                    logger.debug("Skipped {name}".format(name=name))
    return igpu


def find_dgpu():
    # Check if there are discrete gpu
    if not os.path.exists("/dev/nvidiactl") and not os.path.isdir("/dev/nvgpu-pci"):
        return []
    logger.info("Discrete GPU found")
    igpu = []
    return igpu


class GPUService(object):

    def __init__(self):
        # Detect integrated GPU
        self._gpu_list = find_igpu()
        # Find discrete GPU
        self._gpu_list += find_dgpu()
        # Check status
        if not self._gpu_list:
            logger.info("No NVIDIA GPU available")

    def get_status(self):
        gpu_list = []
        # Read iGPU frequency
        for data in self._gpu_list:
            # Initialize GPU status
            gpu = {'name': data['name'], 'type': data['type']}
            # Detect frequency and load
            if gpu['type'] == 'integrated':
                # Read status GPU
                gpu['status'] = igpu_read_status(data['path'])
                # Read frequency
                gpu['freq'] = igpu_read_freq(data['frq_path'])
                # Read power control status
                if os.access(data['path'] + "/power/control", os.R_OK):
                    with open(data['path'] + "/power/control", 'r') as f:
                        gpu['power_control'] = f.read().strip()
            elif gpu['type'] == 'discrete':
                logger.info("TODO discrete GPU")
            # Load all status in GPU
            gpu_list += [gpu]
        return gpu_list
# EOF
