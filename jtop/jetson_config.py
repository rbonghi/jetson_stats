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
import curses
# Logging
import logging

from .gui import JTOPCONFIG
from .service import status_service
# Create logger
logger = logging.getLogger(__name__)
# Detect user
user = os.environ.get('USER', '')
# Get user from sudo
if 'SUDO_USER' in os.environ:
    user = os.environ['SUDO_USER']

# ---------------------- Pages ---------------------------------------------
JTOP_MENU = {
    'title': 'status jtop',
    'menu': [
        (None, None, "Fix all"),
        (status_service, None, "Fix jetson-stats service"),
        (None, None, "Fix permissions for '{user}'".format(user=user)),
        (None, None, "Fix jtop variables"),
    ],
}
DISPLAY_MENU = {
    'title': 'GUI menu option',
    'menu': [
        (None, None, "Text console, requiring user to login"),
        (None, None, "Text console, automatically logged in as '{user}' user".format(user=user)),
        (None, None, "Desktop GUI, requiring user to login"),
        (None, None, "Desktop GUI, automatically logged in as '{user}' user".format(user=user)),
    ]
}
MAIN_PAGE = {
    'title': 'jtop {version} - main page'.format(version='AAA'),
    'menu': [
        (None, JTOP_MENU, "Check the status of jetson-stats"),
        (None, DISPLAY_MENU, "Enable/Disable boot from desktop"),
        (None, None, "Update this tool to the latest version"),
        (None, None, "Information about this configuration tool"),
    ]}


def jtop_config():
    # Run wrapper from JTOP menu
    curses.wrapper(JTOPCONFIG, JTOP_MENU)


def main():
    # Run wrapper
    curses.wrapper(JTOPCONFIG, MAIN_PAGE)


if __name__ == "__main__":
    main()
# EOF
