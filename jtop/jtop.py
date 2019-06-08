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

import os
# Logging
import logging
# Launch command
import subprocess as sp

from .core import NVPmodel
from .core import Tegrastats
from .core import Fan
from .core import (import_os_variables,
                   get_uptime,
                   status_disk,
                   get_local_interfaces)

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class jtop():
    """
        JTOP is a complete controller of all systems in your NVIDIA Jetson
        * Tegrastats
        * NVP Model
        * Fan
    """
    # List of available fan
    JTOP_FOLDER = '/opt/jetson_stats/'
    LIST_FANS = ['/sys/kernel/debug/tegra_fan/target_pwm', '/sys/devices/pwm-fan/target_pwm']
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']

    def __init__(self, interval=500, time=10.0):
        # Load all Jetson variables
        if "JETSON_BOARD" not in os.environ:
            logger.info("Load jetson variables from script")
            for k, v in import_os_variables(jtop.JTOP_FOLDER + 'jetson_variables').items():
                logger.debug("New Enviroment variable {}:{}".format(k, v))
                os.environ[k] = v
        # Initialize NVP model
        self.nvp = NVPmodel(os.environ["JETSON_BOARD"])
        # Find all fans availables
        self.qfans = []
        for fan in jtop.LIST_FANS:
            if os.path.isfile(fan):
                self.qfans += [Fan(fan, interval, time)]
        # Start process tegrastats
        tegrastats_file = ""
        for f_tegra in jtop.TEGRASTATS:
            if os.path.isfile(f_tegra):
                logger.info("Load tegrastats {}".format(f_tegra))
                tegrastats_file = f_tegra
                break
        # Initialize Tegrastats controller
        self._stats = {}
        self.tegrastats = Tegrastats(tegrastats_file, interval, time)

    @property
    def fans(self):
        return [fan.status for fan in self.qfans]

    @property
    def disk(self):
        return status_disk()

    def jetson_clock_status(self):
        p = sp.Popen(['systemctl', 'is-active', 'jetson_performance.service'], stdout=sp.PIPE)
        out, _ = p.communicate()
        return out.strip()

    @property
    def uptime(self):
        return get_uptime()

    @property
    def nvpmodel(self):
        return self.nvp.status

    @property
    def local_interfaces(self):
        return get_local_interfaces()

    @property
    def board(self):
        board = {"name": os.environ["JETSON_DESCRIPTION"],
                 "type": os.environ["JETSON_TYPE"],
                 "jetpack": os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]",
                 "GPU-arch": os.environ["JETSON_CUDA_ARCH_BIN"]}
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
        self.tegrastats.open(self.reader)

    def close(self):
        self.tegrastats.close()

    def reader(self, stats):
        # Update status
        self._stats = stats
        # Update status from fan
        for fan in self.qfans:
            fan.update()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
# EOF
