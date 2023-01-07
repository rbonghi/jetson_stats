# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2023 Raffaello Bonghi.
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
# Page class definition
from .jtopgui import Page
from .lib.common import value_to_string


def linear_frequency_gauge(stdscr, pos_y, pos_x, size, name, data):
    curr = data['curr']
    unit = data['unit']
    # Draw name engine
    stdscr.addstr(pos_y, pos_x, name, curses.color_pair(6))
    # Draw frequency
    curr_string = value_to_string(curr, unit)
    # Write status bar
    size_bar = size - len(name) - len(curr_string) - 4
    start_bar = pos_x + len(name) + 1
    end_bar = start_bar + size_bar
    # Check if there is a limit
    if data['status']:
        if 'max' in data:
            min_string = "< {min}".format(min=value_to_string(data['min'], unit)) if min != 0 else ""
            max_string = "{max}>".format(max=value_to_string(data['max'], unit))
            # Draw bar
            # https://www.htmlsymbols.xyz/box-drawing
            stdscr.addstr(pos_y, start_bar, "[" + " " * (size_bar) + "]", curses.A_BOLD)
            # Draw min and max value
            stdscr.addstr(pos_y, start_bar + 1, min_string, curses.A_DIM)
            stdscr.addstr(pos_y, end_bar - len(max_string) + 1, max_string, curses.A_DIM)
            # Draw indicator
            value = ((curr * size_bar) / float(data['max']))
            stdscr.addstr(pos_y, start_bar + int(value), '\u2588', curses.A_NORMAL)
        else:
            stdscr.addstr(pos_y, start_bar, "\u2501" * (size_bar - 2) + "\u25B6", curses.A_BOLD)
            stdscr.addstr(pos_y, end_bar - (size) // 2, " RUNNING ", curses.A_NORMAL)
            stdscr.addstr(pos_y, pos_x + size - len(curr_string) - 3, "F=", curses.A_NORMAL)
    else:
        stdscr.addstr(pos_y, start_bar, "[" + "\u2500" * (size_bar - 3) + "]", curses.A_BOLD)
        stdscr.addstr(pos_y, pos_x + size - len(curr_string) - 3, "F=", curses.A_NORMAL)
        stdscr.addstr(pos_y, end_bar - (size) // 2, ' OFF ', curses.A_BOLD)
    # Show current frequency
    stdscr.addstr(pos_y, pos_x + size - len(curr_string), curr_string, curses.A_NORMAL)


class ENGINE(Page):

    def __init__(self, stdscr, jetson):
        super(ENGINE, self).__init__("ENG", stdscr, jetson)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Draw all engines
        offset_y = first + 2
        offset_x = 1
        size_gauge = width - 2
        # Draw all engines
        for gidx, group in enumerate(self.jetson.engine):
            engines = self.jetson.engine[group]
            size_eng = size_gauge // len(engines) - 1
            for idx, (name, engine) in enumerate(engines.items()):
                linear_frequency_gauge(self.stdscr, offset_y + gidx * 2, offset_x + (size_eng + 1) * idx, size_eng, name, engine)
# EOF
