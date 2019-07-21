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

from jtop import Fan


def test_wrong_open():
    # Initialize object
    try:
        Fan('wrong_path')
        assert False
    except Fan.FanException:
        assert True


def test_open():
    # Init fan
    fan = Fan('tests/fan/')
    # Update
    fan.update()
    # Check dictionary
    assert 'cap' in fan.status
    assert 'step' in fan.status
    assert 'cpwm' in fan.status
    assert 'tpwm' in fan.status
    assert 'status' in fan.status
    # Read status fan
    assert fan.status['tpwm'] == 100
# EOF
