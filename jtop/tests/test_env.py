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


def test_example(setup_jtop_server):
    with jtop() as jetson:
        # Check contain hardware variables
        assert len(jetson.board['hardware']) > 0
        # Check contain Libraries information
        assert len(jetson.board['libraries']) > 0
        # Check contain platform variables
        assert len(jetson.board['platform']) > 0


test_example = pytest.mark.parametrize("setup_jtop_server", [['empty']], indirect=True)(test_example)
# EOF
