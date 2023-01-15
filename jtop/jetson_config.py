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
import shlex
import curses
import sys
# Logging
import logging

from .gui import JTOPCONFIG
from .core import get_var, Command
from .core.jetson_variables import status_variables, install_variables
from .core.config import get_config_service
from .service import status_service, status_permission, install_service, set_service_permission
# Create logger
logger = logging.getLogger(__name__)
# Detect user
user = os.environ.get('USER', '')
# Get user from sudo
if 'SUDO_USER' in os.environ:
    user = os.environ['SUDO_USER']
# Locate folder and type of installation
folder, _ = os.path.split(__file__)
folder = os.path.dirname(folder)
developer = os.path.isdir("{folder}/tests".format(folder=folder))
config = get_config_service()
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
GUI_GRAPHIC_RE = re.compile(r'^AutomaticLoginEnable[ ]*=[ ]*[tT]rue')

# -------------------- JTOP ------------------------------------------------


def fix_service(data):
    copy = not developer
    # Install service (linking only for develop)
    install_service(folder, copy=copy)


def fix_variables(data):
    copy = not developer
    # Install variables
    install_variables(folder, copy=copy)


def fix_jtop_all(data):
    fix_service(data)
    set_service_permission()
    fix_variables(data)

# -------------------- Graphic ---------------------------------------------


def get_type_desktop():
    cmd_status_gui = Command(shlex.split('systemctl get-default'))
    status = 0
    try:
        status_gui = cmd_status_gui()[0]
        if status_gui == 'multi-user.target':
            status = 1
            if os.path.isfile('/etc/systemd/system/getty@tty1.service.d/autologin.conf'):
                status = 2
        elif status_gui == 'graphical.target':
            status = 3
            # Check GUI autologin
            if os.path.isfile('/etc/gdm3/custom.conf'):
                with open('/etc/gdm3/custom.conf', 'r') as f:
                    for line in f.readlines():
                        if GUI_GRAPHIC_RE.match(line):
                            status = 4
                            break
    except (OSError, Command.CommandException):
        pass
    return status


def desktop_is_type_one(data):
    return "[B1]" if data == 1 else " B1 "


def desktop_is_type_two(data):
    return "[B2]" if data == 2 else " B2 "


def desktop_is_type_tree(data):
    return "[B3]" if data == 3 else " B3 "


def desktop_is_type_four(data):
    return "[B4]" if data == 4 else " B4 "


# ---------------------- Pages ---------------------------------------------
JTOP_MENU = {
    'title': 'status jtop',
    'description': 'config folder: {config}\njtop path:{jtop_path}'.format(config=config, jtop_path=folder),
    'menu': [
        (None, fix_jtop_all, "Fix all"),
        (status_service, fix_service, "Fix jetson-stats service"),
        (status_permission, set_service_permission, "Fix permissions for '{user}'".format(user=user)),
        (status_variables, fix_variables, "Fix jtop variables"),
    ],
}
DISPLAY_MENU = {
    'title': 'GUI menu option',
    'run_before': get_type_desktop,
    'menu': [
        (desktop_is_type_one, None, "Text console, requiring user to login"),
        (desktop_is_type_two, None, "Text console, automatically logged in as '{user}' user".format(user=user)),
        (desktop_is_type_tree, None, "Desktop GUI, requiring user to login"),
        (desktop_is_type_four, None, "Desktop GUI, automatically logged in as '{user}' user".format(user=user)),
    ]
}
MAIN_PAGE = {
    'title': 'jtop {version} - main page'.format(version=get_var(VERSION_RE)),
    'menu': [
        (None, JTOP_MENU, "Check the status of jetson-stats"),
        (None, None, "Update jetson-stats to the latest version"),
        (None, DISPLAY_MENU, "Enable/Disable boot from desktop"),
        (None, None, "Information about this configuration tool"),
    ]}


def jtop_config():
    # Check if running a root
    if os.getuid() == 0:
        # Run wrapper
        curses.wrapper(JTOPCONFIG, JTOP_MENU)
        sys.exit(0)
    # Quit with error
    print("Please run with sudo")
    sys.exit(1)


def main():
    # Check if running a root
    if os.getuid() == 0:
        # Run wrapper
        curses.wrapper(JTOPCONFIG, MAIN_PAGE)
        sys.exit(0)
    # Quit with error
    print("Please run with sudo")
    sys.exit(1)


if __name__ == "__main__":
    main()
# EOF
