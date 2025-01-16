#!/usr/bin/python
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
import re
import sys
import warnings
import logging
from shutil import copyfile
try:
    from smbus2 import SMBus  # pyright: ignore[reportMissingImports]
except ImportError:
    print("Skip for setup.py")

from .common import cat
from .command import Command
# Create logger
logger = logging.getLogger(__name__)
# https://github.com/robotframework/robotframework/issues/2552
if not sys.warnoptions:
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='runpy')

# ---------------------
# JETPACK DETECTION
# ---------------------
# Write version of jetpack installed
# https://developer.nvidia.com/embedded/jetpack-archive
NVIDIA_JETPACK = {
    # -------- JP6 --------
    "36.4.3": "6.2",
    "36.4.2": "6.1 (rev1)",
    "36.4.0": "6.1",
    "36.3.0": "6.0",
    "36.2.0": "6.0 DP",
    "36.0.0": "6.0 EA",
    # -------- JP5 --------
    "35.6.0": "5.1.4",
    "35.5.0": "5.1.3",
    "35.4.1": "5.1.2",
    "35.3.1": "5.1.1",
    "35.3.0": "5.1.1 PRE",
    "35.2.1": "5.1",
    "35.1.0": "5.0.2 GA",
    "34.1.1": "5.0.1 DP",
    "34.1.0": "5.0 DP",
    "34.0.1": "5.0 PRE-DP",
    # -------- JP4 --------
    "32.7.6": "4.6.6",
    "32.7.5": "4.6.5",
    "32.7.4": "4.6.4",
    "32.7.3": "4.6.3",
    "32.7.2": "4.6.2",
    "32.7.1": "4.6.1",
    "32.6.1": "4.6",
    "32.5.2": "4.5.1",
    "32.5.1": "4.5.1",
    "32.5.0": "4.5",
    "32.5": "4.5",
    "32.4.4": "4.4.1",
    "32.4.3": "4.4",
    "32.4.2": "4.4 DP",
    "32.3.1": "4.3",
    "32.2.3": "4.2.3",
    "32.2.1": "4.2.2",
    "32.2.0": "4.2.1",
    "32.2": "4.2.1",
    "32.1.0": "4.2",
    "32.1": "4.2",
    "31.1.0": "4.1.1",
    "31.1": "4.1.1",
    "31.0.2": "4.1",
    "31.0.1": "4.0",
    # -------- Old JP --------
    "28.4.0": "3.3.3",
    "28.2.1": "3.3 | 3.2.1",
    "28.2.0": "3.2",
    "28.2": "3.2",
    "28.1.0": "3.1",
    "28.1": "3.1",
    "27.1.0": "3.0",
    "27.1": "3.0",
    "24.2.1": "3.0 | 2.3.1",
    "24.2.0": "2.3",
    "24.2": "2.3",
    "24.1.0": "2.2.1 | 2.2",
    "24.1": "2.2.1 | 2.2",
    "23.2.0": "2.1",
    "23.2": "2.1",
    "23.1.0": "2.0",
    "23.1": "2.0",
    "21.5.0": "2.3.1 | 2.3",
    "21.5": "2.3.1 | 2.3",
    "21.4.0": "2.2 | 2.1 | 2.0 | 1.2 DP",
    "21.4": "2.2 | 2.1 | 2.0 | 1.2 DP",
    "21.3.0": "1.1 DP",
    "21.3": "1.1 DP",
    "21.2.0": "1.0 DP",
    "21.2": "1.0 DP",
}


CUDA_TABLE = {
    'tegra234': '8.7',  # JETSON ORIN - tegra234
    'tegra23x': '8.7',  # JETSON ORIN - tegra234
    'tegra194': '7.2',  # JETSON XAVIER
    'tegra186': '6.2',  # JETSON TX2
    'tegra210': '5.3',  # JETSON TX1
    'tegra124': '3.2',  # JETSON TK1
}

