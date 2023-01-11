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
# EOF
