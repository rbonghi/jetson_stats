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
    http://toilers.mines.edu/~jrosenth/101python/code/curses_plot/
"""
import re, argparse, time
# System and signal
import signal, os, sys
# control command line
import curses
# Launch command
import subprocess
# read tegrastats
from jstatslib import Tegrastats

from jstatsgui import *

def signal_handler(sig, frame):
    """
        Close the system when catch SIGIN (CTRL-C)
    """
    sys.exit(0)

def refreshwindow(stdscr, jetsonstats):
    """
        Update screen with values
    """
    # Clear screen
    height, width = stdscr.getmaxyx()

    line_counter = 2
    max_bar = int(float(width)/2.0)
    
    # Plot Status CPU
    line_counter = plot_CPUs(stdscr, line_counter, jetsonstats['CPU'], width)
    # RAM linear gauge info
    ram_status = jetsonstats['RAM']['RAM']
    lfb_status = jetsonstats['RAM']['lfb']
    RAM_VALUE = { 'name': "Mem", 
                  'value': int(float(ram_status['used'])/float(ram_status['total']) * 100.0),
                  'label': "(lfb " + str(lfb_status['nblock']) + "x" + str(lfb_status['size']) + "MB)",
                  'percent': "{0:2.1f}GB/{1:2.1f}GB".format(ram_status['used']/1000.0, ram_status['total']/1000.0),
                }
    linear_percent_gauge(stdscr, RAM_VALUE, width, offset=line_counter + 1)
    # EMC linear gauge info
    linear_percent_gauge(stdscr, make_gauge_from_percent(jetsonstats['EMC']), width, offset=line_counter + 2)
    # IRAM linear gauge info
    iram_status = jetsonstats['IRAM']
    if iram_status:
        line_counter += 1
        IRAM_VALUE = { 'name': "Imm", 
                      'value': int(float(iram_status['used'])/float(iram_status['total']) * 100.0),
                      'label': "(lfb " + str(iram_status['size']) + "MB)",
                      'percent': "{0:2.1f}GB/{1:2.1f}GB".format(iram_status['used']/1000.0, iram_status['total']/1000.0),
                    }
        linear_percent_gauge(stdscr, IRAM_VALUE, width, offset=line_counter + 2)
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
    linear_percent_gauge(stdscr, SWAP_VALUE, width, offset=line_counter + 3)
    line_counter += 4
    # GPU linear gauge info
    linear_percent_gauge(stdscr, make_gauge_from_percent(jetsonstats['GR3D']), width, offset=line_counter + 1)
    line_counter += 2
    # Status disk
    #line_counter += 1
    disk_status = jetsonstats['DISK']
    DISK_STATUS = { 'name': "Dsk", 
                  'value': int(float(disk_status['used'])/float(disk_status['total']) * 100.0),
                  'percent': "{0:2.1f}GB/{1:2.1f}GB".format(disk_status['used'], disk_status['total']),
                }
    linear_percent_gauge(stdscr, DISK_STATUS, width, offset=line_counter, type_bar="#", color_name=3)
    
    
    split = 1.0
    split += 1.0 if jetsonstats['temperatures'] else 0.0
    split += 1.0 if jetsonstats['voltages'] else 0.0
    column_width = int(float(width - 4)/split)
    line_counter += 1
    # Add temperatures and voltages
    plot_other_info(stdscr, line_counter, jetsonstats, column_width, start=1)
    if jetsonstats['temperatures']:
        plot_temperatures(stdscr, line_counter, jetsonstats['temperatures'], start=2 + column_width)
    if jetsonstats['voltages']:
        plot_voltages(stdscr, line_counter, jetsonstats['voltages'], start= 2 + 2*column_width)
    
# The easiest way to use curses is to use a wrapper around a main function
# Essentially, what goes in the main function is the body of your program,
# The `stdscr' parameter passed to it is the curses screen generated by our
# wrapper.
def main(stdscr):
    # In this program, we don't want keystrokes echoed to the console,
    # so we run this to disable that
    curses.noecho()

    # Additionally, we want to make it so that the user does not have to press
    # enter to send keys to our program, so here is how we get keys instantly
    curses.cbreak()
    # Define pairing colorss
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)

    # Hide the cursor
    curses.curs_set(0)

    # Lastly, keys such as the arrow keys are sent as funny escape sequences to
    # our program. We can make curses give us nicer values (such as curses.KEY_LEFT)
    # so it is easier on us.
    stdscr.keypad(True)
    
    # Refreshing page curses loop
    # https://stackoverflow.com/questions/54409978/python-curses-refreshing-text-with-a-loop
    stdscr.nodelay(1)

    counter = 0
    # Here is the loop of our program, we keep clearing and redrawing in this loop
    while True:
        # First, clear the screen
        stdscr.erase()
        # Extract height and width from windows
        height, width = stdscr.getmaxyx()
        
        stdscr.addstr(0, 0, "jtop - Raffaello Bonghi", curses.A_BOLD)
        stdscr.addstr(1, 0, os.environ["JETSON_DESCRIPTION"] + " - Jetpack " + os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]", curses.A_BOLD)
        
        stat = tegra.read() 
        if stat:
            refreshwindow(stdscr, stat)
        
        # Close option menu
        stdscr.addstr(height-1, 0, ("{0:<" + str(width-1) + "}").format("CTRL-C to close"), curses.A_REVERSE)
        
        # Draw the screen
        stdscr.refresh()
        # Set a timeout and read keystroke
        stdscr.timeout(250)
        key = stdscr.getch()
        # keyboard check list
        if key == ord('q'):
            break
        
if __name__ == "__main__":
    # Check if the system work in sudo
    if os.getuid() != 0:
        print("Run with sudo")
        sys.exit(0)
    # Add arg parser
    parser = argparse.ArgumentParser(description='jtop the command line monitor')
    parser.add_argument('--server', help='Run jtop json server', action="store_true", default=False)
    parser.add_argument('-p', dest="port", help='Set server port', default='5555')
    # Parse arguments
    args = parser.parse_args()
    # Catch SIGINT (CTRL-C)
    signal.signal(signal.SIGINT, signal_handler)
    # Open tegrastats reader and run the curses wrapper
    with Tegrastats() as tegra:
        if args.server:
            while True:
                # Read tegra stats
                stat = tegra.read()
                # TODO: Convert print to server post
                #if stat: print(tegra.read())
                print(tegra.q.qsize())
                # Sleep before send new stat
                time.sleep(1)
        else:
            # Call the curses wrapper
            curses.wrapper(main)
#EOF
