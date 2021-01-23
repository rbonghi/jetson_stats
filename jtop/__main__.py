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

import re
import signal
import os
import sys
import argparse
# control command line
import curses
# Logging
import logging
# jtop service
from .service import JtopServer
# jtop client
from .jtop import jtop
# jtop exception
from .core import JtopException, get_var
# GUI jtop interface
from .gui import JTOPGUI, ALL, GPU, CPU, MEM, CTRL, INFO
# Load colors
from .github import jetpack_missing, board_missing
# Create logger
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
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
    def ok(message="OK"):
        return bcolors.OKGREEN + message + bcolors.ENDC

    @staticmethod
    def warning(message="WARN"):
        return bcolors.WARNING + message + bcolors.ENDC

    @staticmethod
    def fail(message="ERR"):
        return bcolors.FAIL + message + bcolors.ENDC


def warning_messages(jetson, no_warnings=False):
    if no_warnings:
        return
    # Read status version
    version = get_var(VERSION_RE)
    # Check is well stored the default jetson_clocks configuration
    if jetson.jetson_clocks:
        if not jetson.jetson_clocks.is_config:
            print("[{status}] Please stop manually jetson_clocks or reboot this board".format(status=bcolors.warning()))
    # Check if is running on sudo
    if os.getuid() == 0:
        print("[{status}] SUDO is no more required".format(status=bcolors.warning()))
    # Check if jetpack is missing
    if jetson.board.hardware['TYPE'] == "UNKNOWN" and jetson.board.hardware['BOARD'] and 'JETSON_DEBUG' not in os.environ:
        print("[{status}] {link}".format(status=bcolors.warning(), link=board_missing(REPOSITORY, jetson, version)))
    # Check if jetpack is missing
    if jetson.board.info['jetpack'] == "UNKNOWN" and jetson.board.info['L4T'] != "N.N.N":
        print("[{status}] jetson-stats not supported for [L4T {l4t}]".format(status=bcolors.warning(), l4t=jetson.board.info['L4T']))
        print("  Please, try: {bold}sudo -H pip install -U jetson-stats{reset}".format(bold=bcolors.BOLD, reset=bcolors.ENDC))
        print("  or {link}".format(link=jetpack_missing(REPOSITORY, jetson, version)))


def exit_signal(signum, frame):
    logger.info("Close service by signal {signum}".format(signum=signum))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='jtop is system monitoring utility and runs on terminal',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('service', nargs='?', help=argparse.SUPPRESS, default=False)
    parser.add_argument('--force', dest='force', help=argparse.SUPPRESS, action="store_true", default=False)
    parser.add_argument('--no-warnings', dest="no_warnings", help='Do not show warnings', action="store_true", default=False)
    parser.add_argument('--restore', dest="restore", help='Reset Jetson configuration', action="store_true", default=False)
    parser.add_argument('--loop', dest="loop", help='Automatically switch page every {sec}s'.format(sec=LOOP_SECONDS), action="store_true", default=False)
    parser.add_argument('-r', '--refresh', dest="refresh", help='refresh interval', type=int, default='500')
    parser.add_argument('-p', '--page', dest="page", help='Open fix page', type=int, default=1)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=get_var(VERSION_RE)))
    # Parse arguments
    args = parser.parse_args()
    # Initialize signals
    # signal.signal(signal.SIGINT, exit_signal)  # Do not needed equivalent to exception KeyboardInterrupt
    signal.signal(signal.SIGTERM, exit_signal)
    # Run jtop service
    if args.service == 'service':
        # Initialize logging level
        logging.basicConfig(level=logging.INFO, filemode='w', format='[%(levelname)s] %(name)s - %(message)s')
        # Run service
        try:
            # Initialize stats server
            server = JtopServer(force=args.force)
            logger.info("jetson_stats server loaded")
            server.loop_for_ever()
        except JtopException as e:
            print(e)
        # Close service
        exit(0)
    # Initialize logging level
    logging.basicConfig()
    # Convert refresh to second
    interval = float(args.refresh / 1000.0)
    # Restore option
    if args.restore:
        with jtop(interval=interval) as jetson:
            # Write warnings
            warning_messages(jetson, args.no_warnings)
            # Restore configuration
            if jetson.ok():
                for status, name in jetson.restore():
                    status = bcolors.ok() if status else bcolors.fail()
                    print(" [{status}] {name}".format(name=name.capitalize(), status=status))
        # Close service
        exit(0)
    # jtop client start
    try:
        # Open jtop client
        with jtop(interval=interval) as jetson:
            # Call the curses wrapper
            curses.wrapper(JTOPGUI, jetson, [ALL, GPU, CPU, MEM, CTRL, INFO], init_page=args.page, loop=args.loop, seconds=LOOP_SECONDS)
            # Write warnings
            warning_messages(jetson, args.no_warnings)
    except (KeyboardInterrupt, SystemExit):
        pass
    except JtopException as e:
        print(e)


if __name__ == "__main__":
    main()
# EOF
