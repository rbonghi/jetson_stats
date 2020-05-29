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

# Math functions
from math import ceil
import curses
from curses.textpad import rectangle
from collections import deque
from .common import check_curses


class Chart(object):
    """
    Chart draw object
    http://www.melvilletheatre.com/articles/ncurses-extended-characters/index.html
    """
    def __init__(self, jetson, name, interval, callback, type_value=int, line="*", color=curses.A_NORMAL, color_chart=[], fill=True, time=10.0, tik=2):
        self.jetson = jetson
        self.name = name
        self.callback = callback
        # Set shape
        self.refresh = interval
        # Design chart shape
        self.line = line
        self.color = color
        self.color_chart = color_chart if color_chart else [color]
        self.fill = fill
        # Set timing
        self.time = time
        self.tik = tik
        # Initialization chart
        max_record = int(self.time * (float(1.0 / float(interval)) * 1000.0))
        self.values = deque(max_record * [(len(self.color_chart) * [0])], maxlen=max_record)
        # Initialzie default values and unit
        self.unit = "%"
        self.type_value = type_value
        self.max_val = 100
        self.active = True
        self.message = "OFF"
        # Attach the chart for every update from jtop
        jetson.attach(self)

    def statusChart(self, active, message):
        self.active = active
        self.message = message

    def update(self, jetson):
        """ Local update chart """
        # Call the callback
        data = self.callback(jetson, self.name)
        # Get max value if is present
        self.max_val = data.get("max", self.max_val)
        # Get unit
        self.unit = data.get("unit", self.unit)
        # Get status
        self.active = data.get("active", self.active)
        # update the queue
        value = data.get("value", [0])
        self.values.append(value)

    @check_curses
    def draw(self, stdscr, size_x, size_y, label="", y_label=True):
        # Evaluate Diplay X, and Y size
        displayX = size_x[1] - size_x[0] + 1
        displayY = size_y[1] - size_y[0] - 1
        # Text label
        stdscr.addstr(size_y[0], size_x[0], self.name, curses.A_BOLD)
        if label:
            stdscr.addstr(size_y[0], size_x[0] + len(self.name) + 1, label, self.color | curses.A_BOLD)
        # Plot chart lines
        if self.active:
            # Plot values
            self._plot_values(stdscr, size_x, size_y, displayX, displayY, label=y_label)
        else:
            l_label = size_x[1] - 6 if y_label else size_x[1] - 1
            rectangle(stdscr, size_y[0] + 1, size_x[0], size_y[1] - 2, l_label)
            # Write message
            middle_x = (l_label - size_x[0] - len(self.message)) // 2
            middle_y = (size_y[1] - size_y[0]) // 2
            stdscr.addstr(size_y[0] + middle_y, size_x[0] + middle_x, self.message, curses.A_BOLD)
        # Draw ticks and labels
        self._plot_x_axis(stdscr, size_x, size_y, displayX, label=y_label)
        # Plot chart shape and labels
        self._plot_y_axis(stdscr, size_x, size_y, displayY, label=y_label)

    def _plot_y_axis(self, stdscr, size_x, size_y, displayY, label=True):
        # Plot chart shape and labels
        label_x = size_x[1] - 5 if label else size_x[1]
        for point in range(displayY):
            if displayY != point:
                value_n = self.max_val / float(displayY - 1) * float(displayY - point - 1)
                try:
                    stdscr.addch(1 + size_y[0] + point, label_x, curses.ACS_LTEE)
                    if not label:
                        continue
                    if self.type_value == float:
                        lab_c = "{value:2.1f}{unit}".format(value=value_n, unit=self.unit)
                    else:
                        lab_c = "{value:3d}{unit}".format(value=int(value_n), unit=self.unit)
                    stdscr.addstr(1 + size_y[0] + point, label_x + 2, lab_c, curses.A_BOLD)
                except curses.error:
                    pass

    def _plot_x_axis(self, stdscr, size_x, size_y, displayX, label=True):
        val = float(displayX - 2) / float(len(self.values))
        # Draw ticks and labels
        ten_sec = int(self.tik * 1000 / self.refresh)
        counter = 0
        label_y = size_x[1] - 5 if label else size_x[1]
        # Draw line
        stdscr.hline(size_y[1] - 1, size_x[0], curses.ACS_HLINE, label_y - size_x[0])
        for point in range(displayX):
            x_val = label_y - point
            if x_val >= size_x[0]:
                try:
                    # Draw tick label
                    if ((point) / ceil(val)) % ten_sec == 0:
                        stdscr.addch(size_y[1] - 1, x_val, curses.ACS_TTEE)
                    # Draw label
                    if counter > 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        stdscr.addstr(size_y[1], x_val, "-{time}s".format(time=self.tik * counter))
                    elif counter == 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        if label:
                            stdscr.addstr(size_y[1], x_val + 3, "time")
                        stdscr.addstr(size_y[1], x_val + 1, "0")
                    # Increase counter
                    if ((point - 1) / ceil(val)) % ten_sec == 0:
                        counter += 1
                except curses.error:
                    pass

    def _plot_values(self, stdscr, size_x, size_y, displayX, displayY, label=True):
        """ Plot values """
        val = float(displayX - 2) / float(len(self.values))
        time_block = int(ceil(val))

        label_x = size_x[1] - 5 if label else size_x[1]

        for idx, values in enumerate(reversed(self.values)):
            # TODO: n = n if n <= self.max_val else self.max_val
            x_val = label_x - idx * time_block - 3
            # Draw chart
            counter = 0
            for value, color in zip(values, self.color_chart):
                y_val = int((float(displayY - 1) / self.max_val) * value)

                if x_val >= size_x[0]:
                    if self.fill:
                        for n in range(counter + 1, counter + y_val + 1):
                            try:
                                stdscr.addstr(size_y[1] - 1 - n, x_val, " " * time_block, color)
                            except curses.error:
                                pass
                    else:
                        try:
                            stdscr.addstr(size_y[1] - 1 - y_val, x_val, self.line, self.color)
                        except curses.error:
                            pass
                counter += y_val
# EOF
