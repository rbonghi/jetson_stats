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

import re
import os
import sys
import argparse
from .terminal_colors import bcolors
from .core.memory import MemoryService, read_swapon
from .core.common import get_var
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
COPYRIGHT_RE = re.compile(r""".*__copyright__ = ["'](.*?)['"]""", re.S)


def main():
    parser = argparse.ArgumentParser(
        description='Create a swap file and enable on boot (require sudo)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-d', '--dir', dest="directory", help='Directory to place swapfile', type=str, default='')
    parser.add_argument('-n', '--name', dest="name", help='Name swap file', type=str, default='swapfile')
    parser.add_argument('-s', '--size', dest="size", help='Size in Gigabytes', type=int, default='8')
    parser.add_argument('-a', '--auto', dest="auto", help='Enable swap on boot', action="store_true", default=False)
    parser.add_argument('-t', '--status', dest="status", help='Check if the swap is currently active', action="store_true", default=False)
    parser.add_argument('--off', dest="off", help='Switch off the swap', action="store_true", default=False)
    # Parse arguments
    args = parser.parse_args()
    # Copyrights
    print("Software part of jetson-stats {version} - {copyright}".format(version=get_var(VERSION_RE), copyright=get_var(COPYRIGHT_RE)))
    # Status swap
    if args.status:
        # Print all swap
        swap_table = read_swapon()
        print("NAME\t\tTYPE\t\tPRIO\t\tSIZE\t\tUSED")
        for name, swap in swap_table.items():
            print("{name}\t{type}\t\t{prio}\t\t{size}{unit}\t{used}{unit}".format(
                name=name,
                type=swap['type'],
                prio=swap['prio'],
                size=swap['size'],
                used=swap['used'],
                unit='k'))
        sys.exit(0)
    # Check if running a root
    if os.getuid() != 0:
        # Quit with error
        print(bcolors.fail("Please run with sudo"))
        parser.print_help(sys.stderr)
        sys.exit(1)
    # Define Memory Service
    memory_service = MemoryService
    # Path swap
    size = args.size
    auto = args.auto
    path_swap = "{directory}/{name}".format(directory=args.directory, name=args.name)
    if args.off:
        print("Switch off swap {path_swap}".format(path_swap=path_swap))
        memory_service.swap_deactivate(path_swap)
        sys.exit(0)
    # Create Swap
    print("Create swap {path_swap} [{size}GB] - on boot={auto}".format(path_swap=path_swap, size=size, auto=auto))
    # Create swap
    memory_service.swap_set(size, path_swap, auto)


if __name__ == "__main__":
    main()
# EOF
