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

# Thor GPU backend for jtop — uses sysfs + thor_power helpers

from .process_types import PROCESS_TYPE_COMPUTE, PROCESS_TYPE_GRAPHIC
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

# pynvml (nvidia-ml-py) is a declared jetson-stats dependency.
# NVML is a *management* interface — it reads driver state without creating a
# CUDA context, so it is safe to call from the jtop service (no host1x/DRM
# side-effects).
# NOTE: nvmlInit() is NOT called here at import time.  The jtop service forks
# a subprocess for monitoring; NVML state does not survive fork, so nvmlInit()
# must be called lazily inside nvml_process_table() (i.e. in the child process).
try:
    import pynvml as _pynvml
    _NVML = True
except ImportError:
    _pynvml = None  # type: ignore
    _NVML = False

from .common import GenericInterface
from .exceptions import JtopException
from .hw_detect import devfreq_nodes
from .thor_power import (
    rail_status,
    set_rail,
    current_governor,
    set_governor,
)

logger = logging.getLogger(__name__)


# Thor detection: present if the devfreq GPC domain exists
THOR_GPC = "/sys/class/devfreq/gpu-gpc-0"

# 1-second TTL cache for the NVML process-sum so read_gpu_mem_rows_for_gui()
# and the memory service don't both call nvml_process_table() on the same tick.
_GPU_USED_CACHE: Dict[str, Any] = {"ts": 0.0, "kb": None}


def _read_memtotal_bytes() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024  # kB -> B
    except Exception:
        pass
    return 0


def _read_memavailable_bytes() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024  # kB -> B
    except Exception:
        pass
    return 0


def nvml_process_table() -> Tuple[int, List]:
    """
    Return (total_kb, rows) for GPU processes on the nvidia.ko stack (Thor).

    Queries both compute and graphics process lists via pynvml, deduplicating
    by PID with max() so a process that appears in both lists (common on Thor)
    is counted once at its peak allocation.

    Row format: [pid_str, 'user', process_name, gpu_mem_kb, type_str]
    type_str is "Compute" or "Graphic"; a PID in both lists is classified
    as "Compute" (compute getter is queried first).

    pynvml is a declared jetson-stats dependency and is available in the jtop
    venv.  NVML does not create a CUDA context — no host1x/DRM side-effects.
    """
    if not _NVML:
        return 0, []
    try:
        _pynvml.nvmlInit()  # idempotent; required after fork
        count = _pynvml.nvmlDeviceGetCount()
    except _pynvml.NVMLError as e:
        logger.debug("NVML init/count failed: %s", e)
        return 0, []
    pid_mem: Dict[int, int] = {}
    pid_name: Dict[int, str] = {}
    pid_type: Dict[int, str] = {}
    for idx in range(count):
        try:
            h = _pynvml.nvmlDeviceGetHandleByIndex(idx)
        except _pynvml.NVMLError as e:
            logger.debug("nvmlDeviceGetHandleByIndex(%d) failed: %s", idx, e)
            continue
        for getter, type_str in (
            (_pynvml.nvmlDeviceGetComputeRunningProcesses, PROCESS_TYPE_COMPUTE),
            (_pynvml.nvmlDeviceGetGraphicsRunningProcesses, PROCESS_TYPE_GRAPHIC),
        ):
            try:
                procs = getter(h)
            except _pynvml.NVMLError:
                continue
            for p in procs:
                mem_kb = (p.usedGpuMemory or 0) // 1024
                # max() — same PID in both lists means same allocation
                pid_mem[p.pid] = max(pid_mem.get(p.pid, 0), mem_kb)
                # Compute wins: first-seen type is kept (Compute iterated first)
                if p.pid not in pid_type:
                    pid_type[p.pid] = type_str
                if p.pid not in pid_name:
                    try:
                        pid_name[p.pid] = _pynvml.nvmlSystemGetProcessName(p.pid).split('/')[-1]
                    except _pynvml.NVMLError:
                        pid_name[p.pid] = str(p.pid)
    total_kb = sum(pid_mem.values())
    rows = [[str(pid), 'user', pid_name[pid], pid_mem[pid], pid_type[pid]] for pid in pid_mem]
    return total_kb, rows


