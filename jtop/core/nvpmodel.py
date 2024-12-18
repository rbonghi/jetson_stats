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

import re
import time
from threading import Thread
# Logging
import logging
# Launch command
from .command import Command
# Import exceptions
from .exceptions import JtopException
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

# Create logger
logger = logging.getLogger(__name__)
# Regular expressions
POWER_MODEL_DEFAULT_RE = re.compile(r'PM_CONFIG: DEFAULT=(?P<name>\w+)\((?P<id>\d+)\)')
TPC_POWER_GATING_RE = re.compile(r'TPC_POWER_GATING TPC_PG_MASK (?P<mask>\w+)')
POWER_MODEL_RE = re.compile(r'POWER_MODEL: ID=(?P<id>\d+) NAME=(?P<name>\w+)')
NV_POWER_MODE_RE = re.compile(r'NV Power Mode: (?P<name>\w+)')

COMMAND_TIMEOUT = 4.0
NVP_TIMER_WAIT_JETSON_CLOCKS = 0.5
NVP_COUNTER_ALIVE_JETSON_CLOCKS = 5


def nvpmodel_decode():
    default = {}
    nvpm = {}
    nvpm_masks = {}
    nvpmodel_p = Command(['nvpmodel', '-p', '--verbose'])
    lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
    # Decode lines
    for line in lines:
        # Search default value
        match = re.search(POWER_MODEL_DEFAULT_RE, line)
        if match:
            parsed_line = match.groupdict()
            default = {'name': parsed_line['name'], 'id': int(parsed_line['id'])}
        # Search configuration NVPmodel
        match = re.search(POWER_MODEL_RE, line)
        # if match extract name and number
        if match:
            parsed_line = match.groupdict()
            # Extract id and name
            mode_id = int(parsed_line['id'])
            # Save in nvpm list
            nvpm[mode_id] = parsed_line['name']
        # Search TPC Power Gating
        match = re.search(TPC_POWER_GATING_RE, line)
        if match:
            parsed_line = match.groupdict()
            # Extract save mask in nvpm_masks list with the same id
            nvpm_masks[mode_id] = parsed_line['mask']
    # Make a list
    nvpm_masks_list = list(nvpm_masks.values()) if nvpm_masks else [True] * len(nvpm)
    return default, list(nvpm.values()), nvpm_masks_list


def nvpmodel_query():
    """ Read nvpmodel to know the status of the board """
    try:
        nvpmodel_p = Command(['nvpmodel', '-q'])
        lines = nvpmodel_p(timeout=COMMAND_TIMEOUT)
    except FileNotFoundError:
        raise JtopException("nvpmodel doesn't exist")
    except Command.CommandException:
        raise JtopException("nvpmodel command unavailable")
    # Extract lines
    for idx, line in enumerate(lines):
        # Search configuration NVPmodel
        match = NV_POWER_MODE_RE.search(line)
        # if match extract name and number
        if match:
            parsed_line = match.groupdict()
            # Extract NV Power Mode
            return {'name': parsed_line['name'], 'id': int(lines[idx + 1])}


def set_nvpmodel_level(level, force):
    """ Set nvpmodel to a new status """
    # Set the new nvpmodel status
    try:
        # If there are no errors return the NV Power mode
        if force:
            lines = Command.run_command(['nvpmodel', '-m', str(level)], repeat=5, timeout=COMMAND_TIMEOUT, input='YES')
        else:
            lines = Command.run_command(['nvpmodel', '-m', str(level)], repeat=5, timeout=COMMAND_TIMEOUT)
        # Check if error is in vector
        for line in lines:
            if "NVPM ERROR" in line:
                text = "\n".join(lines)
                logger.error("Error to set nvpmodel {level}. Message:\n{text}".format(level=level, text=text))
                return False
    except Command.TimeoutException:
        logger.error("nvpmodel does not reply in time")
        return False
    except Command.CommandException:
        logger.error("nvpmodel command exception")
        return False
    return True


