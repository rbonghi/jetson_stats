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


import os
# Launch command
import subprocess as sp
# Logging
import logging
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


def get_uptime():
    """ Read uptime system
        http://planzero.org/blog/2012/01/26/system_uptime_in_python,_a_better_way
    """
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def status_disk(folder="/var/"):
    disk = os.statvfs(folder)
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
# EOF
