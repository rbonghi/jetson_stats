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

from os import path
import curses
from curses.textpad import rectangle
# Page class definition
from .jtopgui import Page
# Graphics elements
from .lib.common import (size_min)
from .lib.linear_gauge import linear_gauge, GaugeName
from .lib.chart import Chart
from .lib.button import Button

SWAP_MAX_SIZE = 15
SWAP_MIN_SIZE = 2


class MEM(Page):

    def __init__(self, stdscr, jetson):
        super(MEM, self).__init__("MEM", stdscr, jetson)
        # Initialize MEM chart
        self.chart_ram = Chart(jetson, "RAM", self.update_chart,
                               type_value=float,
                               color_text=curses.COLOR_CYAN,
                               color_chart=[curses.COLOR_GREEN, curses.COLOR_CYAN])
        # Initialize buttons
        self.button_cache = Button(stdscr, "c", action=self.action_cache)
        self.button_swap = Button(stdscr, "s", action=self.action_swap)
        self.button_increase = Button(stdscr, "+", action=self.action_increase, underline=False)
        self.button_decrease = Button(stdscr, "-", action=self.action_decrease, underline=False)
        # Size swap
        self._swap_size = 2
        self._swap_old_size = self._swap_size

    def action_cache(self, key):
        self.jetson.swap.clear_cache()

    def action_swap(self, key):
        # Change status swap
        if not self.jetson.swap.is_enable:
            self.jetson.swap.set(self._swap_size, on_boot=True)
            self._swap_old_size = self._swap_size
        else:
            self.jetson.swap.deactivate()

    def action_increase(self, key):
        if self._swap_size < SWAP_MAX_SIZE:
            self._swap_size += 1

    def action_decrease(self, key):
        if self._swap_size > SWAP_MIN_SIZE:
            self._swap_size -= 1

    def update_chart(self, jetson, name):
        parameter = jetson.ram
        # Get max value if is present
        max_val = parameter.get("tot", 100)
        # Get unit
        unit = parameter.get("unit", "k")
        # Get value
        use_val = parameter.get("use", 0)
        cpu_val = parameter.get("use", 0) - parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start=unit)
        # Append in list
        use_out = use_val / divider
        cpu_out = cpu_val / divider
        return {
            'value': [use_out, cpu_out],
            'max': szw,
            'unit': unit
        }

    def swap_menu(self, lc, size, start, width):
        line_counter = lc + 1
        # SWAP linear gauge info
        swap_status = self.jetson.swap
        swap_cached = swap_status.get('cached', {})
        szw, divider, unit = size_min(swap_status.get('tot', 0), start=swap_status.get('unit', ''))
        percent = "{use}{unit}B/{tot}{unit}B".format(use=swap_status.get('use', 0) / divider, tot=szw, unit=unit)
        # Make label cache
        label = "(cached {size}{unit}B)".format(size=swap_cached.get('size', '0'), unit=swap_cached.get('unit', ''))
        self.stdscr.addstr(line_counter, start, "Swap", curses.A_BOLD)
        self.stdscr.addstr(line_counter, width - len(label) - 1, label, curses.A_NORMAL)
        # Add all swaps
        for name in self.jetson.swap.all:
            swap = self.jetson.swap.all[name]
            line_counter += 1
            value = int(swap['used'] / float(swap['size']) * 100.0)
            # Extract size swap and unit
            szw, divider, unit = size_min(swap['size'])
            used = swap['used'] / divider
            # Change color for type partition
            if swap['type'] == 'partition':
                color = curses.color_pair(5)
            elif swap['type'] == 'file':
                color = curses.color_pair(3)
            else:
                color = curses.color_pair(6)
            linear_gauge(self.stdscr, offset=line_counter, size=size, start=start,
                         name=GaugeName(path.basename(name), color=color),
                         value=value,
                         percent="{use}/{tot}{unit}B".format(use=int(round(used)), tot=round(szw, 1), unit=unit),
                         label="P={prio: d}".format(prio=int(swap['prio'])))
        # Draw total swap gauge
        line_counter += 1
        self.stdscr.hline(line_counter, start, curses.ACS_HLINE, size - 1)
        line_counter += 1
        linear_gauge(self.stdscr, offset=line_counter, size=size, start=start,
                     name=GaugeName('TOT', color=curses.color_pair(6)),
                     value=int(swap_status.get('use', 0) / float(swap_status.get('tot', 1)) * 100.0),
                     percent=percent,
                     status='ON' if swap_status else 'OFF')

    def memory_legend(self, start_y, start_x):
        r_height = 6
        r_width = 20
        # Draw border legend
        try:
            rectangle(self.stdscr, start_y, start_x, start_y + r_height, start_x + r_width)
        except curses.error:
            pass
        # Draw name
        self.stdscr.addstr(start_y + 1, start_x + 3, "RAM Legend", curses.A_BOLD)
        # Draw CPU
        self.stdscr.addstr(start_y + 2, start_x + 2, "CPU:", (curses.color_pair(12) | curses.A_BOLD))
        self.stdscr.addstr(start_y + 3, start_x + 2, "GPU:", (curses.color_pair(8) | curses.A_BOLD))
        # Line
        self.stdscr.hline(start_y + 4, start_x + 2, curses.ACS_HLINE, r_width - 3)
        # Total used
        self.stdscr.addstr(start_y + 5, start_x + 2, "USE:", curses.A_BOLD)
        # Draw values
        cpu_val = (self.jetson.ram['use'] - self.jetson.ram['shared'])
        cpu_val, divider, cpu_unit = size_min(cpu_val, start=self.jetson.ram['unit'])
        gpu_val = self.jetson.ram['shared']
        gpu_val, divider, gpu_unit = size_min(gpu_val, start=self.jetson.ram['unit'])
        use_val = self.jetson.ram['use']
        use_val, divider, use_unit = size_min(use_val, start=self.jetson.ram['unit'])
        self.stdscr.addstr(start_y + 2, start_x + 7, "{value: 3.1f}".format(value=cpu_val), curses.A_NORMAL)
        self.stdscr.addstr(start_y + 3, start_x + 7, "{value: 3.1f}".format(value=gpu_val), curses.A_NORMAL)
        self.stdscr.addstr(start_y + 5, start_x + 7, "{value: 3.1f}".format(value=use_val), curses.A_NORMAL)
        # Unit
        self.stdscr.addstr(start_y + 2, start_x + 16, "{unit}B".format(unit=cpu_unit), curses.A_NORMAL)
        self.stdscr.addstr(start_y + 3, start_x + 16, "{unit}B".format(unit=gpu_unit), curses.A_NORMAL)
        self.stdscr.addstr(start_y + 5, start_x + 16, "{unit}B".format(unit=use_unit), curses.A_NORMAL)

    def draw_nv_table(self, start_y, start_x, r_width):
        columns_title = self.jetson.ram['table'][0]
        table = self.jetson.ram['table'][1]
        gpu_val = self.jetson.ram['shared']
        gpu_val, divider, gpu_unit = size_min(gpu_val, start=self.jetson.ram['unit'])
        gpu_val_string = str(gpu_val).rstrip('0').rstrip('.')
        gpu_val_string = "{value}{unit}B".format(value=gpu_val_string, unit=gpu_unit)
        # Size table
        r_height = 5 + len(table)
        # Draw table legend
        try:
            rectangle(self.stdscr, start_y, start_x, start_y + r_height, start_x + r_width)
            self.stdscr.hline(start_y + 2, start_x + 1, curses.ACS_HLINE, r_width - 1)
            self.stdscr.hline(start_y + 3 + len(table), start_x + 1, curses.ACS_HLINE, r_width - 1)
        except curses.error:
            pass
        # Table
        size = r_width // len(columns_title) + 1
        for idx, name in enumerate(columns_title):
            self.stdscr.addstr(start_y + 1, start_x + 2 + idx * size, name, curses.A_BOLD)
            if idx < len(columns_title) - 1:
                self.stdscr.addch(start_y, start_x + (idx + 1) * size, curses.ACS_TTEE)
                self.stdscr.addch(start_y + 1, start_x + (idx + 1) * size, curses.ACS_VLINE)
                self.stdscr.addch(start_y + 2, start_x + (idx + 1) * size, curses.ACS_BTEE)
        for num_row, row in enumerate(table):
            for num_cell, cell in enumerate(row):
                if cell == "Size":
                    value = row[cell]['val']
                    value, _, unit = size_min(value, start='k')
                    val_string = str(value).rstrip('0').rstrip('.')
                    val_string = "{value}{unit}B".format(value=val_string, unit=unit)
                else:
                    val_string = row[cell]
                try:
                    self.stdscr.addstr(start_y + 3 + num_row, start_x + 2 + size * num_cell, val_string[:size - 2], curses.A_NORMAL)
                except curses.error:
                    pass
                if num_cell < len(columns_title) - 1:
                    self.stdscr.addch(start_y + 3 + num_row, start_x + (1 + num_cell) * size, curses.ACS_VLINE)
        # Total GPU
        try:
            self.stdscr.addstr(start_y + 4 + len(table), start_x + 2 + size * (len(columns_title) - 2),
                               "Shared Tot: {GPU}".format(GPU=gpu_val_string),
                               (curses.color_pair(8) | curses.A_BOLD))
        except curses.error:
            pass
        return r_height + 1

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Set size chart memory
        size_x = [1, width * 1 // 2 + 5]
        size_y = [first + 1, height * 1 // 2 - 1]
        # Read RAM status and make gaugues
        ram_status = self.jetson.ram
        lfb_status = self.jetson.ram['lfb']
        szw, divider, unit = size_min(ram_status['tot'], start=ram_status['unit'])
        # lfb label
        percent = "{use:2.1f}{unit}/{tot:2.1f}{unit}B".format(use=ram_status['use'] / divider, unit=unit, tot=szw)
        label_lfb = "(lfb {nblock}x{size}{unit}B)".format(nblock=lfb_status['nblock'],
                                                          size=lfb_status['size'],
                                                          unit=lfb_status['unit'])
        # Draw the GPU chart
        self.chart_ram.draw(self.stdscr, size_x, size_y, label="{percent} - {lfb}".format(percent=percent, lfb=label_lfb))
        # Make swap list file
        self.swap_menu(lc=first, start=size_x[1] + 3, size=size_x[1] - 13, width=width)
        # Plot Linear Gauge
        # cpu_val = int((ram_status['use'] - ram_status['shared']) / float(ram_status['tot']) * 100.0)
        # shared_val = int(ram_status['shared'] / float(ram_status['tot']) * 100.0)
        # cpu_bar = GaugeBar(cpu_val, curses.color_pair(6))
        # gpu_bar = GaugeBar(shared_val, curses.color_pair(2))
        # RAM linear gauge info
        if 'table' in self.jetson.ram:
            size_table = self.draw_nv_table(size_y[1] + 2, 1, size_x[1])
            if size_y[1] + size_table + 2 >= height:
                for n_arrow in range(1, size_x[1]):
                    self.stdscr.addch(height - 2, 1 + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
        else:
            # Write memory legend
            self.memory_legend(size_y[1] + 2, 1)
        # Swap controller
        self.button_swap.draw(first + height - 7, size_x[1] + 3, key, mouse)
        self.stdscr.addstr(first + height - 7, size_x[1] + 9, "Swap extra", curses.A_UNDERLINE)
        enable_swap = "Status:"
        self.stdscr.addstr(first + height - 6, size_x[1] + 9, enable_swap, curses.A_NORMAL)
        # Status swap
        swap_enable = self.jetson.swap.is_enable
        self.stdscr.addstr(
            first + height - 5, size_x[1] + 10,
            "Enabled" if swap_enable else "Disable",
            curses.A_BOLD if swap_enable else curses.A_NORMAL)
        # Swap boxes
        start_pos = size_x[1] + 3
        if not swap_enable:
            # Draw keys to decrease size swap
            self.button_decrease.draw(first + height - 4, start_pos, key, mouse)
            # Draw keys to increase size swap
            self.button_increase.draw(first + height - 4, start_pos + 6, key, mouse)
            # Draw selected number
            if self._swap_size > self._swap_old_size:
                color = curses.color_pair(2)
            elif self._swap_size < self._swap_old_size:
                color = curses.color_pair(3)
            else:
                color = curses.A_NORMAL
            try:
                self.stdscr.addstr(first + height - 3, start_pos + 12, "size", curses.A_NORMAL)
                self.stdscr.addstr(first + height - 3, start_pos + 17, "{size: <2}".format(size=self._swap_size), color)
                self.stdscr.addstr(first + height - 3, start_pos + 18, "GB", curses.A_BOLD)
            except curses.error:
                pass
        # else:
        #    # Print folder swapfile
        #    self.stdscr.addstr(first + height - 3, start_pos + 11, "{folder}".format(folder=self.jetson.swap.file), curses.A_BOLD)
        # Clear cache button
        self.button_cache.draw(first + height - 7, size_x[1] + 21, key, mouse)
        try:
            self.stdscr.addstr(first + height - 7, size_x[1] + 27, "Clear", curses.A_UNDERLINE)
            self.stdscr.addstr(first + height - 6, size_x[1] + 27, "cache", curses.A_NORMAL)
        except curses.error:
            pass
# EOF
