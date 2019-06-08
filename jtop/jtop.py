# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import os
# Logging
import logging
# Launch command
import subprocess as sp
# Threading
from threading import Thread
from collections import deque
# Socket and IP information
import socket
import fcntl
import struct
import array

# Create logger for jplotlib
logger = logging.getLogger(__name__)


def import_os_variables(SOURCE, PATTERN="JETSON_"):
    if os.path.isfile(SOURCE):
        logger.info("Open source file {}".format(SOURCE))
        proc = sp.Popen(['bash', '-c', 'source {} && env'.format(SOURCE)], stdout=sp.PIPE)
        # Load variables
        source_env = {}
        for tup in map(lambda s: s.decode("utf-8").strip().split('=', 1), proc.stdout):
            name = tup[0].strip()
            value = tup[1].strip()
            if PATTERN in name:
                source_env[name] = value
        return source_env
    else:
        logger.error("File does not exist")
        return {}


class nvpmodel():
    """
        This controller read the status from your NVIDIA Jetson and you can control
        performance and status.
        It is available for NVIDIA Jetson TX2, Jetson AGX Xavier, Jetson Nano
        Boards reference:
        * TX2: https://www.jetsonhacks.com/2017/03/25/nvpmodel-nvidia-jetson-tx2-development-kit/
        * AGX Xavier: https://www.jetsonhacks.com/2018/10/07/nvpmodel-nvidia-jetson-agx-xavier-developer-kit/
        * Nano: https://www.jetsonhacks.com/2019/04/10/jetson-nano-use-more-power/
    """
    BOARDS = {"NO-BOARD": [{"Name": "Test mode"}],
              "TX2": [{"Name": 'Max-N'},
                      {"Name": 'Max-Q'},
                      {"Name": 'Max-P Core-All'},
                      {"Name": 'Max-P ARM'},
                      {"Name": 'Max-P Denver'}],
              "Xavier": [{"Name": 'Max-N', "Power": 'N/A'},
                         {"Name": 'Mode-10W', "Power": '10W'},
                         {"Name": 'Mode-15W', "Power": '15W'},
                         {"Name": 'Mode-30W-All', "Power": '30W'},
                         {"Name": 'Mode-30W-6CORE', "Power": '30W'},
                         {"Name": 'Mode-30W-4CORE', "Power": '30W'},
                         {"Name": 'Mode-30W-2CORE', "Power": '30W'}],
              "NANO": [{"Name": 'Max-N', "Power": '20W'},
                       {"Name": 'Mode-1', "Power": '5W'}]}

    def __init__(self, board):
        self.board = ""
        # Find name board from board list
        for name in nvpmodel.BOARDS.keys():
            if board.lower() in name.lower():
                self.board = name
                logger.info("Board found: {}".format(self.board))
                break
        if self.board:
            logger.info("This board {} does not have NVP Model".format(self.board))

    def modes(self):
        if self.board:
            return nvpmodel.BOARDS[self.board]
        else:
            return {}

    def set(self, level):
        """ Set nvpmodel to a new status """
        if self.board:
            try:
                sp.Popen(['nvpmodel', '-m', level], stdout=sp.PIPE)
                return True
            except OSError:
                logger.info("NVP Model does not exist")
        else:
            return False

    @property
    def status(self):
        """ Read nvpmodel to know the status of the board """
        if self.board:
            try:
                nvpmodel_p = sp.Popen(['nvpmodel', '-q'], stdout=sp.PIPE)
                out, _ = nvpmodel_p.communicate()
                # Log value
                logger.debug('nvqmodel status %s', out)
                # Decode lines and split
                lines = out.decode("utf-8").split("\n")
                # Return the mode type
                return nvpmodel.BOARDS[self.board][int(lines[1])]
                #return {'name': lines[0].split(": ")[1], 'mode': int(lines[1])}
            except OSError:
                logger.info("NVP Model does not exist")
        else:
            return {}


