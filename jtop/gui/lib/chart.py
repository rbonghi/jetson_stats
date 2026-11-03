# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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
import itertools
from math import ceil
from functools import lru_cache
import curses
from collections import deque
from .common import check_curses


class Chart(object):

    COLOR_COUNTER = 0
    OFFSET_COLOR_CHART = 20
    OFFSET_COLOR_TEXT = 18

    """
    Chart draw object
    http://www.melvilletheatre.com/articles/ncurses-extended-characters/index.html
    """

    def __init__(self, jetson, name, callback, type_value=int, line="*", color_text=curses.COLOR_WHITE, color_chart=[], fill=True, time=10.0, tik=2):
        self._color_obj_counter = Chart.COLOR_COUNTER
        self.jetson = jetson
        self.name = name
        self.callback = callback
        # Set shape
        self.refresh = jetson.interval * 1000
        # Design chart shape
        self.line = line
        self.color_text = color_text
        self.color_chart = color_chart if color_chart else [color_text]
        self.fill = fill
        # Set timing
        self.time = time
        self.tik = tik
        # Initialization chart
        max_record = int(self.time * (float(1.0 / float(self.refresh)) * 1000.0))
        self.values = deque(max_record * [(len(self.color_chart) * [0])], maxlen=max_record)
        # Initialize default values and unit
        self.unit = "%"
        self.type_value = type_value
        self.max_val = 100
        self.active = True
        self.message = "OFF"
        # Initialize all colors
        color_step = len(self.color_chart)
        values = list(range(len(self.color_chart)))[::-1] + [len(self.color_chart)]
        self._combinations = list(itertools.combinations(values, 2))
        list_colors = {}
        for c in self._combinations:
            if c[0] not in list_colors:
                list_colors[c[0]] = []
            list_colors[c[0]] = [c] + list_colors[c[0]]
        try:
            for idx, list_element in enumerate(list_colors.values()):
                list_element = sorted(list_element, key=lambda x: x[1], reverse=True)
                for idy, color_set in enumerate(list_element):
                    idx_name = Chart.OFFSET_COLOR_CHART + self._color_obj_counter + (len(self.color_chart) - idx - 1) * color_step + idy
                    if idx_name < 1:
                        continue
                    second_color = self.color_chart[color_set[1]] if color_set[1] < len(self.color_chart) else curses.COLOR_BLACK
                    curses.init_pair(idx_name, self.color_chart[color_set[0]], second_color)
        except (curses.error, ValueError):
            curses.use_default_colors()
        # Update counter colors
        Chart.COLOR_COUNTER += len(self._combinations) + 1
        # Attach the chart for every update from jtop
        jetson.attach(self.update)

    @classmethod
    def reset_color_counter(cls):
        cls.COLOR_COUNTER = 0

    def __del__(self):
        Chart.COLOR_COUNTER = max(0, Chart.COLOR_COUNTER - len(self._combinations) - 1)

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

    def draw_y_axis(self, stdscr, pos_y, pos_x, size_height):
        self._plot_y_axis(stdscr, [0, pos_x + 4], [pos_y, pos_y + size_height])

    @check_curses
    def draw(self, stdscr, size_x, size_y, label="", y_label=True):
        curses.init_pair(Chart.OFFSET_COLOR_TEXT, self.color_text, curses.COLOR_BLACK)
        # Evaluate Diplay X, and Y size
        displayX = size_x[1] - size_x[0] + 1
        # displayY = size_y[1] - size_y[0] - 1
        # Text label
        stdscr.addstr(size_y[0], size_x[0], self.name, curses.A_BOLD)
        if label:
            stdscr.addstr(size_y[0], size_x[0] + len(self.name) + 1, label[:displayX - len(self.name)],
                          curses.color_pair(Chart.OFFSET_COLOR_TEXT) | curses.A_BOLD)
        # Draw ticks and labels
        self._plot_x_axis(stdscr, size_x, size_y, label=y_label)
        # Plot chart shape and labels
        self._plot_y_axis(stdscr, size_x, size_y, label=y_label)
        # Plot chart lines
        # Plot values
        self._plot_values(stdscr, size_x, size_y, label=y_label)
        # Add messsage not active
        if not self.active:
            l_label = size_x[1] - 6 if y_label else size_x[1] - 1
            # rectangle(stdscr, size_y[0] + 1, size_x[0], size_y[1], l_label)
            stdscr.hline(size_y[0] + 1, size_x[0], curses.ACS_HLINE, l_label - size_x[0] + 1)
            # Write message
            middle_x = (l_label - size_x[0] - len(self.message)) // 2
            middle_y = (size_y[1] - size_y[0]) // 2
            stdscr.addstr(size_y[0] + middle_y, size_x[0] + middle_x, self.message, curses.A_BOLD)

    def _plot_y_axis(self, stdscr, size_x, size_y, label=True):
        # Plot chart shape and labels
        displayY = size_y[1] - size_y[0] - 1
        label_x = size_x[1] - 5 if label else size_x[1]
        for point in range(displayY):
            if displayY != point:
                value_n = self.max_val / float(displayY) * float(displayY - point)
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

    def _plot_x_axis(self, stdscr, size_x, size_y, label=True):
        displayX = size_x[1] - size_x[0] + 1
        val = float(displayX - 2) / float(len(self.values))
        # Draw ticks and labels
        ten_sec = int(self.tik * 1000 / self.refresh)
        counter = 0
        label_y = size_x[1] - 5 if label else size_x[1]
        # Draw line
        stdscr.hline(size_y[1] - 1, size_x[0], curses.A_UNDERLINE, label_y - size_x[0])
        for point in range(displayX):
            x_val = label_y - point
            if x_val >= size_x[0]:
                try:
                    # Draw tick label
                    if ((point) / ceil(val)) % ten_sec == 0:
                        stdscr.addch(size_y[1], x_val, curses.ACS_LLCORNER)
                    # Draw label
                    if counter > 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        stdscr.addstr(size_y[1], x_val + 3, "-{time}s".format(time=self.tik * counter))
                    elif counter == 0 and ((point - 1) / ceil(val)) % ten_sec == 0:
                        if label:
                            stdscr.addstr(size_y[1], x_val + 3, "time")
                        stdscr.addstr(size_y[1], x_val + 1, "0")
                    # Increase counter
                    if ((point - 1) / ceil(val)) % ten_sec == 0:
                        counter += 1
                except curses.error:
                    pass

    def _plot_values(self, stdscr, size_x, size_y, label=True):
        # Area Plot data
        size_plot_x = [size_x[0], size_x[1] - 6 if label else size_x[1] - 1]
        size_plot_y = [size_y[0], size_y[1] - 1]
        size_y = size_plot_y[1] - size_plot_y[0]
        list_values = list(self.values)
        val = ceil(float(size_plot_x[1] - size_plot_x[0]) / float(len(list_values)))
        points = []
        for n in list_values:
            points += [n] * int(val)
        # Draw all chart
        color_step = len(self.color_chart)
        color_offset = Chart.OFFSET_COLOR_CHART + self._color_obj_counter
        for idx, values in enumerate(reversed(points)):
            pos_x = size_plot_x[1] - idx
            if pos_x < size_plot_x[0]:
                continue
            if self.fill:
                # Height of each series in 1/8 of a row
                targets = [min(max(value, 0) * size_y * 8 / self.max_val, size_y * 8) for value in values]
                if all(x >= y for x, y in zip(targets, targets[1:])):
                    # Stacked chart: fit the boundaries so every cell has at most two colors
                    tops = Chart._stacked_tops(tuple(round(x, 2) for x in targets), size_y * 8)
                else:
                    tops = tuple(max(1, int(round(x))) if x > 0 else 0 for x in targets)
                for n, (fg, fg_h, bg) in enumerate(Chart._column_cells(tops)):
                    if fg_h == 8:
                        # Full block: \u2588
                        glyph, pair = u'\u2588', color_offset + fg * color_step
                    else:
                        # Lower 1/8 (\u2581) to 7/8 (\u2587) block, background for the rest of the cell
                        # Color pair index: 0 = black background, k = background of series fg - k
                        glyph, pair = chr(0x2580 + fg_h), color_offset + fg * color_step + (fg - bg if bg is not None else 0)
                    stdscr.addstr(size_plot_y[1] - n, pos_x, glyph.encode('utf-8'), curses.color_pair(pair))
            else:
                for value in values:
                    cell_val = min(value * size_y / self.max_val, size_y)
                    if cell_val > 0:
                        stdscr.addstr(size_plot_y[1] - int(cell_val), pos_x, self.line, curses.color_pair(Chart.OFFSET_COLOR_TEXT))

    @staticmethod
    @lru_cache(maxsize=256)
    def _stacked_tops(targets, limit):
        """
        Fit the tops (in eighths) of a stacked chart, largest series first.

        A terminal cell can show only two colors, so at most one top may end
        inside each cell (tops on a cell border are free). Search the tops
        within one row of their target that respect this, and keep the one
        closest to the real chart: each non-zero segment as thick as its value
        but at least 1/8 (thin values show as a line), and the same total height.
        Dynamic programming from the innermost series outward.
        """
        inner = targets[::-1]
        # best[top] = (cost, tops so far) for the series processed so far
        best = {0: (0.0, ())}
        previous = 0.0
        for target in inner:
            length = target - previous
            goal = max(length, 1.0) if length > 0 else 0.0
            center = int(round(target))
            following = {}
            for low, (cost, path) in best.items():
                for top in range(max(low, center - 8), min(limit, center + 8) + 1):
                    size = top - low
                    if (goal > 0 and size < 1) or (goal == 0 and size != 0):
                        continue
                    # Two tops inside the same cell would need three colors
                    if low % 8 and top % 8 and low // 8 == top // 8:
                        continue
                    new_cost = cost + abs(size - goal)
                    if top not in following or new_cost < following[top][0]:
                        following[top] = (new_cost, path + (top,))
            best = following
            previous = target
        # Add the error on the total height (outermost top)
        _, path = min(best.values(), key=lambda item: item[0] + abs(item[1][-1] - targets[0]))
        return path[::-1]

    @staticmethod
    @lru_cache(maxsize=256)
    def _column_cells(tops):
        """
        Return (foreground, height in eighths, background) for each row of a column.

        Series drawn later are on top, so the color at any height (in eighths)
        is the highest series index whose top is above it. Each cell is drawn as
        a lower block in the color at its bottom, and the color just above as
        background (None = empty).
        """
        column = [max([i for i, top in enumerate(tops) if top > pos] or [None]) for pos in range(max(tops + (0,)))]
        cells = []
        for low in range(0, len(column), 8):
            cell = column[low:low + 8]
            cell += [None] * (8 - len(cell))
            fg_h = 1
            while fg_h < 8 and cell[fg_h] == cell[0]:
                fg_h += 1
            cells.append((cell[0], fg_h, cell[fg_h] if fg_h < 8 else None))
        return cells
# EOF