class NVPModel(object):
    """
    The NVP Model control voltage regulators, and power tree to optimize power efficiency.
    It supports three optimized power budgets, such as 10 watts, 15 watts, and 30 watts.
    For each power budget, several configurations are possible with various CPU frequencies and number of cores online.

    Capping the memory, CPU, and GPU frequencies, and number of online CPU, GPU TPC, DLA and PVA cores at a prequalified level confines the module to the target mode.

    This method simplify in a set of functions and variables this controller.

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                # Read current nvpmodel name
                print(jetson.nvpmodel)
                # List of all nvpmodel available
                models = jetson.nvpmodel.models
                print(models)
                # You can write a string for a name
                jetson.nvpmodel = models[0]
                # or an the ID name is also allowed
                jetson.nvpmodel = 0

    You can also increase/decrease the ID

    .. code-block:: python

        with jtop() as jetson:
            if jetson.ok():
                jetson.nvpmodel += 1
                # or
                jetson.nvpmodel = jetson.nvpmodel + 1

    Read how to use in :py:attr:`~jtop.jtop.nvpmodel`

    .. admonition:: Reference

        #. `NVP Model - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/Tegra%20Linux%20Driver%20Package%20Development%20Guide/power_management_tx2.html#wwpID0E0AM0HA>`_
        #. `NVP Model - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html#supported-modes-and-power-efficiency>`_
        #. `NVP Model - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#supported-modes-and-power-efficiency>`_
    """  # noqa

    def __init__(self, controller, nvpmodel):
        self._controller = controller
        self._nvp_models = nvpmodel['models']
        self._nvp_default = nvpmodel['default']
        self._status = []
        self._running = False
        self._nvpmodel_now = {}

    def _update(self, nvp_status):
        self._status = nvp_status['status']
        self._running = nvp_status['thread']
        self._nvpmodel_now = nvp_status['model']

    def is_running(self):
        """
        Return the status of the NVP Model service, if **True** the service is already running.

        :return: status nvpmodel service
        :rtype: bool
        """
        return self._running

    @property
    def id(self):
        """
        Read che current nvpmodel ID status selected

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read current nvpmodel ID
                    print(jetson.nvpmodel.id)

        :return: nvpmodel ID
        :rtype: int
        """
        return self._nvpmodel_now['id']

    @property
    def name(self):
        """
        Read che current nvpmodel ID **name** selected

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read current nvpmodel name
                    print(jetson.nvpmodel.name)
                    # same of
                    print(jetson.nvpmodel)

        :return: nvpmodel ID **name**
        :rtype: str
        """
        return self._nvpmodel_now['name']

    @property
    def status(self):
        """
        Return a list with a NVP model status. If when you set an NVP Model, something going wrong, you will read here the output

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read current nvpmodel status
                    print(jetson.nvpmodel.status)

        Output

        .. code-block:: python
            :class: no-copybutton

            # [True True True True ... True]


        :return: Status NVP Models
        :rtype: list
        """
        return self._status

    def set_nvpmodel_id(self, nvpmodel_id, force=False):
        """
        Set a new NVP model by ID. The list of nvpmodel available is with :py:func:`~get_all_nvpmodels` or :py:attr:`~models`.

        .. danger::

            If you set **force=True** the board will be rebooted immediately without any warning.

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Set a new NVP Model by ID
                    jetson.nvpmodel.set_nvpmodel_id(0, force=False)
                    # same of
                    jetson.nvpmodel = 0

        :param nvpmodel_id: nvpmodel ID
        :type nvpmodel_id: int
        :param force: Force set nvpmodel (can reboot your board), defaults to False
        :type force: bool, optional
        :raises ValueError: the variable is not an int
        :raises JtopException: nvpmodel name doesn't' exist
        """
        if not isinstance(nvpmodel_id, int):
            raise ValueError("Use an int")
        # Check if ID is in list
        if nvpmodel_id < 0 or nvpmodel_id > len(self._nvp_models) - 1:
            raise JtopException("NV Power Model ID {id} does not exists! Range [0, {max}]".format(id=nvpmodel_id, max=len(self._nvp_models) - 1))
        if nvpmodel_id == self._nvpmodel_now['id'] and not force:
            return
        # Send new nvpmodel
        self._controller.put({'nvp': {'id': nvpmodel_id, 'force': force}})

    def get_nvpmodel_id(self):
        """
        Read che current nvpmodel ID status selected

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read current nvpmodel ID
                    print(jetson.nvpmodel.get_nvpmodel_id())
                    # same of
                    print(jetson.nvpmodel.id)

        :return: nvpmodel ID
        :rtype: int
        """
        return self._nvpmodel_now['id']

    def get_all_nvpmodels(self):
        """
        All nvp models available for this board

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # list of NVP models available
                    print(jetson.nvpmodel.get_all_nvpmodels())
                    # same of
                    print(jetson.nvpmodel.models)

        :return: List os string with all nvpmodels name
        :rtype: list
        """
        return self._nvp_models

    @property
    def models(self):
        """
        All nvp models available for this board

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # list of NVP models available
                    print(jetson.nvpmodel.models)

        :return: List os string with all nvpmodels name
        :rtype: list
        """
        return self._nvp_models

    def set_nvpmodel_name(self, nvpmodel_name, force=False):
        """
        Set a new NVP model by name. The list of nvpmodel available is with :py:func:`~get_all_nvpmodels` or :py:attr:`~models`.

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Set a new NVP Model by name
                    jetson.nvpmodel.set_nvpmodel_name("15W", force=False)
                    # same of
                    jetson.nvpmodel = "15W"

        :param nvpmodel_name: name nvpmodel
        :type nvpmodel_name: str
        :param force: Force set nvpmodel (can reboot your board), defaults to False
        :type force: bool, optional
        :raises ValueError: the variable is not a string
        :raises JtopException: nvpmodel name doesn't' exist
        """
        if not isinstance(nvpmodel_name, str):
            raise ValueError("Use a string")
        if nvpmodel_name not in self._nvp_models:
            raise JtopException("NV Power Model {name} does not exists! Check all NVPmode available".format(name=nvpmodel_name))
        if nvpmodel_name == self._nvpmodel_now['name'] and not force:
            return
        # Convert in nvpmodel id and send
        nvpmodel_id = self._nvp_models.index(nvpmodel_name)
        # Send new nvpmodel
        self._controller.put({'nvp': {'id': nvpmodel_id, 'force': force}})

    def get_nvpmodel_name(self):
        """
        Read che current nvpmodel ID **name** selected

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Read current nvpmodel ID
                    print(jetson.nvpmodel.get_nvpmodel_name())
                    # same of
                    print(jetson.nvpmodel.name)
                    # or
                    print(jetson.nvpmodel)

        :return: nvpmodel ID **name**
        :rtype: str
        """
        return self._nvpmodel_now['name']

    def get_default(self):
        """
        Return a :py:class:`dict` with the default status for this board

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    default = jetson.nvpmodel.get_default()
                    print(default)

        output

        .. code-block:: python
            :class: no-copybutton

            # {'name': '15W', 'id': 0}

        :return: default NVP model
        :rtype: dict
        """
        return self._nvp_default

    def __add__(self, number):
        return self._nvpmodel_now['id'] + number

    def __radd__(self, number):
        return self._nvpmodel_now['id'] + number

    def __sub__(self, number):
        return self._nvpmodel_now['id'] - number

    def __rsub__(self, number):
        return self._nvpmodel_now['id'] - number

    def __iadd__(self, number):
        return self._nvpmodel_now['id'] + number

    def __isub__(self, number):
        return self._nvpmodel_now['id'] - number

    def __eq__(self, other):
        if isinstance(other, int):
            return self._nvpmodel_now['id'] == other
        elif isinstance(other, str):
            return self._nvpmodel_now['name'] == other
        elif isinstance(other, NVPModel):
            return self._nvpmodel_now['id'] == other._nvpmodel_now['id']
        else:
            return False

    def __repr__(self):
        return self._nvpmodel_now['name']


