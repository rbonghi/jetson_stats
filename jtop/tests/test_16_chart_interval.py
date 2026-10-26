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
from ..gui.lib import chart
from ..gui.lib.chart import Chart


class FakeJetson(object):

    def __init__(self, interval):
        self.interval = interval

    def attach(self, observer):
        pass


class FakeScreen(object):

    def __init__(self):
        self.text = []

    def addstr(self, y, x, string, *args):
        self.text.append(string)

    def addch(self, y, x, char, *args):
        pass

    def hline(self, y, x, char, n):
        pass


@pytest.fixture
def no_terminal(monkeypatch):
    # Draw without a terminal: skip colors and define the line characters set by initscr()
    monkeypatch.setattr(chart.curses, "init_pair", lambda *args: None)
    monkeypatch.setattr(chart.curses, "color_pair", lambda n: 0)
    for name in ["ACS_LLCORNER", "ACS_LTEE", "ACS_HLINE"]:
        monkeypatch.setattr(chart.curses, name, ord('+'), raising=False)
    yield
    Chart.reset_color_counter()


def draw_chart(interval):
    chart_test = Chart(FakeJetson(interval), "GPU", lambda jetson, name: {'value': [50]})
    chart_test.update(None)
    stdscr = FakeScreen()
    chart_test.draw(stdscr, [1, 79], [1, 20])
    return [text for text in stdscr.text if isinstance(text, str) and text.startswith('-')]


@pytest.mark.parametrize("interval, labels", [
    (1.0, ['-2s', '-4s', '-6s', '-8s']),
    (0.5, ['-2s', '-4s', '-6s', '-8s']),
    # Longer than the 2s tik (#527): one tick on each value
    (2.5, ['-2.5s', '-5s', '-7.5s']),
    (3.0, ['-3s', '-6s']),
    # Longer than the 10s chart time: a single value, no time labels
    (20.0, []),
])
def test_chart_draws_with_long_interval(no_terminal, interval, labels):
    assert draw_chart(interval) == labels
# EOF
