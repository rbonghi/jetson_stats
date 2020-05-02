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
from .jtopguilib import check_curses


class Chart(object):
    """
    Chart draw object
    """
    def __init__(self, jetson, name, interval, callback, line="*", color=curses.A_NORMAL, color_chart=None, fill=True, time=10.0, tik=2): #value_name='val', value_max="max_val"
        self.jetson = jetson
        self.name = name
        self.callback = callback
        # Set shape
        self.refresh = interval
        # Design chart shape
        self.line = line
        self.color = color
        self.color_chart = color if color_chart is None else color_chart
        self.fill = fill
        # Set timing
        self.time = time
        self.tik = tik
        # Initialization chart
        max_record = int(self.time * (float(1.0 / float(interval)) * 1000.0))
        self.value = deque(max_record * [0], maxlen=max_record)
        # Initialzie default values and unit
        self.unit = "%"
        self.max_val = 100
        self.active = True
        self.message = "OFF"
        # local variable no data
        self._noData = True
        # Attach the chart for every update from jtop
        jetson.attach(self)

    def update(self, jetson):
        """ Local update chart """
        self._noData = False
        # Call the callback
        data = self.callback(jetson, self.name)
        # Get max value if is present
        self.max_val = data.get("max", 100)
        # Get unit
        self.unit = data.get("unit", "%")
        # Get status
        self.active = data.get("active", True)
        # update the queue
        self.value.append(data.get("value", 0))

    @check_curses
    def draw(self, stdscr, size_x, size_y, label=""):
        if self._noData:
            return
        # Evaluate Diplay X, and Y size
        displayX = size_x[1] - size_x[0] + 1
        displayY = size_y[1] - size_y[0] - 1
        val = float(displayX - 2) / float(len(self.value))
        points = []
        for n in self.value:
            points += [n] * int(ceil(val))
        # Plot chart shape and labels
        for point in range(displayY - 1):
            if displayY != point:
                value_n = self.max_val / float(displayY - 2) * float(displayY - point - 2)
                try:
                    stdscr.addstr(1 + size_y[0] + point, size_x[1], "-")
                    stdscr.addstr(1 + size_y[0] + point, size_x[1] + 2,
                                  "{value:3d}{unit}".format(value=int(value_n), unit=self.unit),
                                  curses.A_BOLD)
                except curses.error:
                    pass
        # Text label
        stdscr.addstr(size_y[0], size_x[0], self.name, curses.A_BOLD)
        if label:
            stdscr.addstr(size_y[0], size_x[0] + len(self.name) + 1, label, self.color)
        # Draw ticks and labels
        self._plot_x_axis(stdscr, val, size_x, size_y, displayX)
        # Plot chart lines
        if self.active:
            # Plot values
            self._plot_values(stdscr, points, size_x, size_y, displayY)
        else:
            rectangle(stdscr, size_y[0] + 1, size_x[0], size_y[1] - 2, size_x[1] - 1)
            # Write message
            middle_x = (size_x[1] - size_x[0] - len(self.message)) // 2
            middle_y = (size_y[1] - size_y[0]) // 2
            stdscr.addstr(size_y[0] + middle_y, size_x[0] + middle_x, self.message, curses.A_BOLD)

    def _plot_x_axis(self, stdscr, val, size_x, size_y, displayX):
        # Draw ticks and labels
        ten_sec = int(self.tik * 1000 / self.refresh)
        counter = 0
        for point in range(displayX):
            x_val = size_x[1] - 1 - point
            if x_val >= size_x[0]:
                try:
                    # Draw tick label
                    tik_label = "|" if ((point) / ceil(val)) % ten_sec == 0 else "-"
                    stdscr.addstr(size_y[1] - 1, x_val, tik_label)
                    # Draw label
                    if counter > 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        stdscr.addstr(size_y[1], x_val, "-{time}s".format(time=self.tik * counter))
                        counter += 1
                    elif counter == 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        stdscr.addstr(size_y[1], x_val, "time")
                        counter += 1
                except curses.error:
                    pass

    def _plot_values(self, stdscr, points, size_x, size_y, displayY):
        """ Plot values
        """
        for idx, point in enumerate(reversed(points)):
            y_val = int((float(displayY - 2) / self.max_val) * point)
            x_val = size_x[1] - 1 - idx
            if x_val >= size_x[0]:
                if self.fill:
                    for n in range(0, y_val + 1):
                        try:
                            stdscr.addstr(size_y[1] - 2 - n, x_val, " ", self.color_chart)
                        except curses.error:
                            pass
                else:
                    try:
                        stdscr.addstr(size_y[1] - 2 - y_val, x_val, self.line, self.color)
                    except curses.error:
                        pass
# EOF
