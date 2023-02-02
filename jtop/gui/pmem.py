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
from .lib.linear_gauge import linear_gauge, GaugeName, basic_gauge
from .lib.chart import Chart
from .lib.button import Button

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


def ram_legend(stdscr, pos_y, pos_x, jetson):
    stdscr.addstr(pos_y, pos_x + 1, "     RAM     ", curses.A_REVERSE)
    # Plot all RAM values
    used = size_to_string(jetson.memory['RAM']['used'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 1, pos_x + 1, 'Used', used, spacing=3, color=NColors.cyan())
    shared = size_to_string(jetson.memory['RAM']['shared'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 2, pos_x + 1, 'Shared', shared, spacing=1, color=NColors.green())
    buffers = size_to_string(jetson.memory['RAM']['buffers'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 3, pos_x + 1, 'Buffers', buffers, color=NColors.blue())
    cached = size_to_string(jetson.memory['RAM']['cached'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 4, pos_x + 1, 'Cached', cached, spacing=1, color=NColors.yellow())
    free = size_to_string(jetson.memory['RAM']['free'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 5, pos_x + 1, 'Free', free, spacing=3)
    total = size_to_string(jetson.memory['RAM']['tot'], jetson.memory['RAM']['unit'])
    plot_name_info(stdscr, pos_y + 6, pos_x + 1, 'TOT', total, spacing=4, color=curses.A_BOLD)


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
        parameter = jetson.memory['RAM']
        # Get max value if is present
        max_val = parameter.get("tot", 100)
        # Get unit
        unit = parameter.get("unit", "k")
        # Get value
        use_val = parameter.get("used", 0)
        cpu_val = parameter.get("used", 0) - parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start=unit)
        # Append in list
        use_out = use_val / divider
        cpu_out = cpu_val / divider
        return {
            'value': [use_out, cpu_out],
            'max': szw,
            'unit': unit
        }

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
        ram_legend(self.stdscr, first + 1, width - 16, self.jetson)
        # Draw swap list
        self.draw_swap(first + height // 2 - 1, 0, width - 16, height - 2)

    def draw_swap(self, pos_y, pos_x, width, height):
        swap_table = self.jetson.memory['SWAP']['table']
        self.stdscr.addstr(pos_y, pos_x, str(len(swap_table)), curses.A_NORMAL)
        for idx, swap in enumerate(swap_table):
            if pos_y + idx < height - 1:
                if idx == 0:
                    self.stdscr.addstr(pos_y + idx, pos_x, str(swap), curses.A_REVERSE)
                else:
                    # Color gauge
                    # Change color for type partition
                    if swap[1] == 'partition':
                        color = NColors.magenta()
                    elif swap[1] == 'file':
                        color = NColors.yellow()
                    else:
                        color = NColors.cyan()
                    # data gauge
                    swap_status = swap[3]
                    used = size_to_string(swap_status['used'], swap_status['unit'])
                    total = size_to_string(swap_status['size'], swap_status['unit'])
                    data = {
                        'name': path.basename(swap[0]),
                        'color': color,
                        'values': [(swap_status.get('used', 0) / swap_status.get('size', 0) * 100.0, color)],
                        'mright': "{used}/{total}".format(used=used, total=total),
                    }
                    basic_gauge(self.stdscr, pos_y + idx, pos_x + 1, width - 8, data)
                    # Draw Priority
                    self.stdscr.addstr(pos_y + idx, width - 5, "P={prio: d}".format(prio=swap[2]), curses.A_NORMAL)
            else:
                self.stdscr.addstr(height - 1, pos_x, "BB", curses.A_NORMAL)
                break

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
                color = NColors.magenta()
            elif swap['type'] == 'file':
                color = NColors.yellow()
            else:
                color = NColors.cyan()
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
                     name=GaugeName('TOT', color=NColors.cyan()),
                     value=int(swap_status.get('use', 0) / float(swap_status.get('tot', 1)) * 100.0),
                     percent=percent,
                     status='ON' if swap_status else 'OFF')

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

    def draw_old(self, key, mouse):
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
        # cpu_bar = GaugeBar(cpu_val, NColors.cyan())
        # gpu_bar = GaugeBar(shared_val, NColors.green())
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
                color = NColors.green()
            elif self._swap_size < self._swap_old_size:
                color = NColors.yellow()
            else:
                color = curses.A_NORMAL
            try:
                self.stdscr.addstr(first + height - 3, start_pos + 12, "size", curses.A_NORMAL)
                self.stdscr.addstr(first + height - 3, start_pos + 17, "{size: <2}".format(size=self._swap_size), color)
                self.stdscr.addstr(first + height - 3, start_pos + 20, "GB", curses.A_BOLD)
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
