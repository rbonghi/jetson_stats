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
from jtop.core.jetson_clocks import JetsonClocks
from .conftest import emulate_all_devices
from .marco_functions import set_jetson_clocks_boot
# test functions
MAX_COUNT = 10


def test_jetson_clocks_output(setup_jtop_server):
    device, jtop_server = setup_jtop_server
    with jtop() as jetson:
        print("Running test with parameter:", device)
        if jetson.ok():
            # Read jetson_clocks status
            jetson_clocks = jetson.jetson_clocks
            # Status jetson_clocks
            print("jetson_clocks output: {jetson_clocks}".format(jetson_clocks=jetson_clocks))
            # Check depend of parameter
            if device in ['simple', 'tk']:
                assert jetson_clocks is None
            else:
                assert isinstance(jetson_clocks, JetsonClocks)


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
    device, jtop_server = setup_jtop_server
    with jtop() as jetson:
        # Set to false jetson_clocks
        assert not bool(jetson.jetson_clocks)
        # Enable on boot
        set_jetson_clocks_boot(jetson, True)
        # Disable on boot
        assert bool(jetson.jetson_clocks.boot)


test_jetson_clocks_output = pytest.mark.parametrize(
    "setup_jtop_server", emulate_all_devices(), indirect=True)(test_jetson_clocks_output)
test_set_true_false = pytest.mark.parametrize(
    "setup_jtop_server", ['tx', 'nano', 'xavier', 'orin'], indirect=True)(test_set_true_false)
test_set_boot = pytest.mark.parametrize(
    "setup_jtop_server", ['tx', 'nano', 'xavier', 'orin'], indirect=True)(test_set_boot)
# EOF
