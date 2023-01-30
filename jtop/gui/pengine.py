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


def add_engine_in_list(label, engine, group, name):
    return [(label, get_value_engine(engine[group][name]))] if group in engine else []


def pass_agx_orin(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_AXI'),
        add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def map_xavier(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('CVNAS', engine, 'CVNAS', 'CVNAS'),
        add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_AXI'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def map_jetson_nano(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('SE', engine, 'SE', 'SE'),
    ]


MAP_JETSON_MODELS = {
    'agx orin': pass_agx_orin,
    'xavier': map_xavier,
    'jetson nano': map_jetson_nano,
    'nintendo': map_jetson_nano,
}


def engine_model(model):
    for name, func in MAP_JETSON_MODELS.items():
        if name.lower() in model.lower():
            return func
    return None


def map_engines(jetson):
    # Check if there is a map for each engine
    func_list_engines = engine_model(jetson.board['hardware']["Module"])
    if func_list_engines:
        return func_list_engines(jetson.engine)
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
            if name is not None:
                plot_name_info(stdscr, pos_y + gidx + 1, pos_x + (size_eng + 1) * idx + 1, name, value)
    return size_map


class ENGINE(Page):

    def __init__(self, stdscr, jetson):
        super(ENGINE, self).__init__("ENG", stdscr, jetson)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Draw all engines
        offset_y = first + 1
        offset_x = 1
        size_gauge = width - 2
        # Draw all engines
        for gidx, group in enumerate(self.jetson.engine):
            engines = self.jetson.engine[group]
            size_eng = size_gauge // len(engines) - 1
            # Plot all engines
            for idx, (name, engine) in enumerate(engines.items()):
                name_array = name.split("_")
                # Plot block name
                if len(engines) > 1 and len(name_array) > 1:
                    self.stdscr.addstr(offset_y + gidx * 2, offset_x + (size_eng + 1) * idx,
                                       "{group}".format(group=group), curses.color_pair(6) | curses.A_BOLD)
                # Plot Gauge
                new_name = ' '.join(name_array[1:]) if len(name_array) > 1 and len(engines) > 1 else name
                linear_frequency_gauge(self.stdscr, offset_y + gidx * 2 + 1, offset_x + (size_eng + 1) * idx, size_eng, new_name, engine)
# EOF
