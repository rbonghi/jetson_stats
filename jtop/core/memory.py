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
import stat
import shlex
# Logging
import logging
import subprocess as sp
from .processes import read_process_table
from .engine import read_engine
from .common import cat, GenericInterface
from .command import Command
# Create logger
logger = logging.getLogger(__name__)
# Memory regular exception
MEMINFO_REG = re.compile(r'(?P<key>.+):\s+(?P<value>.+) (?P<unit>.)B')
FSTAB_RE = re.compile(r'^(?P<path>[^ ]+) +(?P<mount>[^ ]+) +(?P<type>[^ ]+) +(?P<options>[^ ]+) +(?P<dump>\d+) +(?P<pass>\d+)$')
BUDDYINFO_REG = re.compile(r'Node\s+(?P<numa_node>\d+).*zone\s+(?P<zone>\w+)\s+(?P<nr_free>.*)')
SWAP_REG = re.compile(r'(?P<name>[^ ]+)\s+(?P<type>[^ ]+)\s+(?P<size>\d+)\s+(?P<used>\d+)\s+(?P<prio>-?\d+)')
# Swap configuration
PATH_FSTAB = '/etc/fstab'
CONFIG_DEFAULT_SWAP_DIRECTORY = ''
CONFIG_DEFAULT_SWAP_NAME = 'swfile'


def meminfo():
    # Read meminfo and decode
    # https://access.redhat.com/solutions/406773
    status_mem = {}
    with open("/proc/meminfo", 'r') as fp:
        for line in fp:
            # Search line
            match = re.search(MEMINFO_REG, line.strip())
            if match:
                parsed_line = match.groupdict()
                status_mem[parsed_line['key']] = int(parsed_line['value'])
    return status_mem


def buddyinfo(page_size):
    # Read status free memory
    # http://andorian.blogspot.com/2014/03/making-sense-of-procbuddyinfo.html
    buddyhash = {}
    with open("/proc/buddyinfo", 'r') as fp:
        buddyinfo = fp.readlines()
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


def read_swapon():
    """
    This method list all processes working with GPU

    ============== ======================= ======== =============
    name           type                    prio     size
    ============== ======================= ======== =============
    name partition type: partition or file priority dictionary
    ============== ======================= ======== =============

    :return: list of all processes
    :type spin: list
    """
    table = {}
    swap = Command(['swapon', '--show', '--raw', '--byte'])
    lines = swap()
    for line in lines:
        # Search line
        match = re.search(SWAP_REG, line.strip())
        if match:
            parsed_line = match.groupdict()
            name = parsed_line['name']
            data = {
                # Improve this detection. (Now only checking if zram is on name to saving time)
                'type': parsed_line['type'] if 'zram' not in name else 'zram',
                'prio': int(parsed_line['prio']),
                'size': int(parsed_line['size']) // 1024,
                'used': int(parsed_line['used']) // 1024,
            }
            table[name] = data
    return table


def read_fstab():
    fstab = {}
    with open(PATH_FSTAB, "r") as fp:
        for line in fp:
            match = re.search(FSTAB_RE, line.strip())
            if match:
                parsed_line = match.groupdict()
                path = parsed_line['path']
                del parsed_line['path']
                fstab[path] = parsed_line
    return fstab


