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

from .jetson_variables import get_jetson_variables
from .common import cat
import os
import logging
import platform
# Load distro library from python3 or use platform
try:
    import distro
except ImportError:
    distro = platform
# Create logger
logger = logging.getLogger(__name__)


def get_parameter(path):
    if os.path.isfile(path):
        return cat(path).strip()


def get_platform_variables():
    return {
        'Machine': platform.machine(),
        'System': platform.system(),
        'Distribution': " ".join(distro.linux_distribution()),
        'Release': platform.release(),
        'Python': platform.python_version(),
    }


def get_x86_64_variables():
    hardware = {}
    hardware_path = "/sys/devices/virtual/dmi/id/"
    items = os.listdir(hardware_path)
    for item in sorted(items):
        if item in ['uevent', 'modalias', 'board_serial', 'bios_release', 'product_uuid', 'chassis_type']:
            continue
        path = os.path.join(hardware_path, item)
        output = ""
        if os.path.isfile(path):
            output = cat(path).strip()
        if not output or output == 'Default string':
            continue
        name = item.replace("_", " ").capitalize()
        hardware[name] = output
    return hardware


def get_hardware():
    # If hardware is ARM check if NVIDIA Jetson
    platform_board = platform.machine()
    logger.info("Hardware detected {}".format(platform_board))
    if platform_board == 'aarch64':
        # Load Jetson data
        jetson = get_jetson_variables()
        # Print main jetson variables
        if '699-level Part Number' in jetson:
            logger.info("NVIDIA Jetson 699-level Part Number={}".format(jetson['699-level Part Number']))
        else:
            logger.error("NVIDIA Jetson No 699-level Part Number detected!")
        if 'Module' in jetson:
            logger.info("NVIDIA Jetson Module={}".format(jetson['Module']))
        else:
            logger.error("NVIDIA Jetson No Module detected!")
        # Check L4T detection
        if jetson['L4T']:
            logger.info("NVIDIA Jetson detected L4T={}".format(jetson['L4T']))
        else:
            logger.error("NVIDIA Jetson L4T not detected!")
        return jetson
    elif platform_board == 'x86_64':
        return get_x86_64_variables()
    else:
        logger.warning("Unrecognized board {}".format(platform_board))
        return {}
# EOF
