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
# Page class definition
from .jtopgui import Page
# Graphics elements
from .lib.colors import NColors
from .lib.common import (size_min, unit_to_string, size_to_string, plot_name_info)
from .lib.linear_gauge import basic_gauge, basic_gauge_simple
from .lib.chart import Chart
from .lib.smallbutton import SmallButton
from .pcpu import cpu_grid

SWAP_MAX_SIZE = 100
SWAP_MIN_SIZE = 1


def mem_gauge(stdscr, pos_y, pos_x, size, mem_data):
    # Plot values
    values = [
        ((mem_data['used'] - mem_data['shared']) / mem_data['tot'] * 100.0, NColors.cyan()),
        (mem_data['shared'] / mem_data['tot'] * 100.0, NColors.green() | curses.A_BOLD),
        (mem_data['buffers'] / mem_data['tot'] * 100.0, NColors.blue()),
        (mem_data['cached'] / mem_data['tot'] * 100.0, NColors.yellow()),
    ]
    used = size_to_string(mem_data['used'], 'k')
    total = size_to_string(mem_data['tot'], 'k')
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
    ] if mem_data['tot'] > 0 else []
    used = size_to_string(mem_data['used'], 'k')
    total = size_to_string(mem_data['tot'], 'k')
    # Draw gauge
    data = {
        'name': 'Swp',
        'color': NColors.cyan(),
        'values': values,
        'online': mem_data['tot'] > 0,
        'mright': "{used}/{total}".format(used=used, total=total)
    }
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


def emc_gauge(stdscr, pos_y, pos_x, size, mem_data):
    # online status
    online = mem_data['online'] if 'online' in mem_data else True
    # Plot values
    if 'max' in mem_data:
        values = [
            (mem_data['cur'] / mem_data['max'] * 100.0, NColors.green()),
        ] if online else []
        # Draw gauge
        data = {
            'name': 'Emc',
            'color': NColors.cyan(),
            'values': values,
            'mleft': unit_to_string(mem_data['min'], 'k', 'Hz') if 'min' in mem_data else '',
            'mright': unit_to_string(mem_data['max'], 'k', 'Hz'),
        }
        # Draw gauge
        basic_gauge(stdscr, pos_y, pos_x, size - 13, data, bar=':')
        # Draw info EMC
        curr_string = unit_to_string(mem_data['cur'], 'k', 'Hz')
        stdscr.addstr(pos_y, pos_x + size - 11, curr_string, NColors.italic())
    else:
        mem_data['name'] = 'Emc'
        basic_gauge_simple(stdscr, pos_y, pos_x, size - 6, mem_data)
    # Show val
    curr_string = "{val:3.0f}%".format(val=mem_data['val'])
    stdscr.addstr(pos_y, pos_x + size - 4, curr_string, curses.A_BOLD)


def iram_gauge(stdscr, pos_y, pos_x, size, mem_data):
    used = size_to_string(mem_data['used'], 'k')
    total = size_to_string(mem_data['tot'], 'k')
    # Make data for gauge
    data = {
        'name': 'Iram',
        'color': NColors.cyan(),
        'values': [(mem_data['used'] / mem_data['tot'] * 100.0, NColors.cyan())],
        'mright': "{used}/{total}".format(used=used, total=total),
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 12, data)
    # Write lfb
    label_lfb = "(lfb {nblock}{unit}B)".format(nblock=mem_data['lfb'], unit='k')
    stdscr.addstr(pos_y, pos_x + size - 11, label_lfb, curses.A_NORMAL)


