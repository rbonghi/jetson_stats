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


import pytest

from ..core import jetson_variables, nvpmodel
from ..core.exceptions import JtopException
from ..core.jetson_variables import NVIDIA_JETPACK, MODULE_NAME_TABLE
from ..jtop import jtop, MIN_INTERVAL


def fake_command(lines=None, error=None):
    """Stand-in for core.command.Command returning ``lines`` or raising ``error``."""
    class FakeCommand:
        CommandException = jetson_variables.Command.CommandException

        def __init__(self, command, **kwargs):
            self.command = command

        def __call__(self, timeout=None):
            if error is not None:
                raise error
            return list(lines or [])
    return FakeCommand


# --- #941 / #598 / #864: missing JetPack and module entries -------------------

def test_l4t_35_7_0_is_jetpack_5_1_8():
    assert NVIDIA_JETPACK["35.7.0"] == "5.1.8"


@pytest.mark.parametrize("pnumber", ["p3701-0001", "p3701-0008"])
def test_agx_orin_modules_are_known(pnumber):
    assert "AGX Orin" in MODULE_NAME_TABLE[pnumber]


# --- #567: nvpmodel without a configured power mode -------------------------

def test_nvpmodel_query_without_mode_raises(monkeypatch):
    monkeypatch.setattr(nvpmodel, "Command", fake_command(["NVPM WARN: power mode is not set!"]))
    with pytest.raises(JtopException):
        nvpmodel.nvpmodel_query()


def test_nvpmodel_query_with_mode(monkeypatch):
    monkeypatch.setattr(nvpmodel, "Command", fake_command(["NV Power Mode: MAXN_SUPER", "2"]))
    assert nvpmodel.nvpmodel_query() == {"name": "MAXN_SUPER", "id": 2}


# --- #521: no dpkg on the system ---------------------------------------------

def test_check_dpkg_without_dpkg(monkeypatch):
    monkeypatch.setattr(jetson_variables, "Command", fake_command(error=FileNotFoundError("dpkg")))
    assert jetson_variables.check_dpkg_nvidia_l4t_core() is False


def test_check_dpkg_failure_is_logged(monkeypatch, caplog):
    # dpkg exists but exits non-zero: no crash, but the failure is reported
    error = jetson_variables.Command.CommandException("Error process:", 2)
    monkeypatch.setattr(jetson_variables, "Command", fake_command(error=error))
    with caplog.at_level("WARNING"):
        assert jetson_variables.check_dpkg_nvidia_l4t_core() is False
    assert "dpkg --get-selections failed" in caplog.text


def test_get_nvidia_l4t_without_dpkg_or_release_file(monkeypatch):
    monkeypatch.setattr(jetson_variables, "Command", fake_command(error=FileNotFoundError("dpkg")))
    real_isfile = jetson_variables.os.path.isfile
    monkeypatch.setattr(jetson_variables.os.path, "isfile",
                        lambda path: False if path == "/etc/nv_tegra_release" else real_isfile(path))
    assert jetson_variables.get_nvidia_l4t() == ""


# --- #482: lower bound on the refresh interval -------------------------------

@pytest.mark.parametrize("requested, expected", [(0.1, MIN_INTERVAL), (0.0, MIN_INTERVAL), (0.5, 0.5), (2.0, 2.0)])
def test_interval_lower_bound(requested, expected):
    assert jtop(interval=requested)._interval == expected
# EOF
