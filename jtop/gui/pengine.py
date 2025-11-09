# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2026 Raffaello Bonghi.
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
import re

# Page class definition
from .jtopgui import Page
from .lib.colors import NColors
from .lib.common import unit_to_string, plot_name_info
from .lib.linear_gauge import freq_gauge

# Use shared BPMP helper (cached per call)
try:
    from ..core.bpmp import BpmpSnapshot
except Exception:
    BpmpSnapshot = None

# Thor helpers

def _read_bpmp_clk_rate(clk_name: str):
    """Use shared BPMP snapshot to avoid re-reading clk_tree on each call."""
    if not BpmpSnapshot:
        return None
    snap = BpmpSnapshot()
    return snap.rate_hz(clk_name)


def _hz_to_mhz_str(hz):
    if not isinstance(hz, int) or hz <= 0:
        return None
    mhz = round(hz / 1_000_000)
    return f"{mhz}MHz"


# existing core helpers

def get_value_engine(engine):
    return unit_to_string(engine["cur"], "k", "Hz") if engine["online"] else "[OFF]"


def add_engine_in_list(label, engine, group, name):
    """
    Original behavior, plus: `name` may be a string or a list/tuple of alias names.
    We will pick the first that exists inside engine[group].
    """
    if group not in engine:
        return []
    names = name if isinstance(name, (list, tuple)) else [name]
    return next(
        ([(label, get_value_engine(engine[group][n]))] for n in names if n in engine[group]),
        [],
    )

# Convenience: directly add a label/value pair (used for VIC BPMP fallback)
def _add_label_value(label, value):
    return [] if value is None else [(label, value)]

# Jetson mappings
def pass_thor(engine):
    """Jetson Thor engine mapping – adds aliases + live VIC via BPMP fallback."""
    rows = [
        # Audio Processing Engine – typically ON/OFF
        add_engine_in_list("APE", engine, "APE", "APE"),
        # Codecs – try common aliases (MSENC sometimes backs NVENC)
        (
            add_engine_in_list("NVENC", engine, "NVENC", ["NVENC", "MSENC"])
            + add_engine_in_list("NVDEC", engine, "NVDEC", ["NVDEC"])
        ),
        # JPEG – some SKUs expose NVJPG1 as a second block
        (
            add_engine_in_list("NVJPG", engine, "NVJPG", ["NVJPG", "NVJPG0"])
            + add_engine_in_list("NVJPG1", engine, "NVJPG", ["NVJPG1"])
        ),
        # Security + (we’ll append VIC below with a BPMP fallback if needed)
        add_engine_in_list("SE", engine, "SE", ["SE", "SE0", "SE1"]),
    ]

    # Vision/OFA blocks commonly used on Thor
    rows.append(add_engine_in_list("PVA0", engine, "PVA0", ["PVA0_CPU_AXI", "PVA0"]))
    rows.append(add_engine_in_list("OFA", engine, "OFA", ["OFA"]))

    # VIC – prefer devfreq (cur_freq) if present; otherwise parse BPMP clock tree
    vic = add_engine_in_list("VIC", engine, "VIC", "VIC")
    if not vic:
        # No devfreq entry: try BPMP to still show live MHz
        mhz_str = _hz_to_mhz_str(_read_bpmp_clk_rate("vic"))
        vic = _add_label_value("VIC", mhz_str) if mhz_str else []
    rows.append(vic)

    # Filter out any empty sublists to keep UI rendering robust
    return [row for row in rows if row]


def pass_orin(engine):
    return [
        (
            add_engine_in_list("APE", engine, "APE", "APE")
            + add_engine_in_list("PVA0a", engine, "PVA0", "PVA0_CPU_AXI")
        ),
        (
            add_engine_in_list("DLA0c", engine, "DLA0", "DLA0_CORE")
            + add_engine_in_list("DLA1c", engine, "DLA1", "DLA1_CORE")
        ),
        (
            add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
            + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
        ),
        (
            add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
            + add_engine_in_list("NVJPG1", engine, "NVJPG", "NVJPG1")
        ),
        (
            add_engine_in_list("SE", engine, "SE", "SE")
            + add_engine_in_list("VIC", engine, "VIC", "VIC")
        ),
    ]


