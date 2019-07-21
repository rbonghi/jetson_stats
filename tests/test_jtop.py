# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
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


def test_open():
    # Initialize object
    jetson = jtop()
    # Open data
    jetson.open()
    # Close connection
    jetson.close()
    assert True


def test_all():
    # Load tegracontroller
    with jtop() as jetson:
        # Read tegra stats
        assert isinstance(jetson.stats, dict)
        # Status disk
        assert isinstance(jetson.disk, dict)
        # Status fans
        assert jetson.fan is None
        # uptime
        assert isinstance(jetson.uptime, float)
        # nvpmodel
        assert jetson.nvpmodel is not None
        # local interfaces
        assert isinstance(jetson.local_interfaces, dict)
        # boards
        assert isinstance(jetson.board, dict)
# EOF
