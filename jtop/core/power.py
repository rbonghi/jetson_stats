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
    # https://forums.developer.nvidia.com/t/orin-nx-power-data-from-jtop/242804/5
    total_name = ""
    for val in power:
        if val in ["POM_5V_IN", "VDD_IN"]:
            total_name = val
            break
    # Extract the total from list
    # Otherwise sum all values
    # Example for Jetson Xavier
    # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
    if total_name:
        total = power[total_name]
        total['name'] = total_name
        del power[total_name]
        return total, power
    # Otherwise measure all total power
    total = {'power': 0, 'avg': 0, 'unit': 'm'}
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


def find_all_i2c_power_monitor(i2c_path):
    power_sensor = {}
    if not os.path.isdir(i2c_path):
        logger.error("Folder {root_dir} doesn't exist".format(root_dir=i2c_path))
        return power_sensor
    power_i2c_sensors = {}
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
                power_i2c_sensors[item] = find_driver_power_folders(path)
    # Build list of all power folder outputs
    # Find all voltage and current monitor
    for name, paths in power_i2c_sensors.items():
        for path in paths:
            sensors = list_all_i2c_ports(path)
            power_sensor.update(sensors)
    if power_sensor:
        logger.info("Found I2C power monitor")
    return power_sensor


def read_power_status(data):
    values = {}
    power_type = data['type']
    for name, path in data.items():
        if 'type' in name:
            continue
        # Fix from values with "ma" in the end, like
        # warn 32760 ma
        raw_value = int(cat(path).split(" ")[0])
        values[name] = raw_value // 1000 if power_type == 'SYSTEM' else raw_value
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
                'type': 'I2C',
            }
            values = read_power_status(warnings)
            logger.info("Alarms {name} - {data}".format(name=raw_name, data=values))
            # Read Voltage, current and limits
            sensor_name[raw_name] = {
                'volt': "{path}/in{num}_input".format(path=path, num=number_port),  # Voltage in mV
                'curr': "{path}/curr{num}_input".format(path=path, num=number_port),  # Current in mA
                'warn': "{path}/curr{num}_max".format(path=path, num=number_port),  # in mA
                'crit': "{path}/curr{num}_crit".format(path=path, num=number_port),  # in mA
                'type': 'I2C',
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
                'crit': "{path}/crit_current_limit_{num}".format(path=path, num=number_port),  # in
                'type': 'I2C',
            }
    return sensor_name


def find_all_system_monitor(system_monitor):
    sensor_name = {}
    if not os.path.isdir(system_monitor):
        logger.error("Folder {root_dir} doesn't exist".format(root_dir=system_monitor))
        return sensor_name
    # Find all system power monitor
    for folder in os.listdir(system_monitor):
        local_path = "{path}/{folder}".format(path=system_monitor, folder=folder)
        name = folder.replace("ucsi-source-psy-", "")
        # Read type
        path_type = "{path}/type".format(path=local_path)
        type_supply = cat(path_type).strip()
        # Read model name
        path_name = "{path}/model_name".format(path=local_path)
        model_name = cat(path_name).strip() if os.path.isfile(path_name) else ""
        logger.info("Found name={name} type={type} model={model}".format(name=name, type=type_supply, model=model_name))
        # Find power, current and voltage
        voltage_path = "{path}/voltage_now".format(path=local_path)
        current_path = "{path}/current_now".format(path=local_path)
        current_max_path = "{path}/current_max".format(path=local_path)
        if os.path.isfile(voltage_path) and os.path.isfile(current_path):
            sensor_name[name] = {
                'volt': voltage_path,  # Voltage in mV
                'curr': current_path,  # Current in mA
                'type': 'SYSTEM',
            }
            if os.path.isfile(current_max_path):
                sensor_name[name]['warn'] = current_max_path
    if sensor_name:
        logger.info("Found SYSTEM power monitor")
    return sensor_name


class PowerService(object):

    def __init__(self):
        self._power_sensor = {}
        self._power_avg = {}
        # Find all I2C sensors on board
        i2c_path = "/sys/bus/i2c/devices"
        system_monitor = "/sys/class/power_supply"
        if os.getenv('JTOP_TESTING', False):
            i2c_path = "/fake_sys/bus/i2c/devices"
            system_monitor = "/fake_sys/class/power_supply"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=i2c_path))
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=system_monitor))
        # Load all power sensors
        self._power_sensor = find_all_i2c_power_monitor(i2c_path)
        self._power_sensor.update(find_all_system_monitor(system_monitor))
        if not self._power_sensor:
            logger.warning("Power sensors not found!")
        # Sort all power sensors
        self._power_sensor = dict(sorted(self._power_sensor.items(), key=lambda item: item[0]))

    def reset_avg_power(self):
        # Reset dictionary
        self._power_avg = {}

    def get_status(self):
        # If there are no sensors return an empty list
        if not self._power_sensor:
            return {}
        # Otherwise measure all values
        rails = {}
        for name, sensors in self._power_sensor.items():
            # Read status sensors
            values = read_power_status(sensors)
            # Measure power
            if 'power' not in values:
                power = values['volt'] * (float(values['curr']) / 1000)
                values['power'] = int(power)
            # print(name, 'Power', values['power'], power)
            # Measure average Power between first and previous interval
            if name in self._power_avg:
                old_avg = self._power_avg[name]
                values['avg'] = (values['power'] + old_avg) // 2
                self._power_avg[name] = values['avg']
            else:
                values['avg'] = values['power']
                self._power_avg[name] = values['power']
            # Add unit
            values['unit'] = 'm'
            # Add on power status
            rails[name] = values
        # Measure total power
        total, rails = total_power(rails)
        return {'rail': rails, 'tot': total}
# EOF
