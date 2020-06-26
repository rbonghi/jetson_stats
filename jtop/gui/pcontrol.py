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
from .jtopgui import Page
# Graphics elements
from .lib.common import check_curses
# Graphic library
from .lib.chart import Chart
from .lib.button import Button, ButtonList


class CTRL(Page):

    def __init__(self, stdscr, jetson):
        super(CTRL, self).__init__("CTRL", stdscr, jetson)
        # Only if exist a fan will be load a chart
        # Initialize FAN chart
        self.chart_fan = Chart(jetson, "FAN", self.update_chart, line="o", color=curses.color_pair(4), color_chart=[curses.color_pair(10)])
        if self.jetson.fan is None:
            self.chart_fan.statusChart(False, "NO FAN")
        # Initialize buttons
        self.service_start = Button(stdscr, key="s", action=self.action_service_start)
        self.service_enable = Button(stdscr, key="e", action=self.action_service_enable)
        # NVP Model controller
        self.nvp_increase = Button(stdscr, key="+", action=self.action_nvp_increase, underline=False)
        self.nvp_decrease = Button(stdscr, key="-", action=self.action_nvp_decrease, underline=False)
        mode_names = self.jetson.nvpmodel.modes
        self.nvp_list = ButtonList(stdscr, range(len(mode_names)), mode_names, action=self.action_nvp)
        # Fan controller
        self.fan_status = Button(stdscr, key="f", action=self.action_fan_status)
        self.fan_status_increase = Button(stdscr, key="p", action=self.action_fan_increase)
        self.fan_status_decrease = Button(stdscr, key="m", action=self.action_fan_decrease)

    def action_nvp_increase(self, key):
        # NVPmodel controller
        self.jetson.nvpmodel += 1

    def action_nvp_decrease(self, key):
        # NVPmodel controller
        self.jetson.nvpmodel -= 1

    def action_nvp(self, key):
        # Run nvpmodel on number selected
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            # Read number
            number = int(key)
            # Set new nvpmodel
            nvpmodel.set(number)

    def action_service_enable(self, key):
        # Start jetson_clocks
        self.jetson.jetson_clocks.boot = not self.jetson.jetson_clocks.boot

    def action_service_start(self, key):
        # Start jetson_clocks
        self.jetson.jetson_clocks = not self.jetson.jetson_clocks

    def action_fan_status(self, key):
        # FAN controller
        fan = self.jetson.fan
        if fan is not None:
            # Go to next configuration
            fan.conf_next()
            # Store configuration
            fan.store()

    def action_fan_increase(self, key):
        # FAN controller
        fan = self.jetson.fan
        if fan is not None:
            fan.increase()
            # Store configuration
            fan.store()

    def action_fan_decrease(self, key):
        # FAN controller
        fan = self.jetson.fan
        if fan is not None:
            fan.decrease()
            # Store configuration
            fan.store()

    def update_chart(self, jetson, name):
        # Append in list
        if jetson.fan is None:
            return {}
        return {
            'value': [jetson.fan.speed],
            'active': jetson.fan is not None
        }

    @check_curses
    def draw(self, key, mouse):
        """ Control board, check status jetson_clocks and change NVP model """
        # Screen size
        height, width, first = self.size_page()
        # Position information
        start_y = first + 1
        start_x = 1
        # Status jetson_clocks
        # Write status jetson_clocks
        jc_status_name = self.jetson.jetson_clocks.status
        # Show service status
        self.service_start.draw(start_y + 1, start_x, key, mouse)
        # Field service
        jetson_clocks_string = "jetson_clocks"
        self.stdscr.addstr(start_y + 2, start_x + 5, jetson_clocks_string, curses.A_UNDERLINE)
        
        # Read status jetson_clocks
        if jc_status_name == "running":
            color = (curses.A_BOLD | curses.color_pair(2))         # Running (Bold)
        elif jc_status_name == "inactive":
            color = curses.A_NORMAL       # Normal (Grey)
        elif "ing" in jc_status_name:
            color = curses.color_pair(3)  # Warning (Yellow)
        else:
            color = curses.color_pair(1)  # Error (Red)
        # Status jetson_clocks
        self.stdscr.addstr(start_y + 2, start_x + len(jetson_clocks_string) + 6,
                           jc_status_name.capitalize(),
                           color)
        # button start/stop jetson clocks
        self.service_enable.draw(start_y + 4, start_x, key, mouse)
        # Read status jetson_clocks
        jetson_clocks_boot_string = "boot"
        self.stdscr.addstr(start_y + 5, start_x + 5, jetson_clocks_boot_string, curses.A_UNDERLINE)
        boot = self.jetson.jetson_clocks.boot
        self.stdscr.addstr(start_y + 5, start_x + len(jetson_clocks_boot_string) + 6,
                           "Enable" if boot else "Disable",
                           curses.A_BOLD if boot else curses.A_NORMAL)
        # Build NVP model list
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            self.stdscr.addstr(start_y + 9, start_x, "NVP model", curses.A_BOLD)
            # Draw keys to decrease nvpmodel
            self.nvp_decrease.draw(start_y + 8, start_x + 10, key, mouse)
            # Draw selected number
            #self.stdscr.addstr(start_y + 9, start_x + 16, str(nvpmodel.selected), curses.A_NORMAL)
            # Draw keys to increase nvpmodel
            self.nvp_increase.draw(start_y + 8, start_x + 18, key, mouse)
            # Write list of available modes
            self.nvp_list.draw(start_y + 11, start_x, width // 2 - start_x, key, mouse,
                               lstatus=nvpmodel.modes,
                               select=nvpmodel.id)
        # Evaluate size chart
        size_x = [start_x + width // 2 + 1, width - start_x - 1]
        if self.jetson.fan is not None:
            size_y = [start_y + 3, height - 3]
        else:
            size_y = [start_y, height - 3]
        # Add label
        label = ""
        if self.jetson.fan is not None:
            fan = self.jetson.stats['FAN']
            # Read status control fan
            if 'ctrl' in fan:
                ctrl_stat = "CTRL=" + ("Enable" if fan['ctrl'] else "Disable")
            else:
                ctrl_stat = ""
            # Add label
            if 'cpwm' in fan:
                label = "{current: >3}% of {target: >3}% {ctrl}".format(current=fan.get("cpwm", 0), target=fan.get("tpwm", 0), ctrl=ctrl_stat)
            else:
                label = "Target: {target: >3}% {ctrl}".format(target=fan.get("tpwm", 0), ctrl=ctrl_stat)
        # Draw the GPU chart
        self.chart_fan.draw(self.stdscr, size_x, size_y, label=label)
        # Add plot fan status
        if self.jetson.fan is not None:
            # Mode
            if 'ctrl' in fan:
                self.fan_status.draw(start_y, start_x + width // 2, key, mouse)
                self.stdscr.addstr(start_y + 1, start_x + width // 2 + 6, self.jetson.fan.config.capitalize(), curses.A_BOLD)
            # Show speed buttons only if is in manual
            if self.jetson.fan.conf == 'manual':
                blk = start_x + width // 2 + 13
                # Draw keys to decrease fan speed
                self.fan_status_decrease.draw(start_y, blk, key, mouse)
                # Draw selected number
                self.stdscr.addstr(start_y, blk + 6, "Speed", curses.A_BOLD)
                speed_str = "{speed: 3}%".format(speed=self.jetson.fan.speed)
                self.stdscr.addstr(start_y + 1, blk + 6, speed_str, curses.A_NORMAL)
                # Draw keys to increase fan speed
                self.fan_status_increase.draw(start_y, blk + 13, key, mouse)
# EOF
