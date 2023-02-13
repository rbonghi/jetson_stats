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


from .common import cat
import os
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)


def initialize_discrete_temperature(thermal_path):
    temperature = {}
    # Find all thermal zone available
    items = os.listdir(thermal_path)
    subdirectories = ["{path}/{item}".format(path=thermal_path, item=item)
                      for item in items if os.path.isdir(os.path.join(thermal_path, item)) and 'thermal_' in item]
    # Check if is a real temperature
    for thermal_path in subdirectories:
        path_name = "{path}/type".format(path=thermal_path)
        path_value = "{path}/temp".format(path=thermal_path)
        if os.path.isfile(path_name) and os.path.isfile(path_value):
            # Decode name
            raw_name = cat(path_name).strip()
            name = raw_name.split("-")[0] if '-' in raw_name else raw_name.split("_")[0]
            # Check value is not -256
            # Remove all CV temperatures and GPU negative in (Orin family)
            # value = float(cat(path_value)) / 1000.0
            # if value == -256:
            #     logger.warn("Skipped {name} temperature= -256C".format(name=name))
            #     continue
            # Remove PMIC temperature (TX family)
            if 'PMIC' in name:
                logger.warn("Skipped PMIC")
                continue
            # Store new temperature
            temperature[name] = thermal_path
    # Sort all temperatures
    return dict(sorted(temperature.items(), key=lambda item: item[0]))


class TemperatureService(object):

    def __init__(self):
        self._temperature = {}
        # Find all temperature available
        thermal_path = "/sys/devices/virtual/thermal"
        if os.getenv('JTOP_TESTING', False):
            thermal_path = "/fake_sys/devices/virtual/thermal"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=thermal_path))
        if os.path.isdir(thermal_path):
            # Sort all temperatures
            self._temperature = initialize_discrete_temperature(thermal_path)
        else:
            logger.warning("Temperature not folder found!")

    def get_status(self):
        status = {}
        # Read temperature from board
        for name, thermal_path in self._temperature.items():
            path_value = "{path}/temp".format(path=thermal_path)
            value = float(cat(path_value)) / 1000.0
            status[name] = value
        return status
# EOF
