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

FAN_STEP = 10


class CTRL(Page):

    def __init__(self, stdscr, jetson):
        super(CTRL, self).__init__("CTRL", stdscr, jetson)
        # Only if exist a fan will be load a chart
        # Initialize FAN chart
        self.chart_fan = Chart(jetson, "FAN", self.update_chart, line="o", color=curses.color_pair(4), color_chart=[curses.color_pair(10)])
        if self.jetson.fan:
            self.chart_fan.statusChart(False, "NO FAN")
        # Initialize buttons
        self.service_start = Button(stdscr, key="s", action=self.action_service_start)
        self.service_enable = Button(stdscr, key="e", action=self.action_service_enable)
        # NVP Model controller
        if self.jetson.nvpmodel is not None:
            self.nvp_increase = Button(stdscr, key="+", action=self.action_nvp_increase, underline=False)
            self.nvp_decrease = Button(stdscr, key="-", action=self.action_nvp_decrease, underline=False)
            mode_names = [name.replace('MODE_', '').replace('_', ' ') for name in self.jetson.nvpmodel.modes]
            self.nvp_list = ButtonList(stdscr, mode_names, action=self.action_nvp)
        # Fan controller
        if self.jetson.fan:
            self.fan_status_increase = Button(stdscr, key="p", action=self.action_fan_increase)
            self.fan_status_decrease = Button(stdscr, key="m", action=self.action_fan_decrease)
            # Fan options
            self.fan_list = ButtonList(stdscr, self.jetson.fan.configs, action=self.action_fan)

    def action_fan(self, key):
        # Get config name
        name = self.jetson.fan.configs[int(key)]
        # Set new fan mode
        self.jetson.fan.mode = name

    def action_nvp_increase(self, key):
        # NVPmodel controller
        self.jetson.nvpmodel += 1

    def action_nvp_decrease(self, key):
        # NVPmodel controller
        self.jetson.nvpmodel -= 1

    def action_nvp(self, key):
        # Set new nvpmodel
        self.jetson.nvpmodel = int(key)

    def action_service_enable(self, key):
        # Start jetson_clocks
        self.jetson.jetson_clocks.boot = not self.jetson.jetson_clocks.boot

    def action_service_start(self, key):
        # Start jetson_clocks
        self.jetson.jetson_clocks = not self.jetson.jetson_clocks

    def action_fan_increase(self, key):
        speed = self.jetson.fan.speed
        # Round speed
        spd = (speed // 10) * 10
        # Increase the speed
        if spd + FAN_STEP <= 100:
            self.jetson.fan.speed = spd + FAN_STEP

    def action_fan_decrease(self, key):
        speed = self.jetson.fan.speed
        # Round speed
        spd = (speed // 10) * 10
        # Increase the speed
        if spd - FAN_STEP >= 0:
            self.jetson.fan.speed = spd - FAN_STEP
        if self.jetson.fan.speed < FAN_STEP:
            self.jetson.fan.speed = 0

    def update_chart(self, jetson, name):
        # Append in list
        if jetson.fan is None:
            return {}
        return {
            'value': [jetson.fan.get('measure', 0)],
            'active': True if jetson.fan else False
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
        if self.jetson.jetson_clocks.is_config:
            self.service_start.draw(start_y + 3, start_x, key, mouse)
        # Field service
        jetson_clocks_string = "jetson_clocks"
        self.stdscr.addstr(start_y + 4, start_x + 5, jetson_clocks_string, curses.A_UNDERLINE)
        # Read status jetson_clocks
        if jc_status_name == "running":
            color = (curses.A_BOLD | curses.color_pair(2))  # Running (Bold)
        elif jc_status_name == "inactive":
            color = curses.A_NORMAL       # Normal (Grey)
        elif "ing" in jc_status_name:
            color = curses.color_pair(3)  # Warning (Yellow)
        else:
            color = curses.color_pair(1)  # Error (Red)
        # Status jetson_clocks
        self.stdscr.addstr(
            start_y + 4, start_x + len(jetson_clocks_string) + 6,
            jc_status_name.capitalize(),
            color)
        # button start/stop jetson clocks
        self.service_enable.draw(start_y + 6, start_x, key, mouse)
        # Read status jetson_clocks
        jetson_clocks_boot_string = "boot"
        self.stdscr.addstr(start_y + 7, start_x + 5, jetson_clocks_boot_string, curses.A_UNDERLINE)
        boot = self.jetson.jetson_clocks.boot
        self.stdscr.addstr(
            start_y + 7, start_x + len(jetson_clocks_boot_string) + 6,
            "Enable" if boot else "Disable",
            curses.A_BOLD if boot else curses.A_NORMAL)
        # Build NVP model list
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            nvp_id = nvpmodel.id
            self.stdscr.addstr(start_y + 10, start_x, "NVP model", curses.A_BOLD)
            # Draw keys to decrease nvpmodel
            if nvp_id != 0:
                self.nvp_decrease.draw(start_y + 9, start_x + 10, key, mouse)
            # Draw selected number
            self.stdscr.addstr(start_y + 10, start_x + 16, str(nvp_id), curses.A_NORMAL)
            # Status NVP model service
            if nvpmodel.is_running:
                self.stdscr.addch(start_y + 10, start_x + 25, curses.ACS_DIAMOND, curses.color_pair(2) | curses.A_BOLD)
            # Draw keys to increase nvpmodel
            if nvp_id != len(self.jetson.nvpmodel.modes) - 1:
                self.nvp_increase.draw(start_y + 9, start_x + 18, key, mouse)
            # Write list of available modes
            self.nvp_list.draw(
                start_y + 12, start_x, width // 2 - start_x, key, mouse,
                lstatus=nvpmodel.status,
                select=nvp_id)
        # Evaluate size chart
        size_x = [start_x + width // 2 + 1, width - start_x - 1]
        size_y = [start_y + 3, height - 3]
        # Add label
        label = ''
        if self.jetson.fan:
            # Read status control fan
            ctrl_stat = "Auto=" + ("Enable" if self.jetson.fan.auto else "Disable")
            # Add label
            if self.jetson.fan.speed is not None:
                label = "{current: >3.0f}% of {target: >3.0f}% {ctrl}".format(current=self.jetson.fan.measure, target=self.jetson.fan.speed, ctrl=ctrl_stat)
            else:
                label = "{current: >3.0f}% {ctrl}".format(current=self.jetson.fan.measure, ctrl=ctrl_stat)
            if self.jetson.fan.speed is not None:
                # Fan label
                self.stdscr.addstr(start_y, start_x, "Fan", curses.A_NORMAL)
                self.stdscr.addstr(start_y + 1, start_x, "Speed", curses.A_BOLD)
                # Draw keys to decrease fan speed
                self.fan_status_decrease.draw(start_y, start_x + 6, key, mouse)
                # Draw selected number
                speed_str = "{speed: >3.0f}%".format(speed=self.jetson.fan.speed)
                self.stdscr.addstr(start_y + 1, start_x + 12, speed_str, curses.A_NORMAL)
                # Draw keys to increase fan speed
                self.fan_status_increase.draw(start_y, start_x + 17, key, mouse)
            if self.jetson.fan.auto is not None:
                # Write list of available modes
                self.stdscr.addstr(start_y, start_x + 24, "Fan", curses.A_NORMAL)
                self.stdscr.addstr(start_y + 1, start_x + 24, "Mode", curses.A_BOLD)
                # Get ID from fan mode
                fan_mode = self.jetson.fan.mode
                fan_id = self.jetson.fan.configs.index(fan_mode)
                self.fan_list.draw(start_y, start_x + 30, width, key, mouse, select=fan_id)
        # Draw the GPU chart
        self.chart_fan.draw(self.stdscr, size_x, size_y, label=label)

    def keyboard(self, key):
        if key == ord('f'):
            l_configs = len(self.jetson.fan.configs)
            idx = self.jetson.fan.configs.index(self.jetson.fan.mode)
            # Get config name
            name = self.jetson.fan.configs[(idx + 1) % l_configs]
            # Set new fan mode
            self.jetson.fan.mode = name
# EOF
