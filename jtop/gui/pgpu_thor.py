# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext>
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
import os
import time

from .jtopgui import Page
from .lib.common import NColors, size_to_string
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

# ---------------------------
# NVML: present in code but DISABLED by default.
# Enable by exporting: JTOP_THOR_ENABLE_NVML=1
# ---------------------------
_ENABLE_NVML = os.environ.get("JTOP_THOR_ENABLE_NVML") == "1"
_HAS_NVML = False
if _ENABLE_NVML:
    try:
        from pynvml import (
            nvmlInit, nvmlShutdown, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex,
            nvmlDeviceGetMemoryInfo, nvmlDeviceGetBAR1MemoryInfo,
            nvmlDeviceGetGraphicsRunningProcesses
        )
        _HAS_NVML = True
    except Exception:
        _HAS_NVML = False

# CUDA for GPU memory on Thor
try:
    from jtop.core.thor_cuda_mem import cuda_gpu_mem_bytes
except Exception:
    cuda_gpu_mem_bytes = None


def _size_human(nbytes: int):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    f = float(nbytes)
    i = 0
    while f >= 1024.0 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    return f, units[i], (1024 ** i)


def _to_gib_series(used_b: int, shared_b: int, total_b: int):
    """Return a Chart series dict always scaled in GiB to avoid iB/B tick spam."""
    G = 1024 ** 3
    return {
        "value": [used_b / G, shared_b / G],
        "max": total_b / G,
        "unit": "",
    }


def _read_podgov_params_gui():
    base = "/sys/class/devfreq/gpu-gpc-0/nvhost_podgov"
    try:
        if not os.path.isdir(base):
            return None

        def rint(name):
            p = os.path.join(base, name)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return int(f.read().strip())
            except Exception:
                return None
        k = rint("k")
        lt = rint("load_target")
        lm = rint("load_margin")
        d = {}
        if k is not None:
            d["k"] = k
        if lt is not None:
            d["load_target"] = lt
        if lm is not None:
            d["load_margin"] = lm
        return d or None
    except Exception:
        return None


def _thor_nvml_mem_summary():
    """
    Returns dict with fb_total, fb_used, bar1_total, bar1_used (bytes),
    or None if NVML not enabled/available.
    """
    if not (_ENABLE_NVML and _HAS_NVML):
        return None
    try:
        nvmlInit()
        try:
            if nvmlDeviceGetCount() < 1:
                return None
            h = nvmlDeviceGetHandleByIndex(0)
            fb = nvmlDeviceGetMemoryInfo(h)
            fb_total, fb_used = int(fb.total), int(fb.used)
            try:
                b = nvmlDeviceGetBAR1MemoryInfo(h)
                bar1_total = int(getattr(b, "bar1Total", 0))
                bar1_used = int(getattr(b, "bar1Used", 0))
            except Exception:
                bar1_total, bar1_used = 0, 0
            return {
                "fb_total": fb_total,
                "fb_used": fb_used,
                "bar1_total": bar1_total,
                "bar1_used": bar1_used,
            }
        finally:
            try:
                nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return None


def _thor_nvml_graphics_process_rows():
    """
    Returns a list of dicts for graphics processes from NVML v3, or [] if unsupported/disabled.
    Each row: {pid, name (maybe None), used_bytes (or None)}
    """
    if not (_ENABLE_NVML and _HAS_NVML):
        return []
    try:
        nvmlInit()
        try:
            if nvmlDeviceGetCount() < 1:
                return []
            h = nvmlDeviceGetHandleByIndex(0)
            procs = nvmlDeviceGetGraphicsRunningProcesses(h)
            rows = []
            for p in procs:
                rows.append({
                    "pid": int(p.pid),
                    "name": getattr(p, "name", None),
                    "used_bytes": None if getattr(p, "usedGpuMemory", None) is None else int(p.usedGpuMemory),
                })
            return rows
        finally:
            try:
                nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return []


