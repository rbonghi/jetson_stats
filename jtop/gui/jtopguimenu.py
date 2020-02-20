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


from copy import deepcopy
from datetime import timedelta
# control command line
import curses
# Graphics elements
from .jtopguilib import (check_curses,
                         strfdelta,
                         linear_gauge,
                         label_freq,
                         plot_name_info)


@check_curses
def plot_CPUs(stdscr, offest, list_cpus, width):
    max_bar = int(float(width) / 2.0)
    for idx, cpu in enumerate(list_cpus):
        # Split in double list
        start = max_bar if idx >= len(list_cpus) / 2 and len(list_cpus) > 4 else 0
        off_idx = idx - len(list_cpus) / 2 if idx >= len(list_cpus) / 2 and len(list_cpus) > 4 else idx
        # Check if exist governor and add in percent name
        percent = ""
        if 'val' in cpu and 'governor' in cpu:
            percent = "{gov} -{val: 4}%".format(gov=cpu['governor'].capitalize(), val=cpu['val'])
        # Show linear gauge
        linear_gauge(stdscr, offset=int(offest + off_idx), start=start, size=max_bar,
                     name=cpu['name'], value=cpu.get('val', 0), status=cpu['status'], percent=percent, label=label_freq(cpu),
                     color=curses.color_pair(6))
    if len(list_cpus) > 4:
        return int(offest + idx / 2 + 1)
    else:
        return int(offest + idx + 1)


@check_curses
def plot_temperatures(stdscr, start, offset, width, jetson):
    # Define color temperatures
    color_options = {
        60: curses.color_pair(1),
        40: curses.color_pair(3),
        20: curses.A_NORMAL,
    }
    list_options = sorted(color_options.keys(), reverse=True)
    # Plot title
    stdscr.addstr(offset, start, ("{name:<9} {val:^8}").format(name="[Sensor]", val="[Temp]"), curses.A_BOLD)
    # Plot name and temperatures
    temps = deepcopy(jetson.stats['TEMP'])
    if 'PMIC' in temps:
        del temps['PMIC']
    for idx, temp in enumerate(sorted(temps)):
        # Print temperature name
        value = jetson.stats['TEMP'][temp]
        stdscr.addstr(offset + idx + 1, start, ("{name:<7}").format(name=temp))
        # Set color temperature
        color = curses.A_NORMAL
        for k in list_options:
            if value >= k:
                color = color_options[k]
                break
        # Print temperature value
        stdscr.addstr(offset + idx + 1, start + offset // 2 + 2, ("{val:8.2f}C").format(val=value), color)


@check_curses
def plot_voltages(stdscr, start, offset, width, jetson):
    # Plot title
    stdscr.addstr(offset, start, "{name:<12} [Cur]   [Avr]".format(name="[Power/mW]"), curses.A_BOLD)
    # Add Variable to keep track of total
    total_avg = 0
    total_cur = 0
    # Plot voltages
    for idx, volt in enumerate(sorted(jetson.stats['VOLT'])):
        value = jetson.stats['VOLT'][volt]
        total_cur += int(value['cur'])
        total_avg += int(value['avg'])
        stdscr.addstr(offset + idx + 1, start,
                      ("{name:<12} {curr: <7} {avg: <7}").format(name=volt, curr=int(value['cur']), avg=int(value['avg'])))
    # Plot totals before finishing
    stdscr.addstr(offset + idx + 2, start,
                  ("{name:<12} {curr: <7} {avg: <7}").format(name="Total", curr=total_cur, avg=total_avg), curses.A_BOLD)


@check_curses
def compact_info(stdscr, start, offset, width, jetson):
    # Title menu
    stdscr.addstr(offset, start, ("{name: ^" + str(width) + "}").format(name="[info]"), curses.A_BOLD)
    counter = 1
    # Model board information
    uptime_string = strfdelta(timedelta(seconds=jetson.uptime), "{days} days {hours}:{minutes}:{seconds}")
    plot_name_info(stdscr, offset + counter, start, "UpT", uptime_string)
    counter += 1
    # FAN status
    if "FAN" in jetson.stats:
        fan = jetson.stats["FAN"]
        if 'cpwm' in fan:
            if 'ctrl' in fan:
                ctrl = "Ta" if fan.get("ctrl", False) else "Tm"
            else:
                ctrl = "T"
            label = "{ctrl}={target: >3}%".format(ctrl=ctrl, target=fan.get("tpwm", 0))
            value = fan.get('cpwm', 0)
        else:
            label = ''
            value = fan.get('tpwm', 0)
        linear_gauge(stdscr, offset=offset + counter, start=start, size=width,
                     name='FAN',
                     value=value,
                     label=label,
                     status=fan['status'],
                     color=curses.color_pair(6))
    else:
        stdscr.addstr(offset + counter, 0, "NO FAN", curses.color_pair(3))
    counter += 1
    # Jetson clocks status
    jc = jetson.jetson_clocks
    if jc is not None:
        jc_status = jc.status
        if jc_status == "active":
            color = curses.color_pair(2)  # Running (Green)
        elif jc_status == "inactive":
            color = curses.A_NORMAL       # Normal (Grey)
        elif "ing" in jc_status:
            color = curses.color_pair(3)  # Warning (Yellow)
        else:
            color = curses.color_pair(1)  # Error (Red)
        # Show if JetsonClock is enabled or not
        if jc.enable:
            jc_status = "[" + jc_status + "]"
        plot_name_info(stdscr, offset + counter, start, "Jetson clocks Sv", jc_status, color)
        counter += 1
    # NVP Model
    nvpmodel = jetson.nvpmodel
    if nvpmodel is not None:
        plot_name_info(stdscr, offset + counter, start, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
        counter += 1
    # APE frequency
    if 'APE' in jetson.stats:
        plot_name_info(stdscr, offset + counter, start, "APE", str(jetson.stats['APE']['val']) + "MHz")
        counter += 1
    # NVENC frequency
    stdscr.addstr(offset + counter, start, "HW engine:", curses.A_BOLD)
    counter += 1
    if 'NVENC' in jetson.stats:
        plot_name_info(stdscr, offset + counter, start, " ENC", str(jetson.stats['NVENC']['val']) + "MHz")
    else:
        plot_name_info(stdscr, offset + counter, start, " ENC", "NOT RUNNING")
    counter += 1
    # NVDEC frequency
    if 'NVDEC' in jetson.stats:
        plot_name_info(stdscr, offset + counter, start, " DEC", str(jetson.stats['NVDEC']['val']) + "MHz")
    else:
        plot_name_info(stdscr, offset + counter, start, " DEC", "NOT RUNNING")
    counter += 1
    if 'MSENC' in jetson.stats:
        plot_name_info(stdscr, offset + counter, start, " ENC", str(jetson.stats['MSENC']['val']) + "MHz")
# EOF
