# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020-2023 Raffaello Bonghi.
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
from .common import cat
from .command import Command


# ---------------------
# JETPACK DETECTION
# ---------------------
# Write version of jetpack installed
# https://developer.nvidia.com/embedded/jetpack-archive
NVIDIA_JETPACK = {
    # -------- JP5 --------
    "35.1.0": "5.0.2 GA",
    "34.1.1": "5.0.1 DP",
    "34.1.0": "5.0 DP",
    "34.0.1": "5.0 PRE-DP",
    # -------- JP4 --------
    "32.7.3": "4.6.3",
    "32.7.2": "4.6.2",
    "32.7.1": "4.6.1",
    "32.6.1": "4.6",
    "32.5.2": "4.5.1",
    "32.5.1": "4.5.1",
    "32.5.0": "4.5",
    "32.5": "4.5",
    "32.4.4": "4.4.1",
    "32.4.3": "4.4",
    "32.4.2": "4.4 DP",
    "32.3.1": "4.3",
    "32.2.3": "4.2.3",
    "32.2.1": "4.2.2",
    "32.2.0": "4.2.1",
    "32.2": "4.2.1",
    "32.1.0": "4.2",
    "32.1": "4.2",
    "31.1.0": "4.1.1",
    "31.1": "4.1.1",
    "31.0.2": "4.1",
    "31.0.1": "4.0",
    # -------- Old JP --------
    "28.4.0": "3.3.3",
    "28.2.1": "3.3 | 3.2.1",
    "28.2.0": "3.2",
    "28.2": "3.2",
    "28.1.0": "3.1",
    "28.1": "3.1",
    "27.1.0": "3.0",
    "27.1": "3.0",
    "24.2.1": "3.0 | 2.3.1",
    "24.2.0": "2.3",
    "24.2": "2.3",
    "24.1.0": "2.2.1 | 2.2",
    "24.1": "2.2.1 | 2.2",
    "23.2.0": "2.1",
    "23.2": "2.1",
    "23.1.0": "2.0",
    "23.1": "2.0",
    "21.5.0": "2.3.1 | 2.3",
    "21.5": "2.3.1 | 2.3",
    "21.4.0": "2.2 | 2.1 | 2.0 | 1.2 DP",
    "21.4": "2.2 | 2.1 | 2.0 | 1.2 DP",
    "21.3.0": "1.1 DP",
    "21.3": "1.1 DP",
    "21.2.0": "1.0 DP",
    "21.2": "1.0 DP",
}

DPKG_L4T_CORE_RE = re.compile(r'^nvidia-l4t-core.*install$')


def check_dpkg_nvidia_l4t_core():
    dpkg = Command(['dpkg', '--get-selections'])
    lines = dpkg()
    for line in lines:
        if re.match(DPKG_L4T_CORE_RE, line):
            return True
    return False


def get_nvidia_l4t():
    # Read NV TEGRA RELEASE
    if os.path.isfile('/etc/nv_tegra_release'):
        # NVIDIA Jetson version
        # reference https://devtalk.nvidia.com/default/topic/860092/jetson-tk1/how-do-i-know-what-version-of-l4t-my-jetson-tk1-is-running-/
        # https://stackoverflow.com/questions/16817646/extract-version-number-from-a-string
        # https://askubuntu.com/questions/319307/reliably-check-if-a-package-is-installed-or-not
        # https://github.com/dusty-nv/jetson-inference/blob/7e81381a96c1ac5f57f1728afbfdec7f1bfeffc2/tools/install-pytorch.sh#L296
        nv_tegra_release = cat("/etc/nv_tegra_release").split(", ")
        l4t_release = nv_tegra_release[0].lstrip("# R").rstrip(" (release)")
        l4t_revision = nv_tegra_release[1].lstrip("REVISION: ")
        return '.'.join([l4t_release, l4t_revision])
        # Ectract GCID - DO NOT NEEDED
        # os_variables['GCID'] = nv_tegra_release[2].lstrip("GCID: ")
        # Ectract SOC - DO NOT USE THIS LINE! CONTAINS ALWAYS WRONG OUTPUT
        # number = re.search(SOC_RE, nv_tegra_release[3].lstrip("BOARD: ")).group()
        # os_variables['SOC'] = "tegra{number}".format(number=number)
    elif check_dpkg_nvidia_l4t_core():
        dpkg = Command(['dpkg-query', '--showformat=\'${Version}\'', '--show', 'nvidia-l4t-core'])
        l4t = dpkg()[0]
        return l4t.split('-')[0].lstrip('\'')
    # If not find any L4T return empty string
    return ''


def get_nvidia_jetpack(l4t):
    return NVIDIA_JETPACK.get(l4t, '')
# EOF
