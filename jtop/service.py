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

# Logging
import logging
# Operative system
# import signal
import copy
import os
import sys
import stat
from grp import getgrnam
from multiprocessing import Process, Queue, Event, Value
from multiprocessing.managers import SyncManager
# jetson_stats imports
from .core import (
    cpu_models,
    nvjpg,
    MemoryService,
    JtopException,
    Tegrastats,
    JetsonClocksService,
    Config,
    NVPModelService,
    FanService,
    SwapService,
    get_key,
    import_os_variables)
# Create logger for tegrastats
logger = logging.getLogger(__name__)
# Load queue library for python 2 and python 3
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
try:
    import queue
except ImportError:
    import Queue as queue

PATH_TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']
PATH_JETSON_CLOCKS = ['/usr/bin/jetson_clocks', '/home/nvidia/jetson_clocks.sh']
PATH_FAN = ['/sys/kernel/debug/tegra_fan', '/sys/devices/pwm-fan']
PATH_NVPMODEL = ['nvpmodel']
# Pipe configuration
# https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s13.html
# https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard
JTOP_PIPE = '/run/jtop.sock'
JTOP_USER = 'jetson_stats'
# Gain timeout lost connection
TIMEOUT_GAIN = 3
TIMEOUT_SWITCHOFF = 3.0
LIST_PRINT = ['CPU', 'MTS', 'RAM', 'IRAM', 'SWAP', 'EMC', 'GR3D', 'TEMP', 'WATT', 'FAN', 'APE', 'NVENC', 'NVDEC', 'MSENC']


def import_jetson_variables():
    JTOP_FOLDER, _ = os.path.split(__file__)
    return import_os_variables(JTOP_FOLDER + "/jetson_variables", "JETSON_")


def load_jetson_variables():
    env = {}
    for k, v in import_jetson_variables().items():
        env[k] = str(v)
    # Make dictionaries
    info = {
        "machine": env["JETSON_MACHINE"],
        "jetpack": env["JETSON_JETPACK"],
        "L4T": env["JETSON_L4T"]}
    hardware = {
        "TYPE": env["JETSON_TYPE"],
        "CODENAME": env["JETSON_CODENAME"],
        "SOC": env["JETSON_SOC"],
        "CHIP_ID": env["JETSON_CHIP_ID"],
        "BOARDIDS": env["JETSON_BOARDIDS"],
        "MODULE": env["JETSON_MODULE"],
        "BOARD": env["JETSON_BOARD"],
        "CUDA_ARCH_BIN": env["JETSON_CUDA_ARCH_BIN"],
        "SERIAL_NUMBER": env["JETSON_SERIAL_NUMBER"].upper()}
    # Board information
    return {'info': info, 'hardware': hardware}


class JtopManager(SyncManager):

    def __init__(self, authkey=None):
        if authkey is None:
            authkey = get_key().encode("utf-8")
        super(JtopManager, self).__init__(address=(JTOP_PIPE), authkey=authkey)

    def get_queue(self):
        pass

    def sync_data(self):
        pass

    def sync_event(self):
        pass


