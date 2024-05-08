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
    jetson_clocks_gui)
from .lib.colors import NColors
from .lib.linear_gauge import basic_gauge
from .lib.common import size_to_string
from .lib.process_table import ProcessTable
from .pcpu import compact_cpus
from .pgpu import compact_gpu
from .pmem import compact_memory
from .pengine import compact_engines
from .pcontrol import compact_temperatures, compact_power


def compact_status(stdscr, pos_y, pos_x, width, height, jetson):
    line_counter = 0
    # Fan status
    if jetson.fan:
        for name, fan in jetson.fan.items():
            for idx, speed in enumerate(fan['speed']):
                try:
                    data = {
                        'name': 'Fan {idx}'.format(idx=idx) if len(fan['speed']) > 1 else 'FAN',
                        'color': NColors.cyan(),
                        'online': jetson.fan,
                        'values': [(speed, NColors.cyan())]
                    }
                    # Show RPM if exist
                    if 'rpm' in fan:
                        rpm = "{rpm:>4}RPM".format(rpm=fan['rpm'][idx])
                        stdscr.addstr(pos_y + line_counter, pos_x + width - 9, rpm, curses.A_NORMAL)
                    size_fan_gauge = width - 12 if 'rpm' in fan else width - 3
                    basic_gauge(stdscr, pos_y + line_counter, pos_x + 1, size_fan_gauge, data)
                    line_counter += 1
                except curses.error:
                    pass
    else:
        try:
            data = {
                'name': 'Fan',
                'color': NColors.cyan(),
                'online': False,
                'coffline': NColors.icyan(),
                'message': 'NOT AVAILABLE',
            }
            basic_gauge(stdscr, pos_y + line_counter, pos_x + 1, width - 3, data)
            line_counter += 1
        except curses.error:
            pass
    # Jetson clocks status: Running (Green) or Normal (Grey)
    if jetson.jetson_clocks is not None:
        jetson_clocks_gui(stdscr, pos_y + line_counter, pos_x + 1, jetson)
        line_counter += 1
    # NVP Model
    if jetson.nvpmodel is not None:
        plot_name_info(stdscr, pos_y + line_counter, pos_x + 1, "NV Power[" + str(jetson.nvpmodel.id) + "]", jetson.nvpmodel.name)
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
        # Add Process table
        self.process_table = ProcessTable(self.stdscr, self.jetson)
        # Number columns
        self._max_height_menu = 0
        self._columns = []
        if jetson.engine:
            self._columns += [compact_engines]
            self._max_height_menu = max(self._max_height_menu, 5)
        if jetson.temperature:
            self._columns += [compact_temperatures]
            self._max_height_menu = max(self._max_height_menu, len(jetson.temperature))
        if jetson.power:
            self._columns += [compact_power]
            self._max_height_menu = max(self._max_height_menu, len(jetson.power['rail']) + 1)
        # End corner
        self._max_height_menu += 2

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
        size_memory = compact_memory(self.stdscr, line_counter, 0, width // 2, height, self.jetson)
        # Plot compact info
        size_status = compact_status(self.stdscr, line_counter, width // 2, width // 2, height, self.jetson)
        # Update line counter
        line_counter += max(size_memory, size_status)
        # GPU linear gauge info
        if height > line_counter:
            line_counter += compact_gpu(self.stdscr, line_counter, 0, width, self.jetson)
        # Status disk
        if height > line_counter:
            line_counter += disk_gauge(self.stdscr, line_counter, 0, width, self.jetson.disk)
        # Plot all processes
        height_free_area = height - line_counter - self._max_height_menu - 1
        offset_process_y = 0
        if self.jetson.processes:
            line_counter += self.process_table.draw(line_counter, 0, width, height_free_area, key, mouse)
            offset_process_y = 2
        # Evaluate number of columns
        n_columns = len(self._columns)
        # If empty return
        if n_columns == 0:
            return
        # Plot low bar background line
        pos_y_mini_menu = line_counter + offset_process_y
        if height_free_area > offset_process_y:
            pos_y_mini_menu = height - self._max_height_menu - 1
        column_height = height - pos_y_mini_menu
        if column_height <= 1:
            return
        # Upper block
        try:
            self.stdscr.addch(pos_y_mini_menu, 0, curses.ACS_ULCORNER)
            self.stdscr.addch(pos_y_mini_menu, width - 1, curses.ACS_URCORNER)
            self.stdscr.hline(pos_y_mini_menu, 1, curses.ACS_HLINE, width - 2)
        except curses.error:
            pass
        # vertical Lines
        if column_height > 3:
            self.stdscr.vline(pos_y_mini_menu + 1, 0, curses.ACS_VLINE, column_height - 3)
            self.stdscr.vline(pos_y_mini_menu + 1, width - 1, curses.ACS_VLINE, column_height - 3)
        # Lower line
        try:
            self.stdscr.addch(pos_y_mini_menu + self._max_height_menu - 1, 0, curses.ACS_LLCORNER)
            self.stdscr.addch(pos_y_mini_menu + self._max_height_menu - 1, width - 1, curses.ACS_LRCORNER)
            self.stdscr.hline(pos_y_mini_menu + self._max_height_menu - 1, 1, curses.ACS_HLINE, width - 2)
        except curses.error:
            self.stdscr.addch(pos_y_mini_menu + column_height - 2, 0, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
            self.stdscr.addch(pos_y_mini_menu + column_height - 2, width - 1, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
        # Cancel columns depend of the width size
        n_print = n_columns
        if width < 75 and n_columns > 1:
            n_print -= 1
        if width < 49 and n_columns > 2:
            n_print -= 1
        # Add engines, temperature and power
        column_width = (width) // (n_print)
        for nline in range(n_print):
            func = self._columns[nline]
            func(self.stdscr, pos_y_mini_menu, column_width * nline, column_width, column_height, self.jetson)
            if nline < n_print - 1:
                self.stdscr.addch(pos_y_mini_menu, column_width * (nline + 1), curses.ACS_TTEE)
                if column_height > 3:
                    self.stdscr.vline(pos_y_mini_menu + 1, column_width * (nline + 1), curses.ACS_VLINE, column_height - 3)
                if height_free_area >= offset_process_y:
                    self.stdscr.addch(pos_y_mini_menu + column_height - 2, column_width * (nline + 1), curses.ACS_BTEE)
                else:
                    self.stdscr.addch(pos_y_mini_menu + column_height - 2, column_width * (nline + 1),
                                      curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
# EOF
