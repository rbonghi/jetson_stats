#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
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

"""
    Graphic reference:
    - http://urwid.org/examples/index.html
    - https://npyscreen.readthedocs.io/
    - https://github.com/chubin/cheat.sh
    - https://stackoverflow.com/questions/6840420/python-rewrite-multiple-lines-in-the-console
    - https://docs.python.org/3.3/howto/curses.html#attributes-and-color
    - http://toilers.mines.edu/~jrosenth/101python/code/curses_plot/
"""
import argparse
# Logging
import logging
# control command line
import curses
# Tegrastats objext reader
from .jtop import jtop, get_version
# GUI jtop interface
from .gui import JTOPGUI, ALL, GPU, MEM, CTRL, INFO
# Create logger for jplotlib
logger = logging.getLogger(__name__)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def main():
    # Add arg parser
    parser = argparse.ArgumentParser(description='jtop is system monitoring utility and runs on terminal')
    parser.add_argument('-r', dest="refresh", help='refresh interval', type=int, default='500')
    parser.add_argument('--debug', dest="debug", help='Run with debug logger', action="store_true", default=False)
    parser.add_argument('--page', dest="page", help='Open fix page', type=int, default=1)
    parser.add_argument('--restore', dest="restore", help='Reset Jetson configuration', action="store_true", default=False)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=get_version()))
    # Parse arguments
    args = parser.parse_args()
    # Set logging level
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, filename='jtop.log', filemode='w',
                            format='%(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig()
    # Open tegrastats reader and run the curses wrapper
    try:
        with jtop(interval=args.refresh) as jetson:
            if not args.restore:
                try:
                    # Call the curses wrapper
                    curses.wrapper(JTOPGUI, args.refresh, jetson, [ALL, GPU, MEM, CTRL, INFO], init_page=args.page)
                except KeyboardInterrupt as x:
                    # Catch keyboard interrupt and close
                    logger.info("Closed with CTRL-C [{status}]".format(status=x))
                except SystemExit as x:
                    # Catch keyboard interrupt and close
                    logger.info("System exit {status}".format(status=x))
            else:
                if jetson.userid == 0:
                    # If enable restore:
                    # * Disable jetson_clocks
                    status = bcolors.OKGREEN + "OK" + bcolors.ENDC
                    if jetson.jetson_clocks:
                        jetson.jetson_clocks.start = False
                        print("[{status}] Stop jetson_clocks service".format(status=status))
                        jetson.jetson_clocks.enable = False
                        print("[{status}] Disable jetson_clocks service".format(status=status))
                    # * Set fan speed to 0
                    if jetson.fan:
                        jetson.fan.speed = 0
                        print("[{status}] Fan speed = 0".format(status=status))
                        jetson.fan.control = True
                        print("[{status}] Fan temp_control = 1".format(status=status))
                    # * Delete fan_configuration
                        if jetson.fan.clear():
                            print("[{status}] Clear Fan Configuration".format(status=status))
                    # * Delete jetson_clocks configuration
                    if jetson.jetson_clocks:
                        if jetson.jetson_clocks.clear():
                            print("[{status}] Clear Jetson Clock Configuration".format(status=status))
                else:
                    print("Please run with sudo")
    except jtop.JtopException as e:
        # Print error and close
        print(e)


if __name__ == "__main__":
    main()
# EOF
