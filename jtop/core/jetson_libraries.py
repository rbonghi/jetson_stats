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
import subprocess
from .common import cat
from .command import Command
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


MODULES = ['cuDNN', 'TensorRT.', 'VPI']  # 'Visionworks'
CUDA_FILE_RE = re.compile(r'CUDA Version (.*)')
CUDA_NVCC_RE = re.compile(r'V([0-9]+.[0-9]+.[0-9]+)')


def get_cuda():
    cuda_version = ''
    if os.path.isfile("/usr/local/cuda/version.txt"):
        version = cat("/usr/local/cuda/version.txt")
        match = re.search(CUDA_FILE_RE, version)
        if match:
            cuda_version = match.group(1)
    elif os.path.isfile("/usr/local/cuda/bin/nvcc"):
        cmd = Command(['/usr/local/cuda/bin/nvcc', '--version'])
        try:
            lines = cmd()
            for line in lines:
                match = re.search(CUDA_NVCC_RE, line)
                if match:
                    cuda_version = match.group(1)
                    break
        except (OSError, Command.CommandException):
            pass
    elif subprocess.call(["which", "nvcc"], stdout=subprocess.DEVNULL) == 0:
        cmd = Command(['nvcc', '--version'])
        try:
            lines = cmd()
            for line in lines:
                match = re.search(CUDA_NVCC_RE, line)
                if match:
                    cuda_version = match.group(1)
                    break
        except (OSError, Command.CommandException):
            pass
    return cuda_version


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
                opencv_cuda = True
                break
            if "Use Cuda" in line:
                opencv_cuda = False if "NO" in line else True
                break
    except (OSError, Command.CommandException):
        pass
    return opencv_version, opencv_cuda


def get_all_modules():
    modules = {}
    # Extract all modules in dpkg -l
    dpkg = Command(['dpkg', '-l'])
    try:
        lines = dpkg()
        for row in lines:
            row = re.sub(r'\n+ +', '\n', row)  # remove spaces at the start of lines and empty lines
            row = re.sub(r'\s +', '\t', row)  # replace two or more spaces with tab
            cells = row.split('\t')
            if len(cells) > 2:
                name = cells[1]
                version = cells[2]
                if version not in ['arm64', 'amd64']:
                    modules[name] = version
    except (OSError, Command.CommandException):
        pass
    return modules


def get_libraries():
    os_variables = {}
    # Find all modules
    modules = get_all_modules()
    for name in MODULES:
        # Fix TensorRT search #462
        name_dict = name[:-1] if name.endswith('.') else name
        os_variables[name_dict] = ''
        # Find version if installed
        for module, version in modules.items():
            if name.endswith('.') and name.lower()[:-1] == module:
                os_variables[name_dict] = version.split('-')[0]
                break
            if name.lower() in module:
                os_variables[name_dict] = version.split('-')[0]
                break
    # Get Vulkan output
    cmd_vulkaninfo = Command(['which', 'vulkaninfo'])
    try:
        lines = cmd_vulkaninfo()
        # Extract version
        if not lines:
            raise Command.CommandException("Missing command", -3)
        cmd_vulkan = Command(lines)
        lines = cmd_vulkan()
        for line in lines:
            if "Vulkan Instance Version" in line:
                os_variables['Vulkan'] = line.lstrip("Vulkan Instance Version: ")
                break
    except (OSError, Command.CommandException):
        pass
    return os_variables


if __name__ == "__main__":
    # Get CUDA
    cuda_version = get_cuda()
    if cuda_version:
        print("CUDA: {version}".format(version=cuda_version))
    else:
        print("CUDA not installed!")
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
