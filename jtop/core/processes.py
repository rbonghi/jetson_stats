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

import re
import os
import pwd
from .common import cat
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
        # Check if jetson board
        self._isJetson = os.path.isfile(self._root_path + "/debug/nvmap/iovmm/maps")
        # Get the clock ticks per second and page size
        self._clk_tck = os.sysconf('SC_CLK_TCK')
        # self._page_size = os.sysconf('SC_PAGE_SIZE')
        # Initialization memory
        logger.info("Process service started")

    def get_process_info(self, pid, gpu_mem_usage, process_name, uptime):
        # Check if exist folder
        if not os.path.isdir(os.path.join('/proc', pid)):
            return []
        # https://man7.org/linux/man-pages/man5/proc.5.html
        stat = cat(os.path.join('/proc', pid, 'stat')).split()
        # Decode uid and find username
        uid = int(cat(os.path.join('/proc', pid, 'loginuid')))
        if uid not in self.usernames:
            self.usernames[uid] = pwd.getpwuid(uid).pw_name
        # Read memory process
        # Extract resident set size (VmRSS) (Second field)
        # VmRSS is the resident set size of the process, which is the portion of the process's memory
        # that is held in RAM and is not swapped out to disk. This is the amount of memory that the process is currently using.
        mem_raw = cat(os.path.join('/proc', pid, 'statm')).split()
        vm_rss = int(mem_raw[1])
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
            "Graphic",              # type process
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
        # Update table
        if self._isJetson:
            # Use the memory table to measure
            total, table = read_process_table(self._root_path + "/debug/nvmap/iovmm/maps")

            uptime = float(open('/proc/uptime', 'r').readline().split()[0])

            table = [self.get_process_info(prc[0], prc[3], prc[2], uptime) for prc in table]

        return total, table
# EOF
