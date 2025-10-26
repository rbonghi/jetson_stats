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

# Minimal, dependency-free helpers for rail-gating (runtime PM) and devfreq governors (3D-scaling)
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import glob
import os
import logging
logger = logging.getLogger(__name__)


_DEVFREQ_NODES = ("/sys/class/devfreq/gpu-gpc-0", "/sys/class/devfreq/gpu-nvd-0")


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return None


def _write(path: str, data: str) -> Tuple[bool, Optional[str]]:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return True, None
    except Exception as e:
        return False, str(e)


def _exists(p: str) -> bool:
    return os.path.exists(p)

# Rail-gating (runtime PM)


def _pm_control_path() -> Optional[str]:
    # Prefer BDF derived from /proc (robust on Jetson/Thor)
    for p in glob.glob("/proc/driver/nvidia/gpus/*/power"):
        bdf = os.path.basename(os.path.dirname(p))
        cand = f"/sys/bus/pci/devices/{bdf}/power/control"
        if _exists(cand):
            return cand
    # Fallback
    cand = "/sys/bus/pci/devices/0000:01:00.0/power/control"
    return cand if _exists(cand) else None


def rail_status() -> Dict:
    """Return presence, readable status, and control info."""
    power_files = glob.glob("/proc/driver/nvidia/gpus/*/power")
    present = bool(power_files)
    enabled = None
    if present:
        txt = _read(power_files[0]) or ""
        for line in txt.splitlines():
            if "Rail-Gating" in line:
                enabled = ("Enabled" in line)
                break
    ctrl = _pm_control_path()
    value = _read(ctrl) if ctrl else None  # "on" or "auto"
    return {
        "present": present,
        "enabled": enabled,     # from /proc (read-only text)
        "control_path": ctrl,   # /sys/bus/pci/devices/.../power/control
        "control_value": value,  # "on" (kept on) or "auto" (idle gating allowed)
        "control_writable": _exists(ctrl) and os.access(ctrl, os.W_OK) if ctrl else False,
    }


def set_rail(allow_idle: bool) -> Tuple[bool, Optional[str]]:
    """allow_idle=True -> 'auto'; False -> 'on'."""
    if not (ctrl := _pm_control_path()):
        return False, "GPU runtime PM control node not found"
    return _write(ctrl, "auto" if allow_idle else "on")


def toggle_rail() -> Tuple[bool, Optional[str]]:
    ctrl = _pm_control_path()
    if not ctrl:
        return False, "GPU runtime PM control node not found"
    cur = _read(ctrl)
    nxt = "on" if cur == "auto" else "auto"
    return _write(ctrl, nxt)

# Devfreq (3D-scaling)


def devfreq_nodes() -> List[str]:
    return [p for p in _DEVFREQ_NODES if _exists(p)]


def available_governors() -> List[str]:
    out: List[str] = []
    for n in devfreq_nodes():
        s = _read(os.path.join(n, "available_governors")) or ""
        for g in s.split():
            if g not in out:
                out.append(g)
    return out


def current_governor() -> Optional[str]:
    for n in devfreq_nodes():
        if g := _read(os.path.join(n, "governor")):
            return g
    return None


def set_governor(gov: str) -> Tuple[bool, Optional[str]]:
    ok_all, last_err = True, None
    for n in devfreq_nodes():
        p = os.path.join(n, "governor")
        ok, err = _write(p, gov)
        if not ok:
            ok_all, last_err = False, err
    return ok_all, last_err


def toggle_governor() -> Tuple[bool, Optional[str]]:
    """Prefer explicit flip between performance <-> nvhost_podgov; else cycle whatever exists."""
    cur = current_governor()
    avail = available_governors()
    if "performance" in avail and "nvhost_podgov" in avail:
        target = "performance" if cur != "performance" else "nvhost_podgov"
    else:
        avail = avail or ["performance", "nvhost_podgov"]
        target = avail[(avail.index(cur) + 1) % len(avail)] if cur in avail else avail[0]
    return set_governor(target)

# nvhost_podgov tunables


def podgov_path(node: str) -> Optional[str]:
    p = os.path.join(node, "nvhost_podgov")
    return p if _exists(p) else None


def read_podgov(node: str) -> Dict[str, Optional[str]]:
    p = podgov_path(node)
    params = ["load_max", "load_target", "load_margin", "k", "up_freq_margin", "down_freq_margin"]
    return {k: (_read(os.path.join(p, k)) if p else None) for k in params}


def write_podgov(node: str, name: str, value: str) -> Tuple[bool, Optional[str]]:
    if not (p := podgov_path(node)):
        return False, f"nvhost_podgov not present on {node}"
    return _write(os.path.join(p, name), value)

# EOF
