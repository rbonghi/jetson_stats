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

import errno
import io
import os
import pytest
from ..core import processes


@pytest.mark.parametrize("filename", ['stat', 'loginuid', 'statm'])
@pytest.mark.parametrize("error", [errno.ESRCH, errno.ENOENT])
def test_get_status_skips_exited_process(monkeypatch, filename, error):
    monkeypatch.setattr(processes, "is_thor", lambda: False)
    service = processes.ProcessService()
    service._isJetson = True
    monkeypatch.setattr(processes.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(processes, "open", lambda path, mode: io.StringIO('100'), raising=False)
    monkeypatch.setattr(processes, "read_process_table", lambda path: (16, [
        ['123', 'root', 'exited', 8], ['456', 'root', 'running', 8],
    ]))
    stat = ['0'] * 22
    stat[2] = 'R'
    values = {'stat': ' '.join(stat), 'loginuid': '4294967295', 'statm': '100 10'}
    exited = False

    def read_process_file(path):
        nonlocal exited
        pid, name = path.split('/')[-2:]
        if pid == '123':
            exited = exited or name == filename
            if exited:
                raise OSError(error, os.strerror(error))
        return values[name]

    monkeypatch.setattr(processes, "cat", read_process_file)
    try:
        status = service.get_status()
    except OSError as exc:
        status = exc
    # A process can exit after the directory check, during any of the proc reads (#525).
    assert status == (16, [[456, 'root', 'I', 'Graphic', 0, 'R', 0.0, 40, 8, 'running']])
# EOF
