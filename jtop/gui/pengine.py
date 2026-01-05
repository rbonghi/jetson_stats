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

# Page class definition
from .jtopgui import Page
from .lib.colors import NColors
from .lib.common import unit_to_string, plot_name_info
from .lib.linear_gauge import freq_gauge

try:
    # Canonical Thor detector (sysfs-based)
    from ..core.hw_detect import is_thor as hw_is_thor
except Exception:
    hw_is_thor = None


# Thor-native grouping & rail mapping (JetsonPower naming)
THOR_ENGINE_GROUPS = {
    "MEDIA": {
        "rail": "VDD_GPU",
        "engines": ["NVDEC0", "NVDEC1", "NVENC0", "NVENC1", "NVJPG0", "NVJPG1", "OFA"],
    },
    "VISION / SECURITY": {
        "rail": "VDD_CPU_SOC_MSS",
        "engines": ["PVA", "PVA0_CPU_AXI", "PVA0_VPS", "SE", "VIC"],
    },
    "AUDIO": {
        "rail": "VIN_SYS_5V0",
        "engines": ["APE"],
    },
}


def is_thor(jetson=None) -> bool:
    """
    Prefer sysfs-based Thor detection. Keep `jetson` arg for fallback.
    """
    if hw_is_thor:
        try:
            return bool(hw_is_thor())
        except Exception:
            pass
    # Fallback (string-based)
    try:
        module = jetson.board.get("hardware", {}).get("Module", "").lower()
        if "thor" in module or "tegra264" in module:
            return True
    except Exception:
        pass
    return False


def _get_stats_dict(jetson):
    # Prefer flat stats for Power/Temp keys
    try:
        d = getattr(jetson, "stats", None)
        if isinstance(d, dict):
            return d
    except Exception:
        pass

    # Fall back to other variants
    for attr in ("data", "_stats", "all_stats"):
        try:
            d = getattr(jetson, attr, None)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}


def _overlay_present(jetson, stats: dict) -> bool:
    """Detect whether JetsonPowerProvider overlay/JP engines are present."""
    # Most reliable: service injected JP engine group into structured schema
    try:
        engines = stats.get("engines", {})
        if isinstance(engines, dict) and isinstance(engines.get("JP"), dict):
            return True
    except Exception:
        pass

    # Next: flat marker written by service overlay
    try:
        flat = stats.get("flat", {})
        if isinstance(flat, dict) and int(flat.get("JP_OVERLAY", 0)) == 1:
            return True
    except Exception:
        pass

    # Fallback: some builds may store marker under jc
    try:
        jc = stats.get("jc", {})
        if isinstance(jc, dict) and int(jc.get("JP_OVERLAY", 0)) == 1:
            return True
    except Exception:
        pass

    # Last resort: presence of JetsonPower rails in flat stats
    try:
        flat = _get_flat_stats(stats)
        return any(isinstance(k, str) and k.startswith("Power VDD_") for k in flat.keys())
    except Exception:
        return False


def _get_flat_stats(stats: dict) -> dict:
    """Return namespaced flat stats dict; fall back to stats for older builds."""
    flat = stats.get("flat")
    return flat if isinstance(flat, dict) else stats
