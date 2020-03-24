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

from jtop import JetsonClocks
import sys


def test_init_jc():
    # Initialize JetsonClocks
    JetsonClocks(sys.prefix + "/local/jetson_stats")
    assert True


def test_read_status():
    # Initialize JetsonClocks
    jc = JetsonClocks(sys.prefix + "/local/jetson_stats")
    try:
        assert isinstance(jc.status, bool)
    except JetsonClocks.JCException:
        assert True


def status_check(var_status, new_status):
    var_status = new_status
    # Wait a second
    try:
        while var_status != new_status:
            pass
    except JetsonClocks.JCException:
        pass
    # Check the status is the same
    assert var_status == new_status


def test_set_start():
    # Initialize JetsonClocks
    jc = JetsonClocks(sys.prefix + "/local/jetson_stats")
    # check status True
    status_check(jc.start, True)
    # Check status False
    status_check(jc.start, False)


def test_set_enable():
    # Initialize JetsonClocks
    jc = JetsonClocks(sys.prefix + "/local/jetson_stats")
    # check status True
    status_check(jc.enable, True)
    # Check status False
    status_check(jc.enable, False)
# EOF
