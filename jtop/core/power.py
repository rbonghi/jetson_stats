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


def total_power(power):
    """
    Function to measure the total watt

    :return: Total power and a second dictionary with all other measures
    :rtype: dict, dict
    """
    # In according with:
    # https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8
    # https://github.com/rbonghi/jetson_stats/issues/51
    # https://forums.developer.nvidia.com/t/tegrastats-monitoring/217088/4?u=user62045
    total_name = ""
    for val in power:
        if "POM_5V_IN" in val:
            total_name = val
            break
    # Extract the total from list
    # Otherwise sum all values
    # Example for Jetson Xavier
    # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
    if total_name:
        total = power[total_name]
        del power[total_name]
        return total, power
    # Otherwise measure all total power
    total = {'cur': 0, 'avg': 0}
    for value in power.values():
        total['cur'] += value['cur']
        total['avg'] += value['avg']
    return total, power


def find_all_i2c_power_monitor():
    power_sensor = {}
    i2c_path = "/sys/bus/i2c/devices"
    items = os.listdir(i2c_path)
    for item in items:
        # Decode full path
        path = "{base_path}/{item}".format(base_path=i2c_path, item=item)
        name_path = "{path}/name".format(path=path)
        if os.path.isfile(name_path):
            raw_name = cat(name_path).strip()
            # Find all shunt and bus voltage monitor mounted on board
            # https://www.ti.com/product/INA3221
            if 'ina3221' in raw_name:
                power_sensor[item] = path
    return power_sensor


def find_all_hwmon_power_monitor():
    power_sensor = {}
    hwmon_path = "/sys/class/hwmon"
    items = os.listdir(hwmon_path)
    for item in items:
        # Decode full path
        path = "{base_path}/{item}".format(base_path=hwmon_path, item=item)
        name_path = "{path}/name".format(path=path)
        if os.path.isfile(name_path):
            raw_name = cat(name_path).strip()
            # Find all shunt and bus voltage monitor mounted on board
            # https://www.ti.com/product/INA3221
            if 'ina3221' in raw_name:
                power_sensor[item] = path
    return power_sensor


def list_all_i2c_ports(path):
    sensor_name = {}
    # Build list label and path
    for item in os.listdir(path):
        # Check if there is a label
        if item.endswith("_label"):
            power_label_path = "{path}/{item}".format(path=path, item=item)
            # Decode name
            raw_name = cat(power_label_path).strip()
            # Remove NC power (Orin family)
            # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#jetson-agx-orin-series
            if 'NC' in raw_name:
                logger.warn("Skipped NC {path}".format(path=power_label_path))
                continue
            # Build list current and average power read
            number_port = int(item.split("_")[0].strip("in"))
            # Skip "sum of shunt voltages" always number 7
            if number_port == 7:
                logger.warn("Skipped \"sum of shunt voltages\" {path}".format(path=power_label_path))
                continue
            # Build list of path
            sensor_name[raw_name] = {
                'input': "{path}/in{num}_input".format(path=path, num=number_port),
                'curr': "{path}/curr{num}_input".format(path=path, num=number_port),
            }
    return sensor_name


class PowerService(object):

    def __init__(self):
        self._power_sensor = {}
        # Find all voltage and current monitor
        if os.path.isdir("/sys/class/hwmon"):
            # Find all hwmons sensors
            hwmons = find_all_hwmon_power_monitor()
            # Find all ports to read
            for name, path in hwmons.items():
                self._power_sensor.update(list_all_i2c_ports(path))
        elif os.path.isdir("/sys/bus/i2c/devices"):
            # Find all sensors using I2C device
            find_all_i2c_power_monitor()
        else:
            logging.error("Temperature folder found!")
        # Sort all power sensors
        self._power_sensor = dict(sorted(self._power_sensor.items(), key=lambda item: item[0]))
        # temp
        status = self.get_status()
        for name, value in status:
            print(name, value)

    def get_status(self):
        status = {}
        for name, path in self._power_sensor.items():
            print(name, path)
        return status
# EOF
