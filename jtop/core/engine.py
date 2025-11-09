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

import os
import re
import logging

logger = logging.getLogger(__name__)

# Common helpers (legacy per-engine debugfs layout)


def read_engine(path):
    # Read status online
    engine = {}
    # Check if access to this file
    if os.access(path + "/clk_enable_count", os.R_OK):
        with open(path + "/clk_enable_count", "r") as f:
            engine["online"] = int(f.read()) == 1
    # Check if access to this file
    if os.access(path + "/clk_rate", os.R_OK):
        with open(path + "/clk_rate", "r") as f:
            engine["cur"] = int(f.read()) // 1000  # Hz -> kHz
    # Decode clock rate
    max_value = False
    if os.access(path + "/clk_max_rate", os.R_OK):
        with open(path + "/clk_max_rate", "r") as f:
            value = int(f.read())
            # 18446744073709551615 = FFFF FFFF FFFF FFFF
            if value != 18446744073709551615:
                engine["max"] = value // 1000
                max_value = True
    if os.access(path + "/clk_min_rate", os.R_OK) and max_value:
        with open(path + "/clk_min_rate", "r") as f:
            engine["min"] = int(f.read()) // 1000
    return engine


# Thor (tegra264) helpers: parse BPMP clk_tree

_BPMP_CLK_TREE = "/sys/kernel/debug/bpmp/debug/clk/clk_tree"

_BPMP_TOKEN_MAP = {
    # token -> list of preferred names (first match wins). Fallback: substring search
    "APE": ["ape"],
    "VIC": ["vic", "nafll_vic"],
    "NVENC": ["nvenc", "msenc", "nafll_nvenc", "nafll_msenc"],
    "MSENC": ["msenc", "nvenc", "nafll_msenc", "nafll_nvenc"],
    "NVDEC": ["nvdec", "nafll_nvdec"],
    "NVJPG": ["nvjpg", "nvjpg0", "nafll_nvjpg"],
    "NVJPG1": ["nvjpg1"],
    "PVA": ["pva", "pva0"],
    "PVA0": ["pva0", "pva"],
    "OFA": ["ofa"],
    "SE": ["se", "se0", "se1"],
    "CVNAS": ["cvnas"],
    "DLA": ["dla", "dla0", "dla1"],  # not present on Thor
}

_BPMP_LINE_RX = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s+(\d+)\s+(\d+)\b", re.MULTILINE)
# header: "clock  on  rate  bpmp  mrq  vdd"
# groups:  name, on,  rate


