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

import jtop

import argparse
import logging
# Create logger
logger = logging.getLogger(__name__)

def main():

    parser = argparse.ArgumentParser(description='jtop is system monitoring utility and runs on terminal')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {version}'.format(version=jtop.__version__))
    # Parse arguments
    args = parser.parse_args()


    # Initialize logging level
    logging.basicConfig(level=logging.DEBUG, filemode='w', format='%(name)s - %(levelname)s - %(message)s')
    # Run service
    try:
        # Initialize stats server
        server = jtop.JtopServer()
        logger.info("Service started")
        server.loop_for_ever()
        # Close stats server
        logger.info("Close service")
    except jtop.JtopException as e:
        print(e)


if __name__ == "__main__":
    main()
# EOF
