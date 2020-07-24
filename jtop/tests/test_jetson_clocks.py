# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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

import time
from jtop import jtop
from ..service import JtopServer
# test functions
from .common import remove_tests
MAX_COUNT = 10


def test_set_true_false(jtop_server):
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


def test_set_boot(jtop_server):
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


def test_boot_set_true():
    # Clean test files
    remove_tests()
    # Make a new object
    jtop_server = JtopServer(force=True, path_fan=['tests/fan/'])
    # Re run jtop_server
    jtop_server.start()
    # Check if is alive
    assert jtop_server.is_alive()
    # Run jtop
    with jtop() as jetson:
        # Check status boot
        jetson.jetson_clocks.boot = True
        # Wait jetson_clocks boot
        counter = 0
        while jetson.ok():
            if jetson.jetson_clocks.boot or counter == MAX_COUNT:
                break
            counter += 1
    # Close service
    jtop_server.close()
    time.sleep(1.0)
    # Check if is alive
    assert not jtop_server.is_alive()
    # Remove object
    del jtop_server
    # Make a new object
    jtop_server = JtopServer(force=True, path_fan=['tests/fan/'])
    # Re run jtop_server
    jtop_server.start()
    # Check if is alive
    assert jtop_server.is_alive()
    # Check if is booting
    with jtop() as jetson:
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
    # Close service
    jtop_server.close()
    time.sleep(1.0)
    # Check if is alive
    assert not jtop_server.is_alive()
    # Clean test files
    remove_tests()
# EOF
