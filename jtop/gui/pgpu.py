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
from .lib.common import (plot_name_info,
                         label_freq,
                         jetson_clocks_gui,
                         nvp_model_gui)
from .lib.chart import Chart


class GPU(Page):

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        # Initialize GPU chart
        self.chart_gpus = []
        for name in sorted(self.jetson.gpu):
            chart = Chart(jetson, "GPU{name}".format(name=name), self.update_chart, color_text=curses.COLOR_GREEN)
            self.chart_gpus += [chart]

    def update_chart(self, jetson, name):
        gpu = jetson.gpu[int(name[3:])]
        # Get max value if is present
        max_val = gpu.get("max_val", 100)
        # Get unit
        unit = gpu.get("unit", "%")
        # Append in list
        return {
            'value': [gpu.get("val", 0)],
            'max': max_val,
            'unit': unit,
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
