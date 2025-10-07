# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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
from .jtopgui import Page
# Graphics elements
from .lib.common import NColors, plot_name_info, size_min, unit_to_string, size_to_string
from .lib.chart import Chart
from .lib.process_table import ProcessTable
from .lib.linear_gauge import basic_gauge, freq_gauge
from .lib.smallbutton import SmallButton
from .pcontrol import color_temperature


def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data['status']
    # Data gauge
    data = {
        'name': 'GPU' if idx == 0 else 'GPU{idx}'.format(idx=idx),
        'color': NColors.green() | curses.A_BOLD,
        'values': [(gpu_status['load'], NColors.igreen())],
    }
    if 'freq' in gpu_data:
        # Draw current frequency
        curr_string = unit_to_string(gpu_data['freq']['cur'], 'k', 'Hz')
        stdscr.addstr(pos_y, pos_x + size - 8, curr_string, NColors.italic())
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 10, data, bar=" ")


def compact_gpu(stdscr, pos_y, pos_x, width, jetson):
    line_counter = 0
    # Status all GPUs
    if jetson.gpu:
        for idx, gpu in enumerate(jetson.gpu.values()):
            gpu_gauge(stdscr, pos_y + line_counter, pos_x, width, gpu, idx)
            line_counter += 1
    else:
        data = {
            'name': 'GPU',
            'color': NColors.green() | curses.A_BOLD,
            'online': False,
            'coffline': NColors.igreen(),
            'message': 'NVIDIA GPU NOT DETECTED/AVAILABLE',
        }
        basic_gauge(stdscr, pos_y, pos_x, width - 2, data)
        line_counter = 1
    return line_counter


