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

import curses
from .jtopgui import Page
# Graphics elements
from .lib.common import (plot_name_info,
                         label_freq,
                         jetson_clocks_gui,
                         nvp_model_gui)
from .lib.linear_gauge import linear_gauge, GaugeName
from .lib.chart import Chart


class GPU(Page):

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        # Initialize GPU chart
        self.chart_gpu = Chart(jetson, "GPU", self.update_chart, color=curses.color_pair(2), color_chart=[curses.color_pair(8)])

    def update_chart(self, jetson, name):
        # Get max value if is present
        max_val = jetson.gpu.get("max_val", 100)
        # Get unit
        unit = jetson.gpu.get("unit", "%")
        # Append in list
        return {
            'value': [jetson.gpu.get("val", 0)],
            'max': max_val,
            'unit': unit,
        }

    def draw(self, key, mouse):
        """
            Draw a plot with GPU payload
        """
        # Screen size
        height, width, first = self.size_page()
        # Evaluate size chart
        size_x = [1, width - 2]
        size_y = [first + 1, height * 2 // 3]
        # Draw the GPU chart
        frq = label_freq(self.jetson.gpu['frq'], start='k')
        label_chart_gpu = "{percent: >2}%".format(percent=self.jetson.gpu['val'])
        if frq:
            label_chart_gpu += " - {frq}".format(frq=frq)
        self.chart_gpu.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)
        # Percent Gauge GPU
        linear_gauge(self.stdscr, offset=first + height * 2 // 3 + 1, start=1, size=width // 2,
                     name=GaugeName('GPU', color=curses.color_pair(6)),
                     value=self.jetson.gpu.get('val', 0),
                     label=label_freq(self.jetson.gpu['frq'], start='k'))
        # Temperature GPU
        if 'GPU' in self.jetson.temperature:
            temp_gpu = self.jetson.temperature['GPU']
            plot_name_info(self.stdscr, first + height * 2 // 3 + 1, width // 2 + 4, "GPU Temp", str(temp_gpu) + "C")
        # Jetson clocks status
        jetson_clocks_gui(self.stdscr, first + height * 2 // 3 + 3, 1, self.jetson)
        # NVP Model
        if self.jetson.nvpmodel is not None:
            nvp_model_gui(self.stdscr, first + height * 2 // 3 + 4, 1, self.jetson)
