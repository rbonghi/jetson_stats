# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
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


def nvjpg(path="/sys/kernel/debug/clk/nvjpg"):
    # Read status enable
    nvjpg = {}
    # Check if access to this file
    if os.access(path + "/clk_enable_count", os.R_OK):
        with open(path + "/clk_enable_count", 'r') as f:
            # Write status engine
            nvjpg['status'] = int(f.read()) == 1
    # Check if access to this file
    if os.access(path + "/clk_rate", os.R_OK):
        with open(path + "/clk_rate", 'r') as f:
            # Write status engine
            nvjpg['rate'] = int(f.read())
    return nvjpg
# EOF
