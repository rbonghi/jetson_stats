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


def test_orin_drops_absent_and_duplicate_engines(monkeypatch):
    # JetPack 7.2 Orin Nano: the provider lists the whole tegra234 engine set.
    # Absent engines (no frequency) and engines EngineService already shows are dropped.
    monkeypatch.setattr(service, "is_thor", lambda: False)
    monkeypatch.setattr(service, "_read_vic_actmon_load", lambda: None)
    data = {"engines": {
        "APE": {"APE": {"online": False, "cur": 200000}},
        "NVDEC": {"NVDEC": {"online": False, "cur": 524800}},
        "NVJPG": {"NVJPG": {"online": False, "cur": 499200}, "NVJPG1": {"online": False, "cur": 499200}},
        "SE": {"SE": {"online": False, "cur": 307200}},
    }}
    absent = {"online": False, "cur": None, "min": None, "max": None}
    engines = {
        "DLA0": dict(absent), "DLA1": dict(absent), "PVA": dict(absent), "NVENC": dict(absent),
        "NVDEC": {"online": False, "cur": 524800, "min": 0, "max": None},
        "NVJPG0": {"online": False, "cur": 499200, "min": 0, "max": None},
        "NVJPG1": {"online": False, "cur": 499200, "min": 0, "max": None},
        "SE": {"online": False, "cur": 307200, "min": 0, "max": None},
        "APE": {"online": False, "cur": 200000, "min": 0, "max": None},
    }
    JtopServer.apply_jetsonpower_overlay(FakeServer(engines), data)
    assert "JP" not in data["engines"]
    for name in ("DLA0", "DLA1", "PVA", "NVENC", "NVJPG0"):
        assert name not in data["flat"]


def test_orin_keeps_extra_engine(monkeypatch):
    # An engine EngineService does not expose, with a real frequency, stays in JP.
    monkeypatch.setattr(service, "is_thor", lambda: False)
    monkeypatch.setattr(service, "_read_vic_actmon_load", lambda: None)
    data = {"engines": {"NVDEC": {"NVDEC": {"online": False, "cur": 524800}}}}
    engines = {
        "NVDEC": {"online": False, "cur": 524800, "min": 0, "max": None},
        "PVA": {"online": True, "cur": 115200, "min": 0, "max": 1152000},
    }
    JtopServer.apply_jetsonpower_overlay(FakeServer(engines), data)
    assert list(data["engines"]["JP"]) == ["PVA"]


def test_thor_keeps_all_engines(monkeypatch):
    # Thor is untouched: JP is its only engine source, absent entries included.
    monkeypatch.setattr(service, "is_thor", lambda: True)
    monkeypatch.setattr(service, "_read_vic_actmon_load", lambda: None)
    data = {"engines": {}}
    engines = {
        "NVDEC0": {"online": True, "cur": 800000, "min": 0, "max": 1000000},
        "DLA0": {"online": False, "cur": None, "min": None, "max": None},
    }
    JtopServer.apply_jetsonpower_overlay(FakeServer(engines), data)
    assert set(data["engines"]["JP"]) == {"NVDEC0", "DLA0"}
# EOF
