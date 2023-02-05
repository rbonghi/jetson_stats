# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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


class SmallButton:

    def __init__(self, stdscr, action, key=''):
        self.stdscr = stdscr
        self._key = key
        self._action = action
        self._timer = 0
        self._start_pressed = False
        self._old_status = False

    def draw(self, pos_y, pos_x, key, mouse, data={}, label='', color=curses.A_REVERSE):
        # String label
        if self._key and label:
            string = "[{key}] {label}".format(label=label, key=self._key)
        elif not self._key:
            string = "{label}".format(label=label)
        else:
            string = "[{key}]".format(key=self._key)
        # status
        status = self._keyPressed(key) or self._mousePressed(pos_y, pos_x, mouse, string)
        # Update status
        if self._old_status != status:
            self._start_pressed = True
            self._old_status = status
        # Counter status pressed
        if self._start_pressed:
            if self._timer > 5:
                self._start_pressed = False
                self._timer = 0
            self._timer += 1
        # Draw button
        self.stdscr.addstr(pos_y, pos_x, string, curses.A_NORMAL if self._start_pressed else color)
        # Run action
        if status:
            # Run action
            self._action(data)

    def _keyPressed(self, key):
        # Default status
        if not self._key:
            return False
        return key == ord(self._key)

    def _mousePressed(self, pos_y, pos_x, mouse, string):
        if mouse:
            mx, my = mouse
            if my >= pos_y and my <= pos_y and \
               mx >= pos_x and mx <= pos_x + len(string):
                return True
        return False
# EOF
