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
                         label_freq)
from .lib.linear_gauge import linear_gauge, GaugeName
from .lib.chart import Chart
from ..core.jetson_clocks import JetsonClocks


class GPU(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(GPU, self).__init__("GPU", stdscr, jetson, refresh)
        # Initialize GPU chart
        self.chart_gpu = Chart(jetson, "GPU", refresh, self.update_chart, color=curses.color_pair(2), color_chart=[curses.color_pair(8)])

    def update_chart(self, jetson, name):
        parameter = jetson.stats.get("GR3D", {})
        # Get max value if is present
        max_val = parameter.get("max_val", 100)
        # Get unit
        unit = parameter.get("unit", "%")
        # Append in list
        return {
            'value': [parameter.get("val", 0)],
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
        if 'GR3D' in self.jetson.stats:
            frq = label_freq(self.jetson.stats['GR3D'])
            label_chart_gpu = "{percent: >2}%".format(percent=self.jetson.stats['GR3D']['val'])
            if frq:
                label_chart_gpu += " - {frq}".format(frq=frq)
            self.chart_gpu.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)
        # Percent Gauge GPU
        gpu = self.jetson.stats.get('GR3D', {})
        linear_gauge(self.stdscr, offset=first + height * 2 // 3 + 1, start=1, size=width // 2,
                     name=GaugeName('GPU', color=curses.color_pair(6)),
                     value=gpu.get('val', 0),
                     label=label_freq(gpu),
                     status='ON' if gpu else 'SUDO SUGGESTED')
        # Temperature GPU
        if "GPU" in self.jetson.stats['TEMP']:
            temp_gpu = self.jetson.stats['TEMP']['GPU']
            plot_name_info(self.stdscr, first + height * 2 // 3 + 1, width // 2 + 4, "GPU Temp", str(temp_gpu) + "C")
        # Jetson clocks status
        jc = self.jetson.jetson_clocks
        if jc is not None:
            try:
                jc_status = jc.status
                # Running (Green) or Normal (Grey)
                jc_color = curses.color_pair(2) if jc_status else curses.A_NORMAL
                # Write status jetson_clocks
                jc_status_name = "Running" if jc_status else "Stopped"
            except JetsonClocks.JCException:
                # Fix error color
                jc_color = curses.color_pair(11)
                jc_status_name = "SUDO SUGGESTED"
            # Status service
            jc_service = jc.service
            if jc_service == "active":
                color = curses.color_pair(2)  # Running (Green)
            elif jc_service == "inactive":
                color = curses.A_NORMAL       # Normal (Grey)
            elif "ing" in jc_service:
                color = curses.color_pair(3)  # Warning (Yellow)
            else:
                color = curses.color_pair(1)  # Error (Red)
            # Show if JetsonClock is enabled or not
            if jc.enable:
                jc_service = "[" + jc_service + "]"
            plot_name_info(self.stdscr, first + height * 2 // 3 + 2, 1, "Jetson Clocks", jc_status_name, jc_color)
            plot_name_info(self.stdscr, first + height * 2 // 3 + 3, 1, "Jetson Clocks Service", jc_service, color)
        # NVP Model
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            plot_name_info(self.stdscr, first + height * 2 // 3 + 4, 1, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
