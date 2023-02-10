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
from curses.textpad import rectangle
from .jtopgui import Page
# Graphics elements
from .lib.common import NColors
from .lib.common import (plot_name_info,
                         label_freq,
                         jetson_clocks_gui,
                         nvp_model_gui,
                         size_min)
from .lib.chart import Chart
from .lib.common import unit_to_string
from .lib.linear_gauge import basic_gauge


def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data['status']
    # Data gauge
    data = {
        'name': 'GPU' if idx == 0 else 'GPU{idx}'.format(idx=idx),
        'color': NColors.green() | curses.A_BOLD,
        'values': [(gpu_status['load'], NColors.igreen())],
    }
    if 'freq' in gpu_data:
        # Draw current frequency
        curr_string = unit_to_string(gpu_data['freq']['cur'], gpu_data['freq']['unit'], 'Hz')
        stdscr.addstr(pos_y, pos_x + size - 7, curr_string, NColors.italic())
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 9, data, bar=" ")


def compact_gpu(stdscr, pos_y, pos_x, width, jetson):
    line_counter = 0
    # Status all GPUs
    if jetson.gpu['gpu']:
        for idx, gpu in enumerate(jetson.gpu['gpu']):
            gpu_gauge(stdscr, pos_y, pos_x, width, gpu, idx)
            line_counter += 1
    else:
        data = {
            'name': 'GPU',
            'color': NColors.green(),
            'online': False,
            'coffline': NColors.igreen(),
            'message': 'NOT AVAILABLE',
        }
        basic_gauge(stdscr, pos_y, pos_x, width - 2, data)
        line_counter = 1
    return line_counter


class GPU(Page):

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        # Initialize GPU chart
        self.chart_gpus = []
        for name in sorted(self.jetson.gpu):
            chart = Chart(jetson, "GPU{name}".format(name=name), self.update_chart, color_text=curses.COLOR_GREEN)
            self.chart_gpus += [chart]

    def update_chart(self, jetson, name):
        # gpu = jetson.gpu[int(name[3:])]
        # Get max value if is present
        # max_val = gpu.get("max_val", 100)
        # Get unit
        # unit = gpu.get("unit", "%")
        # Append in list
        return {
            #    'value': [gpu.get("val", 0)],
            #    'max': max_val,
            #    'unit': unit,
        }

    def draw(self, key, mouse):
        """
            Draw a plot with GPU payload
        """
        n_gpu = len(self.jetson.gpu)
        # Screen size
        height, width, first = self.size_page()
        # Evaluate size single chart
        x_size = (width - 2) // n_gpu
        # Plot all GPUS
        idx_n = 0
        for chart, name in zip(self.chart_gpus, sorted(self.jetson.gpu)):
            # Increase counter
            size_x = [1 + idx_n * (x_size), (1 + idx_n) * (1 + x_size) - 2]
            size_y = [first + 1, height * 2 // 3]
            # Value and frequency
            y_label = (idx_n) % n_gpu == n_gpu - 1
            frq = label_freq(self.jetson.gpu[name]['frq'], start='k')
            label_chart_gpu = "{percent: >2}%".format(percent=self.jetson.gpu[name]['val'])
            if frq:
                label_chart_gpu += " - {frq}".format(frq=frq)
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu, y_label=y_label)
            # Increase counter
            idx_n += 1
        # Temperature GPU
        if 'GPU' in self.jetson.temperature:
            temp_gpu = self.jetson.temperature['GPU']
            plot_name_info(self.stdscr, first + height * 2 // 3 + 2, 1, "GPU Temp", str(temp_gpu) + "C")
        # Jetson clocks status
        jetson_clocks_gui(self.stdscr, first + height * 2 // 3 + 4, 1, self.jetson)
        # NVP Model
        if self.jetson.nvpmodel is not None:
            nvp_model_gui(self.stdscr, first + height * 2 // 3 + 5, 1, self.jetson)

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