def nvml_gpu_used_kb() -> Optional[int]:
    """
    Cached (1-second TTL) sum of GPU process memory from NVML (in kB).
    Returns None when NVML is unavailable or all processes report 0.
    """
    global _GPU_USED_CACHE
    now = time.monotonic()
    if now - _GPU_USED_CACHE["ts"] < 1.0:
        return _GPU_USED_CACHE["kb"]
    total_kb, _ = nvml_process_table()
    result = total_kb if total_kb > 0 else None
    _GPU_USED_CACHE = {"ts": now, "kb": result}
    return result


def read_gpu_mem_rows_for_gui(device_index: int = 0):
    """
    Return a GPU memory summary suitable for the Thor GPU page.

    vram_used_b  — sum of GPU process allocations reported by NVML (bytes).
    vram_total_b — total system RAM (unified memory; no separate VRAM pool).
    shared_used_b/shared_total_b — overall system RAM usage (MemAvailable).
    """
    total_b = _read_memtotal_bytes()
    avail_b = _read_memavailable_bytes()

    used_kb = nvml_gpu_used_kb()
    vram_used_b = used_kb * 1024 if used_kb is not None else 0
    vram_total_b = total_b if _NVML else 0

    return {
        "vram_used_b": vram_used_b,
        "vram_total_b": vram_total_b,
        "shared_used_b": max(0, total_b - avail_b),
        "shared_total_b": total_b,
    }


def is_thor() -> bool:
    """Return True if Thor devfreq nodes are present."""
    return os.path.isdir(THOR_GPC)


def _r_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return int((f.read() or "0").strip())
    except Exception:
        return None


def _gpc_freq_block() -> Dict[str, int]:
    """
    Return {cur,min,max} in kHz from the Thor GPC devfreq (converted to MHz in caller).
    Missing entries are returned as 0.
    """
    base = THOR_GPC
    if not os.path.isdir(base):
        return {"cur": 0, "min": 0, "max": 0}
    cur = _r_int(os.path.join(base, "cur_freq")) or 0
    mn = _r_int(os.path.join(base, "min_freq")) or 0
    mx = _r_int(os.path.join(base, "max_freq")) or 0
    return {"cur": cur, "min": mn, "max": mx}


def _mhz(khz: int) -> int:
    return (khz or 0) // 1000


def _read_utilization() -> Optional[float]:
    """
    Try to read a utilization value for Thor. If not available, return None.
    (Sysfs-only, no NVML / CUDA.)
    """
    candidates = [os.path.join(n, "load") for n in devfreq_nodes()]
    for p in candidates:
        if os.path.isfile(p) and os.access(p, os.R_OK):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read().strip()
                # Many Jetson loads are in tenths of percent (e.g., 345 -> 34.5%)
                val = float(txt)
                return val / 10.0 if val > 100.0 else val
            except Exception:
                pass
    return None


