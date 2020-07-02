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


def test_read_fan_status(jtop_server):
    with jtop() as jetson:
        # Read status jetson fan
        assert isinstance(jetson.fan.auto, bool)
        # Check measure
        assert isinstance(jetson.fan.measure, float)
        # Check speed
        assert isinstance(jetson.fan.speed, float)
        # Check mode in config
        assert jetson.fan.mode in jetson.fan.configs
# EOF
