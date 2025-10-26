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

THOR_GPC = "/sys/class/devfreq/gpu-gpc-0"


def is_thor() -> bool:
    return os.path.isdir(THOR_GPC)


def devfreq_nodes():
    roots = ["/sys/class/devfreq/gpu-gpc-0", "/sys/class/devfreq/gpu-nvd-0"]
    return [p for p in roots if os.path.isdir(p)]
