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
"""
JTOP is a complete controller of all systems in your NVIDIA Jetson
 * Tegrastats
 * NVP Model
 * Fan
 * Status board (i.g. Model version, Jetpack, ... )

You can initialize the jtop node like a file i.g.

.. code-block:: python

    with jtop() as jetson:
        stat = jetson.stats

Or manually start up with the basic function `open/close`

.. code-block:: python

    jetson = jtop()
    jetson.open()
    stat = jetson.stats
    jetson.close()

Jtop include all informations about your board. The default properties are:
 * stats
 * nvpmodel
 * fan
 * board
 * disk

Follow the next attributes to know in detail how it works.
"""
import re
import os
import sys
# Logging
import logging

from .core import NVPmodel
from .core import Tegrastats
from .core import Fan
from .core import JetsonClocks
from .core import Swap
from .core import cpuinfo
from .core import nvjpg
from .core import (import_os_variables,
                   get_uptime,
                   status_disk,
                   get_local_interfaces,
                   StatusObserver)

# Create logger for jplotlib
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)


def import_jetson_variables():
    JTOP_FOLDER, _ = os.path.split(__file__)
    return import_os_variables(JTOP_FOLDER + "/jetson_variables", "JETSON_")


def get_version():
    """
    Show the version of this package

    :return: Version number
    :rtype: string
    """
    # Load version package
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "__init__.py")) as fp:
        VERSION = VERSION_RE.match(fp.read()).group(1)
    return VERSION


class jtop(StatusObserver):
    """
    with this class you can control your jtop statistics and manage your board

    :param interval: Interval update tegrastats and other statistic function
    :type interval: int
    """
    class JtopException(Exception):
        """ Jtop general exception """
        pass

    def __init__(self, interval=500):
        # Load configuration file path
        config_file = sys.prefix + "/local/jetson_stats"
        # Version package
        self.version = get_version()
        # Initialize observer
        self._observers = set()
        self._started = False
        # Load all Jetson variables
        logger.info("Load jetson variables from script")
        for k, v in import_jetson_variables().items():
            logger.debug("New Enviroment variable {}:{}".format(k, v))
            os.environ[k] = v
        # Initialize jetson_clocks controller
        try:
            self.jc = JetsonClocks(config_file)
        except JetsonClocks.JCException as e:
            raise jtop.JtopException(e)
        # Initialize NVP model
        try:
            self.nvp = NVPmodel(jetson_clocks=self.jc)
        except NVPmodel.NVPmodelException:
            self.nvp = None
        # Find all fans availables
        self.qfan = None
        LIST_FANS = [('/sys/kernel/debug/tegra_fan/', False), ('/sys/devices/pwm-fan/', True)]
        for path, temp_control in LIST_FANS:
            try:
                self.qfan = Fan(path, self.jc, config_file, temp_control=temp_control)
                logger.info("Fan {} loaded!".format(path))
                break
            except Fan.FanException:
                logger.info("Fan {} not loaded".format(path))
        # Start process tegrastats
        tegrastats_file = ""
        for f_tegra in ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']:
            if os.path.isfile(f_tegra):
                logger.info("Load tegrastats {}".format(f_tegra))
                tegrastats_file = f_tegra
                break
        if not tegrastats_file:
            raise jtop.JtopException("Tegrastats is not availabe on this board")
        try:
            # Initialize Swap controller
            self.swap = Swap()
        except Swap.SwapException as e:
            raise jtop.JtopException(e)
        # Initialize Tegrastats controller
        self._stats = {}
        self.tegrastats = Tegrastats(tegrastats_file, interval)

    @property
    def userid(self):
        """ Linux User ID """
        return os.getuid()

    @property
    def architecture(self):
        """ CPU architecture """
        return cpuinfo.info()

    @property
    def fan(self):
        """ Fan object controller """
        return self.qfan

    @property
    def disk(self):
        """ Disk status properties """
        return status_disk()

    @property
    def jetson_clocks(self):
        """ JetsonClock controller """
        return self.jc

    @property
    def uptime(self):
        """ Up time """
        return get_uptime()

    @property
    def nvpmodel(self):
        """
        NVPmodel is the controller of your NVP model.
        From this object you read and set the status of your NVIDIA Jetson.
        """
        return self.nvp

    @property
    def nvjpg(self):
        return nvjpg()

    @property
    def local_interfaces(self):
        """ Local interfaces information """
        return get_local_interfaces()

    @property
    def board(self):
        """
        Detailed information of your board, with a complete list of:
         * Jetpack
         * L4T
         * Serial Number
         * ...
        """
        info = {"Machine": os.environ["JETSON_MACHINE"],
                "Jetpack": os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]"}
        board = {"TYPE": os.environ["JETSON_TYPE"],
                 "CODENAME": os.environ["JETSON_CODENAME"],
                 "SOC": os.environ["JETSON_SOC"],
                 "CHIP_ID": os.environ["JETSON_CHIP_ID"],
                 "BOARDIDS": os.environ["JETSON_BOARDIDS"],
                 "MODULE": os.environ["JETSON_MODULE"],
                 "BOARD": os.environ["JETSON_BOARD"],
                 "CUDA_ARCH_BIN": os.environ["JETSON_CUDA_ARCH_BIN"],
                 "SERIAL_NUMBER": os.environ["JETSON_SERIAL_NUMBER"].upper()}
        libraries = {"CUDA": os.environ["JETSON_CUDA"],
                     "cuDNN": os.environ["JETSON_CUDNN"],
                     "TensorRT": os.environ["JETSON_TENSORRT"],
                     "VisionWorks": os.environ["JETSON_VISIONWORKS"],
                     "OpenCV": os.environ["JETSON_OPENCV"],
                     "OpenCV-Cuda": os.environ["JETSON_OPENCV_CUDA"],
                     "VPI": os.environ["JETSON_VPI"],
                     "Vulkan": os.environ["JETSON_VULKAN_INFO"]}
        return {"info": info, "board": board, "libraries": libraries}

    @property
    def stats(self):
        """
        Detailed information of your board, with a complete list of:
         * Jetpack
         * L4T
         * Serial Number
         * ...
        """
        # Wait the deque not empty
        while not self._stats:
            pass
        # Return dictionary parsed
        return self._stats

    def open(self):
        """ Open tegrastats app and read all stats """
        if not self._started:
            try:
                self.tegrastats.open(self)
                self._started = True
            except Tegrastats.TegrastatsException as e:
                raise jtop.JtopException(e)

    def close(self):
        """ Close tegrastats app """
        self.tegrastats.close()
        self._started = False

    def attach(self, observer):
        """
        Attach an obserber to read the status of jtop

        :param observer: The function to call
        :type observer: function
        """
        self._observers.add(observer)
        # Autostart the jtop if is off
        if self._observers:
            self.open()

    def detach(self, observer):
        """
        Detach an obserber from jtop

        :param observer:  The function to detach
        :type observer: function
        """
        self._observers.discard(observer)

    def update(self, stats):
        """
        Update the status of jtop passing stats

        :param stats:  Statistic dictionary
        :type stats: dict
        """
        # Update nvpmodel
        if self.nvp is not None:
            self.nvp.update()
        # Update status from fan
        if self.qfan is not None:
            self.qfan.update()
            # Add fan status
            stats["FAN"] = self.qfan.status
        # Update status
        self._stats = stats
        # Notifiy all observers
        for observer in self._observers:
            if callable(observer):
                observer(self.stats)
            else:
                observer.update(self)

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
# EOF
