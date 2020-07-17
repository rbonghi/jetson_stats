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

import copy
import curses
from curses.textpad import rectangle
import platform
# Page class definition
from .jtopgui import Page
from .lib.chart import Chart
from .lib.common import (check_curses,
                         plot_name_info,
                         label_freq)


class CPU(Page):

    def __init__(self, stdscr, jetson):
        super(CPU, self).__init__("CPU", stdscr, jetson)
        # List all CPU
        self.chart_cpus = []
        for name in sorted(self.jetson.cpu):
            chart = Chart(jetson, name, self.update_chart, color=curses.color_pair(4), color_chart=[curses.color_pair(10)])
            self.chart_cpus += [chart]

    def update_chart(self, jetson, name):
        cpu = jetson.cpu[name]
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
        # Platform information
        arch = platform.machine()
        plot_name_info(self.stdscr, first + 2, 2, "Arch", arch)
        release = platform.release()
        release = release[:x_offset - (first + 3) - 4]
        plot_name_info(self.stdscr, first + 3, 2, "Rel", release)
        plot_name_info(self.stdscr, first + 4, 2, "Cluster", self.jetson.cluster)
        # Architecture CPU cores
        # architecture = self.jetson.architecture
        offset_table = 6
        for idx, name in enumerate(sorted(self.jetson.cpu)):
            cpu = self.jetson.cpu[name]
            status = 'ON' if cpu else 'OFF'
            active = True if cpu else False
            frq = label_freq(cpu['frq'], start='k') if 'frq' in cpu else ''
            # Load model architecture
            model = cpu['model'].split()[0] if 'model' in cpu else ''
            model = model[:x_offset - (first + 3) - 4]
            # Draw info
            color = curses.color_pair(8) if active else curses.color_pair(7)
            self.stdscr.addstr(first + offset_table + idx * 2, 2, name, color)
            try:
                if active:
                    self.stdscr.addstr(first + offset_table + idx * 2, 2 + len(name) + 1, model, curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 2, "Frq:", curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 7, "{}".format(frq), curses.A_BOLD)
                else:
                    self.stdscr.addstr(first + offset_table + idx * 2, 2 + len(name) + 1, status, curses.A_NORMAL)
            except curses.error:
                pass
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
            # Incrase counter
            counter = idx_n - line * (n_cpu // 2)
            # Evaluate size chart
            add_size = offest_label if y_label else 0
            size_x = [x_offset + 2 + (counter * (x_size)), x_offset + x_size * (1 + counter) + add_size]
            size_y = [first + 1 + (line * (y_size)), first + y_size * (1 + line)]
            # Value and frequency
            if status:
                governor = data.get('governor', '')[:x_size + add_size - 12]
                percent = data.get('val', 0)
                label_chart_cpu = "{percent: >3d}% {governor}".format(percent=percent, governor=governor.capitalize())
                chart.draw(self.stdscr, size_x, size_y, label=label_chart_cpu, y_label=y_label)
            idx_n += 1
# EOF
