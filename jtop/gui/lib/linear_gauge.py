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


@check_curses
def linear_gauge(stdscr, offset=0, start=0, size=10, name="", value=0, status="ON", percent="", label="", type_bar="|", color=curses.A_NORMAL):
    # Evaluate size withuout short name
    name_size = len(name)
    size_bar = size - name_size - 4
    # Show short name linear gauge
    stdscr.addstr(offset, start, ("{name:" + str(name_size) + "}").format(name=name), color)
    # Check if value is not a string
    if 'ON' in status:
        # Show bracket linear gauge and label and evaluate size withuout size labels and short name
        size_bar -= (len(label) + 1) if label else 0
        stdscr.addstr(offset, start + name_size + 1, "[" + " " * size_bar + "]", curses.A_BOLD)
        if label:
            stdscr.addstr(offset, start + name_size + 1 + size_bar + 3, label)
        # Show progress value linear gauge
        n_bar = int(float(value) * float(size_bar) / 100.0)
        if n_bar >= 0:
            progress_bar = type_bar * n_bar
            # Build progress barr string
            str_progress_bar = ("{n_bar:" + str(size_bar) + "}").format(n_bar=progress_bar)
            percent_label = percent if percent else str(value) + "%"
            str_progress_bar = str_progress_bar[:size_bar - len(percent_label)] + percent_label
            # Split string in green and grey part
            green_part = str_progress_bar[:n_bar]
            grey_part = str_progress_bar[n_bar:]
            stdscr.addstr(offset, start + name_size + 2, green_part, curses.color_pair(2))
            stdscr.addstr(offset, start + name_size + 2 + size_bar - len(grey_part), grey_part, curses.A_DIM)
    else:
        # Show bracket linear gauge and label
        stdscr.addstr(offset, start + name_size + 1, ("[{value:>" + str(size_bar) + "}]").format(value=" "), curses.color_pair(7))
        # Show bracket linear gauge and label
        status = status if status else "OFF"
        stdscr.addstr(offset, start + name_size + 4, status, curses.color_pair(7))
# EOF
