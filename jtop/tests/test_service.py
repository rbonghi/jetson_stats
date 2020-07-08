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

import logging
import time
from jtop import jtop, JtopException
from ..service import JtopServer
# Create logger
logger = logging.getLogger(__name__)


def test_service_full():
    jtop_server = JtopServer(force=True, path_fan=['tests/fan/'])
    jtop_server.start()
    # Check if is alive
    assert jtop_server.is_alive()
    # Close service
    try:
        jtop_server.close()
    except JtopException:
        pass
    # Check if service is off
    assert not jtop_server.is_alive()


def test_service_full_read():
    jtop_server = JtopServer(force=True, path_fan=['tests/fan/'])
    jtop_server.start()
    # Check if is alive
    assert jtop_server.is_alive()
    # Init and open jtop
    jetson = jtop()
    jetson.start()
    # Wait
    time.sleep(0.5)
    # Close service
    jtop_server.close()
    # Close jetson
    try:
        jetson.close()
    except JtopException:
        pass
    # Check if service is off
    assert not jtop_server.is_alive()


def test_service_nothing_read():
    jtop_server = JtopServer(force=True, path_fan=[], path_nvpmodel='')
    jtop_server.start()
    # Check if is alive
    assert jtop_server.is_alive()
    # Init and open jtop
    jetson = jtop()
    jetson.start()
    # Wait
    time.sleep(0.5)
    # Close service
    jtop_server.close()
    # Close jetson
    try:
        jetson.close()
    except JtopException:
        pass
    # Check if service is off
    assert not jtop_server.is_alive()
# EOF
