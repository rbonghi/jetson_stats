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

import curses
from datetime import timedelta
# Page class definition
from .jtopgui import Page
# Graphics elements
from .lib.common import plot_name_info
# Menu GUI pages
from .jtopguimenu import strfdelta


class INFO(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(INFO, self).__init__("INFO", stdscr, jetson, refresh)

    def info_variable(self, start, offset, name, value, spacing=18):
        self.stdscr.addstr(start, offset, name + ":")
        self.stdscr.addstr(start, offset + spacing, value, curses.A_BOLD)

    def draw(self, key, mouse):
        """
            Write all environment variables
        """
        # Screen size
        _, width, first = self.size_page()
        # Position information
        posx = 1
        start_pos = first + 2
        spacing = 18
        # Up time
        uptime_string = strfdelta(timedelta(seconds=self.jetson.uptime), "{days} days {hours}:{minutes}:{seconds}")
        self.stdscr.addstr(start_pos, posx, "- Up Time:", curses.A_BOLD)
        self.stdscr.addstr(start_pos, posx + spacing, uptime_string)
        start_pos += 1
        # Loop build information
        idx = 0
        # Board info
        self.stdscr.addstr(start_pos + idx, posx, "- Jetpack:", curses.A_BOLD)
        self.stdscr.addstr(start_pos + idx, posx + spacing, self.jetson.board["info"]["Jetpack"], curses.A_BOLD)
        self.stdscr.addstr(start_pos + idx + 1, posx, "- Board:", curses.A_BOLD)
        idx += 2
        # Load Board information
        board = self.jetson.board["board"]
        self.info_variable(start_pos + idx, posx + 2, "* Type", board["TYPE"])
        self.info_variable(start_pos + idx + 1, posx + 2, "* SOC Family", board["SOC"])
        self.info_variable(start_pos + idx + 1, posx + 33, "ID", board["CHIP_ID"], spacing=4)
        self.info_variable(start_pos + idx + 2, posx + 2, "* Module", board["MODULE"])
        self.info_variable(start_pos + idx + 2, posx + 33, "Board", board["BOARD"], spacing=7)
        self.info_variable(start_pos + idx + 3, posx + 2, "* Code Name", board["CODENAME"])
        self.info_variable(start_pos + idx + 4, posx + 2, "* Cuda ARCH", board["CUDA_ARCH_BIN"])
        self.info_variable(start_pos + idx + 5, posx + 2, "* Serial Number", board["SERIAL_NUMBER"])
        idx += 5
        if board["BOARDIDS"]:
            self.info_variable(start_pos + idx + 1, posx + 2, "* Board ids", board["BOARDIDS"])
            idx += 1
        # Libraries info
        library_line = start_pos + idx + 1
        self.stdscr.addstr(library_line, posx, "- Libraries:", curses.A_BOLD)
        idx += 1
        for name, info in sorted(self.jetson.board["libraries"].items()):
            if name == "OpenCV-Cuda":
                continue
            self.stdscr.addstr(start_pos + idx + 1, posx + 2, "* " + name + ":")
            self.stdscr.addstr(start_pos + idx + 1, posx + spacing, info, curses.A_BOLD)
            if name == "OpenCV":
                self.stdscr.addstr(start_pos + idx + 1, posx + 25, "compiled CUDA:")
                cuda = self.jetson.board["libraries"]["OpenCV-Cuda"]
                color = curses.color_pair(2) if cuda == "YES" else curses.color_pair(1)
                self.stdscr.addstr(start_pos + idx + 1, posx + 40, cuda, color | curses.A_BOLD)
            idx += 1
        # IP address and Hostname
        if self.jetson.local_interfaces:
            # Write hostname
            self.stdscr.addstr(library_line, width - 35, "- Hostname:", curses.A_BOLD)
            self.stdscr.addstr(library_line, width - 20, self.jetson.local_interfaces["hostname"], curses.A_BOLD)
            # Write all interfaces
            self.stdscr.addstr(library_line + 1, width - 35, "- Interfaces:", curses.A_BOLD)
            idx = 2
            for name, ip in self.jetson.local_interfaces["interfaces"].items():
                self.stdscr.addstr(library_line + idx, width - 33, "* " + name + ":")
                self.stdscr.addstr(library_line + idx, width - 20, ip, curses.A_BOLD)
                idx += 1
        # Author information
        plot_name_info(self.stdscr, start_pos - 1, width - 31, "Version", self.jetson.version)
        plot_name_info(self.stdscr, start_pos, width - 30, "Author", "Raffaello Bonghi")
        plot_name_info(self.stdscr, start_pos + 1, width - 30, "e-mail", "raffaello@rnext.it")
