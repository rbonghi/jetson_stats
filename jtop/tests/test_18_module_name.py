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

import pytest
from ..core import jetson_variables


@pytest.mark.parametrize("part_number, module", [
    # Read from the EEPROM of a Jetson AGX Thor Developer Kit
    ('699-13834-0008-400 H.1', 'NVIDIA Jetson AGX Thor (Developer kit)'),
    # Reported for a Jetson AGX Orin Industrial (#598)
    ('699-13701-0008-500 R.0', 'NVIDIA Jetson AGX Orin Industrial (64GB ram)'),
])
def test_module_from_part_number(monkeypatch, part_number, module):
    jetson_part_number = "p{board_id}-{sku}".format(board_id=part_number[5:9], sku=part_number[10:14])
    monkeypatch.setattr(jetson_variables, "get_part_number", lambda: (part_number, jetson_part_number))
    hardware = jetson_variables.get_jetson_variables()
    assert hardware['P-Number'] == jetson_part_number
    assert hardware['Module'] == module
# EOF