def get_uptime():
    """ Read uptime system
        http://planzero.org/blog/2012/01/26/system_uptime_in_python,_a_better_way
    """
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def get_local_interfaces():
    """ Returns a dictionary of name:ip key value pairs.
        - Reference:
           * http://code.activestate.com/recipes/439093/#c1
           * https://gist.github.com/pklaus/289646
    """
    # Max possible bytes for interface result.  Will truncate if more than 4096 characters to describe interfaces.
    MAX_BYTES = 4096
    # We're going to make a blank byte array to operate on.  This is our fill char.
    FILL_CHAR = b'\0'
    # Command defined in ioctl.h for the system operation for get iface list
    # Defined at https://code.woboq.org/qt5/include/bits/ioctls.h.html under
    # /* Socket configuration controls. */ section.
    SIOCGIFCONF = 0x8912
    # Read hostname
    hostname = socket.gethostname()
    # Make a dgram socket to use as our file descriptor that we'll operate on.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Make a byte array with our fill character.
    names = array.array('B', MAX_BYTES * FILL_CHAR)
    # Get the address of our names byte array for use in our struct.
    names_address, names_length = names.buffer_info()
    # Create a mutable byte buffer to store the data in
    mutable_byte_buffer = struct.pack('iL', MAX_BYTES, names_address)
    # mutate our mutable_byte_buffer with the results of get_iface_list.
    # NOTE: mutated_byte_buffer is just a reference to mutable_byte_buffer - for the sake of clarity we've defined them as
    # separate variables, however they are the same address space - that's how fcntl.ioctl() works since the mutate_flag=True
    # by default.
    mutated_byte_buffer = fcntl.ioctl(sock.fileno(), SIOCGIFCONF, mutable_byte_buffer)
    # Get our max_bytes of our mutated byte buffer that points to the names variable address space.
    max_bytes_out, names_address_out = struct.unpack('iL', mutated_byte_buffer)
    # Convert names to a bytes array - keep in mind we've mutated the names array, so now our bytes out should represent
    # the bytes results of the get iface list ioctl command.
    namestr = names.tostring()
    # Each entry is 40 bytes long.  The first 16 bytes are the name string.
    # the 20-24th bytes are IP address octet strings in byte form - one for each byte.
    # Don't know what 17-19 are, or bytes 25:40.
    ip_dict = {}
    for i in range(0, max_bytes_out, 40):
        name = namestr[i: i + 16].split(FILL_CHAR, 1)[0]
        name = name.decode('utf-8')
        ip_bytes = namestr[i + 20:i + 24]
        full_addr = []
        for netaddr in ip_bytes:
            if isinstance(netaddr, int):
                full_addr.append(str(netaddr))
            elif isinstance(netaddr, str):
                full_addr.append(str(ord(netaddr)))
        ip_dict[name] = '.'.join(full_addr)
    # Remove loopback interface is in list
    if 'lo' in ip_dict:
        del ip_dict['lo']
    return {"hostname": hostname, "interfaces": ip_dict}


class Fan():

    def __init__(self, path, max_record):
        self.path = path
        self.fan = deque(max_record * [0], maxlen=max_record)

    def update(self):
        fan_status_p = sp.Popen(['cat', self.path], stdout=sp.PIPE)
        query, _ = fan_status_p.communicate()
        logger.debug('{} status status {}'.format(self.path, query))
        fan_level = float(query) / 255.0 * 100.0
        self.fan.append(int(fan_level))

    @property
    def status(self):
        return {'name': 'FAN',
                'value': list(self.fan),
                }


