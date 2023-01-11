# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020-2023 Raffaello Bonghi.
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
from smbus import SMBus

from .exceptions import JtopException

# ---------------------
# JETPACK DETECTION
# ---------------------
# Write version of jetpack installed
# https://developer.nvidia.com/embedded/jetpack-archive
NVIDIA_JETPACK = {
    # -------- JP5 --------
    "35.1.0": "5.0.2 GA",
    "34.1.1": "5.0.1 DP",
    "34.1.0": "5.0 DP",
    "34.0.1": "5.0 PRE-DP",
    # -------- JP4 --------
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
    'tegra234': '8.7',  # JETSON ORIN
    'tegra194': '7.2',  # JETSON XAVIER
    'tegra186': '6.2',  # JETSON TX2
    'tegra210': '5.3',  # JETSON TX1
    'tegra124': '3.2',  # JETSON TK1
}


MODULE_NAME_TABLE = {
    'p3701-0000': 'NVIDIA Jetson AGX Orin',
    'p3668-0000': 'NVIDIA Jetson Xavier NX (Developer kit)',
    'p3668-0001': 'NVIDIA Jetson Xavier NX',
    'p3668-0003': 'NVIDIA Jetson Xavier NX 16GB',
    'p2888-0001': 'NVIDIA Jetson AGX Xavier (16 GB ram)',
    'p2888-0004': 'NVIDIA Jetson AGX Xavier (32 GB ram)',
    'p2888-0005': 'NVIDIA Jetson AGX Xavier (64 GB ram)',
    'p2888-0006': 'NVIDIA Jetson AGX Xavier (8 GB ram)',
    'p2888-0008': 'NVIDIA Jetson AGX Xavier Industrial (32 GB ram)',
    'p3448-0000': 'NVIDIA Jetson Nano (4 GB ram)',
    'p3448-0002': 'NVIDIA Jetson Nano',
    'p3448-0003': 'NVIDIA Jetson Nano (2 GB ram)',
    'p3509-0000': 'NVIDIA Jetson TX2 NX',
    'p3489-0000': 'NVIDIA Jetson TX2i',
    'p3489-0888': 'NVIDIA Jetson TX2 (4 GB ram)',
    'p3310-1000': 'NVIDIA Jetson TX2',
    'p2180-1000': 'NVIDIA Jetson TX1',
    'r375-0001': 'NVIDIA Jetson TK1',
}
# ---------------------
# DO NOT EDIT FROM HERE
# ---------------------
DTSFILENAME_RE = re.compile(r'(.*)-p')


def get_variables_old():
    os_variables = {}
    # Read Jetson model
    if os.path.isfile('/sys/firmware/devicetree/base/model'):
        with open("/sys/firmware/devicetree/base/model", 'r') as f:
            jetson_model = f.readline().rstrip('\x00')
        os_variables['MODEL'] = jetson_model
    # Decode dtsfilename
    if os.path.isfile("/proc/device-tree/nvidia,dtsfilename"):
        # Read dtsfilename
        # AGX Orin - tegra234-p3701-0000-p3737-0000
        # Nano - tegra210-p3448-0000-p3449-0000-b00
        # TX2 - tegra186-quill-p3310-1000-c03-00-base
        # TX1 - tegra210-jetson-tx1-p2597-2180-a01-devkit
        # TK1 - tegra124-jetson_tk1-pm375-000-c00-00
        with open("/proc/device-tree/nvidia,dtsfilename", 'r') as f:
            dtsfilename = f.readline().rstrip('\x00').split('/')
        # Decode codename
        os_variables['CODENAME'] = dtsfilename[-3]
        # Decode NVIDIA Jetson type, model and board
        jetson_soc_module_board = dtsfilename[-1].rstrip('.dts').split('-')
        os_variables['SOC'] = jetson_soc_module_board[0]
        # print("type: {jetson_type}".format(jetson_type=os_variables['TYPE']))
        parts = '-'.join(jetson_soc_module_board[1:])
        match = re.match(DTSFILENAME_RE, parts)
        if match:
            module = match.group(1)
            os_variables['MODULE'] = module
            # print(f"module: {module}".format(module=module))
            carrier = parts.replace("{module}-".format(module=module), '')
            os_variables['CARRIER'] = carrier
            # print(f"carrier: {carrier}".format(carrier=carrier))
            # Decode Jetson type of module
            # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/index.html
            os_variables['TYPE_MODULE'] = MODULE_NAME_TABLE.get(module, '')
        else:
            print("jetson model and board not available")
            print(parts)
    # Decode CUDA architecure
    os_variables['CUDA_ARCH_BIN'] = CUDA_TABLE.get(os_variables['SOC'], '')

    return os_variables


def get_part_number():
    for bus_number in range(3):
        try:
            bus = SMBus(bus_number)
            part_number_raw = bus.read_i2c_block_data(0x50, 20, 29)
            part_number_raw = ''.join(chr(i) for i in part_number_raw)
            # print(part_number)
            board_id = part_number_raw[5:9]
            sku = part_number_raw[10:14]
            part_number = "p{board_id}-{sku}".format(board_id=board_id, sku=sku)
            return part_number
        except OSError:
            # print("Error I2C bus: {bus_number}".format(bus_number=bus_number))
            pass
    raise JtopException("Error find part number!")


def get_l4t():
    # NVIDIA Jetson version
    # reference https://devtalk.nvidia.com/default/topic/860092/jetson-tk1/how-do-i-know-what-version-of-l4t-my-jetson-tk1-is-running-/
    # https://stackoverflow.com/questions/16817646/extract-version-number-from-a-string
    # https://askubuntu.com/questions/319307/reliably-check-if-a-package-is-installed-or-not
    # https://github.com/dusty-nv/jetson-inference/blob/7e81381a96c1ac5f57f1728afbfdec7f1bfeffc2/tools/install-pytorch.sh#L296
    if os.path.isfile('/etc/nv_tegra_release'):
        with open("/etc/nv_tegra_release", 'r') as f:
            nv_tegra_release = f.readline().rstrip('\x00')
            print(nv_tegra_release)


def get_variables():
    os_variables = {}
    # Read Jetson model
    if os.path.isfile('/sys/firmware/devicetree/base/model'):
        with open("/sys/firmware/devicetree/base/model", 'r') as f:
            jetson_model = f.readline().rstrip('\x00')
        os_variables['MODEL'] = jetson_model
    # Find part number from I2C
    # https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3243/index.html
    # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/HR/JetsonEepromLayout.html
    try:
        part_number = get_part_number()
        os_variables['PART_NUMBER'] = part_number
    except JtopException as e:
        print(e)
    # Find module from part_number
    module = MODULE_NAME_TABLE.get(part_number, '')
    if not module:
        print("Error find module name from {part_number}".format(part_number=part_number))
    os_variables['MODULE'] = module
    # Read serial number
    if os.path.isfile('/sys/firmware/devicetree/base/serial-number'):
        with open("/sys/firmware/devicetree/base/serial-number", 'r') as f:
            serial_number = f.readline().rstrip('\x00')
        os_variables['SERIAL_NUMBER'] = serial_number
    return os_variables


def export_variables(os_variables):
    # Export variables to be loaded on bash script
    # https://blog.tintoy.io/2017/06/exporting-environment-variables-from-python-to-bash/
    for name, value in os_variables.items():
        # Escape symbols commonly used by Bash.
        value = value.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        print('export JETSON_{}="{}"'.format(name, value))


if __name__ == "__main__":
    os_variables = get_variables()
    # Test output variables
    export_variables(os_variables)
# EOF
