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
from ..core import temperature


def write_hwmon(root, files):
    path = os.path.join(root, "hwmon0")
    os.makedirs(path)
    for name, value in files.items():
        with open(os.path.join(path, name), 'w') as f:
            f.write(value)


def test_hwmon_sensor_without_crit(tmp_path):
    # NVMe drive on a Jetson AGX Thor: only the composite sensor has a crit threshold
    write_hwmon(str(tmp_path), {
        "name": "nvme",
        "temp1_label": "Composite", "temp1_input": "35850", "temp1_max": "83850", "temp1_crit": "87850",
        "temp2_label": "Sensor 1", "temp2_input": "45850", "temp2_max": "65261850",
    })
    sensors = temperature.get_hwmon_thermal_system(str(tmp_path))
    assert set(sensors['nvme Composite']) == {'temp', 'max', 'crit'}
    assert set(sensors['nvme Sensor 1']) == {'temp', 'max'}
    values = temperature.read_temperature(sensors['nvme Sensor 1'])
    assert temperature.TEMPERATURE_OFFLINE not in values.values()
# EOF
