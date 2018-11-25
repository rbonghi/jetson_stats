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
from jtop.jstatslib import get_status
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
    
def linear_percent_gauge(gauge, max_bar, offset=0, start=0):
    # Evaluate size withuout short name
    size_bar = max_bar - 8
    if 'value' in gauge:
        value = gauge['value']
        # Show short name linear gauge
        stdscr.addstr(offset, start + 0, ("{short_name:4}").format(short_name=gauge['name']), curses.color_pair(6))
        # Show bracket linear gauge and label and evaluate size withuout size labels and short name
        size_bar -= (len(gauge['label']) + 1) if 'label' in gauge else 0
        stdscr.addstr(offset, start + 5, "[" + " " * size_bar + "]")
        if 'label' in gauge:
            stdscr.addstr(offset, start + 5 + size_bar + 3, gauge['label'])
        # Show progress value linear gauge
        n_bar = int(float(value) * float(size_bar - 2) / 100.0)
        progress_bar= "|" * n_bar
        stdscr.addstr(offset, start + 6, ("{n_bar:" + str(size_bar - 2) + "}").format(n_bar=progress_bar), curses.color_pair(2))
        # Show value inside linear gauge
        percent_label = gauge['percent'] if 'percent' in gauge else str(value) + "%"
        stdscr.addstr(offset, start + 6 + size_bar - len(percent_label), percent_label)
    else:
        # Show short name linear gauge
        stdscr.addstr(offset, start + 0, ("{short_name:4}").format(short_name=gauge['name']), curses.color_pair(6))
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
        linear_percent_gauge(make_gauge_from_percent(cpu), max_bar, offest+off_idx, start)
    return offest + idx/2 + 1

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
    #max_bar = int(float(width - 20)/2.0)
    max_bar = int(float(width)/2.0)
    
    # Plot Status CPU
    line_counter = plot_CPUs(line_counter, jetsonstats['CPU'], width)
    # RAM and EMC linear gauge info
    ram_status = jetsonstats['RAM']['RAM']
    lfb_status = jetsonstats['RAM']['lfb']
    RAM_VALUE = { 'name': "RAM", 
                  'value': int(float(ram_status['used'])/float(ram_status['total']) * 100.0),
                  'label': "(lfb " + str(lfb_status['nblock']) + "x" + str(lfb_status['size']) + "MB)",
                  'percent': "{0:2.1f}GB/{1:2.1f}GB".format(ram_status['used']/1000.0, ram_status['total']/1000.0),
                }
    linear_percent_gauge(RAM_VALUE, width, offset=line_counter + 1)
    linear_percent_gauge(make_gauge_from_percent(jetsonstats['EMC']), width, offset=line_counter + 2)
    line_counter += 3
    # GPU linear gauge info
    linear_percent_gauge(make_gauge_from_percent(jetsonstats['GR3D']), width, offset=line_counter + 1)
    line_counter += 2
    # FAN status 
    FAN_VALUE = { 'name': 'FAN',
                  'value': int(jetsonstats['FAN']),
                }
    linear_percent_gauge(FAN_VALUE, width, offset=line_counter + 1)
    line_counter += 2
    
    # Add temperatures and voltages
    plot_dictionary(line_counter + 1, jetsonstats['temperatures'], "Temperatures", start=3)
    plot_dictionary(line_counter + 1, jetsonstats['voltages'], "Voltages", start=int(float(width)/3.0))
    
    # Close option menu
    stdscr.addstr(height-1, 0, "F10 close", curses.A_REVERSE)
    # Refresh page
    stdscr.refresh()
    
    
if __name__ == "__main__":
    # Check if the system work in sudo
    if os.getuid() != 0:
        print("Run with sudo")
        sys.exit(0)
    # Load command line controller
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.cbreak()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    # Catch SIGINT (CTRL-C)
    signal.signal(signal.SIGINT, signal_handler)
    # Open tegrastats
    p = subprocess.Popen(['/home/nvidia/tegrastats', '--interval', '100'], stdout=subprocess.PIPE)
    # launch reader
    try:
        while p.poll() is None:
            # This blocks until it receives a newline.
            tegrastats_stream = p.stdout.readline().decode("utf-8")
            # read status from fan
            fan_status_p = subprocess.Popen(['cat', '/sys/kernel/debug/tegra_fan/target_pwm'], stdout=subprocess.PIPE)
            fan_level = int(fan_status_p.communicate()[0])
            # Build status of jetson
            jetsonstats = get_status(tegrastats_stream, fan_level)
            # Refresh window
            refreshwindow(jetsonstats)
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
