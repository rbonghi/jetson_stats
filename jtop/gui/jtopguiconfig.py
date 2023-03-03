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

import re
import curses
# Logging
import logging
# local modules
from ..core.common import get_var
from .lib.colors import NColors
# Create logger
logger = logging.getLogger(__name__)
# Gui refresh rate
COPYRIGHT_RE = re.compile(r""".*__copyright__ = ["'](.*?)['"]""", re.S)
GUI_REFRESH = 1000 // 20

JTOP_MENU_STATUS = 0
JTOP_MENU_EXEC = 1
JTOP_MENU_DESCRIPTION = 2


class JTOPCONFIG:

    def __init__(self, stdscr, main_page):
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        # Initialize variables
        self._current_menu = main_page
        self._previous_menu = main_page
        self._counter_option = 0
        # Initialize keyboard status
        self.key = -1
        self.old_key = -1
        # Initialize mouse
        self.mouse = ()
        # Set curses reference, refresh and jetson controller
        self.stdscr = stdscr
        # In this program, we don't want keystrokes echoed to the console,
        # so we run this to disable that
        curses.noecho()
        # Additionally, we want to make it so that the user does not have to press
        # enter to send keys to our program, so here is how we get keys instantly
        curses.cbreak()
        # Try to hide the cursor
        if hasattr(curses, 'curs_set'):
            try:
                curses.curs_set(0)
            except Exception:
                pass
        # Lastly, keys such as the arrow keys are sent as funny escape sequences to
        # our program. We can make curses give us nicer values (such as curses.KEY_LEFT)
        # so it is easier on us.
        self.stdscr.keypad(True)
        # Enable mouse mask
        _, _ = curses.mousemask(curses.BUTTON1_CLICKED)
        # Refreshing page curses loop
        # https://stackoverflow.com/questions/54409978/python-curses-refreshing-text-with-a-loop
        self.stdscr.nodelay(1)
        # Run loop
        self.loop()

    def draw_menu_page(self, page):
        height, width = self.stdscr.getmaxyx()
        # Draw menu
        menu = []
        if 'menu' in page:
            menu = page['menu']
        # Find center on y axis
        center_y = (height - len(menu)) // 2
        # Find center on X axis
        max_description = max([len(x) for _, _, x in menu]) if len(menu) else 0
        center_x = (width - max_description) // 2
        # Draw menu
        for idx, (status, _, description) in enumerate(menu):
            # Reverse line if counter is the same
            color = curses.A_REVERSE if self._counter_option == idx else curses.A_NORMAL
            # Draw command if not None
            if isinstance(status, str):
                self.stdscr.addstr(center_y + idx, center_x - 9, status, color)
            elif callable(status):
                # Run function and get output
                if 'run_before' in page:
                    cmd_before_out = page['run_before']()
                    status = status(cmd_before_out)
                else:
                    status = status()
                # Print output
                if isinstance(status, bool):
                    message = " OK " if status else "FAIL"
                    color_status = NColors.green() if status else NColors.red()
                    self.stdscr.addstr(center_y + idx, center_x - 6, message, color_status | curses.A_BOLD)
                elif isinstance(status, str):
                    self.stdscr.addstr(center_y + idx, center_x - 6, status)
            # Write description
            self.stdscr.addstr(center_y + idx, center_x, description, color)
        # Draw description
        description_y = 0
        if 'description' in page:
            description = page['description'].split('\n')
            # Find center description
            max_line = max([len(x) for x in description])
            description_center = (max_description - max_line) // 2
            # Draw all lines
            for idx, line in enumerate(description):
                self.stdscr.addstr(center_y - len(description) + idx - 1, center_x + description_center, line)
            description_y = len(description) + 1
        # Draw title
        title = page['title']
        title_center = (max_description - len(title)) // 2
        self.stdscr.addstr(center_y - 2 - description_y, center_x + title_center, title, curses.A_BOLD)
        # Draw buttons
        center_x = (width - 45) // 2
        self.stdscr.addstr(center_y + len(menu) + 1, center_x + 5, "Commands:", curses.A_BOLD)  # Size 9
        if 'menu' in page:
            # Up key
            self.stdscr.addch(center_y + len(menu) + 1, center_x + 30, curses.ACS_UARROW)
            self.stdscr.addstr(center_y + len(menu) + 1, center_x + 32, "Up", curses.A_BOLD)
            # Down key
            self.stdscr.addch(center_y + len(menu) + 2, center_x + 30, curses.ACS_DARROW)
            self.stdscr.addstr(center_y + len(menu) + 2, center_x + 32, "Down", curses.A_BOLD)
            # Enter
            self.stdscr.addstr(center_y + len(menu) + 3, center_x + 30, "ENTER", curses.A_BOLD)
        # Esc button
        message_button = "ESC = Back" if self._current_menu != self._previous_menu else "ESC = exit"
        self.stdscr.addstr(center_y + len(menu) + 1, center_x + 16, "{message}".format(message=message_button), curses.A_BOLD)
        # Quit
        self.stdscr.addstr(center_y + len(menu) + 2, center_x + 16, "q/Q Quit", curses.A_BOLD)
        # Draw copyrights
        self.stdscr.addstr(height - 2, width - 31, "Software parts of jetson-stats", curses.A_NORMAL)
        self.stdscr.addstr(height - 1, width - 28, get_var(COPYRIGHT_RE), curses.A_NORMAL)

    def _print_message(self, title, message):
        return {
            'title': title,
            'description': message
        }

    def loop(self):
        # Here is the loop of our program, we keep clearing and redrawing in this loop
        while not self.events():
            # First, clear the screen
            self.stdscr.erase()
            # Draw menu page
            self.draw_menu_page(self._current_menu)
            # Draw the screen
            self.stdscr.refresh()
            # Set a timeout and read keystroke
            self.stdscr.timeout(GUI_REFRESH)

    def events(self):
        event = self.stdscr.getch()
        # Run keyboard check
        status_keyboard = self.keyboard(event)
        # Clear event mouse
        self.mouse = ()
        # Check event mouse
        if event == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                # Run event menu controller
                self.mouse = (mx, my)
            except curses.error:
                pass
        return status_keyboard

    def keyboard(self, event):
        self.key = event
        if self.old_key != self.key:
            # keyboard check list
            if self.key == ord('q') or self.key == ord('Q'):
                # keyboard check quit button
                return True
            elif self.key == curses.KEY_UP:
                if self._counter_option > 0:
                    self._counter_option -= 1
            elif self.key == curses.KEY_DOWN:
                if self._counter_option + 1 < len(self._current_menu['menu']):
                    self._counter_option += 1
            elif self.key in {curses.KEY_ENTER, 10, 13}:
                cmd = self._current_menu['menu'][self._counter_option][JTOP_MENU_EXEC]
                if isinstance(cmd, dict):
                    self._counter_option = 0
                    self._previous_menu = self._current_menu
                    self._current_menu = cmd
                elif callable(cmd):
                    # Execute command
                    output = cmd()
                    if output:
                        title = self._current_menu['menu'][self._counter_option][JTOP_MENU_DESCRIPTION]
                        data = self._print_message(title, output)
                        self._counter_option = 0
                        self._previous_menu = self._current_menu
                        self._current_menu = data
            elif self.ESC_BUTTON(self.key):
                if self._current_menu != self._previous_menu:
                    self._current_menu = self._previous_menu
                    self._counter_option = 0
                else:
                    return True
            # Store old value key
            self.old_key = self.key
        return False

    def ESC_BUTTON(self, key):
        """
            Check there is another character prevent combination ALT + <OTHER CHR>
            https://stackoverflow.com/questions/5977395/ncurses-and-esc-alt-keys
        """
        if key == 27:
            n = self.stdscr.getch()
            if n == -1:
                return True
        return False
# EOF
