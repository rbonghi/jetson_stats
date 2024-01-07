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
import signal
import os
import sys
# import locale
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
from .core.exceptions import JtopException
from .core.common import get_var
# GUI jtop interface
from .jetson_config import jtop_config
from .gui import JTOPGUI, ALL, GPU, CPU, ENGINE, MEM, CTRL, INFO, engine_model
# Load colors
from .terminal_colors import bcolors
from .github import jetpack_missing, hardware_missing, engine_gui, get_hardware_log
# Create logger
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
# Reference repository
REPOSITORY = "https://github.com/rbonghi/jetson_stats/issues"
LOOP_SECONDS = 5
JTOP_LOG_NAME = 'jtop-error.log'


def warning_messages(jetson, no_warnings=False):
    if no_warnings:
        return
    # Read status version
    hardware = jetson.board['hardware']
    version = get_var(VERSION_RE)
    # Check is well stored the default jetson_clocks configuration
    if jetson.jetson_clocks:
        if not jetson.jetson_clocks.is_config:
            print("[{status}] Please stop manually jetson_clocks or reboot this board".format(status=bcolors.warning()))
    # Check if an hardware value is missing
    if not all([data for name, data in hardware.items() if name not in ['Jetpack']]):
        hardware_missing(REPOSITORY, hardware, version)
    # Check if jetpack is missing
    if not hardware['Jetpack'] and hardware['L4T']:
        jetpack_missing(REPOSITORY, hardware, version)
    # Check if model is in map list
    if not engine_model(hardware["Module"]) and hardware["Module"]:
        engine_gui(REPOSITORY, hardware, version)


def exit_signal(signum, frame):
    logger.info("Close service by signal {signum}".format(signum=signum))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='jtop is system monitoring utility and runs on terminal',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--force', dest='force', help=argparse.SUPPRESS, action="store_true", default=False)
    parser.add_argument('--health', dest="health", help='Status jtop and fix', action="store_true", default=False)
    parser.add_argument('--error-log', dest="log", help='Generate a log for GitHub', action="store_true", default=False)
    parser.add_argument('--no-warnings', dest="no_warnings", help='Do not show warnings', action="store_true", default=False)
    parser.add_argument('--restore', dest="restore", help='Reset Jetson configuration', action="store_true", default=False)
    parser.add_argument('--loop', dest="loop", help='Automatically switch page every {sec}s'.format(sec=LOOP_SECONDS), action="store_true", default=False)
    parser.add_argument('--color-filter', dest="color_filter",
                        help='Change jtop base colors, you can use also JTOP_COLOR_FILTER=True', action="store_true", default=False)
    parser.add_argument('-r', '--refresh', dest="refresh", help='refresh interval', type=int, default='1000')
    parser.add_argument('-p', '--page', dest="page", help='Open fix page', type=int, default=1)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=get_var(VERSION_RE)))
    # Parse arguments
    args = parser.parse_args()
    # Initialize signals
    # signal.signal(signal.SIGINT, exit_signal)  # Do not needed equivalent to exception KeyboardInterrupt
    signal.signal(signal.SIGTERM, exit_signal)
    # Run jtop service
    if os.getenv('JTOP_SERVICE', False):
        # Initialize logging level
        logging.basicConfig(level=logging.INFO, filemode='w', format='[%(levelname)s] %(name)s - %(message)s')
        # Run service
        try:
            # Initialize stats server
            server = JtopServer(force=args.force)
            server.loop_for_ever()
        except JtopException as e:
            print(e)
        # Close service
        sys.exit(0)
    # Initialize logging level
    logging.basicConfig()
    # Convert refresh to second
    interval = float(args.refresh / 1000.0)
    # Restore option
    if args.restore:
        try:
            with jtop(interval=interval) as jetson:
                # Write warnings
                if 'L4T' in jetson.board['hardware']:
                    warning_messages(jetson, args.no_warnings)
                # Restore configuration
                if jetson.ok():
                    for status, name in jetson.restore():
                        status = bcolors.ok() if status else bcolors.fail()
                        print(" [{status}] {name}".format(name=name, status=status))
        except JtopException as e:
            print(e)
        # Close service
        sys.exit(0)
    # Run health jtop
    if args.health:
        jtop_config()
    # Generate a log for GitHub
    if args.log:
        body = get_hardware_log()
        body += "\n\nLog from jtop {version}\n".format(version=get_var(VERSION_RE))
        with open('{cwd}/{name}'.format(cwd=os.getcwd(), name=JTOP_LOG_NAME), 'w') as writer:
            writer.write(body)
        print("LOG '{name}' generated in {path}".format(name=JTOP_LOG_NAME, path=os.getcwd()))
        sys.exit(0)
    # jtop client start
    try:
        # https://stackoverflow.com/questions/56373360/n-curses-within-python-how-to-catch-and-print-non-ascii-character
        # Commented for issues #466 #393
        # locale.setlocale(locale.LC_ALL, '')
        # Open jtop client
        with jtop(interval=interval) as jetson:
            # Call the curses wrapper
            color_filter = bool(os.getenv('JTOP_COLOR_FILTER', args.color_filter))
            # Build list pages available
            pages = [ALL]
            if jetson.gpu:
                pages += [GPU]
            pages += [CPU, MEM]
            if jetson.engine:
                pages += [ENGINE]
            if jetson.fan or jetson.jetson_clocks is not None or jetson.nvpmodel is not None:
                pages += [CTRL]
            pages += [INFO]
            curses.wrapper(JTOPGUI, jetson, pages, init_page=args.page,
                           loop=args.loop, seconds=LOOP_SECONDS, color_filter=color_filter)
            # Write warnings
            if 'L4T' in jetson.board['hardware']:
                warning_messages(jetson, args.no_warnings)
    except (KeyboardInterrupt, SystemExit):
        pass
    except JtopException as e:
        print(e)


if __name__ == "__main__":
    main()
# EOF
