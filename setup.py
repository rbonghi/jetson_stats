# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
from os import path
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open
# Launch command
import subprocess as sp
import shlex
import os
import sys


if os.getuid() != 0:
    print("\nRequire super user")
    sys.exit(1)


here = path.abspath(path.dirname(__file__))
project_homepage = "https://github.com/rbonghi/jetson_stats"


# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


class PostInstallCommand(install):
    """Installation mode."""
    def run(self):
        # Run the uninstaller before to copy all scripts
        sp.call(shlex.split('./scripts/install.sh -s --uninstall'))
        # Run the default installation script
        install.run(self)
        # Run the restart all services before to close the installer
        sp.call(shlex.split('./scripts/install.sh -s -no-pip'))


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        # Run the uninstaller before to copy all scripts
        sp.call(shlex.split('./scripts/install.sh -s --uninstall'))
        # Run the default installation script
        develop.run(self)
        # Run the restart all services before to close the installer
        sp.call(shlex.split('./scripts/install.sh -s -no-pip'))


# Configuration setup module
setup(
    name="jetson-stats",
    version="1.7.0",
    author="Raffaello Bonghi",
    author_email="raffaello@rnext.it",
    description="Interactive system-monitor and process viewer for all NVIDIA Jetson [Nano, AGX Xavier, TX1, TX2]",
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=project_homepage,
    download_url=(project_homepage + "/archive/master.zip"),
    project_urls={
        "How To": (project_homepage + "/tree/master/docs"),
        "Examples": (project_homepage + "/tree/master/examples"),
        "Bug Reports": (project_homepage + "/issues"),
        "Source": (project_homepage + "/tree/master")
    },
    packages=find_packages(exclude=['examples', 'scripts', 'tests']),  # Required
    keywords=("jetson_stats jtop python system-monitor docker \
               nvidia Jetson Nano Xavier TX2 TX1 process viewer"
              ),
    classifiers=["Development Status :: 4 - Beta",
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
                 "License :: OSI Approved :: MIT License",
                 # Programming and Operative system
                 "Programming Language :: Python :: 2",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.7",
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
    data_files=[('/opt/jetson_stats', ['scripts/jetson_variables', 'scripts/jetson_performance.sh']),
                ('/etc/profile.d', ['scripts/jetson_env.sh']),
                ('/etc/systemd/system', ['scripts/jetson_performance.service']),
                ],
    # Install extra scripts
    scripts=['scripts/jetson-docker',
             'scripts/jetson-swap',
             'scripts/jetson-release',
             ],
    cmdclass={'develop': PostDevelopCommand,
              'install': PostInstallCommand},
    # The following provide a command called `jtop`
    entry_points={'console_scripts': ['jtop=jtop.__main__:main']},
)
# EOF
