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

from jtop import jtop


def test_set_true_false(jtop_server):
    with jtop() as jetson:
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'inactive'
        # check status is false
        assert not bool(jetson.jetson_clocks)
        # Set true jetson_clocks
        jetson.jetson_clocks = True
        # Wait jetson_clocks on
        while not jetson.jetson_clocks:
            pass
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'running'
        # Check if is true
        assert bool(jetson.jetson_clocks)
        # Switch off jetson_clocks
        jetson.jetson_clocks = False
        # Wait jetson_clocks on
        while bool(jetson.jetson_clocks):
            pass
        # Check jetson_clocks status
        assert jetson.jetson_clocks.status == 'inactive'
        # Set to false jetson_clocks
        assert not bool(jetson.jetson_clocks)


def test_set_boot(jtop_server):
    with jtop() as jetson:
        # Check status boot
        jetson.jetson_clocks.boot = True
        # Wait jetson_clocks boot
        while not bool(jetson.jetson_clocks.boot):
            pass
        # Check if is not set
        assert jetson.jetson_clocks.boot
        # Check status boot
        jetson.jetson_clocks.boot = False
        # Wait jetson_clocks boot
        while bool(jetson.jetson_clocks.boot):
            pass
        # Check if is not set
        assert not jetson.jetson_clocks.boot
# EOF
