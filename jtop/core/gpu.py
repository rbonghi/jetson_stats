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
from .common import cat, GenericInterface
from .exceptions import JtopException
from .command import Command
# Create logger
logger = logging.getLogger(__name__)
# default ipgu path for Jetson devices
DEFAULT_IGPU_PATH = "/sys/class/devfreq/"


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
    # GPU status
    if os.access(path + "/railgate_enable", os.R_OK):
        with open(path + "/railgate_enable", 'r') as f:
            # Read status railgate
            gpu['railgate'] = int(f.read()) == 1
    # Mask status (Useful for nvpmodel)
    if os.access(path + "/tpc_pg_mask", os.R_OK):
        with open(path + "/tpc_pg_mask", 'r') as f:
            # Read status TPG PG mask
            gpu['tpc_pg_mask'] = int(f.read()) == 1
    # Status 3D scaling
    if os.access(path + "/enable_3d_scaling", os.R_OK):
        with open(path + "/enable_3d_scaling", 'r') as f:
            # Read status 3D scaling
            gpu['3d_scaling'] = int(f.read()) == 1
    # Current load GPU
    if os.access(path + "/load", os.R_OK):
        with open(path + "/load", 'r') as f:
            # Read current GPU load
            gpu['load'] = float(f.read()) / 10.0
    return gpu


