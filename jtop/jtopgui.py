# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
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

import os
import curses
from datetime import timedelta
# Graphics elements
from .jtopguilib import (check_size,
                         check_curses,
                         linear_percent_gauge,
                         make_gauge_from_percent,
                         plot_name_info,
                         draw_chart)
# Menu GUI pages
from .jtopguimenu import (strfdelta,
                          plot_voltages,
                          compact_info,
                          plot_temperatures,
                          plot_CPUs)


@check_curses
def Variables(stdscr, jetson):
    """
        Write all environment variables
    """
    # Screen size
    height, width = stdscr.getmaxyx()
    # Position information
    posx = 2
    start_pos = 2
    spacing = 20
    # Up time
    uptime_string = strfdelta(timedelta(seconds=jetson.uptime), "{days} days {hours}:{minutes}:{seconds}")
    plot_name_info(stdscr, start_pos, posx, "- Up Time", uptime_string)
    start_pos += 1
    # Loop build information
    for idx, info in enumerate(jetson.board):
        # Board info
        if "info" in info:
            stdscr.addstr(start_pos + idx, posx + 2, "* " + info["name"] + ":")
            stdscr.addstr(start_pos + idx, posx + spacing, info["info"], curses.A_BOLD)
        else:
            stdscr.addstr(start_pos + idx, posx, "- " + info["name"], curses.A_BOLD)
    # IP address and Hostname
    if jetson.local_interfaces:
        plot_name_info(stdscr, start_pos + idx + 1, posx, "- Hostname", jetson.local_interfaces["hostname"])
        stdscr.addstr(start_pos + idx + 2, posx, "- Interfaces", curses.A_BOLD)
        idx += 3
        for name, ip in jetson.local_interfaces["interfaces"].items():
            stdscr.addstr(start_pos + idx, posx + 2, "* " + name + ":")
            stdscr.addstr(start_pos + idx, posx + spacing, ip, curses.A_BOLD)
            idx += 1
    # Author information
    plot_name_info(stdscr, start_pos, width - 30, "Author", "Raffaello Bonghi")
    plot_name_info(stdscr, start_pos + 1, width - 30, "e-mail", "raffaello@rnext.it")


