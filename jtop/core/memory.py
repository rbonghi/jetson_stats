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
MEMINFO_REG = re.compile(r'(?P<key>.+):\s+(?P<value>.+) (?P<unit>.)B')
BUDDYINFO_REG = re.compile(r'Node\s+(?P<numa_node>\d+).*zone\s+(?P<zone>\w+)\s+(?P<nr_free>.*)')
MEM_TABLE_REG = re.compile(r'(?P<user>\w+)\s+(?P<process>[^ ]+)\s+(?P<value>\d+)\s+(?P<size>\d+)(?P<unit>\w)\n')


def meminfo():
    # Read meminfo and decode
    status_mem = {}
    with open("/proc/meminfo", "r") as fp:
        for line in fp:
            # Search line
            match = re.search(MEMINFO_REG, line.strip())
            if match:
                parsed_line = match.groupdict()
                status_mem[parsed_line['key']] = {'val': int(parsed_line['value']), 'unit': parsed_line['unit']}
    return status_mem


def buddyinfo(page_size):
    # Read status free memory
    # http://andorian.blogspot.com/2014/03/making-sense-of-procbuddyinfo.html
    buddyhash = {}
    buddyinfo = open("/proc/buddyinfo").readlines()
    for line in buddyinfo:
        # Decode line
        parsed_line = re.match(BUDDYINFO_REG, line.strip()).groupdict()
        # detect buddy size
        numa_node = int(parsed_line["numa_node"])
        free_fragments = [int(i) for i in parsed_line["nr_free"].split()]
        max_order = len(free_fragments)
        fragment_sizes = [page_size * 2**order for order in range(0, max_order)]
        usage_in_bytes = [free * fragmented for free, fragmented in zip(free_fragments, fragment_sizes)]
        data = {
            "zone": parsed_line["zone"],
            "nr_free": free_fragments,
            "sz_fragment": fragment_sizes,
            "usage": usage_in_bytes}
        buddyhash[numa_node] = buddyhash[numa_node] + [data] if numa_node in buddyhash else [data]
    return buddyhash


def convert_cell(key, string_cell):
    if key == "Size":
        return {'val': int(string_cell[:-1]), 'unit': string_cell[-1].lower()}
    return string_cell


def read_mem_table():
    with open("/sys/kernel/debug/nvmap/iovmm/maps", "r") as fp:
        for line in fp:
            # Search line
            match = re.search(MEM_TABLE_REG, line.strip())
            if match:
                parsed_line = match.groupdict()
                print(parsed_line)

class MemoryService(object):

    COLUMNS = ["Client", "Process", "PID", "Size"]

    def __init__(self):
        # Extract memory page size
        self._page_size = os.sysconf("SC_PAGE_SIZE")
        # board type
        self._isJetson = os.path.isfile("/sys/kernel/debug/nvmap/iovmm/maps")
        # TEMP
        memory = self.get_status()
        print(memory)

    def get_status(self):
        memory = {}
        # Measure the largest free bank for 4MB
        mem_size = buddyinfo(self._page_size)
        # Count only the biggest Large free bank (lfb)
        large_free_bank = 0
        for _, data in mem_size.items():
            large_free_bank += sum([zone['nr_free'][-1] for zone in data])
        # Status Memory
        status_mem = meminfo()
        # Read memory use
        if self._isJetson:
            # Update table
            read_mem_table()
            #total, table = self._update_table()
            # Update shared size
            #nv_usage['shared'] = total['val']
            # Add table nv memory
            #nv_usage['table'] = [self.COLUMNS, table]
        # Extract memory info
        ram_total = status_mem.get('MemTotal', {})
        ram_available = status_mem.get('MemAvailable', {})
        ram_buffer = status_mem.get('Buffers', {})
        # NvMapMemUsed: Is the shared memory between CPU and GPU
        # This key is always available on Jetson (not really always)
        # Use the memory table to measure
        ram_shared = status_mem.get('NvMapMemUsed', {})
        # Add fields for RAM
        memory['RAM'] = {
            'tot': ram_total.get('val', 0),
            'used': ram_total.get('val', 0) - ram_available.get('val', 0),
            'buffers': ram_buffer.get('val', 0),
            'shared': ram_shared.get('val', 0),
            'unit': ram_total.get('unit', 'k'),
            'lfb': large_free_bank,  # In 4MB
        }
        # Extract swap numbers
        swap_total = status_mem.get('SwapTotal', {})
        swap_free = status_mem.get('SwapFree', {})
        swap_cached = status_mem.get('SwapCached', {})
        # Add fields for swap
        memory['SWAP'] = {
            'tot': swap_total.get('val', 0),
            'used': swap_total.get('val', 0) - swap_free.get('val', 0),
            'cached': swap_cached.get('val', 0),
            'unit': swap_total.get('unit', 'k'),
        }
        # TODO Add EMC
        return memory

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
        if os.path.isfile("/sys/kernel/debug/nvmap/iovmm/maps"):
            # Update table
            self._update_table()
            # Update shared size
            nv_usage['shared'] = self._total['val']
            # Add table nv memory
            nv_usage['table'] = [self.COLUMNS, self._table]
        return nv_usage

    def _update_table(self):
        table = []
        total = {}
        first = True
        with open("/sys/kernel/debug/nvmap/iovmm/maps", 'r') as fp:
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
                    total = {'val': int(total_string[:-1]), 'unit': total_string[-1].lower()}
                    continue
                table += [{self.COLUMNS[idx]: convert_cell(self.COLUMNS[idx], cell) for idx, cell in enumerate(cells)}]
        return total, table
# EOF
