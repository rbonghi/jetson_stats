# -*- coding: UTF-8 -*-
# This file is part of the ros_webconsole package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
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


class jtop(StatusObserver):
    """
        JTOP is a complete controller of all systems in your NVIDIA Jetson
        * Tegrastats
        * NVP Model
        * Fan
    """

    class JtopException(Exception):
        pass

    # List of available fan
    JTOP_FOLDER = '/opt/jetson_stats/'
    LIST_FANS = ['/sys/kernel/debug/tegra_fan/', '/sys/devices/pwm-fan/']
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']

    def __init__(self, interval=500, time=10.0):
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
        for path in jtop.LIST_FANS:
            try:
                self.qfan = Fan(path)
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
        return os.getuid()

    @property
    def fan(self):
        return self.qfan

    @property
    def disk(self):
        return status_disk()

    @property
    def jetson_clocks(self):
        return self.jc

    @property
    def uptime(self):
        return get_uptime()

    @property
    def nvpmodel(self):
        return self.nvp

    @property
    def local_interfaces(self):
        return get_local_interfaces()

    @property
    def board(self):
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
        # Wait the deque not empty
        while not self._stats:
            pass
        # Return dictionary parsed
        return self._stats

    def open(self):
        try:
            self.tegrastats.open(self)
        except Tegrastats.TegrastatsException as e:
            raise jtop.JtopException(e)

    def close(self):
        self.tegrastats.close()

    def attach(self, observer):
        self._observers.add(observer)

    def detach(self, observer):
        self._observers.discard(observer)

    def update(self, stats):
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
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
# EOF
