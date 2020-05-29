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
# Jetson Clock event
from ..core.jetson_clocks import JetsonClocks


class CTRL(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(CTRL, self).__init__("CTRL", stdscr, jetson, refresh)
        # Only if exist a fan will be load a chart
        # Initialize FAN chart
        self.chart_fan = Chart(jetson, "FAN", refresh, self.update_chart, line="o", color=curses.color_pair(4), color_chart=[curses.color_pair(10)])
        if 'FAN' not in self.jetson.stats:
            self.chart_fan.statusChart(False, "NO FAN")
        # Initialize buttons
        self.service_start = Button(stdscr, key="s", action=self.action_service_start)
        self.service_enable = Button(stdscr, key="e", action=self.action_service_enable)
        # NVP Model controller
        self.nvp_increase = Button(stdscr, key="+", action=self.action_nvp_increase, underline=False)
        self.nvp_decrease = Button(stdscr, key="-", action=self.action_nvp_decrease, underline=False)
        mode_names = [mode["Name"] for mode in self.jetson.nvpmodel.modes]
        self.nvp_list = ButtonList(stdscr, range(len(mode_names)), mode_names, action=self.action_nvp)
        # Fan controller
        self.fan_status = Button(stdscr, key="f", action=self.action_fan_status)
        self.fan_status_increase = Button(stdscr, key="p", action=self.action_fan_increase)
        self.fan_status_decrease = Button(stdscr, key="m", action=self.action_fan_decrease)

    def action_nvp_increase(self, key):
        if self.jetson.userid == 0:
            # NVPmodel controller
            nvpmodel = self.jetson.nvpmodel
            if nvpmodel is not None:
                nvpmodel.increase()

    def action_nvp_decrease(self, key):
        if self.jetson.userid == 0:
            # NVPmodel controller
            nvpmodel = self.jetson.nvpmodel
            if nvpmodel is not None:
                nvpmodel.decrease()

    def action_nvp(self, key):
        if self.jetson.userid == 0:
            # Run nvpmodel on number selected
            nvpmodel = self.jetson.nvpmodel
            if nvpmodel is not None:
                # Read number
                number = int(key)
                # Set new nvpmodel
                nvpmodel.set(number)

    def action_service_enable(self, key):
        if self.jetson.userid == 0:
            # Start jetson_clocks
            self.jetson.jetson_clocks.enable = not self.jetson.jetson_clocks.enable

    def action_service_start(self, key):
        if self.jetson.userid == 0:
            # Start jetson_clocks
            self.jetson.jetson_clocks.start = not self.jetson.jetson_clocks.start

    def action_fan_status(self, key):
        if self.jetson.userid == 0:
            # FAN controller
            fan = self.jetson.fan
            if fan is not None:
                # Go to next configuration
                fan.conf_next()
                # Store configuration
                fan.store()

    def action_fan_increase(self, key):
        if self.jetson.userid == 0:
            # FAN controller
            fan = self.jetson.fan
            if fan is not None:
                fan.increase()
                # Store configuration
                fan.store()

    def action_fan_decrease(self, key):
        if self.jetson.userid == 0:
            # FAN controller
            fan = self.jetson.fan
            if fan is not None:
                fan.decrease()
                # Store configuration
                fan.store()

    def update_chart(self, jetson, name):
        parameter = jetson.stats.get("FAN", {})
        value = 'cpwm' if 'cpwm' in parameter else 'tpwm'
        # Get max value if is present
        max_val = parameter.get("max_val", 100)
        # Get unit
        unit = parameter.get("unit", "%")
        # Append in list
        return {
            'value': [parameter.get(value, 0)],
            'max': max_val,
            'unit': unit,
            'active': 'FAN' in jetson.stats
        }

    @check_curses
    def draw(self, key, mouse):
        """ Control board, check status jetson_clocks and change NVP model """
        # Screen size
        height, width, first = self.size_page()
        # Position information
        start_y = first + 1
        start_x = 1
        # Jetson Clocks status
        jc_field = "jetson_clocks"
        # Show status jetson_clocks
        self.stdscr.addstr(start_y + 1, start_x + 1, jc_field, curses.A_BOLD)
        try:
            status = self.jetson.jetson_clocks.status
            color = curses.color_pair(2) if status else curses.A_NORMAL
            jc_status_name = "Running" if status else "Stopped"
        except JetsonClocks.JCException:
            status = False
            # Fix error color
            color = curses.color_pair(11)
            jc_status_name = "SUDO SUGGESTED"
        self.stdscr.addstr(start_y + 1, start_x + len(jc_field) + 2, jc_status_name, color)
        # Show service status
        service = self.jetson.jetson_clocks.service
        jc_manual = status and service != "active"
        if self.jetson.userid == 0 and not jc_manual:
            # button start/stop jetson clocks
            self.service_start.draw(start_y + 2, start_x, key, mouse)
        # Field service
        service_string = "service"
        self.stdscr.addstr(start_y + 3, start_x + 5, service_string, curses.A_UNDERLINE)
        self.stdscr.addstr(start_y + 6, start_x + 5, service_string, curses.A_UNDERLINE)
        # Read status jetson_clocks
        if service == "active":
            color = curses.A_BOLD         # Running (Bold)
        elif service == "inactive":
            color = curses.A_NORMAL       # Normal (Grey)
        elif "ing" in service:
            color = curses.color_pair(3)  # Warning (Yellow)
        else:
            color = curses.color_pair(1)  # Error (Red)
        # Status service
        self.stdscr.addstr(start_y + 3, start_x + len(service_string) + 6,
                           service.capitalize(),
                           color)
        # button start/stop jetson clocks
        if self.jetson.userid == 0 and not jc_manual:
            self.service_enable.draw(start_y + 5, start_x, key, mouse)
        # Read status jetson_clocks
        enabled = self.jetson.jetson_clocks.enable
        self.stdscr.addstr(start_y + 6, start_x + len(service_string) + 6,
                           "Enable" if enabled else "Disable",
                           curses.A_BOLD if enabled else curses.A_NORMAL)
        # Build NVP model list
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            self.stdscr.addstr(start_y + 9, start_x, "NVP model", curses.A_BOLD)
            if self.jetson.userid == 0:
                # Draw keys to decrease nvpmodel
                self.nvp_decrease.draw(start_y + 8, start_x + 10, key, mouse)
                # Draw selected number
                self.stdscr.addstr(start_y + 9, start_x + 16, str(nvpmodel.selected), curses.A_NORMAL)
                # Draw keys to increase nvpmodel
                self.nvp_increase.draw(start_y + 8, start_x + 18, key, mouse)
            # Write list of available modes
            self.nvp_list.draw(start_y + 11, start_x, width // 2 - start_x, key, mouse,
                               lstatus=[mode["status"] for mode in nvpmodel.modes],
                               select=nvpmodel.num)
        # Evaluate size chart
        size_x = [start_x + width // 2 + 1, width - start_x - 1]
        if self.jetson.userid == 0 and 'FAN' in self.jetson.stats:
            size_y = [start_y + 3, height - 3]
        else:
            size_y = [start_y, height - 3]
        # Add label
        label = ""
        if 'FAN' in self.jetson.stats:
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
        if self.jetson.userid == 0 and 'FAN' in self.jetson.stats:
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
