#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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
import os
import argparse
# Logging
import logging
# control command line
import curses
# Load colors
from .github import jetpack_missing, board_missing
# Tegrastats objext reader
from .jtop import jtop, get_version
# GUI jtop interface
from .gui import JTOPGUI, ALL, CPU, GPU, MEM, CTRL, INFO
# Create logger for jplotlib
logger = logging.getLogger(__name__)
# Reference repository
REPOSITORY = "https://github.com/rbonghi/jetson_stats/issues"
LOOP_SECONDS = 5


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def ok():
        return bcolors.OKGREEN + "OK" + bcolors.ENDC

    @staticmethod
    def warning():
        return bcolors.WARNING + "WARN" + bcolors.ENDC

    @staticmethod
    def fail():
        return bcolors.FAIL + "ERR" + bcolors.ENDC


def main():
    # Add arg parser
    parser = argparse.ArgumentParser(description='jtop is system monitoring utility and runs on terminal')
    parser.add_argument('--debug', dest="debug", help='Run with debug logger', action="store_true", default=False)
    parser.add_argument('--no-warnings', dest="no_warnings", help='Do not show warnings', action="store_true", default=False)
    parser.add_argument('--restore', dest="restore", help='Reset Jetson configuration', action="store_true", default=False)
    parser.add_argument('--loop', dest="loop", help='Automatically switch page every {sec}s'.format(sec=LOOP_SECONDS), action="store_true", default=False)
    parser.add_argument('-r', '--refresh', dest="refresh", help='refresh interval', type=int, default='500')
    parser.add_argument('-p', '--page', dest="page", help='Open fix page', type=int, default=1)
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
                    curses.wrapper(JTOPGUI, args.refresh, jetson, [ALL, GPU, CPU, MEM, CTRL, INFO], init_page=args.page, loop=args.loop, seconds=LOOP_SECONDS)
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
                    if jetson.jetson_clocks:
                        jetson.jetson_clocks.start = False
                        print("[{status}] Stop jetson_clocks service".format(status=bcolors.ok()))
                        jetson.jetson_clocks.enable = False
                        print("[{status}] Disable jetson_clocks service".format(status=bcolors.ok()))
                    # * Set fan speed to 0
                    if jetson.fan:
                        jetson.fan.speed = 0
                        print("[{status}] Fan speed = 0".format(status=bcolors.ok()))
                        jetson.fan.control = True
                        print("[{status}] Fan temp_control = 1".format(status=bcolors.ok()))
                    # * Delete fan_configuration
                        clear = jetson.fan.clear()
                        status = bcolors.ok() if clear else bcolors.fail()
                        print("[{status}] Clear Fan Configuration".format(status=status))
                    # * Delete jetson_clocks configuration
                    if jetson.jetson_clocks:
                        clear = jetson.jetson_clocks.clear()
                        status = bcolors.ok() if clear else bcolors.fail()
                        print("[{status}] Clear Jetson Clock Configuration".format(status=status))
                else:
                    print("[{status}] Please run with sudo".format(status=bcolors.fail()))
        if not args.no_warnings:
            # Check if jetpack is missing
            if not os.environ["JETSON_TYPE"] and os.environ["JETSON_BOARD"] and "DEBUG" not in os.environ["JETSON_MACHINE"]:
                print("[{status}] {link}".format(status=bcolors.warning(), link=board_missing(REPOSITORY, get_version())))
            # Check if jetpack is missing
            if os.environ["JETSON_JETPACK"] == "UNKNOWN" and os.environ["JETSON_L4T"] != "N.N.N":
                print("[{status}] {link}".format(status=bcolors.warning(), link=jetpack_missing(REPOSITORY, get_version())))
    except jtop.JtopException as e:
        # Print error and close
        print("[{status}] {error}".format(status=bcolors.fail(), error=e.message))
        print("Run jetson_config (health page) to fix it")
        print("or open an issue on {url}".format(url=REPOSITORY))


if __name__ == "__main__":
    main()
# EOF
