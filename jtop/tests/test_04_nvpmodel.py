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
import warnings
from jtop import jtop, NVPModel
from .marco_functions import set_jetson_clocks, set_nvp_mode
from .conftest import emulate_all_devices
# Max count to wait
MAX_COUNT = 50


def test_nvpmodel_output(setup_jtop_server):
    device, jtop_server = setup_jtop_server
    with jtop() as jetson:
        print("Running test with parameter:", device)
        if jetson.ok():
            # Read nvpmodel status
            nvpmodel = jetson.nvpmodel
            # Status nvpmodel
            print("nvpmodel output: {nvpmodel}".format(nvpmodel=nvpmodel))
            # Check depend of parameter
            if device in ['simple', 'tk', 'tx']:
                assert nvpmodel is None
            else:
                assert isinstance(nvpmodel, NVPModel)


def test_nvpmodel(setup_jtop_server):
    with jtop() as jetson:
        # Check status nvpmodel
        set_nvp_mode(jetson, "MIN_MAX_TEST")


def test_nvpmodel_fail(setup_jtop_server):
    with jtop() as jetson:
        # Check status nvpmodel
        if jetson.ok():
            jetson.nvpmodel = "MINTEST"
        # Check if is same model
        assert str(jetson.nvpmodel) != "MINTEST"
        # Check name variable
        assert jetson.nvpmodel.name != "MINTEST"


def test_nvpmodel_increment_decrement(setup_jtop_server):
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


def test_nvpmodel_jetson_clocks(setup_jtop_server):
    with jtop() as jetson:
        # Enable jetson_clocks
        set_jetson_clocks(jetson, True)
        # Check status nvpmodel
        set_nvp_mode(jetson, "TEST")
        # Disable jetson_clocks
        set_jetson_clocks(jetson, False)
        # Check status nvpmodel
        set_nvp_mode(jetson, "MIN_MAX_TEST")


test_nvpmodel_output = pytest.mark.parametrize(
    "setup_jtop_server", emulate_all_devices(), indirect=True)(test_nvpmodel_output)
test_nvpmodel = pytest.mark.parametrize(
    "setup_jtop_server", ['nano', 'xavier', 'orin'], indirect=True)(test_nvpmodel)
test_nvpmodel_fail = pytest.mark.parametrize(
    "setup_jtop_server", ['nano', 'xavier', 'orin'], indirect=True)(test_nvpmodel_fail)
test_nvpmodel_increment_decrement = pytest.mark.parametrize(
    "setup_jtop_server", ['nano', 'xavier', 'orin'], indirect=True)(test_nvpmodel_increment_decrement)
test_nvpmodel_jetson_clocks = pytest.mark.parametrize(
    "setup_jtop_server", ['nano', 'xavier', 'orin'], indirect=True)(test_nvpmodel_jetson_clocks)
# EOF
