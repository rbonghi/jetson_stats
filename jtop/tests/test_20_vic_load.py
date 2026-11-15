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


from .. import service
from ..service import add_vic_load
from ..gui.lib.linear_gauge import running_label


def test_vic_load_added_to_existing_entry(monkeypatch):
    # Issue #590: Orin exposes the VIC actmon load like Thor
    monkeypatch.setattr(service, '_read_vic_actmon_load', lambda: 64.8)
    engines = {'VIC': {'VIC': {'online': True, 'cur': 115200}}, 'NVDEC': {'NVDEC': {'online': False, 'cur': 0}}}
    add_vic_load(engines)
    assert engines['VIC']['VIC'] == {'online': True, 'cur': 115200, 'load': 64.8}
    assert 'load' not in engines['NVDEC']['NVDEC']


def test_vic_load_without_actmon_node(monkeypatch):
    monkeypatch.setattr(service, '_read_vic_actmon_load', lambda: None)
    engines = {'VIC': {'VIC': {'online': True, 'cur': 115200}}}
    add_vic_load(engines)
    assert engines['VIC']['VIC'] == {'online': True, 'cur': 115200}


def test_vic_load_never_creates_an_entry(monkeypatch):
    monkeypatch.setattr(service, '_read_vic_actmon_load', lambda: 10.0)
    for engines in ({}, {'VIC': {}}, {'VIC': None}, {'NVENC': {'NVENC': {'online': True, 'cur': 1}}}):
        before = repr(engines)
        add_vic_load(engines)
        assert repr(engines) == before


def test_running_label():
    assert running_label({'online': True, 'cur': 1}) == " RUNNING "
    assert running_label({'online': True, 'cur': 1, 'load': 64.8}) == "  65% "
    assert running_label({'online': True, 'cur': 1, 'load': 100.0}) == " 100% "
    assert running_label({'online': True, 'cur': 1, 'load': None}) == " RUNNING "