def get_raw_igpu_devices():
    igpu_path = DEFAULT_IGPU_PATH
    raw_output = {}
    for item in os.listdir(igpu_path):
        item_path = os.path.join(igpu_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            # Check name device
            name_path = "{item}/device/of_node/name".format(item=item_path)
            if os.path.isfile(name_path):
                # Decode name
                name = cat(name_path)
                # path and file
                raw_output[name_path] = "{}".format(name)
    return raw_output


def find_igpu(igpu_path):
    # Check if exist a integrated gpu
    # if not os.path.exists("/dev/nvhost-gpu") and not os.path.exists("/dev/nvhost-power-gpu"):
    #     return []
    igpu = {}
    if not os.path.isdir(igpu_path):
        logger.error("Folder {root_dir} doesn't exist".format(root_dir=igpu_path))
        return igpu
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
                    igpu[name] = {'type': 'integrated', 'path': path, 'frq_path': frq_path}
                    logger.info("GPU \"{name}\" status in {path}".format(name=name, path=path))
                    logger.info("GPU \"{name}\" frq in {path}".format(name=name, path=frq_path))
                    # Check if railgate exist
                    path_railgate = os.path.join(path, "railgate_enable")
                    if os.path.isfile(path_railgate):
                        igpu[name]['railgate'] = path_railgate
                    # Check if 3d scaling exist
                    path_3d_scaling = os.path.join(path, "enable_3d_scaling")
                    if os.path.isfile(path_3d_scaling):
                        igpu[name]['3d_scaling'] = path_3d_scaling
                else:
                    logger.debug("Skipped {name}".format(name=name))
    return igpu


def find_dgpu():
    # Check if there are discrete gpu
    # if not os.path.exists("/dev/nvidiactl") and not os.path.isdir("/dev/nvgpu-pci"):
    #     return []
    # https://enterprise-support.nvidia.com/s/article/Useful-nvidia-smi-Queries-2
    dgpu = {}
    if check_nvidia_smi():
        logger.info("NVIDIA SMI exist!")
    if dgpu:
        logger.info("Discrete GPU found")
    return dgpu


class GPU(GenericInterface):
    """
    This class get the output from your GPU, this class is readable like a dictionary,
    please read the documentation on :py:attr:`~jtop.jtop.gpu` but is also usable to enable, disable 3d scaling on your device.

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                jetson.gpu.set_scaling_3D("gpu", True)

    Below all methods available using the :py:attr:`~jtop.jtop.gpu` attribute
    """

    def __init__(self):
        super(GPU, self).__init__()

    def set_scaling_3D(self, name, value):
        """
        Enable disable GPU 3D scaling. this method send a command like below on your Jetson.

        Set 3D scaling on your board, like the command below. To know the GPU name use :py:attr:`~jtop.jtop.gpu`

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    jetson.gpu.set_scaling_3D("ga10b", True)

        is equivalent to:

        .. code-block:: bash
            :class: no-copybutton

            echo 1 > /sys/devices/17000000.ga10b/enable_3d_scaling

        :param name: GPU name
        :type name: str
        :param value: Enable/Disable 3D scaling
        :type value: bool
        :raises JtopException: if GPU doesn't exist
        """
        if name not in self._data:
            raise JtopException("GPU \"{name}\" does not exist".format(name=name))
        # Set new 3D scaling
        self._controller.put({'gpu': {'command': '3d_scaling', 'name': name, 'value': value}})

    def get_scaling_3D(self, name):
        """
        Return status of 3D scaling, this output is also readable from :py:attr:`~jtop.jtop.gpu` attribute

        :param name: GPU name
        :type name: str
        :raises JtopException: if GPU doesn't exist
        :return: status 3D scaling
        :rtype: bool
        """
        if name not in self._data:
            raise JtopException("GPU \"{name}\" does not exist".format(name=name))
        return self._data[name]['status']['3d_scaling']

    @property
    def scaling_3D(self):
        """
        Return status of 3D scaling, this output is also readable from :py:attr:`~jtop.jtop.gpu` attribute

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Set new 3D scaling
                    jetson.gpu.set_scaling_3D = True
                    # same of
                    jetson.gpu.set_scaling_3D("ga10b", True)

        :raises JtopException: if there are no integrated GPU
        :return: status 3D scaling
        :rtype: bool
        """
        # Get first integrated gpu
        name = self._get_first_integrated_gpu()
        if not name:
            raise JtopException("no Integrated GPU available")
        return self.get_scaling_3D(name)

    @scaling_3D.setter
    def scaling_3D(self, value):
        # Get first integrated gpu
        name = self._get_first_integrated_gpu()
        if not name:
            raise JtopException("no Integrated GPU available")
        self.set_scaling_3D(name, value)

    def set_railgate(self, name, value):
        if name not in self._data:
            raise JtopException("GPU \"{name}\" does not exist".format(name=name))
        # Set new 3D scaling
        self._controller.put({'gpu': {'command': 'railgate', 'name': name, 'value': value}})

    def get_railgate(self, name):
        if name not in self._data:
            raise JtopException("GPU \"{name}\" does not exist".format(name=name))
        return self._data[name]['status']['railgate']

    def _get_first_integrated_gpu(self):
        for name in self._data:
            if self._data[name]['type'] == 'integrated':
                return name
        return ''


class GPUService(object):

    def __init__(self):
        # Detect integrated GPU
        igpu_path = DEFAULT_IGPU_PATH
        if os.getenv('JTOP_TESTING', False):
            igpu_path = "/fake_sys/class/devfreq/"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=igpu_path))
        self._gpu_list = find_igpu(igpu_path)
        # Find discrete GPU
        self._gpu_list.update(find_dgpu())
        # Check status
        if not self._gpu_list:
            logger.warning("No NVIDIA GPU available")

    def set_scaling_3D(self, name, value):
        if name not in self._gpu_list:
            logger.error("GPU \"{name}\" does not exist".format(name=name))
            return False
        if '3d_scaling' not in self._gpu_list[name]:
            logger.error("GPU \"{name}\" does not have 3D scaling".format(name=name))
            return False
        path_3d_scaling = self._gpu_list[name]['3d_scaling']
        string_value = "1" if value else "0"
        # Write new status 3D scaling
        try:
            if os.access(path_3d_scaling, os.W_OK):
                with open(path_3d_scaling, 'w') as f:
                    f.write(string_value)
            logger.info("GPU \"{name}\" set 3D scaling to {value}".format(name=name, value=value))
        except OSError as e:
            logger.error("I cannot set 3D scaling {}".format(e))

    def set_railgate(self, name, value):
        if name not in self._gpu_list:
            logger.error("GPU \"{name}\" does not exist".format(name=name))
            return False
        if 'railgate' not in self._gpu_list[name]:
            logger.error("GPU \"{name}\" does not have railgate".format(name=name))
            return False
        path_railgate = self._gpu_list[name]['railgate']
        string_value = "1" if value else "0"
        # Write new status railgate
        try:
            if os.access(path_railgate, os.W_OK):
                with open(path_railgate, 'w') as f:
                    f.write(string_value)
            logger.info("GPU \"{name}\" set railgate to {value}".format(name=name, value=value))
        except OSError as e:
            logger.error("I cannot set Railgate {}".format(e))

    def get_status(self):
        gpu_list = {}
        # Read iGPU frequency
        for name, data in self._gpu_list.items():
            # Initialize GPU status
            gpu = {'type': data['type']}
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
            gpu_list[name] = gpu
        return gpu_list
# EOF
