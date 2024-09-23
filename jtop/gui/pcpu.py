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
# Page class definition
from .jtopgui import Page
from .lib.chart import Chart
from .lib.colors import NColors
from .lib.common import unit_to_string
from .lib.linear_gauge import freq_gauge, basic_gauge


def cpu_gauge(stdscr, idx, cpu, pos_y, pos_x, _, size_w):
    # online status
    online = cpu['online'] if 'online' in cpu else True
    # name cpu - workararound for TOTAL cpu
    name = cpu['name'] if 'name' in cpu else str(idx + 1) + (" " if idx < 9 else "")
    # Plot values
    values = [
        (cpu['user'], NColors.green()),
        (cpu['nice'], NColors.yellow()),
        (cpu['system'], NColors.red()),
    ] if online else []
    # Draw gauge
    data = {
        'name': name,
        'color': NColors.cyan(),
        'online': online,
        'values': values,
        # 'mleft': cpu.get('governor', '').capitalize(),
    }
    if size_w < 16:
        basic_gauge(stdscr, pos_y, pos_x, size_w - 1, data)
        return
    elif 'freq' in cpu:
        # Draw current frequency
        curr_string = unit_to_string(cpu['freq']['cur'], 'k', 'Hz')
        stdscr.addstr(pos_y, pos_x + size_w - 6, curr_string, NColors.italic())
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size_w - 8, data)


def cpu_grid(stdscr, list_cpu, print_cpu, start_y, start_x, size_height=0, size_width=0):
    num_cpu = len(list_cpu)
    if num_cpu == 0:
        return size_height, size_width, 0, 0
    size_columns = 4 if num_cpu > 6 else 2
    # Measure size rows and columns
    size_rows = int(num_cpu / size_columns) + bool((num_cpu / size_columns) % 1)
    size_columns = int(num_cpu / size_rows) + bool((num_cpu / size_rows) % 1)
    # Measure step height and width
    step_height = int(round(size_height / size_rows)) if size_height > 0 else 1
    step_width = int(size_width / size_columns) if size_width > 0 else 1
    # Build Grid
    idx_row = 0
    idx_column = 0
    for idx, cpu in enumerate(list_cpu):
        # Check row index
        if idx_row >= size_rows:
            idx_row = 0
            idx_column += 1
        # Get CPU in grid
        try:
            print_cpu(stdscr, idx, cpu, start_y + idx_row * step_height, start_x + idx_column * step_width, step_height - 1, step_width - 1)
        except curses.error:
            pass
        idx_row += 1
    # return matrix
    return step_height, step_width, size_columns, size_rows


def compact_cpus(stdscr, pos_y, pos_x, width, jetson):
    _, _, _, size_rows = cpu_grid(stdscr, jetson.cpu['cpu'], cpu_gauge, pos_y, pos_x + 1, size_width=width - 2)
    return size_rows


class CPU(Page):

    def __init__(self, stdscr, jetson):
        super(CPU, self).__init__("CPU", stdscr, jetson)
        # List all chart CPU
        size_cpu = len(jetson.cpu['cpu'])
        self._chart_cpus = [Chart(jetson, str(idx + 1), self.update_chart, color_text=curses.COLOR_BLUE,
                                  color_chart=[curses.COLOR_BLUE]) for idx in range(size_cpu)]

    def update_chart(self, jetson, name):
        cpu = jetson.cpu['cpu'][int(name) - 1]
        return {
            'active': cpu['online'],
            'value': [100 - cpu.get("idle", 100)],
        }

    def print_cpu(self, stdscr, idx, cpu, pos_y, pos_x, size_h, size_w):
        # Print status CPU
        governor = cpu.get('governor', '').capitalize()
        label_chart_cpu = "{percent: >3.0f}% {governor}".format(percent=100 - cpu.get('idle', 100), governor=governor)
        # Print chart
        chart = self._chart_cpus[idx]
        chart.draw(stdscr, [pos_x, pos_x + size_w], [pos_y, pos_y + size_h - 2], label=label_chart_cpu, y_label=False)
        # Print model
        model = cpu['model'] if 'model' in cpu else ''
        model = model[:size_w]
        try:
            stdscr.addstr(pos_y + size_h - 1, pos_x, model, curses.A_NORMAL)
        except curses.error:
            pass
        # Print info
        if 'freq' in cpu:
            freq = cpu['freq']
            freq['online'] = cpu['online']
            freq['name'] = "Frq"
            try:
                freq_gauge(stdscr, pos_y + size_h, pos_x, size_w, cpu['freq'])
            except curses.error:
                pass

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Print gauge all CPU
        total = self.jetson.cpu['total']
        total['name'] = 'ALL'
        cpu_gauge(self.stdscr, 0, total, first + 1, 1, '', width)
        # Print all GRID CPU
        step_height, step_width, size_columns, size_rows = cpu_grid(
            self.stdscr, self.jetson.cpu['cpu'], self.print_cpu, first + 2, 1, size_height=height - 4, size_width=width - 8)
        # Print CPU Y axis
        chart = self._chart_cpus[0]
        for i in range(size_rows):
            chart.draw_y_axis(self.stdscr, first + 2 + i * step_height, 1 + step_width * size_columns, step_height - 3)
# EOF