def GPU(stdscr, jetson):
    """
        Draw a plot with GPU payload
    """
    # Screen size
    max_y, max_x = stdscr.getmaxyx()
    # Evaluate size chart
    size_x = [2, max_x - 10]
    size_y = [1, max_y * 2 // 3 - 1]
    # Read GPU status
    gpu = jetson.stats["GR3D"]
    # Draw the GPU chart
    draw_chart(stdscr, size_x, size_y, gpu)
    # Percent Gauge GPU
    linear_percent_gauge(stdscr, make_gauge_from_percent(jetson.stats['GR3D']), max_x // 2, offset=max_y * 2 // 3, start=2)
    # Temperature GPU
    if "GPU" in jetson.stats['temperatures']:
        plot_name_info(stdscr, max_y * 2 // 3 + 1, 2, "GPU Temp", jetson.stats['temperatures']['GPU']['text'])
    # NVP Model
    if jetson.nvpmodel:
        plot_name_info(stdscr, max_y * 2 // 3 + 2, 2, "NV Power", jetson.nvpmodel['name'] + " - " + str(jetson.nvpmodel['mode']))


def all_info(stdscr, jetson):
    """
        Update screen with values
    """
    # Screen size
    height, width = stdscr.getmaxyx()
    line_counter = 1
    # Plot Status CPU
    line_counter = plot_CPUs(stdscr, line_counter, jetson.stats['CPU'], width)
    # RAM linear gauge info
    ram_status = jetson.stats['RAM']['RAM']
    lfb_status = jetson.stats['RAM']['lfb']
    RAM_VALUE = {'name': "Mem",
                 'value': int(ram_status['used'][-1] / float(ram_status['total']) * 100.0),
                 'label': "(lfb " + str(lfb_status['nblock']) + "x" + str(lfb_status['size']) + "MB)",
                 'percent': "{0:2.1f}GB/{1:2.1f}GB".format(ram_status['used'][-1] / 1000.0, ram_status['total'] / 1000.0),
                 }
    linear_percent_gauge(stdscr, RAM_VALUE, width, offset=line_counter + 1)
    # EMC linear gauge info
    linear_percent_gauge(stdscr, make_gauge_from_percent(jetson.stats['EMC']), width, offset=line_counter + 2)
    # IRAM linear gauge info
    iram_status = jetson.stats['IRAM']
    if iram_status:
        line_counter += 1
        IRAM_VALUE = {'name': "Imm",
                      'value': int(iram_status['used'][-1] / float(iram_status['total']) * 100.0),
                      'label': "(lfb " + str(iram_status['size']) + "MB)",
                      'percent': "{0:2.1f}GB/{1:2.1f}GB".format(iram_status['used'][-1] / 1000.0,
                                                                iram_status['total'] / 1000.0),
                      }
        linear_percent_gauge(stdscr, IRAM_VALUE, width, offset=line_counter + 2)
    # SWAP linear gauge info
    swap_status = jetson.stats['SWAP']
    if swap_status:
        SWAP_VALUE = {'name': "Swp",
                      'value': int(swap_status['used'][-1] / float(swap_status['total']) * 100.0),
                      'label': "(cached " + str(swap_status['cached']) + "MB)",
                      'percent': "{0:2.1f}GB/{1:2.1f}GB".format(swap_status['used'][-1] / 1000.0,
                                                                swap_status['total'] / 1000.0),
                      }
    else:
        SWAP_VALUE = {'name': "Swp"}
    linear_percent_gauge(stdscr, SWAP_VALUE, width, offset=line_counter + 3)
    line_counter += 4
    # GPU linear gauge info
    linear_percent_gauge(stdscr, make_gauge_from_percent(jetson.stats['GR3D']), width, offset=line_counter + 1)
    line_counter += 2
    # Status disk
    disk_status = jetson.disk
    DISK_STATUS = {'name': "Dsk",
                   'value': int(float(disk_status['used']) / float(disk_status['total']) * 100.0),
                   'percent': "{0:2.1f}GB/{1:2.1f}GB".format(disk_status['used'], disk_status['total']),
                   }
    linear_percent_gauge(stdscr, DISK_STATUS, width, offset=line_counter, type_bar="#", color_name=3)
    # Last part of information
    split = 1.0
    split += 1.0 if jetson.stats['temperatures'] else 0.0
    split += 1.0 if jetson.stats['voltages'] else 0.0
    column_width = int(float(width - 4) / split)
    line_counter += 1
    # List of all mini menu
    mini_menu = [compact_info, plot_temperatures, plot_voltages]
    # Evaluate column width
    column_width = int(float(width) / len(mini_menu))
    for idx, mini in enumerate(mini_menu):
        # Run mini page
        mini(stdscr, idx * column_width, line_counter, column_width, jetson)


class JTOPGUI:

    def __init__(self, stdscr, pages, init_page=0):
        self.stdscr = stdscr
        self.pages = pages
        self.n_page = init_page

    @check_size(20, 50)
    def draw(self, stat):
        # Write head of the jtop
        self.header()
        # Write page selected
        if "func" in self.pages[self.n_page]:
            page = self.pages[self.n_page]["func"]
            if page is not None:
                page(self.stdscr, stat)
        # Draw menu
        self.menu()

    def increase(self):
        idx = self.n_page + 1
        self.set(idx + 1)

    def decrease(self):
        idx = self.n_page + 1
        self.set(idx - 1)

    def set(self, idx):
        if idx <= len(self.pages) and idx > 0:
            self.n_page = idx - 1

    @check_curses
    def header(self):
        board_info = os.environ["JETSON_DESCRIPTION"] + " - Jetpack " + os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]"
        self.stdscr.addstr(0, 0, board_info, curses.A_BOLD)
        if os.getuid() != 0:
            self.stdscr.addstr(0, len(board_info) + 1, "- PLEASE RUN WITH SUDO", curses.color_pair(1))

    @check_curses
    def menu(self):
        height, width = self.stdscr.getmaxyx()
        # Set background for all menu line
        self.stdscr.addstr(height - 1, 0, ("{0:<" + str(width - 1) + "}").format(" "), curses.A_REVERSE)
        position = 1
        for idx, page in enumerate(self.pages):
            name = page["name"]
            if self.n_page != idx:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=name), curses.A_REVERSE)
            else:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=name))
            position += len(name) + 2
            self.stdscr.addstr(height - 1, position, " - ", curses.A_REVERSE)
            position += 3
        # Add close option menu
        self.stdscr.addstr(height - 1, position, "Q to close", curses.A_REVERSE)
        # Author name
        name_author = "Raffaello Bonghi"
        self.stdscr.addstr(height - 1, width - len(name_author), name_author, curses.A_REVERSE)
# EOF
