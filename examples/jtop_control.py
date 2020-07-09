#!/usr/bin/env python
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

from jtop import jtop, JtopException

if __name__ == "__main__":

    print("Simple jtop controller")

    try:
        # All options are not blocking
        with jtop() as jetson:
            # Read jetson_clocks status
            print(jetson.jetson_clocks)
            # Set a new status
            jetson.jetson_clocks = True
            # Read nvpmodel
            if jetson.nvpmodel:
                # Read nvpmodel
                print(jetson.nvpmodel)
                # Set new state
                jetson.nvpmodel = 0  # You can write the name of the model as well
                # Wait nvpmodel changed
                while jetson.ok():
                    if jetson.nvpmodel.id == 0:
                        break
                # You can increase or decrease the nvpmodel using
                jetson.nvpmodel += 1  # or jetson.nvpmodel = jetson.nvpmodel + 1
                # Wait nvpmodel changed
                while jetson.ok():
                    if jetson.nvpmodel.id == 1:
                        break
            # You can control the fan
            if jetson.fan:
                # read fan status
                print(jetson.fan)
                # You can change mode and setting
                jetson.fan.mode = 'system'
                # Wait nvpmodel changed
                while jetson.ok():
                    if jetson.fan.mode == 'system':
                        break
                # Or you can change the fan speed
                jetson.fan.speed = 100
                while jetson.ok():
                    # Print jetson fan status
                    print(jetson.fan)
                    # Leave when fan measure is at 100%
                    if jetson.fan.measure == 100:
                        break
    except JtopException as e:
        print(e)
# EOF
