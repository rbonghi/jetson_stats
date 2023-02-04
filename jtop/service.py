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

# Logging
import logging
# Operative system
# import signal
import re
import os
import sys
import stat
import shlex
import subprocess as sp
from copy import deepcopy
from grp import getgrnam
from shutil import copyfile
from multiprocessing import Process, Queue, Event, Value
from multiprocessing.managers import SyncManager

# jetson_stats imports
from .core.jetson_variables import get_jetson_variables, get_platform_variables
from .core import (
    Command,
    CPUService,
    MemoryService,
    JtopException,
    Tegrastats,
    JetsonClocksService,
    Config,
    NVPModelService,
    EngineService,
    FanService,
    FanServiceLegacy,
    get_key,
    get_var)
# Create logger
logger = logging.getLogger(__name__)
# Fix connection refused for python 2.7
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError
# Load queue library for python 2 and python 3
try:
    import queue
except ImportError:
    import Queue as queue  # pyright: ignore[reportMissingImports]
# Version match
VERSION_RE = re.compile(r""".*__version__ = ["'](.*?)['"]""", re.S)

PATH_TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']
PATH_JETSON_CLOCKS = ['/usr/bin/jetson_clocks', '/home/nvidia/jetson_clocks.sh']
PATH_FAN_LEGACY = ['/sys/kernel/debug/tegra_fan', '/sys/devices/pwm-fan']
PATH_FAN = ['/sys/devices/platform']
PATH_NVPMODEL = ['nvpmodel']
# Pipe configuration
# https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s13.html
# https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard
JTOP_PIPE = '/run/jtop.sock'
JTOP_USER = 'jtop'
JTOP_SERVICE_NAME = 'jtop.service'
# Gain timeout lost connection
TIMEOUT_GAIN = 3
TIMEOUT_SWITCHOFF = 3.0


def status_service(service=JTOP_SERVICE_NAME):
    return os.system('systemctl is-active --quiet {service}'.format(service=service)) == 0


def remove_service_pipe():
    # Remove old pipes if exists
    if os.path.isdir(JTOP_PIPE):
        logger.info("Remove folder {pipe}".format(pipe=JTOP_PIPE))
        os.rmdir(JTOP_PIPE)
    elif os.path.isfile(JTOP_PIPE):
        logger.info("Remove pipe {pipe}".format(pipe=JTOP_PIPE))
        os.remove(JTOP_PIPE)


def uninstall_service(name=JTOP_SERVICE_NAME):
    if os.path.isfile('/etc/systemd/system/{name}'.format(name=name)) or os.path.islink('/etc/systemd/system/{name}'.format(name=name)):
        logger.info("Found {name}".format(name=name))
        # Check if service is active
        if status_service(service=name):
            # Stop service
            logger.info(" - STOP {name}".format(name=name))
            sp.call(shlex.split('systemctl stop {name}'.format(name=name)))
        # Disable service
        logger.info(" - DISABLE {name}".format(name=name))
        sp.call(shlex.split('systemctl disable {name}'.format(name=name)))
        # Remove jetson_performance service from /etc/init.d
        if os.path.isfile('/etc/systemd/system/{name}'.format(name=name)) or os.path.islink('/etc/systemd/system/{name}'.format(name=name)):
            logger.info(" - REMOVE {name} from /etc/systemd/system".format(name=name))
            os.remove('/etc/systemd/system/{name}'.format(name=name))
        # Update service list
        logger.info(" - Reload all daemons")
        sp.call(shlex.split('systemctl daemon-reload'))
        return True
    return False


