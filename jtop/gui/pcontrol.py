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
from .jtopguilib import (check_curses,
                         box_keyboard,
                         box_list)
from .chart import Chart
from ..core.jetson_clocks import JetsonClocks


class CTRL(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(CTRL, self).__init__("CTRL", stdscr, jetson, refresh)
        # Only if exist a fan will be load a chart
        # Initialize FAN chart
        self.chart_fan = Chart(jetson, "FAN", refresh, self.update_chart, line="o", color=curses.color_pair(4), color_chart=curses.color_pair(10))
        if 'FAN' not in self.jetson.stats:
            self.chart_fan.statusChart(False, "NO FAN")

    def update_chart(self, jetson, name):
        parameter = jetson.stats.get("FAN", {})
        value = 'cpwm' if 'cpwm' in parameter else 'tpwm'
        # Get max value if is present
        max_val = parameter.get("max_val", 100)
        # Get unit
        unit = parameter.get("unit", "%")
        # Append in list
        return {
            'value': parameter.get(value, 0),
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
        posx = 2
        start_pos = first + 2
        # Jetson Clocks status
        jc_field = "jetson_clocks"
        # Show status jetson_clocks
        self.stdscr.addstr(start_pos, posx, jc_field, curses.A_BOLD)
        try:
            status = self.jetson.jetson_clocks.status
            color = curses.color_pair(2) if status else curses.A_NORMAL
            jc_status_name = "Running" if status else "Stopped"
        except JetsonClocks.JCException:
            status = False
            # Fix error color
            color = curses.color_pair(11)
            jc_status_name = "SUDO SUGGESTED"
        self.stdscr.addstr(start_pos, posx + len(jc_field) + 1, jc_status_name, color)
        # Show service status
        service = self.jetson.jetson_clocks.service
        jc_manual = status and service != "active"
        if self.jetson.userid == 0 and not jc_manual:
            # button start/stop jetson clocks
            box_keyboard(self.stdscr, posx - 1, start_pos + 1, "a", key, mouse=mouse, action=self.keyboard)
        # Field service
        service_string = "service"
        self.stdscr.addstr(start_pos + 2, posx + 4, service_string, curses.A_UNDERLINE)
        self.stdscr.addstr(start_pos + 5, posx + 4, service_string, curses.A_UNDERLINE)
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
        self.stdscr.addstr(start_pos + 2, posx + len(service_string) + 5,
                           service.capitalize(),
                           color)
        if self.jetson.userid == 0 and not jc_manual:
            # button start/stop jetson clocks
            box_keyboard(self.stdscr, posx - 1, start_pos + 4, "e", key, mouse=mouse, action=self.keyboard)
        # Read status jetson_clocks
        enabled = self.jetson.jetson_clocks.enable
        self.stdscr.addstr(start_pos + 5, posx + len(service_string) + 5,
                           "Enable" if enabled else "Disable",
                           curses.A_BOLD if enabled else curses.A_NORMAL)
        # Build NVP model list
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            self.stdscr.addstr(start_pos + 8, posx, "NVP model", curses.A_BOLD)
            if self.jetson.userid == 0:
                # Draw keys to decrease nvpmodel
                box_keyboard(self.stdscr, posx + 10, start_pos + 7, "-", key, mouse=mouse, action=self.keyboard)
                # Draw selected number
                self.stdscr.addstr(start_pos + 8, posx + 16, str(nvpmodel.selected), curses.A_NORMAL)
                # Draw keys to increase nvpmodel
                box_keyboard(self.stdscr, posx + 18, start_pos + 7, "+", key, mouse=mouse, action=self.keyboard)
            # Write list of available modes
            mode_names = [mode["Name"] for mode in nvpmodel.modes]
            mode_status = [mode["status"] for mode in nvpmodel.modes]
            box_list(self.stdscr, posx - 1, start_pos + 10, mode_names, nvpmodel.num,
                     status=mode_status, max_width=42, numbers=True,
                     mouse=mouse, action=self.nvp_action)
        # Evaluate size chart
        size_x = [posx + 40, width - 2]
        if self.jetson.userid == 0 and 'FAN' in self.jetson.stats:
            size_y = [start_pos + 3, height - 3]
        else:
            size_y = [start_pos, height - 3]
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
                box_keyboard(self.stdscr, posx + 40, start_pos, "f", key, mouse=mouse, action=self.keyboard)
                self.stdscr.addstr(start_pos + 1, posx + 46, self.jetson.fan.config.capitalize(), curses.A_BOLD)
            # Show speed buttons only if is in manual
            if self.jetson.fan.conf == 'manual':
                blk = 53
                # Draw keys to decrease fan speed
                box_keyboard(self.stdscr, posx + blk, start_pos, "m", key, mouse=mouse, action=self.keyboard)
                # Draw selected number
                self.stdscr.addstr(start_pos, posx + blk + 6, "Speed", curses.A_BOLD)
                speed_str = "{speed: 3}%".format(speed=self.jetson.fan.speed)
                self.stdscr.addstr(start_pos + 1, posx + blk + 6, speed_str, curses.A_NORMAL)
                # Draw keys to increase fan speed
                box_keyboard(self.stdscr, posx + blk + 13, start_pos, "p", key, mouse=mouse, action=self.keyboard)

    def nvp_action(self, name):
        # Read number
        number = int(name.split(" ")[0])
        # Run nvpmodel on number selected
        nvpmodel = self.jetson.nvpmodel
        nvpmodel.set(number)

    def keyboard(self, key):
        if self.jetson.userid == 0:
            # Start jetson_clocks
            start = self.jetson.jetson_clocks.start
            # Status enable
            enabled = self.jetson.jetson_clocks.enable
            # NVPmodel controller
            nvpmodel = self.jetson.nvpmodel
            # FAN controller
            fan = self.jetson.fan
            # Write the new jetson_clocks status
            if key == 'a' and not start:
                self.jetson.jetson_clocks.start = True
            elif key == 'a' and start:
                self.jetson.jetson_clocks.start = False
            # Write the new jetson_clocks status
            elif key == 'e' and not enabled:
                self.jetson.jetson_clocks.enable = True
            elif key == 'e' and enabled:
                self.jetson.jetson_clocks.enable = False
            # Enable nvpmodel control
            if nvpmodel is not None:
                if key == '+':
                    nvpmodel.increase()
                elif key == '-':
                    nvpmodel.decrease()
            # Enable fan control
            if fan is not None:
                if key == 'p':
                    fan.increase()
                    # Store configuration
                    fan.store()
                elif key == 'm':
                    fan.decrease()
                    # Store configuration
                    fan.store()
                if key == 'f':
                    # Go to next configuration
                    fan.conf_next()
                    # Store configuration
                    fan.store()
# EOF
