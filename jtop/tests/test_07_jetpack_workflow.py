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

"""Exercise the release check without any Jetson hardware fixtures."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / '.github/scripts/check_jetpack_release.py'


def run_check(tmp_path, title, base=None, head=None, cwd=None):
    event = tmp_path / 'event.json'
    event.write_text(json.dumps({'pull_request': {
        'title': title, 'base': {'sha': base}, 'head': {'sha': head},
    }}), encoding='utf-8')
    summary = tmp_path / 'summary.md'
    env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_STEP_SUMMARY=str(summary))
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=cwd or tmp_path, env=env,
        capture_output=True, text=True,
    )
    return result, summary.read_text(encoding='utf-8') if summary.exists() else ''


def git(repo, *args, **kwargs):
    env = dict(os.environ, GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
               GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return subprocess.run(['git', *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True, **kwargs).stdout.strip()


def make_commit(repo, version, variables='# Jetpack mappings\n', parent=None, source=None):
    # Plumbing creates real objects only in this temporary repo, with no staging,
    # checkout, hooks, or commits in the project's working tree.
    if source is None:
        source = '__version__ = "{}"\n'.format(version)
    version_blob = git(repo, 'hash-object', '-w', '--stdin', input=source)
    entries = '100644 blob {}\t__init__.py\n'.format(version_blob)
    if variables is not None:
        variables_blob = git(repo, 'hash-object', '-w', '--stdin', input=variables)
        core = git(repo, 'mktree', input='100644 blob {}\tjetson_variables.py\n'.format(variables_blob))
        entries += '040000 tree {}\tcore\n'.format(core)
    jtop = git(repo, 'mktree', input=entries)
    tree = git(repo, 'mktree', input='040000 tree {}\tjtop\n'.format(jtop))
    parents = ['-p', parent] if parent else []
    return git(repo, '-c', 'commit.gpgsign=false', 'commit-tree', tree, *parents, input='Test snapshot\n')


def release_repo(tmp_path, version='7.2.3', changed=True):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '--bare', '-q')
    base = make_commit(repo, '7.2.2')
    variables = '# New Jetpack mapping\n' if changed else '# Jetpack mappings\n'
    head = make_commit(repo, version, variables, parent=base)
    return repo, base, head


def test_valid_release_uses_distinct_base_and_head_commits(tmp_path):
    repo, base, head = release_repo(tmp_path)
    assert base != head
    # A bare repo has neither a checkout nor an origin/master ref to accidentally read.
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Validated' in summary
    assert '7.2.2 -> 7.2.3' in summary
    assert 'CODEOWNER' in summary
    assert 'manual' in summary


@pytest.mark.parametrize('title', [
    'Jetpack Release', 'Jetpack Release 7.2', 'Jetpack Release 7.2.3 trailing',
    'Jetpack Release v7.2.3', 'Jetpack Release 07.2.3',
    'Jetpack Release 7.2.3\n', 'Jetpack Release ７.２.３',
])
def test_malformed_release_title_fails(tmp_path, title):
    repo, base, head = release_repo(tmp_path)
    result, summary = run_check(tmp_path, title, base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'Failed' in summary
    assert 'Jetpack Release <VERSION>' in summary


def test_title_must_match_head_version(tmp_path):
    repo, base, head = release_repo(tmp_path)
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.4', base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'title does not match' in summary


@pytest.mark.parametrize('version', ['7.2.2', '7.2.1', '7.2.4', '7.3.0', '8.2.3'])
def test_release_requires_exactly_one_patch_increment(tmp_path, version):
    repo, base, head = release_repo(tmp_path, version=version)
    result, summary = run_check(tmp_path, 'Jetpack Release ' + version, base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'patch increment' in summary
    assert '7.2.3' in summary


@pytest.mark.parametrize('deleted', [False, True])
def test_release_requires_modified_jetson_variables(tmp_path, deleted):
    repo, base, head = release_repo(tmp_path, changed=False)
    if deleted:
        head = make_commit(repo, '7.2.3', variables=None, parent=base)
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'jtop/core/jetson_variables.py' in summary
    assert 'modified' in summary


@pytest.mark.parametrize('changes_mappings', [False, True])
def test_mapping_check_uses_pr_changes_when_base_has_advanced(tmp_path, changes_mappings):
    repo, ancestor, _head = release_repo(tmp_path)
    updated = '# Mapping also added on the base branch\n'
    base = make_commit(repo, '7.2.2', updated, parent=ancestor)
    variables = updated if changes_mappings else '# Jetpack mappings\n'
    head = make_commit(repo, '7.2.3', variables, parent=ancestor)

    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert result.returncode == (0 if changes_mappings else 1), result.stdout + result.stderr
    assert ('Validated' if changes_mappings else 'must be modified') in summary


@pytest.mark.parametrize('source', [
    '# no version\n', '__version__ = 723\n', '__version__ = "07.2.3"\n',
    '__version__ = "7.2.3"\n__version__ = "7.2.4"\n',
    '__version__ = "7.2.3', '__version__ = str("7.2.3")\n',
])
def test_invalid_version_metadata_fails_with_summary(tmp_path, source):
    repo, base, _head = release_repo(tmp_path)
    head = make_commit(repo, '7.2.3', '# New Jetpack mapping\n', parent=base, source=source)
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'Failed' in summary
    assert '__version__' in summary
    assert 'Traceback' not in result.stderr


@pytest.mark.parametrize('revision', ['0' * 40, '--help', None])
@pytest.mark.parametrize('side', ['base', 'head'])
def test_unavailable_commits_fail_with_summary(tmp_path, revision, side):
    repo, base, head = release_repo(tmp_path)
    if side == 'base':
        base = revision
    else:
        head = revision
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert 'Failed' in summary
    assert 'commit' in summary
    assert 'Traceback' not in result.stderr


def test_version_source_is_not_executed(tmp_path):
    repo, base, _head = release_repo(tmp_path)
    marker = tmp_path / 'imported'
    source = 'from pathlib import Path\nPath({!r}).touch()\n__version__ = "7.2.3"\n'.format(str(marker))
    head = make_commit(repo, '7.2.3', '# New Jetpack mapping\n', parent=base, source=source)
    result, summary = run_check(tmp_path, 'Jetpack Release 7.2.3', base, head, repo)
    assert not marker.exists()
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Validated' in summary


def test_workflow_only_runs_the_read_only_validator():
    workflow = (ROOT / '.github/workflows/auto-merge-jetpack.yml').read_text(encoding='utf-8')
    assert re.search(r'^  pull_request:\s*$', workflow, re.MULTILINE)
    assert re.search(r'^      - edited\s*$', workflow, re.MULTILINE)
    assert re.search(r'^permissions:\n  contents: read\s*$', workflow, re.MULTILINE)
    assert 'fetch-depth: 0' in workflow
    assert 'persist-credentials: false' in workflow
    # A single entrypoint keeps non-release PRs from falling through to later checks.
    assert re.findall(r'^        run: (.+)$', workflow, re.MULTILINE) == [
        'python3 .github/scripts/check_jetpack_release.py',
    ]
    actions = re.findall(r'^        uses: (.+)$', workflow, re.MULTILINE)
    assert len(actions) == 1
    assert actions[0].startswith('actions/checkout@')
    assert '${{' not in workflow
    assert 'pull_request_target' not in workflow
    assert not re.search(r'^\s+[\w-]+: write\s*$', workflow, re.MULTILINE)


@pytest.mark.parametrize('prefix,status', [('Fix docs ', 0), ('Jetpack Release ', 1)])
@pytest.mark.parametrize('payload', ['$(touch {marker})', '`touch {marker}`', '\"; touch {marker}; #'])
def test_shell_syntax_in_title_is_never_executed(tmp_path, prefix, status, payload):
    marker = tmp_path / 'injected'
    title = prefix + payload.format(marker=marker)
    result, summary = run_check(tmp_path, title)
    assert not marker.exists()
    assert result.returncode == status, result.stdout + result.stderr
    assert ('Skipped' if status == 0 else 'Failed') in summary


def test_normal_pr_is_skipped_without_accessing_git(tmp_path):
    # The actual title from the failing PR; there is no Git repo or valid SHA here.
    result, summary = run_check(tmp_path, 'Fix jtop_env.sh Python detection')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Skipped' in result.stdout
    assert 'Skipped' in summary
    assert 'not a Jetpack release' in summary
