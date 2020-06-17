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
# Logging
import logging
# Launch command
import subprocess as sp
# Import exceptions
from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)
# Regular expressions
REGEXP = re.compile(r'POWER_MODEL: ID=(.+?) NAME=((.*))')
REGPM = re.compile(r'NV Power Mode: ((.*))')


class NVPModel(object):
    """
        This controller read the status from your NVIDIA Jetson and you can control
        performance and status.
        It is available for NVIDIA Jetson TX2, Jetson AGX Xavier, Jetson Nano
        Boards reference:
        * TX2: https://www.jetsonhacks.com/2017/03/25/nvpmodel-nvidia-jetson-tx2-development-kit/
        * AGX Xavier: https://www.jetsonhacks.com/2018/10/07/nvpmodel-nvidia-jetson-agx-xavier-developer-kit/
        * Nano: https://www.jetsonhacks.com/2019/04/10/jetson-nano-use-more-power/
    """
    def __init__(self):
        # Read all lines and extract modes
        self._nvpm = {}
        try:
            nvpmodel_p = sp.Popen(['nvpmodel', '-p', '--verbose'], stdout=sp.PIPE)
            out, _ = nvpmodel_p.communicate()
            # Decode lines
            lines = out.decode("utf-8")
            for line in lines.split("\n"):
                # Search configuration NVPmodel
                match = REGEXP.search(line)
                # if match extract name and number
                if match:
                    # Extract id and name
                    mode_id = int(match.group(1))
                    mode_name = str(match.group(2)).replace("MODE_", "").replace("_", " ")
                    # Save in nvpm list
                    self._nvpm[mode_id] = {'name': mode_name}
        except OSError:
            logger.warning("This board does not have NVP Model")
            raise JtopException("NVPmodel does not exist for this board")
        except AttributeError:
            logger.error("Wrong open")
            raise JtopException("Wrong open")
        # Initialize mode
        self._mode = ""

    @property
    def modes(self):
        return self._nvpm

    def set(self, value):
        if isinstance(value, str):
            print("string", value)
        elif isinstance(value, int):
            print("Number", value)
        return value

    def __add__(self, number):
        pass

    def __sub__(self, number):
        pass

    def __iadd__(self, number):
        pass

    def __isub__(self, number):
        pass

    def __repr__(self):
        return self._mode

    def _update(self, mode):
        self._mode = mode


class NVPModelService(object):

    def __init__(self, jetson_clocks=None):
        self.jetson_clocks = jetson_clocks
        try:
            NVPModelService.query()
        except OSError:
            logger.warning("This board does not have NVP Model")
            raise JtopException("NVPmodel does not exist for this board")

    def set(self, value):
        if self.jetson_clocks is None:
            # Set NV Power Mode
            return self._mode(value)
        # Otherwise disable the jetson_clocks
        old_status = self.jetson_clocks.is_alive
        if old_status:
            self.jetson_clocks.stop()
            # Check jetson_clocks is off
            while self.jetson_clocks.is_alive:
                pass
        # Set NV Power Mode
        status = self._mode(value)
        # Enable again the jetson_clocks status
        if old_status:
            self.jetson_clocks.start()
        # Return status
        return status

    def _mode(self, level):
        """ Set nvpmodel to a new status """
        self.selected = level
        # Set the new nvpmodel status
        sep_nvp = sp.Popen(['nvpmodel', '-m', str(level)], stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.PIPE)
        out, _ = sep_nvp.communicate()
        # If there are no errors return the NV Power mode
        return "NVPM ERROR" not in out.decode("utf-8")

    def get(self):
        # Initialize mode and num
        _, mode = NVPModelService.query()
        # Return the mode
        return mode

    @staticmethod
    def query():
        """ Read nvpmodel to know the status of the board """
        num = -1
        mode = ""
        nvpmodel_p = sp.Popen(['nvpmodel', '-q'], stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = nvpmodel_p.communicate()
        # Decode lines and split
        lines = out.decode("utf-8").split("\n")
        # Extract lines
        for idx, line in enumerate(lines):
            # Search configuration NVPmodel
            match = REGPM.search(line)
            # if match extract name and number
            if match:
                # Extract NV Power Mode
                mode = str(match.group(1))
                mode = mode.replace("MODE_", "").replace("_", " ")
                # Extract number
                num = int(lines[idx + 1])
                break
        return num, mode
# EOF
