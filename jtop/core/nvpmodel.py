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
# Functions and decorators
from functools import wraps

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def jetson_clocks_checks(func):
    """ Enable and disable Jetson Clocks after NVP model change """
    @wraps(func)
    def wrapped(self, level):
        # Disable the jetson_clocks (only if is it active) before change NVPmodel level
        if self.jetson_clocks is not None:
            old_status = self.jetson_clocks.start
            if old_status:
                self.jetson_clocks.start = False
        status = func(self, level)
        # Enable again the jetson_clocks status
        if self.jetson_clocks is not None:
            if old_status:
                self.jetson_clocks.start = True
        # Return status function
        return status
    return wrapped


class NVPmodel():
    """
        This controller read the status from your NVIDIA Jetson and you can control
        performance and status.
        It is available for NVIDIA Jetson TX2, Jetson AGX Xavier, Jetson Nano
        Boards reference:
        * TX2: https://www.jetsonhacks.com/2017/03/25/nvpmodel-nvidia-jetson-tx2-development-kit/
        * AGX Xavier: https://www.jetsonhacks.com/2018/10/07/nvpmodel-nvidia-jetson-agx-xavier-developer-kit/
        * Nano: https://www.jetsonhacks.com/2019/04/10/jetson-nano-use-more-power/
    """
    REGEXP = re.compile(r'POWER_MODEL: ID=(.+?) NAME=((.*))')
    REGPM = re.compile(r'NV Power Mode: ((.*))')

    class NVPmodelException(Exception):
        pass

    def __init__(self, jetson_clocks=None):
        self.jetson_clocks = jetson_clocks
        try:
            nvpmodel_p = sp.Popen(['nvpmodel', '-p', '--verbose'], stdout=sp.PIPE)
            out, _ = nvpmodel_p.communicate()
            # Log value
            logger.debug('nvqmodel status %s', out)
            # Decode lines
            lines = out.decode("utf-8")
            # Read all lines and extract modes
            self.board = []
            for line in lines.split("\n"):
                # Search configuration NVPmodel
                match = NVPmodel.REGEXP.search(line)
                # if match extract name and number
                if match:
                    mode = str(match.group(2))
                    pm = {"ID": int(match.group(1)), "Name": mode.replace("MODE_", "").replace("_", " "), "status": True}
                    self.board += [pm]
        except OSError:
            logger.info("This board does not have NVP Model")
            raise NVPmodel.NVPmodelException("NVPmodel does not exist for this board")
        except AttributeError:
            logger.info("Wrong open")
            raise NVPmodel.NVPmodelException("Wrong open")
        # Initialize mode and num
        self.update()
        # Initialize with first configuration number
        self.selected = self.num

    @property
    def modes(self):
        return self.board

    @jetson_clocks_checks
    def set(self, level):
        """ Set nvpmodel to a new status """
        try:
            self.selected = level
            # Set the new nvpmodel status
            sep_nvp = sp.Popen(['nvpmodel', '-m', str(level)], stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.PIPE)
            out, _ = sep_nvp.communicate()
            if "NVPM ERROR" in out.decode("utf-8"):
                self.board[level]["status"] = False
                return False
            else:
                self.board[level]["status"] = True
                return True
        except OSError:
            logger.info("NVP Model does not exist")
            return False
        except AttributeError:
            logger.info("Wrong open")
            return False

    def increase(self):
        if self.selected + 1 < len(self.modes):
            self.selected += 1
            return self.set(self.selected)
        else:
            return False

    def decrease(self):
        if self.selected - 1 >= 0:
            self.selected -= 1
            return self.set(self.selected)
        else:
            return False

    def update(self):
        """ Read nvpmodel to know the status of the board """
        try:
            nvpmodel_p = sp.Popen(['nvpmodel', '-q'], stdout=sp.PIPE, stderr=sp.PIPE)
            out, _ = nvpmodel_p.communicate()
            # Log value
            logger.debug('nvqmodel status %s', out)
            # Decode lines and split
            lines = out.decode("utf-8").split("\n")
            # Extract lines
            for idx, line in enumerate(lines):
                # Search configuration NVPmodel
                match = NVPmodel.REGPM.search(line)
                # if match extract name and number
                if match:
                    # Extract NV Power Mode
                    mode = str(match.group(1))
                    self.mode = mode.replace("MODE_", "").replace("_", " ")
                    # Extract number
                    self.num = int(lines[idx + 1])
                    break
        except OSError:
            logger.info("NVP Model does not exist")
        except AttributeError:
            logger.info("Wrong open")
# EOF
