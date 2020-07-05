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

import argparse
# control command line
import curses
# Logging
import logging
# jtop service
from .service import JtopServer
# jtop client
from .jtop import jtop, get_version
# jtop exception
from .core import JtopException
# GUI jtop interface
from .gui import JTOPGUI, ALL, GPU, CPU, MEM, CTRL, INFO
# Create logger
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
    def ok(message="OK"):
        return bcolors.OKGREEN + message + bcolors.ENDC

    @staticmethod
    def warning(message="WARN"):
        return bcolors.WARNING + message + bcolors.ENDC

    @staticmethod
    def fail(message="ERR"):
        return bcolors.FAIL + message + bcolors.ENDC


def main():
    parser = argparse.ArgumentParser(
        description='jtop is system monitoring utility and runs on terminal',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('service', nargs='?', help=argparse.SUPPRESS, default=False)
    parser.add_argument('--restore', dest="restore", help='Reset Jetson configuration', action="store_true", default=False)
    parser.add_argument('--loop', dest="loop", help='Automatically switch page every {sec}s'.format(sec=LOOP_SECONDS), action="store_true", default=False)
    parser.add_argument('-r', '--refresh', dest="refresh", help='refresh interval', type=int, default='500')
    parser.add_argument('-p', '--page', dest="page", help='Open fix page', type=int, default=1)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=get_version()))
    # Parse arguments
    args = parser.parse_args()
    # Run jtop service
    if args.service == 'service':
        # Initialize logging level
        logging.basicConfig(level=logging.DEBUG, filemode='w', format='%(name)s - %(levelname)s - %(message)s')
        # Run service
        try:
            # Initialize stats server
            server = JtopServer()
            logger.info("Service started")
            server.loop_for_ever()
            # Close stats server
            logger.info("Close service")
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
            if jetson.ok():
                print('Restore')
        # Close service
        exit(0)
    # jtop client start
    try:
        # Open jtop client
        with jtop(interval=interval) as jetson:
            # Call the curses wrapper
            curses.wrapper(JTOPGUI, jetson, [ALL, GPU, CPU, MEM, CTRL, INFO], init_page=args.page, loop=args.loop, seconds=LOOP_SECONDS)
    except (KeyboardInterrupt, SystemExit):
        pass
    except JtopException as e:
        print(e)


if __name__ == "__main__":
    main()
# EOF
