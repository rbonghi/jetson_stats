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

import logging
import re
import sys
import json
# from warnings import warn
from datetime import datetime, timedelta
from multiprocessing import Event, AuthenticationError
from threading import Thread
from .service import JtopManager
from .core.hardware import get_platform_variables
from .core.memory import Memory
from .core.fan import Fan
from .core.gpu import GPU
from .core.jetson_clocks import JetsonClocks
from .core.nvpmodel import NVPModel
from .core.common import compare_versions, get_var, get_local_interfaces, status_disk
from .core.jetson_libraries import get_libraries, get_cuda, get_opencv
from .core.exceptions import JtopException
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


class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime):
            return (str(z))
        elif isinstance(z, timedelta):
            return (str(z))
        else:
            return super().default(z)


class jtop(Thread):
    """
    This class control the access to your board, from here you can control your
    NVIDIA Jetson board or read the jetson_clocks status or change the nvp model.
    """

    def __init__(self, interval=1.0):
        """
        When you initialize your jtop you can setup a communication speed **interval**,
        if there is another jtop running this speed will be not used.

        When jtop is started you can read the server speed in **interval** property.

        :param interval: Interval to setup the jtop speed (in seconds), defaults to 1.0
        :type interval: float, optional
        """
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

        #. Switch off, disable on boot **jetson_clocks** and remove configuration file(reference :py:class:`~jtop.core.jetson_clocks.JetsonClocks`)
        #. Set all **fan** to default profile and all speed to zero (reference :py:class:`~jtop.core.fan.Fan`)
        #. Set to default **nvpmodel** (reference :py:class:`~jtop.core.nvpmodel.NVPModel`)
        #. **clear** the configuration jtop file

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    for status, message in jetson.restore():
                        if status:
                            print(message)
                        else:
                            print("Fail")

        :param max_counter: Counter time for each test before fail, defaults to 10
        :type max_counter: int, optional
        :yield: Generator of all operations to restore your NVIDIA Jetson
        :rtype: bool, str
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
            yield counter != max_counter, "jetson_clocks disabled"
            # Disable jetson_clocks on boot
            self.jetson_clocks.boot = False
            # Wait jetson_clocks boot
            counter = 0
            while self.ok() and (counter < max_counter):
                if not self.jetson_clocks.boot:
                    break
                counter += 1
            yield counter != max_counter, "jetson_clocks disabled on boot"
            # Clear configuration
            self.jetson_clocks.clear_config()
            # Wait jetson_clocks clear configuration
            counter = 0
            while self.ok() and (counter < max_counter):
                if not self.jetson_clocks.is_config():
                    break
                counter += 1
            yield counter != max_counter, "clear jetson_clocks configuration file"
        # Reset fan control
        if self.fan is not None:
            # Reset mode fan
            for name in self.fan:
                profile_default = self.fan.get_profile_default(name)
                self.fan.set_profile(name, profile_default)
                counter = 0
                while self.ok() and (counter < max_counter):
                    if self.fan.get_profile(name) == profile_default:
                        break
                    counter += 1
                yield counter != max_counter, "Fan \"{name}\" set to profile \"{profile}\"".format(name=name, profile=profile_default)
            # Reset speed to zero
            for idx in range(len(self.fan[name]['speed'])):
                self.fan.set_speed(name, 0, idx)
                counter = 0
                while self.ok() and (counter < max_counter):
                    if self.fan.get_speed(name, idx) == 0:
                        break
                    counter += 1
                yield counter != max_counter, "Fan \"{name}[{idx}]\" set speed to 0".format(name=name, idx=idx)
        # Set to default nvpmodel
        if self.nvpmodel is not None:
            # Read default value
            default = self.nvpmodel.get_default()
            try:
                self.nvpmodel.set_nvpmodel_id(default['id'])
            except JtopException as ex:
                yield False, ex
            # Wait nvpmodel is default
            counter = 0
            while self.ok() and (counter < max_counter):
                if self.nvpmodel == default['name']:
                    break
                counter += 1
            yield counter != max_counter, "Default nvpmodel[{id}] {name}".format(id=default['id'], name=default['name'])
        # Clear config file
        self._controller.put({'config': 'reset'})
        yield True, "Clear jtop configuration file"

    @property
    def engine(self):
        """
        Engine status, in this property you can find like: APE, DLA, NVDEC, NVENC, and other

        The output of this property is a dictionary:

        * **name group X** - In this group are collected all engines similar
            * **name engine a** - In this key there is a dictionary with engine status
            * **name engine b** - Same like above, there is the dictionary status engine

        For each engine the dictionary is defined like the table below:

        ========== ================ ==============================================
        Name       Type             Description
        ========== ================ ==============================================
        online     :py:class:`bool` Status of the engine
        min        :py:class:`int`  Minimum frequency of the core in **kHz** :sup:`A`
        max        :py:class:`int`  Maximum frequency of the core in **kHz** :sup:`A`
        cur        :py:class:`int`  Current frequency of the core in **kHz**
        ========== ================ ==============================================

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
        Board status, in this property where are available all information about your device.

        The output is a dictionary with 3 keys:

        * **platform**
        * **hardware**
        * **libraries**

        *platform* (If you are running in docker this output is extracted from your **container**)

        ============= ====================================== ====================================================
        Name          Type                                   Description
        ============= ====================================== ====================================================
        Machine       :py:func:`platform.machine`            Mapped output: machine type
        System        :py:func:`platform.system`             Mapped output: Type system
        Distribution  :py:func:`platform.linux_distribution` Mapped output: Linux distribution
        Release       :py:func:`platform.release`            Mapped output: Release kernel
        Python        :py:func:`platform.python_version`     Mapped output: Python version is running jtop
        ============= ====================================== ====================================================

        *hardware* (If you are running in docker this output is extracted from your **host**)

        ===================== ====================================== ====================================================
        Name                  Type                                   Description
        ===================== ====================================== ====================================================
        Model                 :py:class:`str`                        Model name from :code:`/sys/firmware/devicetree/base/model`
        699-level Part Number :py:class:`str`                        699 part number (read reference)
        P-Number              :py:class:`str`                        Part number (read reference)
        BoardIDs              :py:class:`str`                        *(Optional)* Board ID in :code:`/proc/device-tree/nvidia,boardids`
        Module                :py:class:`str`                        Conversion from P-Number to Module name
        SoC                   :py:class:`str`                        System on Chip :code:`/proc/device-tree/compatible`
        CUDA Arch BIN         :py:class:`str`                        Cuda Architecture
        Codename              :py:class:`str`                        *(Optional)* Codename architecture
        Serial Number         :py:class:`str`                        Serial Number board :code:`/sys/firmware/devicetree/base/serial-number`
        L4T                   :py:class:`str`                        Linux 4 Tegra :sup:`A`
        Jetpack               :py:class:`str`                        From L4T is evaluated the Jetpack running on your NVIDIA Jetson
        ===================== ====================================== ====================================================

        *libraries* (If you are running in docker this output is extracted from your **container**)

        ===================== ====================================== ====================================================
        Name                  Type                                   Description
        ===================== ====================================== ====================================================
        CUDA                  :py:class:`str`                        CUDA version :sup:`B`
        OpenCV                :py:class:`str`                        OpenCV version use :code:`opencv_version`
        OpenCV-Cuda           :py:class:`bool`                       Check running :code:`opencv_version --verbose`
        cuDNN                 :py:class:`str`                        Check and read the version with :code:`dpkg -l`
        TensorRT              :py:class:`str`                        Check and read the version with :code:`dpkg -l`
        VPI                   :py:class:`str`                        Check and read the version with :code:`dpkg -l`
        Vulkan                :py:class:`str`                        Run and read :code:`which vulkaninfo`
        ===================== ====================================== ====================================================

        .. note::

            Note **A**
                The Linux For Tegra (L4T) is extracted in two ways:
                    1. Reading :code:`/etc/nv_tegra_release`
                    2. Reading version in **nvidia-l4t-core** package

            Note **B**
                The CUDA version is read depend of the version in:
                    1. On :code:`/usr/local/cuda/version.txt`
                    2. Running :code:`nvcc --version`

        .. admonition:: Reference

            #. `699 Part number - Before Jetpack 5 <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3243/index.html>`_
            #. `699 Part number - After Jetpack 5 <https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/HR/JetsonEepromLayout.html>`_

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
        Fan status and control. This property show speed, rpm and control every fan on your board

        The :py:class:`~jtop.core.fan.Fan` class is readable such a :py:class:`dict` where for each key are colleted all metrics for each Fan.

        ============= =================== ====================================================
        Name          Type                Description
        ============= =================== ====================================================
        speed         :py:class:`list`    List of speed between [0, 100]
        rpm           :py:class:`list`    *(Optional)* List of RPM for each fan
        profile       :py:class:`str`     Fan Profile, read :py:func:`~jtop.core.fan.Fan.all_profiles()`
        governor      :py:class:`str`     (Jetson with JP5+) Governor fan
        control       :py:class:`str`     (Jetson with JP5+) Type of controller
        ============= =================== ====================================================

        If you are working with Jetpack 5 or higher, the fan profile map nvfancontrol `nvfancontrol <https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#fan-profile-control>`_

        you can also control your fan with:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Print profile
                    print(jetson.fan.profile)
                    # Set new profile
                    jetson.fan.profile = 'quiet'
                    # Read speed
                    print(jetson.fan.speed)
                    # Set new speed
                    jetson.fan.speed = 90

        Full documentation on :py:class:`~jtop.core.fan.Fan`

        :return: Status Fan
        :rtype: Fan
        :raises JtopException: Wrong speed fan name, profile or speed
        """  # noqa
        return self._fan

    @property
    def nvpmodel(self):
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

        Advanced features are available in :py:class:`~jtop.core.nvpmodel.NVPModel`

        .. admonition:: Reference

            #. `NVP Model - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/Tegra%20Linux%20Driver%20Package%20Development%20Guide/power_management_tx2.html#wwpID0E0AM0HA>`_
            #. `NVP Model - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html#supported-modes-and-power-efficiency>`_
            #. `NVP Model - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#supported-modes-and-power-efficiency>`_

        :return: Return the name of NV Power Mode
        :rtype: NVPModel or None
        :raises JtopException: if the nvp model does not exist
        """  # noqa
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
        jetson_clocks is a tool provided for all NVIDIA Jetson to maximize all performance, read reference for more information.

        You can use this attribute like a simple boolean or use the advanced features in :py:class:`~jtop.core.jetson_clocks.JetsonClocks`

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Change status jetson_clocks
                    jetson.jetson_clocks = not jetson.jetson_clocks
                    # Set on board boot
                    jetson.jetson_clocks.boot = True
                    # Read status jetson_clocks service
                    print(jetson.jetson_clocks.status)

        .. admonition:: Reference

            #. `jetson_clocks - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/index.html#page/Tegra%2520Linux%2520Driver%2520Package%2520Development%2520Guide%2Fpower_management_tx2.html%23>`_
            #. `jetson_clocks - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html>`_
            #. `jetson_clocks - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#maximizing-jetson-orin-performance>`_

        :return: status jetson_clocks script
        :rtype: JetsonClocks or None
        :raises ValueError: Wrong jetson_clocks value
        """  # noqa
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

        ============= ============================== ========================= ====================================================
        Name          Type                           Reference                 Description
        ============= ============================== ========================= ====================================================
        time          :py:class:`datetime.datetime`                            local time in your board
        uptime        :py:class:`datetime.timedelta` :py:attr:`~uptime`        up time on your board
        cpu **X**     :py:class:`float`              :py:attr:`~cpu`           The status for each cpu in your board, if disabled *OFF*
        RAM           :py:class:`float`              :py:attr:`~memory`        RAM used / total
        SWAP          :py:class:`float`              :py:attr:`~memory`        SWAP used / total
        EMC           :py:class:`float`              :py:attr:`~memory`        *(Optional)* EMC Percentage of bandwidth
        IRAM          :py:class:`float`              :py:attr:`~memory`        *(Optional)* IRAM used / total
        GPU           :py:class:`float`              :py:attr:`~gpu`           *(Optional)* Status of your GPU
        engine **X**  :py:class:`float`              :py:attr:`~engine`        *(Optional)* Frequency for each engine, if disabled *OFF*
        fan           :py:class:`float`              :py:attr:`~fan`           *(Optional)* Fan speed
        Temp **X**    :py:class:`float`              :py:attr:`~power`         *(Optional)* Current power from rail X
        Temp **TOT**  :py:class:`float`              :py:attr:`~power`         *(Optional)* Total power
        jetson_clocks :py:class:`str`                :py:attr:`~jetson_clocks` *(Optional)* Status of jetson_clocks, human readable
        nvpmodel      :py:class:`str`                :py:attr:`~nvpmodel`      *(Optional)* NV Power Model name active
        ============= ============================== ========================= ====================================================

        :return: Compacts jetson statistics
        :rtype: dict
        """
        stats = {'time': datetime.now(), 'uptime': self.uptime}
        # -- CPU --
        for idx, cpu in enumerate(self.cpu['cpu']):
            stats["CPU{idx}".format(idx=idx + 1)] = 100 - int(cpu['idle']) if cpu['online'] else 'OFF'
        # -- MEMORY --
        tot_ram = self.memory['RAM']['tot']
        stats['RAM'] = self.memory['RAM']['used'] / tot_ram if tot_ram > 0 else 0
        tot_swap = self.memory['SWAP']['tot']
        stats['SWAP'] = self.memory['SWAP']['used'] / tot_swap if tot_swap > 0 else 0
        if 'EMC' in self.memory:
            stats['EMC'] = self.memory['EMC']['val']
        if 'IRAM' in self.memory:
            tot_iram = self.memory['IRAM']['tot']
            stats['IRAM'] = float(self.memory['IRAM']['used']) / tot_iram if tot_iram > 0 else 0
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
                stats["Power {name}".format(name=name)] = rail['power']
            # Load total current power
            stats['Power TOT'] = self.power['tot']['power']
        # -- jetson_clocks --
        if self.jetson_clocks is not None:
            stats['jetson_clocks'] = 'ON' if self.jetson_clocks else 'OFF'
        # -- NV Power Model --
        if self.nvpmodel is not None:
            stats['nvp model'] = self.nvpmodel.name
        return stats

    def json(self, stats=False, **json_args):
        """
        This method export all metrics in a `json` readable output.

        You can export all metrics or the same output in :py:attr:`stats` depending of the parameter input.

        :param stats: json with same output of :py:attr:`stats`, defaults to False
        :type stats: bool, optional
        :param json_args: additional keyword arguments passed to json.dumps
        :type json_args: Any
        :return: json output requested
        :rtype: str
        """
        if stats:
            json_args.setdefault("cls", DateTimeEncoder)
            return json.dumps(self.stats, **json_args)
        # Read all variable and build a complete json
        return json.dumps(self._stats, **json_args)

    @property
    def memory(self):
        """
        This property show in a simple way all memories available, the main output is available in this way:

        * **RAM** - It is a dictionary with all information about RAM :sup:`A`
        * **SWAP** - It is a dictionary with all information about SWAP
        * **EMC** - It is a dictionary with EMC data, not in all boards this data is available
        * **IRAM** - It is a dictionary with SWAP data, not in all boards this data is available

        You can also use this property to set a new swap, deactivate or clear cache,
        read all methods available :py:class:`~jtop.core.memory.Memory`

        example:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # Print memory status
                    print(jetson.memory)
                    # make a new 10Gb swap
                    jetson.memory.swap_set(10, on_boot=False)


        For each dictionary there are specific outputs

        *RAM* :sup:`A`

        ========== =================== ====================================================
        Name       Type                Description
        ========== =================== ====================================================
        tot        :py:class:`int`     Total RAM in **KB**
        used       :py:class:`int`     Total used RAM in **KB**
        free       :py:class:`int`     Free RAM in **KB**
        buffers    :py:class:`int`     Buffered RAM in **KB**
        cached     :py:class:`int`     Cached RAM in **KB**
        shared     :py:class:`int`     Shared RAM in **KB**, for NVIDIA Jetson the RAM used from GPU
        lfb        :py:class:`int`     Large Free Block in **4MB**
        ========== =================== ====================================================

        *SWAP*

        ========== =================== ====================================================
        Name       Type                Description
        ========== =================== ====================================================
        tot        :py:class:`int`     Total SWAP in **KB**
        used       :py:class:`int`     Total used SWAP in **KB**
        cached     :py:class:`int`     Cached RAM in **KB**
        table      :py:class:`dict`    Dictionary with all swap available :sup:`B`
        ========== =================== ====================================================

        *EMC* (if available on your device)

        ========== =================== ====================================================
        Name       Type                Description
        ========== =================== ====================================================
        online     :py:class:`bool`    Status EMC
        val        :py:class:`int`     Percentage of bandwidth used relative to running frequency
        cur        :py:class:`int`     Current working frequency in **kHz**
        max        :py:class:`int`     Max EMC frequency usable in **kHz**
        min        :py:class:`int`     Min EMC frequency usable in **kHz**
        ========== =================== ====================================================

        *IRAM* (if available on your device)

        ========== =================== ====================================================
        Name       Type                Description
        ========== =================== ====================================================
        tot        :py:class:`int`     Total IRAM in **KB**
        used       :py:class:`int`     Total used IRAM in **KB**
        lfb        :py:class:`int`     Large Free Block in **4MB**
        ========== =================== ====================================================

        .. note::

            Note **A**
                The RAM is measured reading the file :code:`/proc/meminfo` for each field is read:

                ========== ====================================================
                Name       Description
                ========== ====================================================
                tot        :code:`MemTotal`
                used       :code:`MemTotal - (Buffers + Cached)`
                free       :code:`MemFree`
                buffers    :code:`Buffers`
                cached     :code:`Cached + SReclaimable`
                ========== ====================================================

            Note **B**
                The swap table is a list of dictionary with this data

                ========== =================== ==============================================
                Name       Type                Description
                ========== =================== ==============================================
                type       :py:class:`str`     Type of partition
                prio       :py:class:`int`     Priority partition
                size       :py:class:`int`     Size partition in **KB**
                used       :py:class:`int`     Used part of this partition in **KB**
                boot       :py:class:`bool`    Check if this swap start on boot
                ========== =================== ==============================================

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

        ========== ================= =======================================
        Name       Type              Description
        ========== ================= =======================================
        online     :py:class:`bool`  Status core
        governor   :py:class:`str`   Type of governor running on the core
        freq       :py:class:`dict`  Frequency of the core :sup:`A`
        info_freq  :py:class:`dict`  Frequency of the core :sup:`A`
        idle_state :py:class:`dict`  All Idle state running
        user       :py:class:`float` User percentage utilization :sup:`B`
        nice       :py:class:`float` Nice percentage utilization :sup:`B`
        system     :py:class:`float` System percentage utilization :sup:`B`
        idle       :py:class:`float` Idle percentage :sup:`B`
        model      :py:class:`str`   Model core running
        ========== ================= =======================================

        .. note::

            Note **A**
                The frequency dictionary is defined like below:

                ========== =================== ==============================================
                Name       Type                Description
                ========== =================== ==============================================
                min        :py:class:`int`     Minimum frequency of the core in **kHz**
                max        :py:class:`int`     Maximum frequency of the core in **kHz**
                cur        :py:class:`int`     Current frequency of the core in **kHz**
                ========== =================== ==============================================

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
        Return a list with all processing running in GPU.

        For each item are collected all information about the process.

        ========== ================= =======================================
        Item       Type              Description
        ========== ================= =======================================
        0          :py:class:`int`   PID process running
        1          :py:class:`str`   User start the process
        2          :py:class:`str`   GPU used :sup:`E`
        3          :py:class:`str`   Type of process :sup:`F`
        4          :py:class:`int`   Priority
        5          :py:class:`str`   State process :sup:`A`
        6          :py:class:`float` CPU percent utilization :sup:`B`
        7          :py:class:`int`   Memory occupied :sup:`C`
        8          :py:class:`int`   GPU Memory occupied :sup:`D`
        9          :py:class:`str`   Process name
        ========== ================= =======================================

        .. note::

            Note **A**
                This field indicating the status process:
                    * **R**  Running
                    * **S**  Sleeping in an interruptible wait
                    * **D**  Waiting in uninterruptible disk sleep
                    * **Z**  Zombie
                    * **T**  Stopped (on a signal)
                    * **t**  Tracing stop
                    * **X**  Dead

            Note **B**
                Measure the CPU percent utilization are read live the values from :code:`/proc/[PID]/stat`:
                    * **#14 utime** - CPU time spent in user code, measured in *clock ticks*
                    * **#15 stime** - CPU time spent in kernel code, measured in *clock ticks*
                    * **#22 starttime** - Time when the process started, measured in *clock ticks*

                Where *clock ticks* is `SC_CLK_TCK <http://pubs.opengroup.org/onlinepubs/009695399/utilities/getconf.html>`_

                It is also used :code:`/proc/uptime` to know the system up time.

                The CPU percent is:

                .. code-block:: python
                    :class: no-copybutton

                        total_time = utime + stime
                        total_time = uptime - (starttime / clock_ticks)
                        cpu_usage = 100 * (total_time / clock_ticks)

            Note **C**
                Extract resident set size (VmRSS) (Second field) in :code:`/proc/[PID]/statm`:
                    VmRSS is the resident set size of the process,
                    which is the portion of the process's memory that is held in RAM and is not swapped out to disk.
                    This is the amount of memory that the process is currently using.

            Note **D**
                This value is the GPU memory occupied from the process.

            Note **E**
                GPU used:
                    * **I**: Integrated GPU
                    * **dX**: Discrete GPU with number graphic card (next release)

            Note **F**
                Type of process:
                    * **Graphic**: Graphic process
                    * **System**: System process (next release)

        .. admonition:: Reference

            #. https://man7.org/linux/man-pages/man5/proc.5.html

        :return: list of all GPU processes
        :rtype: list
        """
        return self._stats['processes']

    @property
    def gpu(self):
        """
        This property show in a simple way all GPU available on your board.

        You can also use this attribute to enable/disable 3D scaling:

        .. code-block:: python

            with jtop() as jetson:
                if jetson.ok():
                    # change 3D scaling status
                    jetson.gpu.set_scaling_3D = not jetson.gpu.set_scaling_3D

        The :py:class:`~jtop.core.gpu.GPU` class is readable such a :py:class:`dict` where for each key are colleted all metrics for each GPU.

        ============= =================== ====================================================
        Name          Type                Description
        ============= =================== ====================================================
        type          :py:class:`str`     Type of GPU (integrated, discrete)
        status        :py:class:`dict`    Status of GPU :sup:`A`
        freq          :py:class:`dict`    Frequency GPU :sup:`B`
        power_control :py:class:`dict`    *(Optional)* Type of power control
        ============= =================== ====================================================

        .. note::

            Note **A**
                Status GPU, from current load to features

                =========== =================== ==============================================
                Name        Type                Description
                =========== =================== ==============================================
                railgate    :py:class:`bool`    Status Railgate
                tpc_pg_mask :py:class:`bool`    Status TPC PG Mask (for NVP model)
                3d_scaling  :py:class:`bool`    Status 3D scaling
                load        :py:class:`float`   Current GPU load
                =========== =================== ==============================================

            Note **B**
                The frequency dictionary is defined like below:

                ========== =================== ==============================================
                Name       Type                Description
                ========== =================== ==============================================
                governor   :py:class:`str`     Name GPU governor
                min        :py:class:`int`     Minimum GPU frequency in **kHz**
                max        :py:class:`int`     Maximum GPU frequency in **kHz**
                cur        :py:class:`int`     Current GPU frequency in **kHz**
                GPC        :py:class:`list`    List GPC frequency in **kHz** (Available for Orin series)
                ========== =================== ==============================================

        :return: current status of your GPU.
        :rtype: GPU
        """
        # Extract GPU
        return self._gpu

    @property
    def power(self):
        """
        All NVIDIA Jetson have one ore more integrate three-channel `INA3221 <https://www.ti.com/product/INA3221>`_ to measure the power consumption.

        This jtop attribute collect and show the output from each rail in a simple view.

        ============= =================== ====================================================
        Name          Type                Description
        ============= =================== ====================================================
        rail          :py:class:`dict`    A dictionary with all thermal rails
        tot           :py:class:`dict`    Total estimate board power
        ============= =================== ====================================================

        The total power is the **sum of all rails** or

        * Jetson Xavier NX and Jetson Orin NX - `Output VDD_IN <https://forums.developer.nvidia.com/t/orin-nx-power-data-from-jtop/242804/5>`_
        * Jetson Nano - `Output POM_5V_IN <https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8>`_

        For each rail there are different values available

        ============= =================== ====================================================
        Name          Type                Description
        ============= =================== ====================================================
        online        :py:class:`bool`    If sensor is online
        type          :py:class:`str`     Type of sensors (For NVIDIA Jetson is INA3221)
        status        :py:class:`str`     *(if available)* Status sensor
        volt          :py:class:`int`     Gets rail voltage in millivolts
        curr          :py:class:`int`     Gets rail current in milliamperes
        power         :py:class:`int`     Gets rail power in milliwatt
        avg           :py:class:`int`     Gets rail power average in milliwatt
        warn          :py:class:`int`     *(if available)* Gets rail average current limit in milliamperes
        crit          :py:class:`int`     *(if available)* Gets rail instantaneous current limit in milliamperes
        ============= =================== ====================================================

        .. admonition:: Reference

            #. `Power Consumption - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/Tegra%20Linux%20Driver%20Package%20Development%20Guide/power_management_tx2.html#wwpID0E0EE0HA>`_
            #. `Power Consumption - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html#software-based-power-consumption-modeling>`_
            #. `Power Consumption - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#software-based-power-consumption-modeling>`_
            #. `INA3221 datasheet <https://www.ti.com/product/INA3221>`_

        :return: A dictionary with a list of power and the total
        :rtype: dict
        """  # noqa
        return self._stats['power']

    @property
    def temperature(self):
        """
        BSP thermal management features are part of the firmware running on BPMP for Jetson platforms running any host operating system (host OS) on the CPU.

        this attribute provide a dictionary with a list of all thermal rail available on your board.

        All temperatures are in Celsius

        ============= =================== ====================================================
        Name          Type                Description
        ============= =================== ====================================================
        online        :py:class:`bool`    If sensor is online
        temp          :py:class:`int`     Gets rail voltage in Celsius. *(If offline show -256)*
        max           :py:class:`int`     *(if available)* Gets rail average current limit in Celsius
        crit          :py:class:`int`     *(if available)* Gets rail instantaneous current limit in Celsius
        ============= =================== ====================================================

        .. note::

            all measures are with a 0.5 °C precision margin

        Not all values are available, jtop hide some values usually not available:

        * **PMIC** - For NVIDIA Jetson TX/Nano

        .. admonition:: Reference

            #. `Thermal specification - Jetson TX/Nano <https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-283/Tegra%20Linux%20Driver%20Package%20Development%20Guide/power_management_tx2.html#wwpID0E0IH0HA>`_
            #. `Thermal specification - Jetson Xavier <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonXavierNxSeriesAndJetsonAgxXavierSeries.html#thermal-management-in-bpmp>`_
            #. `Thermal specification - Jetson Orin <https://docs.nvidia.com/jetson/archives/r35.2.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#thermal-management-in-bpmp>`_

        :return: Temperature dictionary
        :rtype: dict
        """  # noqa
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
        * **used** - Disk space used in GB
        * **available_no_root**

        :return: Disk information
        :rtype: dict
        """
        return status_disk()

    @property
    def uptime(self):
        """
        Up time, The time since the board is turned on.

        This command read the value in :code:`/proc/uptime` .

        :return: Board up time
        :rtype: datetime.timedelta
        """
        return timedelta(seconds=self._stats['uptime'])

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
                self._get_data()
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
        # Decode and update all jtop data
        self._stats = data
        # -- GPU --
        self._gpu._update(self._stats['gpu'])
        # -- MEMORY --
        self._memory._update(self._stats['mem'])
        # -- FAN --
        self._fan._update(self._stats['fan'])
        # -- JETSON_CLOCKS --
        if 'jc' in self._stats:
            self._jetson_clocks._update(self._stats['jc'])
        # -- NVP Model --
        if 'nvp' in self._stats:
            self._nvpmodel._update(self._stats['nvp'])
        # Set trigger
        self._trigger.set()
        # Notify all observers
        for observer in self._observers:
            # Call all observer in list
            observer(self)

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
        # Check version compatibility between client and server raise exception only if minor version is different
        if not compare_versions(service_version, get_var(VERSION_RE)):
            raise JtopException("""Mismatch version jtop service: [{service_version}] and client: [{client_version}]. Please run:\n
sudo systemctl restart jtop.service""".format(
                service_version=service_version,
                client_version=get_var(VERSION_RE)))
        # Load server speed
        self._server_interval = init['interval']
        # Load board information
        self._board['hardware'] = init['board']['hardware']
        # Initialize gpu controller
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
        self._get_data()
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

        :param spin: If True, this function will be not blocking, defaults to False
        :type spin: bool, optional
        :raises ex_value: if jtop client fail, will be raise here
        :return: status jtop client
        :rtype: bool
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
        This method close the jtop server.

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
