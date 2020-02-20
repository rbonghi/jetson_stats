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


from jtop import import_jetson_variables


def test_load():
    JETSONS = import_jetson_variables()
    assert len(JETSONS) > 0


def test_env():
    JETSONS = import_jetson_variables()
    # Check contain JETSON_BOARD
    assert "JETSON_BOARD" in JETSONS
    # Check contain JETSON_L4T
    assert "JETSON_L4T" in JETSONS
    # Check contain JETSON_CUDA
    assert "JETSON_CUDA" in JETSONS

# EOF
