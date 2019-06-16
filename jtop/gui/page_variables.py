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
from datetime import timedelta
# Graphics elements
from .jtopguilib import (check_curses,
                         plot_name_info)
# Menu GUI pages
from .jtopguimenu import strfdelta


@check_curses
def Variables(stdscr, jetson, key):
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
    idx = 0
    # Board info
    stdscr.addstr(start_pos + idx, posx, "- Board:", curses.A_BOLD)
    for name, info in jetson.board["board"].items():
        stdscr.addstr(start_pos + idx + 1, posx + 2, "* " + name + ":")
        stdscr.addstr(start_pos + idx + 1, posx + spacing, info, curses.A_BOLD)
        idx += 1
    # Libraries info
    stdscr.addstr(start_pos + idx + 1, posx, "- Libraries:", curses.A_BOLD)
    idx += 1
    for name, info in jetson.board["libraries"].items():
        stdscr.addstr(start_pos + idx + 1, posx + 2, "* " + name + ":")
        stdscr.addstr(start_pos + idx + 1, posx + spacing, info, curses.A_BOLD)
        idx += 1
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
