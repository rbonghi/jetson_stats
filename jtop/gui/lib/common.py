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

import os
import sys
# control command line
import curses
# Functions and decorators
from .colors import NColors
from functools import wraps


def set_xterm_title(title):
    '''
    Set XTerm title using escape sequences.
    By default, sets as 'Python' and the version number.
    '''
    # Make sure this terminal supports the OSC code (\33]),
    # though not necessarily that it supports setting the title.
    # If this check causes compatibility issues, you can add
    # items to the tuple, or remove the check entirely.
    if os.environ.get('TERM') in ('xterm',
                                  'xterm-color',
                                  'xterm-256color',
                                  'linux',
                                  'screen',
                                  'screen-256color',
                                  'screen-bce',
                                  ):
        sys.stdout.write('\33]0;' + title + '\a')
        sys.stdout.flush()


def jetson_clocks_gui(stdscr, offset, start, jetson):
    # Write status jetson_clocks
    jc_status_name = jetson.jetson_clocks.get_status()
    # Read status jetson_clocks
    if jc_status_name == "running":
        color = (curses.A_BOLD | NColors.green())  # Running (Bold)
    elif jc_status_name == "inactive":
        color = curses.A_NORMAL       # Normal (Grey)
    elif "ing" in jc_status_name:
        color = NColors.yellow()  # Warning (Yellow)
    else:
        color = NColors.red()  # Error (Red)
    # Show if JetsonClock is enabled or not
    if jetson.jetson_clocks.get_boot():
        jc_status_name = "[" + jc_status_name + "]"
    # Show status jetson_clocks
    plot_name_info(stdscr, offset, start, "Jetson Clocks", jc_status_name, color)


def check_curses(func):
    """ Check curses write """
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except curses.error:
            pass
    return wrapped


def strfdelta(tdelta, fmt):
    """ Print delta time
        - https://stackoverflow.com/questions/8906926/formatting-python-timedelta-objects
    """
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def label_freq(frq, start='k'):
    szw, _, k_unit = size_min(frq, start=start)
    if szw >= 100:
        label = '{tot:2.0f}{unit}Hz'.format(tot=szw, unit=k_unit)
    elif szw >= 10:
        label = '{tot:2.0f} {unit}Hz'.format(tot=szw, unit=k_unit)
    else:
        label = '{tot:2.1f}{unit}Hz'.format(tot=szw, unit=k_unit)
    return label


def size_min(num, divider=1.0, n=0, start=''):
    return find_unit(num, 1024.0, divider, n, start)


def unit_min(num, divider=1.0, n=0, start=''):
    return find_unit(num, 1000.0, divider, n, start)


def find_unit(size, power, divider=1.0, n=0, start=''):
    n = 0
    power_labels = ['m', '', 'k', 'M', 'G', 'T']
    while size > power - 1:
        divider *= power
        size /= power
        n += 1
    idx = power_labels.index(start)
    return round(size, 1), divider, power_labels[n + idx]


def size_to_string(value, unit):
    return value_to_string(value, unit, "", size_min)


def unit_to_string(value, unit, type):
    return value_to_string(value, unit, type, unit_min)


def value_to_string(value, unit, type, func):
    value, _, unit = func(value, start=unit)
    value_string = str(value)
    if value >= 100:
        # value_string = value_string.rstrip('0').rstrip('.')
        value_string = value_string[:3].rstrip('.')
    return "{value}{unit}{type}".format(value=value_string, unit=unit, type=type)


def plot_dictionary(stdscr, pos_y, pos_x, name, data, size=None):
    size_y = 1
    size_x = 0
    try:
        stdscr.addstr(pos_y, pos_x, name, curses.A_BOLD)
    except curses.error:
        pass
    # Build table from dictionary
    for idx, (name, value) in enumerate(data.items()):
        # Plot nanme
        try:
            stdscr.addstr(pos_y + idx + 1, pos_x + 1, str(name) + ":", curses.A_BOLD)
        except curses.error:
            pass
        # Plot value
        color = curses.A_NORMAL if value else NColors.red()
        if not value:
            value = "MISSING"
        len_value = len(value)
        if size:
            if len(name) + len(value) + 3 > size:
                len_value = size - len(name) - 3
        try:
            stdscr.addstr(pos_y + idx + 1, pos_x + 3 + len(name), value[:len_value], color)
        except curses.error:
            pass
        size_x = max(size_x, len(name) + len(value) + 3)
        size_y += 1
    return size_y, size_x


def plot_name_info(stdscr, offset, start, name, value, color=curses.A_NORMAL, spacing=0):
    try:
        stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
        stdscr.addstr(offset, start + len(name) + 2 + spacing, value, color)
    except curses.error:
        pass
    return len(name) + len(value) + 2
# EOF
