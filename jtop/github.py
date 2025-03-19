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
    # Prepare hardware information, marking missing values
    hardware = {k: v or "**MISSING**" for k, v in deepcopy(hardware).items() if k != 'Serial Number'}
    module = hardware['Module']

    # Create issue title and template
    title = f"GUI compact engine page missing for [{module}]"
    template = "engine-gui.md"

    # Create issue body
    body = (
        "Please add a new jtop engine compact page for\n\n### Board\n\n" +
        "\n".join(
            [f" - {name}: {value}" for name, value in hardware.items()]
        )
    )
    body += f"\n\n### jetson-stats\n\n - Version: {version}\n"
    body += "\n<!-- Please attach a screenshot page from jtop Engine page -->\n### Screenshot engine page\n\nScreenshot page from jtop engine page attached"

    # Generate issue URL
    url = make_issue(repository, title, body=body, labels="GUI,missing", template=template)

    # Print message with hyperlink
    message = f"Module \"{module}\" missing in jtop GUI"
    hyperlink(message, url, f"open a Github issue & {bcolors.bold('attach')} a engine page screenshot")


def jetpack_missing(repository, hardware, version):
    # Prepare L4T information
    l4t = hardware['L4T']

    # Create issue title and template
    title = f"jetson-stats not supported for [L4T {l4t}]"
    template = "jetpack-missing.md"

    # Create issue body
    body = f"Please update jetson-stats with new jetpack\n\n### Linux for Tegra\n\n - L4T: {l4t}\n\n### Jetson-Stats\n\n - Version: {version}\n"

    # Generate issue URL
    url = make_issue(repository, title, body=body, labels="Jetpack,missing", template=template)

    # Print message with hyperlink
    message = f"jetson-stats not supported for [L4T {l4t}]"
    hyperlink(message, url, "open a Github issue")


def get_hardware_log():
    # Collect platform and raw output information
    platform = get_platform_variables()
    raw_output = get_jetson_raw_output()
    igpu_output = get_raw_igpu_devices()

    # Create log body
    body = (
        "--------------------- PLATFORM -------------------------\n" +
        "\n".join([f"{name}: {value}" for name, value in platform.items()])
    )
    body += "\n-------------------- JETSON RAW OUTPUT -----------------\n"
    body += "\n".join([f"------------------\nPath: {name}\n{value}" for name, value in raw_output.items()])
    body += "\n-------------------- IGPU OUTPUT ---------------------\n"
    body += "\n".join([f"------------------\nPath: {path}\n{value}" for path, value in igpu_output.items()])

    return body


def hardware_missing(repository, hardware, version):
    # Prepare hardware information, marking missing values
    hardware = {k: v or "**MISSING**" for k, v in deepcopy(hardware).items() if k != 'Serial Number'}

    # Create issue title and template
    title = f"Hardware Missing: {hardware.get('P-Number', '')}" if 'P-Number' in hardware else "Hardware Missing"
    template = "hardware-missing.md"

    # Create issue body
    body = (
        "Please update jetson-stats with this board\n\n### Board\n\n" +
        "\n".join(
            [f" - {name}: {value}" for name, value in hardware.items()]
        )
    )
    body += f"\n\n### Jetson-Stats\n\n - Version: {version}\n"
    body += "\n<!-- Please attach the output from: jtop --error-log -->\n### RAW Data\n\nFile from `--error-log` attached"

    # Generate issue URL
    url = make_issue(repository, title, body=body, labels="Hardware,missing", template=template)

    # Print message with hyperlink
    message = "jtop not support this hardware"
    hyperlink(message, url, f"open a Github issue & {bcolors.bold('attach')} file from: jtop --error-log")


def hyperlink(message, url, text):
    # Print starting message
    print(f"[{bcolors.warning()}] {message}")
    print(f"  Please, try: {bcolors.BOLD}sudo pip3 install -U jetson-stats{bcolors.ENDC} or")

    # Generate hyperlink for shell
    try:
        link = f'\u001b]8;;{url}\u001b\\{text}\u001b]8;;\u001b\\ (press CTRL + Click)'
    except UnicodeDecodeError:
        link = f"{text}"
    print(f"  {link}")


def make_issue(repository, title, body="", labels="", template=""):
    # Encode title and body for URL
    title = title.replace(" ", "+").replace("[", "%5B").replace("]", "%5D")
    url = f"{repository}/new?title={title}"
    if labels:
        url += f"&labels={labels}"
    if template:
        url += f"&template={template}"
    if body:
        body = body.replace(" ", "+").replace("#", "%23").replace("\n", "%0A").replace("*", "%2A")
        url += f"&body={body}"
    return url
# EOF
