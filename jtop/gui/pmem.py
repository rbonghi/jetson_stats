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

from os import path
import curses
from curses.textpad import rectangle
# Page class definition
from .jtopgui import Page
# Graphics elements
from .lib.colors import NColors
from .lib.common import (size_min, unit_to_string, size_to_string, plot_name_info)
from .lib.linear_gauge import basic_gauge
from .lib.chart import Chart
from .lib.button import Button
from .lib.smallbutton import SmallButton

SWAP_MAX_SIZE = 15
SWAP_MIN_SIZE = 2


def mem_gauge(stdscr, pos_y, pos_x, size, mem_data):
    # Plot values
    values = [
        ((mem_data['used'] - mem_data['shared']) / mem_data['tot'] * 100.0, NColors.green()),
        (mem_data['shared'] / mem_data['tot'] * 100.0, NColors.green() | curses.A_BOLD),
        (mem_data['buffers'] / mem_data['tot'] * 100.0, NColors.blue()),
        (mem_data['cached'] / mem_data['tot'] * 100.0, NColors.yellow()),
    ]
    used = size_to_string(mem_data['used'], mem_data['unit'])
    total = size_to_string(mem_data['tot'], mem_data['unit'])
    # Draw gauge
    data = {
        'name': 'Mem',
        'color': NColors.cyan(),
        'values': values,
        'mright': "{used}/{total}".format(used=used, total=total)
    }
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


def swap_gauge(stdscr, pos_y, pos_x, size, mem_data):
    # Plot values
    values = [
        (mem_data['used'] / mem_data['tot'] * 100.0, NColors.red()),
        (mem_data['cached'] / mem_data['tot'] * 100.0, NColors.yellow()),
    ]
    used = size_to_string(mem_data['used'], mem_data['unit'])
    total = size_to_string(mem_data['tot'], mem_data['unit'])
    # Draw gauge
    data = {
        'name': 'Swp',
        'color': NColors.cyan(),
        'values': values,
        'mright': "{used}/{total}".format(used=used, total=total)
    }
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


def emc_gauge(stdscr, pos_y, pos_x, size, mem_data):
    # online status
    online = mem_data['online'] if 'online' in mem_data else True
    # Plot values
    values = [
        (mem_data['cur'] / mem_data['max'] * 100.0, NColors.green()),
    ] if online else []
    # Draw gauge
    data = {
        'name': 'Emc',
        'color': NColors.cyan(),
        'values': values,
        'mleft': unit_to_string(mem_data['min'], mem_data['unit'], 'Hz'),
        'mright': unit_to_string(mem_data['max'], mem_data['unit'], 'Hz'),
    }
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 13, data, bar=':')
    # Draw info EMC
    curr_string = unit_to_string(mem_data['cur'], mem_data['unit'], 'Hz')
    stdscr.addstr(pos_y, pos_x + size - 11, curr_string, curses.A_ITALIC)
    curr_string = "{val:3.0f}%".format(val=mem_data['val'])
    stdscr.addstr(pos_y, pos_x + size - 4, curr_string, curses.A_BOLD)


def compact_memory(stdscr, pos_y, pos_x, width, jetson):
    line_counter = 1
    # Draw memory gauge
    mem_gauge(stdscr, pos_y, pos_x, width, jetson.memory['RAM'])
    if 'SWAP' in jetson.memory:
        swap_gauge(stdscr, pos_y + line_counter, pos_x, width, jetson.memory['SWAP'])
        line_counter += 1
    if 'EMC' in jetson.memory:
        emc_gauge(stdscr, pos_y + line_counter, pos_x, width, jetson.memory['EMC'])
        line_counter += 1
    if 'IRAM' in jetson.memory:
        # TODO add Iram gauge
        stdscr.addstr(pos_y + line_counter, pos_x, "TODO", curses.A_BOLD)
        line_counter += 1
    return line_counter


