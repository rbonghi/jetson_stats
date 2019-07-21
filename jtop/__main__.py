#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
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

"""
    Graphic reference:
    - http://urwid.org/examples/index.html
    - https://npyscreen.readthedocs.io/
    - https://github.com/chubin/cheat.sh
    - https://stackoverflow.com/questions/6840420/python-rewrite-multiple-lines-in-the-console
    - https://docs.python.org/3.3/howto/curses.html#attributes-and-color
    - http://toilers.mines.edu/~jrosenth/101python/code/curses_plot/
"""
import re
import os
import sys
import argparse
# Logging
import logging
# control command line
import curses
# Tegrastats objext reader
from .jtop import jtop
# GUI jtop interface
from .gui import JTOPGUI, ALL, GPU, CTRL, INFO

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def set_xterm_title(title):
    '''
    Set XTerm title using escape sequences.
    By default, sets as 'Python' and the version number.
    '''
    # Make sure this terminal supports the OSC code (\33]),
    # though not necessarily that it supports setting the title.
    # If this check causes compatibility issues, you can add
    # items to the tuple, or remove the check entirely.
    if os.environ.get('TERM') in ('xterm',
                                  'xterm-color',
                                  'xterm-256color',
                                  'linux',
                                  'screen',
                                  'screen-256color',
                                  'screen-bce',
                                  ):
        sys.stdout.write('\33]0;' + title + '\a')
        sys.stdout.flush()


def get_version():
    # Load version package
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "__init__.py")) as fp:
        VERSION = (
            re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S).match(fp.read()).group(1)
        )
    return VERSION


def main():
    # Add arg parser
    parser = argparse.ArgumentParser(description='jtop is system monitoring utility and runs in the terminal')
    parser.add_argument('-r', dest="refresh", help='refresh interval', type=int, default='500')
    parser.add_argument('--debug', dest="debug", help='Run with debug logger', action="store_true", default=False)
    parser.add_argument('--page', dest="page", help='Open fix page', type=int, default=1)
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=get_version()))
    # Parse arguments
    args = parser.parse_args()
    # Set logging level
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, filename='jtop.log', filemode='w',
                            format='%(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig()
    # Title script
    # Reference: https://stackoverflow.com/questions/25872409/set-gnome-terminal-window-title-in-python
    set_xterm_title("jtop")
    # Open tegrastats reader and run the curses wrapper
    try:
        with jtop(interval=args.refresh) as jetson:
            try:
                # Call the curses wrapper
                curses.wrapper(JTOPGUI, args.refresh, jetson, [ALL, GPU, CTRL, INFO], init_page=args.page)
            except KeyboardInterrupt:
                # Catch keyboard interrupt and close
                logger.info("Closed with CTRL-C")
    except jtop.JtopException as e:
        # Print error and close
        print(e)


if __name__ == "__main__":
    main()
# EOF