def compact_memory(stdscr, pos_y, pos_x, width, height, jetson):
    line_counter = 1
    # Draw memory gauge
    try:
        mem_gauge(stdscr, pos_y, pos_x, width, jetson.memory['RAM'])
    except curses.error:
        return 0
    try:
        swap_gauge(stdscr, pos_y + line_counter, pos_x, width, jetson.memory['SWAP'])
        line_counter += 1
    except curses.error:
        return line_counter
    if 'EMC' in jetson.memory:
        try:
            emc_gauge(stdscr, pos_y + line_counter, pos_x, width, jetson.memory['EMC'])
            line_counter += 1
        except curses.error:
            return line_counter
    if 'IRAM' in jetson.memory:
        try:
            iram_gauge(stdscr, pos_y + line_counter, pos_x, width, jetson.memory['IRAM'])
            line_counter += 1
        except curses.error:
            pass
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
        self._button_cache = SmallButton(stdscr, self.action_cache, "clear cache", trigger_key='c')
        self._button_increase = SmallButton(stdscr, self.action_increase, trigger_key='+')
        self._button_decrease = SmallButton(stdscr, self.action_decrease, trigger_key='-')
        self._button_create = SmallButton(stdscr, self.action_create, "Create new", trigger_key='s')
        self._button_boot = SmallButton(stdscr, self.action_boot, "on boot", toggle=True, trigger_key='b')
        self._button_swap = SmallButton(stdscr, self.action_swap)
        # Size swap
        self._swap_size = SWAP_MIN_SIZE
        self._swap_old_size = self._swap_size
        self._on_boot = False
        # Swap table control
        self._swap_pressed = -1
        self._swap_name = self.get_new_swap_name()

    def action_cache(self, info, selected):
        self.jetson.memory.clear_cache()

    def action_create(self, info, selected):
        # Change status swap
        if not self.jetson.memory.swap_is_enable(self._swap_name):
            self.jetson.memory.swap_set(self._swap_size, self._swap_name, on_boot=self._on_boot)
            self._swap_old_size = self._swap_size

    def action_boot(self, info, selected):
        self._on_boot = selected

    def action_swap(self, info, selected):
        if self._swap_pressed != -1:
            # Read name swap
            name = list(self._swaps)[self._swap_pressed]
            swap = self._swaps[name]
            # Deactivate SWAP
            if self.jetson.memory.swap_is_enable(name) and swap['type'] == 'file':
                self.jetson.memory.swap_deactivate(name)

    def action_increase(self, info, selected):
        if self._swap_size < SWAP_MAX_SIZE:
            self._swap_size += 1

    def action_decrease(self, info, selected):
        if self._swap_size > SWAP_MIN_SIZE:
            self._swap_size -= 1

    def update_chart(self, jetson, name):
        parameter = jetson.memory['RAM']
        # Get max value if is present
        max_val = parameter.get("tot", 100)
        # Get value
        cached_val = parameter.get("cached", 0)
        buffer_val = parameter.get("buffers", 0)
        use_val = parameter.get("used", 0)
        cpu_val = parameter.get("used", 0) - parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start='k')
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
        used = size_to_string(self.jetson.memory['RAM']['used'], 'k')
        plot_name_info(self.stdscr, pos_y + 1, pos_x + 1, 'Used', used, spacing=3, color=NColors.cyan())
        shared = size_to_string(self.jetson.memory['RAM']['shared'], 'k')
        plot_name_info(self.stdscr, pos_y + 2, pos_x + 1, 'GPU Sh', shared, spacing=1, color=NColors.green())
        buffers = size_to_string(self.jetson.memory['RAM']['buffers'], 'k')
        plot_name_info(self.stdscr, pos_y + 3, pos_x + 1, 'Buffers', buffers, color=NColors.blue())
        cached = size_to_string(self.jetson.memory['RAM']['cached'], 'k')
        plot_name_info(self.stdscr, pos_y + 4, pos_x + 1, 'Cached', cached, spacing=1, color=NColors.yellow())
        free = size_to_string(self.jetson.memory['RAM']['free'], 'k')
        plot_name_info(self.stdscr, pos_y + 5, pos_x + 1, 'Free', free, spacing=3)
        total = size_to_string(self.jetson.memory['RAM']['tot'], 'k')
        plot_name_info(self.stdscr, pos_y + 6, pos_x + 1, 'TOT', total, spacing=4, color=curses.A_BOLD)

    def print_zram(self, stdscr, idx, swap, pos_y, pos_x, size_h, size_w):
        name, swap = swap
        # data gauge
        used = size_to_string(swap['used'], 'k')
        total = size_to_string(swap['size'], 'k')
        data = {
            'name': path.basename(name),
            'color': NColors.cyan(),
            'values': [(swap.get('used', 0) / swap.get('size', 0) * 100.0, NColors.cyan())],
            'mleft': "P{prio}".format(prio=swap['prio']),
            'mright': "{used}/{total}".format(used=used, total=total),
        }
        try:
            basic_gauge(stdscr, pos_y, pos_x, size_w - 2, data)
        except curses.error:
            pass

    def draw_swap_table(self, pos_y, pos_x, width, height, key, mouse):
        swap_info = self.jetson.memory['SWAP']
        used = size_to_string(swap_info['used'], 'k')
        total = size_to_string(swap_info['tot'], 'k')
        cached = size_to_string(swap_info['cached'], 'k')
        self.stdscr.addstr(pos_y, pos_x + 1, "SWAP", curses.A_BOLD)
        self.stdscr.addstr(pos_y, pos_x + 6, "{used}/{total} (Cached {cached})".format(used=used, total=total, cached=cached), NColors.red())
        # Print only zrams
        _, _, _, size_rows = cpu_grid(self.stdscr, self._zrams.items(), self.print_zram, pos_y + 1, pos_x + 1, size_width=width)
        # swap position
        pos_y_swap = pos_y + size_rows + 1
        # Detect line pressed
        line_pressed = self._mousePressed(mouse, pos_y_swap, pos_x, width, len(self._swaps) - 1)
        if line_pressed is not None:
            self._swap_pressed = line_pressed
        # Draw swap table
        for idx, (name, swap) in enumerate(self._swaps.items()):
            if pos_y_swap + idx < height:
                # Color gauge
                # Change color for type partition
                if swap['type'] == 'partition':
                    color = NColors.magenta() if self._swap_pressed != idx else NColors.imagenta()
                elif swap['type'] == 'file':
                    color = NColors.yellow() if self._swap_pressed != idx else NColors.iyellow()
                else:
                    color = NColors.green() if self._swap_pressed != idx else NColors.igreen()
                # data gauge
                used = size_to_string(swap['used'], 'k')
                total = size_to_string(swap['size'], 'k')
                data = {
                    'name': path.basename(name),
                    'color': color,
                    'values': [(swap.get('used', 0) / swap.get('size', 0) * 100.0, color)],
                    'mleft': "P{prio}".format(prio=swap['prio']),
                    'mright': "{used}/{total}".format(used=used, total=total),
                }
                width_swap = width - 8 if swap['boot'] else width - 3
                basic_gauge(self.stdscr, pos_y_swap + idx, pos_x + 1, width_swap, data)
                if swap['boot']:
                    color_boot = curses.A_BOLD if self._swap_pressed != idx else curses.A_REVERSE | curses.A_BOLD
                    self.stdscr.addstr(pos_y_swap + idx, pos_x + width_swap + 3, "Boot", color_boot)
            else:
                for n_arrow in range(width):
                    self.stdscr.addch(height, pos_x + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
                break

    def draw_swap_controller(self, pos_y, pos_x, key, mouse):
        string_name = ''
        color = curses.A_REVERSE
        # Read swap name
        if self._swap_pressed != -1:
            operation = ''
            # Read name swap
            name = list(self._swaps)[self._swap_pressed]
            # Get info swap
            swap = self._swaps[name]
            if swap['type'] == 'partition':
                color = NColors.imagenta()
            elif swap['type'] == 'file':
                color = NColors.iyellow()
                operation = 'Disable '
            else:
                color = NColors.icyan()
            # Swap name and operation
            string_name = "{operation}{name}".format(operation=operation, name=name)
        # Swap controller button
        try:
            label = string_name if string_name else 'Select swap'
            self._button_swap.update(pos_y, pos_x, label, key, mouse, color=color)
        except curses.error:
            pass
        # Button create new swap
        try:
            self._button_create.update(pos_y + 2, pos_x, key=key, mouse=mouse)
            self._button_boot.update(pos_y + 3, pos_x, key=key, mouse=mouse)
        except curses.error:
            pass
        # Draw selected number
        try:
            if self._swap_size > self._swap_old_size:
                color = NColors.green()
            elif self._swap_size < self._swap_old_size:
                color = NColors.yellow()
            else:
                color = curses.A_NORMAL
            self.stdscr.addstr(pos_y + 4, pos_x + 5, "{size: <2}".format(size=self._swap_size), color)
            self.stdscr.addstr(pos_y + 4, pos_x + 8, "GB", curses.A_BOLD)
        except curses.error:
            pass
        # Draw buttons
        try:
            self._button_decrease.update(pos_y + 4, pos_x, key=key, mouse=mouse)
            self._button_increase.update(pos_y + 4, pos_x + 11, key=key, mouse=mouse)
        except curses.error:
            pass
        # Draw swap name
        self._swap_name = self.get_new_swap_name()
        try:
            self.stdscr.addstr(pos_y + 5, pos_x, "New: ")
            self.stdscr.addstr(self._swap_name, NColors.yellow())
        except curses.error:
            pass

    def draw(self, key, mouse):
        swap_info = self.jetson.memory['SWAP']
        swap_table = swap_info['table']
        # Remove all zram
        self._zrams = {}
        self._swaps = {}
        for (name, swap) in swap_table.items():
            if swap['type'] == 'zram':
                self._zrams[name] = swap
            else:
                self._swaps[name] = swap
        # Screen size
        height, width, first = self.size_page()
        # Set size chart memory
        size_x = [1, width - 18]
        size_y = [first + 1, height // 2 - 2]
        # Draw the GPU chart
        # lfb label
        mem_data = self.jetson.memory['RAM']
        used = size_to_string(mem_data['used'], 'k')
        total = size_to_string(mem_data['tot'], 'k')
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
            iram_gauge(self.stdscr, first + height // 2 - 1 + line_counter, 1, width - 22, self.jetson.memory['IRAM'])
            line_counter += 1
        # Draw buttons
        self._button_cache.update(first + height // 2, width - 20, key=key, mouse=mouse)
        self.draw_swap_controller(first + height // 2 + 2, width - 20, key, mouse)
        # Draw swap list
        self.draw_swap_table(first + height // 2 - 1 + line_counter, 0, width - 22, height - 2, key, mouse)

    def get_new_swap_name(self):
        # Get default name
        swap_name = self.jetson.memory.swap_path()
        base_name = swap_name
        counter = 0
        # Get table
        swap_info = self.jetson.memory['SWAP']
        swap_table = swap_info['table']
        while swap_name in swap_table:
            swap_name = "{name}_{counter}".format(name=base_name, counter=counter)
            counter += 1
        return swap_name

    def _mousePressed(self, mouse, pos_y, pos_x, width, height):
        line_pressed = None
        if mouse:
            mx, my = mouse
            line_pressed = -1
            if my >= pos_y and my <= pos_y + height and \
               mx >= pos_x and mx <= pos_x + width:
                line_pressed = my - pos_y
        return line_pressed
# EOF
