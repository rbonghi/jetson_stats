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
from ..service import JtopServer


class FakeJetsonPower:
    """Minimal stand-in for JetsonPowerProvider: only what apply_jetsonpower_overlay touches."""

    def __init__(self, engines):
        self._engines = engines

    def available(self):
        return True

    def read_power(self):
        return {}

    def read_thermal(self):
        return {}

    def read_fans(self):
        return {}

    def read_engines(self):
        return self._engines


class FakeServer:
    """Carries only the attribute apply_jetsonpower_overlay reads from the server."""

    def __init__(self, engines):
        self.jetsonpower = FakeJetsonPower(engines)


def run_overlay(monkeypatch, engines, vic_load):
    monkeypatch.setattr(service, "_read_vic_actmon_load", lambda: vic_load)
    data = {}
    JtopServer.apply_jetsonpower_overlay(FakeServer(engines), data)
    return data


def test_vic_load_without_vic_engine(monkeypatch):
    # Orin: the actmon node exists but the provider does not list a VIC engine.
    # The load must only go to the flat dict; no schema-less engine entry.
    engines = {"NVDEC": {"online": True, "cur": 524800, "min": 0, "max": None}}
    data = run_overlay(monkeypatch, engines, 12.5)
    assert data["flat"]["VIC_LOAD"] == 12.5
    assert "VIC" not in data["engines"]["JP"]
    for engine in data["engines"]["JP"].values():
        assert "online" in engine and "cur" in engine


def test_vic_load_with_vic_engine(monkeypatch):
    # Thor: the provider lists VIC, so the entry gains the load alongside its schema.
    engines = {"VIC": {"online": True, "cur": 729600, "min": 0, "max": 1036800}}
    data = run_overlay(monkeypatch, engines, 12.5)
    assert data["flat"]["VIC_LOAD"] == 12.5
    vic = data["engines"]["JP"]["VIC"]
    assert vic["load"] == 12.5
    assert vic["online"] is True and vic["cur"] == 729600


def test_no_vic_load(monkeypatch):
    # No actmon node (non-Thor kernels): nothing VIC-related is added.
    engines = {"NVDEC": {"online": True, "cur": 524800, "min": 0, "max": None}}
    data = run_overlay(monkeypatch, engines, None)
    assert "VIC_LOAD" not in data["flat"]
    assert "VIC" not in data["engines"]["JP"]
# EOF
