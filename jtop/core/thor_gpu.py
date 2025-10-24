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
from typing import Any, Dict, Optional

from .common import GenericInterface
from .exceptions import JtopException
from .thor_power import (
    rail_status,
    set_rail,
    toggle_rail,      # not used directly here, but kept for parity/extension
    devfreq_nodes,
    current_governor,
    set_governor,
    toggle_governor,  # not used directly here, but kept for parity/extension
)

logger = logging.getLogger(__name__)

# Thor detection: present if the devfreq GPC domain exists
THOR_GPC = "/sys/class/devfreq/gpu-gpc-0"


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
    (You can extend this with NVML if desired; keeping sysfs-only here.)
    """
    # Some Jetson kernels expose a 'load' in the devfreq device; Thor may not.
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
        ok, err = set_rail(bool(value))
        if not ok:
            raise JtopException(err or "Failed to set rail-gating")

    def get_railgate(self, name: str) -> bool:
        if name not in self._data:
            raise JtopException(f'GPU "{name}" does not exist')
        rs = rail_status()
        return rs.get("control_value") == "auto"

    def _get_first_integrated_gpu(self) -> str:
        for name in self._data:
            if self._data[name]["type"] == "integrated":
                return name
        return ""


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
        ok, err = set_rail(bool(value))
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
            rail_bool = (rs.get("control_value") == "auto")

            # Load (best-effort)
            load = _read_utilization()
            load = float(load) if load is not None else 0.0

            # Assemble structures compatible with the UI
            freq = {
                "governor": gov,
                "cur": _mhz(f["cur"]),
                "max": _mhz(f["max"]),
                "min": _mhz(f["min"]),
            }
            status = {
                "load": load,
                "3d_scaling": (gov != "performance"),
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