class jtop(Thread):
    """
        - Subprocess read:
        https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        - Property
        https://www.programiz.com/python-programming/property
    """
    # List of available fan
    JTOP_FOLDER = '/opt/jetson_stats/'
    LIST_FANS = ['/sys/kernel/debug/tegra_fan/target_pwm', '/sys/devices/pwm-fan/target_pwm']
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']

    class jtopException(Exception):
        pass

    def __init__(self, interval=500, time=10.0):
        Thread.__init__(self)
        # Load all Jetson variables
        if "JETSON_BOARD" not in os.environ:
            logger.info("Load jetson variables from script")
            for k, v in import_os_variables(jtop.JTOP_FOLDER + 'jetson_variables').items():
                logger.debug("New Enviroment variable {}:{}".format(k, v))
                os.environ[k] = v
        # Initialize number max records to record
        max_record = int(float(time) * (float(1 / float(interval)) * 1000.0))
        self.max_record = max_record
        # Sensors deque list
        self.swap = deque(max_record * [0], maxlen=max_record)
        self.iram = deque(max_record * [0], maxlen=max_record)
        self.ram = deque(max_record * [0], maxlen=max_record)
        self.cpus = {}
        self.emc = jtop.initProcess("EMC", max_record, status="REQUIRE SUDO")
        self.gpu = jtop.initProcess("GPU", max_record, status="REQUIRE SUDO")
        self.temperatures = {}
        self.voltages = {}
        # Initialize NVP model
        self.nvp = nvpmodel(os.environ["JETSON_BOARD"])
        # Find all fans availables
        self.qfans = []
        for fan in jtop.LIST_FANS:
            if os.path.isfile(fan):
                self.qfans += [Fan(fan, max_record)]
        # Initialize jetson stats
        self._jetsonstats = {}
        # Start process tegrastats
        tegrastats_file = ""
        for f_tegra in jtop.TEGRASTATS:
            if os.path.isfile(f_tegra):
                logger.info("Load tegrastats {}".format(f_tegra))
                tegrastats_file = f_tegra
                break
        # Launch subprocess or raise and exception
        if tegrastats_file:
            self.p = sp.Popen([tegrastats_file, '--interval', str(interval)], stdout=sp.PIPE)
        else:
            logger.error("Tegrastats not in list!")
            raise jtop.TegrastatsException("Tegrastats is not available on this hardware")

    def run(self):
        try:
            while self.p.poll() is None:
                # Read line process output
                line = self.p.stdout.readline()
                # Decode line in UTF-8
                tegrastats_data = line.decode("utf-8")
                # Decode and store
                self._jetsonstats = self.decode(tegrastats_data)
        except SystemExit:
            logger.error("System exit", exc_info=True)
        except AttributeError:
            logger.error("Attribute error", exc_info=True)

    @property
    def fans(self):
        return [fan.status for fan in self.qfans]

    @property
    def disk(self):
        disk = os.statvfs("/var/")
        # Evaluate the total space in GB
        totalSpace = float(disk.f_bsize * disk.f_blocks) / 1024 / 1024 / 1024
        # Evaluate total used space in GB
        totalUsedSpace = float(disk.f_bsize * (disk.f_blocks - disk.f_bfree)) / 1024 / 1024 / 1024
        # Evaluate total available space in GB
        totalAvailSpace = float(disk.f_bsize * disk.f_bfree) / 1024 / 1024 / 1024
        # Evaluate total non super-user space in GB
        totalAvailSpaceNonRoot = float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024
        return {'total': totalSpace,
                'used': totalUsedSpace,
                'available': totalAvailSpace,
                'available_no_root': totalAvailSpaceNonRoot
                }

    def jetson_clock_status(self):
        p = sp.Popen(['systemctl', 'is-active', 'jetson_performance.service'], stdout=sp.PIPE)
        out, _ = p.communicate()
        return out.strip()

    @property
    def uptime(self):
        return get_uptime()

    @property
    def nvpmodel(self):
        return self.nvp.status

    @property
    def local_interfaces(self):
        return get_local_interfaces()

    @property
    def board(self):
        board = {"name": os.environ["JETSON_DESCRIPTION"],
                 "type": os.environ["JETSON_TYPE"],
                 "jetpack": os.environ["JETSON_JETPACK"] + " [L4T " + os.environ["JETSON_L4T"] + "]",
                 "GPU-arch": os.environ["JETSON_CUDA_ARCH_BIN"]}
        libraries = {"CUDA": os.environ["JETSON_CUDA"],
                     "cuDNN": os.environ["JETSON_CUDNN"],
                     "TensorRT": os.environ["JETSON_TENSORRT"],
                     "VisionWorks": os.environ["JETSON_VISIONWORKS"],
                     "OpenCV": os.environ["JETSON_OPENCV"] + " compiled CUDA: " + os.environ["JETSON_OPENCV_CUDA"]}
        return {"board": board, "libraries": libraries}

    @property
    def stats(self):
        # Wait the deque not empty
        while not self._jetsonstats:
            pass
        # Return dictionary parsed
        return self._jetsonstats

    def open(self):
        # Start himself like file
        self.daemon = True
        self.start()

    def close(self):
        self.p.kill()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def updateProcess(text, status):
        status['idle'].pop(0)
        status['frequency'].pop(0)
        if 'off' in text:
            status['idle'].append(0.0)
            status['frequency'].append(0.0)
            status['status'] = "OFF"
        elif '@' in text:
            info = re.findall(r"\d+", text)
            status['idle'].append(float(info[0]))
            status['frequency'].append(float(info[1]))
            status['status'] = "ON"
        else:
            info = re.findall(r"\d+", text)
            status['idle'].append(float(info[0]))
            status['frequency'].append(0.0)
            status['status'] = "ON-SIMPLE"
        return status

    @staticmethod
    def initProcess(name, max_record, status="OFF"):
        return {'name': name,
                'idle': max_record * [0.0],
                'frequency': max_record * [0.0],
                'status': status,
                }

    def _SWAP(self, text):
        # SWAP X/Y (cached Z)
        # X = Amount of SWAP in use in megabytes.
        # Y = Total amount of SWAP available for applications.
        # Z = Amount of SWAP cached in megabytes.
        find_swap = re.search(r'SWAP (.+?)B \(cached (.+?)B\)', text)
        if find_swap is not None:
            swap_string = find_swap.group()
            swap_stat = re.findall(r"\d+", swap_string)
            text = re.sub(r'SWAP (.+?)B \(cached (.+?)B\) ', '', text)
            self.swap.append(float(swap_stat[0]))
            return {'used': list(self.swap),
                    'total': float(swap_stat[1]),
                    'cached': int(swap_stat[2])
                    }, text
        else:
            return {}, text

    def _IRAM(self, text):
        # IRAM X/Y (lfb Z)
        # IRAM is memory local to the video hardware engine.
        # X = Amount of IRAM memory in use, in kilobytes.
        # Y = Total amount of IRAM memory available.
        # Z = Size of the largest free block.
        find_iram = re.search(r'IRAM (.+?)B\(lfb (.+?)B\)', text)
        # Find if IRAM is inside
        if find_iram is not None:
            iram_lfb_string = find_iram.group()
            iram_stat = re.findall(r"\d+", iram_lfb_string)
            text = re.sub(r'IRAM (.+?)B\(lfb (.+?)B\) ', '', text)
            self.iram.append(float(iram_stat[0]))
            return {'used': list(self.iram),
                    'total': float(iram_stat[1]),
                    'size': int(iram_stat[2])
                    }, text
        else:
            return {}, text

    def _RAM(self, text):
        # RAM X/Y (lfb NxZ)
        # Largest Free Block (lfb) is a statistic about the memory allocator.
        # It refers to the largest contiguous block of physical memory
        # that can currently be allocated: at most 4 MB.
        # It can become smaller with memory fragmentation.
        # The physical allocations in virtual memory can be bigger.
        # X = Amount of RAM in use in MB.
        # Y = Total amount of RAM available for applications.
        # N = The number of free blocks of this size.
        # Z = is the size of the largest free block.
        ram_string = re.search(r'RAM (.+?)B', text).group()
        lfb_string = re.search(r'\(lfb (.+?)\)', text).group()
        ram_stat = re.findall(r"\d+", ram_string)
        lfb_stat = re.findall(r"\d+", lfb_string)
        text = re.sub(r'RAM (.+?)\) ', '', text)
        self.ram.append(float(ram_stat[0]))
        return {'RAM': {'used': list(self.ram), 'total': float(ram_stat[1])},
                'lfb': {'nblock': lfb_stat[0], 'size': lfb_stat[1]},
                }, text

    def _CPU(self, text):
        # CPU [X%,Y%, , ]@Z
        # or
        # CPU [X%@Z, Y%@Z,...]
        # X and Y are rough approximations based on time spent
        # in the system idle process as reported by the Linux kernel in /proc/stat.
        # X = Load statistics for each of the CPU cores relative to the
        #     current running frequency Z, or 'off' in case a core is currently powered down.
        # Y = Load statistics for each of the CPU cores relative to the
        #     current running frequency Z, or 'off' in case a core is currently powered down.
        # Z = CPU frequency in megahertz. Goes up or down dynamically depending on the CPU workload.
        cpu_string = re.search(r'CPU (.+?)\]', text).group()
        cpu_string = cpu_string[cpu_string.find("[") + 1:cpu_string.find("]")]
        text = re.sub(r'CPU (.+?)\] ', '', text)
        for idx, cpu in enumerate(cpu_string.split(",")):
            name = "CPU" + str(idx + 1)
            if idx in self.cpus:
                cpu_status = self.cpus[idx]
            else:
                cpu_status = jtop.initProcess(name, self.max_record)
            cpu_status = jtop.updateProcess(cpu, cpu_status)
            # Update status governor
            governor_name = '/sys/devices/system/cpu/cpu' + str(idx) + '/cpufreq/scaling_governor'
            if os.path.isfile(governor_name):
                with open(governor_name, 'r') as f:
                    cpu_status['governor'] = f.read()[:-1]
            else:
                cpu_status['governor'] = ""
            # Update status CPU
            self.cpus[idx] = cpu_status
        return text

    def decode(self, text):
        jetsonstats = {}
        # Update status from fan
        for fan in self.qfans:
            fan.update()
        # Read SWAP status
        swap_status, text = self._SWAP(text)
        jetsonstats['SWAP'] = swap_status
        # Read IRAM status
        iram_status, text = self._IRAM(text)
        jetsonstats['IRAM'] = iram_status
        # Read RAM status
        ram_status, text = self._RAM(text)
        jetsonstats['RAM'] = ram_status
        # Read CPU status
        text = self._CPU(text)
        jetsonstats['CPU'] = list(self.cpus.values())
        # Start while loop to decode
        idx = 0
        other_values = text.split(" ")
        while idx < len(other_values):
            data = other_values[idx]
            if 'EMC' in data:
                # EMC X%@Y
                # EMC is the external memory controller,
                # through which all sysmem/carve-out/GART memory accesses go.
                # X = Percent of EMC memory bandwidth being used, relative to the current running frequency.
                # Y = EMC frequency in megahertz.
                self.emc = jtop.updateProcess(other_values[idx + 1], self.emc)
                # extra increase counter
                idx += 1
            elif 'APE' in data:
                # APE Y
                # APE is the audio processing engine.
                # The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
                # Y = APE frequency in megahertz.
                jetsonstats['APE'] = other_values[idx + 1]
                # extra increase counter
                idx += 1
            elif 'GR3D' in data:
                # GR3D X%@Y
                # GR3D is the GPU engine.
                # X = Percent of the GR3D that is being used, relative to the current running frequency.
                # Y = GR3D frequency in megahertz
                self.gpu = jtop.updateProcess(other_values[idx + 1], self.gpu)
                # extra increase counter
                idx += 1
            elif 'MTS' in data:
                # MTS fg X% bg Y%
                # X = Time spent in foreground tasks.
                # Y = Time spent in background tasks.
                fg = float(other_values[idx + 2].split("%")[0])
                bg = float(other_values[idx + 4].split("%")[0])
                jetsonstats['MTS'] = {'fg': fg, 'bg': bg}
                # extra increase counter
                idx += 4
            elif 'MSENC' in data:
                # MSENC Y
                # Y = MSENC frequency in megahertz.
                # MSENC is the video hardware encoding engine.
                jetsonstats['MSENC'] = int(other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif 'NVDEC' in data:
                # NVDEC Y
                # Y = NVDEC frequency in megahertz.
                # NVDEC is the video hardware decoding engine.
                # It is shown only when hardware decoder/encoder engine is used.
                jetsonstats['NVDEC'] = int(other_values[idx + 1])
                # extra increase counter
                idx += 1
            elif '@' in data:
                # [temp name] C
                # [temp name] is one of the names under the nodes
                # /sys/devices/virtual/thermal/thermal_zoneX/type.
                info = data.split("@")
                name = info[0].strip()
                value = info[1]
                # Read from dictionary temperature or initialize it
                if name in self.temperatures:
                    temp = self.temperatures[name]
                else:
                    temp = {'value': self.max_record * [0.0], 'unit': 'C'}
                # Remove last measured temp
                temp['value'].pop(0)
                # Add new value
                temp['value'].append(float(value.split("C")[0]))
                # Update text value
                temp['text'] = value
                # Store temperature value
                self.temperatures[name] = temp
            else:
                # [VDD_name] X/Y
                # X = Current power consumption in milliwatts.
                # Y = Average power consumption in milliwatts.
                value = other_values[idx + 1].split("/")
                # Read from dictionary temperature or initialize it
                if data in self.voltages:
                    volt = self.voltages[data]
                else:
                    volt = {'current': self.max_record * [0.0], 'average': self.max_record * [0.0], 'unit': 'mW'}
                # Remove last measure
                volt['current'].pop(0)
                volt['average'].pop(0)
                # Add new value
                volt['current'].append(float(value[0]))
                volt['average'].append(float(value[1]))
                # Update text value
                volt['text'] = other_values[idx + 1].rstrip() + "mW"
                # Store temperature value
                self.voltages[data] = volt
                # extra increase counter
                idx += 1
            # Update counter
            idx += 1
        # EMC status
        jetsonstats['EMC'] = self.emc
        # Add GPU status
        jetsonstats['GR3D'] = self.gpu
        # Add Temperatures and voltages
        jetsonstats['temperatures'] = self.temperatures
        jetsonstats['voltages'] = self.voltages
        return jetsonstats
# EOF
