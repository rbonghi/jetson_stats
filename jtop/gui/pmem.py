# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import curses
# Page class definition
from .jtopgui import Page
# Graphics elements
from .jtopguilib import (linear_gauge,
                         label_freq)
# Graphics elements
from .jtopguilib import (box_keyboard,
                         Chart)


class MEM(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(MEM, self).__init__("MEM", stdscr, jetson, refresh)
        # Initialize MEM chart
        self.chart_ram = Chart("RAM", refresh, color=curses.color_pair(6), value_name="use", value_max="tot")
        # Attach the chart for every update from jtop
        jetson.attach(self.chart_ram)

    def draw(self, key):
        # Screen size
        height, width = self.stdscr.getmaxyx()
        # Set size chart memory
        size_x = [2, width - 10]
        size_y = [1, height * 1 // 2 - 1]
        # RAM linear gauge info
        line_counter = size_y[1] + 2
        # Read RAM status and make gaugues
        ram_status = self.jetson.stats['RAM']
        lfb_status = self.jetson.stats['RAM']['lfb']
        unit_name = 'G'  # TODO improve with check unit status
        # lfb label
        percent = "{use:2.1f}{unit}/{tot:2.1f}{unit}B".format(use=ram_status['use'] / 1000.0,
                                                              unit=unit_name,
                                                              tot=ram_status['tot'] / 1000.0)
        label_lfb = "(lfb {nblock}x{size}{unit}B)".format(nblock=lfb_status['nblock'],
                                                          size=lfb_status['size'],
                                                          unit=lfb_status['unit'])
        # Draw the GPU chart
        self.chart_ram.draw(self.stdscr, size_x, size_y, label="{percent} - {lfb}".format(percent=percent, lfb=label_lfb))
        # Draw the Memory gague
        linear_gauge(self.stdscr, offset=line_counter, size=width,
                     name='Mem',
                     value=int(ram_status['use'] / float(ram_status['tot']) * 100.0),
                     label=label_lfb,
                     percent=percent,
                     color=curses.color_pair(6))
        # IRAM linear gauge info
        if 'IRAM' in self.jetson.stats:
            iram_status = self.jetson.stats['IRAM']
            line_counter += 1
            if iram_status['tot'] > 1000:
                if 'k' == iram_status['unit']:
                    unit = 'M'
                elif 'M' == iram_status['unit']:
                    unit = 'G'
                percent = "{use:2.1f}{unit}B/{tot:2.1f}{unit}B".format(use=iram_status['use'] / 1000.0,
                                                                       tot=iram_status['tot'] / 1000.0,
                                                                       unit=unit)
            else:
                percent = "{use}{unit}B/{tot}{unit}B".format(use=iram_status['use'],
                                                             tot=iram_status['tot'],
                                                             unit=iram_status['unit'])
            linear_gauge(self.stdscr, offset=line_counter, size=width,
                         name='Imm',
                         value=int(iram_status['use'] / float(iram_status['tot']) * 100.0),
                         label="(lfb {size}{unit}B)".format(size=iram_status['lfb']['size'],
                                                            unit=iram_status['lfb']['unit']),
                         percent=percent,
                         color=curses.color_pair(6))
        # SWAP linear gauge info
        line_counter += 1
        swap_status = self.jetson.stats.get('SWAP', {})
        swap_cached = swap_status.get('cached', {})
        if swap_status.get('tot', 0) > 1000:
            if 'k' == swap_status['unit']:
                unit = 'M'
            elif 'M' == swap_status['unit']:
                unit = 'G'
            percent = "{use:2.1f}{unit}B/{tot:2.1f}{unit}B".format(use=swap_status['use'] / 1000.0,
                                                                   tot=swap_status['tot'] / 1000.0,
                                                                   unit=unit)
        else:
            percent = "{use}{unit}B/{tot}{unit}B".format(use=swap_status.get('use', 0),
                                                         tot=swap_status.get('tot', 0),
                                                         unit=swap_status.get('unit', ''))
        linear_gauge(self.stdscr, offset=line_counter, size=width,
                     name='Swp',
                     value=int(swap_status.get('use', 0) / float(swap_status.get('tot', 1)) * 100.0),
                     label="(cached {size}{unit}B)".format(size=swap_cached.get('size', '0'),
                                                           unit=swap_cached.get('unit', '')),
                     percent=percent,
                     status='ON' if swap_status else 'OFF',
                     color=curses.color_pair(6))
        # EMC linear gauge info
        line_counter += 1
        emc = self.jetson.stats.get('EMC', {})
        linear_gauge(self.stdscr, offset=line_counter, size=width,
                     name='EMC',
                     value=emc.get('val', 0),
                     status='ON' if emc else 'REQUIRE SUDO',
                     label=label_freq(emc),
                     color=curses.color_pair(6))
        # Clear cache button
        clear_cache = "Clear cache"
        self.stdscr.addstr(height - 3, 1, clear_cache, curses.A_NORMAL)
        box_keyboard(self.stdscr, len(clear_cache) + 2, height - 4, "c", key)
        enable_swap = "Enable swap"
        self.stdscr.addstr(height - 3, len(clear_cache) + 8, enable_swap, curses.A_NORMAL)
        box_keyboard(self.stdscr, len(clear_cache) + len(enable_swap) + 8, height - 4, "h", key)

    def keyboard(self, key):
        if self.jetson.userid == 0:
            pass
# EOF