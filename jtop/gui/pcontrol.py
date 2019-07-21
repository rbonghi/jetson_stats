# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
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
                         box_status,
                         box_list,
                         Chart)


class CTRL(Page):

    def __init__(self, stdscr, jetson, refresh):
        super(CTRL, self).__init__("CTRL", stdscr, jetson, refresh)
        # Only if exist a fan will be load a chart
        if 'FAN' in self.jetson.stats:
            fan = self.jetson.stats['FAN']
            value = 'cpwm' if 'cpwm' in fan else 'tpwm'
            # Initialize FAN chart
            self.chart_fan = Chart("FAN", refresh, line="o", color=curses.color_pair(4), value_name=value)
            # Attach the chart for every update from jtop
            jetson.attach(self.chart_fan)

    @check_curses
    def draw(self, key):
        """ Control board, check status jetson_clocks and change NVP model """
        # Screen size
        height, width = self.stdscr.getmaxyx()
        # Position information
        posx = 2
        start_pos = 2
        self.stdscr.addstr(start_pos, posx, "jetson_clocks controller", curses.A_BOLD)
        if self.jetson.userid == 0:
            # button start/stop jetson clocks
            box_keyboard(self.stdscr, start_pos - 1, posx + 1, "a", key)
        # Read status jetson_clocks
        start = self.jetson.jetson_clocks.start
        status = self.jetson.jetson_clocks.status
        box_status(self.stdscr, start_pos + 4, posx + 1, status.capitalize(), start)
        if self.jetson.userid == 0:
            # button start/stop jetson clocks
            box_keyboard(self.stdscr, start_pos - 1, posx + 4, "e", key)
        # Read status jetson_clocks
        enabled = self.jetson.jetson_clocks.enable
        enabled_box = "Enable" if enabled else "Disable"
        box_status(self.stdscr, start_pos + 4, posx + 4, enabled_box, enabled)
        # Build NVP model list
        nvpmodel = self.jetson.nvpmodel
        if nvpmodel is not None:
            self.stdscr.addstr(start_pos + 8, posx, "NVP model", curses.A_BOLD)
            if self.jetson.userid == 0:
                # Draw keys to decrease nvpmodel
                box_keyboard(self.stdscr, start_pos + 10, posx + 7, "-", key)
                # Draw selected number
                self.stdscr.addstr(start_pos + 8, posx + 16, str(nvpmodel.selected), curses.A_NORMAL)
                # Draw keys to increase nvpmodel
                box_keyboard(self.stdscr, start_pos + 18, posx + 7, "+", key)
            # Write list of available modes
            mode_names = [mode["Name"] for mode in nvpmodel.modes]
            mode_status = [mode["status"] for mode in nvpmodel.modes]
            box_list(self.stdscr, start_pos - 1, posx + 10, mode_names, nvpmodel.num, status=mode_status, max_width=42, numbers=True)
        # Add plot fan status
        if 'FAN' in self.jetson.stats:
            fan = self.jetson.stats['FAN']
            # Add label
            if 'cpwm' in fan:
                label = "{current: >3}% of {target: >3}%".format(current=fan.get("cpwm", 0), target=fan.get("tpwm", 0))
            else:
                label = "Target: {target: >3}%".format(target=fan.get("tpwm", 0))
            # Evaluate size chart
            size_x = [posx + 40, width - 10]
            size_y = [start_pos, height - 3] if self.jetson.userid != 0 else [start_pos + 3, height - 3]
            # Draw the GPU chart
            self.chart_fan.draw(self.stdscr, size_x, size_y, label=label)
            if self.jetson.userid == 0:
                self.stdscr.addstr(start_pos + 1, posx + 40, "Speed", curses.A_BOLD)
                # Draw keys to decrease fan speed
                box_keyboard(self.stdscr, posx + 46, start_pos, "m", key)
                # Draw selected number
                self.stdscr.addstr(start_pos + 1, posx + 52, str(self.jetson.fan.speed), curses.A_NORMAL)
                # Draw keys to increase fan speed
                box_keyboard(self.stdscr, posx + 56, start_pos, "p", key)

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
            if key == ord('a') and not start:
                self.jetson.jetson_clocks.start = True
            elif key == ord('a') and start:
                self.jetson.jetson_clocks.start = False
            # Write the new jetson_clocks status
            elif key == ord('e') and not enabled:
                self.jetson.jetson_clocks.enable = True
            elif key == ord('e') and enabled:
                self.jetson.jetson_clocks.enable = False
            # Enable nvpmodel control
            if nvpmodel is not None:
                if key == ord('+'):
                    nvpmodel.increase()
                elif key == ord('-'):
                    nvpmodel.decrease()
            # Enable fan control
            if fan is not None:
                if key == ord('p'):
                    fan.increase()
                elif key == ord('m'):
                    fan.decrease()
# EOF
