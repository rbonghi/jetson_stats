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
import os
import logging
from typing import Any, Dict, Optional, Tuple

from .common import GenericInterface
from .exceptions import JtopException
from .hw_detect import devfreq_nodes, is_thor
from .thor_power import (
    rail_status,
    set_rail,
    read_vdd_gpu_mw,
    current_governor,
    set_governor,
)
from .thor_cuda_mem import cuda_gpu_mem_bytes

logger = logging.getLogger(__name__)

# Thor detection: present if the devfreq GPC domain exists
THOR_GPC = "/sys/class/devfreq/gpu-gpc-0"

# Power→util proxy calibration (use your measured values) ---
_GPU_IDLE_MW = 5525.0    # steady idle VDD_GPU power (≈ 5.525 W)
_GPU_FULL_MW = 22050.0   # typical sustained vLLM plateau (≈ 22.05 W)

# tiny utils

def _r_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return int((f.read() or "0").strip())
    except Exception:
        return None

def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return None

def _mhz(khz: int) -> int:
    return (khz or 0) // 1000

def _parse_percent(txt: str) -> Optional[float]:
    try:
        v = float(txt)
    except Exception:
        return None
    # Jetson kernels sometimes report tenths of a percent (e.g., 345 == 34.5%)
    return v / 10.0 if v > 100.0 else v

# freq / governor

def _gpc_freq_block() -> Dict[str, int]:
    """
    Return {cur,min,max} in kHz from the Thor GPC devfreq (converted to MHz in caller).
    Missing entries are returned as 0.
    """
    base = THOR_GPC
    if not os.path.isdir(base):
        return {"cur": 0, "min": 0, "max": 0}
    cur = _r_int(os.path.join(base, "cur_freq")) or 0
    mn  = _r_int(os.path.join(base, "min_freq")) or 0
    mx  = _r_int(os.path.join(base, "max_freq")) or 0
    return {"cur": cur, "min": mn, "max": mx}

def _read_podgov_params() -> Optional[Dict[str, int]]:
    """Read nvhost_podgov parameters k / load_target / load_margin if present."""
    base = os.path.join(THOR_GPC, "nvhost_podgov")
    if not os.path.isdir(base):
        return None
    def rint(name: str) -> Optional[int]:
        p = os.path.join(base, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return None
    k  = rint("k")
    lt = rint("load_target")
    lm = rint("load_margin")
    if k is None and lt is None and lm is None:
        return None
    out: Dict[str, int] = {}
    if k  is not None:
        out["k"] = k
    if lt is not None:
        out["load_target"] = lt
    if lm is not None:
        out["load_margin"] = lm
    return out

# utilization

def _read_utilization() -> Optional[float]:
    """
    Best-effort GPU utilization (%) from sysfs.
    Order:
      1) devfreq busy_time/total_time
      2) nvhost_podgov/load
      3) legacy devfreq load
    Returns None if not available.
    """
    base = THOR_GPC
    if os.path.isdir(base):
        busy  = _read_file(os.path.join(base, "busy_time"))
        total = _read_file(os.path.join(base, "total_time"))
        if busy is not None and total is not None:
            try:
                b = float(busy)
                t = float(total)
                if t > 0.0:
                    util = 100.0 * b / t
                    return max(0.0, min(100.0, util))
            except Exception:
                pass
        # nvhost_podgov/load (if exported on this kernel)
        podgov_load = _read_file(os.path.join(base, "nvhost_podgov", "load"))
        if podgov_load is not None:
            val = _parse_percent(podgov_load)
            if val is not None:
                return max(0.0, min(100.0, val))

    # Legacy: .../devfreq/*/load
    for node in devfreq_nodes():
        txt = _read_file(os.path.join(node, "load"))
        if not txt:
            continue
        val = _parse_percent(txt)
        if val is not None:
            return max(0.0, min(100.0, val))

    return None

def _util_from_power_fallback() -> Optional[float]:
    """Map VDD_GPU rail power to a rough utilization proxy (0..100%) when no counters exist."""
    p_mw = read_vdd_gpu_mw()
    if p_mw is None:
        return None
    num = max(0.0, p_mw - _GPU_IDLE_MW)
    den = max(1.0, _GPU_FULL_MW - _GPU_IDLE_MW)
    return max(0.0, min(100.0, 100.0 * (num / den)))

# memory

def get_memory_bytes() -> Tuple[int, int]:
    """
    Return (used_bytes, total_bytes) for GPU memory.
    1) Prefer CUDA driver via thor_cuda_mem.
    2) Fallback to (0, 0) to avoid NameError on undefined helpers.
    """
    res = cuda_gpu_mem_bytes(0)
    return res if res is not None else (0, 0)

#  classes 

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
        for name in self._data:
            if self._data[name].get("type") == "integrated":
                return name
        return ""

class GPUService(object):
    """
    Thor-only GPU service. Builds a single integrated GPU entry and
    returns status using thor_power + devfreq.
    """
    def __init__(self):
        if not is_thor():
            raise JtopException("thor_gpu.GPUService used on non-Thor system")
        self._gpu_list: Dict[str, Dict[str, Any]] = self._initialize_thor()

    def _initialize_thor(self) -> Dict[str, Dict[str, Any]]:
        name = "thor"
        return {name: {"type": "integrated", "path": THOR_GPC, "frq_path": THOR_GPC}}

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
        """
        Return a dict of GPU status keyed by GPU name.
        Some fields may be Optional if data could not be read.
        """
        gpu_list: Dict[str, Dict[str, Any]] = {}

        for name, data in self._gpu_list.items():
            # Frequency & governor
            f: Dict[str, int] = _gpc_freq_block()
            gov: Optional[str] = current_governor() or "nvhost_podgov"

            # Governor parameters (only when nvhost_podgov active)
            gov_params: Optional[Dict[str, int]] = _read_podgov_params() if gov == "nvhost_podgov" else None

            # Rail-gating (runtime PM)
            rs: Dict[str, Any] = rail_status()
            rail_bool: bool = (rs.get("control_value") == "auto")

            # Load (best-effort): sysfs first, then power proxy fallback
            load: Optional[float] = _read_utilization()
            if load is None:
                load = _util_from_power_fallback()
            if load is not None:
                load = float(max(0.0, min(100.0, load)))

            # Assemble structures compatible with the UI
            freq: Dict[str, Optional[Any]] = {
                "governor": gov,
                "cur": _mhz(f.get("cur", 0)) if f else None,
                "max": _mhz(f.get("max", 0)) if f else None,
                "min": _mhz(f.get("min", 0)) if f else None,
            }
            status: Dict[str, Optional[Any]] = {
                "load": load,
                "3d_scaling": (gov != "performance") if gov else None,
                "railgate": rail_bool,
                "tpc_pg_mask": None,
                "gov_params": gov_params,  # <-- surfaced for GUI
            }

            gpu_list[name] = {
                "type": data.get("type", "unknown"),
                "status": status,
                "freq": freq,
                "power_control": "runtime_pm",
            }

        return gpu_list

# EOF

