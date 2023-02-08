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
        total = {'power': power[total_name]['power'], 'avg': power[total_name]['avg']}
        del power[total_name]
        return total, power
    # Otherwise measure all total power
    total = {'power': 0, 'avg': 0}
    for value in power.values():
        total['power'] += value['power']
        total['avg'] += value['avg']
    return total, power


def find_driver_power_folders(path):
    subdirectories = []
    driver_items = os.listdir(path)
    for item in driver_items:
        # All folder starting with:
        # - hwmon are JP5 compatible
        # - iio:device from JP4 or below
        if os.path.isdir(os.path.join(path, item)):
            driver_path = "{base_path}/{item}".format(base_path=path, item=item)
            if 'hwmon' in item:
                # Bring the second hwmon folder
                hwmon_name = os.listdir(driver_path)[0]
                driver_path = "{base_path}/{item}".format(base_path=driver_path, item=hwmon_name)
                subdirectories += [driver_path]
            elif 'iio:device' in item:
                subdirectories += [driver_path]
    return subdirectories


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
                # Check which type of driver is working
                power_sensor[item] = find_driver_power_folders(path)
    return power_sensor


def read_power_status(data):
    values = {}
    for name, path in data.items():
        # Fix from values with "ma" in the end, like
        # warn 32760 ma
        raw_value = cat(path).split(" ")[0]
        values[name] = int(raw_value)
    return values


def list_all_i2c_ports(path):
    sensor_name = {}
    # Build list label and path
    for item in os.listdir(path):
        power_label_path = "{path}/{item}".format(path=path, item=item)
        # Check if there is a label
        if item.endswith("_label"):
            # Decode name for JP 5 or above
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
            warnings = {
                'crit_alarm': "{path}/curr{num}_crit_alarm".format(path=path, num=number_port),
                'max_alarm': "{path}/curr{num}_max_alarm".format(path=path, num=number_port),
            }
            values = read_power_status(warnings)
            logger.info("Alarms {name} - {data}".format(name=raw_name, data=values))
            # Read Voltage, current and limits
            sensor_name[raw_name] = {
                'volt': "{path}/in{num}_input".format(path=path, num=number_port),  # Voltage in mV
                'curr': "{path}/curr{num}_input".format(path=path, num=number_port),  # Current in mA
                'warn': "{path}/curr{num}_max".format(path=path, num=number_port),  # in mA
                'crit': "{path}/curr{num}_crit".format(path=path, num=number_port),  # in mA
            }
        elif item.startswith("rail_name_"):
            # Decode name for JP 4 or previous
            raw_name = cat(power_label_path).strip()
            # Build list current and average power read
            number_port = int(item.lstrip("rail_name_"))
            # Build list of path
            # https://forums.developer.nvidia.com/t/jetson-tx1-ina226-power-monitor-with-i2c-interface/43819/5
            sensor_name[raw_name] = {
                'volt': "{path}/in_current{num}_input".format(path=path, num=number_port),  # Voltage in mV
                'curr': "{path}/in_voltage{num}_input".format(path=path, num=number_port),  # Current in mA
                'power': "{path}/in_power{num}_input".format(path=path, num=number_port),  # Power in mW
                'warn': "{path}/warn_current_limit_{num}".format(path=path, num=number_port),  # in mA
                'crit': "{path}/crit_current_limit_{num}".format(path=path, num=number_port),  # in mA
            }
    return sensor_name


class PowerService(object):

    def __init__(self):
        self._power_sensor = {}
        # Find all I2C sensors on board
        power_sensor = find_all_i2c_power_monitor()
        if not power_sensor:
            logging.error("Power sensors not found!")
        # Build list of all power folder outputs
        # Find all voltage and current monitor
        for name, paths in power_sensor.items():
            for path in paths:
                sensors = list_all_i2c_ports(path)
                self._power_sensor.update(sensors)
        # Sort all power sensors
        self._power_sensor = dict(sorted(self._power_sensor.items(), key=lambda item: item[0]))
        # temp
        print("-------------- TEMP DATA --------------")
        status = self.get_status()
        for name, value in status.items():
            print(name, value)
        print("-------------- TEMP DATA - END --------------")

    def get_status(self):
        # If threre are no sensors return an empty list
        if not self._power_sensor:
            return {}
        # Otherwise measure all values
        rails = {}
        for name, sensors in self._power_sensor.items():
            # Read status sensors
            values = read_power_status(sensors)
            # Measure power
            power = values['volt'] * (values['curr'] // 1000)
            if 'power' not in values:
                values['power'] = power
            # print(name, 'Power', values['power'], power)
            # Measure average Power between first and previous interval
            values['avg'] = (values['power'] - values['avg']) // 2 if 'avg' in values else values['power']
            # Add unit
            values['unit'] = 'm'
            # Add on power status
            rails[name] = values
        total, rails = total_power(rails)
        return {'rail': rails, 'tot': total}
# EOF
