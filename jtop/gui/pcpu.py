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
from .lib.common import value_to_string
from .lib.linear_gauge import linear_frequency_gauge


def basic_gauge(stdscr, pos_y, pos_x, size_w, data, bar='|'):
    """_summary_

        data = {
            'name': name value
            'color': color test
            'values': [(value, color), (value, color), ... ] sum of values = 100
            'mleft': message on left
            'mright': message on right otherwise a percentage
        }
    """
    # Evaluate size without short name
    name = data['name'] if 'name' in data else ''
    name_size = len(name) + 1 if 'name' in data else 0
    size_bar = size_w - name_size - 1
    # Show short name linear gauge
    name_color = data['color'] if 'color' in data else curses.A_NORMAL
    stdscr.addstr(pos_y, pos_x, name, name_color)
    # Draw gauge
    online = data['online'] if 'online' in data else True
    if online:
        values = data['values']if 'name' in data else []
        # Draw gauge border
        stdscr.addstr(pos_y, pos_x + name_size, "[" + " " * size_bar + "]", curses.A_BOLD)
        # size dynamic bar
        total = sum([value for value, _ in values])
        n_bar = total * size_bar // 100
        # Draw bar
        str_progress_bar = bar * n_bar + " " * (size_bar - n_bar)
        # Add label right otherwise write a percent
        label_right = data['mright'] if 'mright' in data else "{:.0f}%".format(total)
        str_progress_bar = str_progress_bar[:size_bar - len(label_right)] + label_right
        # Add message on left
        if 'mleft' in data:
            str_progress_bar = data['mleft'] + str_progress_bar[len(data['mleft']):]
        # Draw all values
        x_bar_start = 0
        old_val = 0
        for value, color in values:
            x_bar_end = ((old_val + value) * size_bar) // 100
            stdscr.addstr(pos_y, pos_x + name_size + x_bar_start + 1, str_progress_bar[x_bar_start:x_bar_end], color)
            x_bar_start = x_bar_end
            old_val += value
        # Draw grey part or message
        grey_part = str_progress_bar[n_bar:]
        stdscr.addstr(pos_y, pos_x + name_size + x_bar_start + 1, grey_part, curses.A_DIM)
    else:
        # Draw offline gauge
        stdscr.addstr(pos_y, pos_x + name_size + 1, ("[{value:>" + str(size_bar) + "}]").format(value=" "), curses.color_pair(7))
        # Show message status
        stdscr.addstr(pos_y, pos_x + name_size + 4, "OFF", curses.color_pair(7))


def cpu_grid(stdscr, list_cpu, print_cpu, start_y, start_x, size_height=0, size_width=0):
    num_cpu = len(list_cpu)
    size_columns = 4
    # Measure size rows and columns
    size_rows = int(num_cpu / size_columns) + bool((num_cpu / size_columns) % 1)
    size_columns = int(num_cpu / size_rows) + bool((num_cpu / size_rows) % 1)
    # Measure step height and width
    step_height = round(size_height / size_rows) if size_height > 0 else 1
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
        print_cpu(stdscr, idx, cpu, start_y + idx_row * step_height, start_x + idx_column * step_width, step_height - 1, step_width - 1)
        idx_row += 1
    # return matrix
    return step_height, step_width, size_columns, size_rows


def cpu_gauge(stdscr, idx, cpu, pos_y, pos_x, _, size_w):
    # Draw gauge
    data = {
        'name': str(idx) + (" " if idx <= 9 else ""),
        'color': curses.color_pair(6) | curses.A_BOLD,
        'online': cpu['online'],
        'values': [
            (int(cpu['user']), curses.color_pair(1)),
            (int(cpu['nice']), curses.color_pair(2)),
            (int(cpu['system']), curses.color_pair(3)),
        ],
    }
    if size_w < 16:
        basic_gauge(stdscr, pos_y, pos_x, size_w - 1, data)
    else:
        # Draw gauge
        basic_gauge(stdscr, pos_y, pos_x, size_w - 8, data)
        # Draw current frequency
        curr_string = value_to_string(cpu['freq']['cur'], cpu['freq']['unit'])
        stdscr.addstr(pos_y, pos_x + size_w - 6, curr_string, curses.A_NORMAL)


def compact_cpus(stdscr, pos_y, width, jetson):
    _, _, _, size_rows = cpu_grid(stdscr, jetson.cpu['cpu'], cpu_gauge, pos_y, 1, size_width=width - 2)
    return size_rows


class CPU(Page):

    def __init__(self, stdscr, jetson):
        super(CPU, self).__init__("CPU", stdscr, jetson)
        # List all chart CPU
        size_cpu = len(jetson.cpu['cpu'])
        self._chart_cpus = [Chart(jetson, str(idx + 1), self.update_chart, color_text=curses.COLOR_BLUE) for idx in range(size_cpu)]

    def update_chart(self, jetson, name):
        cpu = jetson.cpu['cpu'][int(name) - 1]
        return {
            'value': [100 - cpu.get("idle", 0)],
        }

    def print_cpu(self, stdscr, idx, cpu, pos_y, pos_x, size_h, size_w):
        # Print status CPU
        governor = cpu.get('governor', '').capitalize()
        label_chart_cpu = "{percent: >3.0f}% {governor}".format(percent=100 - cpu.get('idle', 0), governor=governor)
        # Print chart
        chart = self._chart_cpus[idx]
        chart.draw(stdscr, [pos_x, pos_x + size_w], [pos_y, pos_y + size_h - 2], label=label_chart_cpu, y_label=False)
        # Print model
        model = cpu['model'] if 'model' in cpu else ''
        model = model[:size_w]
        stdscr.addstr(pos_y + size_h - 1, pos_x, model, curses.A_NORMAL)
        # Print info
        freq = cpu['freq']
        freq['online'] = cpu['online']
        linear_frequency_gauge(stdscr, pos_y + size_h, pos_x, size_w, "Frq", cpu['freq'])

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Print gauge all CPU
        self.stdscr.addstr(first + 1, 1, "CPU ALL STATUS", curses.A_BOLD)
        # Print all GRID CPU
        step_height, step_width, size_columns, size_rows = cpu_grid(
            self.stdscr, self.jetson.cpu['cpu'], self.print_cpu, first + 2, 1, size_height=height - 4, size_width=width - 8)
        # Print CPU Y axis
        chart = self._chart_cpus[0]
        for i in range(size_rows):
            chart.draw_y_axis(self.stdscr, first + 2 + i * step_height, 1 + step_width * size_columns, step_height - 3)
# EOF
