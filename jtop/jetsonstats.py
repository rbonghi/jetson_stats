#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
    Graphic reference:
    http://urwid.org/examples/index.html
    https://npyscreen.readthedocs.io/
    https://github.com/chubin/cheat.sh
    
    https://stackoverflow.com/questions/6840420/python-rewrite-multiple-lines-in-the-console
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

def linear_gauge(offset, value, short_name, label, max_bar):
    n_bar = int(float(value) * float(max_bar) / 100.0)
    stdscr.addstr(offset, 0, ("{0}  [{1:" + str(max_bar) + "}] {2}").format(short_name,"|" * n_bar, label))

def refreshwindow(jetsonstats):
    """progress: 0-10"""
    height, width = stdscr.getmaxyx()
    
    
    stdscr.addstr(0, 0, "Size: %d - %d"%(height, width))
    line_counter = 1
    
    max_bar = int(float(width - 20)/2.0)
    # Plot Status CPU
    cpu_counter = 0
    for cpu in jetsonstats['CPU']:
        if isinstance(cpu, dict):
            label = str(cpu['idle']) + "% - " + str(cpu['frequency']) + "MHz"
            linear_gauge(line_counter, cpu['idle'], "CPU" + str(cpu_counter+1), label, max_bar)
            cpu_counter += 1
            line_counter += 1
    # GPU linear gauge info
    gpu_counter = 0
    for gpu in jetsonstats['GR3D']:
        if isinstance(gpu, dict):
            if 'frequency' in gpu:
                label = str(gpu['idle']) + "% - " + str(gpu['frequency']) + "MHz"
            else:
                label = str(gpu['idle']) + "%"
            linear_gauge(line_counter, gpu['idle'], "GPU" + str(gpu_counter+1), label, max_bar)
            gpu_counter += 1
            line_counter += 1
    # Refresh page
    stdscr.refresh()
    
if __name__ == "__main__":
    # Check if the system work in sudo
    if os.getuid() != 0:
        print("Run with sudo")
        sys.exit(0)
    # Load command line controller
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    # Catch SIGINT (CTRL-C)
    signal.signal(signal.SIGINT, signal_handler)
    # Open tegrastats
    p = subprocess.Popen(['/home/nvidia/tegrastats', '--interval', '100'], stdout=subprocess.PIPE)
    # launch reader
    try:
        while p.poll() is None:
            # This blocks until it receives a newline.
            tegrastats_stream = p.stdout.readline().decode("utf-8")
            # Build status of jetson
            jetsonstats = get_status(tegrastats_stream)
            # Refresh window
            refreshwindow(jetsonstats)
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()