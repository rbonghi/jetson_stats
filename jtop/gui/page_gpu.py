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
                         make_gauge_from_percent,
                         plot_name_info,
                         draw_chart)


def GPU(stdscr, jetson, key):
    """
        Draw a plot with GPU payload
    """
    # Screen size
    max_y, max_x = stdscr.getmaxyx()
    # Evaluate size chart
    size_x = [2, max_x - 10]
    size_y = [1, max_y * 2 // 3 - 1]
    # Read GPU status
    if 'GR3D' in jetson.stats:
        gpu = jetson.stats['GR3D']
        # Draw the GPU chart
        draw_chart(stdscr, size_x, size_y, gpu, color=curses.color_pair(2))
        # Percent Gauge GPU
        linear_percent_gauge(stdscr, make_gauge_from_percent(jetson.stats['GR3D']), max_x // 2, offset=max_y * 2 // 3, start=2)
        # Temperature GPU
        if "GPU" in jetson.stats['temperatures']:
            plot_name_info(stdscr, max_y * 2 // 3, max_x // 2 + 4, "GPU Temp", jetson.stats['temperatures']['GPU']['text'])
        # Jetson clocks status
        jc = jetson.jetson_clocks
        if jc is not None:
            jc_status = jc.status
            if jc_status == "active":
                color = curses.color_pair(2)  # Running (Green)
            elif jc_status == "inactive":
                color = curses.A_NORMAL       # Normal (Grey)
            elif "ing" in jc_status:
                color = curses.color_pair(3)  # Warning (Yellow)
            else:
                color = curses.color_pair(1)  # Error (Red)
            # Show if JetsonClock is enabled or not
            if jc.enable:
                jc_status = "[" + jc_status + "]"
            plot_name_info(stdscr, max_y * 2 // 3 + 2, 2, "Jetson Clocks", jc_status, color)
        # NVP Model
        nvpmodel = jetson.nvpmodel
        if nvpmodel is not None:
            plot_name_info(stdscr, max_y * 2 // 3 + 3, 2, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
