#!/usr/bin/env python
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

from jtop import jtop
import time
import csv
import argparse
from datetime import datetime

parser = argparse.ArgumentParser(description='Simple Tegrastats logger.')

# Standard file to store the logs
parser.add_argument('--file', action="store", dest="file", default="log.csv")

args = parser.parse_args()


def build_header(jetson):
    header = ['time']
    header += ['GR3D']
    header += [cpu['name'] for cpu in jetson.stats.get('CPU', [])]
    header += [key for key in jetson.stats.get('TEMP', {}).keys()]
    header += [key for key in jetson.stats.get('VOLT', {}).keys()]
    return header


def build_row(jetson, now):
    row = {'time': now}
    # Add GPU idle
    if 'GR3D' in jetson.stats:
        row['GR3D'] = jetson.stats['GR3D']['val']
    # Add CPUS idle value
    for cpu in jetson.stats.get('CPU', []):
        row[cpu['name']] = cpu.get('val', 'OFF')
    # Add TEMP value
    row.update(jetson.stats.get('TEMP', {}))
    # Add average value VOLT
    for key, value in jetson.stats.get('VOLT', {}).items():
        row[key] = value.get('avg', 'na')
    return row


if __name__ == "__main__":

    print("Simple Tegrastats reader")
    print("Save log on {file}".format(file=args.file))
    first = True
    try:
        with open(args.file, 'w') as csvfile:
            with jtop() as jetson:
                while True:
                    # Make header
                    if first:
                        writer = csv.DictWriter(csvfile, fieldnames=build_header(jetson))
                        writer.writeheader()
                        first = False
                    # Write row
                    now = datetime.now()
                    writer.writerow(build_row(jetson, now))
                    print("Logged at {time}".format(time=now))
                    # Sleep before send new stat
                    time.sleep(1)
    except KeyboardInterrupt:
        print("Closed with CTRL-C")
    except IOError:
        print("I/O error")
