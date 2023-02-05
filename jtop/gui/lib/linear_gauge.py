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
from .colors import NColors
from .common import check_curses
from .common import unit_to_string


def basic_gauge(stdscr, pos_y, pos_x, size_w, data, bar='|'):
    """_summary_

        data = {
            'name': name value
            'color': color test
            'online': bool status
            'message': Offline message - Default OFF
            'coffline': Color offline - Default RED
            'values': [(value, color), (value, color), ... ] sum of values = 100
            'mleft': message on left
            'mright': message on right - Default percentage
        }
    """
    # Evaluate size without short name
    name_size = 0
    if 'name' in data:
        if data['name']:
            name = data['name']
            name_size = len(name) + 1
            # Show short name linear gauge
            name_color = data['color'] if 'color' in data else curses.A_NORMAL
            stdscr.addstr(pos_y, pos_x, name, name_color)
    # Size bar
    size_bar = size_w - name_size - 1
    # Draw gauge
    online = data['online'] if 'online' in data else True
    # Draw gauge border
    color_offline = data['coffline'] if 'coffline' in data else NColors.ired()
    stdscr.addstr(pos_y, pos_x + name_size, "[" + " " * size_bar + "]", curses.A_BOLD if online else color_offline)
    # Draw bar
    if online:
        values = data['values'] if 'values' in data else []
        # size dynamic bar
        total = min(sum([value for value, _ in values]), 100)
        n_bar = int(total) * size_bar // 100
        # Draw progress bar
        str_progress_bar = bar * n_bar + " " * (size_bar - n_bar)
        # Add label right otherwise write a percent
        label_right = data['mright'] if 'mright' in data else "{:.1f}%".format(total)
        if size_bar > len(label_right):
            str_progress_bar = str_progress_bar[:size_bar - len(label_right)] + label_right
        # Add message on left
        if 'mleft' in data:
            if size_bar > len(data['mleft']) + len(label_right):
                str_progress_bar = data['mleft'] + str_progress_bar[len(data['mleft']):]
        # Draw all values
        x_bar_start = 0
        old_val = 0
        for value, color in values:
            x_bar_end = int((old_val + value) * size_bar) // 100
            stdscr.addstr(pos_y, pos_x + name_size + x_bar_start + 1, str_progress_bar[x_bar_start:x_bar_end], color)
            x_bar_start = x_bar_end
            old_val += int(value)
        # Draw grey part or message
        grey_part = str_progress_bar[x_bar_start:]
        stdscr.addstr(pos_y, pos_x + name_size + x_bar_start + 1, grey_part, curses.A_DIM)
    else:
        # Show message status
        stdscr.addstr(pos_y, pos_x + name_size + 2, data['message'] if 'message' in data else "OFF", color_offline)


def basic_gauge_simple(stdscr, pos_y, pos_x, size, freq_data):
    # Name gauge
    name = freq_data['name'] if 'name' in freq_data else ""
    # Current value in string
    curr_string = unit_to_string(freq_data['cur'], freq_data['unit'], 'Hz')
    # Draw name engine
    stdscr.addstr(pos_y, pos_x, name, NColors.cyan())
    # Write online bar
    size_bar = size - len(name) - len(curr_string) - 4
    start_bar = pos_x + len(name) + 1 if len(name) > 0 else pos_x
    end_bar = start_bar + size_bar
    # Check if there is a limit
    color_bar = NColors.green() if freq_data['online'] else NColors.red()
    if freq_data['online']:
        stdscr.hline(pos_y, start_bar + 1, curses.ACS_HLINE, size_bar)
        stdscr.addch(pos_y, start_bar + size_bar, curses.ACS_DIAMOND, curses.A_BOLD)
        stdscr.addstr(pos_y, end_bar - (size) // 2, " RUNNING ", color_bar | curses.A_BOLD)
    else:
        stdscr.hline(pos_y, start_bar + 1, curses.ACS_BULLET, size_bar)
        if size_bar > 7:
            stdscr.addstr(pos_y, start_bar + (size_bar - 5) // 2, ' OFF ', color_bar | curses.A_NORMAL)
        else:
            stdscr.addstr(pos_y, start_bar + (size_bar - 3) // 2, 'OFF', color_bar | curses.A_NORMAL)
    # Draw current frequency
    stdscr.addstr(pos_y, pos_x + size - 6, curr_string, NColors.italic())


def freq_gauge(stdscr, pos_y, pos_x, size, freq_data):
    # Name gauge
    name = freq_data['name'] if 'name' in freq_data else ""
    # Current value in string
    curr_string = unit_to_string(freq_data['cur'], freq_data['unit'], 'Hz')
    # If there is a min and a max
    if 'max' in freq_data:
        value = ((freq_data['cur'] - freq_data['min']) / (freq_data['max'] - freq_data['min'])) * 100 if freq_data['min'] != freq_data['max'] else 0
        # Convert values data
        data = {
            'name': name,
            'color': NColors.cyan(),
            'online': freq_data['online'],
            'values': [(value, NColors.green())],
            'mleft': unit_to_string(freq_data['min'], freq_data['unit'], 'Hz') if 'min' in freq_data else "",
            'mright': unit_to_string(freq_data['max'], freq_data['unit'], 'Hz') if 'max' in freq_data else "",
        }
        basic_gauge(stdscr, pos_y, pos_x, size - 8, data, bar=":")
        # Draw current frequency
        stdscr.addstr(pos_y, pos_x + size - 6, curr_string, NColors.italic())
    else:
        basic_gauge_simple(stdscr, pos_y, pos_x, size, freq_data)


# OLD - TO REMOVE


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
    values = (GaugeBar(value, NColors.green()), ) if isinstance(value, (int, float)) else value
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
        stdscr.addstr(offset, start + name_size + 1, ("[{value:>" + str(size_bar) + "}]").format(value=" "), NColors.ired())
        # Show bracket linear gauge and label
        status = status if status else "OFF"
        stdscr.addstr(offset, start + name_size + 4, status, NColors.ired())
# EOF