def pass_orin_nx(engine):
    if "DLA0" in engine:
        return [
            (
                add_engine_in_list("APE", engine, "APE", "APE")
                + add_engine_in_list("PVA0a", engine, "PVA0", "PVA0_CPU_AXI")
            ),
            (
                add_engine_in_list("DLA0c", engine, "DLA0", "DLA0_CORE")
                + add_engine_in_list("DLA1c", engine, "DLA1", "DLA1_CORE")
            ),
            (
                add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
                + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
            ),
            (
                add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
                + add_engine_in_list("NVJPG1", engine, "NVJPG", "NVJPG1")
            ),
            (
                add_engine_in_list("SE", engine, "SE", "SE")
                + add_engine_in_list("VIC", engine, "VIC", "VIC")
            ),
        ]
    else:
        return [
            (
                add_engine_in_list("APE", engine, "APE", "APE")
                + add_engine_in_list("PVA0a", engine, "PVA0", "PVA0_CPU_AXI")
            ),
            (
                add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
                + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
            ),
            (
                add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
                + add_engine_in_list("NVJPG1", engine, "NVJPG", "NVJPG1")
            ),
            (
                add_engine_in_list("SE", engine, "SE", "SE")
                + add_engine_in_list("VIC", engine, "VIC", "VIC")
            ),
        ]


def pass_orin_nano(engine):
    return [
        add_engine_in_list("APE", engine, "APE", "APE"),
        (
            add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
            + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
        ),
        (
            add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
            + add_engine_in_list("NVJPG1", engine, "NVJPG", "NVJPG1")
        ),
        (
            add_engine_in_list("SE", engine, "SE", "SE")
            + add_engine_in_list("VIC", engine, "VIC", "VIC")
        ),
    ]


def map_xavier(engine):
    return [
        (
            add_engine_in_list("APE", engine, "APE", "APE")
            + add_engine_in_list("CVNAS", engine, "CVNAS", "CVNAS")
        ),
        (
            add_engine_in_list("DLA0c", engine, "DLA0", "DLA0_CORE")
            + add_engine_in_list("DLA1c", engine, "DLA1", "DLA1_CORE")
        ),
        (
            add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
            + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
        ),
        (
            add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
            + add_engine_in_list("PVA0a", engine, "PVA0", "PVA0_AXI")
        ),
        (
            add_engine_in_list("SE", engine, "SE", "SE")
            + add_engine_in_list("VIC", engine, "VIC", "VIC")
        ),
    ]


def map_jetson_nano(engine):
    return [
        add_engine_in_list("APE", engine, "APE", "APE"),
        (
            add_engine_in_list("NVENC", engine, "NVENC", "NVENC")
            + add_engine_in_list("NVDEC", engine, "NVDEC", "NVDEC")
        ),
        (
            add_engine_in_list("NVJPG", engine, "NVJPG", "NVJPG")
            + add_engine_in_list("SE", engine, "SE", "SE")
        ),
    ]


MAP_JETSON_MODELS = {
    "thor": pass_thor,
    "orin nano": pass_orin_nano,
    "orin nx": pass_orin_nx,
    "agx orin": pass_orin,
    "xavier": map_xavier,
    "jetson nano": map_jetson_nano,
    "nintendo": map_jetson_nano,
    "jetson tx": map_jetson_nano,
}


def engine_model(model):
    for name, func in MAP_JETSON_MODELS.items():
        if name.lower() in model.lower():
            return func
    return None


def map_engines(jetson):
    """Map the hardware engines for the detected Jetson model."""
    func_list_engines = engine_model(jetson.board["hardware"]["Module"])
    try:
        if func_list_engines:
            return func_list_engines(jetson.engine)
    except KeyError:
        pass

    # Otherwise, if not mapped, show all engines (skip empty groups)
    return [
        row
        for row in (
            [(name, get_value_engine(engine)) for name, engine in group.items()]
            for group in jetson.engine.values()
        )
        if row
    ]


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
        if len(row) == 0:  # Skip empty rows to avoid division by zero
            continue
        size_eng = size_table // len(row) - 1
        for idx, (name, value) in enumerate(row):
            if name is not None:
                color = curses.A_NORMAL if "[OFF]" in value else NColors.green() | curses.A_BOLD
                plot_name_info(
                    stdscr,
                    pos_y + gidx + 1,
                    center_x - size_table // 2 + (size_eng + 1) * idx + 1,
                    name,
                    value,
                    color=color,
                )
    return size_map


class ENGINE(Page):
    def __init__(self, stdscr, jetson):
        super().__init__("ENG", stdscr, jetson)

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
                        self.stdscr.addstr(
                            offset_y + gidx * 2,
                            offset_x + (size_eng + 1) * idx,
                            f"{group}",
                            NColors.cyan() | curses.A_BOLD,
                        )
                except curses.error:
                    pass
                # Plot Gauge
                new_name = " ".join(name_array[1:]) if len(name_array) > 1 and len(engines) > 1 else name
                # Add name in plot string
                engine["name"] = new_name
                try:
                    freq_gauge(
                        self.stdscr,
                        offset_y + gidx * 2 + 1,
                        offset_x + (size_eng + 1) * idx,
                        size_eng,
                        engine,
                    )
                except curses.error:
                    pass


# EOF
