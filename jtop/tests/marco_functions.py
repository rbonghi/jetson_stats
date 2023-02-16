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

import warnings
# Max count to wait
MAX_COUNT = 50
# TEST NVP MODELS:
# - [0] MAXTEST (DEFAULT)
# - [1] TEST
# - [2] MINTEST
# - [3] MIN_MAX_TEST


def set_fan_profile(jetson, new_profile):
    # Set new speed
    if jetson.ok():
        jetson.fan.profile = new_profile
    # Wait jetson_clocks on
    counter = 0
    while jetson.ok():
        if jetson.fan.profile == new_profile or counter == MAX_COUNT:
            break
        counter += 1
    if counter == MAX_COUNT:
        warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
    # Check if is true
    assert jetson.fan.profile == new_profile


def set_fan_speed(jetson, new_speed):
    # Set new speed
    if jetson.ok():
        jetson.fan.speed = new_speed
    # Wait jetson_clocks on
    counter = 0
    while jetson.ok():
        if jetson.fan.speed == new_speed or counter == MAX_COUNT:
            break
        counter += 1
    if counter == MAX_COUNT:
        warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
    # Check if is true
    assert jetson.fan.speed == new_speed


def set_jetson_clocks(jetson, status):
    if jetson.jetson_clocks is None:
        warnings.warn("jetson_clocks does not exists, please check file", UserWarning)
        return
    # Check if status is different
    if bool(jetson.jetson_clocks) != status:
        # Set true jetson_clocks
        if jetson.ok():
            jetson.jetson_clocks = status
        # Wait jetson_clocks on
        counter = 0
        while jetson.ok():
            if bool(jetson.jetson_clocks) == status or counter == MAX_COUNT:
                break
            counter += 1
        if counter == MAX_COUNT:
            warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
    # Check if is true
    assert bool(jetson.jetson_clocks) == status


def set_nvp_mode(jetson, mode):
    # Check if status is different
    print("NVP-MODE: BEFORE assert str(jetson.nvpmodel)={nvp} - mode={mode}".format(nvp=str(jetson.nvpmodel), mode=mode))
    if str(jetson.nvpmodel) != mode:
        # Check status nvpmodel
        if jetson.ok():
            jetson.nvpmodel = mode
        # Wait change nvpmodel
        counter = 0
        while jetson.ok():
            if str(jetson.nvpmodel) == mode or counter == MAX_COUNT:
                break
            counter += 1
        if counter == MAX_COUNT:
            warnings.warn("Max time counter {counter}".format(counter=MAX_COUNT), UserWarning)
    # Check if is same model
    print("NVP-MODE: assert jetson.nvpmodel={nvp} - mode={mode}".format(nvp=str(jetson.nvpmodel), mode=mode))
    assert str(jetson.nvpmodel) == mode
    # Check name variable
    assert jetson.nvpmodel.name == mode
# EOF
