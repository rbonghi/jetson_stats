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

import copy
import curses
from curses.textpad import rectangle
# Page class definition
from .jtopgui import Page
from .lib.chart import Chart
from .lib.common import (check_curses,
                         label_freq)


def cpu_grid(list_cpu, print_cpu, start_y, start_x, size_height=0, size_width=0):
    num_cpu = len(list_cpu)
    size_columns = 4
    # Measure size rows and columns
    size_rows = int(num_cpu / size_columns) + bool((num_cpu / size_columns) % 1)
    size_columns = int(num_cpu / size_rows) + bool((num_cpu / size_rows) % 1)
    # Measure step height and width
    step_height = round(size_height / size_rows) if size_height > 0 else 1
    step_width = round(size_width / size_columns) if size_width > 0 else 1
    # Build Grid
    idx_row = 0
    idx_column = 0
    for idx, cpu in enumerate(list_cpu):
        # Check row index
        if idx_row >= size_rows:
            idx_row = 0
            idx_column += 1
        # Get CPU in grid
        print_cpu(idx, cpu, start_y + idx_row * step_height, start_x + idx_column * step_width, step_height - 1, step_width - 1)
        idx_row += 1
    # return matrix
    return step_height, step_width, size_columns, size_rows


class CPU(Page):

    def __init__(self, stdscr, jetson):
        super(CPU, self).__init__("CPU", stdscr, jetson)
        # List all chart CPU
        size_cpu = len(jetson.cpu['cpu'])
        self._chart_cpus = [Chart(jetson, str(idx), self.update_chart, color_text=curses.COLOR_BLUE) for idx in range(size_cpu)]

    def update_chart(self, jetson, name):
        return {}

    def print_cpu(self, idx, cpu, pos_y, pos_x, size_h, size_w):
        # string = f"({idx}) y{pos_y} x{pos_x}|H{size_h} W{size_w}"
        # self.stdscr.addstr(pos_y, pos_x, string, curses.A_NORMAL)
        self.stdscr.addstr(pos_y, pos_x, str(idx), curses.A_BOLD)

        label_chart_cpu = "{percent: >3d}%".format(percent=cpu.get('val', 0))
        # Print chart
        chart = self._chart_cpus[idx]
        chart.draw(self.stdscr, [pos_x, pos_x + size_w], [pos_y, pos_y + size_h - 2], label=label_chart_cpu, y_label=False)
        # Print info
        self.stdscr.addstr(pos_y + size_h - 1, pos_x, "First", curses.A_NORMAL)
        self.stdscr.addstr(pos_y + size_h, pos_x, "Second", curses.A_NORMAL)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Print gauge all CPU
        self.stdscr.addstr(first + 1, 1, "CPU ALL STATUS", curses.A_BOLD)
        # Print all GRID CPU
        step_height, step_width, size_columns, size_rows = cpu_grid(
            self.jetson.cpu['cpu'], self.print_cpu, first + 2, 1, size_height=height - 4, size_width=width - 8)
        # Print CPU Y axis
        chart = self._chart_cpus[0]
        for i in range(size_rows):
            chart.draw_y_axis(self.stdscr, first + 2 + i * step_height, 1 + step_width * size_columns, step_height - 3)


class CPU_OLD(Page):

    def __init__(self, stdscr, jetson):
        super(CPU_OLD, self).__init__("CPU", stdscr, jetson)
        # List all CPU
        self.chart_cpus = []
        for name, value in enumerate(self.jetson.cpu['cpu']):
            chart = Chart(jetson, "CPU{name}".format(name=name), self.update_chart, color_text=curses.COLOR_BLUE)
            self.chart_cpus += [chart]

    def update_chart(self, jetson, name):
        cpu = jetson.cpu['cpu'][int(name[3:])]
        status = True if cpu else False
        return {
            'value': [cpu.get("val", 0)],
            'active': status
        }

    @check_curses
    def draw(self, key, mouse):
        """
            Draw a plot with GPU payload
        """
        n_cpu = sum([1 if cpu else 0 for _, cpu in self.jetson.cpu.items()])
        # Screen size
        height, width, first = self.size_page()
        # Make all CPU charts
        counter = 0
        x_offset = width // 4
        # Draw info rectangle
        rectangle(self.stdscr, first + 1, 0, height - 2 + first, first + x_offset)
        # Draw title side area
        self.stdscr.addstr(first + 1, 1, " Platform ", curses.A_BOLD)
        # Architecture CPU cores
        # architecture = self.jetson.architecture
        offset_table = 2
        for idx, name in enumerate(self.jetson.cpu):
            cpu = self.jetson.cpu[name]
            status = 'ON' if cpu else 'OFF'
            active = True if cpu else False
            frq = label_freq(cpu['frq'], start='k') if 'frq' in cpu else ''
            # Load model architecture
            model = cpu['model'].split()[0] if 'model' in cpu else ''
            model = model[:x_offset - (first + 3) - 4]
            governor = cpu.get('governor', '').capitalize()
            # governor = governor[:x_size + add_size - 12]
            # Draw info
            color = curses.color_pair(8) if active else curses.color_pair(7)
            name = "CPU{name}".format(name=name)
            try:
                self.stdscr.addstr(first + offset_table + idx * 2, 2, name, color)
                if active:
                    self.stdscr.addstr(first + offset_table + idx * 2, 3 + len(name), governor, curses.color_pair(3) | curses.A_BOLD)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 2, model, curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 3 + len(model), "Frq:", curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 7 + len(model), "{}".format(frq), curses.A_BOLD)
                else:
                    self.stdscr.addstr(first + offset_table + idx * 2, 2 + len(name) + 1, status, curses.A_NORMAL)
            except curses.error:
                pass
            # Add alert ARROW Down
            if first + offset_table + idx * 2 > height - 4:
                for n_arrow in range(x_offset - 1):
                    self.stdscr.addch(first + height - 2, 1 + n_arrow, curses.ACS_DARROW, curses.A_REVERSE | curses.A_BOLD)
        # Evaluate size single chart
        x_size = (width - x_offset - 6) // (n_cpu // 2)
        y_size = (height - 2 - first) // 2
        # Measure offset label
        offest_label = width - (2 + x_offset + x_size * (n_cpu // 2))
        # Plot all CPUs
        idx_n = 0
        for chart, name in zip(self.chart_cpus, sorted(self.jetson.cpu)):
            data = copy.deepcopy(self.jetson.cpu[name])
            # status CPU
            status = True if data else False
            if not status:
                continue
            y_label = idx_n % (n_cpu // 2) == (n_cpu // 2) - 1
            # Select line
            line = 1 if idx_n >= n_cpu // 2 else 0
            # Increase counter
            counter = idx_n - line * (n_cpu // 2)
            # Evaluate size chart
            add_size = offest_label if y_label else 0
            size_x = [x_offset + 2 + (counter * (x_size)), x_offset + x_size * (1 + counter) + add_size]
            size_y = [first + 1 + (line * (y_size)), first + y_size * (1 + line)]
            # Value and frequency
            if status:
                label_chart_cpu = "{percent: >3d}%".format(percent=data.get('val', 0))
                chart.draw(self.stdscr, size_x, size_y, label=label_chart_cpu, y_label=y_label)
            idx_n += 1
# EOF
