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
# Page class definition
from .jtopgui import Page
from .lib.common import value_to_string, plot_name_info
from .lib.linear_gauge import linear_frequency_gauge


def get_value_engine(engine):
    return value_to_string(engine['curr'], engine['unit']) if engine['status'] else '[OFF]'


def map_engines(jetson):
    model = jetson.board.info["model"].lower()
    # Check if there is a map for each engine
    if 'agx orin' in model:
        return [
            [('APE', get_value_engine(jetson.engine['APE']['APE'])), ('SE', get_value_engine(jetson.engine['SE']['SE']))],
            [('DLA0c', get_value_engine(jetson.engine['DLA0']['DLA0_CORE'])), ('DLA1c', get_value_engine(jetson.engine['DLA1']['DLA1_CORE']))],
            [('NVENC', get_value_engine(jetson.engine['NVENC']['NVENC'])), ('NVDEC', get_value_engine(jetson.engine['NVDEC']['NVDEC']))],
            [('NVJPG', get_value_engine(jetson.engine['NVJPG']['NVJPG'])), ('NVJPG1', get_value_engine(jetson.engine['NVJPG']['NVJPG1']))],
            [('PVA0a', get_value_engine(jetson.engine['PVA0']['PVA0_CPU_AXI'])), ('VIC', get_value_engine(jetson.engine['VIC']['VIC']))],
        ]
    # Otherwise if not mapped show all engines
    list_engines = []
    for group in jetson.engine:
        list_engines += [[(name, get_value_engine(engine)) for name, engine in jetson.engine[group].items()]]
    return list_engines


def compact_engines(stdscr, pos_x, pos_y, width, jetson):
    map_eng = map_engines(jetson)
    size_map = len(map_eng)
    # Write first line
    if size_map > 0:
        stdscr.hline(pos_y, pos_x + 1, curses.ACS_HLINE, width - 1)
        stdscr.addstr(pos_y, pos_x + (width - 13) // 2, " [HW engines] ", curses.A_BOLD)
        size_map += 1
    # Plot all engines
    for gidx, row in enumerate(map_eng):
        size_eng = width // len(row) - 1
        for idx, (name, value) in enumerate(row):
            plot_name_info(stdscr, pos_y + gidx + 1, pos_x + (size_eng + 1) * idx + 1, name, value)
    return size_map


class ENGINE(Page):

    def __init__(self, stdscr, jetson):
        super(ENGINE, self).__init__("ENG", stdscr, jetson)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Draw all engines
        offset_y = first + 2
        offset_x = 1
        size_gauge = width - 2
        # Draw all engines
        for gidx, group in enumerate(self.jetson.engine):
            engines = self.jetson.engine[group]
            size_eng = size_gauge // len(engines) - 1
            for idx, (name, engine) in enumerate(engines.items()):
                linear_frequency_gauge(self.stdscr, offset_y + gidx * 2, offset_x + (size_eng + 1) * idx, size_eng, name, engine)
# EOF