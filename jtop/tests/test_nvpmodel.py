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

from jtop import jtop


def set_jetson_clocks(jetson, status):
    # Check if status is different
    if bool(jetson.jetson_clocks) != status:
        # Set true jetson_clocks
        jetson.jetson_clocks = status
        # Wait jetson_clocks on
        while bool(jetson.jetson_clocks) != status:
            pass
    # Check if is true
    assert bool(jetson.jetson_clocks) == status


def set_nvp_mode(jetson, mode):
    # Check if status is different
    if str(jetson.nvpmodel) != mode:
        # Check status nvpmodel
        jetson.nvpmodel = mode
        # Wait change nvpmodel
        while str(jetson.nvpmodel) != mode:
            pass
    # Check if is same model
    assert str(jetson.nvpmodel) == mode
    # Check name variable
    assert jetson.nvpmodel.name == mode


def test_nvpmodel(jtop_server):
    with jtop() as jetson:
        # Check status nvpmodel
        set_nvp_mode(jetson, "MIN_MAX_TEST")


def test_nvpmodel_increment(jtop_server):
    with jtop() as jetson:
        if jetson.nvpmodel.name != "TEST":
            set_nvp_mode(jetson, "TEST")
        # Save nvp ID
        nvp_id = jetson.nvpmodel.id
        # Set new NVP mode
        jetson.nvpmodel += 1
        # Wait change nvpmodel
        while jetson.nvpmodel.id != 2:
            pass
        # Check if is same model
        assert jetson.nvpmodel.id != nvp_id


def test_nvpmodel_decrement(jtop_server):
    with jtop() as jetson:
        if jetson.nvpmodel.name != "TEST":
            set_nvp_mode(jetson, "TEST")
        # Save nvp ID
        nvp_id = jetson.nvpmodel.id
        # Set new NVP mode
        jetson.nvpmodel -= 1
        # Wait change nvpmodel
        while jetson.nvpmodel.id != 0:
            pass
        # Check if is same model
        assert jetson.nvpmodel.id != nvp_id


def fix_test_nvpmodel_jetson_clocks(jtop_server):
    # TODO Fix test with jetson_clocks
    with jtop() as jetson:
        # Enable jetson_clocks
        set_jetson_clocks(jetson, True)
        # Check status nvpmodel
        set_nvp_mode(jetson, "TEST")
        # Disable jetson_clocks
        set_jetson_clocks(jetson, False)
        # Check status nvpmodel
        set_nvp_mode(jetson, "MAXTEST")
# EOF
