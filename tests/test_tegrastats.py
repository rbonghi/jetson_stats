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

from jtop import Tegrastats


def test_wrong_open():
    # Initialize object
    tegra = Tegrastats('wrong_path', 100)
    try:
        # Open data
        tegra.open()
        assert False
    except Tegrastats.TegrastatsException:
        assert True


def test_open():
    # Initialize object
    tegra = Tegrastats('/usr/bin/tegrastats', 100)
    # Open data
    tegra.open()
    # Close connection
    tegra.close()
    assert True


def check_tegra(stats):
    # Check if is correctly written the variable
    assert "RAM" in stats
    variable = stats["RAM"]
    # Check if ram["used"] is a list
    assert isinstance(variable["use"], int)
    # Check temperature is in list
    assert "TEMP" in stats
    variable = stats["TEMP"]
    # Check negative number is parsed
    assert variable["BCPU"] < 0


def test_stats():
    # Load tegracontroller
    with Tegrastats('/usr/bin/tegrastats', 100) as tegra:
        # Check tegra stats
        check_tegra(tegra.stats)


def test_stats_callback():
    # Initialize object
    tegra = Tegrastats('/usr/bin/tegrastats', 100)
    # Open data
    tegra.open(check_tegra)
    # Close connection
    tegra.close()
# EOF