class MEM(Page):

    def __init__(self, stdscr, jetson):
        super(MEM, self).__init__("MEM", stdscr, jetson)
        # Initialize MEM chart
        self.chart_ram = Chart(jetson, "RAM", self.update_chart,
                               type_value=float,
                               color_text=curses.COLOR_CYAN,
                               color_chart=[curses.COLOR_YELLOW, curses.COLOR_BLUE, curses.COLOR_GREEN, curses.COLOR_CYAN])
        # Initialize buttons
        self._button_cache = SmallButton(stdscr, self.action_cache, key='c')
        self._button_increase = SmallButton(stdscr, self.action_increase, key='+')
        self._button_decrease = SmallButton(stdscr, self.action_decrease, key='-')
        self._button_swap = SmallButton(stdscr, self.action_swap, key='s')
        # Size swap
        self._swap_size = 2
        self._swap_old_size = self._swap_size

    def action_cache(self, key):
        self.jetson.memory.clear_cache()

    def action_swap(self, key):
        swap_status = self.jetson.memory.swap_is_enable()
        # Change status swap
        if not swap_status:
            self.jetson.memory.swap_set(self._swap_size, on_boot=True)
            self._swap_old_size = self._swap_size
        else:
            self.jetson.memory.swap_deactivate()

    def action_increase(self, key):
        if self._swap_size < SWAP_MAX_SIZE:
            self._swap_size += 1

    def action_decrease(self, key):
        if self._swap_size > SWAP_MIN_SIZE:
            self._swap_size -= 1

    def update_chart(self, jetson, name):
        parameter = jetson.memory['RAM']
        # Get max value if is present
        max_val = parameter.get("tot", 100)
        # Get unit
        unit = parameter.get("unit", "k")
        # Get value
        cached_val = parameter.get("cached", 0)
        buffer_val = parameter.get("buffers", 0)
        use_val = parameter.get("used", 0)
        cpu_val = parameter.get("used", 0) - parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start=unit)
        # Append in list
        cached_out = (cached_val + buffer_val + use_val) / divider
        buffers_out = (buffer_val + use_val) / divider
        gpu_out = (use_val) / divider
        cpu_out = cpu_val / divider
        return {
            'value': [cached_out, buffers_out, gpu_out, cpu_out],
            'max': szw,
            'unit': unit
        }

    def draw_ram_legend(self, pos_y, pos_x):
        self.stdscr.addstr(pos_y, pos_x + 1, "     RAM     ", curses.A_REVERSE)
        # Plot all RAM values
        used = size_to_string(self.jetson.memory['RAM']['used'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 1, pos_x + 1, 'Used', used, spacing=3, color=NColors.cyan())
        shared = size_to_string(self.jetson.memory['RAM']['shared'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 2, pos_x + 1, 'Shared', shared, spacing=1, color=NColors.green())
        buffers = size_to_string(self.jetson.memory['RAM']['buffers'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 3, pos_x + 1, 'Buffers', buffers, color=NColors.blue())
        cached = size_to_string(self.jetson.memory['RAM']['cached'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 4, pos_x + 1, 'Cached', cached, spacing=1, color=NColors.yellow())
        free = size_to_string(self.jetson.memory['RAM']['free'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 5, pos_x + 1, 'Free', free, spacing=3)
        total = size_to_string(self.jetson.memory['RAM']['tot'], self.jetson.memory['RAM']['unit'])
        plot_name_info(self.stdscr, pos_y + 6, pos_x + 1, 'TOT', total, spacing=4, color=curses.A_BOLD)

    def draw_swap_table(self, pos_y, pos_x, width, height):
        swap_info = self.jetson.memory['SWAP']
        swap_table = swap_info['table']
        used = size_to_string(swap_info['used'], swap_info['unit'])
        total = size_to_string(swap_info['tot'], swap_info['unit'])
        cached = size_to_string(swap_info['cached'], swap_info['unit'])
        self.stdscr.addstr(pos_y, pos_x + 1, "SWAP", curses.A_BOLD)
        self.stdscr.addstr(pos_y, pos_x + 6, "{used}/{total} (Cached {cached})".format(used=used, total=total, cached=cached), NColors.red())
        for idx, (name, swap) in enumerate(swap_table.items()):
            if pos_y + idx < height:
                # Color gauge
                # Change color for type partition
                if swap['type'] == 'partition':
                    color = NColors.magenta()
                elif swap['type'] == 'file':
                    color = NColors.yellow()
                else:
                    color = NColors.cyan()
                # data gauge
                used = size_to_string(swap['used'], swap['unit'])
                total = size_to_string(swap['size'], swap['unit'])
                data = {
                    'name': path.basename(name),
                    'color': color,
                    'values': [(swap.get('used', 0) / swap.get('size', 0) * 100.0, color)],
                    'mleft': "P{prio}".format(prio=swap['prio']),
                    'mright': "{used}/{total}".format(used=used, total=total),
                }
                basic_gauge(self.stdscr, pos_y + idx + 1, pos_x + 1, width - 2, data)
            else:
                for n_arrow in range(width):
                    self.stdscr.addch(height, pos_x + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
                break

    def draw_swap_controller(self, pos_y, pos_x, key, mouse):
        status = self.jetson.memory.swap_is_enable()
        self._button_swap.draw(pos_y, pos_x, key, mouse, label="Disable Swap" if status else "Enable Swap ")
        # Draw selected number
        if self._swap_size > self._swap_old_size:
            color = NColors.green()
        elif self._swap_size < self._swap_old_size:
            color = NColors.yellow()
        else:
            color = curses.A_NORMAL
        self.stdscr.addstr(pos_y + 1, pos_x + 6, "{size: <2}".format(size=self._swap_size), color)
        self.stdscr.addstr(pos_y + 1, pos_x + 9, "GB", curses.A_BOLD)
        # Draw buttons
        if status:
            return
        self._button_increase.draw(pos_y + 1, pos_x, key, mouse)
        self._button_decrease.draw(pos_y + 1, pos_x + 13, key, mouse)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()

        # Set size chart memory
        size_x = [1, width - 18]
        size_y = [first + 1, height // 2 - 2]
        # Draw the GPU chart
        # lfb label
        mem_data = self.jetson.memory['RAM']
        used = size_to_string(mem_data['used'], mem_data['unit'])
        total = size_to_string(mem_data['tot'], mem_data['unit'])
        percent = "{used}/{total}B".format(used=used, total=total)
        label_lfb = "(lfb {nblock}x4MB)".format(nblock=mem_data['lfb'])
        self.chart_ram.draw(self.stdscr, size_x, size_y, label="{percent} - {lfb}".format(percent=percent, lfb=label_lfb))
        # Draw all RAM
        self.draw_ram_legend(first + 1, width - 16)
        # Draw EMC gague
        line_counter = 0
        if 'EMC' in self.jetson.memory:
            emc_gauge(self.stdscr, first + height // 2 - 1 + line_counter, 1, width - 22, self.jetson.memory['EMC'])
            line_counter += 1
        if 'IRAM' in self.jetson.memory:
            # TODO add Iram gauge
            self.stdscr.addstr(self.stdscr, first + height // 2 - 1 + line_counter, 1, "TODO", curses.A_BOLD)
            line_counter += 1
        # Draw swap list
        self.draw_swap_table(first + height // 2 - 1 + line_counter, 0, width - 22, height - 2)
        # Draw buttons
        self._button_cache.draw(first + height // 2, width - 18, key, mouse, label="clear cache ")
        self.draw_swap_controller(first + height // 2 + 2, width - 18, key, mouse)

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
            try:
                self.stdscr.addstr(start_y + 1, start_x + 2 + idx * size, name, curses.A_BOLD)
            except curses.error:
                pass
            if idx < len(columns_title) - 1:
                try:
                    self.stdscr.addch(start_y, start_x + (idx + 1) * size, curses.ACS_TTEE)
                    self.stdscr.addch(start_y + 1, start_x + (idx + 1) * size, curses.ACS_VLINE)
                    self.stdscr.addch(start_y + 2, start_x + (idx + 1) * size, curses.ACS_BTEE)
                except curses.error:
                    pass
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
                    try:
                        self.stdscr.addch(start_y + 3 + num_row, start_x + (1 + num_cell) * size, curses.ACS_VLINE)
                    except curses.error:
                        pass
        # Total GPU
        try:
            self.stdscr.addstr(start_y + 4 + len(table), start_x + 2 + size * (len(columns_title) - 2),
                               "Shared Tot: {GPU}".format(GPU=gpu_val_string),
                               (NColors.igreen() | curses.A_BOLD))
        except curses.error:
            pass
        return r_height + 1
# EOF
