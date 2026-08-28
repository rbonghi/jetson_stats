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

import curses
import logging
import os
import re
from glob import glob

from .jtopgui import Page
from .lib.colors import NColors

logger = logging.getLogger(__name__)

_HWMON = "/sys/class/hwmon"
_DEVFREQ = "/sys/class/devfreq"
_THERMAL = "/sys/devices/virtual/thermal"

_NVPMODEL_CONFS = (
    "/etc/nvpmodel.conf",
)
_RE_PARAM = re.compile(r"<\s*PARAM\s+TYPE=(\w+)\s+NAME=(\w+)\s*>")
_RE_MODE = re.compile(r"<\s*POWER_MODEL\s+ID=(\d+)\s+NAME=(\w+)\s*>")

# Codecs on Thor (tegra264) share this devfreq clock domain
_SHARED_CODEC_DEVFREQ = "gpu-nvd-0"
_SHARED_CODEC_NOTE = "shared: nvdec/nvenc/nvjpg"

# Prettier display names for common nvpmodel PARAM identifiers.
# Unknown params fall through to their raw name from the conf.
_PARAM_DISPLAY = {
    "PVA0_VPS": "PVA VPS",
    "PVA0_AXI": "PVA AXI",
}

# Preferred display order for common domain params; unknowns append alphabetically.
_PARAM_PREFERRED_ORDER = ("GPU", "VIDEO", "EMC", "PVA0_VPS", "PVA0_AXI")


