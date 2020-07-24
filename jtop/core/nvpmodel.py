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
from threading import Thread
# Logging
import logging
# Launch command
from .command import Command
# Import exceptions
from .exceptions import JtopException
# Create logger
logger = logging.getLogger(__name__)
# Regular expressions
REGEXP = re.compile(r'POWER_MODEL: ID=(.+?) NAME=((.*))')
REGPM = re.compile(r'NV Power Mode: ((.*))')
COMMAND_TIMEOUT = 4.0
NVP_RESEND_JETSON_CLOCKS_MESSAGE = 3
NVP_COUNTER_ALIVE_JETSON_CLOCKS = 3


def NVP_get_id(modes, value):
    try:
        mode_id = modes.index(value)
    except ValueError:
        raise JtopException("This mode {value} does not exists".format(value=value))
    return mode_id


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
        self._nvpm = {}
        # Initialize mode
        self._mode = ""

    @property
    def is_running(self):
        return self._running

    @property
    def status(self):
        return [self._nvpm[k]['status'] for k in sorted(self._nvpm)]

    @property
    def modes(self):
        # Make sorted list
        return [self._nvpm[k]['name'] for k in sorted(self._nvpm)]

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._mode

    def set(self, value):
        if isinstance(value, str):
            # Convert MODE to ID
            mode_id = NVP_get_id(self.modes, value)
        elif isinstance(value, int):
            # Check if ID is in list
            if value < 0 or value > len(self.modes) - 1:
                raise JtopException("NV Power Model ID {value} does not exists! Range [0, {max}]".format(value=value, max=len(self.modes) - 1))
            mode_id = value
        else:
            raise TypeError("Data type not allowed {type}".format(type=type(value)))
        return mode_id

    def __add__(self, number):
        return self._id + number

    def __radd__(self, number):
        return self._id + number

    def __sub__(self, number):
        return self._id - number

    def __rsub__(self, number):
        return self._id - number

    def __iadd__(self, number):
        # Get new number
        return self._id + number

    def __isub__(self, number):
        # Get new number
        return self._id - number

    def __repr__(self):
        return self._mode

    def _update(self, nvp_status):
        # Update nvpm modes
        self._nvpm = nvp_status['modes']
        self._mode = nvp_status['mode']
        self._running = nvp_status['thread']
        self._id = NVP_get_id(self.modes, self._mode)


class NVPModelService(object):

    def __init__(self, jetson_clocks, nvp_model):
        self.nvpmodel_name = "".join(nvp_model)
        # Initialize thread
        self._thread = None
        # Initialize jetson_clocks config
        self.jetson_clocks = jetson_clocks
        # Read all lines and extract modes
        self._nvpm = {}
        try:
            nvpmodel_p = Command([self.nvpmodel_name, '-p', '--verbose'])
            lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
            # Decode lines
            for line in lines:
                # Search configuration NVPmodel
                match = REGEXP.search(line)
                # if match extract name and number
                if match:
                    # Extract id and name
                    mode_id = int(match.group(1))
                    mode_name = str(match.group(2))
                    # Save in nvpm list
                    self._nvpm[mode_id] = {'name': mode_name, 'status': True}
            # Get starting model
            self.selected, _ = NVPModelService.query(self.nvpmodel_name)
        except (OSError, Command.CommandException):
            logger.warning("This board does not have NVP Model")
            raise JtopException("NVPmodel does not exist for this board")

    def _thread_set_nvp_model(self, value):
        if self.jetson_clocks is None:
            # Set NV Power Mode
            status = self.set_mode(value)
            self._nvpm[value]['status'] = status
            return status
        if not self.jetson_clocks.is_config():
            # Set NV Power Mode
            status = self.set_mode(value)
            self._nvpm[value]['status'] = status
            return status
        # Otherwise disable the jetson_clocks
        old_status = self.jetson_clocks.alive(wait=False)
        # Switch off jetson_clocks if is running
        if old_status:
            for idx in range(NVP_RESEND_JETSON_CLOCKS_MESSAGE):
                logger.debug("{idx} Counter switch on jetson_clocks".format(idx=idx))
                self.jetson_clocks.set(False)
                # Check jetson_clocks is off
                counter = 0
                try:
                    while self.jetson_clocks.alive():
                        counter += 1
                        if counter > NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                            logger.info("Timeout wait jetson_clocks alive")
                            break
                    if counter <= NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                        logger.info("NVPmodel has switched off jetson_clocks")
                        break
                except JtopException:
                    logger.error("I cannot set jetson_clocks")
                    break
        # Set NV Power Mode
        try:
            status = self.set_mode(value)
        except JtopException as e:
            logger.error(e)
            status = False
        # Update status
        self._nvpm[value]['status'] = status
        # Enable again the jetson_clocks status
        if old_status:
            for idx in range(NVP_RESEND_JETSON_CLOCKS_MESSAGE):
                logger.debug("{idx} Counter switch on jetson_clocks".format(idx=idx))
                self.jetson_clocks.set(True)
                # Check jetson_clocks is on
                counter = 0
                try:
                    while not self.jetson_clocks.alive():
                        counter += 1
                        if counter > NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                            logger.info("Timeout wait jetson_clocks alive")
                            break
                    if counter <= NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                        logger.info("NVPmodel has switched on jetson_clocks")
                        break
                except JtopException:
                    logger.error("I cannot set jetson_clocks")
                    break
        if status:
            logger.info("NVPmodel started {value}".format(value=value))
        else:
            logger.warning("Error to set NVPmodel {value}".format(value=value))

    def is_running(self):
        if self._thread is None:
            return False
        return self._thread.isAlive()

    def set(self, value):
        if self.is_running():
            return False
        # Start thread Service client
        self._thread = Thread(target=self._thread_set_nvp_model, args=(value, ))
        # self._thread.daemon = True
        self._thread.start()
        return True

    def reset(self):
        status = self.set_mode(self.selected)
        if status:
            logger.info("RESET nvpmodel to {ID}".format(ID=self.selected))
        else:
            logger.error("Fail to reset nvpmodel to {ID}".format(ID=self.selected))

    def modes(self):
        return self._nvpm

    def set_mode(self, level):
        """ Set nvpmodel to a new status """
        # Set the new nvpmodel status
        try:
            # If there are no errors return the NV Power mode
            lines = Command.run_command([self.nvpmodel_name, '-m', str(level)], repeat=5, timeout=COMMAND_TIMEOUT)
            # Check if error is in vector
            for line in lines:
                if "NVPM ERROR" in line:
                    text = "\n".join(lines)
                    logger.error("Error to set nvpmodel {level}. Message:\n{text}".format(level=level, text=text))
                    return False
        except Command.TimeoutException:
            raise JtopException("nvpmodel does not reply in time")
        # If everithing go well save the new mode
        self.selected = level
        return True

    def get(self):
        # Initialize mode and num
        _, mode = NVPModelService.query(self.nvpmodel_name)
        # Return the mode
        return mode

    @staticmethod
    def query(nvp_model):
        """ Read nvpmodel to know the status of the board """
        num = -1
        mode = ""
        nvpmodel_p = Command([nvp_model, '-q'])
        lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
        # Extract lines
        for idx, line in enumerate(lines):
            # Search configuration NVPmodel
            match = REGPM.search(line)
            # if match extract name and number
            if match:
                # Extract NV Power Mode
                mode = str(match.group(1))
                # Extract number
                num = int(lines[idx + 1])
                break
        return num, mode
# EOF
