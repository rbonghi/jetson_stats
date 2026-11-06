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


from ..core.memory import large_free_blocks

PAGE_4K = 4096


def zones(*nr_free_lists):
    return {0: [{"nr_free": list(nr_free)} for nr_free in nr_free_lists]}


def test_stock_kernel_last_column_is_4mb():
    # MAX_PAGE_ORDER 10: 11 columns, the last one is 4MB (same as the old behaviour)
    assert large_free_blocks(zones([9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 3]), PAGE_4K) == 3


def test_r39_kernel_counts_4mb_and_bigger_orders():
    # L4T R39: 14 columns (up to 32MB); 8MB/16MB/32MB blocks hold 2/4/8 x 4MB
    mem = zones([0] * 10 + [5, 1, 0, 2])
    assert large_free_blocks(mem, PAGE_4K) == 5 + 1 * 2 + 0 * 4 + 2 * 8


def test_r39_real_sample_is_not_zero():
    # Real Orin Nano R39 sample: the last (32MB) column is 0 in both zones
    mem = zones([1977, 779, 700, 366, 131, 73, 50, 14, 4, 6, 5, 0, 0, 0],
                [1568, 837, 343, 84, 55, 21, 30, 14, 2, 0, 0, 0, 0, 0])
    assert large_free_blocks(mem, PAGE_4K) == 5


def test_small_kernel_falls_back_to_biggest_order():
    # Fewer columns than the 4MB order: report the biggest available order
    assert large_free_blocks(zones([1, 2, 3]), PAGE_4K) == 3


def test_64k_pages_use_order_6():
    # 64KB pages: 4MB is order 6 (64 pages), not order 0
    mem = zones([100, 100, 100, 100, 100, 100, 3, 1])
    assert large_free_blocks(mem, 64 * 1024) == 3 + 1 * 2
# EOF