def _read_int(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def _read_str(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _hwmon_by_name(name):
    for h in sorted(glob(os.path.join(_HWMON, "hwmon*"))):
        if _read_str(os.path.join(h, "name")) == name:
            return h
    return None


def _fmt_freq(v):
    """Format a frequency value. Heuristic: devfreq sysfs is in Hz, cpufreq
    (and nvpmodel.conf CPU entries) is in kHz. Any value above 10_000_000 is
    treated as Hz; smaller values are treated as kHz. Works for the full
    Jetson range (CPU 400 MHz..3 GHz, devfreq 100 MHz..5 GHz)."""
    if v is None:
        return "n/a"
    hz = v if v > 10_000_000 else v * 1000
    if hz >= 1_000_000_000:
        return "{:.2f} GHz".format(hz / 1_000_000_000)
    return "{:d} MHz".format(hz // 1_000_000)


def _bar(fraction, width=10):
    """Text bar matching jtop's basic_gauge style: [|||||     ]"""
    if fraction is None:
        return "[" + " " * width + "]"
    f = max(0.0, min(1.0, fraction))
    filled = int(round(f * width))
    return "[" + "|" * filled + " " * (width - filled) + "]"


def _bar_color(fraction):
    """Bar fill color: green<50%, cyan 50-80%, yellow 80-95%, red >95%."""
    if fraction is None:
        return 0
    if fraction > 0.95:
        return NColors.red() | curses.A_BOLD
    if fraction > 0.80:
        return NColors.yellow()
    if fraction > 0.50:
        return NColors.cyan()
    return NColors.green()


def _find_nvpmodel_conf():
    for p in _NVPMODEL_CONFS:
        if os.path.isfile(p):
            return p
    return None


def _parse_nvpmodel_conf(path):
    """Returns (params, modes).
    params = { PARAM_NAME: { ARG_NAME: sysfs_path } }
    modes  = [ { 'id': str, 'name': str, 'settings': [(param, arg, val), ...] } ]
    """
    params = {}
    modes = []
    cur_param = None
    cur_mode = None
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("<"):
                m_param = _RE_PARAM.match(line)
                m_mode = _RE_MODE.match(line)
                if m_param:
                    cur_param = m_param.group(2)
                    params.setdefault(cur_param, {})
                    cur_mode = None
                elif m_mode:
                    cur_mode = {"id": m_mode.group(1), "name": m_mode.group(2), "settings": []}
                    modes.append(cur_mode)
                    cur_param = None
                else:
                    cur_param = None
                    cur_mode = None
                continue
            parts = line.split()
            if cur_param is not None and len(parts) == 2:
                params[cur_param][parts[0]] = parts[1]
            elif cur_mode is not None and len(parts) == 3:
                cur_mode["settings"].append((parts[0], parts[1], parts[2]))
    return params, modes


_UNCAPPED_SENTINEL = 2147483647  # INT_MAX; some nvpmodel.conf variants emit this literally


def _cap_from_mode(mode, param, arg):
    for pname, aname, val in mode["settings"]:
        if pname == param and aname == arg:
            try:
                v = int(val)
            except ValueError:
                return None
            # -1 (documented) and INT_MAX (some variants) both mean uncapped
            return None if v < 0 or v == _UNCAPPED_SENTINEL else v
    return None


class SYSFS(Page):

    def __init__(self, stdscr, jetson):
        super(SYSFS, self).__init__("SYSFS", stdscr, jetson)
        # Panel 1 — soctherm_oc: baseline is captured at jtop start; last is
        # updated each draw so we can tell "fired since jtop start" (history)
        # apart from "fired since last refresh" (live event).
        self._oc_hwmon = _hwmon_by_name("soctherm_oc")
        self._oc_baseline = self._read_oc_counters()
        self._oc_last = dict(self._oc_baseline)
        # Panel 2 — devfreq nodes
        self._devfreq_nodes = sorted(glob(os.path.join(_DEVFREQ, "*")))
        # Panel 3 — INA rails + thermal zones
        self._ina3221 = _hwmon_by_name("ina3221")
        self._ina238 = _hwmon_by_name("ina238")
        self._thermal_zones = sorted(glob(os.path.join(_THERMAL, "thermal_zone*")))
        # Panel 4 — fans: discover PWM controls and tachometers across all hwmons
        self._pwms = []   # list of (hwmon_name, pwm_path, enable_path_or_none)
        self._tachs = []  # list of (hwmon_name, tach_path)
        for h in sorted(glob(os.path.join(_HWMON, "hwmon*"))):
            hname = _read_str(os.path.join(h, "name")) or os.path.basename(h)
            for pwm in sorted(glob(os.path.join(h, "pwm[0-9]"))):
                en = pwm + "_enable"
                self._pwms.append((hname, pwm, en if os.path.exists(en) else None))
            for tach in sorted(glob(os.path.join(h, "fan[0-9]_input"))) + \
                    ([os.path.join(h, "rpm")] if os.path.exists(os.path.join(h, "rpm")) else []):
                self._tachs.append((hname, tach))
        # Panel 5 — nvpmodel conf (one-time parse)
        self._nvp_conf_path = _find_nvpmodel_conf()
        self._nvp_params = {}
        self._nvp_modes = []
        if self._nvp_conf_path:
            try:
                self._nvp_params, self._nvp_modes = _parse_nvpmodel_conf(self._nvp_conf_path)
            except OSError as e:
                logger.debug("nvpmodel conf parse failed: %s", e)

    def _read_oc_counters(self):
        if not self._oc_hwmon:
            return {}
        out = {}
        for p in sorted(glob(os.path.join(self._oc_hwmon, "oc*_event_cnt"))):
            v = _read_int(p)
            if v is not None:
                out[os.path.basename(p)] = v
        return out

    def _safe_addstr(self, y, x, text, attr=0):
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _panel_header(self, y, text):
        self._safe_addstr(y, 1, text, NColors.cyan() | curses.A_BOLD)
        return y + 1

    def _draw_throttle(self, y, _width):
        y = self._panel_header(y, "THROTTLE & OVER-CURRENT")
        if not self._oc_hwmon:
            self._safe_addstr(y, 3, "soctherm_oc hwmon not present", curses.A_DIM)
            return y + 1

        # Header line
        self._safe_addstr(y, 3, "OC counters (total / delta since jtop start):", curses.A_DIM)
        y += 1

        # Per-counter colored parts on one line
        cur = self._read_oc_counters()
        x = 5
        for k in sorted(cur.keys()):
            base = self._oc_baseline.get(k, 0)
            last = self._oc_last.get(k, base)
            since_start = cur[k] - base
            since_last = cur[k] - last
            label = k.replace("_event_cnt", "")
            text = "{}={} (+{})".format(label, cur[k], since_start)
            if since_last > 0:
                attr = NColors.red() | curses.A_BOLD  # actually firing right now
            elif since_start > 0:
                attr = NColors.yellow()               # fired since jtop start
            elif cur[k] > 0:
                attr = NColors.cyan()                 # fired earlier (before jtop)
            else:
                attr = NColors.green()                # clean since boot
            self._safe_addstr(y, x, text, attr)
            x += len(text) + 3
        self._oc_last = cur
        y += 1

        # Currently-active throttle indicators (throt_en)
        en_items = []
        for p in sorted(glob(os.path.join(self._oc_hwmon, "oc*_throt_en"))):
            v = _read_int(p)
            if v is None:
                continue
            base = os.path.basename(p).replace("_throt_en", "")
            en_items.append((base, v))
        if en_items:
            self._safe_addstr(y, 3, "OC throttle enable: ", curses.A_DIM)
            x = 3 + len("OC throttle enable: ")
            for base, v in en_items:
                if v:
                    text = "{}=ON".format(base)
                    attr = NColors.red() | curses.A_BOLD
                else:
                    text = "{}=off".format(base)
                    attr = NColors.green()
                self._safe_addstr(y, x, text, attr)
                x += len(text) + 3
            y += 1

        # Thermal trip zones currently above threshold. We report only the
        # instantaneous state — this is not a history counter, so a zone that
        # crossed and then cooled off will not appear here.
        alarm_zones = []
        for tz in self._thermal_zones:
            zname = _read_str(os.path.join(tz, "type")) or "?"
            for a in glob(os.path.join(tz, "trip_point_*_temp")):
                idx = os.path.basename(a).split("_")[2]
                cur_t = _read_int(os.path.join(tz, "temp"))
                trip_t = _read_int(a)
                trip_type = _read_str(os.path.join(tz, "trip_point_{}_type".format(idx))) or "?"
                if cur_t is not None and trip_t is not None and cur_t >= trip_t and trip_type in ("critical", "hot"):
                    alarm_zones.append("{}({}:{}m°C)".format(zname, trip_type, cur_t))
                    break
        if alarm_zones:
            self._safe_addstr(y, 3, "Zones currently above trip point: " + ", ".join(alarm_zones),
                              NColors.red() | curses.A_BOLD)
        else:
            self._safe_addstr(y, 3, "No zones above trip point right now", curses.A_DIM)
        y += 1
        return y + 1

    def _draw_devfreq(self, y, _width):
        y = self._panel_header(y, "DEVFREQ LOAD & CAPS")
        if not self._devfreq_nodes:
            self._safe_addstr(y, 3, "no /sys/class/devfreq entries", curses.A_DIM)
            return y + 1

        self._safe_addstr(y, 3, "{:<22} {:>10} {:>10} {:>10}   note".format(
            "NODE", "cur", "min", "max"), curses.A_DIM)
        y += 1
        for node in self._devfreq_nodes:
            name = os.path.basename(node)
            cur = _read_int(os.path.join(node, "cur_freq"))
            mn = _read_int(os.path.join(node, "min_freq"))
            mx = _read_int(os.path.join(node, "max_freq"))

            # Color cur based on where it sits between min and max
            cur_attr = 0
            if cur is not None and mx is not None and cur >= mx:
                cur_attr = NColors.green() | curses.A_BOLD          # running full
            elif cur is not None and mn is not None and cur <= mn:
                cur_attr = NColors.cyan()                            # idle/floor

            # Emit prefix, then cur with color, then rest
            prefix = "{:<22} ".format(name[:22])
            cur_str = "{:>10}".format(_fmt_freq(cur))
            rest = " {:>10} {:>10}   ".format(_fmt_freq(mn), _fmt_freq(mx))
            note = _SHARED_CODEC_NOTE if name == _SHARED_CODEC_DEVFREQ else ""
            self._safe_addstr(y, 3, prefix)
            self._safe_addstr(y, 3 + len(prefix), cur_str, cur_attr)
            self._safe_addstr(y, 3 + len(prefix) + len(cur_str), rest)
            if note:
                self._safe_addstr(y, 3 + len(prefix) + len(cur_str) + len(rest), note, NColors.cyan())
            y += 1
        return y + 1

    def _draw_rail_ma(self, y, label, curr_ma, max_ma):
        if curr_ma is None:
            self._safe_addstr(y, 3, "{:<18} n/a".format(label))
            return y + 1
        if max_ma and max_ma > 0:
            frac = curr_ma / float(max_ma)
            self._safe_addstr(y, 3, "{:<18} ".format(label[:18]))
            self._safe_addstr(y, 3 + 19, _bar(frac, 12), _bar_color(frac))
            self._safe_addstr(y, 3 + 19 + 14, " {:>6d}/{:<6d} mA".format(curr_ma, max_ma))
        else:
            self._safe_addstr(y, 3, "{:<18} {:>6d} mA (no max)".format(label[:18], curr_ma))
        return y + 1

    def _draw_rails(self, y, _width):
        y = self._panel_header(y, "POWER RAILS")

        if self._ina3221:
            for ch in (1, 2, 3):
                label = _read_str(os.path.join(self._ina3221, "in{}_label".format(ch)))
                if not label:
                    continue
                cur = _read_int(os.path.join(self._ina3221, "curr{}_input".format(ch)))
                mx = _read_int(os.path.join(self._ina3221, "curr{}_max".format(ch)))
                y = self._draw_rail_ma(y, label, cur, mx)
        else:
            self._safe_addstr(y, 3, "ina3221 not present", curses.A_DIM)
            y += 1

        if self._ina238:
            p_uw = _read_int(os.path.join(self._ina238, "power1_input"))
            p_max_uw = _read_int(os.path.join(self._ina238, "power1_max"))
            v_mv = _read_int(os.path.join(self._ina238, "in1_input"))
            t_mc = _read_int(os.path.join(self._ina238, "temp1_input"))
            extra = ""
            if v_mv is not None:
                extra = "bus {:.1f} V".format(v_mv / 1000.0)
            if t_mc is not None:
                extra += "  chip {:.1f}°C".format(t_mc / 1000.0)
            if p_uw is not None and p_max_uw and p_max_uw > 0:
                frac = p_uw / float(p_max_uw)
                self._safe_addstr(y, 3, "{:<18} ".format("VIN (ina238)"))
                self._safe_addstr(y, 3 + 19, _bar(frac, 12), _bar_color(frac))
                self._safe_addstr(y, 3 + 19 + 14, " {:>5.1f}/{:<5.1f} W   {}".format(
                    p_uw / 1_000_000.0, p_max_uw / 1_000_000.0, extra))
                y += 1
            elif p_uw is not None:
                self._safe_addstr(y, 3, "{:<18} {:>5.1f} W   {}".format(
                    "VIN (ina238)", p_uw / 1_000_000.0, extra))
                y += 1
        return y + 1

    def _draw_fans(self, y, _width):
        y = self._panel_header(y, "FANS")
        if not self._pwms and not self._tachs:
            self._safe_addstr(y, 3, "no PWM controllers or tachometers found", curses.A_DIM)
            return y + 1

        # PWMs
        for hname, pwm_path, en_path in self._pwms:
            raw = _read_int(pwm_path)
            en = _read_int(en_path) if en_path else None
            en_map = {0: "disabled", 1: "userspace", 2: "kernel-auto"}
            en_txt = en_map.get(en, "en={}".format(en)) if en is not None else "n/a"
            pct = (raw / 255.0 * 100.0) if raw is not None else None
            label = "PWM {} ({})".format(os.path.basename(pwm_path), hname)
            if raw is None:
                self._safe_addstr(y, 3, "{:<23} n/a".format(label[:23]))
            else:
                stats = " {:>3d}/255  ({:>5.1f}%)  mode: ".format(raw, pct or 0.0)
                self._safe_addstr(y, 3, "{:<23} ".format(label[:23]))
                self._safe_addstr(y, 3 + 24, _bar(pct / 100.0 if pct else 0, 12), _bar_color(pct / 100.0 if pct else 0))
                self._safe_addstr(y, 3 + 24 + 14, stats)
                # 0=disabled (nothing driving fan), 1=userspace (nvfancontrol on Thor), 2=kernel driver
                mode_attr = NColors.red() | curses.A_BOLD if en == 0 else \
                    (NColors.green() if en == 1 else NColors.yellow())
                self._safe_addstr(y, 3 + 24 + 14 + len(stats), en_txt, mode_attr)
            y += 1

        # Tachometers
        for hname, tach_path in self._tachs:
            rpm = _read_int(tach_path)
            fname = os.path.basename(tach_path)
            label = "TACH {} ({})".format(fname, hname)
            if rpm is None:
                self._safe_addstr(y, 3, "{:<23} n/a".format(label[:23]))
            else:
                # Stuck-fan warning: only meaningful when we can unambiguously
                # pair a tach with a PWM. We don't attempt matching by path
                # (on Thor PWM and tach live in different hwmons), so restrict
                # the check to the 1-PWM / 1-tach case common on Jetson devkits.
                warn = (rpm == 0 and len(self._pwms) == 1 and len(self._tachs) == 1 and
                        (_read_int(self._pwms[0][1]) or 0) > 0)
                attr = NColors.red() | curses.A_BOLD if warn else NColors.green()
                suffix = "  (PWM>0 but no rotation)" if warn else ""
                self._safe_addstr(y, 3, "{:<23} {:>6d} RPM{}".format(label[:23], rpm, suffix), attr)
            y += 1
        return y + 1

    def _draw_nvpmodel(self, y, _width):
        y = self._panel_header(y, "NVPMODEL ACTIVE CAPS")

        nvp = getattr(self.jetson, "nvpmodel", None)
        if nvp is None:
            self._safe_addstr(y, 3, "nvpmodel is not available on this system", curses.A_DIM)
            return y + 1

        # Mode header
        conf_path = self._nvp_conf_path or "(not found)"
        self._safe_addstr(y, 3, "Active: ", curses.A_DIM)
        active_txt = "[{}] {}".format(nvp.id, nvp.name)
        self._safe_addstr(y, 3 + 8, active_txt, NColors.green() | curses.A_BOLD)
        self._safe_addstr(y, 3 + 8 + len(active_txt), "    configuration: {}".format(conf_path), curses.A_DIM)
        y += 1

        # Locate active mode in parsed conf
        active = None
        mid = str(nvp.id)
        for m in self._nvp_modes:
            if m["id"] == mid:
                active = m
                break
        if active is None:
            self._safe_addstr(y, 3, "No cap data for current mode in conf", curses.A_DIM)
            return y + 1

        # CPU summary — find first CPU_* clock param that carries a value in this mode
        cpu_online = sum(1 for p, _, v in active["settings"] if p == "CPU_ONLINE" and v == "1")
        cpu_total = sum(1 for p, _, _ in active["settings"] if p == "CPU_ONLINE")
        cpu_min = None
        cpu_max = None
        for pname in sorted(n for n in self._nvp_params if n.startswith("CPU_") and "MAX_FREQ" in self._nvp_params[n]):
            if cpu_min is None:
                cpu_min = _cap_from_mode(active, pname, "MIN_FREQ")
            if cpu_max is None:
                cpu_max = _cap_from_mode(active, pname, "MAX_FREQ")
            if cpu_min is not None and cpu_max is not None:
                break
        self._safe_addstr(y, 3, "CPU     {}/{} online   min {}   max {}".format(
            cpu_online, cpu_total, _fmt_freq(cpu_min), _fmt_freq(cpu_max)))
        y += 2  # blank row before DOMAIN header

        # Auto-discover domain clock params: any non-CPU param with MAX_FREQ declared
        domain_params = [n for n, args in self._nvp_params.items()
                         if not n.startswith("CPU_") and "MAX_FREQ" in args]
        # Order: preferred names first, then alphabetical for the rest
        preferred = [n for n in _PARAM_PREFERRED_ORDER if n in domain_params]
        rest = sorted(n for n in domain_params if n not in _PARAM_PREFERRED_ORDER)
        ordered = preferred + rest

        # Cap table (widened DOMAIN col to fit DLA*_FALCON etc. seen on Orin)
        self._safe_addstr(y, 3, "{:<12} {:>12}   {:>12}".format(
            "DOMAIN", "configured", "live"), curses.A_DIM)
        y += 1
        for pname in ordered:
            conf_v = _cap_from_mode(active, pname, "MAX_FREQ")
            live_path = self._nvp_params[pname].get("MAX_FREQ")
            live_v = _read_int(live_path) if live_path else None
            if conf_v is None and live_v is None:
                continue  # nothing to say about this domain in this mode
            mark = ""
            attr = 0
            if conf_v is not None and live_v is not None:
                if conf_v == live_v:
                    mark = "  ok"
                    attr = NColors.green()
                else:
                    mark = "  drift"
                    attr = NColors.yellow() | curses.A_BOLD
            label = _PARAM_DISPLAY.get(pname, pname)
            self._safe_addstr(y, 3, "{:<12} {:>12}   {:>12}{}".format(
                label[:12], _fmt_freq(conf_v), _fmt_freq(live_v), mark), attr)
            y += 1
        return y + 1

    def draw(self, key, mouse):
        _, width, first = self.size_page()
        y = first + 2  # blank line under Model header
        y = self._draw_throttle(y, width)
        y = self._draw_devfreq(y, width)
        y = self._draw_rails(y, width)
        y = self._draw_fans(y, width)
        y = self._draw_nvpmodel(y, width)
# EOF
