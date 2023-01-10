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

##### PLEASE NOTE #####
# This package WILL sobstitute the jetson_variables variable in the future

import os
import re

CUDA_TABLE = {
    'tegra234': '8.7',  # JETSON ORIN
    'tegra210': '7.2',  # JETSON XAVIER
    'tegra186': '6.2',  # JETSON TX2
    'tegra210': '5.3',  # JETSON TX1
    'tegra124': '3.2',  # JETSON TK1
}


MODULE_NAME_TABLE = {
    'p3701-0000': 'NVIDIA Jetson AGX Orin',
    'p3668-0000': 'NVIDIA Jetson Xavier NX (developer kit)',
    'p3668-0001': 'NVIDIA Jetson Xavier NX',
    'p3668-0003': 'NVIDIA Jetson Xavier NX 16GB',
    'p2888-0001': 'NVIDIA Jetson AGX Xavier (16 GB ram)',
    'p2888-0004': 'NVIDIA Jetson AGX Xavier (32 GB ram)',
    'p2888-0005': 'NVIDIA Jetson AGX Xavier (64 GB ram)',
    'p2888-0008': 'NVIDIA Jetson AGX Xavier Industrial (32 GB ram)',
    'pm375-000': 'NVIDIA Jetson TK1',
}
#######################
# DO NOT EDIT FROM HERE
#######################
DTSFILENAME_RE = re.compile(r'(.*)-p')


def get_variables():
    os_variables = {}
    # Read Jetson model
    if os.path.isfile('/sys/firmware/devicetree/base/model'):
        with open("/sys/firmware/devicetree/base/model", 'r') as f:
            jetson_model = f.readline().rstrip('\x00')
        os_variables['JETSON_MODEL'] = jetson_model
    # Decode dtsfilename
    if os.path.isfile("/proc/device-tree/nvidia,dtsfilename"):
        # Read dtsfilename
        # AGX Orin - tegra234-p3701-0000-p3737-0000
        # Xavier NX - tegra210-p3448-0000-p3449-0000-b00
        # TX2 - tegra186-quill-p3310-1000-c03-00-base
        # TX1 - tegra210-jetson-tx1-p2597-2180-a01-devkit
        # TK1 - tegra124-jetson_tk1-pm375-000-c00-00
        with open("/proc/device-tree/nvidia,dtsfilename", 'r') as f:
            dtsfilename = f.readline().rstrip('\x00').split('/')
        # Decode codename
        os_variables['JETSON_CODENAME'] = dtsfilename[-3]
        # Decode NVIDIA Jetson type, model and board
        jetson_soc_module_board = dtsfilename[-1].rstrip('.dts').split('-')
        os_variables['JETSON_SOC'] = jetson_soc_module_board[0]
        # print("type: {jetson_type}".format(jetson_type=os_variables['JETSON_TYPE']))
        parts = '-'.join(jetson_soc_module_board[1:])
        match = re.match(DTSFILENAME_RE, parts)
        if match:
            module = match.group(1)
            os_variables['JETSON_MODULE'] = module
            # print(f"module: {module}".format(module=module))
            carrier = parts.replace("{module}-".format(module=module), '')
            os_variables['JETSON_CARRIER'] = carrier
            # print(f"carrier: {carrier}".format(carrier=carrier))
            # Decode Jetson type of module
            # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/index.html
            os_variables['JETSON_TYPE_MODULE'] = MODULE_NAME_TABLE.get(module, '')
        else:
            print("jetson model and board not available")
    # Decode CUDA architecure
    os_variables['JETSON_CUDA_ARCH_BIN'] = CUDA_TABLE.get(os_variables['JETSON_SOC'], '')
    # Read serial number
    if os.path.isfile('/sys/firmware/devicetree/base/serial-number'):
        with open("/sys/firmware/devicetree/base/serial-number", 'r') as f:
            serial_number = f.readline().rstrip('\x00')
        os_variables['JETSON_SERIAL_NUMBER'] = serial_number
    return os_variables


if __name__ == "__main__":
    os_variables = get_variables()
    for name, value in os_variables.items():
        print(f"{name}: {value}")
# EOF
