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
import curses
from copy import deepcopy
# Find variable
from ..core.common import get_var
# Page class definition
from .jtopgui import Page
# Graphics elements
from .lib.colors import NColors
from .lib.smallbutton import HideButton
from .lib.common import plot_name_info, plot_dictionary
# Regex
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)
COPYRIGHT_RE = re.compile(r""".*__copyright__ = ["'](.*?)['"]""", re.S)
EMAIL_RE = re.compile(r""".*__email__ = ["'](.*?)['"]""", re.S)


def plot_libraries(stdscr, pos_y, pos_x, libraries):
    libraries = deepcopy(libraries)
    opencv = libraries['OpenCV']
    opencv_cuda = libraries['OpenCV-Cuda']
    opencv_cuda_string = "YES" if opencv_cuda else "NO"
    color = NColors.green() if opencv_cuda else NColors.red()
    del libraries['OpenCV']
    del libraries['OpenCV-Cuda']
    # Plot Library
    libraries_size_y, libraries_size_x = plot_dictionary(stdscr, pos_y, pos_x, 'Libraries', libraries)
    # Plot OpenCV and CUDA
    opencv_string = opencv if opencv else "MISSING"
    opencv_color = curses.A_NORMAL if opencv else NColors.red()
    opencv_size_x = plot_name_info(stdscr, pos_y + libraries_size_y, pos_x + 1, 'OpenCV', opencv_string, color=opencv_color)
    len_opencv = opencv_size_x
    if opencv:
        try:
            stdscr.addstr(pos_y + libraries_size_y, pos_x + opencv_size_x + 1, " with CUDA:")
            stdscr.addstr(pos_y + libraries_size_y, pos_x + opencv_size_x + 13, opencv_cuda_string, color | curses.A_BOLD)
        except curses.error:
            pass
        len_opencv += len(opencv_cuda_string) + 15
    return libraries_size_y + 1, max(libraries_size_x, len_opencv)


def plot_hardware(stdscr, pos_y, pos_x, hardware, size_hardware_x):
    hardware = deepcopy(hardware)
    # Remove from list and add a button
    if 'Serial Number' in hardware:
        del hardware['Serial Number']
    # Plot all hardware data
    hardware_size_y, hardware_size_x = plot_dictionary(stdscr, pos_y, pos_x, 'Hardware', hardware, size=size_hardware_x)
    return hardware_size_y, hardware_size_x


class INFO(Page):

    def __init__(self, stdscr, jetson):
        super(INFO, self).__init__("INFO", stdscr, jetson)
        # Store serial number
        self._hide_serial_number = None
        hardware = self.jetson.board['hardware']
        if 'Serial Number' in hardware:
            if self.jetson.board['hardware']['Serial Number']:
                serial_number = hardware['Serial Number']
                self._hide_serial_number = HideButton(stdscr, 's', serial_number)

    def draw(self, key, mouse):
        """
            Write all environment variables
        """
        # Screen size
        _, width, first = self.size_page()
        start_pos = first + 3
        # Clear first line
        self.stdscr.move(0, 0)
        self.stdscr.clrtoeol()
        # Author info
        string_author = "jtop {version} - {copyright} [{email}]".format(version=get_var(VERSION_RE),
                                                                        copyright=get_var(COPYRIGHT_RE),
                                                                        email=get_var(EMAIL_RE))
        self.stdscr.addstr(first, 0, string_author, curses.A_BOLD)
        self.stdscr.addstr(first + 1, 0, "Website: https://rnext.it/jetson_stats", curses.A_BOLD)
        # Plot platform
        platform_size_y, platform_size_x = plot_dictionary(self.stdscr, start_pos, 1, 'Platform', self.jetson.board['platform'])
        # Plot libraries
        libraries_size_y, libraries_size_x = plot_libraries(self.stdscr, start_pos + platform_size_y + 1, 1, self.jetson.board['libraries'])
        # Plot hardware
        size_hardware_x = width - platform_size_x - 2
        # Plot serial number
        offset_y_sn = 0
        if 'Serial Number' in self.jetson.board['hardware']:
            if self.jetson.board['hardware']['Serial Number']:
                try:
                    self.stdscr.addstr(start_pos, 1 + platform_size_x + 1, "Serial Number:", curses.A_BOLD)
                except curses.error:
                    pass
                self._hide_serial_number.update(start_pos, 1 + platform_size_x + 16, key=key, mouse=mouse)
                offset_y_sn = 1
        hardware_size_y, hardware_size_x = plot_hardware(self.stdscr,
                                                         start_pos + offset_y_sn,
                                                         1 + platform_size_x + 1,
                                                         self.jetson.board['hardware'], size_hardware_x)
        hardware_size_y += offset_y_sn
        # Plot interfaces
        interfaces = self.jetson.local_interfaces["interfaces"]
        hostname = self.jetson.local_interfaces["hostname"]
        max_size_x = max(platform_size_x, libraries_size_x)
        plot_name_info(self.stdscr, start_pos + hardware_size_y + 1, 2 + max_size_x, "Hostname", hostname)
        interfaces_size_y, interfaces_size_x = plot_dictionary(self.stdscr, start_pos + hardware_size_y + 2, 2 + max_size_x, 'Interfaces', interfaces)
# EOF