def read_emc(root_path):
    emc = {}
    # Initialize emc['cur'] to avoid a crash when starting this service
    emc['cur'] = 1
    if os.path.isdir(root_path + "/debug/bpmp/debug/clk/emc"):
        path = root_path + "/debug/bpmp/debug/clk/emc"
        # Check if access to this file
        if os.access(path + "/rate", os.R_OK):
            with open(path + "/rate", 'r') as f:
                # Write min
                emc['cur'] = int(f.read()) // 1000
        # Check if access to this file
        if os.access(path + "/max_rate", os.R_OK):
            with open(path + "/max_rate", 'r') as f:
                # Write min
                emc['max'] = int(f.read()) // 1000
        # Check if access to this file
        if os.access(path + "/min_rate", os.R_OK):
            with open(path + "/min_rate", 'r') as f:
                # Write min
                emc['min'] = int(f.read()) // 1000
        # Check if access to this file
        if os.access(path + "/mrq_rate_locked", os.R_OK):
            with open(path + "/mrq_rate_locked", 'r') as f:
                # Write min
                emc['override'] = int(f.read()) // 1000
    elif os.path.isdir(root_path + "/debug/tegra_bwmgr"):
        path = root_path + "/debug/clk/override.emc"
        # Check if access to this file
        if os.access(path + "/clk_rate", os.R_OK):
            with open(path + "/clk_rate", 'r') as f:
                # Write min
                emc['cur'] = int(f.read()) // 1000
        # Check if access to this file
        if os.access(path + "/clk_state", os.R_OK):
            with open(path + "/clk_state", 'r') as f:
                # Write min
                emc['override'] = int(f.read()) // 1000
        # Decode from tegra_bwmgr
        path = root_path + "/tegra_bwmgr"
        # Check if access to this file
        if os.access(path + "/emc_max_rate", os.R_OK):
            with open(path + "/emc_max_rate", 'r') as f:
                # Write min
                emc['max'] = int(f.read()) // 1000
        # Check if access to this file
        if os.access(path + "/emc_min_rate", os.R_OK):
            with open(path + "/emc_min_rate", 'r') as f:
                # Write min
                emc['min'] = int(f.read()) // 1000
    elif os.path.isdir(root_path + "/clk/emc"):
        emc = read_engine(root_path + "/clk/emc")
    # Fix max frequency
    emc_cap = 0
    # Check if access to this file
    if os.access(root_path + "/nvpmodel_emc_cap/emc_iso_cap", os.R_OK):
        with open(root_path + "/nvpmodel_emc_cap/emc_iso_cap", 'r') as f:
            # Write min
            emc_cap = int(f.read()) // 1000
    # Fix max EMC
    if 'max' in emc:
        if emc_cap > 0 and emc_cap < emc['max']:
            emc['max'] = emc_cap
    # Percentage utilization
    # https://forums.developer.nvidia.com/t/real-time-emc-bandwidth-with-sysfs/107479/3
    if os.access(root_path + "/debug/cactmon/mc_all", os.R_OK):
        with open(root_path + "/debug/cactmon/mc_all", 'r') as f:
            utilization = int(f.read())
    elif os.access(root_path + "/actmon_avg_activity/mc_all", os.R_OK):
        with open(root_path + "/actmon_avg_activity/mc_all", 'r') as f:
            utilization = int(f.read())
    else:
        # if utilization not accesibile return empty EMC data
        return {}
    emc['val'] = utilization // emc['cur']
    # Set always online this engine
    emc['online'] = True
    return emc