def _dbg(msg: str):
    """
    Optional debug logger for GPU memory sampling.
    Logging is DISABLED by default.
    To enable, set:
        export JTOP_THOR_MEM_LOG_PATH=/tmp/jtop_thor_mem.log
    """
    log_path = os.environ.get("JTOP_THOR_MEM_LOG_PATH")
    if not log_path or log_path.upper() == "DISABLED":
        return
    try:
        with open(log_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _fmt_bytes_mib(n):
    return "—" if n is None else f"{n / (1024**2):.1f} MiB"


def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data['status']
    data = {
        'name': 'GPU' if idx == 0 else f'GPU{idx}',
        'color': NColors.green() | curses.A_BOLD,
        'values': [(gpu_status['load'], NColors.igreen())],
    }
    # Disable static Hz text at top (often stale on Thor)
    # if 'freq' in gpu_data:
    #     curr_string = unit_to_string(gpu_data['freq']['cur'], 'k', 'Hz')
    #     stdscr.addstr(pos_y, pos_x + size - 8, curr_string, NColors.italic())
    basic_gauge(stdscr, pos_y, pos_x, size - 10, data, bar=" ")


def compact_gpu(stdscr, pos_y, pos_x, width, jetson, mouse=None):
    """Compact GPU display for summary view."""
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

    # Mouse interaction
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
            type_gpu = "i" if self.jetson.gpu[gpu_name]['type'] == 'integrated' else 'd'
            chart = Chart(jetson, f"{type_gpu}GPU {gpu_name}", self.update_chart,
                          color_text=curses.COLOR_GREEN)
            button_3d_scaling = SmallButton(stdscr, self.action_scaling_3D, info={'name': gpu_name})
            chart_ram = Chart(jetson, "GPU Shared RAM", self.update_chart_ram,
                              type_value=float,
                              color_text=curses.COLOR_GREEN,
                              color_chart=[COLOR_GREY, curses.COLOR_GREEN]) if type_gpu == 'i' else None
            self.draw_gpus[gpu_name] = {'chart': chart, '3d_scaling': button_3d_scaling, 'ram': chart_ram}
        self.process_table = ProcessTable(self.stdscr, self.jetson)
        self._click_regions = {"scaling": [], "railgate": []}

        # CUDA reading cache to avoid flicker when probe momentarily fails
        self._cuda_mem_last = None          # (used_b, total_b)
        self._cuda_mem_last_ts = 0.0        # time.time()

    # ---------- small helpers (class) ----------

    def _get_cuda_mem_cached(self, ttl=3.0, stale_ok=10.0):
        """
        Try CUDA probe. If it succeeds, cache & return.
        If it fails, return cached value if it's not older than `stale_ok`.
        ttl: recency window to avoid spamming the driver every frame.
        """
        now = time.time()
        # reuse fresh cache
        if self._cuda_mem_last and (now - self._cuda_mem_last_ts) < ttl:
            return self._cuda_mem_last

        res = None
        if cuda_gpu_mem_bytes is not None:
            try:
                res = cuda_gpu_mem_bytes(0)  # (used_b, total_b) or None
            except Exception:
                res = None

        if res:
            self._cuda_mem_last = res
            self._cuda_mem_last_ts = now
            return res

        # return stale (recent) value to smooth over brief failures
        if self._cuda_mem_last and (now - self._cuda_mem_last_ts) <= stale_ok:
            return self._cuda_mem_last

        return None

    # ---------- actions ----------

    def action_railgate(self, info, selected):
        toggle_rail()

    def action_scaling_3D(self, info, selected):
        toggle_governor()

    # ---------- charts data providers ----------

    def update_chart(self, jetson, name):
        gpu_name = name.split(" ")[1]
        gpu_status = jetson.gpu[gpu_name]['status']
        return {'value': [gpu_status['load']]}

    def update_chart_ram(self, jetson, name):
        """
        GPU Shared RAM chart values.

        Order of preference:
          1) CUDA driver (thor_cuda_mem): FB total/used, shared=0 (no BAR1 visibility)
          2) NVML (if enabled): prefer BAR1 when available and show FB used as reference
          3) Legacy jetson.memory['RAM'] as last resort
        """
        # --- 1) CUDA driver first (Thor), with caching ---
        res = self._get_cuda_mem_cached(ttl=3.0, stale_ok=10.0)
        if res:
            used_b, total_b = res
            _dbg(f"RAM via CUDA: used={used_b} total={total_b}")
            return _to_gib_series(used_b, 0, total_b)  # shared=0 with CUDA path

        # --- 2) NVML BAR1/FB path (only if enabled) ---
        nv = _thor_nvml_mem_summary()
        if nv:
            fb_total = nv["fb_total"]    # bytes
            fb_used = nv["fb_used"]      # bytes
            bar1_total = nv["bar1_total"]  # bytes
            bar1_used = nv["bar1_used"]    # bytes

            if bar1_total and bar1_total > 0:
                total_bytes = bar1_total
                shared_bytes = bar1_used
                ref_bytes = fb_used
            else:
                total_bytes = fb_total
                shared_bytes = 0
                ref_bytes = fb_used

            _dbg(f"RAM via NVML: fb_used={fb_used} fb_total={fb_total} bar1_used={bar1_used} bar1_total={bar1_total}")
            return _to_gib_series(ref_bytes, shared_bytes, total_bytes)

        # --- 3) Legacy absolute fallback (system RAM) ---
        parameter = jetson.memory.get("RAM", {})
        tot_kib = int(parameter.get("tot", 0))
        used_kib = int(parameter.get("used", 0))
        shared_kib = int(parameter.get("shared", 0))

        tot_b = tot_kib * 1024
        used_b = used_kib * 1024
        shared_b = shared_kib * 1024

        _dbg(f"RAM via HOST: used={used_b} total={tot_b}")
        return _to_gib_series(used_b, shared_b, tot_b)

    # ---------- input handling ----------

    def _handle_mouse(self, mouse):
        if not mouse:
            return False
        try:
            mx, my = mouse
            for which, regions in (("scaling", self._click_regions["scaling"]),
                                   ("railgate", self._click_regions["railgate"])):
                for (ry, rx1, rx2) in regions:
                    if my == ry and rx1 <= mx <= rx2:
                        toggle_governor() if which == "scaling" else toggle_rail()
                        return True
        except Exception:
            pass
        return False

    def _handle_hotkeys(self, key):
        if isinstance(key, int):
            if key in (ord('g'), ord('G')):
                toggle_governor()
                return True
            if key in (ord('r'), ord('R')):
                toggle_rail()
                return True
        return False

    # ---------- main draw ----------

    def draw(self, key, mouse):
        if self._handle_mouse(mouse) or self._handle_hotkeys(key):
            pass

        height, width, first = self.size_page()
        gpu_height = (height * 2 // 3 - 3) // max(1, len(self.jetson.gpu))
        self.stdscr.addstr(first + 1, 1, "Temperatures:", curses.A_NORMAL)

        for name in self.jetson.temperature:
            if 'gpu' in name.lower():
                color_temperature(self.stdscr, first + 1, 15, name, self.jetson.temperature[name])

        self._click_regions = {"scaling": [], "railgate": []}

        # Draw per-GPU blocks
        for idx, (gpu_name, gpu_data) in enumerate(self.jetson.gpu.items()):
            chart = self.draw_gpus[gpu_name]['chart']
            chart_ram = self.draw_gpus[gpu_name]['ram']
            gpu_status = gpu_data['status']
            gpu_freq = gpu_data.get('freq', {})

            size_x = [1, width // 2 - 2]
            size_y = [first + 2 + idx * (gpu_height + 1), first + 2 + (idx + 1) * (gpu_height - 3)]

            # --- draw podgov params directly under the gov line ---
            gp = gpu_status.get("gov_params")

            # If core didn't provide it, read directly from sysfs when governor is nvhost_podgov
            if not gp:
                gov_name = gpu_freq.get("governor", "")
                if gov_name == "nvhost_podgov":
                    gp = _read_podgov_params_gui()

            if isinstance(gp, dict) and gp:
                parts = []
                if "k" in gp:
                    parts.append(f"k={gp['k']}")
                if "load_target" in gp:
                    parts.append(f"load_target={gp['load_target']}")
                if "load_margin" in gp:
                    parts.append(f"load_margin={gp['load_margin']}")
                if parts:
                    try:
                        # draw one row below the chart title, indented slightly
                        self.stdscr.addstr(
                            size_y[0] + 1,
                            size_x[0] + 2,
                            "  " + "  ".join(parts),
                            curses.A_DIM,
                        )
                    except curses.error:
                        pass

            # Draw main GPU load chart (title + governor label)
            label_chart_gpu = f"{gpu_status['load']:>3.0f}% - gov: {gpu_freq.get('governor', '')}"
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)

            # GPU Shared RAM chart + label (per GPU)
            if chart_ram:
                label = ""

                # NVML label (only if enabled)
                if _ENABLE_NVML:
                    nv = _thor_nvml_mem_summary()
                    if nv:
                        fb_total = nv["fb_total"]
                        fb_used = nv["fb_used"]
                        bar1_total = nv["bar1_total"]
                        bar1_used = nv["bar1_used"]
                        if bar1_total > 0:
                            used_k = bar1_used // 1024
                            tot_k = bar1_total // 1024
                            label = f"{size_to_string(used_k, 'k')}/{size_to_string(tot_k, 'k')} (BAR1)"
                        else:
                            used_k = fb_used // 1024
                            tot_k = fb_total // 1024
                            label = f"{size_to_string(used_k, 'k')}/{size_to_string(tot_k, 'k')} (FB)"

                # CUDA GPU memory on Thor
                if not label:
                    res = self._get_cuda_mem_cached(ttl=3.0, stale_ok=10.0)
                    if res:
                        used_b, total_b = res
                        used_k = used_b // 1024
                        tot_k = total_b // 1024
                        label = f"{size_to_string(used_k, 'k')}/{size_to_string(tot_k, 'k')}"

                # Last resort: legacy system RAM label (host)
                if not label:
                    try:
                        ram = self.jetson.memory.get('RAM', {})
                        used_k = int(ram.get('used', 0))     # use 'used' not 'shared'
                        tot_k = int(ram.get('tot', 0))
                        label = f"{size_to_string(used_k, 'k')}/{size_to_string(tot_k, 'k')} (host)"
                    except Exception:
                        label = "N/A"

                chart_ram.draw(self.stdscr, [1 + width // 2, width - 2], size_y, label=label)

            # Clickable toggles row (per GPU area)
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
            self._click_regions["scaling"].append((y, x + len(label), x + len(label) + len(field) - 1))

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
            self._click_regions["railgate"].append((y, x + len(label), x + len(label) + len(field) - 1))

            # Frequency meters (live row above the 3D/Railgate line)
            label_y = first + 1 + (idx + 1) * gpu_height - 1
            meter_y = label_y - 1

            frq_size = width - 3
            if 'GPC' in gpu_freq:
                # allocate right half for GPC lane meters
                size_gpc_gauge = (width - 2) // (2 + len(gpu_freq['GPC']))
                for gpc_idx, gpc in enumerate(gpu_freq['GPC']):
                    freq_data = {
                        'name': f'GPC{gpc_idx}',
                        'cur': gpc,
                        'unit': 'k',
                        'online': gpc > 0,
                    }
                    freq_gauge(
                        self.stdscr,
                        meter_y,
                        width // 2 + gpc_idx * size_gpc_gauge + 2,
                        size_gpc_gauge - 1,
                        freq_data,
                    )
                frq_size = width // 2
            # Overall frequency meter on the left — shift right 1 col and shrink 1 to avoid overlaps
            gpu_freq['name'] = "Frq"
            freq_gauge(self.stdscr, meter_y, 2, frq_size - 1, gpu_freq)

        height_table = height - first + 2 + gpu_height
        self.process_table.draw(first + 2 + gpu_height, 0, width, height_table, key, mouse)

# EOF
