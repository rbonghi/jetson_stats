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
                         box_list,
                         draw_chart)


@check_curses
def CTRL(stdscr, jetson, key):
    """ Control board, check status jetson_clocks and change NVP model """
    # Screen size
    height, width = stdscr.getmaxyx()
    # Position information
    posx = 2
    start_pos = 2
    stdscr.addstr(start_pos, posx, "jetson_clocks controller", curses.A_BOLD)
    if jetson.userid == 0:
        # button start/stop jetson clocks
        status_key_active = box_keyboard(stdscr, start_pos, posx + 1, "a", key)
    # Read status jetson_clocks
    start = jetson.jetson_clocks.start
    status = jetson.jetson_clocks.status
    box_status(stdscr, start_pos + 5, posx + 1, status.capitalize(), start)
    if jetson.userid == 0:
        # Write the new jetson_clocks status
        if status_key_active and not start:
            jetson.jetson_clocks.start = True
        elif status_key_active and start:
            jetson.jetson_clocks.start = False
    if jetson.userid == 0:
        # button start/stop jetson clocks
        status_key_enable = box_keyboard(stdscr, start_pos, posx + 4, "e", key)
    # Read status jetson_clocks
    enabled = jetson.jetson_clocks.enable
    enabled_box = "Enable" if enabled else "Disable"
    box_status(stdscr, start_pos + 5, posx + 4, enabled_box, enabled)
    if jetson.userid == 0:
        # Write the new jetson_clocks status
        if status_key_enable and not enabled:
            jetson.jetson_clocks.enable = True
        elif status_key_enable and enabled:
            jetson.jetson_clocks.enable = False
    # Build NVP model list
    nvpmodel = jetson.nvpmodel
    if nvpmodel is not None:
        stdscr.addstr(start_pos + 8, posx, "NVP model", curses.A_BOLD)
        if jetson.userid == 0:
            # Draw keys to increase and decrease nvpmodel
            status_key_nvp_inc = box_keyboard(stdscr, start_pos + 10, posx + 7, "-", key)
            status_key_nvp_dec = box_keyboard(stdscr, start_pos + 15, posx + 7, "+", key)
            if status_key_nvp_inc:
                nvpmodel.increase()
            elif status_key_nvp_dec:
                nvpmodel.decrease()
        # Write list of available modes
        mode_names = [mode["Name"] for mode in nvpmodel.modes]
        box_list(stdscr, start_pos, posx + 10, mode_names, nvpmodel.num, max_width=40)
        # Draw background rectangle
        # rectangle(stdscr, y, x, y + 2, x + 3 + len(name))
    # Add plot fan status
    fan = jetson.fan
    if fan is not None:
        # Fan chart name
        stdscr.addstr(start_pos, posx + 40, "FAN speed", curses.A_BOLD)
        # Evaluate size chart
        size_x = [posx + 40, width - 10]
        size_y = [3, height * 2 // 3 - 1]
        gpu = jetson.stats['GR3D']
        # Draw the GPU chart
        draw_chart(stdscr, size_x, size_y, gpu)
# EOF
