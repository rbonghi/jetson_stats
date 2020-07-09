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


def read_stats(jetson):
    """
    This is your callback function where you can read all files when are availables.
    """
    print(jetson.stats)


if __name__ == "__main__":
    print("Initialize jtop callback")
    # Open the jtop
    jetson = jtop()
    # Attach a function where you can read the status of your jetson
    jetson.attach(read_stats)

    # This try excpet will catch jtop exception
    try:
        # This loop will manage the jtop status all the time
        # This is a blocking a function, if you do not want use you can use as well
        # start: jetson.start()
        # stop: jetson.stop()
        jetson.loop_for_ever()
    except JtopException as e:
        print(e)
# EOF