class Memory(GenericInterface):
    """
    This class get the output from your memory, this class is readable like a dictionary,
    please read the documentation on :py:attr:`~jtop.jtop.memory` but is also usable to enable, disable swap on your device

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                jetson.memory.swap_set(10, on_boot=False)


    or if you want to deactivate a swap you can use this command

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                jetson.memory.swap_deactivate()

    Below all methods available using the :py:attr:`~jtop.jtop.memory` attribute
    """

    def __init__(self):
        super(Memory, self).__init__()

    def swap_path(self):
        """
        Return the default SWAP path, Default path `/`

        :return: Path swap
        :rtype: str
        """
        return self._init

    def clear_cache(self):
        """
        Clear the memory cache
        """
        # Set new swap size configuration
        self._controller.put({'clear_cache': ''})

    def swap_is_enable(self, path):
        """
        Check if a swap is on list

        :param path: Path swap
        :type path: str

        :return: Status swap
        :rtype: bool
        """
        return path in self._data['SWAP']['table']

    def swap_set(self, value, path='', on_boot=False):
        """
        Create a new swap on a default path. :py:func:`~swap_path`

        :param value: Size in **G** of a new SWAP
        :type value: int
        :param path: Path swap, defaults ''
        :type path: str, optional
        :param on_boot: Set this swap on boot, defaults False
        :type on_boot: bool, optional
        :raises ValueError: value is not an :py:class:`int` or a :py:class:`float`
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Need a Number")
        # if path_swap is empty load from default configuration
        if not path:
            path = self._init
        # Set new swap size configuration
        self._controller.put({'swap': {'command': 'set', 'path': path, 'size': value, 'boot': on_boot}})

    def swap_deactivate(self, path=''):
        """
        Deactivate a swap from a path or from default location `/`

        :param path: Path swap
        :type path: str, optional
        """
        # if path_swap is empty load from default configuration
        if not path:
            path = self._init
        # Set new swap size configuration
        self._controller.put({'swap': {'command': 'unset', 'path': path}})


class MemoryService(object):

    def __init__(self, config):
        self._config = config
        # Extract memory page size
        self._page_size = os.sysconf("SC_PAGE_SIZE")
        # board type
        self._root_path = "/sys/kernel"
        if os.getenv('JTOP_TESTING', False):
            self._root_path = "/fake_sys/kernel"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=self._root_path))
        self._is_emc = True if read_emc(self._root_path) else False
        if self._is_emc:
            logger.info("Found EMC!")
        self._is_iram = os.path.isdir(self._root_path + "/debug/nvmap/iram")
        if self._is_iram:
            logger.info("Found IRAM!")
        # Initialization memory
        logger.info("Memory service started")

    def swap_path(self):
        config = self._config.get('swap', {})
        directory = config.get('directory', CONFIG_DEFAULT_SWAP_DIRECTORY)
        swap_name = config.get('name', CONFIG_DEFAULT_SWAP_NAME)
        return "{directory}/{name}".format(directory=directory, name=swap_name)

    def clear_cache(self):
        """
        Clear cache following https://coderwall.com/p/ef1gcw/managing-ram-and-swap
        """
        clear_cache = Command(['sysctl', 'vm.drop_caches=3'])
        out = clear_cache()
        return True if out else False

    @staticmethod
    def swap_set(size, path_swap, on_boot):
        if os.path.isfile(path_swap):
            logger.error("{path_swap} already exist".format(path_swap=path_swap))
            return
        # Load swap configuration
        logger.info("Activate {path_swap} auto={on_boot}".format(path_swap=path_swap, on_boot=on_boot))
        # Create a swapfile for Ubuntu at the current directory location
        sp.call(shlex.split('fallocate -l {size}G {path_swap}'.format(size=size, path_swap=path_swap)))
        # Change permissions so that only root can use it
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # Equivalent permission 600 srw-------
        os.chmod(path_swap, stat.S_IREAD | stat.S_IWRITE)
        # Set up the Linux swap area
        sp.call(shlex.split('mkswap {path_swap}'.format(path_swap=path_swap)))
        # Now start using the swapfile
        sp.call(shlex.split('swapon {path_swap}'.format(path_swap=path_swap)))
        # Add not on boot return
        if not on_boot:
            return
        # Find if is already on boot
        swap_string_boot = "{path_swap} none swap sw 0 0".format(path_swap=path_swap)
        fstab = read_fstab()
        if path_swap in fstab:
            logger.warn("{path_swap} Already on boot".format(path_swap=path_swap))
            return
        # Append swap line
        file_object = open(PATH_FSTAB, 'a')
        file_object.write("{swap_string_boot}\n".format(swap_string_boot=swap_string_boot))
        file_object.close()

    @staticmethod
    def swap_deactivate(path_swap):
        # Check if exist swap
        if not os.path.isfile(path_swap):
            logger.error("{path_swap} Does not exist".format(path_swap=path_swap))
            return
        # Disable swap
        sp.call(shlex.split('swapoff {path_swap}'.format(path_swap=path_swap)))
        # Remove swap
        os.remove(path_swap)
        # Run script
        logger.info("Deactivate {path_swap}".format(path_swap=path_swap))
        # Remove if on fstab
        swap_string_boot = "{path_swap} none swap sw 0 0".format(path_swap=path_swap)
        fstab = read_fstab()
        if path_swap not in fstab:
            return
        # Check if is on boot
        logger.info("Removing {path_swap} from fstab".format(path_swap=path_swap))
        with open(PATH_FSTAB, "r") as f:
            lines = f.readlines()
        with open(PATH_FSTAB, "w") as f:
            for line in lines:
                if line.strip("\n") != swap_string_boot:
                    f.write(line)
        # Run script
        logger.info("Removed {path_swap} from boot".format(path_swap=path_swap))

    def get_status(self, mem_total):
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
        ram_shared = status_mem.get('NvMapMemUsed', 0)
        if mem_total:
            # Update shared size
            ram_shared = mem_total if ram_shared == 0 else ram_shared
        # Extract memory info
        ram_total = status_mem.get('MemTotal', 0)
        ram_free = status_mem.get('MemFree', 0)
        # ram_available = status_mem.get('MemAvailable', 0)
        ram_buffer = status_mem.get('Buffers', 0)
        ram_cached = status_mem.get('Cached', 0)
        ram_SReclaimable = status_mem.get('SReclaimable', 0)
        # ram_Shmem = status_mem.get('Shmem', 0)
        total_used_memory = ram_total - ram_free
        cached_memory = ram_cached + ram_SReclaimable  # + ram_Shmem
        # Add fields for RAM
        memory['RAM'] = {
            'tot': ram_total,
            'used': total_used_memory - (ram_buffer + ram_cached),
            'free': ram_free,
            'buffers': ram_buffer,
            'cached': cached_memory,
            'shared': ram_shared,
            'lfb': large_free_bank,  # In 4MB
        }
        # Extract swap numbers
        swap_total = status_mem.get('SwapTotal', 0)
        swap_free = status_mem.get('SwapFree', 0)
        swap_cached = status_mem.get('SwapCached', 0)
        # read all swap and check if are on boot
        swap_table = read_swapon()
        fstab = read_fstab()
        for name in swap_table:
            swap_table[name]['boot'] = name in fstab
        # Add fields for swap
        memory['SWAP'] = {
            'tot': swap_total,
            'used': swap_total - swap_free,
            'cached': swap_cached,
            'table': swap_table,
        }
        # Read EMC status
        if self._is_emc:
            memory['EMC'] = read_emc(self._root_path)
        # Read IRAM if available
        if self._is_iram:
            size = 0
            if os.path.isfile(self._root_path + "/debug/nvmap/iram/size"):
                # Convert from Hex to decimal - Number in bytes
                size = int(cat(self._root_path + "/debug/nvmap/iram/size"), 16) // 1024
            used_total, _ = read_process_table(self._root_path + "/debug/nvmap/iram/clients")
            memory['IRAM'] = {
                'tot': size,
                'used': used_total,
                'lfb': size - used_total,  # TODO To check
            }
        return memory
# EOF
