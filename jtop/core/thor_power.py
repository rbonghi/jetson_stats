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
import time

logger = logging.getLogger(__name__)

_DEVFREQ_NODES = ("/sys/class/devfreq/gpu-gpc-0", "/sys/class/devfreq/gpu-nvd-0")

# Cache discovered hwmon paths so we don't rescan every read
_HW_CACHE = {
    "ina3221": None,   # (base_dir, {label -> (inX_input, currX_input)})
    "ina238": None,    # (base_dir, power1_input)
    "ts": 0.0,
}


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


def _scan_ina3221() -> Optional[Tuple[str, Dict[str, Tuple[str, str]]]]:
    """Find an INA3221 and map labels -> (mV_path, mA_path)."""
    for hdir in glob.glob("/sys/class/hwmon/hwmon*"):
        # heuristic: has in1_label and curr1_input
        lbls = glob.glob(os.path.join(hdir, "in*_label"))
        if not lbls:
            continue
        label_map: Dict[str, Tuple[str, str]] = {}
        ok = False
        for lbl in lbls:
            try:
                with open(lbl, "r", encoding="utf-8", errors="ignore") as f:
                    name = f.read().strip()
            except Exception:
                continue
            chan = os.path.basename(lbl)[2:].split("_", 1)[0]  # X in inX_label
            v_path = os.path.join(hdir, f"in{chan}_input")     # mV
            i_path = os.path.join(hdir, f"curr{chan}_input")   # mA
            if os.path.isfile(v_path) and os.path.isfile(i_path):
                label_map[name] = (v_path, i_path)
                ok = True
        if ok:
            return (hdir, label_map)
    return None


def _scan_ina238() -> Optional[Tuple[str, str]]:
    """Find an INA238 and return (base_dir, power1_input_uW)."""
    for hdir in glob.glob("/sys/class/hwmon/hwmon*"):
        p_path = os.path.join(hdir, "power1_input")
        if os.path.isfile(p_path):
            # optional: verify device name looks like ina238
            name_path = os.path.join(hdir, "name")
            try:
                with open(name_path, "r", encoding="utf-8", errors="ignore") as f:
                    nm = f.read().strip().lower()
            except Exception:
                nm = ""
            if "ina238" in nm or nm.startswith("ina2") or not nm:
                return (hdir, p_path)
    return None


def _refresh_hwmon_cache(max_age_s: float = 2.0) -> None:
    now = time.time()
    if now - _HW_CACHE["ts"] < max_age_s:
        return
    _HW_CACHE["ina3221"] = _scan_ina3221()
    _HW_CACHE["ina238"] = _scan_ina238()
    _HW_CACHE["ts"] = now


def _read_number(path: str) -> Optional[float]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except Exception:
        return None


def read_vdd_gpu_mw() -> Optional[float]:
    """
    Return instantaneous GPU rail power in mW.
    Prefers INA3221 VDD_GPU (mV * mA), else None.
    """
    _refresh_hwmon_cache()
    ina = _HW_CACHE["ina3221"]
    if not ina:
        return None
    _, label_map = ina
    # Common label on Thor
    for key in ("VDD_GPU", "vdd_gpu", "GPU", "gpu"):
        if key in label_map:
            v_path, i_path = label_map[key]
            mv = _read_number(v_path)
            ma = _read_number(i_path)
            if mv is not None and ma is not None:
                return (mv * ma) / 1000.0  # mW
    # If label differs, just fall through
    return None


def read_cpu_soc_mss_mw() -> Optional[float]:
    """INA3221 channel often labeled VDD_CPU_SOC_MSS."""
    _refresh_hwmon_cache()
    ina = _HW_CACHE["ina3221"]
    if not ina:
        return None
    _, label_map = ina
    for key in ("VDD_CPU_SOC_MSS", "vdd_cpu_soc_mss"):
        if key in label_map:
            mv = _read_number(label_map[key][0])
            ma = _read_number(label_map[key][1])
            if mv is not None and ma is not None:
                return (mv * ma) / 1000.0
    return None


def read_vin_sys_5v0_mw() -> Optional[float]:
    """INA3221 channel often labeled VIN_SYS_5V0."""
    _refresh_hwmon_cache()
    ina = _HW_CACHE["ina3221"]
    if not ina:
        return None
    _, label_map = ina
    for key in ("VIN_SYS_5V0", "vin_sys_5v0"):
        if key in label_map:
            mv = _read_number(label_map[key][0])
            ma = _read_number(label_map[key][1])
            if mv is not None and ma is not None:
                return (mv * ma) / 1000.0
    return None


def read_system_total_mw() -> Optional[float]:
    """
    INA238: power1_input is total system power in uW (module + carrier).
    """
    _refresh_hwmon_cache()
    ina = _HW_CACHE["ina238"]
    if not ina:
        return None
    _, p_uW = ina
    uw = _read_number(p_uW)
    return uw / 1000.0 if uw is not None else None


def get_power_snapshot() -> Dict[str, Optional[float]]:
    """
    Convenient one-shot read for callers (GUI/service).
    Keys are mW values where available.
    """
    return {
        "gpu_mw": read_vdd_gpu_mw(),
        "cpu_soc_mss_mw": read_cpu_soc_mss_mw(),
        "vin_sys_5v0_mw": read_vin_sys_5v0_mw(),
        "system_total_mw": read_system_total_mw(),
        "ts": time.time(),
    }


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
    ctrl = _pm_control_path()
    if not ctrl:
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
    p = podgov_path(node)
    if not p:
        return False, f"nvhost_podgov not present on {node}"
    return _write(os.path.join(p, name), value)


# EOF
