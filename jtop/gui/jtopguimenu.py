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


# control command line
import curses
# Graphics elements
from .lib.common import (check_curses,
                         strfdelta,
                         plot_name_info,
                         size_min,
                         label_freq,
                         jetson_clocks_gui,
                         nvp_model_gui)
from .lib.linear_gauge import linear_gauge, GaugeName


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
def plot_temperatures(stdscr, start, offset, width, height, jetson):
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
        stdscr.addstr(offset + idx + 1, start, ("{name:<7}").format(name=name))
        # Set color temperature
        color = curses.A_NORMAL
        for k in list_options:
            if value >= k:
                color = color_options[k]
                break
        # Print temperature value
        stdscr.addstr(offset + idx + 1, start + offset // 2 + 3, ("{val:8.2f}C").format(val=value), color)


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
    stdscr.addstr(offset + idx + 2, start - 10, 'ALL', curses.A_BOLD)
    stdscr.addstr(offset + idx + 2, start + 3, str(total['cur']), curses.A_BOLD)
    stdscr.addstr(offset + idx + 2, start + 10, str(total['avg']), curses.A_BOLD)


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
    ctrl = "Ta" if jetson.fan.auto else "Tm"
    if jetson.fan.speed is not None:
        label = "{ctrl}={target: >3.0f}%".format(ctrl=ctrl, target=jetson.fan.speed)
    else:
        label = "{ctrl}".format(ctrl=ctrl)
    linear_gauge(
        stdscr,
        offset=offset + counter, start=start + 1, size=width,
        name=GaugeName('FAN', color=curses.color_pair(6)),
        value=jetson.fan.get('measure', 0),
        status='ON' if jetson.fan else 'DISABLED',
        label=label)
    counter += 1
    # Jetson clocks status: Running (Green) or Normal (Grey)
    jetson_clocks_gui(stdscr, offset + counter, start + 1, jetson)
    counter += 1
    # NVP Model
    if jetson.nvpmodel is not None:
        nvp_model_gui(stdscr, offset + counter, start + 1, jetson)
        counter += 1
    # Write all engines
    engines(stdscr, start, offset + counter, width, height, jetson)


def engines(stdscr, start, offset, width, height, jetson):
    stdscr.hline(offset, start + 1, curses.ACS_HLINE, width - 1)
    stdscr.addstr(offset, start + (width - 13) // 2, " [HW engines] ", curses.A_BOLD)
    counter = 1
    # APE frequency
    if jetson.engine.ape:
        plot_name_info(stdscr, offset + counter, start + 1, "APE", str(jetson.engine.ape['val']) + "MHz")
        counter += 1
    # Find encoders
    if jetson.engine.nvenc:
        enc_name = 'NVENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.engine.nvenc['val'], unit="M")
    elif jetson.engine.msenc:
        enc_name = 'MSENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.engine.msenc['val'], unit="M")
    else:
        enc_name = 'NVENC'
        enc_val = "[OFF]"
    # Find decoders
    if jetson.engine.nvdec:
        dec_name = 'NVDEC'
        dec_val = "{value}{unit}Hz".format(value=jetson.engine.nvdec['val'], unit="M")
    else:
        dec_name = 'NVDEC'
        dec_val = "[OFF]"
    double_info(stdscr, start + 1, offset + counter, width, (enc_name, enc_val), (dec_name, dec_val))
    counter += 1
    # NVJPG
    if jetson.engine.nvjpg is not None:
        if jetson.engine.nvjpg:
            value, _, unit = size_min(jetson.engine.nvjpg)
            value = "{value}{unit}Hz".format(value=value, unit=unit)
        else:
            value = "[OFF]"
        # Plot status
        plot_name_info(stdscr, offset + counter, start + 1, "NVJPG", value)


def double_info(stdscr, start, offset, width, enc, dec):
    plot_name_info(stdscr, offset, start, enc[0], enc[1])
    plot_name_info(stdscr, offset, start + width // 2, dec[0], dec[1])
# EOF
