# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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

import pytest
from jtop import jtop
# test functions
MAX_COUNT = 10


def test_set_true_false(setup_jtop_server):
    with jtop() as jetson:
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'inactive'
        # check status is false
        assert not bool(jetson.jetson_clocks)
        # Set true jetson_clocks
        jetson.jetson_clocks = True
        # Wait jetson_clocks on
        counter = 0
        while jetson.ok():
            if bool(jetson.jetson_clocks) or counter == MAX_COUNT:
                break
            counter += 1
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'running'
        # Check if is true
        assert bool(jetson.jetson_clocks)
        # Switch off jetson_clocks
        jetson.jetson_clocks = False
        # Wait jetson_clocks on
        counter = 0
        while jetson.ok():
            if not bool(jetson.jetson_clocks) or counter == MAX_COUNT:
                break
            counter += 1
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'inactive'
        # Set to false jetson_clocks
        assert not bool(jetson.jetson_clocks)


def test_set_boot(setup_jtop_server):
    with jtop() as jetson:
        # Check status boot
        jetson.jetson_clocks.boot = True
        # Wait jetson_clocks boot
        counter = 0
        while jetson.ok():
            if jetson.jetson_clocks.boot or counter == MAX_COUNT:
                break
            counter += 1
        # Check if is not set
        assert jetson.jetson_clocks.boot
        # Check status boot
        jetson.jetson_clocks.boot = False
        # Wait jetson_clocks boot
        counter = 0
        while jetson.ok():
            if not jetson.jetson_clocks.boot or counter == MAX_COUNT:
                break
            counter += 1
        # Check if is not set
        assert not jetson.jetson_clocks.boot


test_set_true_false = pytest.mark.parametrize(
    "setup_jtop_server", [['jetson_clocks', 'igpu', 'emc'], ['jetson_clocks', 'igpu', 'emc', 'fan']], indirect=True)(test_set_true_false)
test_set_boot = pytest.mark.parametrize(
    "setup_jtop_server", [['jetson_clocks', 'igpu', 'emc'], ['jetson_clocks', 'igpu', 'emc', 'fan']], indirect=True)(test_set_boot)
# EOF
