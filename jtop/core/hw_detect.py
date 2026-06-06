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

# jtop/core/hw_detect.py

import os
import platform
import re

THOR_GPC = "/sys/class/devfreq/gpu-gpc-0"

# L4T R38 = JetPack 7.0/7.1, R39 = JetPack 7.2. Everything < R38 is JetPack 6
# or older.  JetPack 7 ships the Thor-class kernel & userspace even on Jetson
# Orin (which keeps the classic nvgpu sysfs interface but loses some legacy
# control nodes such as ``enable_3d_scaling``).
JETPACK7_L4T_MAJOR = 38


def is_thor() -> bool:
    """True only on the real Thor PCIe GPU stack (gpu-gpc-0 devfreq domain)."""
    return os.path.isdir(THOR_GPC)


def is_jetpack7() -> bool:
    """
    True on the JetPack 7.x / L4T R38+ OS — the Thor-class kernel and userspace
    that JetPack 7.2 also ships on Jetson Orin.

    Unlike :func:`is_thor` this is an *OS* check, not a GPU-stack check: a
    JetPack 7.2 Orin reports True here while still exposing the classic nvgpu
    sysfs interface (``/sys/class/devfreq/17000000.gpu``) rather than Thor's
    ``gpu-gpc-0``.

    Detection order:
      1. ``/etc/nv_tegra_release`` -> ``# R39 (release), ...`` (major >= 38)
      2. kernel release fallback   -> ``*-tegra`` with version >= 6.8
    """
    # 1) L4T release file (authoritative)
    try:
        with open("/etc/nv_tegra_release", "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        match = re.search(r"R(\d+)", first_line)
        if match:
            return int(match.group(1)) >= JETPACK7_L4T_MAJOR
    except Exception:
        pass
    # 2) Kernel fallback, e.g. "6.8.12-1021-tegra"
    try:
        release = platform.release()
        if "tegra" in release:
            major, minor = (int(p) for p in release.split(".")[:2])
            return (major, minor) >= (6, 8)
    except Exception:
        pass
    return False


def devfreq_nodes():
    roots = ["/sys/class/devfreq/gpu-gpc-0", "/sys/class/devfreq/gpu-nvd-0"]
    return [p for p in roots if os.path.isdir(p)]
