# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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

import time
import pytest
from ..service import JtopServer
from ..core import JtopException
# Test functions
from .common import remove_tests
# pytest fixture reference
# https://docs.pytest.org/en/stable/fixture.html


@pytest.fixture(scope="function")
def jtop_server():
    # Clean test files
    remove_tests()
    print("Initialize jtop service")
    jtop_server = JtopServer(force=True, path_fan=['tests/fan/'])
    try:
        jtop_server.start()
    except JtopException as e:
        print(e)
        jtop_server.remove_files()
    # Check if is alive
    assert jtop_server.is_alive()
    # yeld server
    yield jtop_server
    jtop_server.close()
    time.sleep(1.0)
    print("Close jtop service")
    # Clean test files
    remove_tests()


@pytest.fixture(scope="function")
def jtop_server_nothing():
    # Clean test files
    remove_tests()
    print("Initialize jtop service")
    jtop_server = JtopServer(force=True, path_fan=[], path_nvpmodel=[], path_jetson_clocks=[])
    try:
        jtop_server.start()
    except JtopException as e:
        print(e)
        jtop_server.remove_files()
    # Check if is alive
    assert jtop_server.is_alive()
    # yeld server
    yield jtop_server
    jtop_server.close()
    time.sleep(1.0)
    print("Close jtop service")
    # Clean test files
    remove_tests()
# EOF
