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
from shutil import copyfile, rmtree
from multiprocessing import Process, Queue, Event, Value
from multiprocessing.managers import SyncManager

# jetson_stats imports
from .core.exceptions import JtopException
from .core.common import get_key, get_var, get_uptime
from .core.hardware import get_hardware, get_platform_variables
from .core.command import Command
from .core.config import Config
from .core.timer_reader import TimerReader
from .core.cpu import CPUService
from .core.memory import MemoryService
from .core.processes import ProcessService
from .core.gpu import GPUService
from .core.engine import EngineService
from .core.temperature import TemperatureService
from .core.power import PowerService
from .core.fan import FanService
from .core.jetson_clocks import JetsonClocksService
from .core.nvpmodel import NVPModelService
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
        rmtree(JTOP_PIPE)
    elif os.path.exists(JTOP_PIPE):
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
    sudo_user = os.environ.get('SUDO_USER', '')
    # If are both empty assign 'root'
    user = sudo_user or 'root'
    # Check if user is in group
    cmd_group_user = Command(shlex.split('groups {user}'.format(user=user)))
    try:
        lines = cmd_group_user()
        for line in lines:
            if ":" not in line:
                continue
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
    return status_permission_user(group) and status_permission_group(group)


def unset_service_permission(group=JTOP_USER):
    user = os.environ.get('USER', '')
    # Get user from sudo
    sudo_user = os.environ.get('SUDO_USER', '')
    # If are both empty assign 'root'
    user = sudo_user or 'root'
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
    sudo_user = os.environ.get('SUDO_USER', '')
    # If are both empty assign 'root'
    user = sudo_user or 'root'
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

    def __init__(self, force=False):
        self.force = force
        # Check if running a root
        if os.getuid() != 0:
            raise JtopException("jtop service need sudo to work")
        # Load configuration
        self.config = Config()
        # Save version jtop
        self._version = deepcopy(get_var(VERSION_RE))
        logger.info("jetson_stats {version} - server loaded".format(version=self._version))
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
        # Load board and platform variables
        data_platform = get_platform_variables()
        logger.info("Running on Python: {python_version}".format(python_version=data_platform['Python']))
        self.board = {'hardware': get_hardware()}
        # From this point are initialized or hardware services
        # Setup cpu service
        self.cpu = CPUService()
        # Setup gpu service
        self.gpu = GPUService()
        # Setup process service
        self.processes = ProcessService()
        # Setup memory service
        self.memory = MemoryService(self.config)
        # Setup engine service
        self.engine = EngineService()
        # Setup Temperature service
        self.temperature = TemperatureService()
        # Setup Power meter service
        self.power = PowerService()
        # Initialize Fan
        self.fan = FanService(self.config)
        # Initialize jetson_clocks controller
        self.jetson_clocks = JetsonClocksService(self.config, self.fan)
        # Initialize nvpmodel controller
        self.nvpmodel = NVPModelService(self.jetson_clocks)
        # Initialize timer reader
        self._timer_reader = TimerReader(self.jtop_stats)

    def run(self):
        logger.info("Initialization service")
        # Initialize jetson_fan
        self.fan.initialization()
        # Run setup
        if self.jetson_clocks.exists():
            # Decode for initialization and reset
            data = self.jtop_decode()
            # Reset CPU estimation
            self.cpu.reset_estimation()
            # Reset avg temperatures
            self.power.reset_avg_power()
            # Initialization jetson_clocks
            self.jetson_clocks.initialization(self.nvpmodel, data)
        logger.info("service ready")
        # Initialize variables
        timeout = None
        interval = 1
        try:
            while True:
                try:
                    # Decode control message
                    control = self.q.get(timeout=timeout)
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
                        if 'command' in swap:
                            command = swap['command']
                            if command == 'set':
                                logger.info("Activating swap in {path}".format(path=swap['path']))
                                self.memory.swap_set(swap['size'], swap['path'], swap['boot'])
                            elif command == 'unset':
                                logger.info("Deactivating swap in {path}".format(path=swap['path']))
                                self.memory.swap_deactivate(swap['path'])
                            else:
                                logger.error("swap command not detected: {command}".format(command=command))
                        else:
                            logger.error("no swap command in this message {message}".format(message=swap))
                    # Clear cache
                    if 'clear_cache' in control:
                        # Clear cache
                        self.memory.clear_cache()
                        logger.info("Clear cache")
                    # Set GPU configuration
                    if 'gpu' in control:
                        gpu = control['gpu']
                        if 'command' in gpu:
                            command = gpu['command']
                            name = gpu['name']
                            if command == '3d_scaling':
                                self.gpu.set_scaling_3D(name, gpu['value'])
                            elif command == 'railgate':
                                self.gpu.set_railgate(name, gpu['value'])
                            else:
                                logger.error("gpu command not detected: {command}".format(command=command))
                        else:
                            logger.error("no gpu command in this message {message}".format(message=gpu))
                    # Speed Fan and configuration
                    if 'fan' in control:
                        fan = control['fan']
                        if 'command' in fan:
                            command = fan['command']
                            if command == 'profile':
                                name = fan['name']
                                profile = fan['profile']
                                logger.info('Fan \"{name}\" set profile {profile}'.format(name=name, profile=profile))
                                self.fan.set_profile(name, profile)
                            elif command == 'speed':
                                name = fan['name']
                                speed = fan['speed']
                                idx = fan['idx']
                                logger.info('Fan \"{name}[{idx}]\" set speed {speed}'.format(name=name, idx=idx, speed=speed))
                                self.fan.set_speed(name, speed, idx)
                            else:
                                logger.error("fan command not detected: {command}".format(command=command))
                        else:
                            logger.error("no fan command in this message {message}".format(message=fan))
                    if 'jc' in control:
                        jc = control['jc']
                        # Enable / disable jetson_clocks
                        if 'enable' in jc:
                            self.jetson_clocks.set_enable(jc['enable'])
                        # Update jetson_clocks configuration
                        if 'boot' in jc:
                            self.jetson_clocks.set_boot(jc['boot'])
                        # Clear configuration
                        if 'clear' in jc:
                            self.jetson_clocks.clear()
                    # Decode nvp model
                    if 'nvp' in control:
                        nvpmodel = control['nvp']
                        nvpmodel_id = nvpmodel['id']
                        nvpmodel_force = nvpmodel['force']
                        # Set new NV Power Mode
                        logger.info("Set new NV Power Model ID {id}".format(id=nvpmodel_id))
                        self.nvpmodel.set_nvpmodel_id(nvpmodel_id, nvpmodel_force)
                    # Initialize tegrastats speed
                    if 'interval' in control:
                        interval = control['interval']
                        # Run stats
                        if self._timer_reader.open(interval=interval):
                            # Set interval value
                            self.interval.value = interval
                            # Status start tegrastats
                            logger.info("jtop timer thread started {interval}ms".format(interval=int(interval * 1000)))
                        # send configuration board
                        init = {
                            'version': self._version,
                            'board': self.board,
                            'interval': self.interval.value,
                            'memory': self.memory.swap_path(),
                            'fan': self.fan.get_configs(),
                            'jc': self.jetson_clocks.exists(),
                        }
                        # If nvpmodel exist load all modes
                        if self.nvpmodel.exists():
                            init['nvpmodel'] = {
                                'models': self.nvpmodel.get_all_nvpmodels(),
                                'default': self.nvpmodel.get_default()
                            }
                        # Push initialization string
                        self.q.put({'init': init})
                    # Manage jetson_clocks
                    if 'config' in control:
                        command = control['config']
                        if command == 'reset':
                            logger.info('Reset configuration')
                            self.config.clear()
                    # Update timeout interval
                    timeout = TIMEOUT_GAIN if interval <= TIMEOUT_GAIN else interval * TIMEOUT_GAIN
                except queue.Empty:
                    self.sync_event.clear()
                    # Reset CPU estimation
                    self.cpu.reset_estimation()
                    # Reset avg temperatures
                    self.power.reset_avg_power()
                    # Close and log status
                    if self._timer_reader.close():
                        logger.info("jtop timer thread close")
                    # Disable timeout
                    timeout = None
                    self.interval.value = -1.0
        except (KeyboardInterrupt, SystemExit):
            logger.warning("KeyboardInterrupt, SystemExit interrupt")
        except FileNotFoundError:
            logger.warning("FileNotFoundError on service thread")
        except Exception as e:
            logger.error("Error subprocess {error}".format(error=e), exc_info=1)
            # Write error message
            self._error.put(sys.exc_info())
        finally:
            # Close tegra
            if self._timer_reader.close(timeout=TIMEOUT_SWITCHOFF):
                logger.info("FORCE jtop timer thread close")
                # Reset CPU estimation
                self.cpu.reset_estimation()
                # Reset avg temperatures
                self.power.reset_avg_power()

    def start(self):
        # Initialize socket
        try:
            gid = getgrnam(JTOP_USER).gr_gid
        except KeyError:
            # User does not exist
            raise JtopException("Group {jtop_user} does not exist!".format(jtop_user=JTOP_USER))
        # Remove old pipes if exists
        if self.force:
            self.remove_files()
        # If exist JTOP pipe raise exception
        if os.path.exists(JTOP_PIPE):
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
        # Switch off jetson_clocks if there are threads alive
        self.jetson_clocks.close()
        # Switch off nvpmodel if there are threads alive
        self.nvpmodel.close()
        # Close stats server
        logger.info("Service closed")
        return True

    def remove_files(self):
        # If exist remove pipe
        remove_service_pipe()

    def config_clear(self):
        self.config.clear()

    def jtop_decode(self):
        # Make configuration dict
        data = {}
        # -- UPTIME --
        data['uptime'] = get_uptime()
        # -- CPU --
        # Read CPU data
        data['cpu'] = self.cpu.get_status()
        # -- GPU ---
        # Read GPU status
        data['gpu'] = self.gpu.get_status()
        # -- All processes
        total, table = self.processes.get_status()
        data['processes'] = table
        # -- RAM --
        # Read memory data
        # In this dictionary are collected
        # - RAM
        # - SWAP
        # - EMC (If available)
        # - IRAM (If available)
        data['mem'] = self.memory.get_status(total)
        # -- Engines --
        # Read all engines available
        # Can be empty for x86 architecture
        data['engines'] = self.engine.get_status()
        # -- Temperature --
        data['temperature'] = self.temperature.get_status()
        # -- Power --
        data['power'] = self.power.get_status()
        # -- FAN --
        # Update status fan speed
        data['fan'] = self.fan.get_status()
        # -- JETSON_CLOCKS --
        # Jetson Clock to check if is running need to read the status from:
        # CPU, EMC, GPU, ENGINES
        # If not empty return status
        if self.jetson_clocks.exists():
            # Get status jetson_clocks
            data['jc'] = self.jetson_clocks.get_status(data)
        # -- NVP MODEL --
        # Read nvpmodel status, ID, name, and status thread
        if self.nvpmodel.exists():
            data['nvp'] = self.nvpmodel.get_status()
        return data

    def jtop_stats(self):
        # logger.info("jtop read")
        data = self.jtop_decode()
        # Pack and send all data
        # https://stackoverflow.com/questions/6416131/add-a-new-item-to-a-dictionary-in-python
        self.sync_data.update(data)
        # Set event for all clients
        if not self.sync_event.is_set():
            self.sync_event.set()
# EOF