def install_service(package_root, copy, name=JTOP_SERVICE_NAME):
    logger.info("Install {name}".format(name=name))
    # Copy or link file
    service_install_path = '/etc/systemd/system/{name}'.format(name=name)
    service_package_path = '{package_root}/services/{name}'.format(package_root=package_root, name=name)
    # remove if exist file
    if os.path.isfile(service_install_path) or os.path.islink(service_install_path):
        logger.info(" - Remove old {path}".format(path=service_install_path))
        os.remove(service_install_path)
    if copy:
        type_service = "Copying"
        copyfile(service_package_path, service_install_path)
    else:
        type_service = "Linking"
        os.symlink(service_package_path, service_install_path)
    # Prompt message
    logger.info(" - {type} {file} -> {path}".format(type=type_service.upper(), file=name, path=service_install_path))
    # Update service list
    cmd_daemon_reload = Command(shlex.split('systemctl daemon-reload'))
    try:
        cmd_daemon_reload()
        logger.info(" - Reload all daemons")
    except (OSError, Command.CommandException):
        logger.error("Fail reload all daemons")
    # Enable jetson_stats at startup
    cmd_service_enable = Command(shlex.split('systemctl enable {name}'.format(name=name)))
    try:
        cmd_service_enable()
        logger.info(" - ENABLE {name}".format(name=name))
        # logger.info(lines)
    except (OSError, Command.CommandException):
        logger.error("Fail enable service {name}".format(name=name))
    # Start service
    cmd_service_start = Command(shlex.split('systemctl start {name}'.format(name=name)))
    try:
        cmd_service_start()
        logger.info(" - START {name}".format(name=name))
        # logger.info(lines)
    except (OSError, Command.CommandException):
        logger.error("Fail start service {name}".format(name=name))


def status_permission_user(group=JTOP_USER):
    user = os.environ.get('USER', '')
    # Get user from sudo
    if 'SUDO_USER' in os.environ:
        user = os.environ['SUDO_USER']
    # Check if user is in group
    cmd_group_user = Command(shlex.split('groups {user}'.format(user=user)))
    try:
        lines = cmd_group_user()
        for line in lines:
            name, info = line.split(":")
            info = info.strip().split()
            if name.strip() == user and group in info:
                return True
    except (OSError, Command.CommandException):
        logger.error("{user} does not exist".format(user=user))
    return False


def status_permission_group(group=JTOP_USER):
    # Check if exist group
    cmd_group = Command(shlex.split('getent group {group}'.format(group=group)))
    try:
        cmd_group()
    except (OSError, Command.CommandException):
        logger.error("Does not exist {group}".format(group=group))
        return False
    return True


def status_permission(group=JTOP_USER):
    return status_permission_group(group) and status_permission_group(group)


def unset_service_permission(group=JTOP_USER):
    user = os.environ.get('USER', '')
    # Get user from sudo
    if 'SUDO_USER' in os.environ:
        user = os.environ['SUDO_USER']
    # Check if user is in group
    if status_permission_user(group):
        logger.info("Remove {user} from group {group}".format(group=group, user=user))
        sp.call(shlex.split('gpasswd -d {user} {group}'.format(group=group, user=user)))
    if status_permission_group(group):
        logger.info("Delete group {group}".format(group=group))
        sp.call(shlex.split('groupdel {group}'.format(group=group)))