class NVPModelService(object):

    def __init__(self, jetson_clocks):
        self._is_nvpmodel = True
        # Initialize thread
        self._nvp_mode_set_thread = None
        # Initialize jetson_clocks config
        self._jetson_clocks = jetson_clocks
        try:
            # Read all NVP modes and masks available for this board
            self._default, self._nvp_models, self._nvp_masks = nvpmodel_decode()
            # Read current nvpmodel
            self._nvpmodel_now = nvpmodel_query()
            logger.info("nvpmodel running in [{id}]{name} - Default: {default}".format(
                name=self._nvpmodel_now['name'],
                id=self._nvpmodel_now['id'],
                default=self._default['id']))
            # Decode current mask
            current_mask = self._nvp_masks[self._nvpmodel_now['id']]
            # list of all nvpmodel status that can be changed from the current
            self._nvp_status = [current_mask == mask for idx, mask in enumerate(self._nvp_masks)]
        except (OSError, Command.CommandException):
            self._is_nvpmodel = False
            logger.warning("nvpmodel not available")

    def exists(self):
        return self._is_nvpmodel

    def get_all_nvpmodels(self):
        return self._nvp_models

    def _thread_set_nvp_model(self, nvpmodel_id, force):
        if not self._jetson_clocks.exists():
            # Set NV Power Mode
            status = set_nvpmodel_level(nvpmodel_id, force)
            # Update status
            self._nvp_status[nvpmodel_id] = status
            return
        if not self._jetson_clocks.is_config():
            # Set NV Power Mode
            status = set_nvpmodel_level(nvpmodel_id, force)
            # Update status
            self._nvp_status[nvpmodel_id] = status
            return
        # Otherwise disable the jetson_clocks
        old_status = self._jetson_clocks.get_enable()
        # Switch off jetson_clocks if is running
        if old_status:
            self._jetson_clocks.set_enable(False)
            # Check jetson_clocks is off
            counter = 0
            while self._jetson_clocks.get_enable():
                logger.info("[{counter}] NVPmodel waiting jetson_clocks setting off. Sleep for {time}s".format(
                    counter=counter, time=NVP_TIMER_WAIT_JETSON_CLOCKS))
                time.sleep(NVP_TIMER_WAIT_JETSON_CLOCKS)
                if counter > NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                    logger.error("NVPmodel jetson_clocks didn't change status in time")
                    break
                counter += 1
            if counter <= NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                logger.info("NVPmodel has switched off jetson_clocks")
        # Set NV Power Mode
        status = set_nvpmodel_level(nvpmodel_id, force)
        # Update status
        self._nvp_status[nvpmodel_id] = status
        # Status message
        if status:
            logger.info("NVPmodel started ID {id}".format(id=nvpmodel_id))
        else:
            logger.error("Error to set NVPmodel ID {id}".format(id=nvpmodel_id))
        # Switch off jetson_clocks if is running
        if old_status:
            self._jetson_clocks.set_enable(True)
            # Check jetson_clocks is off
            counter = 0
            while not self._jetson_clocks.get_enable():
                logger.info("[{counter}] NVPmodel waiting jetson_clocks setting on. Sleep for {time}s".format(
                    counter=counter, time=NVP_TIMER_WAIT_JETSON_CLOCKS))
                time.sleep(NVP_TIMER_WAIT_JETSON_CLOCKS)
                if counter > NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                    logger.error("NVPmodel jetson_clocks didn't change status in time")
                    break
                counter += 1
            if counter <= NVP_COUNTER_ALIVE_JETSON_CLOCKS:
                logger.info("NVPmodel has switched on jetson_clocks")

    def set_nvpmodel_id(self, nvpmodel_id, force):
        if self.is_running():
            return False
        # Get current NV Power Mode
        old_nvp_mask = self._nvp_masks[self.get_nvpmodel_id()]
        nvp_mask = self._nvp_masks[nvpmodel_id]
        if force:
            logger.warning("Force set nvpmodel {nvpmodel_id}".format(nvpmodel_id=nvpmodel_id))
        else:
            if nvp_mask != old_nvp_mask:
                logger.error(
                    "The new nvpmodel {nvpmodel_id} has a different mask {nvp_mask}, is not compatible".format(
                        nvpmodel_id=nvpmodel_id, nvp_mask=nvp_mask))
                return False
        # Start thread Service client
        self._nvp_mode_set_thread = Thread(target=self._thread_set_nvp_model, args=(nvpmodel_id, force))
        # self._thread.daemon = True
        self._nvp_mode_set_thread.start()

    def get_nvpmodel_id(self):
        # Read current nvpmodel
        status = self.get_status()
        return status['model']['id']

    def get_nvpmodel_name(self):
        # Read current nvpmodel
        status = self.get_status()
        return status['model']['name']

    def set_default(self):
        self.set_nvpmodel_id(self._default['id'], False)

    def get_default(self):
        return self._default

    def is_running(self):
        if self._nvp_mode_set_thread is None:
            return False
        # https://github.com/fkie/multimaster_fkie/issues/149
        # https://docs.python.org/2.7/library/threading.html#threading.Thread.is_alive
        return self._nvp_mode_set_thread.is_alive()

    def close(self):
        # If jetson_clocks doesn't exist skip
        if not self.exists():
            return
        # If there are no thread running skip
        if self._nvp_mode_set_thread is None:
            return
        if self._nvp_mode_set_thread.is_alive():
            logger.warning("Wait switch off nvpmodel thread")
            self._nvp_mode_set_thread.join(COMMAND_TIMEOUT)

        self._nvp_mode_set_thread.join()

    def get_status(self):
        running = self.is_running()
        # If thread is not running update status
        if not running:
            self._nvpmodel_now = nvpmodel_query()
        return {
            'status': self._nvp_status,
            'thread': running,
            'model': self._nvpmodel_now,
        }
# EOF