# Module reference
# https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3231/index.html
# https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/IN/QuickStart.html
MODULE_NAME_TABLE = {
    'p3767-0005': 'NVIDIA Jetson Orin Nano (Developer kit)',
    'p3767-0004': 'NVIDIA Jetson Orin Nano (4GB ram)',
    'p3767-0003': 'NVIDIA Jetson Orin Nano (8GB ram)',
    'p3767-0001': 'NVIDIA Jetson Orin NX (8GB ram)',
    'p3767-0000': 'NVIDIA Jetson Orin NX (16GB ram)',
    'p3701-0005': 'NVIDIA Jetson AGX Orin (64GB ram)',
    'p3701-0004': 'NVIDIA Jetson AGX Orin (32GB ram)',
    'p3701-0002': 'NVIDIA Jetson IGX Orin (Developer kit)',
    'p3701-0000': 'NVIDIA Jetson AGX Orin',
    'p3668-0003': 'NVIDIA Jetson Xavier NX (16GB ram)',
    'p3668-0001': 'NVIDIA Jetson Xavier NX',
    'p3668-0000': 'NVIDIA Jetson Xavier NX (Developer kit)',
    'p2888-0008': 'NVIDIA Jetson AGX Xavier Industrial (32 GB ram)',
    'p2888-0006': 'NVIDIA Jetson AGX Xavier (8 GB ram)',
    'p2888-0005': 'NVIDIA Jetson AGX Xavier (64 GB ram)',
    'p2888-0004': 'NVIDIA Jetson AGX Xavier (32 GB ram)',
    'p2888-0003': 'NVIDIA Jetson AGX Xavier (32 GB ram)',
    'p2888-0001': 'NVIDIA Jetson AGX Xavier (16 GB ram)',
    'p3448-0003': 'NVIDIA Jetson Nano (2 GB ram)',
    'p3448-0002': 'NVIDIA Jetson Nano module (16Gb eMMC)',
    'p3448-0000': 'NVIDIA Jetson Nano (4 GB ram)',
    'p3636-0001': 'NVIDIA Jetson TX2 NX',
    'p3509-0000': 'NVIDIA Jetson TX2 NX',
    'p3489-0888': 'NVIDIA Jetson TX2 (4 GB ram)',
    'p3489-0000': 'NVIDIA Jetson TX2i',
    'p3310-1000': 'NVIDIA Jetson TX2',
    'p2180-1000': 'NVIDIA Jetson TX1',
    'r375-0001': 'NVIDIA Jetson TK1',
    'p3904-0000': 'NVIDIA Clara AGX',
    # Other modules
    'p2595-0000-A0': 'Nintendo Switch'
}
# ---------------------
# DO NOT EDIT FROM HERE
# ---------------------
# THIS SCRIPT MUST HAVE .SH !
JTOP_VARIABLE_FILE = 'jtop_env.sh'
DTSFILENAME_RE = re.compile(r'(.*)-p')
SOC_RE = re.compile(r'[0-9]+')
DPKG_L4T_CORE_RE = re.compile(r'^nvidia-l4t-core.*install$')
# Number 7 is for Jetson TX2
I2C_EEPROM_BUS = [0, 1, 2, 7]
RAW_FILES = ['/etc/nv_tegra_release',
             '/sys/firmware/devicetree/base/model',
             '/proc/device-tree/nvidia,boardids',
             '/proc/device-tree/compatible',
             '/proc/device-tree/nvidia,dtsfilename']


