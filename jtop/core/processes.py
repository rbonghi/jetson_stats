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

import re
import os
import pwd
from .common import cat
from .hw_detect import is_thor
from .thor_gpu import PROCESS_TYPE_GRAPHIC
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)

MEM_TABLE_REG = re.compile(r'^(?P<user>\w+)\s+(?P<process>[^ ]+)\s+(?P<PID>\d+)\s+(?P<size>\d+)(?P<unit>\w)\n')
TOT_TABLE_REG = re.compile(r'total\s+(?P<size>\d+)(?P<unit>\w)')


def read_process_table(path_table):
    """
    This method list all processes working with GPU

    ========== ============ ======== =============
    user       process      PID      size
    ========== ============ ======== =============
    user       name process number   dictionary
    ========== ============ ======== =============

    :return: list of all processes
    :type spin: list
    """
    table = []
    total = {}
    with open(path_table, "r") as fp:
        for line in fp:
            # Search line
            match = re.search(MEM_TABLE_REG, line)
            if match:
                parsed_line = match.groupdict()
                data = [
                    parsed_line['PID'],
                    parsed_line['user'],
                    parsed_line['process'],
                    int(parsed_line['size']),
                ]
                table += [data]
                continue
            # Find total on table
            match = re.search(TOT_TABLE_REG, line)
            if match:
                parsed_line = match.groupdict()
                total = int(parsed_line['size'])
                continue
    # return total and table
    return total, table


class ProcessService(object):

    def __init__(self):
        self.usernames = {4294967295: "root"}
        # board type
        self._root_path = "/sys/kernel"
        if os.getenv('JTOP_TESTING', False):
            self._root_path = "/fake_sys/kernel"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=self._root_path))
        # nvmap (nvgpu stack, e.g. Orin): per-process GPU memory via debugfs
        self._isJetson = os.path.isfile(self._root_path + "/debug/nvmap/iovmm/maps")
        # nvidia.ko stack (Thor): use NVML for per-process GPU memory
        self._isThor = is_thor()
        if self._isThor:
            from .thor_gpu import nvml_process_table
            self._nvml_process_table = nvml_process_table
        else:
            self._nvml_process_table = None
        # Get the clock ticks per second and page size
        self._clk_tck = os.sysconf('SC_CLK_TCK')
        # self._page_size = os.sysconf('SC_PAGE_SIZE')
        # Initialization memory
        logger.info("Process service started")

    def get_process_info(self, pid, gpu_mem_usage, process_name, uptime, process_type=PROCESS_TYPE_GRAPHIC):
        # Check if exist folder
        if not os.path.isdir(os.path.join('/proc', pid)):
            return []
        # https://man7.org/linux/man-pages/man5/proc.5.html
        stat = cat(os.path.join('/proc', pid, 'stat')).split()
        # Decode uid and find username
        try:
            uid = int(cat(os.path.join('/proc', pid, 'loginuid')))
        except (FileNotFoundError, ValueError, TypeError):
            # This might happen if kernel CONFIG_AUDIT is not set
            # Fall back to avoid crashing on those systems.
            uid = -1
        if uid not in self.usernames:
            try:
                self.usernames[uid] = pwd.getpwuid(uid).pw_name
            except KeyError:
                self.usernames[uid] = "-"
        # Read memory process
        # Extract resident set size (VmRSS) (Second field)
        # VmRSS is the resident set size of the process, which is the portion of the process's memory
        # that is held in RAM and is not swapped out to disk. This is the amount of memory that the process is currently using.
        mem_raw = cat(os.path.join('/proc', pid, 'statm')).split()
        vm_rss = int(mem_raw[1]) * 4
        # CPU percent
        # https://stackoverflow.com/questions/16726779/how-do-i-get-the-total-cpu-usage-of-an-application-from-proc-pid-stat
        utime = float(stat[13])
        stime = float(stat[14])
        starttime = float(stat[21]) / self._clk_tck
        total_time = (utime + stime) / self._clk_tck
        proc_uptime = max(1, uptime - starttime)
        cpu_percent = 100 * (total_time / proc_uptime)

        process = [
            int(pid),               # pid process
            self.usernames[uid],    # username
            "I",                    # GPU name
            process_type,           # type process
            int(stat[17]),          # Priority
            stat[2],                # state
            cpu_percent,            # CPU percent
            vm_rss,                 # MEM process
            gpu_mem_usage,          # GPU mem usage
            process_name,           # Process name
        ]
        return process

    def get_status(self):
        total = {}
        table = []
        with open('/proc/uptime', 'r') as f:
            uptime = float(f.readline().split()[0])
        if self._isThor and self._nvml_process_table is not None:
            # nvidia.ko stack (Thor): nvmap absent, NVML gives compute+graphics
            total, raw = self._nvml_process_table()
            table = [self.get_process_info(prc[0], prc[3], prc[2], uptime, prc[4]) for prc in raw if prc]
        elif self._isJetson:
            # nvgpu stack (Orin): nvmap debugfs is the authoritative source
            total, raw = read_process_table(self._root_path + "/debug/nvmap/iovmm/maps")
            table = [self.get_process_info(prc[0], prc[3], prc[2], uptime) for prc in raw]
        table = [p for p in table if p]
        return total, table
# EOF
