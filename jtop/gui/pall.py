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

import curses
from curses.textpad import rectangle
from .jtopgui import Page
# Graphics elements
from .lib.common import (
    strfdelta,
    plot_name_info,
    jetson_clocks_gui,
    nvp_model_gui)
from .lib.colors import NColors
from .lib.linear_gauge import basic_gauge
from .lib.common import size_to_string
from .pcpu import compact_cpus
from .pmem import compact_memory
from .pgpu import compact_gpu
# Menu GUI pages
from .jtopguimenu import (
    plot_watts,
    compact_info,
    plot_temperatures)


def compact_status(stdscr, pos_y, pos_x, width, jetson):
    line_counter = 0
    # Fan status
    if jetson.fan.all_speed().items():
        for fan, speed in jetson.fan.all_speed().items():
            line_counter += 1
            data = {
                'name': 'Fan',
                'color': NColors.magenta(),
                'online': jetson.fan,
                'values': [(speed, NColors.magenta() | curses.A_BOLD)]
            }
            basic_gauge(stdscr, pos_y, pos_x + line_counter, width - 3, data)
    else:
        line_counter += 1
        data = {
            'name': 'Fan',
            'color': NColors.magenta(),
            'online': False,
            'coffline': NColors.imagenta(),
            'message': 'NOT AVAILABLE',
        }
        basic_gauge(stdscr, pos_y, pos_x + line_counter, width - 3, data)
    # Jetson clocks status: Running (Green) or Normal (Grey)
    if jetson.jetson_clocks is not None:
        jetson_clocks_gui(stdscr, pos_y + line_counter, pos_x + 1, jetson)
        line_counter += 1
    # NVP Model
    if jetson.nvpmodel is not None:
        nvp_model_gui(stdscr, pos_y + line_counter, pos_x + 1, jetson)
        line_counter += 1
    # Model board information
    uptime_string = strfdelta(jetson.uptime, "{days} days {hours}:{minutes}:{seconds}")
    plot_name_info(stdscr, pos_y + line_counter, pos_x + 1, "Uptime", uptime_string)
    return line_counter + 1


def disk_gauge(stdscr, pos_y, pos_x, size, disk_status):
    # value disk
    value = int(float(disk_status['used']) / float(disk_status['total']) * 100.0)
    used = size_to_string(disk_status['used'], disk_status['unit'])
    total = size_to_string(disk_status['total'], disk_status['unit'])
    data = {
        'name': 'Dsk',
        'color': NColors.yellow(),
        'values': [(value, NColors.yellow())],
        'mright': "{used}/{total}".format(used=used, total=total)
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 2, data, bar="#")
    return 1


class ALL(Page):

    def __init__(self, stdscr, jetson):
        super(ALL, self).__init__("ALL", stdscr, jetson)

    def draw(self, key, mouse):
        """
            Update screen with values
        """
        # Screen size
        height, width, first = self.size_page()
        line_counter = first + 1
        # Plot Status CPU
        line_counter += compact_cpus(self.stdscr, line_counter, 0, width, self.jetson)
        # Plot status memory
        size_memory = compact_memory(self.stdscr, line_counter, 0, width // 2, self.jetson)
        # Plot compact info
        size_status = compact_status(self.stdscr, line_counter, width // 2, width // 2, self.jetson)
        # Update line counter
        line_counter += max(size_memory, size_status)
        # GPU linear gauge info
        line_counter += compact_gpu(self.stdscr, line_counter, 0, width, self.jetson)
        # Status disk
        line_counter += disk_gauge(self.stdscr, line_counter, 0, width, self.jetson.disk)
        # Last part of information
        total, power = self.jetson.power
        mini_menu = 1
        mini_menu += 1 if self.jetson.temperature else 0
        mini_menu += 1 if power else 0
        column_width = (width) // (mini_menu)
        column_height = height - line_counter - 3 + first
        # Make rectangle
        rectangle(self.stdscr, line_counter + 1, 0, line_counter + 1 + column_height, width - 1)
        # Plot compact info
        size_info = compact_info(self.stdscr, 0, line_counter + 1, column_width + 2, column_height, self.jetson)
        if size_info > column_height:
            for n_arrow in range(column_width + 1):
                self.stdscr.addch(first + height - 2, 1 + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
        # Plot temperatures
        if self.jetson.temperature:
            self.add_line(line_counter + 1, column_width + 2, column_height)
            size_temperatures = plot_temperatures(self.stdscr, column_width + 2, line_counter + 1, column_width - 4, column_height, self.jetson)
            if size_temperatures > column_height:
                for n_arrow in range(column_width - 5):
                    self.stdscr.addch(first + height - 2, column_width + n_arrow + 3, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
        # plot watts
        if power:
            self.add_line(line_counter + 1, 2 * column_width - 2, column_height)
            plot_watts(self.stdscr, 2 * column_width - 1, line_counter + 1, column_width + 2, column_height, self.jetson)

    def add_line(self, pos_y, pos_x, height):
        """
        http://www.melvilletheatre.com/articles/ncurses-extended-characters/index.html
        """
        self.stdscr.addch(pos_y, pos_x, curses.ACS_TTEE)
        self.stdscr.vline(pos_y + 1, pos_x, curses.ACS_VLINE, height - 1)
        self.stdscr.addch(pos_y + height, pos_x, curses.ACS_BTEE)
# EOF
