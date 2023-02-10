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


# control command line
import curses
# Graphics elements
from .lib.common import check_curses
from .lib.colors import NColors
from .pengine import compact_engines


@check_curses
def plot_temperatures(stdscr, start, offset, width, height, jetson):
    counter = 0
    start = start + (width - 17) // 2
    # Define color temperatures
    color_options = {
        60: NColors.red(),
        40: NColors.yellow(),
        20: curses.A_NORMAL,
    }
    list_options = sorted(color_options.keys(), reverse=True)
    # Plot title
    stdscr.addstr(offset, start - 1, " [Sensor] ", curses.A_BOLD)
    stdscr.addstr(offset, start + 11, " [Temp] ", curses.A_BOLD)
    # Plot name and temperatures
    for idx, name in enumerate(sorted(jetson.temperature)):
        # Print temperature name
        value = jetson.temperature[name]
        # Set color temperature
        color = curses.A_NORMAL
        for k in list_options:
            if value >= k:
                color = color_options[k]
                break
        # Print temperature value
        try:
            stdscr.addstr(offset + idx + 1, start, ("{name:<7}").format(name=name))
            stdscr.addstr(offset + idx + 1, start + offset // 2 + 3, ("{val:8.2f}C").format(val=value), color)
        except curses.error:
            pass
        counter = idx
    return counter + 2


@check_curses
def plot_watts(stdscr, start, offset, width, height, jetson):
    start = start + (width - 6) // 2
    # Plot title
    stdscr.addstr(offset, start - 11, " [Power/mW] ", curses.A_BOLD)
    stdscr.addstr(offset, start + 2, " [Cur] ", curses.A_BOLD)
    stdscr.addstr(offset, start + 9, " [Avr] ", curses.A_BOLD)
    # Plot watts
    total, power = jetson.power
    for idx, name in enumerate(sorted(power)):
        value = power[name]
        stdscr.addstr(offset + idx + 1, start - 10, name, curses.A_NORMAL)
        stdscr.addstr(offset + idx + 1, start + 3, str(value['cur']), curses.A_NORMAL)
        stdscr.addstr(offset + idx + 1, start + 10, str(value['avg']), curses.A_NORMAL)
    # Plot totals before finishing
    len_power = len(power)
    stdscr.addstr(offset + len_power + 1, start - 10, 'ALL', curses.A_BOLD)
    stdscr.addstr(offset + len_power + 1, start + 3, str(total['cur']), curses.A_BOLD)
    stdscr.addstr(offset + len_power + 1, start + 10, str(total['avg']), curses.A_BOLD)


@check_curses
def compact_info(stdscr, start, offset, width, height, jetson):
    # Title menu
    # stdscr.addstr(offset, start + (width - 7) // 2, " [info] ", curses.A_BOLD)
    # counter = 1
    # Write all engines
    return compact_engines(stdscr, start, offset, width, jetson)
# EOF
