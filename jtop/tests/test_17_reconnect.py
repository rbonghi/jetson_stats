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
import time
import threading
import multiprocessing
from .. import service
from ..jtop import jtop, VERSION_RE
from ..core.common import get_var


class FakeController(object):
    """Reply to the configuration request of a jtop client like jtop.service does."""

    def __init__(self, init):
        self._init = init

    def put(self, message):
        pass

    def get(self, timeout=None):
        return {'init': self._init}

    def empty(self):
        return True


def serve(address):
    """A minimal jtop.service: only what jtop.start() needs."""
    service.JTOP_PIPE = address
    controller = FakeController({
        'version': get_var(VERSION_RE),
        'board': {'hardware': {}},
        'interval': 1.0,
        'memory': '',
        'fan': {},
        'jc': False,
    })
    data = {'gpu': {}, 'mem': {}, 'fan': {}}
    event = threading.Event()
    event.set()
    service.JtopManager.register('get_queue', callable=lambda: controller)
    service.JtopManager.register('sync_data', callable=lambda: data)
    service.JtopManager.register('sync_event', callable=lambda: event)
    service.JtopManager().get_server().serve_forever()


def start_service(address):
    # spawn: the jtop client threads are already running in this process
    process = multiprocessing.get_context('spawn').Process(target=serve, args=(address, ), daemon=True)
    process.start()
    deadline = time.time() + 10.0
    while not os.path.exists(address):
        assert time.time() < deadline, "fake jtop.service did not start"
        time.sleep(0.05)
    return process


def stop_service(process, address):
    process.kill()
    process.join()
    os.remove(address)


def test_connect_after_service_restart(monkeypatch, tmp_path):
    address = str(tmp_path / "jtop.sock")
    monkeypatch.setattr(service, "JTOP_PIPE", address)
    process = start_service(address)
    first = jtop()
    first.start()
    # jtop.service restarts while the first client still exists, like a client
    # that lost the connection and is kept alive by the error it stored (#601)
    stop_service(process, address)
    process = start_service(address)
    try:
        second = jtop()
        # Raised BrokenPipeError: the new proxies reused the connection to the old service
        second.start()
        assert second.ok()
        second.close()
    finally:
        first.close()
        stop_service(process, address)
# EOF
