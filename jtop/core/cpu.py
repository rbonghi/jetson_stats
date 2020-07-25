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


import re
REGEXP = re.compile(r'(.+?): ((.*))')


def cpu_info():
    list_cpu = {}
    with open("/proc/cpuinfo", "r") as fp:
        for line in fp:
            # Search line
            match = REGEXP.search(line)
            if match:
                key = match.group(1).rstrip()
                value = match.group(2).rstrip()
                # Load value or if it is a new processor initialize a new field
                if key == "processor":
                    idx = int(value) + 1
                    name = "CPU{idx}".format(idx=idx)
                    list_cpu[name] = {}
                else:
                    # Load cpu info
                    list_cpu[name][key] = value
    return list_cpu


def cpu_models():
    # Load cpuinfo
    list_cpu = cpu_info()
    models = {}
    # Find all models
    for name, info in list_cpu.items():
        models[name] = info.get("model name", "")
    return models
# EOF
