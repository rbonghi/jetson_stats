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

import re
from .command import Command

MODULES = ['libcudnn', 'libvisionworks', 'tensorrt', 'vpi']


def get_opencv():
    opencv_version = ''
    opencv_cuda = False
    cmd = Command(['opencv_version'])
    try:
        lines = cmd()
        # Extract OpenCV version
        opencv_version = ''.join(lines)
        # Extract if compiled with CUDA
        cmd = Command(['opencv_version', '--verbose'])
        lines = cmd()
        for line in lines:
            if "NVIDIA CUDA" in line:
                return True
            if "Use Cuda" in line:
                return False if "NO" in line else True
    except FileNotFoundError:
        pass
    return opencv_version, opencv_cuda


def get_all_modules():
    modules = {}
    # Extract all modules in dpkg -l
    dpkg = Command(['dpkg', '-l'])
    lines = dpkg()
    for row in lines:
        row = re.sub(r'\n+ +', '\n', row)  # remove spaces at the start of lines and empty lines
        row = re.sub(r'\s +', '\t', row)  # replace two or more spaces with tab
        cells = row.split('\t')
        if len(cells) > 2:
            name = cells[1]
            version = cells[2]
            modules[name] = version
    return modules


def get_libraries():
    os_variables = {}
    # Find all modules
    modules = get_all_modules()
    for name in MODULES:
        os_variables[name.upper()] = ''
        # Find version if installed
        for module, version in modules.items():
            if name in module:
                os_variables[name.upper()] = version.split('-')[0]
                break
    # Get Vulkan output
    cmd_vulkaninfo = Command(['which', 'vulkaninfo'])
    try:
        lines = cmd_vulkaninfo()
        # Extract version
        cmd_vulkan = Command(lines)
        lines = cmd_vulkan()
        for line in lines:
            if "Vulkan Instance Version" in line:
                os_variables['VULKAN'] = line.lstrip("Vulkan Instance Version: ")
                break
    except FileNotFoundError:
        pass

    return os_variables


if __name__ == "__main__":
    # Find OpenCV
    opencv_version, opencv_cuda = get_opencv()
    if opencv_version:
        opencv_cuda_string = "YES" if opencv_cuda else "NO"
        print("OPENCV: {opencv_version} - with CUDA: {opencv_cuda}".format(opencv_version=opencv_version, opencv_cuda=opencv_cuda_string))
    else:
        print("OPENCV not Installed!")
    # Get all libraries
    os_variables = get_libraries()
    for name, value in os_variables.items():
        print("{name}: {value}".format(name=name, value=value))
# EOF
