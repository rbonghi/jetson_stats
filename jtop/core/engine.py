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

import os


class Engine(object):
    def __init__(self, name):
        self.name = name
        self._status = False
        self._freq = None
        self._min_freq = None
        self._max_freq = None

    @property
    def frequency(self):
        return self._freq

    def get_constrains(self):
        return (self._min_freq, self._max_freq)

    @property
    def status(self):
        return self._status

    def update(self, data):
        if not data:
            return
        # Decode frequency
        if 'rate' in data:
            self._freq = data['rate']
        if 'val' in data:
            self._freq = data['val']
        if 'frq' in data:
            self._freq = data['frq']
        if 'current_freq' in data:
            self._freq = data['current_freq']
        # Decode constrains
        if 'min_freq' in data:
            self._min_freq = data['min_freq']
        if 'max_freq' in data:
            self._max_freq = data['max_freq']
        # Set status engine ON
        self._status = True
        if 'status' in data:
            self._status = data['status']

    def __repr__(self):
        if self._freq is not None:
            return "Engine[{freq}Mhz]".format(freq=self._freq)
        status_string = 'ON' if self._status else 'OFF'
        return "Engine[{status}]".format(status=status_string)


class Engines(object):

    def __init__(self):
        self._engines = {'NVDEC': Engine('NVDEC'), 'NVENC': Engine('NVENC')}

    def _update(self, engines):
        for name in engines:
            # Multiple engines
            if name in ['DLA', 'PVA']:
                for idx in engines[name]:
                    dla_name = "{name}{idx}".format(name=name, idx=idx)
                    if dla_name not in self._engines:
                        self._engines[dla_name] = {value: Engine("{dla}_{value}".format(dla=dla_name, value=value.upper())) for value in engines[name][idx]}
                    for value in engines[name][idx]:
                        self._engines[dla_name][value].update(engines[name][idx][value])
                continue
            # single engine
            if name not in self._engines:
                eng = Engine(name)
                self._engines[name] = eng
            self._engines[name].update(engines[name])

    def items(self):
        return self._engines.items()

    def get(self, name, value=None):
        if name in self._engines:
            return self._engines[name]
        else:
            return value

    def __getitem__(self, name):
        return self._engines[name]

    def __iter__(self):
        return iter(self._engines)

    def __next__(self):
        return next(self._engines)

    def __len__(self):
        return len(self._engines)

    def __repr__(self):
        return str(self._engines)


def read_engine(path):
    # Read status enable
    engine = {}
    # Check if access to this file
    if os.access(path + "/clk_enable_count", os.R_OK):
        with open(path + "/clk_enable_count", 'r') as f:
            # Write status engine
            engine['status'] = int(f.read()) == 1
    # Check if access to this file
    if os.access(path + "/clk_rate", os.R_OK):
        with open(path + "/clk_rate", 'r') as f:
            # Write status engine
            engine['rate'] = int(f.read()) // 1000000
    return engine
# EOF
