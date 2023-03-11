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
import argparse
from .core.common import get_var
from .core.nvpmodel import nvpmodel_query
from .core.hardware import get_platform_variables
from .core.jetson_variables import get_jetson_variables
from .core.jetson_libraries import get_libraries, get_cuda, get_opencv
from .core.exceptions import JtopException
from .service import status_service
from .terminal_colors import bcolors
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
COPYRIGHT_RE = re.compile(r""".*__copyright__ = ["'](.*?)['"]""", re.S)


def main():
    parser = argparse.ArgumentParser(
        description='Show detailed information about this board. Machine, Jetpack, libraries and other',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', dest="verbose", help='Show all variables', action="store_true", default=False)
    parser.add_argument('-s', '--serial', dest="serial", help='Show serial number', action="store_true", default=False)
    # Copyrights
    print("Software part of jetson-stats {version} - {copyright}".format(version=get_var(VERSION_RE), copyright=get_var(COPYRIGHT_RE)))
    # Parse arguments
    args = parser.parse_args()
    # Read all Jetson Variables
    jetson = get_jetson_variables()
    # Extract and remove Serial Number
    serial_number = jetson['Serial Number']
    del jetson['Serial Number']
    # Print headline
    if jetson['Jetpack']:
        print("Model: {model} - Jetpack {jetpack} [L4T {L4T}]".format(model=bcolors.bold(jetson['Model']),
              jetpack=bcolors.bold(jetson['Jetpack']), L4T=bcolors.bold(jetson['L4T'])))
    else:
        print(bcolors.fail(bcolors.bold("Jetpack missing!")))
        print(" - Model: {model}".format(model=bcolors.bold(jetson['Model'])))
        print(" - L4T: {L4T}".format(L4T=bcolors.bold(jetson['L4T'])))
    del jetson['Model']
    del jetson['Jetpack']
    del jetson['L4T']
    # Print NVP model status
    try:
        nvpmodel_now = nvpmodel_query()
        print("{service}[{number}]: {name}".format(
            service=bcolors.ok(bcolors.bold("NV Power Mode")),
            name=bcolors.bold(nvpmodel_now['name']),
            number=bcolors.bold(nvpmodel_now['id'])))
    except JtopException:
        pass
    # Print serial number
    if serial_number:
        if not args.serial:
            serial_number = "[XXX Show with: jetson_release -s XXX]"
        print("{sn_string} {serial_number}".format(sn_string=bcolors.ok(bcolors.bold("Serial Number:")), serial_number=serial_number))
    # Print jetson hardware variables
    if not args.verbose:
        for name in ['699-level Part Number', 'SoC', 'Codename', 'BoardIDs', 'CUDA Arch BIN']:
            if name in jetson:
                del jetson[name]
    print(bcolors.ok(bcolors.bold("Hardware:")))
    for name, variable in jetson.items():
        if not variable:
            variable = bcolors.fail("Not available")
            if name == 'Module' and os.getuid() != 0:
                variable = bcolors.fail("Check with sudo")
        print(" - {name}: {variable}".format(name=bcolors.bold(name), variable=variable))
    # Print platform variables
    plat = get_platform_variables()
    if not args.verbose:
        for name in ['Machine', 'System', 'Python']:
            if name in plat:
                del plat[name]
    print(bcolors.ok(bcolors.bold("Platform:")))
    for name, variable in plat.items():
        if not variable:
            variable = bcolors.fail("Not available")
        print(" - {name}: {variable}".format(name=bcolors.bold(name), variable=variable))
    # jtop status
    print(bcolors.ok(bcolors.bold("jtop:")))
    # Print status jetson-stats service
    print(" - {name}: {value}".format(name=bcolors.bold("Version"), value=get_var(VERSION_RE)))
    jtop_status = bcolors.ok("Active") if status_service() else bcolors.fail("Inactive")
    print(" - {name}: {value}".format(name=bcolors.bold("Service"), value=jtop_status))
    # Read CUDA status
    print(bcolors.ok(bcolors.bold("Libraries:")))
    cuda_version = get_cuda()
    if cuda_version:
        print(" - {name}: {value}".format(name=bcolors.bold('CUDA'), value=cuda_version))
    else:
        print(" - {name}: {value}".format(name=bcolors.bold('CUDA'), value=bcolors.fail("Not installed")))
    # Read all libraries
    os_variables = get_libraries()
    for name, value in os_variables.items():
        if not value:
            value = bcolors.fail("Not installed")
        print(" - {name}: {value}".format(name=bcolors.bold(name), value=value))
    # Read OpenCV status
    opencv_version, opencv_cuda = get_opencv()
    if opencv_version:
        opencv_cuda_string = bcolors.ok("YES") if opencv_cuda else bcolors.fail("NO")
        opencv_string = "{name}: {value}".format(name=bcolors.bold('OpenCV'), value=opencv_version)
        print(" - {opencv_string} - with CUDA: {opencv_cuda}".format(opencv_string=opencv_string, opencv_cuda=opencv_cuda_string))
    else:
        print(" - {name}: {value}".format(name=bcolors.bold('OpenCV'), value=bcolors.fail("Not installed")))


if __name__ == "__main__":
    main()
# EOF
