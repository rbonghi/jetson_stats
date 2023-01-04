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
    counter += engines(stdscr, start, offset + counter, width, height, jetson)
    return counter


def engines(stdscr, start, offset, width, height, jetson):
    stdscr.hline(offset, start + 1, curses.ACS_HLINE, width - 1)
    stdscr.addstr(offset, start + (width - 13) // 2, " [HW engines] ", curses.A_BOLD)
    counter = 1
    # DLA0 - DLA1
    # NVJPG0 - NVJPG1
    # NVDEC - NVENC
    # APE - SE
    # PVA

    # DLA engines
    dla0_val_string = '[OFF]'
    if 'DLA0' in jetson.engine:
        if jetson.engine['DLA0']['core'].status:
            dla0_val = jetson.engine['DLA0']['core'].frequency
            dla0_val, _, unit = size_min(dla0_val, start='M')
            dla0_val_string = "{value}{unit}Hz".format(value=dla0_val, unit=unit)
    dla1_val_string = '[OFF]'
    if 'DLA1' in jetson.engine:
        if jetson.engine['DLA1']['core'].status:
            dla1_val = jetson.engine['DLA1']['core'].frequency
            dla1_val, _, unit = size_min(dla1_val, start='M')
            dla1_val_string = "{value}{unit}Hz".format(value=dla1_val, unit=unit)
    double_info(stdscr, start + 1, offset + counter, width, ('DLA0', dla0_val_string), ('DLA1', dla1_val_string), spacing=2)
    counter += 1
    # NVJPG engines
    nvjpg0_val_string = '[OFF]'
    if 'NVJPG' in jetson.engine:
        if jetson.engine['NVJPG'].status:
            nvjpg0_val = jetson.engine['NVJPG'].frequency
            nvjpg0_val, _, unit = size_min(nvjpg0_val, start='M')
            nvjpg0_val_string = str(nvjpg0_val).rstrip('0').rstrip('.')
            nvjpg0_val_string = "{value}{unit}Hz".format(value=nvjpg0_val_string, unit=unit)
    nvjpg1_val_string = '[OFF]'
    if 'NVJPG1' in jetson.engine:
        if jetson.engine['NVJPG1'].status:
            nvjpg1_val = jetson.engine['NVJPG1'].frequency
            nvjpg1_val, _, unit = size_min(nvjpg1_val, start='M')
            nvjpg1_val_string = str(nvjpg1_val).rstrip('0').rstrip('.')
            nvjpg1_val_string = "{value}{unit}Hz".format(value=nvjpg1_val_string, unit=unit)
    double_info(stdscr, start + 1, offset + counter, width, ('NVJPG0', nvjpg0_val_string), ('NVJPG1', nvjpg1_val_string))
    counter += 1
    # Find encoders
    if 'MSENC' in jetson.engine:
        enc_name = 'MSENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.engine['MSENC'].frequency, unit="M")
    elif jetson.engine['NVENC'].status:
        enc_name = 'NVENC'
        enc_val = "{value}{unit}Hz".format(value=jetson.engine['NVENC'].frequency, unit="M")
    else:
        enc_name = 'NVENC'
        enc_val = "[OFF]"
    # Find decoders
    if jetson.engine['NVDEC'].status:
        dec_val = "{value}{unit}Hz".format(value=jetson.engine['NVDEC'].frequency, unit="M")
    else:
        dec_val = "[OFF]"
    double_info(stdscr, start + 1, offset + counter, width, (enc_name, enc_val), ('NVDEC', dec_val), spacing=1)
    counter += 1
    # APE frequency
    ape_val_string = "[OFF]"
    se_val_string = "[OFF]"
    if 'APE' in jetson.engine:
        ape_val, _, unit = size_min(jetson.engine['APE'].frequency, start='M')
        ape_val_string = str(ape_val).rstrip('0').rstrip('.')
        ape_val_string = "{value}{unit}Hz".format(value=ape_val_string, unit=unit)
    if 'SE' in jetson.engine:
        se_val, _, unit = size_min(jetson.engine['SE'].frequency, start='M')
        se_val_string = str(se_val).rstrip('0').rstrip('.')
        se_val_string = "{value}{unit}Hz".format(value=se_val_string, unit=unit)
    double_info(stdscr, start + 1, offset + counter, width, ("APE", ape_val_string), ("SE", se_val_string), spacing=1)
    counter += 1
    pva0_val_string = "[OFF]"
    vic_val_string = "[OFF]"
    if 'PVA0' in jetson.engine:
        pva0_val, _, unit = size_min(jetson.engine['PVA0']['vps0'].frequency, start='M')
        pva0_val_string = str(pva0_val).rstrip('0').rstrip('.')
        pva0_val_string = "{value}{unit}Hz".format(value=pva0_val_string, unit=unit)
    if 'VIC' in jetson.engine:
        vic_val, _, unit = size_min(jetson.engine['VIC'].frequency, start='M')
        vic_val_string = str(vic_val).rstrip('0').rstrip('.')
        vic_val_string = "{value}{unit}Hz".format(value=vic_val_string, unit=unit)
    double_info(stdscr, start + 1, offset + counter, width, ("PVA0", pva0_val_string), ("VIC", vic_val_string))
    return counter + 1


def double_info(stdscr, start, offset, width, enc, dec, spacing=0):
    plot_name_info(stdscr, offset, start, enc[0], enc[1], spacing=spacing)
    plot_name_info(stdscr, offset, start + width // 2, dec[0], dec[1], spacing=spacing)
# EOF
