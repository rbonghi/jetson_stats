#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020-2023 Raffaello Bonghi.
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

# Shell information
# os.environ['SHELL']

from copy import deepcopy


def jetpack_missing(repository, hardware, version):
    l4t = hardware['L4T']
    # Title
    title = "jetson-stats not supported for [L4T {l4t}]".format(l4t=l4t)
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
    return hyperlink(url, "open an issue on Github")


def hardware_missing(repository, hardware, version):
    hardware = deepcopy(hardware)
    del hardware['Serial Number']
    # Title
    title = "hardware missing"
    # Template
    template = "model-missing.md"
    # Body
    body = "Please update jetson-stats with this board\n\n"
    body += "**Board**\n"
    for name, value in hardware.items():
        if not value:
            value = "**MISSING**"
        body += " - {name}: {value}\n".format(name=name, value=value)
    body += "**Jetson-Stats**\n"
    body += " - Version: " + version + "\n"
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
        return u"\u001b]8;;{url}\u001b\\{text}\u001b]8;;\u001b\\ (press CTRL + Click)".format(url=url, text=text)
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
