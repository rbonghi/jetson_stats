# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import curses
# Graphics elements
from .jtopguilib import (check_size,
                         check_curses)


class JTOPGUI:

    def __init__(self, stdscr, refresh, pages, init_page=0):
        self.stdscr = stdscr
        self.pages = pages
        self.n_page = init_page
        self.refresh = refresh
        self.key = -1
        self.old_key = -1

    @check_size(20, 50)
    def draw(self, jetson):
        # First, clear the screen
        self.stdscr.erase()
        # Write head of the jtop
        self.header(jetson)
        # Write page selected
        if "func" in self.pages[self.n_page]:
            page = self.pages[self.n_page]["func"]
            if page is not None:
                page(self.stdscr, jetson, self.key)
        # Draw menu
        self.menu()
        # Draw the screen
        self.stdscr.refresh()
        # Set a timeout and read keystroke
        self.stdscr.timeout(self.refresh)

    def increase(self):
        idx = self.n_page + 1
        self.set(idx + 1)

    def decrease(self):
        idx = self.n_page + 1
        self.set(idx - 1)

    def set(self, idx):
        if idx <= len(self.pages) and idx > 0:
            self.n_page = idx - 1

    @check_curses
    def header(self, jetson):
        board = jetson.board["board"]
        board_info = board["name"] + " - Jetpack " + board["jetpack"]
        self.stdscr.addstr(0, 0, board_info, curses.A_BOLD)
        if jetson.userid != 0:
            self.stdscr.addstr(0, len(board_info) + 1, "- PLEASE RUN WITH SUDO", curses.color_pair(1))

    @check_curses
    def menu(self):
        height, width = self.stdscr.getmaxyx()
        # Set background for all menu line
        self.stdscr.addstr(height - 1, 0, ("{0:<" + str(width - 1) + "}").format(" "), curses.A_REVERSE)
        position = 1
        for idx, page in enumerate(self.pages):
            name = page["name"]
            if self.n_page != idx:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=name), curses.A_REVERSE)
            else:
                self.stdscr.addstr(height - 1, position, ("{idx} {name}").format(idx=idx + 1, name=name))
            position += len(name) + 2
            self.stdscr.addstr(height - 1, position, " - ", curses.A_REVERSE)
            position += 3
        # Add close option menu
        self.stdscr.addstr(height - 1, position, "Q to close", curses.A_REVERSE)
        # Author name
        name_author = "Raffaello Bonghi"
        self.stdscr.addstr(height - 1, width - len(name_author), name_author, curses.A_REVERSE)

    def keyboard(self, jetson):
        self.key = self.stdscr.getch()
        if self.old_key != self.key:
            # keyboard check list
            if self.key == curses.KEY_LEFT:
                self.decrease()
            elif self.key == curses.KEY_RIGHT:
                self.increase()
            elif self.key in [ord(str(n)) for n in range(10)]:
                num = int(chr(self.key))
                self.set(num)
            elif self.key == ord('q') or self.key == ord('Q'):
                # keyboard check quit button
                return False
            else:
                # Run extra control for page if exist
                for page in self.pages:
                    if "key" in page:
                        # Run key controller
                        page["key"](self.stdscr, jetson, self.key)
            # Store old value key
            self.old_key = self.key
        return True
# EOF