class JtopServer(Process):
    """
        - https://pymotw.com/2/multiprocessing/basics.html
        - https://pymotw.com/2/multiprocessing/communication.html
        - https://stackoverflow.com/questions/1829116/how-to-share-variables-across-scripts-in-python
        - https://stackoverflow.com/questions/45342200/how-to-use-syncmanager-lock-or-event-correctly
        - https://stackoverflow.com/questions/2545961/how-to-synchronize-a-python-dict-with-multiprocessing
        - https://docs.python.org/2.7/reference/datamodel.html
    """

    def __init__(self, force=False, path_tegrastats=PATH_TEGRASTATS, path_jetson_clocks=PATH_JETSON_CLOCKS, path_fan=PATH_FAN, path_nvpmodel=PATH_NVPMODEL):
        self.force = force
        # Check if running a root
        if os.getuid() != 0:
            raise JtopException("jtop service need sudo to work")
        # Load configuration
        self.config = Config()
        # Error queue
        self._error = Queue()
        # Command queue
        self.q = Queue()
        # Speed interval
        self.interval = Value('d', -1.0)
        # Dictionary to sync
        self.data = {}
        # Event lock
        self.event = Event()
        # Load super Thread constructor
        super(JtopServer, self).__init__()
        # Register stats
        # https://docs.python.org/2/library/multiprocessing.html#using-a-remote-manager
        JtopManager.register('get_queue', callable=lambda: self.q)
        JtopManager.register("sync_data", callable=lambda: self.data)
        JtopManager.register('sync_event', callable=lambda: self.event)
        # Generate key and open broadcaster
        self.broadcaster = JtopManager()
        # Load board information
        self.board = load_jetson_variables()
        # Initialize Fan
        self.fan = FanService(self.config, path_fan)
        # Initialize jetson_clocks controller
        try:
            self.jetson_clocks = JetsonClocksService(self.config, self.fan, path_jetson_clocks)
        except JtopException as error:
            logger.warning("{error} in paths {path}".format(error=error, path=path_nvpmodel))
            self.jetson_clocks = None
        # Initialize nvpmodel controller
        try:
            self.nvpmodel = NVPModelService(self.jetson_clocks, nvp_model=path_nvpmodel)
        except JtopException as error:
            logger.warning("{error} in paths {path}".format(error=error, path=path_nvpmodel))
            self.nvpmodel = None
        # Setup memory servive
        self.memory = MemoryService()
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats, path_tegrastats)
        # Swap manager
        self.swap = SwapService(self.config)

    def run(self):
        # Read nvp_mode
        if self.nvpmodel is not None:
            self.nvp_mode = self.nvpmodel.get()
        # Run setup
        if self.jetson_clocks is not None:
            self.jetson_clocks.initialization(self.nvpmodel)
        # Initialize jetson_fan
        self.fan.initialization(self.jetson_clocks)
        # Initialize variables
        timeout = None
        interval = 1
        try:
            while True:
                try:
                    # Decode control message
                    control = self.q.get(timeout=timeout)
                    # Check if the configuration exist
                    if self.jetson_clocks:
                        if not self.jetson_clocks.is_config():
                            if not self.jetson_clocks.alive(wait=False):
                                self.jetson_clocks.store()
                    # Check if control is not empty
                    if not control:
                        continue
                    # If service read the same init message resend it
                    if 'init' in control:
                        self.q.put(control)
                        continue
                    logger.debug("control message {control}".format(control=control))
                    # Manage swap
                    if 'swap' in control:
                        swap = control['swap']
                        if swap:
                            self.swap.set(swap['size'], swap['boot'])
                        else:
                            self.swap.deactivate()
                    # Manage jetson_clocks
                    if 'config' in control:
                        command = control['config']
                        if command == 'reset':
                            logger.info('Reset configuration')
                            self.config.clear()
                            if self.jetson_clocks is not None:
                                logger.info('Remove jetson_clocks config')
                                self.jetson_clocks.clear()
                    if 'jc' in control:
                        jc = control['jc']
                        # Enable / disable jetson_clocks
                        if 'enable' in jc:
                            self.jetson_clocks.set(jc['enable'])
                        # Update jetson_clocks configuration
                        if 'boot' in jc:
                            self.jetson_clocks.boot = jc['boot']
                    # Speed Fan and configuration
                    if 'fan' in control:
                        fan = control['fan']
                        for key, value in fan.items():
                            logger.info('Fan config {} {}'.format(key, value))
                            if key == 'mode':
                                self.fan.mode = value
                            elif key == 'speed':
                                self.fan.speed = value
                    # Decode nvp model
                    if 'nvp' in control:
                        mode = control['nvp']
                        logger.info("Set new NV Power Mode {mode}".format(mode=mode))
                        # Set new NV Power Mode
                        self.nvpmodel.set(mode)
                    if 'memory' in control:
                        logger.info("Clear cache")
                        # Clear cache
                        self.swap.clear_cache()
                    # Initialize tegrastats speed
                    if 'interval' in control:
                        interval = control['interval']
                        # Run stats
                        if self.tegra.open(interval=interval):
                            # Start jetson_clocks
                            if self.jetson_clocks is not None:
                                self.jetson_clocks.start(interval)
                            # Set interval value
                            self.interval.value = interval
                            # Status start tegrastats
                            logger.info("tegrastats started {interval}ms".format(interval=int(interval * 1000)))
                        # send configuration board
                        init = {
                            'board': self.board,
                            'interval': self.interval.value,
                            'swap': self.swap.path,
                            'fan': self.fan.get_configs(),
                            'jc': self.jetson_clocks is not None,
                            'nvpmodel': self.nvpmodel is not None}
                        self.q.put({'init': init})
                    # Update timeout interval
                    timeout = TIMEOUT_GAIN if interval <= TIMEOUT_GAIN else interval * TIMEOUT_GAIN
                except queue.Empty:
                    self.sync_event.clear()
                    # Close and log status
                    if self.tegra.close():
                        logger.info("tegrastats close")
                        # Start jetson_clocks
                        if self.jetson_clocks is not None:
                            self.jetson_clocks.stop()
                            logger.info("jetson_clocks show closed")
                    # Disable timeout
                    timeout = None
                    self.interval.value = -1.0
        except (KeyboardInterrupt, SystemExit):
            pass
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Error subprocess {error}".format(error=e), exc_info=1)
            # Write error messag
            self._error.put(sys.exc_info())
        finally:
            # Close tegra
            if self.tegra.close(timeout=TIMEOUT_SWITCHOFF):
                logger.info("Force tegrastats close")
                # Start jetson_clocks
                if self.jetson_clocks is not None:
                    self.jetson_clocks.close()

    def start(self):
        # Initialize socket
        try:
            gid = getgrnam(JTOP_USER).gr_gid
        except KeyError:
            # User does not exist
            raise JtopException("Group {jtop_user} does not exist!".format(jtop_user=JTOP_USER))
        # Remove old pipes if exists
        if os.path.exists(JTOP_PIPE):
            if self.force:
                logger.info("Remove pipe {pipe}".format(pipe=JTOP_PIPE))
                os.remove(JTOP_PIPE)
            else:
                raise JtopException("Service already active! Please check before run it again")
        # Start broadcaster
        try:
            self.broadcaster.start()
        except EOFError:
            raise JtopException("Server already alive")
        # Initialize synchronized data and conditional
        self.sync_data = self.broadcaster.sync_data()
        self.sync_event = self.broadcaster.sync_event()
        # Change owner
        os.chown(JTOP_PIPE, os.getuid(), gid)
        # Change mode cotroller and stats
        # https://www.tutorialspoint.com/python/os_chmod.htm
        # Equivalent permission 660 srw-rw----
        os.chmod(JTOP_PIPE, stat.S_IREAD | stat.S_IWRITE | stat.S_IWGRP | stat.S_IRGRP)
        # Run the Control server
        super(JtopServer, self).start()

    def loop_for_ever(self):
        try:
            self.start()
        except JtopException as e:
            logger.error(e)
            return
        # Join main subprocess
        try:
            self.join()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            # Close communication
            self.close()

    def close(self):
        self.q.close()
        self.broadcaster.shutdown()
        # If process is alive wait to quit
        # logger.debug("Status subprocess {status}".format(status=self.is_alive()))
        while self.is_alive():
            # If process is in timeout manually terminate
            if self.interval.value == -1.0:
                logger.info("Terminate subprocess")
                self.terminate()
            logger.info("Wait shutdown subprocess")
            self.join(timeout=TIMEOUT_SWITCHOFF)
            self.interval.value = -1.0
        # Close tegrastats
        try:
            error = self._error.get(timeout=0.5)
            # Raise error if exist
            if error:
                ex_type, ex_value, tb_str = error
                ex_value.__traceback__ = tb_str
                raise ex_value
        except queue.Empty:
            pass
        self.remove_files()
        # Close stats server
        logger.info("Service closed")
        return True

    def remove_files(self):
        # If exist remove pipe
        if os.path.exists(JTOP_PIPE):
            logger.info("Remove pipe {pipe}".format(pipe=JTOP_PIPE))
            os.remove(JTOP_PIPE)

    def _total_power(self, power):
        """
        Private function to measure the total watt

        :return: Total power and a second dictionary with all other measures
        :rtype: dict, dict
        """
        # In according with:
        # https://forums.developer.nvidia.com/t/power-consumption-monitoring/73608/8
        # https://github.com/rbonghi/jetson_stats/issues/51
        total_name = ""
        for val in power:
            if "IN" in val:
                total_name = val
                break
        # Extract the total from list
        # Otherwise sum all values
        # Example for Jetson Xavier
        # https://forums.developer.nvidia.com/t/xavier-jetson-total-power-consumption/81016
        if total_name:
            total = power[total_name]
            del power[total_name]
            return total, power
        # Otherwise measure all total power
        total = {'cur': 0, 'avg': 0}
        for value in power.values():
            total['cur'] += value['cur']
            total['avg'] += value['avg']
        return total, power

    def tegra_stats(self, tegrastats):
        # Make configuration dict
        # logger.debug("tegrastats read")
        data = {}
        jetson_clocks_show = copy.deepcopy(self.jetson_clocks.show()) if self.jetson_clocks is not None else {}
        # -- Engines --
        nvjpg_data = nvjpg()
        data['engines'] = {
            'APE': tegrastats['APE'],
            'NVENC': tegrastats['NVENC'] if 'NVENC' in tegrastats else {},
            'NVDEC': tegrastats['NVDEC'] if 'NVDEC' in tegrastats else {},
            'MSENC': tegrastats['MSENC'] if 'MSENC' in tegrastats else {}}
        if nvjpg_data:
            data['engines']['NVJPG'] = nvjpg_data['rate'] if nvjpg_data['status'] else {}
        # -- Power --
        # Refactor names
        power = {k.replace("VDD_", "").replace("POM_", "").replace("_", " "): v for k, v in tegrastats['WATT'].items()}
        total, power = self._total_power(power)
        data['power'] = {'all': total, 'power': power}
        # -- Temperature --
        # Remove PMIC temperature
        if 'PMIC' in tegrastats['TEMP']:
            del tegrastats['TEMP']['PMIC']
        data['temperature'] = tegrastats['TEMP']
        # -- CPU --
        data['cpu'] = tegrastats['CPU']
        # Update data from jetson_clocks show
        if 'CPU' in jetson_clocks_show:
            for name, v in tegrastats['CPU'].items():
                # Extract jc_cpu info
                jc_cpu = jetson_clocks_show['CPU'].get(name, {})
                # Remove current frequency
                del jc_cpu['current_freq']
                # Fix online status
                if 'Online' in jc_cpu:
                    if jc_cpu['Online']:
                        # Remove online info
                        del jc_cpu['Online']
                        # Update CPU information
                        v.update(jc_cpu)
                elif v:
                    # Update CPU information
                    v.update(jc_cpu)
                data['cpu'][name] = v
        for name, value in cpu_models().items():
            data['cpu'][name]['model'] = value
        # -- MTS --
        if 'MTS' in tegrastats:
            data['mts'] = tegrastats['MTS']
        # -- GPU --
        data['gpu'] = tegrastats['GR3D']
        if 'GPU' in jetson_clocks_show:
            data['gpu'].update(jetson_clocks_show['GPU'])
            # Remove current_freq data
            del data['gpu']['current_freq']
        # -- RAM --
        meminfo = self.memory.meminfo()
        data['ram'] = tegrastats['RAM']
        if meminfo:
            data['ram'].update(meminfo)
        # -- IRAM --
        if 'IRAM' in tegrastats:
            data['iram'] = tegrastats['IRAM']
        # -- EMC --
        if 'EMC' in tegrastats:
            data['emc'] = tegrastats['EMC']
            if self.jetson_clocks is not None:
                data['emc'].update(jetson_clocks_show['EMC'])
                # Remove current_freq data
                del data['emc']['current_freq']
        # -- SWAP --
        data['swap'] = {
            'list': self.swap.all(),
            'all': tegrastats['SWAP'] if 'SWAP' in tegrastats else {}}
        # -- OTHER --
        data['other'] = dict((k, tegrastats[k]) for k in tegrastats if k not in LIST_PRINT)
        # -- FAN --
        # Update status fan speed
        data['fan'] = self.fan.update()
        # -- JETSON_CLOCKS --
        if self.jetson_clocks is not None:
            data['jc'] = {
                'status': self.jetson_clocks.alive(wait=False),
                'thread': self.jetson_clocks.is_running(),
                'config': self.jetson_clocks.is_config(),
                'boot': self.jetson_clocks.boot}
        # -- NVP MODEL --
        if self.nvpmodel is not None:
            # Read nvp_mode
            nvp_mode = jetson_clocks_show['NVP'] if 'NVP' in jetson_clocks_show else self.nvpmodel.get()
            if not self.nvpmodel.is_running():
                self.nvp_mode = nvp_mode
            data['nvp'] = {
                'modes': self.nvpmodel.modes(),
                'thread': self.nvpmodel.is_running(),
                'mode': self.nvp_mode}
        # -- Cluster --
        if 'cluster' in jetson_clocks_show:
            data['cluster'] = jetson_clocks_show['cluster']
        # Pack and send all data
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(data)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()
# EOF
