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


from .common import cat, check_file
import os
import re
import subprocess
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)
TEMPERATURE_RE = re.compile(r'^temp(?P<num>\d+)_label$')
TEMPERATURE_OFFLINE = -256


def read_temperature(data):
    values = {}
    for name, value in data.items():
        try:
            # Check if value is already a number (from Mellanox) or a path
            if isinstance(value, (int, float)):
                # Direct numeric value (already in millidegrees)
                values[name] = value / 1000.0
            else:
                # Path to temperature file
                temp_value = float(cat(value)) / 1000.0
                values[name] = temp_value
        except (OSError, ValueError):
            # If negative sensor offline
            values[name] = TEMPERATURE_OFFLINE
    return values


def get_virtual_thermal_temperature(thermal_path):
    temperature = {}
    # Find all thermal zone available
    items = os.listdir(thermal_path)
    subdirectories = ["{path}/{item}".format(path=thermal_path, item=item)
                      for item in items if os.path.isdir(os.path.join(thermal_path, item)) and 'thermal_' in item]
    # Check if is a real temperature
    idx = 0
    for thermal_path in subdirectories:
        path_name = "{path}/type".format(path=thermal_path)
        path_value = "{path}/temp".format(path=thermal_path)
        if os.path.isfile(path_name) and os.path.isfile(path_value):
            # Decode name
            raw_name = cat(path_name).strip()
            name = raw_name.split("-")[0] if '-' in raw_name else raw_name.split("_")[0]
            # Remove PMIC temperature (TX family)
            if 'PMIC' in name:
                logger.warn("Skipped PMIC")
                continue
            # Store new temperature
            name = name if name not in temperature else "{name}{idx}".format(name=name, idx=idx)
            idx = idx if name not in temperature else idx + 1
            # Check if is readable and accessible
            if check_file(os.path.join(thermal_path, "temp")):
                temperature[name] = {'temp': os.path.join(thermal_path, "temp")}
                # Message detected
                logger.info("Found thermal \"{name}\" in {path}".format(name=name, path=os.path.basename(thermal_path)))
    # Sort all temperatures
    return temperature


def get_hwmon_thermal_system(root_dir):
    sensor_name = {}
    if not os.path.isdir(root_dir):
        logger.error("Folder {root_dir} doesn't exist".format(root_dir=root_dir))
        return sensor_name
    # Fin all fans
    for dir in os.listdir(root_dir):
        path = os.path.join(root_dir, dir)
        if not os.path.isdir(path):
            continue
        # Find all pwm in folder
        for file in os.listdir(path):
            name_label_path = os.path.join(path, file)
            # Check if there is a label
            match = re.search(TEMPERATURE_RE, file)
            if not match:
                continue
            parsed_name = match.groupdict()
            # Build list current and average power read
            number_port = int(parsed_name['num'])
            # Read name
            raw_name = cat(name_label_path).strip()
            logger.info("Found temperature sensor: {name}".format(name=raw_name))
            # Build list of path
            path_crit_alarm = os.path.join(path, "temp{num}_crit_alarm".format(num=number_port))
            if check_file(path_crit_alarm):
                warnings = {'crit_alarm': path_crit_alarm}
                values = read_temperature(warnings)
                logger.info("Alarms {name} - {data}".format(name=raw_name, data=values))
            # Read Temperatures
            sensor = {}
            if check_file(os.path.join(path, "temp{num}_input".format(num=number_port))):
                sensor['temp'] = os.path.join(path, "temp{num}_input".format(num=number_port))  # Temperature in deg
            if check_file(os.path.join(path, "temp{num}_input".format(num=number_port))):
                sensor['max'] = os.path.join(path, "temp{num}_max".format(num=number_port))  # Temperature in deg
            if check_file(os.path.join(path, "temp{num}_input".format(num=number_port))):
                sensor['crit'] = os.path.join(path, "temp{num}_crit".format(num=number_port))  # Temperature in deg
            # If there is an file is added in list
            if sensor:
                sensor_name[raw_name] = sensor
    return sensor_name

