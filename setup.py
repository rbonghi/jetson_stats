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

# Reference:
# 1. https://packaging.python.org
# 2. https://julien.danjou.info/starting-your-first-python-project/
# 3. https://medium.com/@trstringer/the-easy-and-nice-way-to-do-cli-apps-in-python-5d9964dc950d
# 4. https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
# 5. https://python-packaging.readthedocs.io
# 6. https://github.com/pypa/sampleproject
# 7. https://pypi.org/classifiers/
# 8. https://stackoverflow.com/questions/20288711/post-install-script-with-python-setuptools

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from jtop.service import status_service, remove_service_pipe, uninstall_service, set_service_permission, unset_service_permission, install_service
from jtop.core.jetson_variables import uninstall_variables, install_variables
from jtop.terminal_colors import bcolors
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open
# Launch command
import os
import sys
import re
import logging
import shutil
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


here = os.path.abspath(os.path.dirname(__file__))
project_homepage = "https://github.com/rbonghi/jetson_stats"
documentation_homepage = "https://rnext.it/jetson_stats"

# Load requirements
with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.read().splitlines()

# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Load version package
with open(os.path.join(here, "jtop", "__init__.py")) as fp:
    VERSION = (
        re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S).match(fp.read()).group(1)
    )
# Store version package
version = VERSION


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
    with open('/proc/self/cgroup', 'r') as procfile:
        for line in procfile:
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


def remove_depecated_data():
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
            remove_depecated_data()
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
        folder, _ = os.path.split(__file__)  # This folder
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
    name="jetson-stats",
    version=version,
    author="Raffaello Bonghi",
    author_email="raffaello@rnext.it",
    description="Interactive system-monitor and process viewer for all NVIDIA Jetson [Orin, Xavier, Nano, TX] series",
    license='AGPL-3.0',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=documentation_homepage,
    project_urls={
        'Documentation': documentation_homepage,
        'Funding': 'https://github.com/sponsors/rbonghi',
        'Say Thanks!': 'https://discord.gg/BFbuJNhYzS',
        'Source': project_homepage,
        'Tracker': (project_homepage + "/issues"),
        'Examples': (project_homepage + "/tree/master/examples"),
    },
    packages=find_packages(exclude=['examples', 'scripts', 'tests', 'jtop.tests', 'jtop.tests_gui']),  # Required
    # Define research keywords
    keywords=("jetson_stats jtop python system-monitor docker \
               nvidia Jetson Orin AGXOrin Xavier AGXXavier XavierNX Nano TX1 TX2 process viewer"
              ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        # Audience and topics
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: Software Development :: Debuggers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: User Interfaces",
        "Topic :: System :: Hardware",
        "Topic :: System :: Logging",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Operating System",
        "Topic :: System :: Operating System Kernels",
        "Topic :: System :: Shells",
        "Topic :: System :: Systems Administration",
        "Topic :: Terminals",
        # License
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        # Programming and Operative system
        "Programming Language :: Unix Shell",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux"],
    # Requisites
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    platforms=["linux", "linux2", "darwin"],
    install_requires=requirements,
    # Zip safe configuration
    # https://setuptools.readthedocs.io/en/latest/setuptools.html#setting-the-zip-safe-flag
    zip_safe=False,
    # Add jetson_variables in /opt/jetson_stats
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    data_files=[('jetson_stats', ['services/jtop.service', 'scripts/jtop_env.sh'])],
    # Install extra scripts
    scripts=['scripts/jetson_swap'],
    cmdclass={'develop': JTOPDevelopCommand,
              'install': JTOPInstallCommand},
    # The following provide a command called `jtop`
    entry_points={'console_scripts': [
        'jtop=jtop.__main__:main',
        'jetson_release = jtop.jetson_release:main',
        'jetson_config = jtop.jetson_config:main',
    ]},
)
# EOF
