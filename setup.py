# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
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
from jtop import import_jetson_variables
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open
# Launch command
import subprocess as sp
import shlex
import os
from shutil import copyfile
import sys
import re


def list_scripts():
    JETSONS = import_jetson_variables()
    # Load scripts to install
    scripts = ['scripts/jetson_swap', 'scripts/jetson_release', 'scripts/jetson_config']
    # If jetpack lower than 32 install also jetson_docker
    l4t_release = JETSONS['JETSON_L4T_RELEASE']
    if l4t_release.isdigit():
        if int(l4t_release) < 32:
            scripts += ['scripts/jetson_docker']
    return scripts


def list_services():
    return ["services/{file}".format(file=f) for f in os.listdir("services") if os.path.isfile(os.path.join("services", f))]


if os.getuid() != 0:
    print("\nRequire super user")
    sys.exit(1)


here = os.path.abspath(os.path.dirname(__file__))
project_homepage = "https://github.com/rbonghi/jetson_stats"
documentation_homepage = "https://rbonghi.github.io/jetson_stats"


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


def install_services(copy=False):
    """
    This function install all services in a proper folder and setup the deamons
    """
    print("System prefix {prefix}".format(prefix=sys.prefix))
    # Make jetson stats folder
    root = sys.prefix + "/local/jetson_stats/"
    if not os.path.exists(root):
        os.makedirs(root)
    # Copy all files
    for f_service in list_services():
        folder, _ = os.path.split(__file__)
        path = root + os.path.basename(f_service)
        # remove if exist file
        if os.path.exists(path):
            os.remove(path)
        # Copy or link file
        if copy:
            type_service = "Copying"
            copyfile(folder + "/" + f_service, path)
        else:
            type_service = "Linking"
            os.symlink(folder + "/" + f_service, path)
        # Prompt message
        print("{type} {file} -> {path}".format(type=type_service, file=os.path.basename(f_service), path=path))


"""
Add in installer create group
sudo groupadd jetson_stats

sudo usermod -a -G jetson_stats $USER
"""

class PostInstallCommand(install):
    """Installation mode."""
    def run(self):
        # Run the uninstaller before to copy all scripts
        #sp.call(shlex.split('./scripts/jetson_config --uninstall'))
        # Install services (copying)
        #install_services(copy=True)
        # Run the default installation script
        install.run(self)
        # Run the restart all services before to close the installer
        #sp.call(shlex.split('./scripts/jetson_config --install'))


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        # Run the uninstaller before to copy all scripts
        #sp.call(shlex.split('./scripts/jetson_config --uninstall'))
        # Install services (linking)
        #install_services()
        # Run the default installation script
        develop.run(self)
        # Run the restart all services before to close the installer
        #sp.call(shlex.split('./scripts/jetson_config --install'))


# Configuration setup module
setup(
    name="jetson-stats",
    version=version,
    author="Raffaello Bonghi",
    author_email="raffaello@rnext.it",
    description="Interactive system-monitor and process viewer for all NVIDIA Jetson [Xavier NX, Nano, AGX Xavier, TX1, TX2]",
    license='AGPL-3.0',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=project_homepage,
    download_url=(project_homepage + "/archive/master.zip"),
    project_urls={
        "How To": documentation_homepage,
        "Examples": (project_homepage + "/tree/master/examples"),
        "Bug Reports": (project_homepage + "/issues"),
        "Source": (project_homepage + "/tree/master")
    },
    packages=find_packages(exclude=['examples', 'scripts', 'tests']),  # Required
    # Load jetson_variables
    package_data={"jtop": ["jetson_variables"]},
    # Define research keywords
    keywords=("jetson_stats jtop python system-monitor docker \
               nvidia Jetson XavierNX Nano Xavier TX2 TX1 process viewer"
              ),
    classifiers=["Development Status :: 5 - Production/Stable",
                 # Audiencence and topics
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
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.7",
                 "Programming Language :: Python :: 3.8",
                 "Operating System :: POSIX :: Linux",
                 ],
    # Requisites
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4',
    platforms=["linux", "linux2", "darwin"],
    # Zip safe configuration
    # https://setuptools.readthedocs.io/en/latest/setuptools.html#setting-the-zip-safe-flag
    zip_safe=False,
    # Add jetson_variables in /opt/jetson_stats
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    data_files=[('jetson_stats', list_services())],
    # Install extra scripts
    scripts=list_scripts(),
    cmdclass={'develop': PostDevelopCommand,
              'install': PostInstallCommand},
    # The following provide a command called `jtop`
    entry_points={'console_scripts': ['jtop=jtop.__main__:main']},
)
# EOF
