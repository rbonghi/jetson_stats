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
import time
from copy import deepcopy


class SmallButton(object):
    def __init__(self, stdscr, on_click, label='', toggle=False, trigger_key=None, info={}):
        self.stdscr = stdscr
        self.on_click = on_click
        self.toggle = toggle
        self.selected = False
        self.trigger_key = trigger_key
        self.info = info
        self.label = label
        self.highlight_time = None

    def update(self, y, x, label='', key=None, mouse=None, color=None):
        label = label if label else self.label
        if mouse and mouse[1] == y and x <= mouse[0] <= x + len(label) + 1:
            self.selected = not self.selected if self.toggle else True
            self.on_click(self.info, selected=self.selected)
            self.highlight_time = time.time()
        elif self.trigger_key:
            if key == ord(self.trigger_key):
                self.selected = not self.selected if self.toggle else True
                self.on_click(self.info, selected=self.selected)
                self.highlight_time = time.time()

        color_normal = color if color else curses.A_NORMAL

        if self.trigger_key:
            # self.stdscr.addstr(y, x, '[{trigger_key}]{label}'.format(trigger_key=self.trigger_key,
            #                   label=" " + label if label else ""), curses.A_REVERSE if self.selected else color_normal)
            self.stdscr.addstr(y, x, '[', curses.A_REVERSE if self.selected else curses.A_NORMAL)
            self.stdscr.addstr('{trigger_key}'.format(trigger_key=self.trigger_key), curses.A_REVERSE if self.selected else color_normal)
            if label:
                self.stdscr.addstr('|', curses.A_REVERSE if self.selected else curses.A_NORMAL)
            self.stdscr.addstr('{label}'.format(label=" " + label if label else ""), curses.A_REVERSE if self.selected else color_normal)
            self.stdscr.addstr(']', curses.A_REVERSE if self.selected else curses.A_NORMAL)
        else:
            # self.stdscr.addstr(y, x, '[{label}]'.format(label=label), curses.A_REVERSE if self.selected else color_normal)
            self.stdscr.addstr(y, x, '[', curses.A_REVERSE if self.selected else curses.A_NORMAL)
            self.stdscr.addstr('{label}'.format(label=label), curses.A_REVERSE if self.selected else color_normal)
            self.stdscr.addstr(']', curses.A_REVERSE if self.selected else curses.A_NORMAL)
        if self.highlight_time and not self.toggle and time.time() - self.highlight_time > 0.1:
            self.selected = False
            self.highlight_time = None

    def is_selected(self):
        return self.selected

    def set_selected(self, value):
        self.selected = value

    def get_label(self):
        return self.label


class HideButton(SmallButton):

    def __init__(self, stdscr, key, text):
        hide_message = "XX CLICK TO READ XXX"
        super(HideButton, self).__init__(stdscr, self.action_on_click, trigger_key=key, label=hide_message)
        self._text = text
        self._pressed = False

    def action_on_click(self, info, selected):
        self.label = self._text
        self._pressed = True

    def update(self, y, x, label='', key=None, mouse=None, color=None):
        if mouse and mouse[1] == y and x <= mouse[0] <= x + len(self.label) + 1:
            self.selected = not self.selected if self.toggle else True
            self.on_click(self.info, selected=self.selected)
            self.highlight_time = time.time()
        if key == ord(self.trigger_key):
            self.selected = not self.selected if self.toggle else True
            self.on_click(self.info, selected=self.selected)
            self.highlight_time = time.time()

        try:
            if not self._pressed:
                self.stdscr.addstr(y, x, '[{key}|{label}]'.format(key=self.trigger_key, label=self.label),
                                   curses.A_REVERSE if self.selected else curses.A_NORMAL)
            else:
                self.stdscr.addstr(y, x, '{label}'.format(label=self.label), curses.A_NORMAL)
        except curses.error:
            pass

        if self.highlight_time and not self.toggle and time.time() - self.highlight_time > 0.1:
            self.selected = False
            self.highlight_time = None


class ButtonList:
    def __init__(self, stdscr, on_click, buttons=[], info={}, linear=False):
        self.buttons = []
        self.on_click = on_click
        self.stdscr = stdscr
        self.info = info
        self._selected = ''
        self.linear = linear
        # Load all buttons
        for button in buttons:
            self.add_button(button)

    def add_button(self, label):
        info_button = deepcopy(self.info)
        info_button['label'] = label
        button = SmallButton(self.stdscr, self.on_click, toggle=True, label=label, info=info_button)
        self.buttons.append(button)

    def update(self, y, x, key, mouse, selected_button, colors=[]):
        # Update selected button
        self._selected = selected_button
        # read color status
        if not colors:
            colors = [None] * len(self.buttons)
        # Show all buttons
        counter_space = 0
        for i, (button, color) in enumerate(zip(self.buttons, colors)):
            name = button.get_label()
            button.set_selected(self._selected == name)
            if self.linear:
                button.update(y, x + counter_space, key=key, mouse=mouse, color=color)
                counter_space += len(name) + 3
            else:
                button.update(y + i, x, key=key, mouse=mouse, color=color)
# EOF
