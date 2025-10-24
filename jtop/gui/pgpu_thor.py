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
# Graphics elements
from .lib.common import NColors, plot_name_info, size_min, unit_to_string, size_to_string
from .lib.chart import Chart
from .lib.process_table import ProcessTable
from .lib.linear_gauge import basic_gauge, freq_gauge
from .lib.smallbutton import SmallButton
from .pcontrol import color_temperature

from jtop.core.thor_power import (
    current_governor,
    toggle_governor,
    rail_status,
    toggle_rail,
)

def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data['status']
    data = {
        'name': 'GPU' if idx == 0 else 'GPU{idx}'.format(idx=idx),
        'color': NColors.green() | curses.A_BOLD,
        'values': [(gpu_status['load'], NColors.igreen())],
    }
    if 'freq' in gpu_data:
        curr_string = unit_to_string(gpu_data['freq']['cur'], 'k', 'Hz')
        stdscr.addstr(pos_y, pos_x + size - 8, curr_string, NColors.italic())
    basic_gauge(stdscr, pos_y, pos_x, size - 10, data, bar=" ")

# MODIFIED FUNCTION
# Now accepts 'mouse=None' and draws/handles clicks for the clickable labels.
def compact_gpu(stdscr, pos_y, pos_x, width, jetson, mouse=None):
    line_counter = 0
    if not jetson.gpu:
        data = {
            'name': 'GPU',
            'color': NColors.green() | curses.A_BOLD,
            'online': False,
            'coffline': NColors.igreen(),
            'message': 'NVIDIA GPU NOT DETECTED/AVAILABLE',
        }
        basic_gauge(stdscr, pos_y, pos_x, width - 2, data)
        return 1

    # Draw GPU Gauge (original)
    for idx, gpu in enumerate(jetson.gpu.values()):
        gpu_gauge(stdscr, pos_y + line_counter, pos_x, width, gpu, idx)
        line_counter += 1

    # Get current states
    try:
        val3d = current_governor() or "N/A"
    except Exception:
        val3d = "N/A"
    
    try:
        rs = rail_status()
        cv = rs.get("control_value")
        valrg = "Enabled" if cv == "auto" else ("Disabled" if cv == "on" else "Unknown")
    except Exception:
        valrg = "Unknown"

    # Define layout
    y = pos_y + line_counter
    label1_x = pos_x + 1
    label1 = "3D scaling: "
    field1 = "{" + val3d + "}"
    field1_x = label1_x + len(label1)
    field1_x_end = field1_x + len(field1) - 1

    # Position the second label relative to the middle
    label2_x = pos_x + max(width // 2, field1_x_end + 3) # ensure no overlap
    label2 = "Railgate: "
    field2 = "{" + valrg + "}"
    field2_x = label2_x + len(label2)
    field2_x_end = field2_x + len(field2) - 1

    # Handle clicks
    if mouse:
        mx, my = mouse
        if my == y:
            # Check click on 3D scaling
            if label1_x <= mx <= field1_x_end:
                try:
                    toggle_governor()
                except Exception:
                    pass
            # Check click on Railgate
            elif label2_x <= mx <= field2_x_end:
                try:
                    toggle_rail()
                except Exception:
                    pass
    
    # Draw labels
    try:
        stdscr.addstr(y, label1_x, label1, curses.A_BOLD)
        stdscr.addstr(y, field1_x, field1)
        # Only draw second label if it fits
        if field2_x_end < pos_x + width:
            stdscr.addstr(y, label2_x, label2, curses.A_BOLD)
            stdscr.addstr(y, field2_x, field2)
    except curses.error:
        pass

    return line_counter + 1 # Add one more line for the labels

class GPU(Page):
    """Thor-specific GPU page (clickable 3D scaling & Railgate)."""

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        COLOR_GREY = 240 if curses.COLORS >= 256 else curses.COLOR_WHITE
        self.draw_gpus = {}
        for gpu_name in self.jetson.gpu:
            type_gpu = "i" if self.jetson.gpu[gpu_name]['type'] == 'integrated' else 'd'
            chart = Chart(jetson, "{t}GPU {name}".format(t=type_gpu, name=gpu_name), self.update_chart,
                          color_text=curses.COLOR_GREEN)
            button_3d_scaling = SmallButton(stdscr, self.action_scaling_3D, info={'name': gpu_name})
            if type_gpu == 'i':
                chart_ram = Chart(jetson, "GPU Shared RAM", self.update_chart_ram,
                                  type_value=float,
                                  color_text=curses.COLOR_GREEN,
                                  color_chart=[COLOR_GREY, curses.COLOR_GREEN])
            else:
                chart_ram = None
            self.draw_gpus[gpu_name] = {'chart': chart, '3d_scaling': button_3d_scaling, 'ram': chart_ram}
        self.process_table = ProcessTable(self.stdscr, self.jetson)
        # clickable regions for braces {…}
        self._click_regions = {"scaling": [], "railgate": []}

    # keep same API used by smallbutton in case it’s still referenced
    def action_railgate(self, info, selected):
        try:
            toggle_rail()
        except Exception:
            pass

    def action_scaling_3D(self, info, selected):
        try:
            toggle_governor()
        except Exception:
            pass

    def update_chart(self, jetson, name):
        gpu_name = name.split(" ")[1]
        gpu_data = jetson.gpu[gpu_name]
        gpu_status = gpu_data['status']
        return {'value': [gpu_status['load']]}

    def update_chart_ram(self, jetson, name):
        parameter = jetson.memory['RAM']
        max_val = parameter.get("tot", 100)
        cpu_val = parameter.get("used", 0)
        use_val = parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start='k')
        used_out = (cpu_val) / divider
        gpu_out = (use_val) / divider
        return {'value': [used_out, gpu_out], 'max': szw, 'unit': unit}

    # Renamed from _handle_clicks and now accepts 'mouse' tuple
    def _handle_mouse(self, mouse):
        if mouse:  # Check if the mouse tuple is not empty
            try:
                mx, my = mouse  # Unpack coordinates
                # Original click-checking logic
                for which, regions in (("scaling", self._click_regions.get("scaling", [])),
                                        ("railgate", self._click_regions.get("railgate", []))):
                    for (ry, rx1, rx2) in regions:
                        if my == ry and rx1 <= mx <= rx2:
                            try:
                                toggle_governor() if which == "scaling" else toggle_rail()
                            except Exception:
                                pass
                            return True  # Click was handled
            except Exception:
                pass
        return False

    # Extracted hotkey logic from old _handle_clicks
    def _handle_hotkeys(self, key):
        if isinstance(key, int):
            if key in (ord('g'), ord('G')):
                try: toggle_governor()
                except Exception: pass
                return True
            if key in (ord('r'), ord('R')):
                try: toggle_rail()
                except Exception: pass
                return True
        return False

    def draw(self, key, mouse):
        # Pass 'mouse' to mouse handler, 'key' to hotkey handler
        if self._handle_mouse(mouse) or self._handle_hotkeys(key):
            # UI will redraw with new values
            pass

        height, width, first = self.size_page()
        gpu_height = (height * 2 // 3 - 3) // max(1, len(self.jetson.gpu))

        self.stdscr.addstr(first + 1, 1, "Temperatures:", curses.A_NORMAL)
        for idx, name in enumerate(self.jetson.temperature):
            if 'gpu' in name.lower():
                sensor = self.jetson.temperature[name]
                color_temperature(self.stdscr, first + 1, 15, name, sensor)

        # reset regions each frame
        self._click_regions = {"scaling": [], "railgate": []}

        # Draw GPUs
        for idx, (gpu_name, gpu_data) in enumerate(self.jetson.gpu.items()):
            chart = self.draw_gpus[gpu_name]['chart']
            chart_ram = self.draw_gpus[gpu_name]['ram']
            gpu_status = gpu_data['status']
            gpu_freq = gpu_data['freq']

            size_x = [1, width // 2 - 2]
            size_y = [first + 2 + idx * (gpu_height + 1), first + 2 + (idx + 1) * (gpu_height - 3)]

            governor = gpu_freq.get('governor', '')
            label_chart_gpu = "{percent: >3.0f}% - gov: {governor}".format(percent=gpu_status['load'], governor=governor)
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)

            size_x_ram = [1 + width // 2, width - 2]
            mem_data = self.jetson.memory['RAM']
            total = size_to_string(mem_data['tot'], 'k')
            shared = size_to_string(mem_data['shared'], 'k')
            if chart_ram is not None:
                chart_ram.draw(self.stdscr, size_x_ram, size_y, label="{used}/{total}B".format(used=shared, total=total))

            button_position = width // 4
            button_idx = 0


            # 3D scaling — clickable { … }
            y = first + 1 + (idx + 1) * gpu_height - 1
            x = 1 + button_idx
            try:
                gov = (current_governor() or "").strip()
                val3d = "Enabled" if gov != "performance" else "Disabled"
            except Exception:
                val3d = "Unknown"
            label = "3D scaling: "
            field = "{" + val3d + "}"
            try:
                self.stdscr.addstr(y, x, label, curses.A_BOLD)
                color = NColors.green() if val3d == "Enabled" else curses.A_NORMAL
                self.stdscr.addstr(y, x + len(label), field, color)
            except curses.error:
                pass
            self._click_regions["scaling"].append((y, x + len(label), x + len(label) + len(field) - 1))
            button_idx += button_position


            # Railgate — clickable { … }
            y = first + 1 + (idx + 1) * gpu_height - 1
            x = 1 + button_idx
            try:
                rs = rail_status()
                cv = rs.get("control_value")
                valrg = "Enabled" if cv == "auto" else ("Disabled" if cv == "on" else "Unknown")
            except Exception:
                valrg = "Unknown"
            label = "Railgate: "
            field = "{" + valrg + "}"
            try:
                color = NColors.green() if valrg == "Enabled" else curses.A_NORMAL
                self.stdscr.addstr(y, x, label, curses.A_BOLD)
                self.stdscr.addstr(y, x + len(label), field, color)
            except curses.error:
                pass
            self._click_regions["railgate"].append((y, x + len(label), x + len(label) + len(field) - 1))
            button_idx += button_position

            # Power control (informational)
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx,
                           "Power ctrl", gpu_data.get('power_control', 'runtime_pm'))
            button_idx += button_position

            # Optional: GPC lanes frequency gauge remains unchanged if present
            frq_size = width - 3
            if 'GPC' in gpu_freq:
                size_gpc_gauge = (width - 2) // (2 + len(gpu_freq['GPC']))
                for gpc_idx, gpc in enumerate(gpu_freq['GPC']):
                    freq_data = {'name': 'GPC{idx}'.format(idx=gpc_idx), 'cur': gpc, 'unit': 'k', 'online': gpc > 0}
                    freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height,
                               width // 2 + gpc_idx * (size_gpc_gauge) + 2, size_gpc_gauge - 1, freq_data)
                frq_size = width // 2

            gpu_freq['name'] = "Frq"
            freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height, 1, frq_size, gpu_freq)

        height_table = height - first + 2 + gpu_height
        self.process_table.draw(first + 2 + gpu_height, 0, width, height_table, key, mouse)
# EOF

