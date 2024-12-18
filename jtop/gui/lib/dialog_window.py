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
from .smallbutton import ButtonList
# Gui refresh rate
GUI_REFRESH = 1000 // 20


class DialogWindow(object):
    def __init__(self, title, text, on_click, buttons, width=44, height=6):
        self.dialog_width = width
        self.dialog_height = height
        self.title = title
        self.text = text
        self.on_click = on_click
        self.buttons = buttons
        self.enable_dialog_window = False
        self._dialog_win = None
        self.info = {}

    def enable(self, title="", info={}):
        if title:
            self.title = title
        self.info = info
        self.enable_dialog_window = True

    def disable(self):
        self.enable_dialog_window = False

    def show(self, stdscr, key, mouse):
        if self.enable_dialog_window:
            self._draw(stdscr, key, mouse)

    def _draw(self, stdscr, key, mouse):
        # Refresh the window to show the changes
        height, width = stdscr.getmaxyx()
        dialog_y, dialog_x = (height - self.dialog_height) // 2, (width - self.dialog_width) // 2
        self._dialog_win = curses.newwin(self.dialog_height, self.dialog_width, dialog_y, dialog_x)
        # Create a list of buttons
        self._buttons_profile = ButtonList(self._dialog_win, self._on_click, self.buttons, info=self.info, linear=True)
        # Add a border around the window
        self._dialog_win.border()
        # Add the title and the text
        self._dialog_win.addstr(1, 2, self.title, curses.A_BOLD)
        self._dialog_win.addstr(2, 2, self.text)
        # Add the buttons
        align_mouse = (mouse[0] - dialog_x, mouse[1] - dialog_y) if mouse else ()
        self._buttons_profile.update(4, 2, key, align_mouse, "")
        # Refresh the window to show the changes
        self._dialog_win.refresh()
        self._dialog_win.timeout(GUI_REFRESH)

    def _on_click(self, info, selected):
        self.on_click(info, selected)
        self.enable_dialog_window = False
# EOF
