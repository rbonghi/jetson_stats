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
from .core.jetson_variables import get_variables
from .core.jetson_libraries import get_cuda


def main():
    parser = argparse.ArgumentParser(
        description='Show detailed information about this board. Machine, Jetpack, libraries and other',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # Parse arguments
    args = parser.parse_args()
    print(args)
    # Read all Jetson Variables
    jetson = get_variables()
    for name, variable in jetson.items():
        print(" - {name}: {variable}".format(name=name.capitalize(), variable=variable))
    # Read all libraries
    print("Libraries")
    cuda_version = get_cuda()
    if cuda_version:
        print(" - CUDA: {version}".format(version=cuda_version))
    else:
        print(" - CUDA not installed!")


if __name__ == "__main__":
    main()
# EOF
