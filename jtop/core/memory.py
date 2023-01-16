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

    COLUMNS = ["Client", "Process", "PID", "Size"]

    def __init__(self, path="/sys/kernel/debug/nvmap/iovmm/maps"):
        self._path = path
        self._table = []
        self._total = {}

    def nv_usage(self):
        """
        Extract all memory information about board.
        - NvMapMemUsed: Is the shared memory between CPU and GPU
        - NvMapMemFree: To be define
        """
        meminfo = mem_info()
        total = meminfo.get('MemTotal', {})
        available = meminfo.get('MemAvailable', {})
        shared = meminfo.get('NvMapMemUsed', {})
        nv_usage = {
            'tot': total.get('val', 0),
            'use': total.get('val', 0) - available.get('val', 0),
            'shared': shared.get('val', 0),
            'unit': total.get('unit', 'k')
        }
        if os.path.isfile(self._path):
            # Update table
            self._update_table()
            # Update shared size
            nv_usage['shared'] = self._total['val']
            # Add table nv memory
            nv_usage['table'] = [self.COLUMNS, self._table]
        return nv_usage

    def _convert_cell(self, key, string_cell):
        if key == "Size":
            return {'val': int(string_cell[:-1]), 'unit': string_cell[-1].lower()}
        return string_cell

    def _update_table(self):
        self._table = []
        first = True
        with open(self._path, 'r') as fp:
            for row in fp.readlines():
                if row[0].isspace():
                    continue
                cells = row.split()
                # Load titles
                if first:
                    first = False
                    continue
                if cells[0] == 'total':
                    total_string = cells[-1]
                    self._total = {'val': int(total_string[:-1]), 'unit': total_string[-1].lower()}
                    continue
                self._table += [{self.COLUMNS[idx]: self._convert_cell(self.COLUMNS[idx], cell) for idx, cell in enumerate(cells)}]
# EOF
