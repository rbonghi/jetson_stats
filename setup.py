#!/usr/bin/env python3
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

"""
Minimal setup.py for backward compatibility and custom install commands.
Main configuration is in pyproject.toml (PEP 517/518/621 compliant).
"""

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
import os
import sys
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


def is_virtualenv():
    # Check if in virtual environment
    return bool(
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )


def is_docker():
    # Check if running in Docker container
    if os.path.exists('/.dockerenv'):
        return True
    # Check cgroup
    path = '/proc/self/cgroup'
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if 'docker' in line or 'buildkit' in line:
                    return True
    return False


def is_superuser():
    return os.getuid() == 0


def pypi_installer(installer, obj, copy):
    """Main installation function for jtop services."""
    # Import here to avoid import errors during build
    try:
        from jtop.service import status_service, remove_service_pipe, uninstall_service, set_service_permission, install_service
        from jtop.core.jetson_variables import uninstall_variables, install_variables
        from jtop.terminal_colors import bcolors
    except ImportError:
        # If imports fail, we're likely in build phase, so skip custom installation
        installer.run(obj)
        return

    log.info("Install status:")
    log.info(f" - [{'X' if is_superuser() else ' '}] super_user")
    log.info(f" - [{'X' if is_virtualenv() else ' '}] virtualenv")
    log.info(f" - [{'X' if is_docker() else ' '}] docker")

    # Run the uninstaller before to copy all scripts
    if not is_virtualenv() and not is_docker():
        if is_superuser():
            # remove service jtop.service
            uninstall_service()
            # Remove service path
            remove_service_pipe()
            # Uninstall variables
            uninstall_variables()
        else:
            log.info("----------------------------------------")
            log.info("Install on your host using superuser permission, like:")
            log.info(bcolors.bold("sudo pip3 install -U jetson-stats"))
            sys.exit(1)
    elif is_docker():
        log.info("Skip uninstall in docker")
    else:
        if is_superuser():
            log.info("Skip uninstall on virtual environment")
        elif not status_service():
            log.info("----------------------------------------")
            log.info("Please, before install in your virtual environment, install jetson-stats on your host with superuser permission, like:")
            log.info(bcolors.bold("sudo pip3 install -U jetson-stats"))
            sys.exit(1)

    # Run the default installation script
    installer.run(obj)

    # Run the restart all services before to close the installer
    if not is_virtualenv() and not is_docker() and is_superuser():
        folder, _ = os.path.split(os.path.realpath(__file__))  # This folder
        # Install variables
        install_variables(folder, copy=copy)
        # Set service permissions
        set_service_permission()
        # Install service (linking only for develop)
        install_service(folder, copy=copy)
    else:
        log.info("Skip install service")


class JTOPInstallCommand(install):
    """Custom installation command for production install."""

    def run(self):
        # Run the custom installer
        pypi_installer(install, self, True)


class JTOPDevelopCommand(develop):
    """Custom installation command for development mode."""

    def run(self):
        # Run the custom installer with linking
        pypi_installer(develop, self, False)


# Minimal setup() call - most configuration is in pyproject.toml
if __name__ == '__main__':
    setup(
        # Custom commands for backward compatibility
        cmdclass={
            'develop': JTOPDevelopCommand,
            'install': JTOPInstallCommand,
        },
        # Include data files that need special installation
        data_files=[('jetson_stats', ['services/jtop.service', 'scripts/jtop_env.sh'])],
    )
