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
from .jtopgui import Page
# Graphics elements
from .lib.common import (
    strfdelta,
    plot_name_info,
    jetson_clocks_gui,
    nvp_model_gui)
from .lib.colors import NColors
from .lib.linear_gauge import linear_gauge, basic_gauge, GaugeName
from .pcpu import compact_cpus
from .pgpu import plot_GPUs
from .pmem import compact_memory
from .pengine import compact_engines
from .pcontrol import plot_temperatures, plot_watts


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


class ALL(Page):

    def __init__(self, stdscr, jetson):
        super(ALL, self).__init__("ALL", stdscr, jetson)
        # Number columns
        self._n_columns = 0
        if jetson.engine:
            self._n_columns += 1
        if jetson.temperature:
            self._n_columns += 1
        if jetson.power:
            self._n_columns += 1

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
        line_counter += 1
        line_counter = plot_GPUs(self.stdscr, line_counter, self.jetson.gpu, width)
        # Status disk
        line_counter += 1
        disk_status = self.jetson.disk
        linear_gauge(self.stdscr, offset=line_counter, size=width,
                     name=GaugeName('Dsk', color=NColors.yellow()),
                     value=int(float(disk_status['used']) / float(disk_status['total']) * 100.0),
                     percent="{0:2.1f}GB/{1:2.1f}GB".format(disk_status['used'], disk_status['total']),
                     bar="#")
        # If empty return
        if self._n_columns == 0:
            return
        # Add engines, temperature and power
        column_width = (width) // (self._n_columns)
        column_height = height - line_counter - 3 + first
        # Plot compact info
        column = 0
        if self.jetson.engine:
            size_info = compact_engines(self.stdscr, 0, line_counter + 1, column_width + 2, self.jetson)
            if size_info > column_height:
                for n_arrow in range(column_width + 1):
                    self.stdscr.addch(first + height - 2, 1 + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
            column += column_width
        # Plot temperatures
        if self.jetson.temperature:
            size_temperatures = plot_temperatures(self.stdscr, column, line_counter + 1, column_width - 4, column_height, self.jetson)
            if size_temperatures > column_height:
                for n_arrow in range(column_width - 5):
                    self.stdscr.addch(first + height - 2, column + n_arrow + 3, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
            column += column_width
        # plot watts
        if self.jetson.power:
            plot_watts(self.stdscr, column, line_counter + 1, column_width - 4, column_height, self.jetson)
# EOF
