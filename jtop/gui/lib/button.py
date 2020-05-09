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

# control command line
import curses
from curses.textpad import rectangle
from threading import Thread
# Size button
SIZE_BUTTON_HEIGHT = 2


class Button:

    def __init__(self, stdscr, key, label="", action=None, underline=True, keyboard=True):
        self.stdscr = stdscr
        self.key = key
        self.label = label
        self.action = action
        self.underline = underline
        self.keyboard = keyboard

    def draw(self, posy, posx, key, mouse, color=curses.A_REVERSE, exstatus=False):
        # Draw rectangle
        width = self.sizeX()
        rectangle(self.stdscr, posy, posx, posy + SIZE_BUTTON_HEIGHT, posx + width)
        # status
        status = self._keyPressed(key) or self._mousePressed(posy, posx, width, mouse)
        # Write key letter
        if self.key:
            underline = curses.A_UNDERLINE if self.underline else curses.A_NORMAL
            pressed = color if status or exstatus and not self.label else curses.A_NORMAL
            self.stdscr.addstr(posy + 1, posx + 2, self.key, underline | pressed)
        # Write label
        if self.label:
            posx_label = 4 if self.key else 2
            pressed = color if status or exstatus else curses.A_NORMAL
            self.stdscr.addstr(posy + 1, posx + posx_label, self.label, pressed)
        # Run action
        if status and self.action is not None:
            # Run a thread
            th = Thread(target=self.action, args=(self.key))
            th.start()

    def sizeX(self):
        width = 4 if self.key else 2
        return width + len(self.label) + 1 if self.label else width

    def _keyPressed(self, key):
        # Default status
        if not self.keyboard:
            return False
        return key == ord(self.key)

    def _mousePressed(self, posy, posx, width, mouse):
        if mouse:
            mx, my = mouse
            if my >= posy and my <= posy + SIZE_BUTTON_HEIGHT and \
               mx >= posx and mx <= posx + width:
                return True
        return False


class ButtonList:

    def __init__(self, stdscr, keys, labels, action=None):
        self.stdscr = stdscr
        # List of buttons
        self.buttons = []
        for key, label in zip(keys, labels):
            key = str(key) if not isinstance(key, str) else key
            self.buttons += [Button(stdscr, key, label=label, underline=False, keyboard=False, action=action)]

    def draw(self, posy, posx, width, key, mouse, lstatus=[], select=-1):
        # Box max size
        # rectangle(self.stdscr, posy, posx, posy + SIZE_BUTTON_HEIGHT, posx + width)
        # draw buttons
        x_line = 0
        y_line = 0
        lstatus = lstatus if lstatus else [False] * len(self.buttons)
        for idx, (button, status) in enumerate(zip(self.buttons, lstatus)):
            # Find next position
            b_width = button.sizeX()
            if x_line + b_width >= width:
                y_line += SIZE_BUTTON_HEIGHT + 1
                x_line = 0
            # Draw button
            color = curses.A_REVERSE if status else curses.color_pair(1)
            selected = True if select == idx else not status
            button.draw(posy + y_line, posx + x_line, key, mouse, color=color, exstatus=selected)
            # Increase x counter
            x_line += b_width + 1
# EOF
