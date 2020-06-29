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


def test_open(jtop_server):
    with jtop() as jetson:
        # Check status OK
        assert jetson.ok()
        # uptime
        assert isinstance(jetson.uptime, float)
        # Status disk
        assert isinstance(jetson.disk, dict)
        # local interfaces
        assert isinstance(jetson.local_interfaces, dict)
        # Status disk
        assert isinstance(jetson.disk, dict)


def jtop_callback(jetson):
    # uptime
    assert isinstance(jetson.uptime, float)
    # Status disk
    assert isinstance(jetson.disk, dict)
    # local interfaces
    assert isinstance(jetson.local_interfaces, dict)
    # Status disk
    assert isinstance(jetson.disk, dict)
    # Close connection
    jetson.close()


def test_open_callback(jtop_server):
    # Initialize object
    jetson = jtop()
    # Attach callback
    jetson.attach(jtop_callback)
    # start jtop
    jetson.start()
# EOF
