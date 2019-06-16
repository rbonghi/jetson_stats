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

import curses
# Graphics elements
from .jtopguilib import (linear_percent_gauge,
                         make_gauge_from_percent)
# Menu GUI pages
from .jtopguimenu import (plot_voltages,
                          compact_info,
                          plot_temperatures,
                          plot_CPUs)


def all_info(stdscr, jetson, key):
    """
        Update screen with values
    """
    # Screen size
    height, width = stdscr.getmaxyx()
    line_counter = 1
    # Plot Status CPU
    line_counter = plot_CPUs(stdscr, line_counter, jetson.stats['CPU'], width)
    # Plot MTS
    if 'MTS' in jetson.stats:
        line_counter += 1
        stdscr.addstr(line_counter, 0, "MTS ", curses.color_pair(5))
        MTS_FG = {'name': 'FG',
                  'value': int(jetson.stats['MTS']['fg']),
                  }
        linear_percent_gauge(stdscr, MTS_FG, width // 2 - 2,
                             offset=line_counter, start=4, color_name=5)
        MTS_BG = {'name': 'BG',
                  'value': int(jetson.stats['MTS']['bg']),
                  }
        linear_percent_gauge(stdscr, MTS_BG, width // 2 - 2,
                             offset=line_counter, start=2 + width // 2, color_name=5)
    # RAM linear gauge info
    ram_status = jetson.stats['RAM']['RAM']
    lfb_status = jetson.stats['RAM']['lfb']
    RAM_VALUE = {'name': "Mem",
                 'value': int(ram_status['used'][-1] / float(ram_status['total']) * 100.0),
                 'label': "(lfb " + str(lfb_status['nblock']) + "x" + str(lfb_status['size']) + "MB)",
                 'percent': "{0:2.1f}GB/{1:2.1f}GB".format(ram_status['used'][-1] / 1000.0, ram_status['total'] / 1000.0),
                 }
    line_counter += 1
    linear_percent_gauge(stdscr, RAM_VALUE, width, offset=line_counter)
    # EMC linear gauge info
    if 'EMC' in jetson.stats:
        line_counter += 1
        linear_percent_gauge(stdscr, make_gauge_from_percent(jetson.stats['EMC']), width, offset=line_counter)
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
        linear_percent_gauge(stdscr, IRAM_VALUE, width, offset=line_counter)
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
    line_counter += 1
    linear_percent_gauge(stdscr, SWAP_VALUE, width, offset=line_counter)
    # GPU linear gauge info
    line_counter += 1
    if 'GR3D' in jetson.stats:
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
