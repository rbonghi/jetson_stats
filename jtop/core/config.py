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
import copy
# Create logger
logger = logging.getLogger(__name__)
# Configurations
JTOP_USER = 'jetson_stats'


class Config:

    def __init__(self):
        if not os.path.isdir(self.path):
            # Make folder directory
            os.makedirs(self.path)
        # Load configuration path
        self.config_file = self.path + '/config.json'
        # Load configuration
        self._config = self._load()
        self._last_config = copy.deepcopy(self._config)

    def set(self, instance, data):
        # Update configuration
        self._config[instance] = data
        # Store configuration
        if self._last_config != self._config:
            self._store()
            # Update last configuration
            self._last_config = copy.deepcopy(self._config)

    def get(self, instance, data):
        return self._config.get(instance, data)

    @property
    def path(self):
        path = sys.prefix
        if hasattr(sys, 'real_prefix'):
            path = sys.real_prefix
        if hasattr(sys, 'base_prefix'):
            path = sys.base_prefix
        # Return directory folder
        return path + '/local/jetson_stats'

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
        logger.info("Store config to {path}".format(path=self.config_file))
        # Write configuration
        with open(self.config_file, 'w') as outfile:
            json.dump(self._config, outfile, sort_keys=True, indent=4)

    def clear(self):
        self._config = {}
        self._last_config = {}
        if os.path.isfile(self.config_file):
            logger.info("Clear config in {path}".format(path=self.config_file))
            # Remove configuration file
            os.remove(self.config_file)
            return True
        return False
# EOF
