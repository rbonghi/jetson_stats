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
from .jtopguilib import plot_name_info
# Menu GUI pages
from .jtopguimenu import strfdelta


class INFO(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(INFO, self).__init__("INFO", stdscr, jetson, refresh)

    def draw(self, key):
        """
            Write all environment variables
        """
        # Screen size
        height, width = self.stdscr.getmaxyx()
        # Position information
        posx = 2
        start_pos = 2
        spacing = 20
        # Up time
        uptime_string = strfdelta(timedelta(seconds=self.jetson.uptime), "{days} days {hours}:{minutes}:{seconds}")
        plot_name_info(self.stdscr, start_pos, posx, "- Up Time", uptime_string)
        start_pos += 1
        # Loop build information
        idx = 0
        # Board info
        self.stdscr.addstr(start_pos + idx, posx, "- Board:", curses.A_BOLD)
        for name, info in self.jetson.board["board"].items():
            self.stdscr.addstr(start_pos + idx + 1, posx + 2, "* " + name + ":")
            self.stdscr.addstr(start_pos + idx + 1, posx + spacing, info, curses.A_BOLD)
            idx += 1
        # Libraries info
        self.stdscr.addstr(start_pos + idx + 1, posx, "- Libraries:", curses.A_BOLD)
        idx += 1
        for name, info in self.jetson.board["libraries"].items():
            self.stdscr.addstr(start_pos + idx + 1, posx + 2, "* " + name + ":")
            self.stdscr.addstr(start_pos + idx + 1, posx + spacing, info, curses.A_BOLD)
            idx += 1
        # IP address and Hostname
        if self.jetson.local_interfaces:
            plot_name_info(self.stdscr, start_pos + idx + 1, posx, "- Hostname", self.jetson.local_interfaces["hostname"])
            self.stdscr.addstr(start_pos + idx + 2, posx, "- Interfaces", curses.A_BOLD)
            idx += 3
            for name, ip in self.jetson.local_interfaces["interfaces"].items():
                self.stdscr.addstr(start_pos + idx, posx + 2, "* " + name + ":")
                self.stdscr.addstr(start_pos + idx, posx + spacing, ip, curses.A_BOLD)
                idx += 1
        # Author information
        plot_name_info(self.stdscr, start_pos - 1, width - 31, "Version", self.jetson.version)
        plot_name_info(self.stdscr, start_pos, width - 30, "Author", "Raffaello Bonghi")
        plot_name_info(self.stdscr, start_pos + 1, width - 30, "e-mail", "raffaello@rnext.it")
