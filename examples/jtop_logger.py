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

from jtop import jtop, JtopException
import csv
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple jtop logger')
    # Standard file to store the logs
    parser.add_argument('--file', action="store", dest="file", default="log.csv")
    args = parser.parse_args()

    print("Simple jtop logger")
    print("Saving log on {file}".format(file=args.file))

    try:
        with jtop() as jetson:
            # Make csv file and setup csv
            with open(args.file, 'w') as csvfile:
                stats = jetson.stats
                # Initialize cws writer
                writer = csv.DictWriter(csvfile, fieldnames=stats.keys())
                # Write header
                writer.writeheader()
                # Write first row
                writer.writerow(stats)
                # Start loop
                while jetson.ok():
                    stats = jetson.stats
                    # Write row
                    writer.writerow(stats)
                    print("Log at {time}".format(time=stats['time']))
    except JtopException as e:
        print(e)
    except KeyboardInterrupt:
        print("Closed with CTRL-C")
    except IOError:
        print("I/O error")
# EOF
