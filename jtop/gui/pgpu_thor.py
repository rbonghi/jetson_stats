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

# Thor GPU UI page
# Requires: jtop/core/thor_power.py

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

# Thor GPU UI page
# Requires: jtop/core/thor_power.py

import curses
from .jtopgui import Page
from .lib.common import NColors, size_min, unit_to_string, size_to_string
from .lib.chart import Chart
from .lib.process_table import ProcessTable
from .lib.linear_gauge import basic_gauge, freq_gauge
from .lib.smallbutton import SmallButton
from .pcontrol import color_temperature

from jtop.core.thor_gpu import read_gpu_mem_rows_for_gui
from jtop.core.thor_power import (
    current_governor,
    toggle_governor,
    rail_status,
    toggle_rail,
)


def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data["status"]
    data = {
        "name": "GPU" if idx == 0 else f"GPU{idx}",
        "color": NColors.green() | curses.A_BOLD,
        "values": [(gpu_status["load"], NColors.igreen())],
    }
    if "freq" in gpu_data:
        curr_string = unit_to_string(gpu_data["freq"]["cur"], "k", "Hz")
        stdscr.addstr(pos_y, pos_x + size - 8, curr_string, NColors.italic())
    basic_gauge(stdscr, pos_y, pos_x, size - 10, data, bar=" ")


