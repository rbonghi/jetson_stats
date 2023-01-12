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

import argparse
from .core import get_jetson_variables, get_cuda, get_opencv, get_libraries, NVPModelService
from .service import status_service
from .terminal_colors import bcolors


def main():
    parser = argparse.ArgumentParser(
        description='Show detailed information about this board. Machine, Jetpack, libraries and other',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', dest="verbose", help='Show all variables', action="store_true", default=False)
    # Parse arguments
    args = parser.parse_args()
    # Read all Jetson Variables
    jetson = get_jetson_variables()
    # Print headline
    # jetson['Jetpack'] = ''
    if jetson['Jetpack']:
        print("Model: {model} - Jetpack {jetpack} [L4T {L4T}]".format(model=bcolors.bold(jetson['Model']),
              jetpack=bcolors.bold(jetson['Jetpack']), L4T=bcolors.bold(jetson['L4T'])))
    else:
        print(bcolors.fail(bcolors.bold("Jetpack missing!")))
        print(" - Model: {model}".format(model=bcolors.bold(jetson['Model'])))
        print(" - L4T: {L4T}".format(L4T=bcolors.bold(jetson['L4T'])))
    del jetson['Model']

    del jetson['L4T']
    # Print NVP model status
    nvp_number, nvp_name = NVPModelService.query('nvpmodel')
    nvp_string = "{number} - {name}".format(number=nvp_number, name=bcolors.ok(nvp_name))
    print("{service}: {status}".format(service=bcolors.bold("NV Power Mode"), status=nvp_string))
    # Print status jetson-stats service
    jtop_status = bcolors.ok("Active") if status_service() else bcolors.fail("Inactive")
    print("{service}: {status}".format(service=bcolors.bold("jtop service"), status=jtop_status))
    # Print jetson hardware variables
    if args.verbose:
        print(bcolors.ok(bcolors.bold("Hardware:")))
        for name, variable in jetson.items():
            if not variable:
                variable = bcolors.fail("Not available")
            print(" - {name}: {variable}".format(name=bcolors.bold(name), variable=variable))
    # Read CUDA status
    print(bcolors.ok(bcolors.bold("Libraries:")))
    cuda_version = get_cuda()
    if cuda_version:
        print(" - {cuda}: {version}".format(cuda=bcolors.bold('CUDA'), version=cuda_version))
    else:
        print(bcolors.fail(" - CUDA not installed!"))
    # Read OpenCV status
    opencv_version, opencv_cuda = get_opencv()
    if opencv_version:
        opencv_cuda_string = bcolors.ok("YES") if opencv_cuda else bcolors.fail("NO")
        opencv_string = "{name}: {value}".format(name=bcolors.bold('OpenCV'), value=opencv_version)
        print(" - {opencv_string} - with CUDA: {opencv_cuda}".format(opencv_string=opencv_string, opencv_cuda=opencv_cuda_string))
    else:
        print(bcolors.fail(" - OpenCV not installed!"))
    # Read all libraries
    os_variables = get_libraries()
    for name, value in os_variables.items():
        if not value:
            value = bcolors.fail("Not installed")
        print(" - {name}: {value}".format(name=bcolors.bold(name), value=value))


if __name__ == "__main__":
    main()
# EOF
