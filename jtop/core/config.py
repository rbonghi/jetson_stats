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

import logging
import os
import json
import sys
import copy
# Create logger
logger = logging.getLogger(__name__)
JTOP_DATA_FOLDER = 'local/jtop'


def make_config_service(data_folder=JTOP_DATA_FOLDER):
    path = get_config_service(data_folder)
    if not os.path.isdir(path):
        logger.info("Build service folder in {path}".format(path=path))
        # Make folder directory
        os.makedirs(path)


def get_config_service(data_folder=JTOP_DATA_FOLDER):
    path = sys.prefix
    if hasattr(sys, 'real_prefix'):
        path = sys.real_prefix
    if hasattr(sys, 'base_prefix'):
        path = sys.base_prefix
    # Return directory folder
    return "{path}/{data_folder}".format(path=path, data_folder=data_folder)


class Config:

    def __init__(self):
        # Build folder if doesn't exists
        make_config_service()
        # Load configuration path
        self.config_file = self.path + '/config.json'
        # Load configuration
        self._config = self._load()
        self._last_config = copy.deepcopy(self._config)

    def set(self, instance, default=None):
        # Update configuration
        self._config[instance] = default
        # Store configuration
        if self._last_config != self._config:
            self._store()
            # Update last configuration
            self._last_config = copy.deepcopy(self._config)

    def get(self, instance, default=None):
        return self._config.get(instance, default)

    @property
    def path(self):
        return get_config_service()

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

    def items(self):
        return self._config.items()

    def keys(self):
        return self._config.keys()

    def values(self):
        return self._config.values()

    def __contains__(self, key):
        return key in self._config

    def __repr__(self):
        return repr(self._config)

    def __str__(self):
        return str(self._config)
# EOF
