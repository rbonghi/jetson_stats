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
from .jtopguilib import (check_curses,
                         box_keyboard,
                         box_status,
                         box_list)


@check_curses
def CTRL(stdscr, jetson, key):
    """ Control board, check status jetson_clock and change NVP model """
    # Screen size
    height, width = stdscr.getmaxyx()
    # Position information
    posx = 2
    start_pos = 2
    stdscr.addstr(start_pos, posx, "jetson_clock controller", curses.A_BOLD)
    # button start/stop jetson clock
    box_keyboard(stdscr, start_pos, posx + 1, "x", key)
    # Read status jetson_clock
    status = jetson.jetson_clock.status
    status_box = True if status == "active" else False
    box_status(stdscr, start_pos + 5, posx + 1, status, status_box)
    # Build NVP model list
    nvpmodel = jetson.nvpmodel
    if nvpmodel is not None:
        stdscr.addstr(start_pos + 5, posx + 4, "NVP model", curses.A_BOLD)
        mode_names = [mode["Name"] for mode in nvpmodel.modes]
        box_list(stdscr, start_pos, posx + 7, mode_names, nvpmodel.num, max_width=60)
        # Draw background rectangle
        # rectangle(stdscr, y, x, y + 2, x + 3 + len(name))
# EOF