class GPU(Page):

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        # Check if grey exist otherwise use white
        COLOR_GREY = 240 if curses.COLORS >= 256 else curses.COLOR_WHITE
        # Initialize GPU chart
        self.draw_gpus = {}
        for gpu_name in self.jetson.gpu:
            type_gpu = "i" if self.jetson.gpu[gpu_name]['type'] == 'integrated' else 'd'
            chart = Chart(jetson, "{t}GPU {name}".format(t=type_gpu, name=gpu_name), self.update_chart,
                          color_text=curses.COLOR_GREEN)
            # button_railgate = SmallButton(stdscr, self.action_railgate, info={'name': gpu_name})
            button_3d_scaling = SmallButton(stdscr, self.action_scaling_3D, info={'name': gpu_name})
            if type_gpu == 'i':
                chart_ram = Chart(jetson, "GPU Shared RAM", self.update_chart_ram,
                                  type_value=float,
                                  color_text=curses.COLOR_GREEN,
                                  color_chart=[COLOR_GREY, curses.COLOR_GREEN])
            else:
                chart_ram = None
            self.draw_gpus[gpu_name] = {'chart': chart, '3d_scaling': button_3d_scaling, 'ram': chart_ram}
        # Add Process table
        self.process_table = ProcessTable(self.stdscr, self.jetson)

    def action_railgate(self, info, selected):
        # Read current status railgate
        status_railgate = not self.jetson.gpu.get_railgate(info['name'])
        # Set new railgate
        self.jetson.gpu.set_railgate(info['name'], status_railgate)

    def action_scaling_3D(self, info, selected):
        # Read current status 3d_scaling
        status_3d_scaling = not self.jetson.gpu.get_scaling_3D(info['name'])
        # Set new 3d_scaling
        self.jetson.gpu.set_scaling_3D(info['name'], status_3d_scaling)

    def update_chart(self, jetson, name):
        # Decode GPU name
        gpu_name = name.split(" ")[1]
        gpu_data = jetson.gpu[gpu_name]
        gpu_status = gpu_data['status']
        # Append in list
        return {
            'value': [gpu_status['load']],
        }

    def update_chart_ram(self, jetson, name):
        parameter = jetson.memory['RAM']
        # Get max value if is present
        max_val = parameter.get("tot", 100)
        # Get value
        cpu_val = parameter.get("used", 0)
        use_val = parameter.get("shared", 0)
        szw, divider, unit = size_min(max_val, start='k')
        # Append in list
        used_out = (cpu_val) / divider
        gpu_out = (use_val) / divider
        return {
            'value': [used_out, gpu_out],
            'max': szw,
            'unit': unit
        }

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Measure height
        gpu_height = (height * 2 // 3 - 3) // len(self.jetson.gpu)
        # Plot all GPU temperatures
        self.stdscr.addstr(first + 1, 1, "Temperatures:", curses.A_NORMAL)
        for idx, name in enumerate(self.jetson.temperature):
            if 'gpu' in name.lower():
                sensor = self.jetson.temperature[name]
                color_temperature(self.stdscr, first + 1, 15, name, sensor)
        # Draw all GPU
        for idx, (gpu_name, gpu_data) in enumerate(self.jetson.gpu.items()):
            chart = self.draw_gpus[gpu_name]['chart']
            chart_ram = self.draw_gpus[gpu_name]['ram']
            gpu_status = gpu_data['status']
            gpu_freq = gpu_data['freq']
            # Set size chart gpu
            size_x = [1, width // 2 - 2]
            size_y = [first + 2 + idx * (gpu_height + 1), first + 2 + (idx + 1) * (gpu_height - 3)]
            # Print status CPU
            governor = gpu_freq.get('governor', '')
            label_chart_gpu = "{percent: >3.0f}% - gov: {governor}".format(percent=gpu_status['load'], governor=governor)
            # Draw GPU chart
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)
            # Draw GPU RAM chart
            size_x_ram = [1 + width // 2, width - 2]
            mem_data = self.jetson.memory['RAM']
            total = size_to_string(mem_data['tot'], 'k')
            shared = size_to_string(mem_data['shared'], 'k')
            chart_ram.draw(self.stdscr, size_x_ram, size_y, label="{used}/{total}B".format(used=shared, total=total))
            # Print all status GPU
            button_position = width // 4
            button_idx = 0
            # 3D scaling - Check if NVML is being used
            if gpu_data.get('power_control') == 'nvml':
                # NVML mode - show as unavailable
                plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "3D scaling", "N/A (NVML)")
            else:
                # Traditional mode - show button
                scaling_string = "Active" if gpu_status['3d_scaling'] else "Disable"
                scaling_status = NColors.green() if gpu_status['3d_scaling'] else curses.A_NORMAL
                try:
                    self.stdscr.addstr(first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "3D scaling:", curses.A_BOLD)
                    self.draw_gpus[gpu_name]['3d_scaling'].update(first + 1 + (idx + 1) * gpu_height - 1, 12 + button_idx,
                                                                  scaling_string, key=key, mouse=mouse, color=scaling_status)
                except curses.error:
                    pass
            button_idx += button_position
            # railgate status - Check if NVML is being used
            if gpu_data.get('power_control') == 'nvml':
                # NVML mode - show as unavailable
                plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "Railgate", "N/A (NVML)")
            else:
                # Traditional mode - show status
                railgate_string = "Active" if gpu_status['railgate'] else "Disable"
                railgate_status = NColors.green() if gpu_status['railgate'] else curses.A_NORMAL
                plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "Railgate", railgate_string, color=railgate_status)
            # self.stdscr.addstr(first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "Railgate:", curses.A_BOLD)
            # self.draw_gpus[gpu_name]['railgate'].update(first + 1 + (idx + 1) * gpu_height - 1, 10 + button_idx, railgate_string,
            #                                             key=key, mouse=mouse, color=railgate_status)
            button_idx += button_position
            # Power control
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "Power ctrl", gpu_data['power_control'])
            button_idx += button_position
            # TPC PG Mask
            if 'tpc_pg_mask' in gpu_status:
                tpc_pg_mask_string = "ON" if gpu_status['tpc_pg_mask'] else "OFF"
                # tpc_pg_mask_status = NColors.green() if gpu_status['tpc_pg_mask'] else NColors.red()
                plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "TPC PG", tpc_pg_mask_string)
                button_idx += button_position
            # Check if GPC data is included
            frq_size = width - 3
            if 'GPC' in gpu_freq:
                size_gpc_gauge = (width - 2) // (2 + len(gpu_freq['GPC']))
                for gpc_idx, gpc in enumerate(gpu_freq['GPC']):
                    freq_data = {
                        'name': 'GPC{idx}'.format(idx=gpc_idx),
                        'cur': gpc,
                        'unit': 'k',
                        'online': gpc > 0,
                    }
                    freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height, width // 2 + gpc_idx * (size_gpc_gauge) + 2, size_gpc_gauge - 1, freq_data)
                # Change size frequency GPU
                frq_size = width // 2
            # Print frequency info
            gpu_freq['name'] = "Frq"
            freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height, 1, frq_size, gpu_freq)
        # Draw all Processes
        height_table = height - first + 2 + gpu_height
        self.process_table.draw(first + 2 + gpu_height, 0, width, height_table, key, mouse)
# EOF
