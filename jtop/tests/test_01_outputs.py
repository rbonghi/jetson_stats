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

import pytest
import os
from datetime import timedelta
from multiprocessing.pool import Pool
from jtop import jtop
from jtop.core.memory import Memory
from jtop.core.fan import Fan
from .conftest import emulate_all_devices
NUM_PROCESSES = 20


def check_attributes(jetson):
    # Jetson stats
    assert isinstance(jetson.stats, dict)
    # uptime
    assert isinstance(jetson.uptime, timedelta)
    # CPU
    assert isinstance(jetson.cpu, dict)
    # Memory
    assert isinstance(jetson.memory, Memory)
    # Fan
    assert isinstance(jetson.fan, Fan)
    # GPU
    assert isinstance(jetson.gpu, list)
    # Engines
    assert isinstance(jetson.engine, dict)
    # Status disk
    assert isinstance(jetson.disk, dict)
    # local interfaces
    assert isinstance(jetson.local_interfaces, dict)
    # Check power
    assert isinstance(jetson.power, dict)
    # Check temperature
    assert isinstance(jetson.temperature, dict)


def test_hardware(setup_jtop_server):
    with jtop() as jetson:
        # Check contain hardware variables
        assert len(jetson.board['hardware']) > 0
        # Check contain Libraries information
        assert len(jetson.board['libraries']) > 0
        # Check contain platform variables
        assert len(jetson.board['platform']) > 0


def test_open(setup_jtop_server):
    with jtop() as jetson:
        # Check status OK
        assert jetson.ok()
        # Check all attributes
        check_attributes(jetson)


def jtop_callback(jetson):
    # Check all attributes
    check_attributes(jetson)
    # Close connection
    jetson.close()


def test_open_callback(setup_jtop_server):
    # Initialize object
    jetson = jtop()
    # Attach callback
    jetson.attach(jtop_callback)
    # start jtop
    jetson.start()


def jtop_worker(x):
    with jtop() as jetson:
        print("[{x}] jtop started on PID {pid}".format(x=x, pid=os.getpid()))
        # Check status OK
        for _ in range(10):
            assert jetson.ok()
    return True


def test_multiple_run(setup_jtop_server):
    p = Pool(NUM_PROCESSES)
    pool_output = p.map(jtop_worker, range(NUM_PROCESSES))
    # Check all return true
    assert all(pool_output)
    # Close pool
    p.close()
    p.join()


test_hardware = pytest.mark.parametrize("setup_jtop_server", emulate_all_devices(), indirect=True)(test_hardware)
test_open = pytest.mark.parametrize("setup_jtop_server", emulate_all_devices(), indirect=True)(test_open)
test_open_callback = pytest.mark.parametrize("setup_jtop_server", emulate_all_devices(), indirect=True)(test_open_callback)
test_multiple_run = pytest.mark.parametrize("setup_jtop_server", emulate_all_devices(), indirect=True)(test_multiple_run)
# EOF
