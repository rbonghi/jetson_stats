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

from ..core.tegra_parse import DATE, VALS, VALS_ARRAY_RE, VALS_PLAIN_RE

# Real tegrastats line from a Jetson AGX Orin Developer Kit running JetPack 7.2
# (L4T R39.2). GR3D_FREQ carries the utilization *and* the per-GPC frequency array.
TEGRASTATS_ORIN_JP7 = (
    "07-25-2026 09:08:28 RAM 20642/62817MB (lfb 1x2MB) "
    "CPU [23%@2201,10%@2201,4%@2201,14%@2201,30%@2201,18%@2201,10%@2201,10%@2201,33%@2201,7%@2201,5%@2201,27%@2201] "
    "EMC_FREQ 3%@3199 GR3D_FREQ 12%@[1300,1300] NVENC0 off NVDEC0 off NVJPG0 off NVJPG1 off VIC off OFA off "
    "NVDLA0 off NVDLA1 off PVA0_FREQ off APE 174 "
    "cpu@52.968C/52.968C soc2@48.406C/48.406C soc0@49.531C/49.531C gpu@47.625C/47.625C "
    "VDD_GPU_SOC 5139mW/5139mW/5139mW VDD_CPU_CV 3268mW/3268mW/3268mW VIN_SYS_5V0 5500mW/5500mW/5500mW"
)

# Thor reports the per-GPC array without any utilization
TEGRASTATS_THOR = "RAM 4722/7844MB (lfb 1x512kB) EMC_FREQ 2%@1866 GR3D_FREQ @[1000,1000,1000] APE 150"

# Classic Orin / JetPack 6 form: a single utilization and frequency pair
TEGRASTATS_ORIN_JP6 = "RAM 4722/7844MB (lfb 1x512kB) EMC_FREQ 2%@1866 GR3D_FREQ 10%@1300 APE 150"


def test_gr3d_jetpack7_array_with_utilization():
    """JetPack 7 Orin: "GR3D_FREQ 12%@[1300,1300]" carries both load and clock."""
    vals = VALS(DATE(TEGRASTATS_ORIN_JP7))
    assert vals['GR3D'] == {'val': 12, 'frq': 1300000}


def test_gr3d_thor_array_without_utilization():
    """Thor: "GR3D_FREQ @[1000,1000,1000]" has no utilization, only the clock."""
    vals = VALS(TEGRASTATS_THOR)
    assert vals['GR3D'] == {'frq': 1000000}


def test_gr3d_plain_value():
    """Orin / JetPack 6: "GR3D_FREQ 10%@1300" is unchanged."""
    vals = VALS(TEGRASTATS_ORIN_JP6)
    assert vals['GR3D'] == {'val': 10, 'frq': 1300000}


def test_gr3d_zero_utilization_keeps_frequency():
    """A 0% load must not drop the frequency (0 is a valid utilization)."""
    vals = VALS("GR3D_FREQ 0%@[1300,1300]")
    assert vals['GR3D'] == {'val': 0, 'frq': 1300000}


def test_plain_regex_cannot_half_match_the_array_form():
    """VALS_PLAIN_RE must reject "X%@[Y,Y]" outright.

    Without the "(?!%?@\\[)" guard it stops at the "%" and matches "GR3D_FREQ 0",
    which silently drops the frequency. Rejecting it here is what makes the two
    passes in VALS() independent, so reordering them cannot reintroduce the bug.
    """
    # "APE 174" is the control: it still matches, so an empty GR3D result means
    # GR3D was rejected specifically, not that the whole regex stopped working.
    assert VALS_PLAIN_RE.findall("GR3D_FREQ 0%@[1300,1300] APE 174 VIC off") == [('APE', '174')]
    assert VALS_PLAIN_RE.findall("GR3D_FREQ 12%@[1300,1300] APE 174 VIC off") == [('APE', '174')]


def test_array_and_plain_regexes_are_mutually_exclusive():
    """No field on a real JetPack 7 line may be claimed by both regexes."""
    text = DATE(TEGRASTATS_ORIN_JP7)
    array_names = set(name for name, _util, _val in VALS_ARRAY_RE.findall(text))
    plain_names = set(name for name, _val in VALS_PLAIN_RE.findall(text))
    assert array_names == {'GR3D_FREQ'}
    assert not array_names & plain_names


def test_other_values_still_parsed_on_jetpack7():
    """The new GR3D form must not disturb the other fields on the same line."""
    vals = VALS(DATE(TEGRASTATS_ORIN_JP7))
    assert vals['EMC'] == {'val': 3, 'frq': 3199000}
    assert vals['APE'] == {'val': 174}
    # The timestamp is stripped by DATE() and must not leak in as a value
    assert '2026' not in vals
