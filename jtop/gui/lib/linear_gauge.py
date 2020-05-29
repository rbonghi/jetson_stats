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
from .common import check_curses


class GaugeName:
    def __init__(self, text, color=curses.A_NORMAL):
        self.text = text
        self.color = color


class GaugeBar:
    def __init__(self, number, color):
        self.number = number
        self.color = color


@check_curses
def linear_gauge(stdscr, offset=0, start=0, size=10, name="", value=0, status="ON", percent="", label="", bar="|"):
    name = GaugeName(name) if isinstance(name, str) else name
    label = GaugeName(label) if isinstance(label, str) else label
    values = (GaugeBar(value, curses.color_pair(2)), ) if isinstance(value, int) else value
    # Evaluate size withuout short name
    name_size = len(name.text)
    size_bar = size - name_size - 4
    # Show short name linear gauge
    stdscr.addstr(offset, start, name.text, name.color)
    # Check if value is not a string
    if 'ON' in status:
        # Show bracket linear gauge and label and evaluate size withuout size labels and short name
        size_bar -= (len(label.text) + 1) if label.text else 0
        stdscr.addstr(offset, start + name_size + 1, "[" + " " * size_bar + "]", curses.A_BOLD)
        if label.text:
            stdscr.addstr(offset, start + name_size + 1 + size_bar + 3, label.text, label.color)
        # Show progress value linear gauge
        total = sum([val.number for val in values])
        n_bar = int(float(total) * float(size_bar) / 100.0)
        if n_bar >= 0:
            # Build progress barr string
            str_progress_bar = bar * n_bar
            percent_label = percent if percent else str(total) + "%"
            str_progress_bar = str_progress_bar[:size_bar - len(percent_label)] + percent_label
            # Split string in green and grey part
            counter = 0
            old_val = 0
            for value in values:
                val_bar = int(float(old_val + value.number) * float(size_bar) / 100.0)
                stdscr.addstr(offset, start + name_size + 2 + counter, str_progress_bar[counter:val_bar], value.color)
                counter += val_bar
                old_val += value.number
            # Draw grey part
            grey_part = str_progress_bar[n_bar:]
            stdscr.addstr(offset, start + name_size + 2 + size_bar - len(grey_part), grey_part, curses.A_DIM)
    else:
        # Show bracket linear gauge and label
        stdscr.addstr(offset, start + name_size + 1, ("[{value:>" + str(size_bar) + "}]").format(value=" "), curses.color_pair(7))
        # Show bracket linear gauge and label
        status = status if status else "OFF"
        stdscr.addstr(offset, start + name_size + 4, status, curses.color_pair(7))
# EOF
