#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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
# jtop variable
from .core.gpu import get_raw_igpu_devices
from .core.hardware import get_platform_variables
from .core.jetson_variables import get_jetson_raw_output
from .terminal_colors import bcolors


def engine_gui(repository, hardware, version):
    hardware = deepcopy(hardware)
    del hardware['Serial Number']
    module = hardware['Module']
    # Title
    title = "GUI compact engine page missing for [{module}]".format(module=module)
    # Template
    template = "engine-gui.md"
    # body
    body = "Please add a new jtop engine compact page for\n\n"
    body += "### Board\n\n"
    for name, value in hardware.items():
        if not value:
            value = "**MISSING**"
        body += " - {name}: {value}\n".format(name=name, value=value)
    body += "\n### jetson-stats\n\n"
    body += " - Version: " + version + "\n"
    # Print all raw output
    body += "\n<!-- Please attach a screenshot page from jtop Engine page -->\n"
    body += "### Screenshot engine page\n\n"
    body += "Screenshot page from jtop engine page attached"
    # Make url
    url = make_issue(repository, title, body=body, labels="GUI,missing", template=template)
    # message shell
    message = "Module \"{module}\" missing in jtop GUI".format(module=module)
    hyperlink(message, url, "open a Github issue & {attach} a engine page screenshot".format(attach=bcolors.bold('attach')))


def jetpack_missing(repository, hardware, version):
    l4t = hardware['L4T']
    # Title
    title = "jetson-stats not supported for [L4T {l4t}]".format(l4t=l4t)
    # Template
    template = "jetpack-missing.md"
    # Body
    body = "Please update jetson-stats with new jetpack\n\n"
    body += "### Linux for Tegra\n\n"
    body += " - L4T: " + l4t + "\n\n"
    body += "### Jetson-Stats\n\n"
    body += " - Version: " + version + "\n"
    # Make url
    url = make_issue(repository, title, body=body, labels="Jetpack,missing", template=template)
    # message shell
    message = "jetson-stats not supported for [L4T {l4t}]".format(l4t=hardware['L4T'])
    hyperlink(message, url, "open a Github issue")


def get_hardware_log():
    # Print platform
    platform = get_platform_variables()
    body = "--------------------- PLATFORM -------------------------\n"
    for name, value in platform.items():
        body += "{name}: {value}\n".format(name=name, value=value)
    # Print all jetson raw output
    raw_output = get_jetson_raw_output()
    body += "-------------------- JETSON RAW OUTPUT -----------------\n"
    for name, value in raw_output.items():
        body += "------------------\n"
        body += "Path: {name}\n{value}\n".format(name=name, value=value)
    # Print device list
    raw_output = get_raw_igpu_devices()
    body += "\n-------------------- IGPU OUTPUT ---------------------\n"
    for path, value in raw_output.items():
        body += "------------------\n"
        body += "Path: {path}\n{value}\n".format(path=path, value=value)
    return body


def hardware_missing(repository, hardware, version):
    hardware = deepcopy(hardware)
    del hardware['Serial Number']
    # Title
    if 'P-Number' in hardware:
        title = "Hardware Missing: {pnumber}".format(pnumber=hardware.get('P-Number', ''))
    else:
        title = "Hardware Missing".format()
    # Template
    template = "hardware-missing.md"
    # Body
    body = "Please update jetson-stats with this board\n\n"
    body += "### Board\n\n"
    for name, value in hardware.items():
        if not value:
            value = "**MISSING**"
        body += " - {name}: {value}\n".format(name=name, value=value)
    body += "\n### Jetson-Stats\n\n"
    body += " - Version: " + version + "\n"
    # Print all raw output
    body += "\n<!-- Please attach the output from: jtop --error-log -->\n"
    body += "### RAW Data\n\n"
    body += "File from `--error-log` attached"
    # Make url
    url = make_issue(repository, title, body=body, labels="Hardware,missing", template=template)
    # message shell
    message = "jtop not support this hardware"
    hyperlink(message, url, "open a Github issue & {attach} file from: jtop --error-log".format(attach=bcolors.bold('attach')))


def hyperlink(message, url, text):
    # Reference:
    # 1. http://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
    # 2. https://stackoverflow.com/questions/40419276/python-how-to-print-text-to-console-as-hyperlink
    # 3. https://purpleidea.com/blog/2018/06/29/hyperlinks-in-gnome-terminal/
    # 4. https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda
    # 5. https://stackoverflow.com/questions/44078888/clickable-html-links-in-python-3-6-shell
    # Print starting message
    print("[{status}] {message}".format(status=bcolors.warning(), message=message))
    print("  Please, try: {bold}sudo pip3 install -U jetson-stats{reset} or".format(bold=bcolors.BOLD, reset=bcolors.ENDC))
    # Generate hyperlink for shell
    # Check type of shell
    try:
        link = u'\u001b]8;;{url}\u001b\\{text}\u001b]8;;\u001b\\ (press CTRL + Click)'.format(url=url, text=text)
    except UnicodeDecodeError:
        link = "{text}".format(text=text)
    print("  {link}".format(link=link))


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
