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

import re
import os
# Logging
import logging

from .core import NVPmodel
from .core import Tegrastats
from .core import Fan
from .core import JetsonClocks
from .core import (import_os_variables,
                   get_uptime,
                   status_disk,
                   get_local_interfaces,
                   StatusObserver)

# Create logger for jplotlib
logger = logging.getLogger(__name__)
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)


def get_version():
    # Load version package
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, "__init__.py")) as fp:
        VERSION = VERSION_RE.match(fp.read()).group(1)
    return VERSION


class jtop(StatusObserver):
    """
    JTOP is a complete controller of all systems in your NVIDIA Jetson
     * Tegrastats
     * NVP Model
     * Fan
     * Status board (i.g. Model version, Jetpack, ... )
    You can initialize the jtop node like a file i.g.

    with jtop() as jetson:
        stat = jetson.stats

    Or manually start up with the basic function open/close

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

    Attributes
    ----------
    userid: int
        User ID launched
    fan: Fan
        Fan object with contron properties
    disk: dict
        Status of the disk with details: free, occupied space
    jetson_clocks: JetsonClock
        JetsonClock controller, with this object you can manage the JetsonClock
    uptime: dict
        Uptime of your jetson board
    nvpmodel: NVPmodel
        NVPmodel is the controller of your NVP model.
        From this object you read and set the status of your NVIDIA Jetson.
    local_interfaces: dict
        Detailed dictionary with the status of all local interfaces
    board: dict
        Detailed information of your board, with a complete list of:
         * Jetpack
         * L4T
         * Serial Number
         * ...
    stats: dict
        Statistics of your board. A complete dictionary with the status of your
        board. There are all information from tegrastats, nvpmodel and fan
    Methods
    -------
    open()
        Initialize and open the tegrastats reader
    close()
        Close the tegratstats reader
    attach(observer)
        Attach an observer to read the status from the jtop
    detach(observer)
        Deatach the observer from the jtop
    update(stats)
        Update the jtop status from stats
    """

    class JtopException(Exception):
        """ Jtop general exception """
        pass

    # List of available fan
    JTOP_FOLDER = '/opt/jetson_stats/'
    LIST_FANS = [('/sys/kernel/debug/tegra_fan/', False), ('/sys/devices/pwm-fan/', True)]
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']

    def __init__(self, interval=500):
        """
        Parameters
        ----------
        interval: int
            Interval update tegrastats and other statistic function
        """
        # Version package
        self.version = get_version()
        # Initialize observer
        self._observers = set()
        # Load all Jetson variables
        logger.info("Load jetson variables from script")
        for k, v in import_os_variables(jtop.JTOP_FOLDER + 'jetson_variables').items():
            logger.debug("New Enviroment variable {}:{}".format(k, v))
            os.environ[k] = v
        # Initialize jetson_clocks controller
        self.jc = JetsonClocks()
        # Initialize NVP model
        try:
            self.nvp = NVPmodel(os.environ["JETSON_TYPE"], jetson_clocks=self.jc)
        except NVPmodel.NVPmodelException:
            self.nvp = None
        # Find all fans availables
        self.qfan = None
        for path, temp_control in jtop.LIST_FANS:
            try:
                self.qfan = Fan(path, self.jc, temp_control)
                logger.info("Fan {} loaded!".format(path))
                break
            except Fan.FanException:
                logger.info("Fan {} not loaded".format(path))
        # Start process tegrastats
        tegrastats_file = ""
        for f_tegra in jtop.TEGRASTATS:
            if os.path.isfile(f_tegra):
                logger.info("Load tegrastats {}".format(f_tegra))
                tegrastats_file = f_tegra
                break
        if not tegrastats_file:
            raise jtop.JtopException("Tegrastats is not availabe on this board")
        # Initialize Tegrastats controller
        self._stats = {}
        self.tegrastats = Tegrastats(tegrastats_file, interval)

    @property
    def userid(self):
        """ Linux User ID """
        return os.getuid()

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
        """ NVPmodel controller """
        return self.nvp

    @property
    def local_interfaces(self):
        """ Local interfaces information """
        return get_local_interfaces()

    @property
    def board(self):
        """ Board information dictionary """
        board = {"Name": os.environ["JETSON_DESCRIPTION"],
                 "Type": os.environ["JETSON_TYPE"],
                 "Jetpack": os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]",
                 "GPU-Arch": os.environ["JETSON_CUDA_ARCH_BIN"],
                 "SN": os.environ["JETSON_SERIAL_NUMBER"].upper()}
        libraries = {"CUDA": os.environ["JETSON_CUDA"],
                     "cuDNN": os.environ["JETSON_CUDNN"],
                     "TensorRT": os.environ["JETSON_TENSORRT"],
                     "VisionWorks": os.environ["JETSON_VISIONWORKS"],
                     "OpenCV": os.environ["JETSON_OPENCV"] + " compiled CUDA: " + os.environ["JETSON_OPENCV_CUDA"]}
        return {"board": board, "libraries": libraries}

    @property
    def stats(self):
        """ Dictionary with a complete list of tegrastats variables """
        # Wait the deque not empty
        while not self._stats:
            pass
        # Return dictionary parsed
        return self._stats

    def open(self):
        """ Open tegrastats app and read all stats """
        try:
            self.tegrastats.open(self)
        except Tegrastats.TegrastatsException as e:
            raise jtop.JtopException(e)

    def close(self):
        """ Close tegrastats app """
        self.tegrastats.close()

    def attach(self, observer):
        """
        Attach an obserber to read the status of jtop

        Parameters
        ----------
        observer: function
            The function to call
        """
        self._observers.add(observer)

    def detach(self, observer):
        """
        Detach an obserber from jtop

        Parameters
        ----------
        observer: function
            The function to detach
        """
        self._observers.discard(observer)

    def update(self, stats):
        """
        Update the status of jtop passing stats
        Parameters
        ----------
        stats: dict
            Statistic dictionary
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
            observer.update(self)

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        self.close()
# EOF
