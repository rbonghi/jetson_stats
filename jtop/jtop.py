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
"""
jtop is a simple package to monitoring and control your NVIDIA Jetson [Orin, Xavier, Nano, TX] series.

It read the status of your board using different native processes:
 * tegrastats
 * jetson_clocks
 * NVP Model
 * Fan
 * Swap
 * Disk
 * Network

Decode the board information and status
 * board name
 * Jetpack
 * L4T
 * Hardware configuration
 * Libraries installed

You can initialize the jtop, look these examples:

.. code-block:: python

    with jtop() as jetson:
        while jetson.ok():
            stats = jetson.stats

Or using a callback function

.. code-block:: python

    def read_stats(jetson):
        stats = jetson.stats

    jetson = jtop()
    jetson.attach(read_stats)
    jetson.loop_for_ever()

Other example are available on https://github.com/rbonghi/jetson_stats/tree/master/examples
Follow the next attributes to know in detail how you can you in your python project.
"""
import logging
import re
import sys
# from warnings import warn
from datetime import datetime, timedelta
from multiprocessing import Event, AuthenticationError
from threading import Thread
from .service import JtopManager
from .core.jetson_variables import get_platform_variables
from .core.memory import Memory
from .core.fan import Fan
from .core.gpu import GPU
from .core import (
    get_var,
    get_cuda,
    get_opencv,
    get_libraries,
    NVPModel,
    get_uptime,
    status_disk,
    get_local_interfaces,
    JetsonClocks,
    JtopException)
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
try:
    PermissionError
except NameError:
    PermissionError = OSError
if sys.version_info[0] == 2:
    from socket import error as ConnectionRefusedError
# Create logger
logger = logging.getLogger(__name__)
# Gain timeout lost connection
TIMEOUT_GAIN = 3
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)


