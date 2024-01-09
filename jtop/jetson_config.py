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
from pwd import getpwnam
import subprocess as sp
# Logging
import logging

from .gui import JTOPCONFIG
from .terminal_colors import bcolors
from .core.common import get_var
from .core.command import Command
from .core.jetson_variables import status_variables, install_variables
from .core.config import get_config_service
from .service import status_service, status_permission, install_service, set_service_permission
# Create logger
logger = logging.getLogger(__name__)
# Detect user
user = os.environ.get('USER', '')
# Get user from sudo
sudo_user = os.environ.get('SUDO_USER', '')
# If are both empty assign 'root'
user = sudo_user or 'root'
# Locate folder and type of installation
folder, _ = os.path.split(__file__)
folder = os.path.dirname(folder)
developer = os.path.isdir("{folder}/tests".format(folder=folder))
config = get_config_service()
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
GUI_GRAPHIC_RE = re.compile(r'^AutomaticLoginEnable[ ]*=[ ]*[tT]rue')
REQUIRE_REBOOT = False

# -------------------- JTOP ------------------------------------------------


def update_jtop():
    cmd_update = Command(shlex.split('pip3 install --no-cache-dir -U jetson_stats'))
    cmd_update_msg = ""
    try:
        cmd_update_msg = cmd_update()
        cmd_update_msg = "JTOP updated!"
    except (OSError, Command.CommandException):
        cmd_update_msg = "Error to update jtop, please run:\n\nsudo pip3 install --no-cache-dir -U jetson_stats"
    return cmd_update_msg


def fix_service():
    copy = not developer
    # Install service (linking only for develop)
    install_service(folder, copy=copy)


def fix_variables():
    copy = not developer
    # Install variables
    install_variables(folder, copy=copy)


def fix_jtop_all():
    fix_service()
    set_service_permission()
    fix_variables()

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
            # Check GUI auto login
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


def desktop_set_B1():
    global REQUIRE_REBOOT
    sp.call(shlex.split('systemctl set-default multi-user.target'))
    # sudo ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    if os.path.isfile('/etc/systemd/system/getty.target.wants/getty@tty1.service'):
        os.remove('/etc/systemd/system/getty.target.wants/getty@tty1.service')
    os.symlink('/lib/systemd/system/getty@.service', '/etc/systemd/system/getty.target.wants/getty@tty1.service')
    # Remove autologin
    if os.path.isfile('/etc/systemd/system/getty@tty1.service.d/autologin.conf'):
        os.remove('/etc/systemd/system/getty@tty1.service.d/autologin.conf')
    REQUIRE_REBOOT = True


def desktop_set_B2():
    global REQUIRE_REBOOT
    sp.call(shlex.split('systemctl set-default multi-user.target'))
    # sudo ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    if os.path.isfile('/etc/systemd/system/getty.target.wants/getty@tty1.service'):
        os.remove('/etc/systemd/system/getty.target.wants/getty@tty1.service')
    os.symlink('/lib/systemd/system/getty@.service', '/etc/systemd/system/getty.target.wants/getty@tty1.service')
    # If the file does not exist make it one
    if not os.path.isfile('/etc/systemd/system/getty@tty1.service.d/autologin.conf'):
        os.makedirs('/etc/systemd/system/getty@tty1.service.d')
    # Write file
    with open('/etc/systemd/system/getty@tty1.service.d/autologin.conf', 'w') as writer:
        writer.write("[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin {user} --noclear %I $TERM\n".format(user=user))
    # Change hownership
    pwnam = getpwnam(user)
    os.chown('/etc/systemd/system/getty@tty1.service.d/autologin.conf', pwnam.pw_uid, pwnam.pw_gid)
    REQUIRE_REBOOT = True


def desktop_set_B3():
    global REQUIRE_REBOOT
    sp.call(shlex.split('systemctl set-default graphical.target'))
    # sudo ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    if os.path.isfile('/etc/systemd/system/getty.target.wants/getty@tty1.service'):
        os.remove('/etc/systemd/system/getty.target.wants/getty@tty1.service')
    os.symlink('/lib/systemd/system/getty@.service', '/etc/systemd/system/getty.target.wants/getty@tty1.service')
    # Remove autologin
    if os.path.isfile('/etc/systemd/system/getty@tty1.service.d/autologin.conf'):
        os.remove('/etc/systemd/system/getty@tty1.service.d/autologin.conf')
    # Update desktop login
    sp.call(shlex.split("update_desktop_login \"False\" {user}".format(user=user)))
    REQUIRE_REBOOT = True


def desktop_set_B4():
    global REQUIRE_REBOOT
    sp.call(shlex.split('systemctl set-default graphical.target'))
    # sudo ln -fs /lib/systemd/system/getty@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    if os.path.isfile('/etc/systemd/system/getty.target.wants/getty@tty1.service'):
        os.remove('/etc/systemd/system/getty.target.wants/getty@tty1.service')
    os.symlink('/lib/systemd/system/getty@.service', '/etc/systemd/system/getty.target.wants/getty@tty1.service')
    # Remove autologin
    if os.path.isfile('/etc/systemd/system/getty@tty1.service.d/autologin.conf'):
        os.remove('/etc/systemd/system/getty@tty1.service.d/autologin.conf')
    # Update desktop login
    sp.call(shlex.split("update_desktop_login \"True\" {user}".format(user=user)))
    REQUIRE_REBOOT = True


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
        (desktop_is_type_one, desktop_set_B1, "Text console, requiring user to login"),
        (desktop_is_type_two, desktop_set_B2, "Text console, automatically logged in as '{user}' user".format(user=user)),
        (desktop_is_type_tree, desktop_set_B3, "Desktop GUI, requiring user to login"),
        (desktop_is_type_four, desktop_set_B4, "Desktop GUI, automatically logged in as '{user}' user".format(user=user)),
    ]
}
INFORMATION_MENU = {
    'title': 'jtop {version} - main page'.format(version=get_var(VERSION_RE)),
    'description': "This tool provide a set of tool to configure your NVIDIA Jetson\
\n\nScripts: jtop, jetson_config, jetson_release, jetson_swap\nServices: jtop.service",
}
MAIN_PAGE = {
    'title': 'jetson-stats {version} - main page'.format(version=get_var(VERSION_RE)),
    'menu': [
        ("Health", JTOP_MENU, "Check the status of jetson-stats"),
        ("Update", update_jtop, "Update jetson-stats to the latest version"),
        ("Desktop", DISPLAY_MENU, "Enable/Disable boot from desktop"),
        ("About", INFORMATION_MENU, "Information about this configuration tool"),
    ]}


def jtop_config():
    # Check if running a root
    if os.getuid() == 0:
        # Run wrapper
        curses.wrapper(JTOPCONFIG, JTOP_MENU)
        sys.exit(0)
    # Quit with error
    print(bcolors.fail("Please run with sudo"))
    sys.exit(1)


def main():
    # Check if running a root
    if os.getuid() == 0:
        # Run wrapper
        curses.wrapper(JTOPCONFIG, MAIN_PAGE)
        if REQUIRE_REBOOT:
            print(bcolors.fail("require reboot"))
        sys.exit(0)
    # Quit with error
    print(bcolors.fail("Please run with sudo"))
    sys.exit(1)


if __name__ == "__main__":
    main()
# EOF
