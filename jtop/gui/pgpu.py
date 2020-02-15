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
from .jtopguilib import (plot_name_info,
                         linear_gauge,
                         label_freq,
                         Chart)


class GPU(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(GPU, self).__init__("GPU", stdscr, jetson, refresh)
        if 'GR3D' in jetson.stats:
            # Initialize GPU chart
            self.chart_gpu = Chart("GR3D", refresh, color=curses.color_pair(2))
            # Attach the chart for every update from jtop
            jetson.attach(self.chart_gpu)

    def draw(self, key):
        """
            Draw a plot with GPU payload
        """
        # Screen size
        max_y, max_x = self.stdscr.getmaxyx()
        # Evaluate size chart
        size_x = [2, max_x - 10]
        size_y = [1, max_y * 2 // 3]
        # Draw the GPU chart
        if 'GR3D' in self.jetson.stats:
            frq = label_freq(self.jetson.stats['GR3D'])
            label_chart_gpu = "{percent: >2}%".format(percent=self.jetson.stats['GR3D']['val'])
            if frq:
                label_chart_gpu += " - {frq}".format(frq=frq)
            self.chart_gpu.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)
        # Percent Gauge GPU
        gpu = self.jetson.stats.get('GR3D', {})
        linear_gauge(self.stdscr, offset=max_y * 2 // 3 + 1, start=2, size=max_x // 2,
                     name='GPU',
                     value=gpu.get('val', 0),
                     label=label_freq(gpu),
                     status='ON' if gpu else 'REQUIRE SUDO',
                     color=curses.color_pair(6))
        # Temperature GPU
        if "GPU" in self.jetson.stats['TEMP']:
            temp_gpu = self.jetson.stats['TEMP']['GPU']
            plot_name_info(self.stdscr, max_y * 2 // 3 + 1, max_x // 2 + 4, "GPU Temp", str(temp_gpu) + "C")
        # Jetson clocks status
        jc = self.jetson.jetson_clocks
        if jc is not None:
            jc_status = jc.status
            if jc_status == "active":
                color = curses.color_pair(2)  # Running (Green)
            elif jc_status == "inactive":
                color = curses.A_NORMAL       # Normal (Grey)
            elif "ing" in jc_status:
                color = curses.color_pair(3)  # Warning (Yellow)
            else:
                color = curses.color_pair(1)  # Error (Red)
            # Show if JetsonClock is enabled or not
            if jc.enable:
                jc_status = "[" + jc_status + "]"
            plot_name_info(self.stdscr, max_y * 2 // 3 + 2, 2, "Jetson Clocks", jc_status, color)
        # NVP Model
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            plot_name_info(self.stdscr, max_y * 2 // 3 + 3, 2, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
