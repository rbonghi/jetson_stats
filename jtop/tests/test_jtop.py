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

import os
import logging
from jtop import jtop
from multiprocessing.pool import Pool
# Create logger
logger = logging.getLogger(__name__)
NUM_PROCESSES = 20


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


def jtop_worker(x):
    with jtop() as jetson:
        logger.info("[{x}] jtop started on PID {pid}".format(x=x, pid=os.getpid()))
        # Check status OK
        for _ in range(10):
            assert jetson.ok()
    return True


def test_multiple_run(jtop_server):
    p = Pool(NUM_PROCESSES)
    pool_output = p.map(jtop_worker, range(NUM_PROCESSES))
    # Check all return true
    assert all(pool_output)
    # Close pool
    p.close()
    p.join()
# EOF
