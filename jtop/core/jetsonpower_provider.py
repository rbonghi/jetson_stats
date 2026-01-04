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
#
# SPDX-License-Identifier: GPL-3.0-or-later
# Optional integration with NVIDIA pylibjetsonpower (libjetsonpower).
# pylibjetsonpower is proprietary and is NOT distributed with jetson-stats/jtop.
# Users must obtain/install it separately under NVIDIA’s applicable license/EULA.

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RailSample:
    name: str
    mv: Optional[int] = None          # millivolt
    ma: Optional[int] = None          # milliamp
    mw: Optional[int] = None          # milliwatt
    mw_avg: Optional[int] = None      # milliwatt (avg)
    warn_ma: Optional[int] = None
    warn_mw: Optional[int] = None
    crit_ma: Optional[int] = None


class JetsonPowerProvider:
    """
    Thin wrapper around NVIDIA's pylibjetsonpower.

    Typical usage (service-side):
        p = JetsonPowerProvider()
        if p.available():
            stats['power']   = p.read_power()
            stats['thermal'] = p.read_thermal()
            stats['engines'] = p.read_engines()
            stats['fan']     = p.read_fans()
            stats['cpu']     = p.read_cpu()
            stats['gpu']     = p.read_igpu()
            stats['emc']     = p.read_emc()
            stats['memory']  = p.read_memory()
            stats['disk']    = p.read_disk(['/'])   # optional
    """

    def __init__(self, lazy_init: bool = True):
        self._jp = None
        self._ok = False

        # Cached name lists
        self._rail_names: List[str] = []
        self._thermal_names: List[str] = []
        self._engine_names: List[str] = []
        self._fan_names: List[str] = []

        # Simple throttling to avoid hammering C API
        self._last_refresh = 0.0
        self._min_refresh_s = 0.25

        if not lazy_init:
            self._ensure_loaded()

    # Lifecycle / detection

    def _ensure_loaded(self) -> bool:
        if self._ok:
            return True

        try:
            import pylibjetsonpower as jp  # type: ignore
        except ModuleNotFoundError as e:
            self._jp = None
            self._ok = False
            logger.debug("JetsonPowerProvider: pylibjetsonpower not installed (%s)", e)
            return False
        except ImportError as e:
            self._jp = None
            self._ok = False
            logger.debug("JetsonPowerProvider: pylibjetsonpower import error (%s)", e)
            return False
        except Exception as e:
            # Present but failing (ABI mismatch, missing lib, etc.)
            self._jp = None
            self._ok = False
            logger.warning("JetsonPowerProvider: pylibjetsonpower present but failed to load (%s)", e)
            return False

        self._jp = jp
        self._ok = True
        try:
            self._prime_caches()
        except Exception as e:
            # Don’t brick everything if cache priming fails; just degrade.
            logger.debug("JetsonPowerProvider: cache prime failed (%s)", e)
        logger.info("JetsonPowerProvider: pylibjetsonpower loaded OK")
        return True


    def available(self) -> bool:
        return self._ensure_loaded()

    def close(self) -> None:
        if self._jp is not None:
            try:
                self._jp.release_libjetsonpower()
            except Exception:
                pass
        self._jp = None
        self._ok = False

    # Name caches
    def _prime_caches(self) -> None:
        if not self._jp:
            return

        # rails
        try:
            self._rail_names = list(self._jp.rail_get_names() or [])
        except Exception:
            self._rail_names = []

        # thermals
        try:
            self._thermal_names = list(self._jp.thermal_get_sensor_names() or [])
        except Exception:
            self._thermal_names = []

        # engines
        try:
            self._engine_names = list(self._jp.engine_get_names() or [])
        except Exception:
            self._engine_names = []

        # fans
        try:
            self._fan_names = list(self._jp.fan_get_names() or [])
        except Exception:
            self._fan_names = []

    @property
    def platform_name(self) -> Optional[str]:
        if not self.available():
            return None
        try:
            return self._jp.platform_get_name()
        except Exception:
            return None

    @property
    def nvpmodel_mode(self) -> Optional[str]:
        if not self.available():
            return None
        try:
            return self._jp.nvpmodel_get_power_mode()
        except Exception:
            return None

    @property
    def rail_names(self) -> List[str]:
        if not self.available():
            return []
        if not self._rail_names:
            self._prime_caches()
        return self._rail_names

    @property
    def thermal_names(self) -> List[str]:
        if not self.available():
            return []
        if not self._thermal_names:
            self._prime_caches()
        return self._thermal_names

    @property
    def engine_names(self) -> List[str]:
        if not self.available():
            return []
        if not self._engine_names:
            self._prime_caches()
        return self._engine_names

    @property
    def fan_names(self) -> List[str]:
        if not self.available():
            return []
        if not self._fan_names:
            self._prime_caches()
        return self._fan_names

    # Read helpers
    def _rate_limit(self) -> None:
        now = time.time()
        dt = now - self._last_refresh
        if dt < self._min_refresh_s:
            time.sleep(self._min_refresh_s - dt)
        self._last_refresh = time.time()

    # POWER (rails)
    def read_power(self) -> Dict[str, Any]:
        """
        Returns:
            {
              'platform': str|None,
              'nvpmodel': str|None,
              'rails': {
                 'VDD_GPU': {'mv':..., 'ma':..., 'mw':..., 'mw_avg':..., 'warn_ma':..., 'warn_mw':..., 'crit_ma':...},
                 ...
              }
            }
        """
        if not self.available():
            return {}

        self._rate_limit()
        jp = self._jp

        out: Dict[str, Any] = {
            "platform": self.platform_name,
            "nvpmodel": self.nvpmodel_mode,
            "rails": {},
        }

        for rn in self.rail_names:
            try:
                # These are all ints; negative means error per docstrings.
                mv = jp.rail_get_voltage(rn)
                ma = jp.rail_get_current(rn)
                mw = jp.rail_get_power(rn)
                mw_avg = jp.rail_get_avg_power(rn)
                warn_ma = jp.rail_get_warn_current(rn)
                warn_mw = jp.rail_get_warn_power(rn)
                crit_ma = jp.rail_get_crit_current(rn)

                def ok(v: int) -> Optional[int]:
                    return v if isinstance(v, int) and v >= 0 else None

                out["rails"][rn] = {
                    "mv": ok(mv),
                    "ma": ok(ma),
                    "mw": ok(mw),
                    "mw_avg": ok(mw_avg),
                    "warn_ma": ok(warn_ma),
                    "warn_mw": ok(warn_mw),
                    "crit_ma": ok(crit_ma),
                }
            except Exception as e:
                logger.debug("rail read failed %s: %s", rn, e)

        return out

    def rail_reset_avg(self, rail_name: str) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.rail_reset_avg_power(rail_name)
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def rail_set_warn_current(self, rail_name: str, limit_ma: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.rail_set_warn_current(rail_name, int(limit_ma))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def rail_set_crit_current(self, rail_name: str, limit_ma: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.rail_set_crit_current(rail_name, int(limit_ma))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # THERMAL
    def read_thermal(self) -> Dict[str, Any]:
        """
        Returns:
            {
              'sensors': {
                'gpu-thermal': {'temp_mc': 42000, 'policy': '...', 'throttle_mc':..., 'shutdown_mc':...},
                ...
              }
            }
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        sensors: Dict[str, Any] = {}
        for name in self.thermal_names:
            try:
                t = jp.thermal_get_sensor_temp(name)
                # validate temp.
                valid = (jp.thermal_is_temp_valid(t) == 1) if isinstance(t, int) else False
                sensors[name] = {
                    "temp_mc": t if valid else None,  # milliC
                    "policy": jp.thermal_get_sensor_policy(name),
                    "throttle_mc": jp.thermal_get_sensor_sw_throttling_temp(name),
                    "shutdown_mc": jp.thermal_get_sensor_sw_shutdown_temp(name),
                    "valid": bool(valid),
                }
            except Exception as e:
                logger.debug("thermal read failed %s: %s", name, e)

        return {"sensors": sensors}

    def thermal_set_policy(self, sensor_name: str, policy: str) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.thermal_set_sensor_policy(sensor_name, policy)
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # ENGINES
    def read_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dict shaped similarly to jtop 'engines' leaf nodes:
            {
              'PVA': {'online': True, 'cur': 123000, 'min':..., 'max':...},
              'NVDEC0': {...},
              ...
            }
        Notes:
          - Values are in KHz.
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        out: Dict[str, Dict[str, Any]] = {}
        for en in self.engine_names:
            try:
                online = jp.engine_get_state(en)
                cur = jp.engine_get_cur_freq(en)
                mn = jp.engine_get_min_freq(en)
                mx = jp.engine_get_max_freq(en)

                def ok(v: int) -> Optional[int]:
                    return v if isinstance(v, int) and v >= 0 else None

                out[en.upper()] = {
                    "online": bool(online == 1),
                    "cur": ok(cur),
                    "min": ok(mn),
                    "max": ok(mx),
                }
            except Exception as e:
                logger.debug("engine read failed %s: %s", en, e)

        return out

    # Back-compat helpers (older service.py prototypes)
    # -----------------------------------------------
    def get_engine_names(self) -> List[str]:
        """Compatibility wrapper for earlier integration attempts."""
        return self.engine_names

    def read_engine_status(self, engine_name: str) -> Dict[str, Any]:
        """Return status for a single engine in the same schema as read_engines()."""
        if not self.available():
            return {"online": False, "cur": None, "min": None, "max": None}

        self._rate_limit()
        jp = self._jp
        en = engine_name
        try:
            online = jp.engine_get_state(en)
            cur = jp.engine_get_cur_freq(en)
            mn = jp.engine_get_min_freq(en)
            mx = jp.engine_get_max_freq(en)

            def ok(v: int) -> Optional[int]:
                return v if isinstance(v, int) and v >= 0 else None

            return {
                "online": bool(online == 1),
                "cur": ok(cur),
                "min": ok(mn),
                "max": ok(mx),
            }
        except Exception as e:
            logger.debug("engine read failed %s: %s", en, e)
            return {"online": False, "cur": None, "min": None, "max": None}


    def engine_set_max(self, engine_name: str, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.engine_set_max_freq(engine_name, int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def engine_set_min(self, engine_name: str, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.engine_set_min_freq(engine_name, int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # CPU
    def read_cpu(self) -> Dict[str, Any]:
        """
        Returns:
          {
            'count': N,
            'cores': {
               0: {'online': True, 'cur':..., 'min':..., 'max':..., 'load':...},
               ...
            }
          }
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        try:
            n = int(jp.cpu_get_nums())
        except Exception:
            return {}

        cores: Dict[int, Any] = {}
        for i in range(max(0, n)):
            try:
                st = jp.cpu_get_state(i)  # 0/1
                cur = jp.cpu_get_cur_freq(i)
                mn = jp.cpu_get_min_freq(i)
                mx = jp.cpu_get_max_freq(i)
                load = jp.cpu_get_load(i)

                def ok(v: int) -> Optional[int]:
                    return v if isinstance(v, int) and v >= 0 else None

                cores[i] = {
                    "online": bool(st == 1),
                    "cur": ok(cur),  # kHz
                    "min": ok(mn),
                    "max": ok(mx),
                    "load": ok(load),  # %
                }
            except Exception as e:
                logger.debug("cpu read failed core %d: %s", i, e)

        return {"count": n, "cores": cores}

    def cpu_set_online(self, core: int, online: bool) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.cpu_set_state(int(core), 1 if online else 0)
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def cpu_set_max(self, core: int, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.cpu_set_max_freq(int(core), int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def cpu_set_min(self, core: int, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.cpu_set_min_freq(int(core), int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # iGPU
    def read_igpu(self, core: int = 0) -> Dict[str, Any]:
        """
        Returns:
          {'cur':..., 'min':..., 'max':..., 'load':...}  (all kHz except load)
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        try:
            cur = jp.igpu_get_cur_freq(core)
            mn = jp.igpu_get_min_freq(core)
            mx = jp.igpu_get_max_freq(core)
            load = jp.igpu_get_load(core)

            def ok(v: int) -> Optional[int]:
                return v if isinstance(v, int) and v >= 0 else None

            return {"cur": ok(cur), "min": ok(mn), "max": ok(mx), "load": ok(load)}
        except Exception as e:
            logger.debug("igpu read failed: %s", e)
            return {}

    def igpu_set_max(self, core: int, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.igpu_set_max_freq(int(core), int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def igpu_set_min(self, core: int, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.igpu_set_min_freq(int(core), int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # EMC + Memory
    def read_emc(self) -> Dict[str, Any]:
        """
        Returns:
          {'cur':..., 'min':..., 'max':..., 'load':...} in kHz (load in %)
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        try:
            cur = jp.emc_get_cur_freq()
            mn = jp.emc_get_min_freq()
            mx = jp.emc_get_max_freq()
            load = jp.emc_get_load()

            def ok(v: int) -> Optional[int]:
                return v if isinstance(v, int) and v >= 0 else None

            return {"cur": ok(cur), "min": ok(mn), "max": ok(mx), "load": ok(load)}
        except Exception as e:
            logger.debug("emc read failed: %s", e)
            return {}

    def emc_set_max(self, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.emc_set_max_freq(int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def emc_set_min(self, khz: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.emc_set_min_freq(int(khz))
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def read_memory(self) -> Dict[str, Any]:
        """
        Returns memory figures from libjetsonpower (MB).
        Useful for Thor where 'shared' vs VRAM may matter for UI.

        Returns:
          {
            'mem_mb': {'total':..., 'free':..., 'buffers':..., 'cached':...},
            'swap_mb': {'total':..., 'free':..., 'cached':...},
          }
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        def ok(v: int) -> Optional[int]:
            return v if isinstance(v, int) and v >= 0 else None

        try:
            return {
                "mem_mb": {
                    "total": ok(jp.emc_get_mem_size()),
                    "free": ok(jp.emc_get_free_mem_size()),
                    "buffers": ok(jp.emc_get_buffers_size()),
                    "cached": ok(jp.emc_get_cached_size()),
                },
                "swap_mb": {
                    "total": ok(jp.emc_get_swap_size()),
                    "free": ok(jp.emc_get_free_swap_size()),
                    "cached": ok(jp.emc_get_cached_swap_size()),
                },
            }
        except Exception as e:
            logger.debug("memory read failed: %s", e)
            return {}

    # Fans
    def read_fans(self) -> Dict[str, Any]:
        """
        Returns:
          {
            'fan1': {'pwm': 0..255, 'rpm': int|None, 'profile': str|None, 'governor': str|None, 'control': str|None}
          }

        NOTE: pylibjetsonpower fan_id is 1-based (per its docstring).
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        out: Dict[str, Any] = {}
        for fan_name in self.fan_names:
            try:
                # fan_name typically "fan1" etc; extract index
                idx = int("".join([c for c in fan_name if c.isdigit()]) or "1")
                pwm = jp.fan_get_pwm(idx)
                rpm = jp.fan_get_speed(idx)
                prof = jp.fan_get_profile(idx)
                gov = jp.fan_get_governor(idx)
                ctrl = jp.fan_get_control(idx)

                def ok(v: int) -> Optional[int]:
                    return v if isinstance(v, int) and v >= 0 else None

                out[fan_name] = {
                    "pwm": ok(pwm),
                    "rpm": ok(rpm),
                    "profile": prof,
                    "governor": gov,
                    "control": ctrl,
                }
            except Exception as e:
                logger.debug("fan read failed %s: %s", fan_name, e)
        return out

    def fan_set_pwm(self, fan_id_1based: int, pwm_0_255: int) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            pwm = max(0, min(255, int(pwm_0_255)))
            rc = self._jp.fan_set_pwm(int(fan_id_1based), pwm)
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    def fan_set_tach(self, fan_id_1based: int, enabled: bool) -> Tuple[bool, Optional[str]]:
        if not self.available():
            return False, "pylibjetsonpower unavailable"
        try:
            rc = self._jp.fan_set_tach_enable(int(fan_id_1based), 1 if enabled else 0)
            return (rc == 0), (None if rc == 0 else f"rc={rc}")
        except Exception as e:
            return False, str(e)

    # Disk (optional)
    def read_disk(self, mount_points: List[str]) -> Dict[str, Any]:
        """
        Returns:
          { '/': {'total_mb':..., 'used_mb':...}, ... }
        """
        if not self.available():
            return {}
        self._rate_limit()
        jp = self._jp

        out: Dict[str, Any] = {}
        for mp in mount_points:
            try:
                tot = jp.disk_get_total_size(mp)
                used = jp.disk_get_used_size(mp)
                def ok(v: int) -> Optional[int]:
                    return v if isinstance(v, int) and v >= 0 else None
                out[mp] = {"total_mb": ok(tot), "used_mb": ok(used)}
            except Exception as e:
                logger.debug("disk read failed %s: %s", mp, e)
        return out

# EOF

