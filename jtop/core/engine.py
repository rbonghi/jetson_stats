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
import logging

logger = logging.getLogger(__name__)

# Shared BPMP helpers
try:
    from .bpmp import BpmpSnapshot, pick_clock
except Exception:
    # If bpmp.py is not present (non-Thor or dev tree), we still keep legacy code paths alive.
    BpmpSnapshot = None
    pick_clock = None

# Common helpers (legacy per-engine debugfs layout)
def read_engine(path: str):
    # Read status online
    engine = {}
    ce = f"{path}/clk_enable_count"
    if os.access(ce, os.R_OK):
        with open(ce, "r") as f:
            engine["online"] = int(f.read()) == 1

    cr = f"{path}/clk_rate"
    if os.access(cr, os.R_OK):
        with open(cr, "r") as f:
            engine["cur"] = int(f.read()) // 1000  # Hz -> kHz

    # Decode clock rate
    max_value = False
    cmax = f"{path}/clk_max_rate"
    if os.access(cmax, os.R_OK):
        with open(cmax, "r") as f:
            value = int(f.read())
            # 18446744073709551615 = FFFF FFFF FFFF FFFF
            if value != 18446744073709551615:
                engine["max"] = value // 1000
                max_value = True

    cmin = f"{path}/clk_min_rate"
    if os.access(cmin, os.R_OK) and max_value:
        with open(cmin, "r") as f:
            engine["min"] = int(f.read()) // 1000
    return engine


def _is_thor() -> bool:
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

        # Preferred BPMP clock name preferences per logical engine (used by pick_clock)
        self._BPMP_TOKEN_MAP = {
            "APE":   ["ape"],
            "VIC":   ["vic", "nafll_vic"],
            "NVENC": ["nvenc", "msenc", "nafll_nvenc", "nafll_msenc"],
            "MSENC": ["msenc", "nvenc", "nafll_msenc", "nafll_nvenc"],
            "NVDEC": ["nvdec", "nafll_nvdec"],
            "NVJPG": ["nvjpg", "nvjpg0", "nafll_nvjpg"],
            "NVJPG1": ["nvjpg1"],
            "PVA":   ["pva", "pva0"],
            "PVA0":  ["pva0", "pva"],
            "OFA":   ["ofa"],
            "SE":    ["se", "se0", "se1"],
            "CVNAS": ["cvnas"],
            "DLA":   ["dla", "dla0", "dla1"],  # not present on Thor, but harmless
        }

        # Thor path: use BPMP snapshot index for discovery
        if self._thor_mode and BpmpSnapshot and pick_clock:
            logger.info("EngineService: Thor mode (BPMP clk_tree)")
            snap = BpmpSnapshot()
            if not snap.index:
                logger.warning(
                    "BPMP clk_tree not readable; mount debugfs?  sudo mount -t debugfs debugfs /sys/kernel/debug"
                )
            else:
                for token in EngineService.ENGINES:
                    key = token.rstrip(".").upper()
                    prefs = self._BPMP_TOKEN_MAP.get(key, [])
                    picked = pick_clock(snap.index, key, prefs)
                    if picked:
                        self.engines_path[key] = [picked]  # store exact clock name
                if self.engines_path:
                    logger.info("Engines (BPMP) found: [" + " ".join(self.engines_path.keys()) + "]")
                    return
                logger.warning("No engines resolved from BPMP clk_tree.")

        # Legacy layout (/sys/kernel/debug/clk/<engine>[/sub])
        engine_path = "/sys/kernel/debug/clk"
        if os.getenv("JTOP_TESTING", False):
            engine_path = "/fake_sys/kernel/debug/clk"
            logger.warning(f"Running in JTOP_TESTING folder={engine_path}")
        list_all_engines = [x[0] for x in os.walk(engine_path)]
        for name in EngineService.ENGINES:
            if name.endswith("."):
                name = name[:-1]
                local_path = f"{engine_path}/{name}"
                if os.path.isdir(local_path):
                    self.engines_path[name.upper()] = [local_path]
            else:
                local_path = f"{engine_path}/{name}"
                matching = [s for s in list_all_engines if local_path in s and "." not in s]
                if matching:
                    if os.path.basename(matching[0]).split("_")[0] == f"{name}0":
                        logger.info(f"Special Engine group found: [{name}X]")
                        for num in range(10):
                            name_engine = f"{name}{num}"
                            new_match = [match for match in matching if name_engine in match]
                            if new_match:
                                self.engines_path[name_engine.upper()] = sorted(new_match)
                            else:
                                break
                    else:
                        self.engines_path[name.upper()] = sorted(matching)
        if self.engines_path:
            engines_string = " ".join(self.engines_path)
            logger.info(f"Engines found: [{engines_string}]")
        else:
            logger.warning("Not engines found!")

    def get_status(self):
        status = {}

        # Thor mode: re-snapshot once per refresh and serve all engines from cache
        if self._thor_mode and BpmpSnapshot:
            snap = BpmpSnapshot()
            for token, names in self.engines_path.items():
                status[token] = {}
                if not names:
                    continue
                clk = names[0]  # exact key from pick_clock
                hz = snap.rate_hz(clk) if snap.index else None
                if hz is None:
                    continue
                status[token][clk.upper()] = {"online": hz > 0, "cur": hz // 1000}
            return status

        # Legacy
        for engine in self.engines_path:
            status[engine] = {}
            for local_path in self.engines_path[engine]:
                name_engine = os.path.basename(local_path).upper()
                logger.debug(f"Status [{name_engine}] in {local_path}")
                status[engine][name_engine] = read_engine(local_path)
        return status


# EOF
