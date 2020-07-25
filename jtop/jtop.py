# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2020 Raffaello Bonghi.
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
jtop is a simple package to monitoring and control your NVIDIA Jetson [Xavier NX, Nano, AGX Xavier, TX1, TX2].

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

Other example are availables on https://github.com/rbonghi/jetson_stats/tree/master/examples
Follow the next attributes to know in detail how you can you in your python project.
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from multiprocessing import Event, AuthenticationError
from threading import Thread
from .service import JtopManager
from .core import (
    Board,
    Engine,
    Swap,
    Fan,
    NVPModel,
    get_uptime,
    status_disk,
    import_os_variables,
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

    def __init__(self, interval=0.5):
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
        self._board = Board()
        self._thread_libraries = Thread(target=self._load_jetson_libraries, args=[])
        self._thread_libraries.daemon = True
        self._thread_libraries.start()
        # Initialize engines
        self._engine = Engine()
        # Initialize swap
        self._swap = None
        # Load jetson_clocks status
        self._jc = None
        # Initialize fan
        self._fan = None
        # Load NV Power Mode
        self._nvp = None

    def _load_jetson_libraries(self):
        try:
            env = {}
            JTOP_FOLDER, _ = os.path.split(__file__)
            libraries = import_os_variables(JTOP_FOLDER + "/jetson_libraries", "JETSON_")
            for k, v in libraries.items():
                env[k] = str(v)
            # Make dictionaries
            self._board._update_libraries({
                "CUDA": env["JETSON_CUDA"],
                "cuDNN": env["JETSON_CUDNN"],
                "TensorRT": env["JETSON_TENSORRT"],
                "VisionWorks": env["JETSON_VISIONWORKS"],
                "OpenCV": env["JETSON_OPENCV"],
                "OpenCV-Cuda": env["JETSON_OPENCV_CUDA"],
                "VPI": env["JETSON_VPI"],
                "Vulkan": env["JETSON_VULKAN_INFO"]})
            # Loaded from script
            logger.debug("Loaded jetson_variables variables")
        except Exception:
            # Write error message
            self._error = sys.exc_info()

    def attach(self, observer):
        """
        Attach an observer to read the status of jtop. You can add more observer that you want.

        The function **must** be with this format:

        .. code-block:: python

            def observer(jetson):
                pass

        The input of your callback will be the jetson object.

        To detach a function, please look :func:`~jtop.jtop.jtop.detach`

        :param observer: The function to call
        :type observer: function
        """
        self._observers.add(observer)

    def detach(self, observer):
        """
        Detach an observer from jtop

        To attach a function, please look :func:`~jtop.jtop.jtop.attach`

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
            * set to **default**, please follow the fan reference :func:`~jtop.jtop.jtop.fan`
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
            not active or your user does not have the permission to connect to *jetson_stats.service*
        """
        # Reset jetson_clocks
        if self.jetson_clocks is not None:
            # Disable jetson_clocks
            self.jetson_clocks = False
            # Wait jetson_clocks boot
            counter = 0
            while self.ok() or counter == max_counter:
                if not self.jetson_clocks:
                    break
                counter += 1
            yield counter != max_counter, "jetson_clocks off"
            # Disable jetson_clocks on boot
            self.jetson_clocks.boot = False
            # Wait jetson_clocks boot
            counter = 0
            while self.ok() or counter == max_counter:
                if not self.jetson_clocks.boot:
                    break
                counter += 1
            yield counter != max_counter, "jetson_clocks boot off"
        # Reset fan control
        if self.fan is not None:
            # Reset mode fan
            self.fan.mode = 'default'
            counter = 0
            while self.ok() or counter == max_counter:
                if self.fan.mode == 'default':
                    break
                counter += 1
            yield counter != max_counter, "fan mode set default"
            # Reset speed to zero
            self.fan.speed = 0
            counter = 0
            while self.ok() or counter == max_counter:
                if self.fan.measure == 0:
                    break
                counter += 1
            yield counter != max_counter, "Fan speed={measure}".format(measure=self.fan.measure)
        # Switch off swap
        if self.swap.is_enable:
            # Deactivate swap
            self.swap.deactivate()
            counter = 0
            while self.ok() or counter == max_counter:
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
        Engine status, in this property you can find:

        * **APE** in MHz
        * **NVENC** in MHz
        * **NVDEC** in MHz
        * **NVJPG** in MHz (If supported in your board)

        :return: List of all active engines
        :rtype: Engine
        """
        return self._engine

    @property
    def board(self):
        """
        Board status, in this property you can find:

        * info
            * machine
            * jetpack
            * L4T (Linux for Tegra)
        * hardware
            * TYPE
            * CODENAME
            * SOC
            * CHIP_ID
            * BOARDIDS
            * MODULE
            * BOARD
            * CUDA_ARCH_BIN
            * SERIAL_NUMBER
        * libraries
            * CUDA
            * cuDNN
            * TensorRT
            * VisionWorks
            * OpenCV
            * OpenCV-Cuda
            * VPI
            * Vulkan

        :return: Status board, hardware and libraries
        :rtype: Board
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

        The variable avalables are:

        * **auto** - boolean with fan control.
            * True = Automatic speed control enabled
            * False = Automatic speed control disabled
        * **speed** - Speed set. Value between [0, 100] (float)
        * **measure** - Speed measured. Value between [0, 100] (float)
        * **rpm** - Revolution Per Minute. This number can be 0 if the hardware does not implement this feature
        * **mode** - Mode selected for your fan

        If you want set a new speed, change the mode or know how many configurations are availables you can use:

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

        The access of this properities is available like below

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
        return self._nvp

    @nvpmodel.setter
    def nvpmodel(self, value):
        if self._nvp is None:
            return
        mode = self._nvp.set(value)
        # Do not send messages if nvpmodel is the same
        if mode == self._nvp.id:
            return
        # Send new nvpmodel
        self._controller.put({'nvp': mode})

    @property
    def jetson_clocks(self):
        """
        Status jetson_clocks, if you want change the jetson_clocks status you can simply write:

        .. code-block:: python

            jetson.jetson_clocks = value

        where *value* is a boolean value

        There are availabe other extra properties:

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
        return self._jc

    @jetson_clocks.setter
    def jetson_clocks(self, value):
        if not isinstance(value, bool):
            raise TypeError("Use a boolean")
        if not self._jc.is_config and not value:
            raise JtopException("I cannot set jetson_clocks.\nPlease shutdown manually jetson_clocks")
        # Check if service is not started otherwise skip
        if self._jc.status in ['booting', 'activating', 'deactivating']:
            return
        if value != self._jc.is_alive:
            # Send status jetson_clocks
            self._controller.put({'jc': {'enable': value}})

    @property
    def stats(self):
        """
        This property return a simplified version of tegrastats,
        it is simple to use if you want log the NVIDIA Jetson status with pandas or in a csv file.

        This property is a simplified version of all data collected from your NVIDIA Jetson,
        if you need more detailed information, please use the other jtop properties

        The field listed are:

        * **time** - A `datetime` variable with the local time in your board
        * **uptime** - A `timedelta` with the up time of your board, same from :func:`~jtop.jtop.jtop.uptime`
        * **jetson_clocks** - Status of jetson_clocks, human readable :func:`~jtop.jtop.jtop.jetson_clocks`
        * **nvp model** - If exist, the NV Power Model name active :func:`~jtop.jtop.jtop.nvpmodel`
        * **cpu X** - The status for each cpu in your board, if disabled you will read *OFF*
        * **GPU** - Status of your GPU :func:`~jtop.jtop.jtop.gpu`
        * **MTS FG** - Foreground tasks :func:`~jtop.jtop.jtop.mts`
        * **MTS BG** - Background tasks :func:`~jtop.jtop.jtop.mts`
        * **RAM** - Used ram :func:`~jtop.jtop.jtop.ram`
        * **EMC** - If exist, the used emc :func:`~jtop.jtop.jtop.emc`
        * **IRAM** - If exist, the used iram :func:`~jtop.jtop.jtop.iram`
        * **SWAP** - If exist, the used swap :func:`~jtop.jtop.jtop.swap`
        * **APE** - Frequency APE engine :func:`~jtop.jtop.jtop.engine`
        * **NVENC** - Frequency NVENC engine :func:`~jtop.jtop.jtop.engine`
        * **NVDEC** - Frequency NVDEC engine :func:`~jtop.jtop.jtop.engine`
        * **NVJPG** - Frequency NVJPG engine :func:`~jtop.jtop.jtop.engine`
        * **fan** - Status fan speed :func:`~jtop.jtop.jtop.fan`
        * **Temp X** - X temperature :func:`~jtop.jtop.jtop.temperature`
        * **power cur** - Total current power :func:`~jtop.jtop.jtop.power`
        * **power avg** - Total average power :func:`~jtop.jtop.jtop.power`

        :return: Compacts jetson statistics
        :rtype: dict
        """
        stats = {'time': datetime.now(), 'uptime': self.uptime}
        # -- jetson_clocks --
        if self.jetson_clocks is not None:
            stats['jetson_clocks'] = 'ON' if self.jetson_clocks else 'OFF'
        # -- NV Power Model --
        if self.nvpmodel is not None:
            stats['nvp model'] = self.nvpmodel.name
        # -- CPU --
        for cpu in sorted(self.cpu):
            stats[cpu] = self.cpu[cpu].get('val', 'OFF')
        # -- GPU --
        stats['GPU'] = self.gpu['val']
        # -- MTS --
        if self.mts:
            stats['MTS FG'] = self.mts['fg']
            stats['MTS BG'] = self.mts['bg']
        # -- RAM --
        stats['RAM'] = self.ram['use']
        # -- EMC --
        if self.emc:
            stats['EMC'] = self.ram['use']
        # -- IRAM --
        if self.iram:
            stats['IRAM'] = self.ram['use']
        # -- SWAP --
        if 'use' in self.swap:
            stats['SWAP'] = self.swap['use']
        # -- Engines --
        stats['APE'] = self.engine.ape['val']
        stats['NVENC'] = self.engine.nvenc['val'] if self.engine.nvenc else 'OFF'
        stats['NVDEC'] = self.engine.nvdec['val'] if self.engine.nvdec else 'OFF'
        stats['NVJPG'] = self.engine.nvjpg['rate'] if self.engine.nvjpg else 'OFF'
        if self.engine.msenc:
            stats['MSENC'] = self.engine.msenc
        # -- FAN --
        if self.fan:
            stats['fan'] = self.fan.measure
        # -- Temperature --
        for temp in sorted(self.temperature):
            stats["Temp {name}".format(name=temp)] = self.temperature[temp]
        # -- Power --
        total, _ = self.power
        stats['power cur'] = total['cur']
        stats['power avg'] = total['avg']
        return stats

    @property
    def swap(self):
        """
        SWAP manager and reader

        If you want read the status of your board will return a dictionary with

        * **use** - Amount of SWAP in use
        * **tot** - Total amount of SWAP available for applications
        * **unit** - Unit SWAP, usually in MB
        * **cached**
            * **size** - Cache size
            * **unit** - Unit cache size

        This property has other extra methods show below

            * If you want know how many swap are active you can run this extra method

        .. code-block:: python

            all_swap = jetson.swap.all

        The output will be a dictionary, where for each swap:

                * **used** - Used Swap in kB
                * **size** - Size in kB
                * **type** - Type
                * **prio** - Priority

        * The method inside this property enable a new swap in your board.
          To work need to write a *size* in GB and if you want this swap enable in boot you can set
          *on_boot* on True (default False).
          This method will create a new swap located usually in **"/"** and called **"swfile"**

        .. code-block:: python

            jetson.swap.set(size, on_boot=False)

        * If you want disable the swap created you can run this method

        .. code-block:: python

            jetson.swap.deactivate()

        * This method will show the status of your SWAP created

        .. code-block:: python

            status = jetson.swap.is_enable

        * This method will show the current swap size created

        .. code-block:: python

            size = jetson.swap.size()

        * If you need to clear the cache in your NVIDIA Jetson you can run this extra call

        .. code-block:: python

            jetson.swap.clear_cache()

        :return: swap status
        :rtype: dict
        """
        return self._swap

    @property
    def emc(self):
        """
        EMC is the external memory controller, through which all sysmem/carve-out/GART memory accesses go.

        If your board have the EMC, the fields are:

        * **min_freq** - Minimum frequency in kHz
        * **max_freq** - Maximum frequency in kHz
        * **frq** - Running frequency in kHz
        * **val** - Status EMC, value between [0, 100]
        * **FreqOverride** - Status override

        :return: emc status
        :rtype: dict
        """
        # Extract EMC
        return self._stats.get('emc', {})

    @property
    def iram(self):
        """
        IRAM is memory local to the video hardware engine.
        If your board have the IRAM, the fields are:

        * **use** - status iram used
        * **tot** - Total size IRAM
        * **unit** - Unit size IRAM, usually in kB
        * **lfb** - Largest Free Block (lfb) is a statistic about the memory allocator
            * **size** - Size of the largest free block
            * **unit** - Unit size lfb

        Largest Free Block (lfb) is a statistic about the memory allocator.
        It refers to the largest contiguous block of physical memory
        that can currently be allocated: at most 4 MB.
        It can become smaller with memory fragmentation.
        The physical allocations in virtual memory can be bigger.

        :return: iram status
        :rtype: dict
        """
        # Extract IRAM
        return self._stats.get('iram', {})

    @property
    def ram(self):
        """
        RAM available on your board.

        * **use** - status iram used
        * **shared** - status of shared memory used from GPU
        * **tot** - Total size RAM
        * **unit** - Unit size RAM, usually in kB
        * **lfb** - Largest Free Block (lfb) is a statistic about the memory allocator
            * **nblock** - Number of block used
            * **size** - Size of the largest free block
            * **unit** - Unit size lfb

        Largest Free Block (lfb) is a statistic about the memory allocator.
        It refers to the largest contiguous block of physical memory
        that can currently be allocated: at most 4 MB.
        It can become smaller with memory fragmentation.
        The physical allocations in virtual memory can be bigger.

        :return: ram status
        :rtype: dict
        """
        return self._stats['ram']

    @property
    def mts(self):
        """
        MTS foreground and background tasks.

        If your board support the MTS variable, the output will be:

        * **fg** - foregroundtasks
        * **bg** - background tasks

        :return: mts status
        :rtype: dict
        """
        # Extract MTS
        return self._stats.get('mts', {})

    @property
    def cpu(self):
        """
        CPU status. From this dictionary you can read the status of the CPU.

        For each CPU all fields are:

        * **min_freq** - Minimum frequency in kHz
        * **max_freq** - Maximum frequency in kHz
        * **frq** - Running frequency in kHz
        * **governor** - Governor selected
        * **val** - Status CPU, value between [0, 100]
        * **model** - Model Architecture
        * **IdleStates**

        :return: CPU configuration, frequencies and speed
        :rtype: dict
        """
        # Return CPU status
        return self._stats['cpu']

    @property
    def cluster(self):
        """
        Cluster status of your board.

        If this data is not available in your board will return an empty string

        :return: Status cluster in your board
        :rtype: string
        """
        # Return status cluster
        return self._stats.get('cluster', '')

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
        return self._stats['gpu']

    @property
    def power(self):
        """
        Two power dictionaries:

        * **total** - The total power estimated is not available of the NVIDIA Jetson power comsumption
        * **power** - A dictionary with all power comsumption

        For each power comsumption there are two fields:

        * **avg** - Average power consumption in milliwatts
        * **cur** - Current power consumption in milliwatts

        :return: Two dictionaries, total and a list of all power consumption available from the board
        :rtype: dict, dict
        """
        total = self._stats['power']['all']
        power = self._stats['power']['power']
        return total, power

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

        :return: Local interfaces and hostaname
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
        # -- ENGINES --
        self._engine._update(data['engines'])
        # -- SWAP --
        self._swap._update(data['swap'])
        # -- FAN --
        self._fan._update(data['fan'])
        # -- JETSON_CLOCKS --
        if 'jc' in data:
            self._jc._update(data['jc'])
        # -- NVP Model --
        if 'nvp' in data:
            self._nvp._update(data['nvp'])
        # Set trigger
        self._trigger.set()
        # Notify all observers
        for observer in self._observers:
            # Call all observer in list
            observer(self)

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
            not active or your user does not have the permission to connect to *jetson_stats.service*
        """
        # Connected to broadcaster
        try:
            self._broadcaster.connect()
        except FileNotFoundError as e:
            if e.errno == 2 or e.errno == 111:  # Message error: 'No such file or directory' or 'Connection refused'
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl restart jetson_stats.service")
            elif e.errno == 13:  # Message error: 'Permission denied'
                raise JtopException("I can't access to jetson_stats.service.\nPlease logout or reboot this board.")
            else:
                raise FileNotFoundError(e)
        except ConnectionRefusedError as e:
            if e.errno == 111:  # Connection refused
                # When server is off but socket files exists in /run
                raise JtopException("The jetson_stats.service is not active. Please run:\nsudo systemctl restart jetson_stats.service")
            else:
                raise ConnectionRefusedError(e)
        except PermissionError as e:
            if e.errno == 13:  # Permission denied
                raise JtopException("I can't access to jetson_stats.service.\nPlease logout or reboot this board.")
            else:
                raise PermissionError(e)
        except ValueError:
            # https://stackoverflow.com/questions/54277946/queue-between-python2-and-python3
            raise JtopException("mismatch python version between library and service")
        except AuthenticationError:
            raise JtopException("Authentication mismatch with jetson-stats server")
        # Initialize synchronized data and condition
        self._controller = self._broadcaster.get_queue()
        self._sync_data = self._broadcaster.sync_data()
        self._sync_event = self._broadcaster.sync_event()
        # Initialize connection
        init = self._get_configuration()
        # Load server speed
        self._server_interval = init['interval']
        # Load board information
        self._board._update_init(init['board'])
        # Initialize jetson_clocks sender
        self._swap = Swap(self._controller, init['swap'])
        # Initialize jetson_clock
        if init['jc']:
            self._jc = JetsonClocks(self._controller)
        # Init FAN (If exist)
        self._fan = Fan(self._controller, init['fan'])
        # Init NVP model (if exist)
        if init['nvpmodel']:
            self._nvp = NVPModel()
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
        Speed jtop service. This speed can be different compare the speed specified in :func:`~jtop.jtop.jtop` constructor

        :return: jtop interval (in seconds)
        :rtype: float
        """
        return self._server_interval

    @property
    def interval_user(self):
        """
        This is the same speed specified in :func:`~jtop.jtop.jtop` constructor

        :return: jtop user interval (in seconds)
        :rtype: float
        """
        return self._interval

    def loop_for_ever(self):
        """
        This blocking method is needed when you design your python code to work only by callback.

        Before to run this method remember to attach a callback using :func:`~jtop.jtop.jtop.attach`

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
