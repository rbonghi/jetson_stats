# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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
from ..core import fan


def write_hwmon(root, entry, files):
    path = os.path.join(root, entry)
    os.makedirs(path)
    for name, value in files.items():
        with open(os.path.join(path, name), 'w') as f:
            f.write(value)
    return path


def test_fans_with_same_hwmon_name(monkeypatch, tmp_path):
    # Two fans driven by pwm-fan, which names both hwmon nodes "pwmfan" (#907)
    monkeypatch.setattr(fan, "is_thor", lambda: False)
    root = str(tmp_path)
    fan0 = write_hwmon(root, "hwmon0", {"name": "pwmfan", "pwm1": "100", "pwm1_enable": "1", "rpm": "2000"})
    fan1 = write_hwmon(root, "hwmon1", {"name": "pwmfan", "pwm1": "150", "pwm1_enable": "1"})
    write_hwmon(root, "hwmon3", {"name": "pwm_tach", "rpm": "3000"})
    fans = fan.get_all_cooling_system(root)
    assert sorted(fans) == ['pwmfan', 'pwmfan1']
    assert fans['pwmfan']['path'] == fan0
    assert fans['pwmfan']['rpm'] == [os.path.join(fan0, "rpm")]
    assert fans['pwmfan1']['path'] == fan1
    assert fans['pwmfan1']['hwmon_name'] == 'pwmfan'


def test_unique_name():
    assert fan._unique_name('pwmfan', {}) == 'pwmfan'
    assert fan._unique_name('pwmfan', {'pwmfan': {}}) == 'pwmfan1'
    assert fan._unique_name('pwmfan', {'pwmfan': {}, 'pwmfan1': {}}) == 'pwmfan2'
# EOF
