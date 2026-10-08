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

from ..core import nvpmodel
from ..core.exceptions import JtopException

MAXN = {'name': 'MAXN', 'id': 0}
LOW_POWER = {'name': '120W', 'id': 1}


def make_service(monkeypatch, replies):
    """Build an NVPModelService whose `nvpmodel -q` calls return, or raise, ``replies`` in order."""
    monkeypatch.setattr(nvpmodel, "nvpmodel_decode", lambda: (MAXN, ['MAXN', '120W'], [True, True]))
    replies = iter(replies)

    def fake_query():
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(nvpmodel, "nvpmodel_query", fake_query)
    return nvpmodel.NVPModelService(jetson_clocks=None)


def test_get_status_keeps_last_mode_when_query_fails(monkeypatch):
    # Under full load `nvpmodel -q` can exceed its timeout. get_status() runs on every stats
    # tick, so raising here would stop the timer thread and the service with it.
    service = make_service(monkeypatch, [MAXN, JtopException("nvpmodel command unavailable"), LOW_POWER])
    assert service.get_status()['model'] == MAXN
    # The next successful query updates the mode again
    assert service.get_status()['model'] == LOW_POWER


def test_startup_query_failure_disables_nvpmodel(monkeypatch):
    # A failing nvpmodel command at startup marks nvpmodel as not available instead of
    # stopping the service from starting.
    service = make_service(monkeypatch, [JtopException("nvpmodel command unavailable")])
    assert not service.exists()
# EOF