def read_i2c_raw_data(bus, registry, size_block):
    string_data = ""
    for idx in range(256 // size_block):
        # Extract part number expected module
        data = bus.read_i2c_block_data(registry, idx * size_block, size_block)
        string_data += ' '.join(["{:02X}".format(x) for x in data]) + " " * 4
        string_data += ''.join([chr(x) if chr(x).isprintable() else "." for x in data]) + "\n"
    return string_data


def get_jetson_raw_output():
    raw_output = {}
    # Catch all output from all files
    for file in RAW_FILES:
        raw_output[file] = cat(file).strip('\n') if os.path.isfile(file) else "No such file or directory"
    # Read all output from all I2C ports
    for bus_number in I2C_EEPROM_BUS:
        try:
            # Forcing read SMBus added from Jetpack 6.0 DP
            bus = SMBus(bus_number, force=True)
            size_block = 16
            raw_output['I2C-{num}-0x50'.format(num=bus_number)] = read_i2c_raw_data(bus, 0x50, size_block)
            raw_output['I2C-{num}-0x56'.format(num=bus_number)] = read_i2c_raw_data(bus, 0x56, size_block)
        except (IOError, OSError):
            # print("Error I2C bus: {bus_number}".format(bus_number=bus_number))
            raw_output['I2C-{num}'.format(num=bus_number)] = 'FAIL'
    return raw_output


def check_dpkg_nvidia_l4t_core():
    dpkg = Command(['dpkg', '--get-selections'])
    lines = dpkg()
    for line in lines:
        if re.match(DPKG_L4T_CORE_RE, line):
            return True
    return False


def get_nvidia_l4t():
    # Read NV TEGRA RELEASE
    if os.path.isfile('/etc/nv_tegra_release'):
        # NVIDIA Jetson version
        # reference https://devtalk.nvidia.com/default/topic/860092/jetson-tk1/how-do-i-know-what-version-of-l4t-my-jetson-tk1-is-running-/
        # https://stackoverflow.com/questions/16817646/extract-version-number-from-a-string
        # https://askubuntu.com/questions/319307/reliably-check-if-a-package-is-installed-or-not
        # https://github.com/dusty-nv/jetson-inference/blob/7e81381a96c1ac5f57f1728afbfdec7f1bfeffc2/tools/install-pytorch.sh#L296
        nv_tegra_release = cat("/etc/nv_tegra_release").split(", ")
        l4t_release = nv_tegra_release[0].lstrip("# R").rstrip(" (release)")
        l4t_revision = nv_tegra_release[1].lstrip("REVISION: ")
        return '.'.join([l4t_release, l4t_revision])
        # Ectract GCID - DO NOT NEEDED
        # os_variables['GCID'] = nv_tegra_release[2].lstrip("GCID: ")
        # Ectract SOC - DO NOT USE THIS LINE! CONTAINS ALWAYS WRONG OUTPUT
        # number = re.search(SOC_RE, nv_tegra_release[3].lstrip("BOARD: ")).group()
        # os_variables['SOC'] = "tegra{number}".format(number=number)
    elif check_dpkg_nvidia_l4t_core():
        dpkg = Command(['dpkg-query', '--showformat=\'${Version}\'', '--show', 'nvidia-l4t-core'])
        l4t = dpkg()[0]
        return l4t.split('-')[0].lstrip('\'')
    # If not find any L4T return empty string
    return ''


def get_variables_from_dtsfilename():
    hardware = {}
    # Decode dtsfilename
    if os.path.isfile("/proc/device-tree/nvidia,dtsfilename"):
        # Read dtsfilename
        # AGX Orin - tegra234-p3701-0000-p3737-0000
        # Nano - tegra210-p3448-0000-p3449-0000-b00
        # TX2 - tegra186-quill-p3310-1000-c03-00-base
        # TX1 - tegra210-jetson-tx1-p2597-2180-a01-devkit
        # TK1 - tegra124-jetson_tk1-pm375-000-c00-00
        dtsfilename = cat("/proc/device-tree/nvidia,dtsfilename").split('/')
        # Decode codename
        hardware['CODENAME'] = dtsfilename[-3]
        # Decode NVIDIA Jetson type, model and board
        jetson_soc_module_board = dtsfilename[-1].rstrip('.dts').split('-')
        hardware['SOC'] = jetson_soc_module_board[0]
        # print("type: {jetson_type}".format(jetson_type=hardware['TYPE']))
        parts = '-'.join(jetson_soc_module_board[1:])
        match = re.match(DTSFILENAME_RE, parts)
        if match:
            module = match.group(1)
            hardware['PART_NUMBER'] = module
            # print(f"module: {module}".format(module=module))
            carrier = parts.replace("{module}-".format(module=module), '')
            hardware['CARRIER'] = carrier
            # print(f"carrier: {carrier}".format(carrier=carrier))
            # Decode Jetson type of module
            # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/index.html
            hardware['MODULE'] = MODULE_NAME_TABLE.get(module, '')
        else:
            print("jetson model and board not available")
            print(parts)
    # Decode CUDA architecure
    hardware['CUDA_ARCH_BIN'] = CUDA_TABLE.get(hardware['SOC'], '')
    return hardware


def get_part_number():
    part_number = ''
    jetson_part_number = ''
    # Find 699-level part number from EEPROM and extract P-number
    for bus_number in I2C_EEPROM_BUS:
        try:
            # Forcing read SMBus added from Jetpack 6.0 DP
            bus = SMBus(bus_number, force=True)
            part_number = bus.read_i2c_block_data(0x50, 20, 29)
            part_number = ''.join(chr(i) for i in part_number).rstrip('\x00')
            # print(part_number)
            board_id = part_number[5:9]
            sku = part_number[10:14]
            jetson_part_number = "p{board_id}-{sku}".format(board_id=board_id, sku=sku)
            return part_number, jetson_part_number
        except (IOError, OSError):
            # logger.error("I2C[{bus_number}] [Errno {errno}]: {msg}".format(errno=e.errno, bus_number=bus_number, msg=e.strerror))
            pass
    return part_number, jetson_part_number


def get_jetson_variables():
    hardware = {}
    # Read Jetson model
    model = ''
    if os.path.isfile('/sys/firmware/devicetree/base/model'):
        model = cat("/sys/firmware/devicetree/base/model")
    hardware['Model'] = model
    # Find part number from I2C
    # https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3243/index.html
    # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/HR/JetsonEepromLayout.html
    part_number, jetson_part_number = get_part_number()
    # Add only if there is a part number
    if part_number:
        hardware['699-level Part Number'] = part_number
        hardware['P-Number'] = jetson_part_number
    # Read boardids
    if os.path.isfile('/proc/device-tree/nvidia,boardids'):
        boardids = cat("/proc/device-tree/nvidia,boardids")
        boardids = "p{boardids}".format(boardids=boardids.replace(':', '-'))
        hardware['BoardIDs'] = boardids
    # Find module from part_number
    module = ''
    if jetson_part_number:
        module = MODULE_NAME_TABLE.get(jetson_part_number, '')
    elif 'BoardIDs' in hardware:
        module = MODULE_NAME_TABLE.get(hardware['BoardIDs'], '')
    hardware['Module'] = module
    # Decode SOC
    compatible = ''
    if os.path.isfile("/proc/device-tree/compatible"):
        compatible = cat("/proc/device-tree/compatible").split(',')
        compatible = compatible[-1]
    hardware['SoC'] = compatible
    # Decode CUDA architecture
    cuda_arch = ''
    for cuda, arch in CUDA_TABLE.items():
        if cuda in hardware['SoC']:
            cuda_arch = arch
            break
    hardware['CUDA Arch BIN'] = cuda_arch
    # Find codename
    if os.path.isfile("/proc/device-tree/nvidia,dtsfilename"):
        # Read dtsfilename
        # AGX Orin - tegra234-p3701-0000-p3737-0000
        # Nano - tegra210-p3448-0000-p3449-0000-b00
        # TX2 - tegra186-quill-p3310-1000-c03-00-base
        # TX1 - tegra210-jetson-tx1-p2597-2180-a01-devkit
        # TK1 - tegra124-jetson_tk1-pm375-000-c00-00
        dtsfilename = cat("/proc/device-tree/nvidia,dtsfilename")
        if 'kernel-dts' in dtsfilename:
            # Decode codename
            idx_codename = dtsfilename.split('/').index('kernel-dts') - 1
            hardware['Codename'] = dtsfilename.split('/')[idx_codename].capitalize()
        elif "/dvs/git/dirty/git-master_linux/kernel" in dtsfilename:
            # Decode codename for TK1
            hardware['Codename'] = dtsfilename.split('/')[-3].capitalize()
    # Read serial number
    serial = ''
    if os.path.isfile('/sys/firmware/devicetree/base/serial-number'):
        serial = cat("/sys/firmware/devicetree/base/serial-number")
    hardware['Serial Number'] = serial
    # Extract L4T
    hardware['L4T'] = get_nvidia_l4t()
    # Read Jetpack
    hardware['Jetpack'] = NVIDIA_JETPACK.get(hardware['L4T'], '')
    return hardware


def status_variables(name=JTOP_VARIABLE_FILE):
    return os.path.isfile('/etc/profile.d/{name}'.format(name=name))


def uninstall_variables(name=JTOP_VARIABLE_FILE):
    if os.path.isfile('/etc/profile.d/{name}'.format(name=name)):
        logger.info("Found {name}".format(name=name))
        # Remove old jetson_stats variable
        os.remove('/etc/profile.d/{name}'.format(name=name))
        logger.info(" - Remove {name} from /etc/profile.d/".format(name=name))


def install_variables(package_root, copy, name=JTOP_VARIABLE_FILE):
    logger.info("Install {name} variables".format(name=name))
    variables_install_path = '/etc/profile.d/{name}'.format(name=name)
    variables_package_path = '{package_root}/scripts/{name}'.format(package_root=package_root, name=name)
    # remove if exist file
    if os.path.isfile(variables_install_path) or os.path.islink(variables_install_path):
        logger.info(" - Remove old {path}".format(path=variables_install_path))
        os.remove(variables_install_path)
    if copy:
        type_service = "Copying"
        copyfile(variables_package_path, variables_install_path)
    else:
        type_service = "Linking"
        os.symlink(variables_package_path, variables_install_path)
    # Prompt message
    logger.info(" - {type} {file} -> {path}".format(type=type_service.upper(), file=name, path=variables_install_path))


def export_variables(hardware):
    # Export variables to be loaded on bash script
    # https://blog.tintoy.io/2017/06/exporting-environment-variables-from-python-to-bash/
    for name, value in hardware.items():
        # Escape symbols commonly used by Bash.
        value = value.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        name = name.upper().replace("-", "_").replace(" ", "_")
        print('export JETSON_{}="{}"'.format(name, value))


# If you want to run this script:
# sudo python3 -m jtop.core.jetson_variables
if __name__ == "__main__":
    # Get all variables
    hardware = get_jetson_variables()
    # Remove variables not needed
    if '699-level Part Number' in hardware:
        del hardware['699-level Part Number']
    # Test output variables
    export_variables(hardware)
# EOF