class jtop(Thread):
    """
    This class control the access to your board, from here you can control your
    NVIDIA Jetson board or read the jetson_clocks status or change the nvp model.

    When you initialize your jtop you can setup a communication speed **interval**,
    if there is another jtop running this speed will be not used.

    When jtop is started you can read the server speed in **interval** property.

    :param interval: Interval to setup the jtop speed (in seconds)
    :type interval: float
    """

    def __init__(self, interval=1.0):
        # Initialize Thread super class
        super(jtop, self).__init__()
        # Local Event thread
        self._trigger = Event()
        # Error message from thread
        self._error = None
        # Start server
        self._running = False
        # Load interval
        self._interval = float(interval)
        # Initialize observer
        self._observers = set()
        # Stats read from service
        self._stats = {}
        # Read stats
        JtopManager.register('get_queue')
        JtopManager.register("sync_data")
        JtopManager.register('sync_event')
        # Initialize broadcaster manager
        self._broadcaster = JtopManager()
        # Initialize board variable
        self._board = {}
        self._thread_libraries = Thread(target=self._load_jetson_libraries, args=[])
        self._thread_libraries.daemon = True
        self._thread_libraries.start()
        # Initialize gpu info
        self._gpu = GPU()
        # Initialize memory controller
        self._memory = Memory()
        # Initialize fan
        self._fan = Fan()
        # Load jetson_clocks status
        self._jetson_clocks = None
        # Load NV Power Mode
        self._nvpmodel = None

    def _load_jetson_libraries(self):
        # Load platform
        self._board['platform'] = get_platform_variables()
        # Load all variables
        cuda_version = get_cuda()
        opencv_version, opencv_cuda = get_opencv()
        os_variables = get_libraries()
        libraries = {
            'CUDA': cuda_version,
            'OpenCV': opencv_version,
            'OpenCV-Cuda': opencv_cuda,
        }
        libraries.update(os_variables)
        # Make dictionaries
        self._board['libraries'] = libraries
        # Loaded from script
        logger.debug("Loaded jetson_variables variables")

    def attach(self, observer):
        """
        Attach an observer to read the status of jtop. You can add more observer that you want.

        The function **must** be with this format:

        .. code-block:: python

            def observer(jetson):
                pass

        The input of your callback will be the jetson object.

        To detach a function, please look :func:`~detach`

        :param observer: The function to call
        :type observer: function
        """
        self._observers.add(observer)

    def detach(self, observer):
        """
        Detach an observer from jtop

        To attach a function, please look :func:`~attach`

        :param observer:  The function to detach
        :type observer: function
        """
        self._observers.discard(observer)

    def restore(self, max_counter=10):
        """
        This block method will restore all jtop configuration, in order:

        * **switch off** jetson_clocks
        * **Disable** jetson_clocks on boot
        * **fan**
            * set to **default**, please follow the fan reference :py:attr:`~fan`
            * set fan speed to 0 (This operation can require time)
        * If active **disable** the jtop swap
        * **Clear** the internal jtop configuration file

        .. code-block:: python

            for status, message in jetson.restore():
                if status:
                    print(message)
                else:
                    print("Fail")

        :param max_counter: Counter time for each test before fail
        :type max_counter: int
        :return: Generator of all operations to restore your NVIDIA Jetson
        :rtype: generator
        :raises JtopException: if the connection with the server is lost,
            not active or your user does not have the permission to connect to *jtop.service*
        """
        # Reset jetson_clocks
        if self.jetson_clocks is not None:
            # Disable jetson_clocks
            try:
                self.jetson_clocks = False
            except JtopException as ex:
                yield False, ex
            # Wait jetson_clocks boot
            counter = 0
            while self.ok() and (counter < max_counter):
                if not self.jetson_clocks:
                    break
                counter += 1
            yield counter != max_counter, "jetson_clocks off"
            # Disable jetson_clocks on boot
            self.jetson_clocks.boot = False
            # Wait jetson_clocks boot
            counter = 0
            while self.ok() and (counter < max_counter):
                if not self.jetson_clocks.boot:
                    break
                counter += 1
            yield counter != max_counter, "jetson_clocks boot off"
        # Reset fan control
        if self.fan is not None:
            # Reset mode fan
            self.fan.mode = 'system'
            counter = 0
            while self.ok() and (counter < max_counter):
                if self.fan.mode == 'system':
                    break
                counter += 1
            yield counter != max_counter, "fan mode set default"
            # Reset speed to zero
            self.fan.speed = 0
            counter = 0
            while self.ok() and (counter < max_counter):
                if self.fan.speed == 0:
                    break
                counter += 1
            yield counter != max_counter, "Fan speed={speed}".format(speed=self.fan.speed)
        # Switch off swap
        if self.swap.is_enable:
            # Deactivate swap
            self.swap.deactivate()
            counter = 0
            while self.ok() and (counter < max_counter):
                if not self.swap.is_enable:
                    break
                counter += 1
            yield counter != max_counter, "Swap disabled"
        # Clear config file
        self._controller.put({'config': 'reset'})
        yield True, "Config disabled"

    @property
    def engine(self):
        """
        Engine status, in this property you can find like: APE, DLA, NVDEC, NVENC, and other

        The output of this property is a dictionary:

        * **name group X** - In this group are collected all engines similar
            * **name engine a** - In this key there is a dictionary with engine status
            * **name engine b** - Same like above, there is the dictionary status engine

        For each engine the dictionary is defined like the table below:

        ========== ========= ==============================================
        Name       Type      Description
        ========== ========= ==============================================
        online     `boolean` Status of the engine
        unit       `string`  The size value of the frequency, usually **k**
        min        `int`     Minimum frequency of the core :sup:`A`
        max        `int`     Maximum frequency of the core :sup:`A`
        cur        `int`     Current frequency of the core
        ========== ========= ==============================================

        .. note::

                Note **A**
                    Some engines doesn't have a *min* and *max* frequency

        :return: Dictionary of all active engines
        :rtype: dict
        """
        return self._stats.get('engines', {})

    @property
    def board(self):
        """
        Board status, in this property you can find:

        * platform (from jtop library is running)
            * Machine
            * System
            * Distribution
            * Release
            * Python
        * hardware (from service is running)
            * Model
            * 699-level Part Number
            * P-Number
            * Module
            * SoC
            * CUDA Arch BIN
            * Codename (Optional)
            * Serial Number
            * L4T (Linux for Tegra)
            * Jetpack
        * libraries (from jtop library is running)
            * CUDA
            * OpenCV
            * OpenCV-Cuda (boolean)
            * cuDNN
            * TensorRT
            * VPI
            * Vulkan

        :return: Status board, hardware and libraries
        :rtype: dict
        """
        # Wait thread end
        self._thread_libraries.join()
        # Return board status
        return self._board

    @property
    def fan(self):
        """
        Fan status and control. From this property you can setup your board

        If your board does not support a fan, the output will be `None`

        The variable available are:

        * **auto** - boolean with fan control.
            * True = Automatic speed control enabled
            * False = Automatic speed control disabled
        * **speed** - Speed set. Value between [0, 100] (float)
        * **measure** - Speed measured. Value between [0, 100] (float)
        * **rpm** - Revolution Per Minute. This number can be 0 if the hardware does not implement this feature
        * **mode** - Mode selected for your fan

        If you want set a new speed, change the mode or know how many configurations are available you can use:

        .. code-block:: python

            jetson.fan.speed = value

        where *value* is a number between [0, 100] *(float)*

        .. code-block:: python

            jetson.fan.mode = name

        where *name* is a **string** of the mode that you want use

        .. code-block:: python

            configs = jetson.fan.configs

        Return a **list** of all available configurations:

        * *default* - The fan is not manage, when jetson_clocks start will follow the jetson_clocks configurations
        * *system* - The fan speed will be manage from the OS
        * *manual* - The fan speed is the same that you have set in *jetson.fan.speed*

        :return: Status Fan
        :rtype: Fan
        :raises ValueError: Wrong speed number or wrong mode name
        """
        return self._fan

    @property
    def nvpmodel(self):
        """
        From this function you set and read NV Power Mode. If your NVIDIA Jetson does not use nvpmodel will return None

        If you want set a new nvpmodel you can follow the NVIDIA Jetson documentation and write a string like below

        .. code-block:: python

            # You can write a string for a name or an integer for the ID
            jetson.nvpmodel = name_or_id

        If you need to increase or decrease the ID you can use

        .. code-block:: python

            jetson.nvpmodel += 1
            # or
            jetson.nvpmodel = jetson.nvpmodel + 1

        There are other properties:

        * **name** - mode name
        * **id** - ID name
        * **modes** - A list with all mode available in your board
        * **status** - A list of status for each NVP model (False if the nvpmodel is in failure)
        * **is_running** - Status updating NVP model service

        The access of this properties is available like below

        .. code-block:: python

            # NVP model name
            print(jetson.nvpmodel.name)
            # NVP model id
            print(jetson.nvpmodel.id)
            # NVP model list
            print(jetson.nvpmodel.modes)
            # NVP model status
            print(jetson.nvpmodel.status)

        :return: Return the name of NV Power Mode
        :rtype: NVPModel or None
        :raises JtopException: if the nvp model does not exist*
        """
        return self._nvpmodel

    @nvpmodel.setter
    def nvpmodel(self, value):
        if self._nvpmodel is None:
            raise JtopException("nvpmodel not available on this board")
        if isinstance(value, int):
            return self._nvpmodel.set_nvpmodel_id(value)
        elif isinstance(value, str):
            return self._nvpmodel.set_nvpmodel_name(value)
        else:
            ValueError("Data type not allowed {type}".format(type=type(value)))

    @property
    def jetson_clocks(self):
        """
        Status jetson_clocks, if you want change the jetson_clocks status you can simply write:

        .. code-block:: python

            jetson.jetson_clocks = value

        where *value* is a boolean value

        There are available other extra properties:

        * **boot** - You can enable and disable on boot **jetson_clocks**
        * **status** - A string with the current jetson_clocks status
            * *running* - The service is running
            * *booting* - jetson_clocks is in booting (When your board boot, jetson_clocks wait 60s before to start)
            * *activating* - jetson_clocks is activating
            * *deactivating* - jetson_clocks is deactivating

        You can change and edit using this property:

        .. code-block:: python

            # Read jetson_clocks boot property
            print(jetson.jetson_clocks.boot)
            # Set a new value
            jetson.jetson_clocks.boot = value  # True or False

        Written jetson_clocks status

        .. code-block:: python

            # Status jetson_clocks
            print(jetson.jetson_clocks.status)

        :return: status jetson_clocks script
        :rtype: JetsonClocks
        :raises ValueError: Wrong jetson_clocks value
        """
        return self._jetson_clocks

    @jetson_clocks.setter
    def jetson_clocks(self, value):
        if self._jetson_clocks is None:
            raise JtopException("jetson_clocks not available on this board")
        self._jetson_clocks.set_enable(value)

    @property
    def stats(self):
        """
        This property return a simplified version of tegrastats,
        it is simple to use if you want log the NVIDIA Jetson status with pandas or in a csv file.

        This property is a simplified version of all data collected from your NVIDIA Jetson,
        if you need more detailed information, please use the other jtop properties

        The field listed are:

        * **time** - A `datetime` variable with the local time in your board
        * **uptime** - A `timedelta` with the up time of your board, same from :py:attr:`~uptime`
        * **cpu X** - The status for each cpu in your board, if disabled *OFF* :py:attr:`~cpu`
        * **RAM** - Used ram :py:attr:`~memory`
        * **SWAP** - used swap :py:attr:`~memory`
        * **EMC** - If exist, the used emc :py:attr:`~memory`
        * **IRAM** - If exist, the used iram :py:attr:`~memory`
        * **GPU** - Status of your GPU :py:attr:`~gpu`
        * **engine X** - Frequency for each engine, if disabled *OFF* :py:attr:`~engine`
        * **fan** - Status fan speed :py:attr:`~fan`
        * **Temp X** - X temperature :py:attr:`~temperature`
        * **Power X** - Current power from rail X :py:attr:`~power`
        * **Power TOT** - Total current power :py:attr:`~power`
        * **jetson_clocks** - Status of jetson_clocks, human readable :py:attr:`~jetson_clocks`
        * **nvp model** - If exist, the NV Power Model name active :py:attr:`~nvpmodel`

        :return: Compacts jetson statistics
        :rtype: dict
        """
        stats = {'time': datetime.now(), 'uptime': self.uptime}
        # -- CPU --
        for idx, cpu in enumerate(self.cpu['cpu']):
            stats["CPU{idx}".format(idx=idx + 1)] = 100 - int(cpu['idle']) if cpu['online'] else 'OFF'
        # -- MEMORY --
        stats['RAM'] = self.memory['RAM']['used']
        stats['SWAP'] = self.memory['SWAP']['used']
        if 'EMC' in self.memory:
            stats['EMC'] = self.memory['EMC']['val']
        if 'IRAM' in self.memory:
            stats['IRAM'] = self.memory['IRAM']['used']
        # -- GPU --
        for idx, gpu in enumerate(self.gpu.values()):
            gpu_name = 'GPU' if idx == 0 else 'GPU{idx}'.format(idx=idx)
            stats[gpu_name] = gpu['status']['load']
        # -- Engines --
        for group in self.engine:
            for name, engine in self.engine[group].items():
                stats[name] = engine['cur'] if engine['online'] else 'OFF'
        # -- FAN --
        # Print all Fan
        for name, fan in self.fan.items():
            for idx, speed in enumerate(fan['speed']):
                stats['Fan {name}{idx}'.format(idx=idx, name=name)] = speed
        # -- Temperature --
        for temp in self.temperature:
            stats["Temp {name}".format(name=temp)] = self.temperature[temp]['temp']
        # -- Power --
        # Load all current power from each power rail
        if self.power:
            for name, rail in self.power['rail'].items():
                stats["Power {name}".format(name=temp)] = rail['power']
            # Load total current power
            stats['Power TOT'] = self.power['tot']['power']
        # -- jetson_clocks --
        if self.jetson_clocks is not None:
            stats['jetson_clocks'] = 'ON' if self.jetson_clocks else 'OFF'
        # -- NV Power Model --
        if self.nvpmodel is not None:
            stats['nvp model'] = self.nvpmodel.name
        return stats

    @property
    def memory(self):
        """
        This property show in a simple way all memories available, the main output is available in this way:

        * **RAM** - It is a dictionary with all information about RAM
        * **SWAP** - It is a dictionary with all information about SWAP
        * **EMC** - It is a dictionary with EMC data, not in all boards this data is available
        * **IRAM** - It is a dictionary with SWAP data, not in all boards this data is available

        You can also use this property to set a new swap, deactivate or clear cache,
        read all methods available :py:class:`~jtop.core.memory.Memory`


        For each dictionary there are specific outputs

        *RAM*

        ========== ========= ====================================================
        Name       Type      Description
        ========== ========= ====================================================
        tot        `int`     Total RAM
        used       `int`     Total used RAM
        free       `int`     Free RAM
        buffers    `int`     Buffered RAM
        cached     `int`     Cached RAM
        shared     `int`     Shared RAM, for NVIDIA Jetson the RAM used from GPU
        lfb        `int`     Large Free Block in **4MB**
        unit       `int`     Unit for all values, always **k**
        ========== ========= ====================================================

        *SWAP*

        ========== ========= ====================================================
        Name       Type      Description
        ========== ========= ====================================================
        tot        `int`     Total SWAP
        used       `int`     Total used SWAP
        cached     `int`     Cached RAM
        unit       `int`     Unit for all values, always **k**
        table      `dict`    Dictionary with all swap available :sup:`A`
        ========== ========= ====================================================

        *EMC* (if available on your device)

        ========== ========= ==========================================================
        Name       Type      Description
        ========== ========= ==========================================================
        online     `bool`    Status EMC
        val        `int`     Percentage of bandwidth used relative to running frequency
        cur        `int`     Current working frequency
        max        `int`     Max EMC frequency usable
        min        `int`     Min EMC frequency usable
        unit       `int`     Unit for all values, always **k**
        ========== ========= ==========================================================

        *IRAM* (if available on your device)

        ========== ========= ====================================================
        Name       Type      Description
        ========== ========= ====================================================
        tot        `int`     Total IRAM
        used       `int`     Total used IRAM
        unit       `int`     Unit for all values, always **k**
        lfb        `int`     Large Free Block in **4MB**
        ========== ========= ====================================================

        .. note::

            Note **A**
                The swap table is a list of dictionary with this data

                ========== ========= ==============================================
                Name       Type      Description
                ========== ========= ==============================================
                type       `string`  Type of partition
                prio       `int`     Priority partition
                size       `int`     Size partition
                used       `int`     Used part of this partition
                unit       `int`     Unit for all values, always **k**
                ========== ========= ==============================================

        :return: memory status
        :rtype: Memory
        """
        return self._memory

    @property
    def cpu(self):
        """
        this property return a dictionary with all information for each core about frequency, idle, and other.

        This dictionary is made:

        * **total** - The aggregate values for all cores of (user, nice, system, idle)
        * **cpu** - a list with a dictionary for each core

        For each core the dictionary is defined:

        ========== ========= =======================================
        Name       Type      Description
        ========== ========= =======================================
        online     `boolean` Status core
        governor   `string`  Type of governor running on the core
        freq       `dict`    Frequency of the core :sup:`A`
        info_freq  `dict`    Frequency of the core :sup:`A`
        idle_state `dict`    All Idle state running
        user       `int`     User percentage utilization :sup:`B`
        nice       `int`     Nice percentage utilization :sup:`B`
        system     `int`     System percentage utilization :sup:`B`
        idle       `int`     Idle percentage :sup:`B`
        model      `string`  Model core running
        ========== ========= =======================================

        .. note::

            Note **A**
                The frequency dictionary is defined like below:

                ========== ========= ==============================================
                Name       Type      Description
                ========== ========= ==============================================
                unit       `string`  The size value of the frequency, usually **k**
                min        `int`     Minimum frequency of the core
                max        `int`     Maximum frequency of the core
                cur        `int`     Current frequency of the core
                ========== ========= ==============================================

            Note **B**
                If a core is offline, this data is not key is not available

        .. admonition:: Reference

            #. https://docs.kernel.org/admin-guide/pm/cpuidle.html
            #. https://www.linuxhowtos.org/System/procstat.htm
            #. https://rosettacode.org/wiki/Linux_CPU_utilization

        :return: A dictionary with the aggregate status and a list of all CPUs, described above.
        :rtype: dict
        """
        # Return CPU status
        return self._stats['cpu']

    @property
    def processes(self):
        """
        List of all GPU processes running.

        :return: GPU processes, frequencies and speed
        :rtype: dict
        """
        return self._stats['processes']

    @property
    def gpu(self):
        """
        GPU engine. The fields are:

        * **min_freq** - Minimum frequency in kHz
        * **max_freq** - Maximum frequency in kHz
        * **frq** - Running frequency in kHz
        * **val** - Status GPU, value between [0, 100]

        :return: GPU engine, frequencies and speed
        :rtype: dict
        """
        # Extract GPU
        return self._gpu

    @property
    def power(self):
        """
        Two power dictionaries:

        * **total** - The total power estimated is not available of the NVIDIA Jetson power consumption
        * **power** - A dictionary with all power consumption

        For each power consumption there are two fields:

        * **avg** - Average power consumption in milliwatt
        * **cur** - Current power consumption in milliwatt

        :return: Two dictionaries, total and a list of all power consumption available from the board
        :rtype: dict, dict
        """
        return self._stats['power']

    @property
    def temperature(self):
        """
        A dictionary with all NVIDIA Jetson temperatures.

        All temperatures are in Celsius

        :return: Temperature dictionary
        :rtype: dict
        """
        return self._stats['temperature']

    @property
    def local_interfaces(self):
        """
        Local interfaces information and hostname

        This dictionary the status of your local network

        * **hostname** - Hostname board
        * **interfaces** - A dictionary with name and IP address for all interfaces listed

        :return: Local interfaces and hostname
        :rtype: dict
        """
        return get_local_interfaces()

    @property
    def disk(self):
        """
        Disk status properties, in dictionary are included

        * **total** - Total disk space in GB
        * **available** - Space available in GB
        * **use** - Disk space used in GB
        * **available_no_root**

        :return: Disk information
        :rtype: dict
        """
        return status_disk()

    @property
    def uptime(self):
        """
        Up time, The time since you turned on the NVIDIA Jetson

        :return: Board up time
        :rtype: timedelta
        """
        return timedelta(seconds=get_uptime())

    def _decode(self, data):
        """
        Internal decode function to decode and refactoring data
        """
        self._stats = data
        # -- GPU --
        self._gpu._update(self._stats['gpu'])
        # -- MEMORY --
        self._memory._update(data['mem'])
        # -- FAN --
        self._fan._update(data['fan'])
        # -- JETSON_CLOCKS --
        if 'jc' in data:
            self._jetson_clocks._update(data['jc'])
        # -- NVP Model --
        if 'nvp' in data:
            self._nvpmodel._update(data['nvp'])

    def run(self):
        """ """
        # https://gist.github.com/schlamar/2311116
        # https://stackoverflow.com/questions/13074847/catching-exception-in-context-manager-enter
        try:
            while self._running:
                # Send alive message
                if self._controller.empty():
                    self._controller.put({})
                # Read stats from jtop service
                data = self._get_data()
                # Decode and update all jtop data
                self._decode(data)
                # Set trigger
                self._trigger.set()
                # Notify all observers
                for observer in self._observers:
                    # Call all observer in list
                    observer(self)
        except Exception:
            # Store error message
            self._error = sys.exc_info()

    def _get_data(self):
        try:
            # Check if is not set event otherwise wait
            if not self._sync_event.is_set():
                self._sync_event.wait(self._interval * TIMEOUT_GAIN)
            # Read stats from jtop service
            data = self._sync_data.copy()
            if not data:
                raise JtopException("Error connection")
            # Clear event
            self._sync_event.clear()
        except EOFError:
            # Raise jtop exception
            raise JtopException("Lost connection with jtop server")
        return data

    def _get_configuration(self):
        while True:
            # Send configuration connection
            self._controller.put({'interval': self._interval})
            # Return configuration
            data = self._controller.get(self._interval * TIMEOUT_GAIN)
            if 'init' in data:
                return data['init']

    def start(self):
        """
        The start() function start your jtop and you can start to read the NVIDIA Jetson status.

        This method is **not** needed to close jtop if you have open jtop using `with` like:

        .. code-block:: python

            with jtop() as jetson:
                pass

        :raises JtopException: if the connection with the server is lost,
            not active or your user does not have the permission to connect to *jtop.service*
        """
        # Connected to broadcaster
        try:
            self._broadcaster.connect()
        except FileNotFoundError as e:
            if e.errno == 2 or e.errno == 111:  # Message error: 'No such file or directory' or 'Connection refused'
                raise JtopException("The jtop.service is not active. Please run:\nsudo systemctl restart jtop.service")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise JtopException("I can't access jtop.service.\nPlease logout or reboot this board.")
            else:
                raise FileNotFoundError(e)
        except ConnectionRefusedError as e:
            if e.errno == 111:  # Connection refused
                # When server is off but socket files exists in /run
                raise JtopException("The jtop.service is not active. Please run:\nsudo systemctl restart jtop.service")
            else:
                raise ConnectionRefusedError(e)
        except PermissionError as e:
            if e.errno == 13:  # Permission denied
                raise JtopException("I can't access jtop.service.\nPlease logout or reboot this board.")
            else:
                raise PermissionError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise JtopException("Mismatch of Python versions between library and service")
        except AuthenticationError:
            raise JtopException("Authentication with jetson-stats server failed")
        # Initialize synchronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Initialize connection
        init = self._get_configuration()
        # Get jtop service version
        service_version = init.get('version', 'unknown')
        if service_version != get_var(VERSION_RE):
            raise JtopException("""Mismatch version jtop service: [{service_version}] and client: [{client_version}]. Please run:\n
sudo systemctl restart jtop.service""".format(
                service_version=service_version,
                client_version=get_var(VERSION_RE)))
        # Load server speed
        self._server_interval = init['interval']
        # Load board information
        self._board['hardware'] = init['board']['hardware']
        # Initialzie gpu controller
        self._gpu._initialize(self._controller)
        # Initialize memory controller
        self._memory._initialize(self._controller, init['memory'])
        # Initialize fan
        self._fan._initialize(self._controller, init['fan'])
        # Initialize jetson_clocks (if exist)
        if init['jc']:
            self._jetson_clocks = JetsonClocks(self._controller)
        # Init NVP model (if exist)
        if 'nvpmodel' in init:
            self._nvpmodel = NVPModel(self._controller, init['nvpmodel'])
        # Wait first value
        data = self._get_data()
        # Decode and update all jtop data
        self._decode(data)
        # Run thread reader
        self._running = True
        self.daemon = True
        super(jtop, self).start()

    @property
    def interval(self):
        """
        Speed jtop service. This speed can be different compare the speed specified in :func:`~jtop` constructor

        :return: jtop interval (in seconds)
        :rtype: float
        """
        return self._server_interval

    @property
    def interval_user(self):
        """
        This is the same speed specified in :func:`~jtop` constructor

        :return: jtop user interval (in seconds)
        :rtype: float
        """
        return self._interval

    def loop_for_ever(self):
        """
        This blocking method is needed when you design your python code to work only by callback.

        Before to run this method remember to attach a callback using :func:`~attach`

        A simple example to use this method is below

        .. code-block:: python

            def read_stats(jetson):
                stats = jetson.stats

            jetson = jtop()
            jetson.attach(read_stats)
            # Blocking method
            jetson.loop_for_ever()
        """
        self.start()
        # Blocking function to catch exceptions
        while self.ok():
            try:
                self.join(timeout=0.1)
            except (KeyboardInterrupt, SystemExit):
                # Close jtop
                self.close()

    def ok(self, spin=False):
        """
        This method is needed when you start jtop using `with` like below

        .. code-block:: python

            with jtop() as jetson:
                while jetson.ok():
                    stats = jetson.stats

        This method is usually blocking, and is not needed to add in your script a sleep function,
        when a new data will be available the function will release and you will read a new fresh data

        :param spin: If True, this function will be not blocking
        :type spin: bool
        """
        # Wait if trigger is set
        if not spin:
            try:
                if not self._trigger.is_set():
                    if not self._trigger.wait(self._interval * TIMEOUT_GAIN):
                        self._running = False
            except (KeyboardInterrupt, SystemExit):
                self._running = False
        # Catch exception if exist
        if self._error:
            # Extract exception and raise
            ex_type, ex_value, tb_str = self._error
            ex_value.__traceback__ = tb_str
            raise ex_value
        # If there are not errors clear the event
        if self._running:
            self._trigger.clear()
        # Return the status
        return self._running

    def close(self):
        """
        This method will close the jtop server.

        This method is **not** needed to close jtop if you have open jtop using `with` like:

        .. code-block:: python

            with jtop() as jetson:
                pass
        """
        # Wait thread end
        self._thread_libraries.join()
        # Switch off broadcaster thread
        self._running = False

    def __enter__(self):
        """ Enter function for 'with' statement """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ Exit function for 'with' statement """
        if exc_tb is not None:
            return False
        return True
# EOF
