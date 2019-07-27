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
from jtop import jtop
# Import gui test
from jtop.gui import JTOPGUI, ALL, GPU, CTRL, INFO


def openGUI(stdscr, jetson):
    # Initialization Menu
    pages = JTOPGUI(stdscr, 500, jetson, [ALL, GPU, CTRL, INFO], start=False)
    return pages


def test_openGUI():
    # Load command line controller
    stdscr = curses.initscr()
    # Initialize colors
    curses.start_color()
    # Run jtop
    with jtop() as jetson:
        # Open JTOPGUI
        pages = openGUI(stdscr, jetson)
        # Start with selected page
        pages.set(0)
    assert True
# EOF
