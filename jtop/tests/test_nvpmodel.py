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

import warnings
from jtop import jtop
from .common import set_jetson_clocks, set_nvp_mode
# Max count to wait
MAX_COUNT = 50


def test_nvpmodel(jtop_server):
    with jtop() as jetson:
        # Check status nvpmodel
        set_nvp_mode(jetson, "MIN_MAX_TEST")


def test_nvpmodel_fail(jtop_server):
    with jtop() as jetson:
        # Check status nvpmodel
        if jetson.ok():
            jetson.nvpmodel = "MINTEST"
        # Wait change nvpmodel
        counter = 0
        while jetson.ok():
            if str(jetson.nvpmodel) == "MINTEST" or counter == MAX_COUNT:
                break
            counter += 1
        # Check if is same model
        assert str(jetson.nvpmodel) != "MINTEST"
        # Check name variable
        assert jetson.nvpmodel.name != "MINTEST"


def test_nvpmodel_increment_decrement(jtop_server):
    with jtop() as jetson:
        # Save nvp ID
        nvp_id = jetson.nvpmodel.id
        # Set new NVP mode
        jetson.nvpmodel += 1
        # Wait change nvpmodel
        counter = 0
        while jetson.ok():
            if jetson.nvpmodel.id == nvp_id + 1 or counter == MAX_COUNT:
                break
            counter += 1
        if counter == MAX_COUNT:
            warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
        # Check if is same model
        assert jetson.nvpmodel.id == nvp_id + 1
        # Save nvp ID
        nvp_id = jetson.nvpmodel.id
        # Set new NVP mode
        jetson.nvpmodel = jetson.nvpmodel - 1
        # Wait change nvpmodel
        counter = 0
        while jetson.ok():
            if jetson.nvpmodel.id == nvp_id - 1 or counter == MAX_COUNT:
                break
            counter += 1
        if counter == MAX_COUNT:
            warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
        # Check if is same model
        assert jetson.nvpmodel.id == nvp_id - 1


def test_nvpmodel_jetson_clocks(jtop_server):
    with jtop() as jetson:
        # Enable jetson_clocks
        set_jetson_clocks(jetson, True)
        # Check status nvpmodel
        set_nvp_mode(jetson, "TEST")
        # Disable jetson_clocks
        set_jetson_clocks(jetson, False)
        # Check status nvpmodel
        set_nvp_mode(jetson, "MIN_MAX_TEST")
# EOF
