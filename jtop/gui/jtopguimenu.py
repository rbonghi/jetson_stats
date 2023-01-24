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
from .lib.common import (check_curses,
                         strfdelta,
                         plot_name_info,
                         label_freq,
                         jetson_clocks_gui,
                         nvp_model_gui)
from .lib.linear_gauge import linear_gauge, GaugeName
from .pengine import compact_engines


@check_curses
def plot_CPUs(stdscr, offest, list_cpus, width):
    max_bar = int(float(width) / 2.0)
    for idx, name in enumerate(sorted(list_cpus)):
        cpu = list_cpus[name]
        # Split in double list
        start = max_bar if idx >= len(list_cpus) / 2 and len(list_cpus) > 4 else 0
        off_idx = idx - len(list_cpus) / 2 if idx >= len(list_cpus) / 2 and len(list_cpus) > 4 else idx
        # Check if exist governor and add in percent name
        percent = ""
        if 'val' in cpu and 'governor' in cpu:
            percent = "{gov} -{val: 4}%".format(gov=cpu['governor'].capitalize(), val=cpu['val'])
        # Show linear gauge
        name = "CPU{name}".format(name=name) + (" " if idx < 9 and len(list_cpus) > 9 else "")
        linear_gauge(
            stdscr, offset=int(offest + off_idx), start=start, size=max_bar,
            name=GaugeName(name, color=curses.color_pair(6)),
            value=cpu.get('val', 0),
            status='ON' if cpu else 'OFF',
            percent=percent,
            label=label_freq(cpu['frq'], start='k') if 'frq' in cpu else '')
    # Size block CPU
    return int(offest + idx / 2 + 1) if len(list_cpus) > 4 else int(offest + idx + 1)


@check_curses
def plot_GPUs(stdscr, offest, list_gpus, width):
    # list_gpus = {1: list_gpus[1]}
    max_bar = int(float(width) / 2.0)
    for idx, name in enumerate(sorted(list_gpus)):
        gpu = list_gpus[name]
        # Split in double list
        start = max_bar if idx >= len(list_gpus) / 2 else 0
        off_idx = idx - len(list_gpus) / 2 if idx >= len(list_gpus) / 2 else idx
        # Show linear gauge
        name = "GPU{name}".format(name=name) if len(list_gpus) > 1 else "GPU"
        linear_gauge(
            stdscr, offset=int(offest + off_idx), start=start, size=max_bar if len(list_gpus) > 1 else width,
            name=GaugeName(name, color=curses.color_pair(6)),
            value=gpu.get('val', 0),
            label=label_freq(gpu['frq'], start='k'))
    # Size block CPU
    return int(offest + idx / 2)


@check_curses
def plot_temperatures(stdscr, start, offset, width, height, jetson):
    counter = 0
    start = start + (width - 17) // 2
    # Define color temperatures
    color_options = {
        60: curses.color_pair(1),
        40: curses.color_pair(3),
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
    stdscr.addstr(offset, start + (width - 7) // 2, " [info] ", curses.A_BOLD)
    counter = 1
    # Model board information
    uptime_string = strfdelta(jetson.uptime, "{days} days {hours}:{minutes}:{seconds}")
    plot_name_info(stdscr, offset + counter, start + 1, "UpT", uptime_string)
    counter += 1
    # FAN status
    if jetson.fan.all_speed().items():
        for fan, speed in jetson.fan.all_speed().items():
            ctrl = "Ta" if jetson.fan.auto else "Tm"
            label = "{ctrl}={target: >3.0f}%".format(ctrl=ctrl, target=speed)
            linear_gauge(
                stdscr,
                offset=offset + counter, start=start + 1, size=width,
                name=GaugeName('FAN', color=curses.color_pair(6)),
                value=speed,
                status='ON' if jetson.fan else 'DISABLED',
                label=label)
            counter += 1
    else:
        linear_gauge(
            stdscr,
            offset=offset + counter, start=start + 1, size=width,
            name=GaugeName('FAN', color=curses.color_pair(6)),
            status='DISABLED')
        counter += 1
    # Jetson clocks status: Running (Green) or Normal (Grey)
    jetson_clocks_gui(stdscr, offset + counter, start + 1, jetson)
    counter += 1
    # NVP Model
    if jetson.nvpmodel is not None:
        nvp_model_gui(stdscr, offset + counter, start + 1, jetson)
        counter += 1
    # Write all engines
    counter += compact_engines(stdscr, start, offset + counter, width, jetson)
    return counter
# EOF
