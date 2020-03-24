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

import sys
from jtop import NVPmodel
from jtop import JetsonClocks


def test_nvp_good():
    # Initialize NVPmodel
    nvp = NVPmodel()
    # Check values
    assert isinstance(nvp.mode, str)
    assert isinstance(nvp.num, int)


def test_initialization():
    # Test board in list
    nvp = NVPmodel()
    assert isinstance(nvp.modes, list)


def test_mode():
    # Test board in list
    nvp = NVPmodel()
    assert nvp.mode == nvp.modes[nvp.num]["Name"]
    assert nvp.num == nvp.modes[nvp.num]["ID"]


def test_set_mode():
    # Initialize NVPmodel
    nvp = NVPmodel()
    # Set value
    assert nvp.set(0)


def test_increase_mode():
    # Initialize NVPmodel
    nvp = NVPmodel()
    # Set value
    assert nvp.increase()


def test_decrease_mode():
    # Initialize NVPmodel
    nvp = NVPmodel()
    # Set value
    assert nvp.decrease()


def test_set_jc_mode():
    # Load JetsonClocks controller
    jc = JetsonClocks(sys.prefix + "/local/jetson_stats")
    try:
        jc.start = True
    except JetsonClocks.JCException:
        pass
    # Initialize NVPmodel
    nvp = NVPmodel(jetson_clocks=jc)
    # Set value
    set_status = nvp.set(0)
    # stop jc
    try:
        jc.start = False
    except JetsonClocks.JCException:
        pass
    assert set_status
# EOF