def _bpmp_read_tree_text():
    try:
        with open(_BPMP_CLK_TREE, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.debug(f"BPMP clk_tree read failed: {e}")
        return ""


def _bpmp_index_tree():
    """
    Return dict name -> {'on': int, 'rate': int}
    """
    text = _bpmp_read_tree_text()
    idx = {}
    if not text:
        return idx
    for m in _BPMP_LINE_RX.finditer(text):
        name = m.group(1)
        on = int(m.group(2))
        rate = int(m.group(3))
        # Skip “buffer” like foo.buf, etc.
        if "." in name:
            continue
        idx[name] = {"on": on, "rate": rate}
    return idx


def _bpmp_pick_clock(idx, token):
    """
    Resolve a logical engine token (e.g., 'VIC') to a concrete clock name in the BPMP index.
    Prefer explicit names in _BPMP_TOKEN_MAP; otherwise substring search.
    """
    prefs = _BPMP_TOKEN_MAP.get(token, [])
    # Try preferred names first (case-insensitive)
    for n in prefs:
        for key in idx.keys():
            if n.lower() == key.lower():
                return key
    # Fallback: substring search (stable ordering)
    lowtok = token.lower()
    return next((name for name in idx.keys() if lowtok in name.lower()), None)


def _bpmp_engine_status_for(token, idx):
    """
    Build an engine dict matching read_engine() shape: {'online': bool, 'cur': kHz}
    Online is inferred as rate > 0 (BPMP 'on' may be 0 while rate is valid).
    """
    name = _bpmp_pick_clock(idx, token)
    if not name:
        return None, None  # (name, engine_dict)
    rate = idx[name]["rate"]
    online = rate > 0
    return name.upper(), {"online": online, "cur": rate // 1000}


def _is_thor():
    # Detect tegra264 via DT compatible (works on JP7)
    paths = (
        "/proc/device-tree/compatible",
        "/sys/firmware/devicetree/base/compatible",
    )
    for p in paths:
        try:
            with open(p, "rb") as f:
                data = f.read().lower()
            if b"nvidia,tegra264" in data or b"thor" in data:
                return True
        except Exception:
            pass
    return False


# EngineService (keeps legacy path; adds Thor BPMP mode)


class EngineService(object):
    ENGINES = [
        "ape",
        "dla",
        "pva",
        "vic",
        "nvjpg",
        "nvenc",
        "nvdec",
        "se.",
        "cvnas",
        "msenc",
        "ofa",
        "nvjpg1",
    ]

    def __init__(self):
        EngineService.ENGINES.sort()
        self.engines_path = {}
        self._thor_mode = _is_thor()

        if self._thor_mode:
            logger.info("EngineService: Thor mode (BPMP clk_tree)")
            # Build a snapshot index of BPMP clocks now; names are resolved in get_status()
            self._bpmp_idx = _bpmp_index_tree()
            if not self._bpmp_idx:
                logger.warning(
                    "BPMP clk_tree not readable; mount debugfs?  sudo mount -t debugfs debugfs /sys/kernel/debug"
                )
            # For parity with legacy, create a name table so UI can show available engines
            for token in EngineService.ENGINES:
                key = token.rstrip(".").upper()
                picked = _bpmp_pick_clock(self._bpmp_idx, key)
                if picked:
                    self.engines_path[key] = [picked]  # store clock names
            if self.engines_path:
                logger.info(
                    "Engines (BPMP) found: [" + " ".join(self.engines_path.keys()) + "]"
                )
            else:
                logger.warning("No engines resolved from BPMP clk_tree.")
            return  # Thor path done

        # Legacy layout (/sys/kernel/debug/clk/<engine>[/sub])
        engine_path = "/sys/kernel/debug/clk"
        if os.getenv("JTOP_TESTING", False):
            engine_path = "/fake_sys/kernel/debug/clk"
            logger.warning(
                "Running in JTOP_TESTING folder={root_dir}".format(root_dir=engine_path)
            )
        list_all_engines = [x[0] for x in os.walk(engine_path)]
        for name in EngineService.ENGINES:
            if name.endswith("."):
                name = name[:-1]
                local_path = "{path}/{name}".format(path=engine_path, name=name)
                if os.path.isdir(local_path):
                    self.engines_path[name.upper()] = [local_path]
            else:
                local_path = "{path}/{name}".format(path=engine_path, name=name)
                matching = [
                    s for s in list_all_engines if local_path in s and "." not in s
                ]
                if matching:
                    if os.path.basename(matching[0]).split("_")[0] == "{name}0".format(
                        name=name
                    ):
                        logger.info(
                            "Special Engine group found: [{name}X]".format(name=name)
                        )
                        for num in range(10):
                            name_engine = "{name}{counter}".format(
                                name=name, counter=num
                            )
                            new_match = [
                                match for match in matching if name_engine in match
                            ]
                            if new_match:
                                self.engines_path[name_engine.upper()] = sorted(
                                    new_match
                                )
                            else:
                                break
                    else:
                        self.engines_path[name.upper()] = sorted(matching)
        if self.engines_path:
            engines_string = " ".join(name for name in self.engines_path)
            logger.info("Engines found: [{engines}]".format(engines=engines_string))
        else:
            logger.warning("Not engines found!")

    def get_status(self):
        status = {}

        if self._thor_mode:
            # Re-snapshot clk tree each poll so values are fresh
            self._bpmp_idx = _bpmp_index_tree()
            for token in self.engines_path.keys():
                clk_name, eng = _bpmp_engine_status_for(token, self._bpmp_idx)
                status[token] = {}
                if clk_name and eng:
                    status[token][clk_name] = eng
            return status

        # Legacy
        for engine in self.engines_path:
            status[engine] = {}
            for local_path in self.engines_path[engine]:
                name_engine = os.path.basename(local_path).upper()
                logger.debug(
                    "Status [{engine}] in {path}".format(
                        engine=name_engine, path=local_path
                    )
                )
                status[engine][name_engine] = read_engine(local_path)
        return status


# EOF
