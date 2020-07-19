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

from jtop import jtop


if __name__ == "__main__":

    print("All accessible jtop properities")

    with jtop() as jetson:
        # boards
        print('*** board ***')
        print(jetson.board)
        # jetson.ok() will provide the proper update frequency
        while jetson.ok():
            # CPU
            print('*** CPUs ***')
            print(jetson.cpu)
            # GPU
            print('*** GPU ***')
            print(jetson.gpu)
            # Engines
            print('*** engine ***')
            print(jetson.engine)
            # nvpmodel
            print('*** NV Power Model ***')
            print(jetson.nvpmodel)
            # jetson_clocks
            print('*** jetson_clocks ***')
            print(jetson.jetson_clocks)
            # Status disk
            print('*** disk ***')
            print(jetson.disk)
            # Status fans
            print('*** fan ***')
            print(jetson.fan)
            # uptime
            print('*** uptime ***')
            print(jetson.uptime)
            # local interfaces
            print('*** local interfaces ***')
            print(jetson.local_interfaces)
            # Temperature
            print('*** temperature ***')
            print(jetson.temperature)
            # Power
            print('*** power ***')
            print(jetson.power)
            # EMC
            print('*** emc ***')
            print(jetson.emc)
            # IRAM
            print('*** ram ***')
            print(jetson.ram)
            # IRAM
            print('*** iram ***')
            print(jetson.iram)
            # MTS
            print('*** mts ***')
            print(jetson.mts)
# EOF
