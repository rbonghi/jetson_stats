#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (C) 2018, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its 
#    contributors may be used to endorse or promote products derived 
#    from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, 
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
    Graphic reference:
    http://urwid.org/examples/index.html
    https://npyscreen.readthedocs.io/
    https://github.com/chubin/cheat.sh
    
    https://stackoverflow.com/questions/6840420/python-rewrite-multiple-lines-in-the-console
    
    https://docs.python.org/3.3/howto/curses.html#attributes-and-color
"""
# control command line
import curses
# Launch command
import subprocess
# read tegrastats
from jstatslib import get_status
# Systema and signal
import signal, os, sys

def signal_handler(sig, frame):
    """
        Close the system when catch SIGIN (CTRL-C)
    """
    sys.exit(0)

def make_gauge_from_percent(data):
    gauge = {'name': data['name']}
    if 'idle' in data:
        gauge['value'] = int(data['idle'])
    if 'frequency' in data:
        if data['frequency'] >= 1000:
            gauge['label'] = "{0:2.1f}GHz".format(data['frequency']/1000.0)
        else:
            gauge['label'] = str(int(data['frequency'])) + "MHz"
    return gauge
    
def linear_percent_gauge(gauge, max_bar, offset=0, start=0, type_bar="|", color_name=6):
    # Evaluate size withuout short name
    size_bar = max_bar - 8
    if 'value' in gauge:
        value = gauge['value']
        # Show short name linear gauge
        stdscr.addstr(offset, start + 0, ("{short_name:4}").format(short_name=gauge['name']), curses.color_pair(color_name))
        # Show bracket linear gauge and label and evaluate size withuout size labels and short name
        size_bar -= (len(gauge['label']) + 1) if 'label' in gauge else 0
        stdscr.addstr(offset, start + 5, "[" + " " * size_bar + "]", curses.A_BOLD)
        if 'label' in gauge:
            stdscr.addstr(offset, start + 5 + size_bar + 3, gauge['label'])
        # Show progress value linear gauge
        n_bar = int(float(value) * float(size_bar) / 100.0)
        progress_bar= type_bar * n_bar
        # Build progress barr string
        str_progress_bar = ("{n_bar:" + str(size_bar) + "}").format(n_bar=progress_bar)
        percent_label = gauge['percent'] if 'percent' in gauge else str(value) + "%"
        str_progress_bar = str_progress_bar[:size_bar - len(percent_label)] + percent_label
        # Split string in green and grey part
        green_part = str_progress_bar[:n_bar]
        grey_part = str_progress_bar[n_bar:]
        stdscr.addstr(offset, start + 6, green_part, curses.color_pair(2))
        stdscr.addstr(offset, start + 6 + size_bar - len(grey_part), grey_part, curses.A_DIM)
    else:
        # Show short name linear gauge
        stdscr.addstr(offset, start + 0, ("{short_name:4}").format(short_name=gauge['name']), curses.color_pair(color_name))
        # Show bracket linear gauge and label
        stdscr.addstr(offset, start + 5, ("[{value:>" + str(size_bar) + "}]").format(value=" "))
        # Show bracket linear gauge and label
        stdscr.addstr(offset, start + 7, "OFF", curses.color_pair(1))

def plot_CPUs(offest, list_cpus, width):
    max_bar = int(float(width)/2.0)
    for idx, cpu in enumerate(list_cpus):
        # Split in double list
        start = max_bar + 1 if idx >= len(list_cpus)/2 and len(list_cpus) > 4 else 0
        off_idx = idx - len(list_cpus)/2 if idx >= len(list_cpus)/2 and len(list_cpus) > 4 else idx
        # Plot the linear gauge
        gauge = make_gauge_from_percent(cpu)
        if 'value' in gauge:
            gauge["percent"] = cpu['governor'] + " - " + str(gauge['value']) + "%"
        linear_percent_gauge(gauge, max_bar, offest+off_idx, start)
    if len(list_cpus) > 4:
        return offest + idx/2 + 1
    else:
        return offest + idx + 1

def plot_dictionary(offset, data, name, start=0):
    # Plot title
    stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
    counter = 1
    for key, value in data.items():
        if 'text' in value:
            stdscr.addstr(offset + counter, start, " {0:<10} {1}".format(key, value['text']))
        else:
            stdscr.addstr(offset + counter, start, " {0:<10} {1}".format(key, value))
        counter += 1
        
def plot_temperatures(offset, data, start=0):
    # Plot title
    stdscr.addstr(offset, start, " {0:<10} {1}".format("[Sensor]", "[Temp]"), curses.A_BOLD)
    counter = 1
    for key, value in data.items():
        stdscr.addstr(offset + counter, start, "{0:<10} {1:>4.2f}{2}".format(key, value['value'], value['unit']))
        counter += 1
        
def plot_voltages(offset, data, start=0):
    # Plot title
    stdscr.addstr(offset, start, " {0:<10} {1}".format("[Power]", " [Cur/Avr]"), curses.A_BOLD)
    counter = 1
    for key, value in data.items():
        stdscr.addstr(offset + counter, start, "{0:<10} {1:^4}mW/{2:^4}mW".format(key, value['current'], value['average']))
        counter += 1
        
def plot_name_info(offset, start, name, value):
    stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
    stdscr.addstr(offset, start + len(name) + 2, value)
        
def plot_other_info(offset, data, width, start=0):
    counter = 0
    # APE frequency
    plot_name_info(offset + counter, start, "APE", str(jetsonstats['APE']) + "MHz")
    counter +=1
    # FAN status
    if 'FAN' in jetsonstats:
        FAN_VALUE = { 'name': 'FAN',
                      'value': int(jetsonstats['FAN']),
                    }
        linear_percent_gauge(FAN_VALUE, width, offset=offset + counter, start= start)
        counter +=1
    # Plot MTS
    if 'MTS' in jetsonstats:
        stdscr.addstr(offset + counter, start, "MTS:", curses.A_BOLD)
        MTS_FG = { 'name': ' FG',
                      'value': int(jetsonstats['MTS']['fg']),
                    }
        linear_percent_gauge(MTS_FG, width, offset=offset + counter + 1, start= start)
        MTS_BG = { 'name': ' BG',
                      'value': int(jetsonstats['MTS']['bg']),
                    }
        linear_percent_gauge(MTS_BG, width, offset=offset + counter + 2, start= start)
        counter += 3
    # Model board information
    stdscr.addstr(offset + counter, start, "Board info:", curses.A_BOLD)
    plot_name_info(offset + counter + 1, start + 2, "Name", os.environ["JETSON_BOARD"])
    plot_name_info(offset + counter + 2, start + 2, "JP", os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]")
    counter += 3
    # NVP Model
    if 'NVPMODEL' in jetsonstats:
        plot_name_info(offset + counter, start, "NV Power", jetsonstats['NVPMODEL']['name'] + " - " + str(jetsonstats['NVPMODEL']['mode']))
        counter += 1

def refreshwindow(jetsonstats):
    """
        Update screen with values
    """
    # Clear screen
    stdscr.clear()
    line_counter = 0
    height, width = stdscr.getmaxyx()
    
    stdscr.addstr(line_counter, 0, "jtop - Raffaello Bonghi", curses.A_BOLD)
    stdscr.addstr(line_counter + 1, 0, os.environ["JETSON_DESCRIPTION"] + " - Jetpack " + os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]", curses.A_BOLD)
    line_counter +=2
    max_bar = int(float(width)/2.0)
    
    # Plot Status CPU
    line_counter = plot_CPUs(line_counter, jetsonstats['CPU'], width)
    # RAM linear gauge info
    ram_status = jetsonstats['RAM']['RAM']
    lfb_status = jetsonstats['RAM']['lfb']
    RAM_VALUE = { 'name': "Mem", 
                  'value': int(float(ram_status['used'])/float(ram_status['total']) * 100.0),
                  'label': "(lfb " + str(lfb_status['nblock']) + "x" + str(lfb_status['size']) + "MB)",
                  'percent': "{0:2.1f}GB/{1:2.1f}GB".format(ram_status['used']/1000.0, ram_status['total']/1000.0),
                }
    linear_percent_gauge(RAM_VALUE, width, offset=line_counter + 1)
    # EMC linear gauge info
    linear_percent_gauge(make_gauge_from_percent(jetsonstats['EMC']), width, offset=line_counter + 2)
    # IRAM linear gauge info
    iram_status = jetsonstats['IRAM']
    if iram_status:
        line_counter += 1
        IRAM_VALUE = { 'name': "Imm", 
                      'value': int(float(iram_status['used'])/float(iram_status['total']) * 100.0),
                      'label': "(lfb " + str(iram_status['size']) + "MB)",
                      'percent': "{0:2.1f}GB/{1:2.1f}GB".format(iram_status['used']/1000.0, iram_status['total']/1000.0),
                    }
        linear_percent_gauge(IRAM_VALUE, width, offset=line_counter + 2)
    # SWAP linear gauge info
    swap_status = jetsonstats['SWAP']
    if swap_status:
        SWAP_VALUE = { 'name': "Swp", 
                       'value': int(float(swap_status['used'])/float(swap_status['total']) * 100.0),
                       'label': "(cached " + str(swap_status['cached']) + "MB)",
                       'percent': "{0:2.1f}GB/{1:2.1f}GB".format(swap_status['used']/1000.0, swap_status['total']/1000.0),
                    }
    else:
        SWAP_VALUE = {'name': "Swp"}
    linear_percent_gauge(SWAP_VALUE, width, offset=line_counter + 3)
    line_counter += 4
    # GPU linear gauge info
    linear_percent_gauge(make_gauge_from_percent(jetsonstats['GR3D']), width, offset=line_counter + 1)
    line_counter += 2
    # Status disk
    #line_counter += 1
    disk_status = jetsonstats['DISK']
    DISK_STATUS = { 'name': "Dsk", 
                  'value': int(float(disk_status['used'])/float(disk_status['total']) * 100.0),
                  'percent': "{0:2.1f}GB/{1:2.1f}GB".format(disk_status['used'], disk_status['total']),
                }
    linear_percent_gauge(DISK_STATUS, width, offset=line_counter, type_bar="#", color_name=3)
    
    
    split = 1.0
    split += 1.0 if jetsonstats['temperatures'] else 0.0
    split += 1.0 if jetsonstats['voltages'] else 0.0
    column_width = int(float(width - 4)/split)
    line_counter += 1
    # Add temperatures and voltages
    plot_other_info(line_counter, jetsonstats, column_width, start=1)
    if jetsonstats['temperatures']:
        plot_temperatures(line_counter, jetsonstats['temperatures'], start=2 + column_width)
    if jetsonstats['voltages']:
        plot_voltages(line_counter, jetsonstats['voltages'], start= 2 + 2*column_width)
    # Close option menu
    stdscr.addstr(height-1, 0, ("{0:<" + str(width-1) + "}").format("CTRL-C to close"), curses.A_REVERSE)
    # Refresh page
    stdscr.refresh()
    
import re
if __name__ == "__main__":
    # Check if the system work in sudo
    if os.getuid() != 0:
        print("Run with sudo")
        sys.exit(0)
    sys.stdout.write('Loading...')
    sys.stdout.flush()
    # Load command line controller
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.cbreak()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    # Catch SIGINT (CTRL-C)
    signal.signal(signal.SIGINT, signal_handler)
    # Open tegrastats
    p = subprocess.Popen(['/usr/bin/tegrastats', '--interval', '100'], stdout=subprocess.PIPE)
    # launch reader
    try:
        while p.poll() is None:
            # This blocks until it receives a newline.
            tegrastats_stream = p.stdout.readline().decode("utf-8")
            # read status from fan
            if os.path.isfile('/sys/kernel/debug/tegra_fan/target_pwm'):
                fan_status_p = subprocess.Popen(['cat', '/sys/kernel/debug/tegra_fan/target_pwm'], stdout=subprocess.PIPE)
                fan_level = int(fan_status_p.communicate()[0])
            else:
                fan_level = None
            # Rad nvpmodel to know the status of the board
            try:
                nvpmodel_p = subprocess.Popen(['nvpmodel', '-q'], stdout=subprocess.PIPE)
                nvpmodel = nvpmodel_p.communicate()[0]
            except:
                nvpmodel = ""
            # Build status of jetson
            jetsonstats = get_status(tegrastats_stream, fan_level, nvpmodel)
            # Refresh window
            refreshwindow(jetsonstats)
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
