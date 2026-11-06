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


from ..gui.pengine import pack_engine_rows
from ..gui.psysfs import _fmt_cap, _is_uncapped


def test_pack_rows_orin_nano():
    # pass_orin on an Orin Nano: empty rows (no PVA/DLA/NVENC) and a 3-entry row
    map_eng = [
        [("APE", "200MHz")], [], [],
        [("NVDEC", "524MHz"), ("NVJPG", "499MHz")],
        [("NVJPG1", "499MHz"), ("SE", "307MHz"), ("VIC", "435MHz")],
        [("OFA", "537MHz")],
    ]
    rows = pack_engine_rows(map_eng, 38)
    assert all(len(row) == 2 for row in rows[:-1])
    assert [name for row in rows for name, _ in row] == ["APE", "NVDEC", "NVJPG", "NVJPG1", "SE", "VIC", "OFA"]


def test_pack_rows_fit_width():
    # Every column must be wide enough for its "name: value" text
    pairs = [[("NVJPG1", "499MHz"), ("SE", "307MHz"), ("VIC", "435MHz")]]
    for width in (26, 38, 60, 118):
        rows = pack_engine_rows(pairs, width)
        cols = len(rows[0])
        assert (width // cols - 1) >= len("NVJPG1") + len("499MHz") + 2


def test_pack_rows_empty():
    assert pack_engine_rows([[], []], 38) == []


MAXN = {"settings": [("GPU", "MAX_FREQ", "-1"), ("EMC", "MAX_FREQ", "2147483647"), ("GPU", "MIN_FREQ", "0")]}
CAPPED = {"settings": [("GPU", "MAX_FREQ", "612000000")]}


def test_uncapped_detection():
    assert _is_uncapped(MAXN, "GPU", "MAX_FREQ")
    assert _is_uncapped(MAXN, "EMC", "MAX_FREQ")
    assert not _is_uncapped(MAXN, "GPU", "MIN_FREQ")
    assert not _is_uncapped(CAPPED, "GPU", "MAX_FREQ")
    assert not _is_uncapped(CAPPED, "EMC", "MAX_FREQ")


def test_fmt_cap():
    assert _fmt_cap(None, True) == "uncapped"
    assert _fmt_cap(None, False) == "n/a"
    assert _fmt_cap(612000000, False) == "612 MHz"


def test_pack_rows_respect_max_rows():
    # AGX Orin has ~12 engines; the box may only have 5 rows: never draw below it
    pairs = [[("E%d" % i, "100MHz")] for i in range(12)]
    rows = pack_engine_rows(pairs, 38, max_rows=5)
    assert len(rows) <= 5
    assert sum(len(r) for r in rows) == 12
# EOF
