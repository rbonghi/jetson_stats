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


import logging
import pytest
from ..core import memory
from ..core.memory import MemoryService, is_swap_file

PAGE = 4096


def _write_swap(path, signature=b'SWAPSPACE2'):
    data = bytearray(PAGE * 2)
    data[PAGE - 10:PAGE] = signature
    path.write_bytes(bytes(data))


@pytest.fixture
def calls(monkeypatch):
    """Record the swap commands instead of running them. Set calls.fail to a command name to make it fail."""
    class Recorder(list):
        fail = None

    recorded = Recorder()

    def fake_call(cmd):
        recorded.append(cmd)
        if cmd[0] == recorded.fail:
            return 1
        if cmd[0] == 'fallocate':
            open(cmd[-1], 'wb').close()
        return 0

    monkeypatch.setattr(memory.sp, 'call', fake_call)
    monkeypatch.setattr(memory.os, 'sysconf', lambda name: PAGE)
    monkeypatch.setattr(memory, 'read_swapon', lambda: {})
    return recorded


def test_is_swap_file(tmp_path):
    swap = tmp_path / 'swfile'
    _write_swap(swap)
    assert is_swap_file(str(swap), PAGE)
    _write_swap(swap, b'SWAP-SPACE')
    assert is_swap_file(str(swap), PAGE)
    other = tmp_path / 'data'
    other.write_bytes(b'x' * PAGE * 2)
    assert not is_swap_file(str(other), PAGE)
    assert not is_swap_file(str(tmp_path / 'missing'), PAGE)


def test_new_swap_is_created(tmp_path, calls):
    path = str(tmp_path / 'swfile')
    MemoryService.swap_set(2, path, False)
    assert calls == [['fallocate', '-l', '2G', path], ['mkswap', path], ['swapon', path]]
    assert (tmp_path / 'swfile').exists()


def test_inactive_leftover_swap_is_recreated(tmp_path, calls):
    # Issue #430: a swap file left after a reboot made "create" fail forever
    path = str(tmp_path / 'swfile')
    _write_swap(tmp_path / 'swfile')
    MemoryService.swap_set(4, path, False)
    new = path + '.new'
    assert calls == [['fallocate', '-l', '4G', new], ['mkswap', new], ['swapon', path]]
    assert (tmp_path / 'swfile').exists()
    assert not (tmp_path / 'swfile.new').exists()


@pytest.mark.parametrize('failing', ['fallocate', 'mkswap'])
def test_failed_recreation_keeps_old_swap(tmp_path, calls, failing, caplog):
    path = str(tmp_path / 'swfile')
    _write_swap(tmp_path / 'swfile')
    before = (tmp_path / 'swfile').read_bytes()
    calls.fail = failing
    with caplog.at_level(logging.ERROR):
        MemoryService.swap_set(4, path, False)
    assert (tmp_path / 'swfile').read_bytes() == before
    assert not (tmp_path / 'swfile.new').exists()
    assert 'swapon' not in [cmd[0] for cmd in calls]
    assert 'Cannot create swap' in caplog.text


@pytest.mark.parametrize('failing', ['fallocate', 'mkswap'])
def test_failed_creation_does_not_raise(tmp_path, calls, failing):
    path = str(tmp_path / 'swfile')
    calls.fail = failing
    MemoryService.swap_set(2, path, False)
    assert not (tmp_path / 'swfile').exists()
    assert 'swapon' not in [cmd[0] for cmd in calls]


def test_active_swap_is_not_touched(tmp_path, calls, monkeypatch, caplog):
    path = tmp_path / 'swfile'
    _write_swap(path)
    monkeypatch.setattr(memory, 'read_swapon', lambda: {str(path): {}})
    with caplog.at_level(logging.ERROR):
        MemoryService.swap_set(2, str(path), False)
    assert calls == []
    assert path.exists()
    assert 'already an active swap' in caplog.text


def test_active_swap_through_symlink_is_not_touched(tmp_path, calls, monkeypatch, caplog):
    real = tmp_path / 'swfile'
    _write_swap(real)
    alias = tmp_path / 'alias'
    alias.symlink_to(real)
    monkeypatch.setattr(memory, 'read_swapon', lambda: {str(real): {}})
    with caplog.at_level(logging.ERROR):
        MemoryService.swap_set(2, str(alias), False)
    assert calls == []
    assert 'already an active swap' in caplog.text


def test_other_file_is_not_overwritten(tmp_path, calls, caplog):
    path = tmp_path / 'swfile'
    path.write_bytes(b'important data' * 1000)
    with caplog.at_level(logging.ERROR):
        MemoryService.swap_set(2, str(path), False)
    assert calls == []
    assert path.read_bytes() == b'important data' * 1000
    assert 'not a swap file' in caplog.text
