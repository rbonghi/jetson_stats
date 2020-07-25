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

import os
import time
from jtop.service import JtopServer
from jtop import jtop, JtopException
import shutil
# test functions
from .common import remove_tests
MAX_COUNT = 10


def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        print('Directory not copied. Error: %s' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        print('Directory not copied. Error: %s' % e)


def test_write_fan_speed():
    remove_tests()
    # Copy folder in temp
    if os.path.isdir('/tmp/fan/'):
        shutil.rmtree('/tmp/fan/')
    copyDirectory('tests/fan/', '/tmp/fan/')
    # Start server
    jtop_server = JtopServer(force=True, path_fan=['/tmp/fan/'])
    try:
        jtop_server.start()
    except JtopException as e:
        print(e)
        jtop_server.remove_files()
    # run client
    with jtop() as jetson:
        # Read status jetson fan
        jetson.fan.speed = 50.0
        time.sleep(1)
        with open('/tmp/fan/target_pwm', 'r') as f:
            value = int(f.read())
        assert value == 128
    # Close
    jtop_server.close()
    print("Close jtop service")
    # remove test fan folder
    if os.path.isdir('/tmp/fan/'):
        shutil.rmtree('/tmp/fan/')
    remove_tests()


def test_no_speed_control():
    counter = 0
    remove_tests()
    # Copy folder in temp
    if os.path.isdir('/tmp/fan/'):
        shutil.rmtree('/tmp/fan/')
    copyDirectory('tests/fan/', '/tmp/fan/')
    # Remove fan control file
    if os.path.isfile('/tmp/fan/target_pwm'):
        os.remove('/tmp/fan/target_pwm')
    # Start server
    jtop_server = JtopServer(force=True, path_fan=['/tmp/fan/'])
    try:
        jtop_server.start()
    except JtopException as e:
        print(e)
        jtop_server.remove_files()
    # run client
    with jtop() as jetson:
        # Read status jetson fan
        try:
            jetson.fan.speed = 50.0
        except JtopException as e:
            print(e)
            assert True
        # Check status boot
        jetson.jetson_clocks = True
        # Wait jetson_clocks boot
        while jetson.ok():
            if jetson.jetson_clocks or counter == MAX_COUNT:
                break
    # Close
    jtop_server.close()
    print("Close jtop service")
    # remove test fan folder
    if os.path.isdir('/tmp/fan/'):
        shutil.rmtree('/tmp/fan/')
    remove_tests()


def test_read_fan_status(jtop_server):
    with jtop() as jetson:
        # Read status jetson fan
        assert isinstance(jetson.fan.auto, bool)
        # Check measure
        assert isinstance(jetson.fan.measure, float)
        # Check speed
        assert isinstance(jetson.fan.speed, float)
        # Check mode in config
        assert jetson.fan.mode in jetson.fan.configs


def test_read_fan_error(jtop_server_nothing):
    with jtop() as jetson:
        # Read status jetson fan
        assert len(jetson.fan) == 0
# EOF
