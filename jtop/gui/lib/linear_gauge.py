# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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
from .common import value_to_string


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
    values = (GaugeBar(value, curses.color_pair(2)), ) if isinstance(value, (int, float)) else value
    # Evaluate size without short name
    name_size = len(name.text)
    size_bar = size - name_size - 4
    # Show short name linear gauge
    stdscr.addstr(offset, start, name.text, name.color)
    # Check if value is not a string
    if 'ON' in status:
        # Show bracket linear gauge and label and evaluate size without size labels and short name
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
            percent_label = percent if percent else "{:.0f}%".format(total)
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


@check_curses
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
    color_bar = curses.color_pair(2) if data['status'] else curses.color_pair(1)
    if 'max' in data:
        min_string = "<{min}".format(min=value_to_string(data['min'], unit)) if min != 0 else ""
        max_string = "{max}>".format(max=value_to_string(data['max'], unit))
        # Draw bar
        # https://www.htmlsymbols.xyz/box-drawing
        stdscr.addstr(pos_y, start_bar, "[" + " " * (size_bar) + "]", curses.A_BOLD)
        # Draw min and max value
        if size_bar <= 7:
            string_min_max = "-" * size_bar
        elif size_bar <= 14:
            string_min_max = "-" * (size_bar - 7) + max_string
        else:
            string_min_max = min_string + "-" * (size_bar - 14) + max_string
        # Draw indicator
        if data['max'] != data['min']:
            value = int((curr * size_bar) / (float(data['max'] - float(data['min']))))
            stdscr.addstr(pos_y, start_bar + 1, string_min_max[:value], color_bar)
            stdscr.addstr(pos_y, start_bar + int(value) + 1, string_min_max[value:], curses.A_DIM)
        else:
            stdscr.addstr(pos_y, start_bar + 1, string_min_max, color_bar)
        if data['status']:
            # Show current frequency
            stdscr.addstr(pos_y, pos_x + size - len(curr_string), curr_string, color_bar | curses.A_BOLD)
        else:
            stdscr.addstr(pos_y, pos_x + size - len(curr_string) + 1, 'OFF', color_bar | curses.A_NORMAL)
    else:
        if data['status']:
            stdscr.hline(pos_y, start_bar + 1, curses.ACS_HLINE, size_bar)
            stdscr.addch(pos_y, start_bar + size_bar, curses.ACS_DIAMOND, curses.A_BOLD)
            stdscr.addstr(pos_y, end_bar - (size) // 2, " RUNNING ", color_bar | curses.A_BOLD)
        else:
            stdscr.hline(pos_y, start_bar + 1, curses.ACS_BULLET, size_bar)
            if size_bar > 7:
                stdscr.addstr(pos_y, start_bar + (size_bar - 5) // 2, ' OFF ', color_bar | curses.A_NORMAL)
            else:
                stdscr.addstr(pos_y, start_bar + (size_bar - 3) // 2, 'OFF', color_bar | curses.A_NORMAL)
        # Show current frequency
        stdscr.addstr(pos_y, pos_x + size - len(curr_string), curr_string, color_bar | curses.A_NORMAL)
# EOF
