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
# Logging
import logging
# Create logger
logger = logging.getLogger(__name__)

MEM_TABLE_REG = re.compile(r'(?P<user>\w+)\s+(?P<process>[^ ]+)\s+(?P<PID>\d+)\s+(?P<size>\d+)(?P<unit>\w)\n')
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
                    {'size': int(parsed_line['size']), 'unit': parsed_line['unit'].lower()}
                ]
                table += [data]
                continue
            # Find total on table
            match = re.search(TOT_TABLE_REG, line)
            if match:
                parsed_line = match.groupdict()
                total = {'size': int(parsed_line['size']), 'unit': parsed_line['unit'].lower()}
                continue
    # return total and table
    return total, table


class ProcessService(object):

    def __init__(self):
        # board type
        self._root_path = "/sys/kernel"
        if os.getenv('JTOP_TESTING', False):
            self._root_path = "/fake_sys/kernel"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=self._root_path))
        # Check if jetson board
        self._isJetson = os.path.isfile(self._root_path + "/debug/nvmap/iovmm/maps")
        # Initialization memory
        logger.info("Process service started")

    def get_status(self):
        total = {}
        table = []
        # Update table
        if self._isJetson:
            # Use the memory table to measure
            total, table = read_process_table(self._root_path + "/debug/nvmap/iovmm/maps")
        return total, table
# EOF
