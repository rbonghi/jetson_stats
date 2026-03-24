#!/usr/bin/env python3
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

"""
Minimal setup.py for backward compatibility and custom install commands.
Main configuration is in pyproject.toml (PEP 517/518/621 compliant).
"""

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.build_py import build_py
import os
import sys
import shutil
import subprocess as sp_mod
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


def is_virtualenv():
    # Check if in virtual environment
    has_real_prefix = hasattr(sys, 'real_prefix')
    has_base_prefix = (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    return bool(has_real_prefix or has_base_prefix)


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


def _run_service_install(source_folder):
    """Install jtop system service and config files using only stdlib.

    This is used by the build_py override so it works inside isolated
    PEP 517 build environments where jtop's runtime dependencies
    (smbus2, distro, …) are *not* available.
    """
    service_src = os.path.join(source_folder, 'services', 'jtop.service')
    service_dst = '/etc/systemd/system/jtop.service'
    env_src = os.path.join(source_folder, 'scripts', 'jtop_env.sh')
    env_dst = '/etc/profile.d/jtop_env.sh'
    pipe_path = '/run/jtop.sock'

    # --- Uninstall previous service ---
    if os.path.isfile(service_dst) or os.path.islink(service_dst):
        sp_mod.call(['systemctl', 'stop', 'jtop.service'])
        sp_mod.call(['systemctl', 'disable', 'jtop.service'])
        os.remove(service_dst)
        sp_mod.call(['systemctl', 'daemon-reload'])
    if os.path.isdir(pipe_path):
        shutil.rmtree(pipe_path)
    elif os.path.exists(pipe_path):
        os.remove(pipe_path)
    if os.path.isfile(env_dst):
        os.remove(env_dst)

    # --- Install service file ---
    if os.path.isfile(service_src):
        shutil.copy2(service_src, service_dst)
        log.info("Installed %s -> %s", service_src, service_dst)
        sp_mod.call(['systemctl', 'daemon-reload'])
        sp_mod.call(['systemctl', 'enable', 'jtop.service'])
        # start may fail during wheel-build (jtop binary not yet installed)
        sp_mod.call(['systemctl', 'start', 'jtop.service'])

    # --- Install env script ---
    if os.path.isfile(env_src):
        shutil.copy2(env_src, env_dst)
        log.info("Installed %s -> %s", env_src, env_dst)

    # --- Set permissions ---
    user = os.environ.get('SUDO_USER', '') or 'root'
    sp_mod.call(['groupadd', 'jtop'])
    sp_mod.call(['usermod', '-a', '-G', 'jtop', user])


class JTOPBuildPy(build_py):
    """Extend build_py to install system service during PEP 517 builds.

    Modern pip always builds a wheel and then installs it, so the legacy
    ``install`` cmdclass never fires.  By hooking into ``build_py`` (which
    *is* executed during ``bdist_wheel``), we can install the systemd
    service, env script, and group as part of ``sudo pip install``.
    """

    def run(self):
        build_py.run(self)
        if is_superuser() and not is_virtualenv() and not is_docker():
            folder = os.path.dirname(os.path.realpath(__file__))
            log.info("Installing jtop system service …")
            _run_service_install(folder)


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
            'build_py': JTOPBuildPy,
            'develop': JTOPDevelopCommand,
            'install': JTOPInstallCommand,
        },
        # Include data files that need special installation
        data_files=[('jetson_stats', ['services/jtop.service', 'scripts/jtop_env.sh'])],
    )
