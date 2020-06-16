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

import logging
import os
import json
import sys
import stat
from grp import getgrnam
import copy
# Create logger for jplotlib
logger = logging.getLogger(__name__)
# Configurations
PIPE_JTOP_USER = 'jetson_stats'
PATH_FOLDER = '/local/jetson_stats'
CONFIG_JTOP = 'config.json'


class Config:

    def __init__(self):
        # Load configuration path
        self.config_file = self.path + '/' + CONFIG_JTOP
        # Load configuration
        self._config = self._load()
        self._last_config = copy.deepcopy(self._config)
        # Initialize configuration
        if not os.path.isfile(self.config_file):
            try:
                gid = getgrnam(PIPE_JTOP_USER).gr_gid
            except KeyError:
                # User does not exist
                raise Exception("Group {jtop_user} does not exist!".format(jtop_user=PIPE_JTOP_USER))
            # Make file
            with open(self.config_file, 'w') as outfile:
                json.dump(self._config, outfile)
            # Change owner
            os.chown(self.config_file, os.getuid(), gid)
            # Set configuration
            # https://www.tutorialspoint.com/python/os_chmod.htm
            os.chmod(self.config_file, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP | stat.S_IROTH)
            logger.info("Initialization configuration file {path}".format(path=self.config_file))

    def set(self, instance, data):
        # Update configuration
        self._config[instance] = data
        # Store configuration
        self._store()

    def get(self, instance, data):
        return self._config.get(instance, data)

    @property
    def path(self):
        return sys.prefix + PATH_FOLDER

    def _load(self):
        config = {}
        # Load configuration if exist
        if not os.path.isfile(self.config_file):
            return config
        logger.info("Load config from {path}".format(path=self.config_file))
        with open(self.config_file) as json_file:
            config = json.load(json_file)
        return config

    def _store(self):
        if self._last_config == self._config:
            return
        logger.info("Store config to {path}".format(path=self.config_file))
        # Write configuration
        with open(self.config_file, 'w') as outfile:
            json.dump(self._config, outfile)
        # Update last configuration
        self._last_config = copy.deepcopy(self._config)
# EOF
