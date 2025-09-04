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
from .jetson_variables import get_jetson_variables, NVIDIA_JETPACK

# Try to import NVML for newer Jetpack versions
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    pynvml = None

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


def check_jetpack_version():
    """Check if current Jetpack version is 7.0 or newer"""
    try:
        jetson_vars = get_jetson_variables()
        l4t_version = jetson_vars.get('L4T', '')
        jetpack_version = NVIDIA_JETPACK.get(l4t_version, '')
        
        # Extract major version number
        if jetpack_version:
            # Handle formats like "7.0", "6.2", "6.1 (rev1)", etc.
            version_number = jetpack_version.split()[0]
            major_version = float(version_number.split('.')[0])
            return major_version >= 7.0
    except Exception as e:
        logger.debug("Could not determine Jetpack version: {}".format(e))
    return False


def nvml_read_gpu_status():
    """Read GPU status using NVML for Jetpack 7.0+"""
    gpu_data = {}
    try:
        if not NVML_AVAILABLE:
            logger.debug("NVML not available")
            return gpu_data
            
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        logger.info("NVML device count: {}".format(device_count))
        
        # If no devices detected, NVML might not support this particular Jetson model
        if device_count == 0:
            logger.info("No devices detected by NVML")
            pynvml.nvmlShutdown()
            return gpu_data
        
        for idx in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            
            # Get GPU name
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            
            # Extract just the GPU model name (e.g., "NVIDIA Thor" -> "Thor")
            # This matches the naming convention expected by the GUI
            if name.startswith("NVIDIA "):
                name = name.replace("NVIDIA ", "")
            
            # Get utilization - this seems to be supported
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            # Get memory info - may not be supported on Jetson
            try:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_used = mem_info.used
                memory_total = mem_info.total
                memory_free = mem_info.free
            except Exception as e:
                logger.debug("Memory info not supported: {}".format(e))
                memory_used = None
                memory_total = None
                memory_free = None
            
            # Get temperature - may not be supported
            try:
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception as e:
                logger.debug("Temperature not supported: {}".format(e))
                temperature = None
            
            # Get power info - may not be supported on Jetson
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to Watts
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            except Exception as e:
                logger.debug("Power info not supported: {}".format(e))
                power_draw = None
                power_limit = None
            
            # Get clock speeds - may not be supported on Jetson
            try:
                sm_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_SM)
                mem_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
            except Exception as e:
                logger.debug("Clock info not supported: {}".format(e))
                sm_clock = None
                mem_clock = None
            
            # Try to get max clocks
            try:
                max_sm_clock = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_SM)
                min_sm_clock = None  # NVML doesn't provide min clocks
            except Exception:
                max_sm_clock = None
                min_sm_clock = None
                
            # Build frequency data with expected structure
            # GUI expects these keys to be present, even if values are None
            freq_data = {
                'governor': 'nvml',  # Indicate NVML control
                'cur': sm_clock if sm_clock is not None else 0,  # Default to 0 if not available
                'max': max_sm_clock if max_sm_clock is not None else 0,
                'min': min_sm_clock if min_sm_clock is not None else 0,
            }
            if mem_clock is not None:
                freq_data['mem'] = mem_clock
                
            # Build status dict with available data
            status = {
                'load': float(utilization.gpu),
                '3d_scaling': False,  # Not available via NVML
                'railgate': False,  # Not available via NVML
                'tpc_pg_mask': False  # Not available via NVML
            }
            
            # Add optional fields only if available
            if memory_used is not None:
                status['memory_used'] = memory_used
            if memory_total is not None:
                status['memory_total'] = memory_total
            if memory_free is not None:
                status['memory_free'] = memory_free
            if temperature is not None:
                status['temperature'] = temperature
            if power_draw is not None:
                status['power_draw'] = power_draw
            if power_limit is not None:
                status['power_limit'] = power_limit
            
            gpu_data[name] = {
                'type': 'integrated',  # For Jetson devices
                'status': status,
                'freq': freq_data,  # Always include freq, even if empty or partial
                'power_control': 'nvml'
            }
            
        pynvml.nvmlShutdown()
        
    except Exception as e:
        logger.debug("NVML error: {}".format(e))
        
    return gpu_data


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
        # Check if we should use NVML (Jetpack 7.0+)
        self._use_nvml = check_jetpack_version() and NVML_AVAILABLE
        
        if self._use_nvml:
            logger.info("Jetpack 7.0+ detected with NVML available, checking device support...")
            # Try to check if NVML actually detects any devices
            try:
                if NVML_AVAILABLE:
                    pynvml.nvmlInit()
                    device_count = pynvml.nvmlDeviceGetCount()
                    pynvml.nvmlShutdown()
                    
                    if device_count == 0:
                        logger.info("NVML detected 0 devices, falling back to traditional method")
                        self._use_nvml = False
                    else:
                        logger.info("NVML detected {} device(s), using NVML for monitoring".format(device_count))
                        self._gpu_list = {}  # Will be populated dynamically by NVML
            except Exception as e:
                logger.warning("NVML check failed: {}, falling back to traditional method".format(e))
                self._use_nvml = False
        
        # If not using NVML (either not available or no devices detected)
        if not self._use_nvml:
            # Detect integrated GPU using traditional method
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
        if self._use_nvml:
            logger.warning("3D scaling control not available via NVML (Jetpack 7.0+)")
            return False
            
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
        if self._use_nvml:
            logger.warning("Railgate control not available via NVML (Jetpack 7.0+)")
            return False
            
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
        if self._use_nvml:
            # Use NVML for Jetpack 7.0+
            return nvml_read_gpu_status()
        else:
            # Use traditional method for older Jetpack versions
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
