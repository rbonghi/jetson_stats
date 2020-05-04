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

import os
import sys
# control command line
import curses
from curses.textpad import rectangle
# Functions and decorators
from functools import wraps


def xterm_line(jetson):
    str_xterm = " " + jetson.board["board"]["Type"]
    nvp = jetson.nvpmodel
    # if "GR3D" in jetson.stats:
    #     gpu = jetson.stats["GR3D"]['val']
    #     str_xterm += " - GPU {gpu: 3}% {label}".format(gpu=gpu, label=label_freq(jetson.stats["GR3D"]))
    if nvp is not None:
        str_xterm += " - {}".format(nvp.mode)
    return str_xterm


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


def check_size(height_max, width_max):
    """ Check curses size window """
    def check_size_window(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            # Extract window size
            height, width = self.stdscr.getmaxyx()
            # Check size window
            if width >= width_max and height >= height_max:
                return func(self, *args, **kwargs)
            else:
                string_warning = "jtop"
                string_warning_msg = "Change size window!"
                size_window_width = "Width: " + str(width) + " >= " + str(width_max)
                size_window_height = "Height: " + str(height) + " >= " + str(height_max)
                try:
                    height_c = int(height / 2)
                    self.stdscr.addstr(height_c - 2, int((width - len(string_warning)) / 2), string_warning, curses.A_BOLD)
                    self.stdscr.addstr(height_c - 1, int((width - len(string_warning_msg)) / 2), string_warning_msg, curses.A_BOLD)
                    # Show size window
                    if width < width_max:
                        self.stdscr.addstr(height_c, int((width - len(size_window_width)) / 2), str(size_window_width), curses.color_pair(1))
                    else:
                        size_window_width = "Width OK!"
                        self.stdscr.addstr(height_c, int((width - len(size_window_width)) / 2), size_window_width, curses.A_BOLD)
                    if height < height_max:
                        self.stdscr.addstr(height_c + 1, int((width - len(size_window_height)) / 2), str(size_window_height), curses.color_pair(1))
                    else:
                        size_window_height = "Height OK!"
                        self.stdscr.addstr(height_c + 1, int((width - len(size_window_height)) / 2), str(size_window_height), curses.A_BOLD)
                    # Set background for all menu line
                    self.stdscr.addstr(height - 1, 0, ("{0:<" + str(width - 1) + "}").format(" "), curses.A_REVERSE)
                    # Add close option menu
                    self.stdscr.addstr(height - 1, 1, "Q to close", curses.A_REVERSE)
                except curses.error:
                    pass
        return wrapped
    return check_size_window


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


def mouse_clicked(mouse, y, x, width, height):
    if mouse:
        mx, my = mouse
        if my >= y and my <= y + height and mx >= x and mx <= x + width:
            return True
    return False


@check_curses
def box_keyboard(stdscr, x, y, letter, key, mouse=(), label=None, action=None):
    # Evaluate size label
    lnlabel = len(label) + 1 if label is not None else 0
    # Draw background rectangle
    rectangle(stdscr, y, x, y + 2, x + 4 + lnlabel)
    # Default status
    status = key == ord(letter) or mouse_clicked(mouse, y, x, 4 + lnlabel, 2)
    # Write letter
    stdscr.addstr(y + 1, x + 2, letter, curses.A_REVERSE if status else curses.A_NORMAL)
    # Write label
    if label is not None:
        stdscr.addstr(y + 1, x + 4, label, curses.A_NORMAL)
    # Run Action
    if action is not None and status:
        action(letter)
    # Return the status of key
    return True if status else False


@check_curses
def box_status(stdscr, x, y, name, status=False, color=curses.A_REVERSE, mouse=(), action=None):
    # Draw background rectangle
    rectangle(stdscr, y, x, y + 2, x + 3 + len(name))
    # Default status
    status = color if status else curses.A_NORMAL
    # Write letter
    stdscr.addstr(y + 1, x + 2, name, status)
    # Run Action
    if action is not None and mouse_clicked(mouse, y, x, 3 + len(name), 2):
        action(name)


@check_curses
def box_list(stdscr, x, y, data, selected, status=[], max_width=-1, numbers=False, mouse=(), action=None):
    len_prev = 0
    line = 0
    skip_line = False if max_width == -1 else True
    for idx, name in enumerate(data):
        if status:
            color = curses.A_REVERSE if status[idx] else curses.color_pair(1)
            status_selected = True if selected == idx else not status[idx]
        else:
            status_selected = True if selected == idx else False
        # Add number idx if required
        str_name = name if not numbers else str(idx) + " " + name
        # Find next position
        if skip_line and len_prev + len(str_name) + 4 >= max_width:
            line += 3
            len_prev = 0
        # Plot box
        box_status(stdscr, x + len_prev, y + line, str_name, status=status_selected, color=color, mouse=mouse, action=action)
        len_prev += len(str_name) + 4
    # Draw background rectangle
    # rectangle(stdscr, y, x, y + 2, x + 3 + len(name))
    return line


def label_freq(value):
    if 'frq' in value:
        freq = value['frq']
        if freq >= 1000:
            return "{0:2.1f}GHz".format(freq / 1000.0)
        else:
            return str(freq) + "MHz"
    else:
        return ""


def size_min(num, divider=1.0, n=0, start=''):
    if num >= divider * 1000.0:
        n += 1
        divider *= 1000.0
        return size_min(num, divider, n, start)
    else:
        vect = ['', 'k', 'M', 'G', 'T']
        idx = vect.index(start)
        return round(num / divider, 1), divider, vect[n + idx]


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


@check_curses
def plot_dictionary(stdscr, offset, data, name, start=0):
    # Plot title
    stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
    counter = 1
    for key, value in data.items():
        if 'text' in value:
            stdscr.addstr(offset + counter, start, " {0:<10} {1}".format(key, value['text']))
        else:
            stdscr.addstr(offset + counter, start, " {0:<10} {1}".format(key, value))
        counter += 1


@check_curses
def plot_name_info(stdscr, offset, start, name, value, color=curses.A_NORMAL):
    stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
    stdscr.addstr(offset, start + len(name) + 2, value, color)
# EOF
