#!/usr/bin/env python3
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

"""Read-only validation for the Jetpack release pull-request checklist."""

import ast
import json
import os
from pathlib import Path
import re
import subprocess


VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'


def git(*args):
    try:
        return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as error:
        raise ValueError('Cannot read PR commits or files; ensure the full base/head history is available.') from error


def version_at(revision):
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('PR base and head must be full commit SHAs.')
    # Read the committed metadata, never import or execute pull-request code.
    message = 'Expected one literal X.Y.Z __version__ in jtop/__init__.py.'
    source = git('show', revision + ':jtop/__init__.py')
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ValueError(message) from error
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              if any(isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets)]
    # Reject additional bindings or deletions rather than approving stale metadata.
    targets = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
               if node.id == '__version__' and isinstance(node.ctx, (ast.Store, ast.Del))]
    if len(values) != 1 or len(targets) != 1 or not isinstance(values[0], ast.Constant):
        raise ValueError(message)
    version = values[0].value
    if not isinstance(version, str) or not re.fullmatch(VERSION, version):
        raise ValueError(message)
    return version


def validate(pr):
    if not pr['title'].startswith('Jetpack Release'):
        return 'Skipped: not a Jetpack release PR.'
    if not re.fullmatch('Jetpack Release ' + VERSION, pr['title']):
        raise ValueError('Expected title `Jetpack Release <VERSION>`, with VERSION in X.Y.Z form.')
    old = version_at(pr['base']['sha'])
    new = version_at(pr['head']['sha'])
    if pr['title'] != 'Jetpack Release ' + new:
        raise ValueError('PR title does not match __version__ in the head commit.')
    major, minor, patch = map(int, old.split('.'))
    expected = '{}.{}.{}'.format(major, minor, patch + 1)
    if new != expected:
        raise ValueError('Expected one patch increment from {} to {}, found {}.'.format(old, expected, new))
    required = 'jtop/core/jetson_variables.py'
    changed = git('diff', '--name-only', '--no-renames', '--diff-filter=M',
                  pr['base']['sha'] + '...' + pr['head']['sha'], '--', required)
    if required not in changed.splitlines():
        raise ValueError(required + ' must be modified (not deleted).')
    return 'Validated: {} -> {}. A CODEOWNER must still give manual approval.'.format(old, new)


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    try:
        message = validate(event['pull_request'])
        status = 0
    except ValueError as error:
        message = 'Failed: ' + str(error)
        status = 1
    print(message)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with Path(summary).open('a', encoding='utf-8') as stream:
            stream.write('## Jetpack release validation\n\n' + message + '\n')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