def draw_thor_engines_from_stats(stdscr, pos_y, pos_x, width, jetson, stats: dict) -> int:
    """
    Thor Engine Page renderer.

    Layout:
      - Left: semantic engine groups (MEDIA / VISION / AUDIO), engines in a single column
      - Right: RAILS panel (uses horizontal space without consuming vertical space)

    Uses flat overlay stats keys (e.g. NVDEC0/NVENC1/NVJPG0/PVA/SE/APE/VIC) and shows:
      - "Idle" when value is 0/None/non-numeric
      - "<freq>" (e.g. 315MHz) when value is numeric and > 0
    """
    y = pos_y
    x = pos_x
    w = width

    # Title
    try:
        stdscr.addstr(y, x + w // 2 - 10, " [HW engines — Thor] ", curses.A_BOLD)
    except curses.error:
        pass
    y += 2

    flat = _get_flat_stats(stats)

    # Helpers
    def _engine_value_str(key: str) -> str:
        if not isinstance(flat, dict):
            return "IDLE"
        v = flat.get(key)
        try:
            vi = int(v)
        except (TypeError, ValueError):
            return "IDLE"
        return unit_to_string(vi, 'k', 'Hz') if vi > 0 else "IDLE"

    def _print_safe(row_y: int, col_x: int, text: str, attr=0):
        try:
            stdscr.addstr(row_y, col_x, text, attr)
        except curses.error:
            pass

    # Rails (right-side panel)
    rails_w = {}
    if isinstance(flat, dict):
        for k, v in flat.items():
            if not (isinstance(k, str) and k.startswith("Power ")):
                continue
            if k.endswith(" AVG"):
                continue
            name = k[6:]  # strip "Power "
            if not name:
                continue
            if isinstance(v, (int, float)):
                val = float(v)
                # Values are typically mW from service overlay; convert to W.
                if val > 1000.0:
                    val /= 1000.0
                rails_w[name] = val


    preferred = ["VDD_CPU_SOC_MSS", "VDD_GPU", "VIN_SYS_5V0"]
    ordered_names = [r for r in preferred if r in rails_w]
    extras = sorted([r for r in rails_w.keys() if r not in ordered_names and r not in ("TOT", "TOTAL")])
    ordered_names.extend(extras)

    if "TOT" in rails_w:
        ordered_names.append("TOT")
    elif "TOTAL" in rails_w:
        ordered_names.append("TOTAL")

    rails_ordered = [(name, rails_w[name]) for name in ordered_names]

    left_min_w = 24
    rails_panel_w = 22
    gap = 2
    draw_rails = (w >= (left_min_w + gap + rails_panel_w)) and bool(rails_ordered)

    rails_x = x + w - rails_panel_w if draw_rails else None
    if draw_rails:
        _print_safe(y - 1, rails_x, " [RAILS] ", curses.A_BOLD)
        r_y = y
        for name, val in rails_ordered:
            label = f"{name[:12]:<12} {val:>5.1f}W"
            _print_safe(r_y, rails_x, label, NColors.cyan())
            r_y += 1
            if r_y - y >= 12:
                break

    left_w = (rails_x - x - gap) if draw_rails else w
    left_w = max(18, left_w)

    # Engine groups (single column, fixed order)
    def _present_in_order(keys):
        if not isinstance(flat, dict):
            return []
        return [k for k in keys if k in flat]

    def _rail_label_for_group(group_name: str) -> str:
        rail = None
        try:
            rail = THOR_ENGINE_GROUPS.get(group_name, {}).get("rail")
        except Exception:
            rail = None
        if rail and rail in rails_w:
            return f"({rail}) {rails_w[rail]:.1f}W"
        return ""

    def _draw_group(title: str, keys: list, start_y: int) -> int:
        yy = start_y
        suffix = _rail_label_for_group(title)
        header = f"{title} {suffix}".rstrip()

        _print_safe(yy, x, header, NColors.cyan() | curses.A_BOLD)
        yy += 2

        # Single-column list
        for k in keys:
            val = _engine_value_str(k)
            attr = (NColors.green() | curses.A_BOLD) if val != "IDLE" else curses.A_NORMAL

            NAME_COL_WIDTH = 16   # engine name column
            GAP = 4               # space between name and value
            name_field = f"{k:<{NAME_COL_WIDTH}}"
            val_field = val
            text = f"{name_field}{' ' * GAP}{val_field}"

            _print_safe(yy, x, text[:left_w - 1], attr)
            yy += 1

        return yy + 2

    # Draw groups in THOR_ENGINE_GROUPS order when engines are present
    for group_name, spec in THOR_ENGINE_GROUPS.items():
        keys = _present_in_order(spec.get("engines", []))
        if keys:
            y = _draw_group(group_name, keys, y)

    return y - pos_y

# Legacy Mapping & Compact View Functions (Required by pall.py)
def get_value_engine(engine):
    return unit_to_string(engine['cur'], 'k', 'Hz') if engine['online'] else '[OFF]'


def add_engine_in_list(label, engine, group, name):
    return [(label, get_value_engine(engine[group][name]))] if group in engine else []


def pass_thor(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def pass_orin(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_CPU_AXI'),
        add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('NVJPG1', engine, 'NVJPG', 'NVJPG1'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def map_xavier(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE') + add_engine_in_list('CVNAS', engine, 'CVNAS', 'CVNAS'),
        add_engine_in_list('DLA0c', engine, 'DLA0', 'DLA0_CORE') + add_engine_in_list('DLA1c', engine, 'DLA1', 'DLA1_CORE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('PVA0a', engine, 'PVA0', 'PVA0_AXI'),
        add_engine_in_list('SE', engine, 'SE', 'SE') + add_engine_in_list('VIC', engine, 'VIC', 'VIC'),
    ]


def map_jetson_nano(engine):
    return [
        add_engine_in_list('APE', engine, 'APE', 'APE'),
        add_engine_in_list('NVENC', engine, 'NVENC', 'NVENC') + add_engine_in_list('NVDEC', engine, 'NVDEC', 'NVDEC'),
        add_engine_in_list('NVJPG', engine, 'NVJPG', 'NVJPG') + add_engine_in_list('SE', engine, 'SE', 'SE'),
    ]


MAP_JETSON_MODELS = {
    'thor': pass_thor,
    'orin': pass_orin,
    'xavier': map_xavier,
    'jetson nano': map_jetson_nano,
    'nintendo': map_jetson_nano,
    'jetson tx': map_jetson_nano,
}


def engine_model(model):
    for name, func in MAP_JETSON_MODELS.items():
        if name.lower() in model.lower():
            return func
    return None


def map_engines(jetson, engine_data=None):
    # Default to legacy behavior
    if engine_data is None:
        engine_data = jetson.engine

    # Check if there is a map for each engine
    func_list_engines = engine_model(jetson.board['hardware']["Module"])
    try:
        if func_list_engines:
            return func_list_engines(engine_data)
    except KeyError:
        pass

    # Otherwise show all engines
    list_engines = []
    for group in engine_data:
        list_engines += [[(name, get_value_engine(engine)) for name, engine in engine_data[group].items()]]
    return list_engines


def compact_engines(stdscr, pos_y, pos_x, width, height, jetson):
    """Function called by pall.py to draw the engine summary on the Main page."""
    center_x = pos_x + width // 2
    size_table = max(26, width - 2)

    stats = _get_stats_dict(jetson)
    jp_active = isinstance(stats, dict) and _overlay_present(jetson, stats)

    # Thor overlay path: stats is a flat dict with keys like NVDEC0/NVENC1/etc
    # Thor overlay path: prefer the namespaced flat overlay for Thor engine keys
    if is_thor(jetson) and jp_active and isinstance(stats, dict):
        flat = _get_flat_stats(stats)
        if not isinstance(flat, dict):
            flat = {}

        # Keep only real HW engine keys; exclude APE_SOUNDWIRE_* noise
        engine_keys = []
        for k in flat.keys():
            if not isinstance(k, str):
                continue
            if k.startswith("APE_SOUNDWIRE_"):
                continue
            if k in ("APE", "SE", "VIC", "PVA", "OFA"):
                engine_keys.append(k)
                continue
            if k.startswith(("NVDEC", "NVENC", "NVJPG", "DLA", "PVA")):
                # allow NVDEC0/NVDEC1/NVJPG0/etc and PVA0_CPU_AXI/PVA0_VPS
                engine_keys.append(k)

        # Stable, readable ordering
        def _sort_key(name):
            # put APE first, then DLA, NVDEC, NVENC, NVJPG, PVA, SE, VIC
            order = {"APE": 0, "DLA": 1, "NVDEC": 2, "NVENC": 3, "NVJPG": 4, "PVA": 5, "SE": 6, "VIC": 7, "OFA": 8}
            for prefix, rank in order.items():
                if name == prefix or name.startswith(prefix):
                    return (rank, name)
            return (99, name)

        engine_keys = sorted(set(engine_keys), key=_sort_key)

        # Build (name, value) pairs
        pairs = []
        for k in engine_keys:
            v = flat.get(k)
            # Treat missing/0/non-numeric as OFF
            try:
                vi = int(v)
            except (TypeError, ValueError):
                vi = 0

            if vi > 0:
                # Most of these are frequencies -> show Hz string
                val_str = unit_to_string(vi, 'k', 'Hz')
            else:
                val_str = "[OFF]"
            pairs.append((f"{k}:", val_str))

        cols = 2 if width >= 40 else 1
        rows = (len(pairs) + cols - 1) // cols
        map_eng = []
        for r in range(rows):
            row = []
            for c in range(cols):
                i = r + c * rows
                if i < len(pairs):
                    row.append(pairs[i])
            map_eng.append(row)

        size_map = len(map_eng)
        if size_map > 0:
            try:
                stdscr.addstr(pos_y, center_x - 7, " [HW engines] ", curses.A_BOLD)
            except curses.error:
                pass
            size_map += 1

        for gidx, row in enumerate(map_eng):
            if not row:
                continue
            size_eng = size_table // len(row) - 1
            for idx, (name, value) in enumerate(row):
                color = curses.A_NORMAL if '[OFF]' in value else NColors.green() | curses.A_BOLD
                try:
                    plot_name_info(
                        stdscr,
                        pos_y + gidx + 1,
                        center_x - size_table // 2 + (size_eng + 1) * idx + 1,
                        name,
                        value,
                        color=color
                    )
                except curses.error:
                    pass

        return size_map

    # Legacy path (Orin / non-overlay): use existing engine mapping
    map_eng = map_engines(jetson)
    size_map = len(map_eng)
    if size_map > 0:
        stdscr.addstr(pos_y, center_x - 7, " [HW engines] ", curses.A_BOLD)
        size_map += 1
    for gidx, row in enumerate(map_eng):
        if not row:
            continue
        size_eng = size_table // len(row) - 1
        for idx, (name, value) in enumerate(row):
            color = curses.A_NORMAL if '[OFF]' in value else NColors.green() | curses.A_BOLD
            plot_name_info(
                stdscr,
                pos_y + gidx + 1,
                center_x - size_table // 2 + (size_eng + 1) * idx + 1,
                name,
                value,
                color=color
            )
    return size_map


class ENGINE(Page):

    def __init__(self, stdscr, jetson):
        super(ENGINE, self).__init__("ENG", stdscr, jetson)

    def draw(self, key, mouse):
        height, width, first = self.size_page()
        offset_y = first + 1
        offset_x = 1
        size_gauge = width - 2

        stats = _get_stats_dict(self.jetson)
        jp_active = isinstance(stats, dict) and _overlay_present(self.jetson, stats)

        # 1. Thor View
        if is_thor(self.jetson) and jp_active:
            draw_thor_engines_from_stats(
                self.stdscr, offset_y, offset_x, width - 2, self.jetson, stats
            )
            return

        # 2. Standard View (fallback and earlier Jetsons)
        engine_data = stats.get('engines', self.jetson.engine) if isinstance(stats, dict) else self.jetson.engine

        for gidx, group in enumerate(engine_data):
            engines = engine_data[group]
            if not engines:
                continue

            size_eng = size_gauge // len(engines) - 1

            for idx, (name, engine) in enumerate(engines.items()):
                try:
                    if idx == 0:
                        self.stdscr.addstr(
                            offset_y + gidx * 2, offset_x,
                            f"[{group}]",
                            NColors.cyan() | curses.A_BOLD
                        )
                except curses.error:
                    pass

                engine['name'] = name
                try:
                    freq_gauge(
                        self.stdscr,
                        offset_y + gidx * 2 + 1,
                        offset_x + (size_eng + 1) * idx,
                        size_eng,
                        engine
                    )
                except curses.error:
                    pass


# EOF
