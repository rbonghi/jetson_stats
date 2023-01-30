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
from .engine import read_engine
# Create logger
logger = logging.getLogger(__name__)
# Memory regular exception
MEMINFO_REG = re.compile(r'(?P<key>.+):\s+(?P<value>.+) (?P<unit>.)B')
BUDDYINFO_REG = re.compile(r'Node\s+(?P<numa_node>\d+).*zone\s+(?P<zone>\w+)\s+(?P<nr_free>.*)')
MEM_TABLE_REG = re.compile(r'(?P<user>\w+)\s+(?P<process>[^ ]+)\s+(?P<PID>\d+)\s+(?P<size>\d+)(?P<unit>\w)\n')
TOT_TABLE_REG = re.compile(r'total\s+(?P<size>\d+)(?P<unit>\w)')


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


def read_mem_table(path_table):
    table = [
        ['user', 'process', 'PID', 'size'],
    ]
    total = {}
    with open(path_table, "r") as fp:
        for line in fp:
            # Search line
            match = re.search(MEM_TABLE_REG, line)
            if match:
                parsed_line = match.groupdict()
                data = [
                    parsed_line['user'],
                    parsed_line['process'],
                    parsed_line['PID'],
                    {'size': int(parsed_line['size']), 'unit': parsed_line['unit'].lower()}
                ]
                table += [data]
                continue
            # Find total on table
            match = re.search(TOT_TABLE_REG, line)
            if match:
                total = match.groupdict()
                continue
    # return total and table
    return total, table


class MemoryService(object):

    def __init__(self):
        # Extract memory page size
        self._page_size = os.sysconf("SC_PAGE_SIZE")
        # board type
        self._isJetson = os.path.isfile("/sys/kernel/debug/nvmap/iovmm/maps")
        if not os.path.isdir("/sys/kernel/debug/clk/emc"):
            logger.warn("EMC not available")
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
        # NvMapMemUsed: Is the shared memory between CPU and GPU
        # This key is always available on Jetson (not really always)
        ram_shared = status_mem.get('NvMapMemUsed', {})
        ram_shared_val = ram_shared.get('size', 0)
        table = []
        if self._isJetson:
            # Update table
            # Use the memory table to measure
            total, table = read_mem_table("/sys/kernel/debug/nvmap/iovmm/maps")
            # Update shared size
            ram_shared_val = total['size'] if ram_shared_val == 0 else ram_shared_val
        # Extract memory info
        ram_total = status_mem.get('MemTotal', {})
        ram_available = status_mem.get('MemAvailable', {})
        ram_buffer = status_mem.get('Buffers', {})
        # Add fields for RAM
        memory['RAM'] = {
            'tot': ram_total.get('val', 0),
            'used': ram_total.get('val', 0) - ram_available.get('val', 0),
            'buffers': ram_buffer.get('val', 0),
            'shared': ram_shared_val,
            'unit': ram_total.get('unit', 'k'),
            'lfb': large_free_bank,  # In 4MB
        }
        # Add memory table ONLY if available
        if table:
            memory['RAM']['table'] = table
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
        # TODO Add list swap
        # Read EMC status
        if os.path.isdir("/sys/kernel/debug/clk/emc"):
            memory['EMC'] = read_engine("/sys/kernel/debug/clk/emc")
            # TODO Add percentage utilizaiton
        # Read IRAM if available
        if os.path.isdir("/sys/kernel/debug/nvmap/iram"):
            table = read_mem_table("/sys/kernel/debug/nvmap/iram/clients")
            for value in range(1, len(table)):
                print(value)
            memory['IRAM'] = {
                'tot': 0,
                'used': 0,
                'unit': 'k',
            }
        return memory
# EOF
