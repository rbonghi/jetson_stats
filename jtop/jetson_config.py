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

import os
import curses
# Logging
import logging
# Timer
from datetime import datetime, timedelta
# Create logger
logger = logging.getLogger(__name__)
# Gui refresh rate
GUI_REFRESH = 1000 // 20
# Detect user
user = os.environ.get('USER', '')
# Get user from sudo
if 'SUDO_USER' in os.environ:
    user = os.environ['SUDO_USER']

JTOP_MENU = [
    (None, "Check all commands if are installed"),
    (None, "Check folders"),
    (None, "Check variables status"),
    (None, "Check status permissions for {user}".format(user=user)),
    (None, "Status jetson-stats service"),
]


MAIN_PAGE = [
    (JTOP_MENU, "Check the status of jetson-stats"),
    (None, "Enable/Disable boot from desktop"),
    (None, "Update this tool to the latest version"),
    (None, "Information about this configuration tool"),
]


class JTOPCONFIG:

    def __init__(self, stdscr):
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

    def draw_menu_page(self, menu):
        height, width = self.stdscr.getmaxyx()
        center_y = (height - len(menu)) // 2
        # Find center on X axis
        max_description = max([len(x) for _, x in menu])
        center_x = (width - max_description) // 2
        # Draw menu
        for idx, (_, description) in enumerate(menu):
            self.stdscr.addstr(center_y + idx, center_x, description)
        # Draw buttons
        self.stdscr.addstr(center_y + len(menu) + 1, center_x, "<OK>")
        self.stdscr.addstr(center_y + len(menu) + 1, center_x + 10, "<Exit>")

    def loop(self):
        # Here is the loop of our program, we keep clearing and redrawing in this loop
        while not self.events():
            # First, clear the screen
            self.stdscr.erase()
            # Draw menu page
            self.draw_menu_page(MAIN_PAGE)
            # Draw the screen
            self.stdscr.refresh()
            # Set a timeout and read keystroke
            self.stdscr.timeout(GUI_REFRESH)

    def events(self):
        event = self.stdscr.getch()
        # Run keyboard check
        status_mouse = False
        status_keyboard = self.keyboard(event)
        # Clear event mouse
        self.mouse = ()
        # Check event mouse
        if event == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                # Run event menu controller
                #status_mouse = self.event_menu(mx, my)
                self.mouse = (mx, my)
            except curses.error:
                pass
        return status_keyboard

    def keyboard(self, event):
        self.key = event
        if self.old_key != self.key:
            # keyboard check list
            if self.key == ord('q') or self.key == ord('Q') or self.ESC_BUTTON(self.key):
                # keyboard check quit button
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


def main():
    # Run wrapper
    curses.wrapper(JTOPCONFIG)


if __name__ == "__main__":
    main()
# EOF