def set_service_permission(group=JTOP_USER):
    user = os.environ.get('USER', '')
    # Get user from sudo
    if 'SUDO_USER' in os.environ:
        user = os.environ['SUDO_USER']
    # Make jetson_stats group
    if not status_permission_group(group):
        logger.info("Add new group {group}".format(group=group))
        sp.call(shlex.split('groupadd {group}'.format(group=group)))
    if not status_permission_user(group):
        logger.info("Add {user} to group {group}".format(group=group, user=user))
        sp.call(shlex.split('usermod -a -G {group} {user}'.format(group=group, user=user)))


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
        # Save version jtop
        self._version = deepcopy(get_var(VERSION_RE))
        logger.info("jetson_stats {version} - server loaded".format(version=self._version))
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
        is_debug = True if "JETSON_DEBUG" in os.environ else False
        # Load board and platform variables
        self.board = {'hardware': get_jetson_variables()}
        data_platform = get_platform_variables()
        logger.info("Running on Python: {python_version}".format(python_version=data_platform['Python']))
        # Initialize Fan
        try:
            self.fan = FanService(self.config, path_fan)
        except JtopException as error:
            logger.warning("{error} in paths {path}".format(error=error, path=path_fan))
            self.fan = FanServiceLegacy(self.config, path_fan if is_debug else PATH_FAN_LEGACY)
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
        # Setup cpu service
        self.cpu = CPUService()
        # Setup memory service
        self.memory = MemoryService(self.config)
        # Setup engine service
        self.engine = EngineService()
        # Setup tegrastats
        self.tegra = Tegrastats(self.tegra_stats, path_tegrastats)

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
                        if swap['type'] == 'set':
                            self.memory.swap_set(swap['size'], swap['path'], swap['boot'])
                        elif swap['type'] == 'unset':
                            self.memory.swap_deactivate(swap['path'])
                    # Clear cache
                    if 'clear_cache' in control:
                        logger.info("Clear cache")
                        # Clear cache
                        self.memory.clear_cache()
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
                            'version': self._version,
                            'board': self.board,
                            'interval': self.interval.value,
                            'cpu': self.cpu.get_cpu_info(),
                            'memory': self.memory.swap_path(),
                            'fan': self.fan.get_configs(),
                            'jc': self.jetson_clocks is not None,
                            'nvpmodel': self.nvpmodel is not None}
                        self.q.put({'init': init})
                    # Update timeout interval
                    timeout = TIMEOUT_GAIN if interval <= TIMEOUT_GAIN else interval * TIMEOUT_GAIN
                except queue.Empty:
                    self.sync_event.clear()
                    # Reset CPU estimation
                    self.cpu.reset_estimation()
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
            # Write error message
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
        if self.force:
            remove_service_pipe()
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
        # Change mode controller and stats
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
        # https://forums.developer.nvidia.com/t/tegrastats-monitoring/217088/4?u=user62045
        total_name = ""
        for val in power:
            if "POM_5V_IN" in val:
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
        jetson_clocks_show = deepcopy(self.jetson_clocks.show()) if self.jetson_clocks is not None else {}
        # -- CPU --
        # Read CPU data
        data['cpu'] = self.cpu.get_status()
        # -- RAM --
        # Read memory data
        # In this dictionary are collected
        # - RAM
        # - SWAP
        # - EMC (If available)
        # - IRAM (If available)
        data['mem'] = self.memory.get_status()
        # -- Engines --
        # Read all engines available
        # Can be empty for x86 architecture
        data['engines'] = self.engine.get_status()
        # -- Power --
        # Remove NC power (Orin family)
        # https://docs.nvidia.com/jetson/archives/r34.1/DeveloperGuide/text/SD/PlatformPowerAndPerformance/JetsonOrinNxSeriesAndJetsonAgxOrinSeries.html#jetson-agx-orin-series
        if 'NC' in tegrastats['WATT']:
            del tegrastats['WATT']['NC']
        # Refactor names
        total, power = self._total_power(tegrastats['WATT'])
        power = {k.replace("VDDQ_", "").replace("VDD_", "").replace("POM_", "").replace("_", " "): v for k, v in power.items()}
        data['power'] = {'all': total, 'power': power}
        # -- Temperature --
        # Remove PMIC temperature (TX family)
        if 'PMIC' in tegrastats['TEMP']:
            del tegrastats['TEMP']['PMIC']
        # Remove all CV temperatures (Orin family)
        for temp in list(tegrastats['TEMP'].keys()):
            if temp.startswith('CV'):
                del tegrastats['TEMP'][temp]
        data['temperature'] = tegrastats['TEMP']
        # -- GPU --
        data['gpu'] = {1: tegrastats['GR3D']}
        # For more GPU change in a next future with
        # data['gpu'] = [value for key,value in tegrastats.items() if key.startswith('GR3D')]
        if 'GR3D2' in tegrastats:
            data['gpu'][2] = tegrastats['GR3D2']
        if 'GPU' in jetson_clocks_show:
            for idx in range(1, len(data['gpu']) + 1):
                data['gpu'][idx].update(jetson_clocks_show['GPU'])
                # Remove current_freq data
                del data['gpu'][idx]['current_freq']
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
            nvp_mode = self.nvpmodel.get()
            if not self.nvpmodel.is_running():
                self.nvp_mode = nvp_mode
            data['nvp'] = {
                'modes': self.nvpmodel.modes(),
                'thread': self.nvpmodel.is_running(),
                'mode': self.nvp_mode}
        # Pack and send all data
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(data)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()
# EOF
