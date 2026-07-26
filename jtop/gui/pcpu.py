# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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
from math import ceil
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


CPU_TILE_MIN_HEIGHT = 7
CPU_TILE_MIN_WIDTH = 20
CPU_TILE_TARGET_RATIO = 3.5


def cpu_grid_columns(num_cpu, size_height, size_width):
    """Choose a grid that follows the terminal aspect ratio.

    The old fixed four-column layout works well in a tall terminal, but makes
    each CPU chart too short in a wide, shallow SSH terminal. Prefer layouts
    whose cells are close to the proportions of the normal CPU chart while
    preserving enough rows and columns for its labels and frequency gauge.
    """
    if num_cpu <= 0:
        return 0
    if size_height <= 0 or size_width <= 0:
        return 4 if num_cpu > 6 else 2

    layouts = []
    fallback = []
    for columns in range(1, num_cpu + 1):
        rows = int(ceil(float(num_cpu) / columns))
        step_height = max(1, size_height // rows)
        step_width = max(1, size_width // columns)
        empty_slots = rows * columns - num_cpu
        ratio_error = abs((float(step_width) / step_height) - CPU_TILE_TARGET_RATIO)
        candidate = (ratio_error, empty_slots, columns)

        if step_height >= CPU_TILE_MIN_HEIGHT and step_width >= CPU_TILE_MIN_WIDTH:
            layouts.append(candidate)

        height_deficit = max(0, CPU_TILE_MIN_HEIGHT - step_height)
        width_deficit = max(0, CPU_TILE_MIN_WIDTH - step_width)
        fallback.append((height_deficit + width_deficit, ratio_error, empty_slots, columns))

    if layouts:
        return min(layouts)[2]
    return min(fallback)[3]


def cpu_grid(stdscr, list_cpu, print_cpu, start_y, start_x, size_height=0,
             size_width=0, size_columns=None):
    num_cpu = len(list_cpu)
    if num_cpu == 0:
        return size_height, size_width, 0, 0
    if size_columns is None:
        # Keep the historical layout for compact_cpus() and other callers.
        size_columns = 4 if num_cpu > 6 else 2
        size_rows = int(ceil(float(num_cpu) / size_columns))
        size_columns = int(ceil(float(num_cpu) / size_rows))
    else:
        size_columns = max(1, min(size_columns, num_cpu))
        size_rows = int(ceil(float(num_cpu) / size_columns))
    # Measure size rows and columns
    # Measure step height and width. Floor division guarantees the final row
    # stays above the page footer; round() could make the grid one row too tall.
    step_height = max(1, size_height // size_rows) if size_height > 0 else 1
    step_width = max(1, size_width // size_columns) if size_width > 0 else 1
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
        # Slot layout (pos_y + size_h is the blank separator, never drawn into):
        #   pos_y … row_chart-1  chart body (amplitude history)
        #   row_chart            time axis   (L -6s  L -4s  L -2s  0)
        #   row_freq             freq gauge
        row_chart = pos_y + size_h - 2
        row_freq  = pos_y + size_h - 1
        governor = cpu.get('governor', '').capitalize()
        label_chart_cpu = "{percent: >3.0f}% {governor}".format(percent=100 - cpu.get('idle', 100), governor=governor)
        chart = self._chart_cpus[idx]
        chart.draw(stdscr, [pos_x, pos_x + size_w], [pos_y, row_chart], label=label_chart_cpu, y_label=False)
        if 'freq' in cpu:
            freq = cpu['freq']
            freq['online'] = cpu['online']
            freq['name'] = "Frq"
            try:
                freq_gauge(stdscr, row_freq, pos_x, size_w, cpu['freq'])
            except curses.error:
                pass

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Print gauge all CPU
        total = self.jetson.cpu['total']
        total['name'] = 'ALL'
        cpu_gauge(self.stdscr, 0, total, first + 1, 1, '', width)
        # Print all GRID CPU. Select the column count from the current terminal
        # dimensions so a wide, shallow SSH window uses more columns and fewer
        # rows instead of collapsing each chart vertically.
        grid_height = max(1, height - 4)
        grid_width = max(1, width - 8)
        size_columns = cpu_grid_columns(len(self.jetson.cpu['cpu']), grid_height, grid_width)
        step_height, step_width, size_columns, size_rows = cpu_grid(
            self.stdscr, self.jetson.cpu['cpu'], self.print_cpu, first + 2, 1,
            size_height=grid_height, size_width=grid_width, size_columns=size_columns)
        # Print CPU Y axis. The uploaded Thor layout ends the chart at
        # pos_y + step_height - 3, so the shared Y axis must use the same end.
        if step_height >= 5:
            chart = self._chart_cpus[0]
            for i in range(size_rows):
                chart.draw_y_axis(
                    self.stdscr,
                    first + 2 + i * step_height,
                    1 + step_width * size_columns,
                    step_height - 3)
# EOF
