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
from curses.textpad import rectangle
import platform
# Page class definition
from .jtopgui import Page
from .lib.chart import Chart
from .lib.common import (check_curses,
                         plot_name_info,
                         label_freq)


class CPU(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(CPU, self).__init__("CPU", stdscr, jetson, refresh)
        # List all CPU
        self.chart_cpus = []
        n_cpu = len(self.jetson.stats["CPU"])
        for idx in range(n_cpu):
            self.chart_cpus += [Chart(jetson,
                                      "CPU {idx}".format(idx=idx + 1),
                                      refresh,
                                      self.update_chart,
                                      color=curses.color_pair(4),
                                      color_chart=[curses.color_pair(10)])]

    def update_chart(self, jetson, name):
        n = int(name.split(" ")[1]) - 1
        cpu = jetson.stats["CPU"][n]
        status = cpu.get("status", "OFF") == "ON"
        return {
            'value': [cpu.get("val", 0)],
            'active': status
        }

    @check_curses
    def draw(self, key, mouse):
        """
            Draw a plot with GPU payload
        """
        n_cpu = sum([1 if cpu.get("status", "OFF") == "ON" else 0 for cpu in self.jetson.stats["CPU"]])
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
        # Architecture CPU cores
        architecture = self.jetson.architecture
        offset_table = 5
        for idx, cpu in enumerate(self.jetson.stats["CPU"]):
            status = cpu.get("status", "OFF")
            active = status == "ON"
            frq = label_freq(cpu)
            # Load governor if exist
            governor = cpu.get("governor", "")
            governor = governor[:x_offset - (first + 3) - 4]
            # Load model architecture
            model = ""
            if idx in architecture:
                cpu_arch = architecture[idx]
                model = cpu_arch.get("model name", "").split()[0]
                model = model[:x_offset - (first + 3) - 4]
            # Write label CPU name
            cpu_name = "CPU {n}:".format(n=idx + 1)
            # Draw info
            color = curses.color_pair(8) if active else curses.color_pair(7)
            self.stdscr.addstr(first + offset_table + idx * 2, 2, cpu_name, color)
            try:
                if active:
                    self.stdscr.addstr(first + offset_table + idx * 2, 2 + len(cpu_name) + 1, model, curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 2, frq, curses.A_NORMAL)
                    self.stdscr.addstr(first + offset_table + idx * 2 + 1, 2 + len(cpu_name) + 1, governor, curses.A_NORMAL)
                else:
                    self.stdscr.addstr(first + offset_table + idx * 2, 2 + len(cpu_name) + 1, status, curses.A_NORMAL)
            except curses.error:
                pass
        # Evaluate size single chart
        x_size = (width - x_offset - 6) // (n_cpu // 2)
        y_size = (height - 2 - first) // 2
        # Measure offset label
        offest_label = width - (2 + x_offset + x_size * (n_cpu // 2))
        # Plot all CPUs
        idxn = 0
        for idx, (cpu, data) in enumerate(zip(self.chart_cpus, self.jetson.stats["CPU"])):
            # status CPU
            status = data.get("status", "OFF") == "ON"
            if not status:
                continue
            y_label = idxn % (n_cpu // 2) == (n_cpu // 2) - 1
            # Select line
            line = 1 if idxn >= n_cpu // 2 else 0
            # Incrase counter
            counter = idxn - line * (n_cpu // 2)
            # Evaluate size chart
            add_size = offest_label if y_label else 0
            size_x = [x_offset + 2 + (counter * (x_size)), x_offset + x_size * (1 + counter) + add_size]
            size_y = [first + 1 + (line * (y_size)), first + y_size * (1 + line)]
            # Value and frequency
            if status:
                label_chart_cpu = "{percent: >2}%".format(percent=data['val']) if 'val' in data else ""
                cpu.draw(self.stdscr, size_x, size_y, label=label_chart_cpu, y_label=y_label)
            idxn += 1
# EOF
