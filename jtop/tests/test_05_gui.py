# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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

import pytest
import curses
from jtop import jtop
from .conftest import emulate_all_devices
# Import gui test
from ..gui.lib.chart import Chart
from ..gui import JTOPGUI, ALL, GPU, CPU, MEM, ENGINE, CTRL, INFO


@pytest.fixture
def reset_chart():
    Chart.reset_color_counter()


def openGUI(stdscr, jetson):
    # Initialization Menu
    pages = [ALL]
    if jetson.gpu:
        pages += [GPU]
    pages += [CPU, MEM]
    if jetson.engine:
        pages += [ENGINE]
    pages += [CTRL, INFO]
    pages = JTOPGUI(stdscr, jetson, pages, start=False)
    return pages


def test_openGUI(setup_jtop_server, reset_chart):
    # Load command line controller
    stdscr = curses.initscr()
    # Initialize colors
    curses.start_color()
    # Run jtop
    with jtop() as jetson:
        if jetson.ok():
            # Reset counter charts
            Chart.reset_color_counter()
            assert Chart.COLOR_COUNTER == 0
            # Open JTOPGUI
            pages = openGUI(stdscr, jetson)
            # Start with selected page
            pages.set(0)
    assert True


test_openGUI = pytest.mark.parametrize("setup_jtop_server", emulate_all_devices(), indirect=True)(test_openGUI)
# EOF
