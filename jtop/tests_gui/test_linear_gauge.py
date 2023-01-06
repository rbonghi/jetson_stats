# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2023 Raffaello Bonghi.
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
# GUI jtop interface
from ..gui import JTOPGUI, Page
from ..gui.lib.linear_gauge import linear_gauge
# jtop client
from ..jtop import jtop

# How to run
# python3 -m jtop.tests_gui.test_linear_gauge


class TestPage(Page):

    def __init__(self, stdscr, jetson):
        super(TestPage, self).__init__("Test", stdscr, jetson)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Print a linear gauge
        for idx in range(21):
            linear_gauge(self.stdscr, offset=first + 1 + idx, start=0, size=width, value=idx * 5)


def main():

    with jtop() as jetson:
        curses.wrapper(JTOPGUI, jetson, [TestPage])


if __name__ == "__main__":
    main()
# EOF
