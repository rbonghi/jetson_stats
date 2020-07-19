# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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
import re
# Logging
import logging
# from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)
# Memory regular exception
REGEXP = re.compile(r'(.+?):\s+(.+?) (.?)B')


def mem_info(path="/proc/meminfo"):
    list_memory = {}
    with open(path, "r") as fp:
        for line in fp:
            # Search line
            match = REGEXP.search(line)
            if match:
                key = str(match.group(1).strip())
                value = int(match.group(2).strip())
                unit = str(match.group(3).strip())
                list_memory[key] = {'val': value, 'unit': unit}
    return list_memory


class MemoryService(object):

    def __init__(self):
        pass

    def meminfo(self):
        """
        Extract all memory information about board.
        - NvMapMemUsed: Is the shared memory between CPU and GPU
        - NvMapMemFree: To be define
        """
        meminfo = {}
        if os.path.isfile("/proc/meminfo"):
            meminfo = mem_info()
        total = meminfo.get('MemTotal', {})
        available = meminfo.get('MemAvailable', {})
        shared = meminfo.get('NvMapMemUsed', {})
        return {
            'tot': total.get('val', 0),
            'use': total.get('val', 0) - available.get('val', 0),
            'shared': shared.get('val', 0),
            'unit': total.get('unit', 'k')
        }
# EOF
