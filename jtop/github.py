#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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

# Shell infromation
# os.environ['SHELL']


def jetpack_missing(repository, version):
    l4t = os.environ["JETSON_L4T"]
    # Title
    title = "Jetpack missing [L4T {l4t}]".format(l4t=l4t)
    # Template
    template = "jetpack-missing.md"
    # Body
    body = "Please update jetson-stats with new jetpack\n\n"
    body += "**Linux for Tegra**\n"
    body += " - L4T: " + l4t + "\n\n"
    body += "**Jetson-Stats**\n"
    body += " - Version: " + version + "\n"
    # Make url
    url = make_issue(repository, title, body=body, labels="missing", template=template)
    # message shell
    return hyperlink(url, title)


def board_missing(repository, version):
    board = os.environ["JETSON_BOARD"]
    # Title
    title = "Board missing {board}".format(board=board)
    # Template
    template = "board-missing.md"
    # Body
    body = "Please update jetson-stats with this board\n\n"
    body += "**Board**\n"
    body += " - Board(s): " + board + "\n"
    body += " - Boardis: " + os.environ["JETSON_BOARDIDS"] + "\n"
    body += " - SOC: " + os.environ["JETSON_SOC"] + "\n"
    body += " - ID: " + os.environ["JETSON_CHIP_ID"] + "\n"
    body += " - Code Name: " + os.environ["JETSON_CODENAME"] + "\n\n"
    body += "**Jetpack**\n"
    body += " - Jetpack: " + os.environ["JETSON_JETPACK"] + "\n"
    body += " - L4T: " + os.environ["JETSON_L4T"] + "\n\n"
    body += "**Jetson-Stats**\n"
    body += " - version: " + version + "\n"
    # Make url
    url = make_issue(repository, title, body=body, labels="missing", template=template)
    # message shell
    return hyperlink(url, title)


def hyperlink(url, text, hyperlink=True):
    # Reference:
    # 1. http://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
    # 2. https://stackoverflow.com/questions/40419276/python-how-to-print-text-to-console-as-hyperlink
    # 3. https://purpleidea.com/blog/2018/06/29/hyperlinks-in-gnome-terminal/
    # 4. https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda
    # 5. https://stackoverflow.com/questions/44078888/clickable-html-links-in-python-3-6-shell
    # Check type of shell
    if hyperlink:
        return u"\u001b]8;;{url}\u001b\\{text}\u001b]8;;\u001b\\ (CTRL + Click to open this issue)".format(url=url, text=text)
    else:
        return "{text} ({url})".format(url=url, text=text)


def make_issue(repository, title, body="", labels="", template=""):
    # Reference
    # https://help.github.com/en/enterprise/2.17/user/github/managing-your-work-on-github/about-automation-for-issues-and-pull-requests-with-query-parameters
    # https://krypted.com/utilities/html-encoding-reference/
    title = title.replace(" ", "+").replace("[", "%5B").replace("]", "%5D")
    url = "{repository}/new?title={title}".format(repository=repository, title=title)
    if labels:
        url += "&labels=" + labels
    if template:
        url += "&template=" + template
    if body:
        body = body.replace(" ", "+").replace("#", "%23").replace("\n", "%0A").replace("*", "%2A")
        url += "&body=" + body
    return url
# EOF
