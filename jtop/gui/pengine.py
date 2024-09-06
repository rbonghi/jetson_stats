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
from .lib.colors import NColors
from .lib.common import unit_to_string, plot_name_info
from .lib.linear_gauge import freq_gauge


def get_value_engine(engine):
    return unit_to_string(engine['cur'], 'k', 'Hz') if engine['online'] else '[OFF]'


def add_engine_in_list(label, engine, group, name):
    return [(label, get_value_engine(engine[group][name]))] if group in engine else []


def pass_orin(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_CPU_AXI'),
        add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def pass_orin_nx(engine):
    if 'DLA0' in engine:
        return [
            add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_CPU_AXI'),
            add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
            add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
            add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
            add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
        ]
    else:
        return [
            add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_CPU_AXI'),
            add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
            add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
            add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
        ]


def pass_orin_nano(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE'),
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
    'orin nano': pass_orin_nano,
    'orin nx': pass_orin_nx,
    'agx orin': pass_orin,
    'xavier': map_xavier,
    'jetson nano': map_jetson_nano,
    'nintendo': map_jetson_nano,
    'jetson tx': map_jetson_nano,
}


def engine_model(model):
    for name, func in MAP_JETSON_MODELS.items():
        if name.lower() in model.lower():
            return func
    return None


def map_engines(jetson):
    # Check if there is a map for each engine
    func_list_engines = engine_model(jetson.board['hardware']["Module"])
    try:
        if func_list_engines:
            return func_list_engines(jetson.engine)
    except KeyError:
        pass
    # Otherwise if not mapped show all engines
    list_engines = []
    for group in jetson.engine:
        list_engines += [[(name, get_value_engine(engine)) for name, engine in jetson.engine[group].items()]]
    return list_engines


def compact_engines(stdscr, pos_y, pos_x, width, height, jetson):
    center_x = pos_x + width // 2
    map_eng = map_engines(jetson)
    size_map = len(map_eng)
    # Write first line
    if size_map > 0:
        stdscr.addstr(pos_y, center_x - 7, " [HW engines] ", curses.A_BOLD)
        size_map += 1
    # Plot all engines
    size_table = 26
    for gidx, row in enumerate(map_eng):
        size_eng = size_table // len(row) - 1
        for idx, (name, value) in enumerate(row):
            if name is not None:
                color = curses.A_NORMAL if '[OFF]' in value else NColors.green() | curses.A_BOLD
                plot_name_info(stdscr, pos_y + gidx + 1, center_x - size_table // 2 + (size_eng + 1) * idx + 1, name, value, color=color)
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
                try:
                    if len(engines) > 1 and len(name_array) > 1:
                        self.stdscr.addstr(offset_y + gidx * 2, offset_x + (size_eng + 1) * idx,
                                           "{group}".format(group=group), NColors.cyan() | curses.A_BOLD)
                except curses.error:
                    pass
                # Plot Gauge
                new_name = ' '.join(name_array[1:]) if len(name_array) > 1 and len(engines) > 1 else name
                # Add name in plot string
                engine['name'] = new_name
                try:
                    freq_gauge(self.stdscr, offset_y + gidx * 2 + 1, offset_x + (size_eng + 1) * idx, size_eng, engine)
                except curses.error:
                    pass
# EOF