class GPU(GenericInterface):
    """
    Thor-only GPU interface compatible with jtop.core.gpu.GPU.
    Exposes:
      - set_scaling_3D(name, bool)  -> maps to governor (True=nvhost_podgov, False=performance)
      - get_scaling_3D(name)        -> True if governor != 'performance'
      - set_railgate(name, bool)    -> runtime PM ('auto' when True, 'on' when False)
      - get_railgate(name)          -> True if control=='auto'
      - scaling_3D property         -> first integrated GPU convenience
    """

    def __init__(self):
        super(GPU, self).__init__()

    # 3D scaling as governor mapping
    def set_scaling_3D(self, name: str, value: bool):
        if name not in self._data:
            raise JtopException(f'GPU "{name}" does not exist')
        target = "nvhost_podgov" if value else "performance"
        ok, err = set_governor(target)
        if not ok:
            raise JtopException(err or f"Failed to set governor: {target}")

    def get_scaling_3D(self, name: str) -> bool:
        if name not in self._data:
            raise JtopException(f'GPU "{name}" does not exist')
        gov = current_governor() or "nvhost_podgov"
        return gov != "performance"

    @property
    def scaling_3D(self) -> bool:
        name = self._get_first_integrated_gpu()
        if not name:
            raise JtopException("no Integrated GPU available")
        return self.get_scaling_3D(name)

    @scaling_3D.setter
    def scaling_3D(self, value: bool):
        name = self._get_first_integrated_gpu()
        if not name:
            raise JtopException("no Integrated GPU available")
        self.set_scaling_3D(name, value)

    # rail-gating via runtime PM control
    def set_railgate(self, name: str, value: bool):
        if name not in self._data:
            raise JtopException(f'GPU "{name}" does not exist')
        ok, err = set_rail(value)
        if not ok:
            raise JtopException(err or "Failed to set rail-gating")

    def get_railgate(self, name: str) -> bool:
        if name not in self._data:
            raise JtopException(f'GPU "{name}" does not exist')
        rs = rail_status()
        return rs.get("control_value") == "auto"

    def _get_first_integrated_gpu(self) -> str:
        return next(
            (
                name
                for name in self._data
                if self._data[name].get("type") == "integrated"
            ),
            "",
        )


class GPUService(object):
    """
    Thor-only GPU service. Builds a single integrated GPU entry and
    returns status using thor_power + devfreq.
    """

    def __init__(self):
        if not is_thor():
            # Intentionally strict: this module should only be imported/used on Thor.
            raise JtopException("thor_gpu.GPUService used on non-Thor system")
        self._gpu_list: Dict[str, Dict[str, Any]] = self._initialize_thor()

    def _initialize_thor(self) -> Dict[str, Dict[str, Any]]:
        # Give the device a stable friendly name; UI will display the key
        name = "thor"
        return {name: {"type": "integrated", "path": THOR_GPC, "frq_path": THOR_GPC}}

    # API parity with legacy service:
    def set_scaling_3D(self, name: str, value: bool):
        if name not in self._gpu_list:
            logger.error(f'GPU "{name}" does not exist')
            return False
        target = "nvhost_podgov" if value else "performance"
        ok, err = set_governor(target)
        if not ok:
            logger.error(err or f"Failed to set governor: {target}")
            return False
        return True

    def set_railgate(self, name: str, value: bool):
        if name not in self._gpu_list:
            logger.error(f'GPU "{name}" does not exist')
            return False
        ok, err = set_rail(value)
        if not ok:
            logger.error(err or "Failed to set rail-gating")
            return False
        return True

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        gpu_list: Dict[str, Dict[str, Any]] = {}
        for name, data in self._gpu_list.items():
            # Frequency & governor
            f = _gpc_freq_block()
            gov = current_governor() or "nvhost_podgov"

            # Rail-gating (runtime PM)
            rs = rail_status()
            rail_bool = rs.get("control_value") == "auto"

            # Load (best-effort)
            load = _read_utilization()
            load = float(load) if load is not None else 0.0

            # Assemble structures compatible with the UI
            freq = {
                "governor": gov,
                "cur": _mhz(f["cur"]),
                "max": _mhz(f["max"]),
                "min": _mhz(f["min"]),
                "GPC": [_mhz(f["cur"])],
            }
            status = {
                "load": load,
                "3d_scaling": gov != "performance",
                "railgate": rail_bool,
                "tpc_pg_mask": None,
            }

            gpu_list[name] = {
                "type": data["type"],
                "status": status,
                "freq": freq,
                # Reflect the control source; helpful for the “Power ctrl” UI line
                "power_control": "runtime_pm",
            }
        return gpu_list


# EOF
