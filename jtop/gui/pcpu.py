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
from curses.textpad import Textbox, rectangle
import platform
# Page class definition
from .jtopgui import Page
from .chart import Chart

class CPU(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(CPU, self).__init__("CPU", stdscr, jetson, refresh)
        # List all CPU
        self.chart_cpus = []
        for idx, cpu in enumerate(self.jetson.stats["CPU"]):
            self.chart_cpus += [Chart(jetson, "CPU {idx}".format(idx=idx + 1), refresh, self.update_chart, color=curses.color_pair(4), color_chart=curses.color_pair(10))]

    def update_chart(self, jetson, name):
        n = int(name.split(" ")[1]) - 1
        cpu = jetson.stats["CPU"][n]
        return {
            'value': cpu.get("val", 0),
        }

    def draw(self, key):
        """
            Draw a plot with GPU payload
        """
        ncpu = len(self.chart_cpus)
        # Screen size
        height, width, first = self.size_page()
        # Make all CPU charts
        counter = 0
        x_offset = width // 4
        # Draw info rectangle
        rectangle(self.stdscr, first + 1, 0, height - 2, first + x_offset)

        self.stdscr.addstr(first + 2, 2, "Platform", curses.A_NORMAL)
        # Architecture CPU cores
        for idx, model in enumerate(self.jetson.architecture):
            number = self.jetson.architecture[model]
            model = model.split(" ")[0]
            self.stdscr.addstr(first + 3 + idx, 2, "{n}: {model}".format(n=number, model=model), curses.A_NORMAL)
        # Evaluate size single chart
        x_size = (width - x_offset -  6 * (ncpu // 2) ) // (ncpu // 2)
        y_size = (height - 4) // 2
        # Plot all CPUs
        for idx, cpu in enumerate(self.chart_cpus):
            # Select line
            line = 1 if idx >= ncpu // 2 else 0
            # Incrase counter
            counter = idx - line * (ncpu // 2)
            # Evaluate size chart    
            size_x = [x_offset + 2 + (counter * (x_size + 6)), x_offset + x_size + (counter * (x_size + 6))]
            size_y = [first + 1 + (line * (y_size + 1)), y_size + (line * (y_size + 1))]
            # Draw chart
            cpu.draw(self.stdscr, size_x, size_y)

# EOF