def get_mellanox_temperature():
    """Detect and read temperature from Mellanox NICs with MLNX_OFED support"""
    temperature = {}
    # Check if mget_temp is available (part of MLNX_OFED)
    try:
        result = subprocess.run(['which', 'mget_temp'], capture_output=True, text=True)
        if result.returncode == 0:
            # mget_temp is available, use it to read temperatures
            logger.info("MLNX_OFED detected, using mget_temp for Mellanox NIC temperatures")
            # Find all Mellanox devices
            try:
                # Get list of Mellanox devices
                devices_result = subprocess.run(['lspci', '-d', '15b3:', '-D'], capture_output=True, text=True)
                if devices_result.returncode == 0 and devices_result.stdout.strip():
                    device_lines = devices_result.stdout.strip().split('\n')
                    for device_line in device_lines:
                        if device_line.strip():
                            # Extract device name and bus address
                            parts = device_line.strip().split()
                            if len(parts) >= 2:
                                bus_addr = parts[0]
                                device_name = ' '.join(parts[1:])
                                # Check if it's a ConnectX device
                                if 'ConnectX' in device_name or 'MT' in device_name:
                                    # Try to read temperature using mget_temp
                                    try:
                                        temp_result = subprocess.run(
                                            ['sudo', 'mget_temp', '-d', bus_addr],
                                            capture_output=True,
                                            text=True,
                                            timeout=2
                                        )
                                        if temp_result.returncode == 0 and temp_result.stdout.strip():
                                            temp_value = temp_result.stdout.strip()
                                            try:
                                                temp_celsius = float(temp_value)
                                                # Create a virtual temperature file path for compatibility
                                                sensor_key = f"mlx_{bus_addr.replace(':', '_').replace('.', '_')}"
                                                temperature[sensor_key] = {
                                                    'temp': temp_celsius * 1000.0  # Store in millidegrees for consistency
                                                }
                                                logger.info(f"Found Mellanox NIC temperature: {device_name} = {temp_celsius}°C")
                                            except ValueError:
                                                logger.warning(f"Could not parse temperature from mget_temp for {bus_addr}")
                                        elif temp_result.returncode != 0:
                                            logger.warning(f"mget_temp failed for {bus_addr}: {temp_result.stderr}")
                                    except subprocess.TimeoutExpired:
                                        logger.warning(f"mget_temp timed out for {bus_addr}")
                                    except Exception as e:
                                        logger.warning(f"Error reading temperature for {bus_addr}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error detecting Mellanox devices: {str(e)}")
    except Exception as e:
        logger.debug(f"mget_temp not available, Mellanox temperature detection skipped: {str(e)}")
    return temperature


class TemperatureService(object):

    def __init__(self):
        self._temperature = {}
        # Find all temperature available
        sys_folder = "/sys"
        if os.getenv('JTOP_TESTING', False):
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=sys_folder))
        # Build folders
        hwmon_dir = os.path.join(sys_folder, "class", "hwmon")
        thermal_path = os.path.join(sys_folder, "devices", "virtual", "thermal")
        if os.path.isdir(thermal_path):
            # Sort all temperatures
            self._temperature = get_virtual_thermal_temperature(thermal_path)
        if os.path.isdir(hwmon_dir):
            hwmon_temperatures = get_hwmon_thermal_system(hwmon_dir)
            self._temperature.update(hwmon_temperatures)
        # Check for Mellanox NICs with MLNX_OFED
        mellanox_temperatures = get_mellanox_temperature()
        self._temperature.update(mellanox_temperatures)
        if not self._temperature:
            logger.warning("Temperature not folder found!")
        # Sort all sensors
        self._temperature = dict(sorted(self._temperature.items(), key=lambda item: item[0].lower()))

    def get_status(self):
        status = {}
        # Read temperature from board
        for name, sensor in self._temperature.items():
            # Check if sensor value is already a number (from Mellanox) or a path
            if isinstance(sensor.get('temp'), (int, float)):
                # Direct value from Mellanox
                values = {'temp': sensor['temp']}
            else:
                # Path-based sensor
                values = read_temperature(sensor)
            # Status sensor
            values['online'] = values['temp'] != TEMPERATURE_OFFLINE
            # Add sensor in dictionary
            status[name] = values
        return status
# EOF
