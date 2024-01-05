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
# Logging
import logging
# from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)


def read_engine(path):
    # Read status online
    engine = {}
    # Check if access to this file
    if os.access(path + "/clk_enable_count", os.R_OK):
        with open(path + "/clk_enable_count", 'r') as f:
            # Write online engine
            engine['online'] = int(f.read()) == 1
    # Check if access to this file
    if os.access(path + "/clk_rate", os.R_OK):
        with open(path + "/clk_rate", 'r') as f:
            # Write current engine
            engine['cur'] = int(f.read()) // 1000
    # Decode clock rate
    max_value = False
    if os.access(path + "/clk_max_rate", os.R_OK):
        with open(path + "/clk_max_rate", 'r') as f:
            # Write status engine
            value = int(f.read())
            # 18446744073709551615 = FFFF FFFF FFFF FFFF = 2 ^ 16
            if value != 18446744073709551615:
                engine['max'] = value // 1000
                max_value = True
    if os.access(path + "/clk_min_rate", os.R_OK) and max_value:
        with open(path + "/clk_min_rate", 'r') as f:
            # Write status engine
            engine['min'] = int(f.read()) // 1000
    return engine


class EngineService(object):

    ENGINES = ['ape', 'dla', 'pva', 'vic', 'nvjpg', 'nvenc', 'nvdec', 'se.', 'cvnas', 'msenc', 'ofa']

    def __init__(self):
        # Sort list before start
        EngineService.ENGINES.sort()
        self.engines_path = {}
        # List all engines available
        engine_path = "/sys/kernel/debug/clk"
        if os.getenv('JTOP_TESTING', False):
            engine_path = "/fake_sys/kernel/debug/clk"
            logger.warning("Running in JTOP_TESTING folder={root_dir}".format(root_dir=engine_path))
        list_all_engines = [x[0] for x in os.walk(engine_path)]
        # Search all available engines
        for name in EngineService.ENGINES:
            if name.endswith('.'):
                name = name[:-1]
                local_path = "{path}/{name}".format(path=engine_path, name=name)
                if os.path.isdir(local_path):
                    self.engines_path[name.upper()] = [local_path]
            else:
                # https://stackoverflow.com/questions/4843158/how-to-check-if-a-string-is-a-substring-of-items-in-a-list-of-strings
                local_path = "{path}/{name}".format(path=engine_path, name=name)
                # In this search are removed all engines that have a '.' on their name
                # like ape.buffer or nvdec.buf
                matching = [s for s in list_all_engines if local_path in s and '.' not in s]
                # Add in list all engines
                if matching:
                    # Check if name end with a number, if true collect by number
                    # dla0 dla1 ...
                    if os.path.basename(matching[0]).split('_')[0] == "{name}0".format(name=name):
                        logger.info("Special Engine group found: [{name}X]".format(name=name))
                        for num in range(10):
                            name_engine = "{name}{counter}".format(name=name, counter=num)
                            new_match = [match for match in matching if name_engine in match]
                            if new_match:
                                self.engines_path[name_engine.upper()] = sorted(new_match)
                            else:
                                break
                    else:
                        self.engines_path[name.upper()] = sorted(matching)
        # Print all engines found
        if self.engines_path:
            engines_string = ' '.join(name for name in self.engines_path)
            logger.info("Engines found: [{engines}]".format(engines=engines_string))
        else:
            logger.warn("Not engines found!")

    def get_status(self):
        status = {}
        # Read status from all engines
        for engine in self.engines_path:
            status[engine] = {}
            for local_path in self.engines_path[engine]:
                name_engine = os.path.basename(local_path).upper()
                logger.debug("Status [{engine}] in {path}".format(engine=name_engine, path=local_path))
                status[engine][name_engine] = read_engine(local_path)
        return status
# EOF
