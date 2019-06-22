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
from .jtopgui import Page
# Graphics elements
from .jtopguilib import (plot_name_info,
                         linear_gauge,
                         label_freq,
                         Chart)


class GPU(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(GPU, self).__init__("GPU", stdscr, jetson, refresh)
        if 'GR3D' in jetson.stats:
            # Initialize GPU chart
            self.chart_gpu = Chart("GR3D", refresh, color=curses.color_pair(2))
            # Attach the chart for every update from jtop
            jetson.attach(self.chart_gpu)

    def draw(self, key):
        """
            Draw a plot with GPU payload
        """
        # Screen size
        max_y, max_x = self.stdscr.getmaxyx()
        # Evaluate size chart
        size_x = [2, max_x - 10]
        size_y = [1, max_y * 2 // 3 - 1]
        # Draw the GPU chart
        if 'GR3D' in self.jetson.stats:
            self.chart_gpu.draw(self.stdscr, size_x, size_y)
        # Percent Gauge GPU
        gpu = self.jetson.stats.get('GR3D', {})
        linear_gauge(self.stdscr, offset=max_y * 2 // 3, start=2, size=max_x // 2,
                     name='GPU',
                     value=gpu.get('val', 0),
                     label=label_freq(gpu),
                     status='ON' if gpu else 'REQUIRE SUDO',
                     color=curses.color_pair(6))
        # Temperature GPU
        if "GPU" in self.jetson.stats['TEMP']:
            temp_gpu = self.jetson.stats['TEMP']['GPU']
            plot_name_info(self.stdscr, max_y * 2 // 3, max_x // 2 + 4, "GPU Temp", str(temp_gpu) + "C")
        # Jetson clocks status
        jc = self.jetson.jetson_clocks
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
            plot_name_info(self.stdscr, max_y * 2 // 3 + 2, 2, "Jetson Clocks", jc_status, color)
        # NVP Model
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            plot_name_info(self.stdscr, max_y * 2 // 3 + 3, 2, "NV Power[" + str(nvpmodel.num) + "]", nvpmodel.mode)
