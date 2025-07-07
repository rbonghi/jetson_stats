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

# Always prefer setuptools over distutils
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from jtop.service import status_service, remove_service_pipe, uninstall_service, set_service_permission, unset_service_permission, install_service
from jtop.core.jetson_variables import uninstall_variables, install_variables
from jtop.terminal_colors import bcolors
# Launch command
import os
import sys
import shutil

def is_virtualenv():
    # https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
    if os.path.exists(os.path.join(sys.prefix, 'conda-meta')):
        # Conda virtual environments
        return True
    if hasattr(sys, 'real_prefix'):
        return True
    if hasattr(sys, 'base_prefix'):
        return sys.prefix != sys.base_prefix
    return False


def is_docker():
    # https://gist.github.com/anantkamath/623ce7f5432680749e087cf8cfba9b69
    # https://stackoverflow.com/questions/68816329/how-to-get-docker-container-id-from-within-the-container-with-cgroup-v2
    def check_mountinfo():
        with open('/proc/self/mountinfo', 'r') as file:
            line = file.readline().strip()
            while line:
                if '/docker/containers/' in line or '/docker/volumes/buildx_buildkit_builder' in line:
                    return True
                line = file.readline().strip()
        return False
    # Check on cgroup
    with open('/proc/self/cgroup', 'r') as procfile:
        for line in procfile:
            # if is the new cgroup v2 check on mountinfo
            if line.startswith("0::/"):
                return check_mountinfo()
            fields = line.strip().split('/')
            if 'docker' in fields or 'buildkit' in fields:
                return True
    return False


def is_superuser():
    return os.getuid() == 0


def remove_data(file_name):
    # Remove old pipes if exists
    if os.path.isfile(file_name):
        print("Remove {file} file".format(file=file_name))
        os.remove(file_name)
    elif os.path.isdir(file_name):
        print("Remove {file} folder".format(file=file_name))
        shutil.rmtree(file_name)


def remove_deprecated_data():
    """
    This function uninstall the service
    """
    # If exist, remove old services names if they exists
    uninstall_service('jetson_performance.service')
    uninstall_service('jetson_stats_boot.service')
    uninstall_service('jetson_stats.service')
    # Remove old variable definitions
    uninstall_variables('jetson_env.sh')
    # Remove old permission and group
    unset_service_permission('jetson_stats')
    # Remove old script if they exists
    remove_data("/usr/local/bin/jetson-docker")
    remove_data("/usr/local/bin/jetson-release")
    # Remove old folders
    remove_data("/usr/local/jetson_stats")
    remove_data("/opt/jetson_stats")
    remove_data("/etc/jetson-swap")
    remove_data("/etc/jetson_easy")


def pypi_installer(installer, obj, copy):
    print("Install status:")
    print(" - [{status}] super_user".format(status="X" if is_superuser() else " "))
    print(" - [{status}] virtualenv".format(status="X" if is_virtualenv() else " "))
    print(" - [{status}] docker".format(status="X" if is_docker() else " "))
    # Run the uninstaller before to copy all scripts
    if not is_virtualenv() and not is_docker():
        if is_superuser():
            # Remove all deprecated data
            # - This function should do nothing
            remove_deprecated_data()
            # remove service jtop.service
            uninstall_service()
            # Remove service path
            remove_service_pipe()
            # Uninstall variables
            uninstall_variables()
        else:
            print("----------------------------------------")
            print("Install on your host using superuser permission, like:")
            print(bcolors.bold("sudo pip3 install -U jetson-stats"))
            sys.exit(1)
    elif is_docker():
        print("Skip uninstall in docker")
    else:
        if is_superuser():
            print("Skip uninstall on virtual environment")
        elif not status_service():
            print("----------------------------------------")
            print("Please, before install in your virtual environment, install jetson-stats on your host with superuser permission, like:")
            print(bcolors.bold("sudo pip3 install -U jetson-stats"))
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
        print("Skip install service")


class JTOPInstallCommand(install):
    """Installation mode."""

    def run(self):
        # Run the uninstaller before to copy all scripts
        pypi_installer(install, self, True)


class JTOPDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        # Run the uninstaller before to copy all scripts
        # Install services (linking)
        pypi_installer(develop, self, False)


# Configuration setup module
setup(
    # Install extra scripts
    cmdclass={'develop': JTOPDevelopCommand,
              'install': JTOPInstallCommand},
)
# EOF
