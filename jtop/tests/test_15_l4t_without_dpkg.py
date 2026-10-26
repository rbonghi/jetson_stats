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

import os
from ..core import jetson_variables

NV_TEGRA_RELEASE = '/etc/nv_tegra_release'


def without_nv_tegra_release(monkeypatch):
    isfile = os.path.isfile
    monkeypatch.setattr(jetson_variables.os.path, "isfile", lambda path: False if path == NV_TEGRA_RELEASE else isfile(path))


def test_l4t_is_empty_without_dpkg(monkeypatch, tmp_path):
    # Images without dpkg, like Yocto with meta-tegra, and without /etc/nv_tegra_release (#521)
    without_nv_tegra_release(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert jetson_variables.get_nvidia_l4t() == ''


def test_l4t_is_empty_when_dpkg_fails(monkeypatch, tmp_path):
    without_nv_tegra_release(monkeypatch)
    dpkg = tmp_path / "dpkg"
    dpkg.write_text("#!/bin/sh\nexit 2\n")
    dpkg.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert jetson_variables.get_nvidia_l4t() == ''
# EOF