def compact_gpu(stdscr, pos_y, pos_x, width, jetson, mouse=None):
    """Compact GPU display for summary view."""
    line_counter = 0
    if not jetson.gpu:
        data = {
            "name": "GPU",
            "color": NColors.green() | curses.A_BOLD,
            "online": False,
            "coffline": NColors.igreen(),
            "message": "NVIDIA GPU NOT DETECTED/AVAILABLE",
        }
        basic_gauge(stdscr, pos_y, pos_x, width - 2, data)
        return 1

    # Draw gauge
    for idx, gpu in enumerate(jetson.gpu.values()):
        gpu_gauge(stdscr, pos_y + line_counter, pos_x, width, gpu, idx)
        line_counter += 1

    # Read Thor runtime states
    try:
        gov = (current_governor() or "").strip()
        val3d = "Enabled" if gov != "performance" else "Disabled"
    except Exception:
        val3d = "Unknown"

    try:
        rs = rail_status()
        cv = rs.get("control_value")
        valrg = "Enabled" if cv == "auto" else ("Disabled" if cv == "on" else "Unknown")
    except Exception:
        valrg = "Unknown"

    # Layout
    y = pos_y + line_counter
    label1_x = pos_x + 1
    label1 = "3D scaling: "
    field1 = "{" + val3d + "}"
    field1_x = label1_x + len(label1)
    field1_x_end = field1_x + len(field1) - 1

    label2_x = pos_x + max(width // 2, field1_x_end + 3)
    label2 = "Railgate: "
    field2 = "{" + valrg + "}"
    field2_x = label2_x + len(label2)
    field2_x_end = field2_x + len(field2) - 1

    # Mouse interaction (compact view)
    if mouse:
        mx, my = mouse
        if my == y:
            if label1_x <= mx <= field1_x_end:
                toggle_governor()
            elif label2_x <= mx <= field2_x_end:
                toggle_rail()

    # Draw labels with color highlighting
    try:
        stdscr.addstr(y, label1_x, label1, curses.A_BOLD)
        color_3d = NColors.green() if val3d == "Enabled" else curses.A_NORMAL
        stdscr.addstr(y, field1_x, field1, color_3d)

        if field2_x_end < pos_x + width:
            stdscr.addstr(y, label2_x, label2, curses.A_BOLD)
            color_rail = NColors.green() if valrg == "Enabled" else curses.A_NORMAL
            stdscr.addstr(y, field2_x, field2, color_rail)
    except curses.error:
        pass

    return line_counter + 1


class GPU(Page):
    """Thor-specific GPU page (clickable 3D scaling & Railgate)."""

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        COLOR_GREY = 240 if curses.COLORS >= 256 else curses.COLOR_WHITE
        self.draw_gpus = {}
        for gpu_name in self.jetson.gpu:
            type_gpu = "i" if self.jetson.gpu[gpu_name]["type"] == "integrated" else "d"
            chart = Chart(
                jetson,
                f"{type_gpu}GPU {gpu_name}",
                self.update_chart,
                color_text=curses.COLOR_GREEN,
            )
            button_3d_scaling = SmallButton(
                stdscr, self.action_scaling_3D, info={"name": gpu_name}
            )
            # Shared-only RAM chart (no VRAM)
            chart_ram = (
                Chart(
                    jetson,
                    "GPU Shared RAM",
                    self.update_chart_ram,
                    type_value=float,
                    color_text=curses.COLOR_GREEN,
                    color_chart=[COLOR_GREY, curses.COLOR_GREEN],
                )
                if type_gpu == "i"
                else None
            )
            self.draw_gpus[gpu_name] = {
                "chart": chart,
                "3d_scaling": button_3d_scaling,
                "ram": chart_ram,
            }
        self.process_table = ProcessTable(self.stdscr, self.jetson)
        self._click_regions = {"scaling": [], "railgate": []}

    # Actions

    def action_railgate(self, info, selected):
        toggle_rail()

    def action_scaling_3D(self, info, selected):
        toggle_governor()

    # Chart callbacks

    def update_chart(self, jetson, name):
        gpu_name = name.split(" ")[1]
        gpu_status = jetson.gpu[gpu_name]["status"]
        return {"value": [gpu_status["load"]]}

    def update_chart_ram(self, jetson, name):
        """
        Shared-only series from system memory (no VRAM line).
        Assumes read_gpu_mem_rows_for_gui returns bytes.
        """
        rows = read_gpu_mem_rows_for_gui(device_index=0)
        s_used_b = rows.get("shared_used_b", 0)
        s_total_b = rows.get("shared_total_b", 0)

        # Chart expects start='k' (kB), so convert bytes -> kB for scaling.
        max_val_kb = max(s_total_b // 1024, 1)
        szw, divider_kb, unit = size_min(max_val_kb, start="k")

        # Convert divider (kB) back to bytes for the value division
        divider_bytes = max(divider_kb * 1024, 1)

        return {
            "value": [s_used_b / divider_bytes],  # single-series: Shared only
            "max": szw,
            "unit": unit,
        }

    # Input handling

    def _handle_mouse(self, mouse):
        if not mouse:
            return False
        try:
            mx, my = mouse
            for which, regions in (
                ("scaling", self._click_regions["scaling"]),
                ("railgate", self._click_regions["railgate"]),
            ):
                for (ry, rx1, rx2) in regions:
                    if my == ry and rx1 <= mx <= rx2:
                        if which == "scaling":
                            toggle_governor()
                        else:
                            toggle_rail()
                        return True
        except Exception:
            pass
        return False

    def _handle_hotkeys(self, key):
        if isinstance(key, int):
            if key in (ord("g"), ord("G")):
                toggle_governor()
                return True
            if key in (ord("r"), ord("R")):
                toggle_rail()
                return True
        return False

    # Main draw

    def draw(self, key, mouse):
        # Handle clicks and hotkeys first
        if self._handle_mouse(mouse) or self._handle_hotkeys(key):
            pass

        height, width, first = self.size_page()
        gpu_height = (height * 2 // 3 - 3) // max(1, len(self.jetson.gpu))
        self.stdscr.addstr(first + 1, 1, "Temperatures:", curses.A_NORMAL)

        for name in self.jetson.temperature:
            if "gpu" in name.lower():
                color_temperature(
                    self.stdscr,
                    first + 1,
                    15,
                    name,
                    self.jetson.temperature[name],
                )

        self._click_regions = {"scaling": [], "railgate": []}

        for idx, (gpu_name, gpu_data) in enumerate(self.jetson.gpu.items()):
            chart = self.draw_gpus[gpu_name]["chart"]
            chart_ram = self.draw_gpus[gpu_name]["ram"]
            gpu_status = gpu_data["status"]
            gpu_freq = gpu_data["freq"]

            size_x = [1, width // 2 - 2]
            size_y = [
                first + 2 + idx * (gpu_height + 1),
                first + 2 + (idx + 1) * (gpu_height - 3),
            ]

            label_chart_gpu = f"{gpu_status['load']:>3.0f}% - gov: {gpu_freq.get('governor', '')}"
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)

            if chart_ram:
                # Compose a clear Shared-only label using kB as base (API expects 'k')
                rows = read_gpu_mem_rows_for_gui(device_index=0)
                s_used_b = rows.get("shared_used_b", 0)
                s_total_b = rows.get("shared_total_b", 0)

                # Convert bytes -> kB for size_to_string/start='k'
                s_used_k = max(1, s_used_b // 1024)
                s_total_k = max(1, s_total_b // 1024)

                label_mem = "Shared {s_used}/{s_tot}".format(
                    s_used=size_to_string(s_used_k, "k"),
                    s_tot=size_to_string(s_total_k, "k"),
                )

                chart_ram.draw(
                    self.stdscr,
                    [1 + width // 2, width - 2],
                    size_y,
                    label=label_mem,
                )

            # Clickable toggles
            y = first + 1 + (idx + 1) * gpu_height - 1
            x = 1
            try:
                gov = (current_governor() or "").strip()
                val3d = "Enabled" if gov != "performance" else "Disabled"
            except Exception:
                val3d = "Unknown"
            label = "3D scaling: "
            field = "{" + val3d + "}"
            color_3d = NColors.green() if val3d == "Enabled" else curses.A_NORMAL
            self.stdscr.addstr(y, x, label, curses.A_BOLD)
            self.stdscr.addstr(y, x + len(label), field, color_3d)
            self._click_regions["scaling"].append(
                (y, x + len(label), x + len(label) + len(field) - 1)
            )

            x += width // 4
            try:
                rs = rail_status()
                cv = rs.get("control_value")
                valrg = "Enabled" if cv == "auto" else ("Disabled" if cv == "on" else "Unknown")
            except Exception:
                valrg = "Unknown"
            label = "Railgate: "
            field = "{" + valrg + "}"
            color_rail = NColors.green() if valrg == "Enabled" else curses.A_NORMAL
            self.stdscr.addstr(y, x, label, curses.A_BOLD)
            self.stdscr.addstr(y, x + len(label), field, color_rail)
            self._click_regions["railgate"].append(
                (y, x + len(label), x + len(label) + len(field) - 1)
            )

            label_y = first + 1 + (idx + 1) * gpu_height - 1
            meter_y = label_y - 1

            # Frequency meters (live row above the 3D/Railgate line)
            frq_size = width - 3
            if "GPC" in gpu_freq:
                # allocate right half for GPC lane meters
                size_gpc_gauge = (width - 2) // (2 + len(gpu_freq["GPC"]))
                for gpc_idx, gpc in enumerate(gpu_freq["GPC"]):
                    freq_data = {
                        "name": f"GPC{gpc_idx}",
                        "cur": gpc,
                        "unit": "k",
                        "online": gpc > 0,
                    }
                    freq_gauge(
                        self.stdscr,
                        meter_y,
                        width // 2 + gpc_idx * size_gpc_gauge + 2,
                        size_gpc_gauge - 1,
                        freq_data,
                    )
                frq_size = width // 2
            # Overall frequency meter on the left
            gpu_freq["name"] = "Frq"
            freq_gauge(self.stdscr, meter_y, 1, frq_size, gpu_freq)

        height_table = height - first + 2 + gpu_height
        self.process_table.draw(first + 2 + gpu_height, 0, width, height_table, key, mouse)


# EOF
