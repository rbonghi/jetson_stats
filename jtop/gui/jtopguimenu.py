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
from .lib.common import (check_curses,
                         strfdelta,
                         label_freq,
                         plot_name_info,
                         size_min)
from .lib.linear_gauge import linear_gauge, GaugeName
from ..core.jetson_clocks import JetsonClocks


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
                     name=GaugeName(cpu['name'], color=curses.color_pair(6)),
                     value=cpu.get('val', 0),
                     status=cpu['status'],
                     percent=percent,
                     label=label_freq(cpu))
    if len(list_cpus) > 4:
        return int(offest + idx / 2 + 1)
    else:
        return int(offest + idx + 1)


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
        stdscr.addstr(offset + idx + 1, start + offset // 2 + 3, ("{val:8.2f}C").format(val=value), color)


@check_curses
def plot_watts(stdscr, start, offset, width, height, jetson):
    # List of all watts
    watts = deepcopy(jetson.stats['WATT'])
    # In according with:
    # https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8
    # https://github.com/rbonghi/jetson_stats/issues/51
    total_name = ""
    for val in watts:
        if "_IN" in val:
            total_name = val
            break
    # Extract the total from list
    # Otherwise sum all values
    # Example for Jetson Xavier
    # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
    if total_name:
        total = watts[total_name]
        del watts[total_name]
    else:
        total = {'cur': 0, 'avg': 0}
    # Plot title
    center_column = width // 2
    stdscr.addstr(offset, start, " [Power/mW] ", curses.A_BOLD)
    stdscr.addstr(offset, start + center_column - 1, " [Cur] ", curses.A_BOLD)
    stdscr.addstr(offset, start + width - 8, " [Avr] ", curses.A_BOLD)
    # Plot watts
    for idx, watt in enumerate(sorted(watts)):
        value = jetson.stats['WATT'][watt]
        watt_name = watt.replace("VDD_", "").replace("POM_", "").replace("_", " ")
        if not total_name:
            total['cur'] += int(value['cur'])
            total['avg'] += int(value['avg'])
        stdscr.addstr(offset + idx + 1, start + 1, watt_name, curses.A_NORMAL)
        stdscr.addstr(offset + idx + 1, start + center_column, str(value['cur']), curses.A_NORMAL)
        stdscr.addstr(offset + idx + 1, start + width - 7, str(value['avg']), curses.A_NORMAL)
    # Fix total_name if empty
    if not total_name:
        total_name = "Total"
    else:
        total_name = total_name.replace("VDD_", "").replace("POM_", "").replace("_", " ")
    # Plot totals before finishing
    stdscr.addstr(offset + idx + 2, start + 1, total_name, curses.A_BOLD)
    stdscr.addstr(offset + idx + 2, start + center_column, str(total['cur']), curses.A_BOLD)
    stdscr.addstr(offset + idx + 2, start + width - 7, str(total['avg']), curses.A_BOLD)


@check_curses
def compact_info(stdscr, start, offset, width, height, jetson):
    # Title menu
    stdscr.addstr(offset, start + (width - 7) // 2, " [info] ", curses.A_BOLD)
    counter = 1
    # Model board information
    uptime_string = strfdelta(timedelta(seconds=jetson.uptime), "{days} days {hours}:{minutes}:{seconds}")
    plot_name_info(stdscr, offset + counter, start + 1, "UpT", uptime_string)
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
        linear_gauge(stdscr, offset=offset + counter, start=start + 1, size=width,
                     name=GaugeName('FAN', color=curses.color_pair(6)),
                     value=value,
                     label=label,
                     status=fan['status'])
    else:
        stdscr.hline(offset + counter, start + 1, curses.ACS_BLOCK, width, curses.color_pair(3))
        stdscr.addstr(offset + counter, start + (width - 8) // 2, " NO FAN ", curses.color_pair(3))
    counter += 1
    # Jetson clocks status
    jc = jetson.jetson_clocks
    if jc is not None:
        jc_service = jc.service
        jc_enable = jc.enable
        try:
            jc_status = jc.status
            # Running (Green) or Normal (Grey)
            color = curses.color_pair(2) if jc_status else curses.A_NORMAL
            # Write status jetson_clocks
            jc_status_name = "Running" if jc_status else "Stopped"
            # Specify the service running
            if jc_service == "active":
                jc_status_name += "+"
            # Show if JetsonClock is enabled or not
            if jc_enable:
                jc_status_name = "[" + jc_status_name + "]"
        except JetsonClocks.JCException:
            # Fix error color
            color = curses.color_pair(11)
            # SUDO SUGGESTED is too long, change with a series of spaces
            # The number 16 = len("jetson clocks: ") + 1
            jc_status_name = (width - 16) * " "
        # Show status jetson_clocks
        plot_name_info(stdscr, offset + counter, start + 1, "Jetson clocks", jc_status_name, color)
        counter += 1
    # NVP Model
    nvpmodel = jetson.nvpmodel
    if nvpmodel is not None:
        plot_name_info(stdscr, offset + counter, start + 1, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
        counter += 1
    # Write all engines
    engines(stdscr, start, offset + counter, width, height, jetson)


def engines(stdscr, start, offset, width, height, jetson):
    stdscr.hline(offset, start + 1, curses.ACS_HLINE, width - 1)
    stdscr.addstr(offset, start + (width - 13) // 2, " [HW engines] ", curses.A_BOLD)
    counter = 1
    # APE frequency
    if 'APE' in jetson.stats:
        plot_name_info(stdscr, offset + counter, start + 1, "APE", str(jetson.stats['APE']['val']) + "MHz")
        counter += 1
    # Find encoders
    if 'NVENC' in jetson.stats:
        enc_name = 'NVENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.stats['NVENC']['val'], unit="M")
    elif 'MSENC' in jetson.stats:
        enc_name = 'MSENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.stats['MSENC']['val'], unit="M")
    else:
        enc_name = 'NVENC'
        enc_val = "[OFF]"
    # Find decoders
    if 'NVDEC' in jetson.stats:
        dec_name = 'NVDEC'
        dec_val = "{value}{unit}Hz".format(value=jetson.stats['NVDEC']['val'], unit="M")
    else:
        dec_name = 'NVDEC'
        dec_val = "[OFF]"
    double_info(stdscr, start + 1, offset + counter, width, (enc_name, enc_val), (dec_name, dec_val))
    counter += 1
    # NVJPG
    nvjpg = jetson.nvjpg
    if nvjpg:
        status = nvjpg['status']
        if status:
            value, _, unit = size_min(nvjpg['rate'])
            value = "{value}{unit}Hz".format(value=value, unit=unit)
        else:
            value = "[OFF]"
        # Plot status
        plot_name_info(stdscr, offset + counter, start + 1, "NVJPG", value)


def double_info(stdscr, start, offset, width, enc, dec):
    plot_name_info(stdscr, offset, start, enc[0], enc[1])
    plot_name_info(stdscr, offset, start + width // 2, dec[0], dec[1])
# EOF
