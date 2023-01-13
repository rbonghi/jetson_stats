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
import platform
try:
    from smbus import SMBus
except ImportError:
    print("Skip for setup.py")
# Load distro library from python3 or use platform
try:
    import distro
except ImportError:
    distro = platform

from .common import cat
from .jetson_l4t import get_nvidia_l4t, get_nvidia_jetpack


CUDA_TABLE = {
    'tegra23x': '8.7',  # JETSON ORIN - tegra234
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
    # Other modules
    'p2595-0000-A0': 'Nintendo Switch'
}
# ---------------------
# DO NOT EDIT FROM HERE
# ---------------------
DTSFILENAME_RE = re.compile(r'(.*)-p')
SOC_RE = re.compile(r'[0-9]+')


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
    for bus_number in range(3):
        try:
            bus = SMBus(bus_number)
            part_number = bus.read_i2c_block_data(0x50, 20, 29)
            part_number = ''.join(chr(i) for i in part_number)
            # print(part_number)
            board_id = part_number[5:9]
            sku = part_number[10:14]
            jetson_part_number = "p{board_id}-{sku}".format(board_id=board_id, sku=sku)
            return part_number, jetson_part_number
        except IOError:
            break
        except OSError:
            # print("Error I2C bus: {bus_number}".format(bus_number=bus_number))
            pass
    return part_number, jetson_part_number


def get_jetson_variables():
    hardware = {}
    # Read Jetson model
    model = ''
    if os.path.isfile('/sys/firmware/devicetree/base/model'):
        model = cat("/sys/firmware/devicetree/base/model")
        model = "p{model}".format(model=model.replace(':', '-'))
    hardware['Model'] = model
    # Find part number from I2C
    # https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3243/index.html
    # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/HR/JetsonEepromLayout.html
    part_number, jetson_part_number = get_part_number()
    hardware['699-level Part Number'] = part_number
    hardware['P-Number'] = jetson_part_number
    # Read boardids
    if os.path.isfile('/proc/device-tree/nvidia,boardids'):
        boardids = cat("/proc/device-tree/nvidia,boardids")
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
        if "/dvs/git/dirty/git-master_linux/kernel" in dtsfilename or 'kernel-dts' in dtsfilename:
            # Decode codename
            hardware['Codename'] = dtsfilename.split('/')[-3].capitalize()
    # Read serial number
    serial = ''
    if os.path.isfile('/sys/firmware/devicetree/base/serial-number'):
        serial = cat("/sys/firmware/devicetree/base/serial-number")
    hardware['Serial Number'] = serial
    # Extract L4T
    hardware['L4T'] = get_nvidia_l4t()
    # Read Jetpack
    hardware['Jetpack'] = get_nvidia_jetpack(hardware['L4T'])
    return hardware


def get_platform_variables():
    return {
        'Machine': platform.machine(),
        'System': platform.system(),
        'Distribution': " ".join(distro.linux_distribution()),
        'Release': platform.release(),
        'Python': platform.python_version(),
    }


def export_variables(hardware):
    # Export variables to be loaded on bash script
    # https://blog.tintoy.io/2017/06/exporting-environment-variables-from-python-to-bash/
    for name, value in hardware.items():
        # Escape symbols commonly used by Bash.
        value = value.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        name = name.upper().replace("-", "_").replace(" ", "_")
        print('export JETSON_{}="{}"'.format(name, value))


if __name__ == "__main__":
    hardware = get_jetson_variables()
    # Test output variables
    export_variables(hardware)
# EOF
