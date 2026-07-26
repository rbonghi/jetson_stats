# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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

from .jetson_variables import get_jetson_variables
from .common import cat
import os
import logging
import platform
# Load distro library from python3 or use platform
try:
    import distro
except ImportError:
    distro = platform
# Create logger
logger = logging.getLogger(__name__)

# (implementer_id, part_id) -> (model_name, isa_string)
_ARM_CPU_PARTS = {
    (0x41, 0xd03): ("Cortex-A53", "Armv8-A"),
    (0x41, 0xd07): ("Cortex-A57", "Armv8-A"),
    (0x41, 0xd08): ("Cortex-A72", "Armv8-A"),
    (0x41, 0xd09): ("Cortex-A73", "Armv8-A"),
    (0x41, 0xd0a): ("Cortex-A75", "Armv8.2-A"),
    (0x41, 0xd0b): ("Cortex-A76", "Armv8.2-A"),
    (0x41, 0xd0c): ("Neoverse N1", "Armv8.2-A"),
    (0x41, 0xd0d): ("Cortex-A77", "Armv8.2-A"),
    (0x41, 0xd0e): ("Cortex-A76AE", "Armv8.2-A"),
    (0x41, 0xd40): ("Neoverse V1", "Armv8.4-A"),
    (0x41, 0xd41): ("Cortex-A78", "Armv8.2-A"),
    (0x41, 0xd42): ("Cortex-A78AE", "Armv8.2-A"),
    (0x41, 0xd44): ("Cortex-X1", "Armv8.2-A"),
    (0x41, 0xd46): ("Cortex-A510", "Armv9-A"),
    (0x41, 0xd47): ("Cortex-A710", "Armv9-A"),
    (0x41, 0xd48): ("Cortex-X2", "Armv9-A"),
    (0x41, 0xd49): ("Neoverse N2", "Armv9-A"),
    (0x41, 0xd4d): ("Cortex-A715", "Armv9-A"),
    (0x41, 0xd4e): ("Cortex-X3", "Armv9-A"),
    (0x41, 0xd4f): ("Cortex-X4", "Armv9.2-A"),
    (0x41, 0xd80): ("Cortex-A520", "Armv9.2-A"),
    (0x41, 0xd81): ("Cortex-A720", "Armv9.2-A"),
    (0x41, 0xd83): ("Neoverse V3AE", "Armv9.2-A"),
    (0x41, 0xd84): ("Neoverse V3", "Armv9.2-A"),
    (0x4e, 0x004): ("Carmel", "Armv8.2-A"),
}


def _parse_first_cpuinfo_block():
    info = {}
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                line = line.strip()
                if not line and info:
                    break
                if ':' in line:
                    key, _, val = line.partition(':')
                    info[key.strip()] = val.strip()
    except OSError:
        pass
    return info


def _count_online_cpus():
    try:
        with open('/sys/devices/system/cpu/online', 'r') as f:
            data = f.read().strip()
        count = 0
        for part in data.split(','):
            if '-' in part:
                lo, hi = part.split('-')
                count += int(hi) - int(lo) + 1
            else:
                count += 1
        return count
    except (OSError, ValueError):
        return os.cpu_count() or 1


def _read_cache_total(num_cpus):
    cache = {}
    base = '/sys/devices/system/cpu/cpu0/cache'
    try:
        indexes = sorted(os.listdir(base))
    except OSError:
        return cache
    for idx in indexes:
        idx_path = os.path.join(base, idx)
        try:
            level = int(open(os.path.join(idx_path, 'level')).read().strip())
            ctype = open(os.path.join(idx_path, 'type')).read().strip()
            raw = open(os.path.join(idx_path, 'size')).read().strip()
        except OSError:
            continue
        mults = {'K': 1024, 'M': 1024 * 1024, 'G': 1024 * 1024 * 1024}
        try:
            size_bytes = int(raw[:-1]) * mults[raw[-1]] if raw[-1] in mults else int(raw)
        except (ValueError, IndexError):
            continue
        total = size_bytes * num_cpus
        if level == 1 and ctype == 'Data':
            cache['L1 Data Cache'] = str(total)
        elif level == 1 and ctype == 'Instruction':
            cache['L1 Instruction Cache'] = str(total)
        elif level == 2:
            cache['L2 Cache'] = str(total)
        elif level == 3:
            cache['L3 Cache'] = str(total)
    return cache


def _decode_arm_features(features_str):
    feats = set(features_str.lower().split())
    result = {}

    vec = []
    if 'asimd' in feats or 'neon' in feats:
        vec.append('NEON')
    if 'sve' in feats:
        vec.append('SVE')
    if 'sve2' in feats:
        vec.append('SVE2')
    if vec:
        result['Vector ISA'] = ', '.join(vec)

    try:
        with open('/proc/sys/abi/sve_default_vector_length', 'r') as f:
            result['SVE vector size'] = '{} bits'.format(int(f.read().strip()) * 8)
    except (OSError, ValueError):
        pass

    num = []
    if 'fphp' in feats or 'fp' in feats:
        num.append('FP16')
    if 'bf16' in feats or 'svebf16' in feats:
        num.append('BF16')
    if num:
        result['Numeric formats'] = ', '.join(num)

    iml = []
    if 'asimddp' in feats:
        iml.append('INT8 Dot Product')
    if 'i8mm' in feats or 'svei8mm' in feats:
        iml.append('INT8 Matrix Multiply')
    if iml:
        result['Integer ML'] = ', '.join(iml)

    if 'lse' in feats or 'atomics' in feats:
        result['Atomics'] = 'Arm LSE'

    sec = []
    if 'paca' in feats or 'pacg' in feats:
        sec.append('PAC')
    if 'bti' in feats:
        sec.append('BTI')
    if 'dit' in feats:
        sec.append('DIT')
    if 'ssbs' in feats:
        sec.append('SSBS')
    if 'sb' in feats:
        sec.append('SB')
    if sec:
        result['Security'] = ', '.join(sec)

    cryp = []
    if 'aes' in feats or 'sveaes' in feats:
        cryp.append('AES')
    if 'sha1' in feats:
        cryp.append('SHA-1')
    sha_vers = [v for f, v in [('sha2', '2'), ('sha3', '3'), ('sha512', '512')]
                if f in feats or 'sve' + f in feats]
    if sha_vers:
        cryp.append('SHA-{}'.format('/'.join(sha_vers)))
    if 'sm3' in feats:
        cryp.append('SM3')
    if 'sm4' in feats or 'svesm4' in feats:
        cryp.append('SM4')
    if 'crc32' in feats:
        cryp.append('CRC32')
    if cryp:
        result['Cryptography'] = ', '.join(cryp)

    return result


def get_cpu_static_info():
    """Collect static AArch64 CPU info from /proc/cpuinfo and sysfs."""
    if platform.machine() != 'aarch64':
        return {}
    cpuinfo = _parse_first_cpuinfo_block()
    if not cpuinfo:
        return {}
    num_cpus = _count_online_cpus()
    try:
        implementer = int(cpuinfo.get('CPU implementer', '0x0'), 16)
        variant = int(cpuinfo.get('CPU variant', '0x0'), 16)
        part = int(cpuinfo.get('CPU part', '0x0'), 16)
        revision = int(cpuinfo.get('CPU revision', '0'), 10)
    except ValueError:
        implementer, variant, part, revision = 0, 0, 0, 0
    # MIDR_EL1: [31:24]=implementer [23:20]=variant [19:16]=0xf [15:4]=part [3:0]=revision
    midr = (implementer << 24) | (variant << 20) | (0xf << 16) | (part << 4) | revision
    model_name, isa_string = _ARM_CPU_PARTS.get((implementer, part), (None, None))
    if not model_name:
        model_name = '0x{:04x}'.format(part)
    arch = '{}'.format(isa_string) if isa_string else 'AArch64'
    result = {
        'Model': 'Arm {}'.format(model_name),
        'Architecture': arch,
        'Configuration': '{} cores'.format(num_cpus),
        'Revision': 'r{}p{}'.format(variant, revision),
        'MIDR': '0x{:08x}'.format(midr),
    }
    result.update(_decode_arm_features(cpuinfo.get('Features', '')))
    result.update(_read_cache_total(num_cpus))
    return result


def get_parameter(path):
    if os.path.isfile(path):
        return cat(path).strip()


def get_platform_variables():
    return {
        'Machine': platform.machine(),
        'System': platform.system(),
        'Distribution': " ".join(distro.linux_distribution()),
        'Release': platform.release(),
        'Python': platform.python_version(),
    }


def get_x86_64_variables():
    hardware = {}
    hardware_path = "/sys/devices/virtual/dmi/id/"
    items = os.listdir(hardware_path)
    for item in sorted(items):
        if item in ['uevent', 'modalias', 'board_serial', 'bios_release', 'product_uuid', 'chassis_type']:
            continue
        path = os.path.join(hardware_path, item)
        output = ""
        if os.path.isfile(path):
            output = cat(path).strip()
        if not output or output == 'Default string':
            continue
        name = item.replace("_", " ").capitalize()
        hardware[name] = output
    return hardware


def get_hardware():
    # If hardware is ARM check if NVIDIA Jetson
    platform_board = platform.machine()
    logger.info("Hardware detected {}".format(platform_board))
    if platform_board == 'aarch64':
        # Load Jetson data
        jetson = get_jetson_variables()
        # Print main jetson variables
        if '699-level Part Number' in jetson:
            logger.info("NVIDIA Jetson 699-level Part Number={}".format(jetson['699-level Part Number']))
        else:
            logger.error("NVIDIA Jetson No 699-level Part Number detected!")
        if 'Module' in jetson:
            logger.info("NVIDIA Jetson Module={}".format(jetson['Module']))
        else:
            logger.error("NVIDIA Jetson No Module detected!")
        # Check L4T detection
        if jetson['L4T']:
            logger.info("NVIDIA Jetson detected L4T={}".format(jetson['L4T']))
        else:
            logger.error("NVIDIA Jetson L4T not detected!")
        return jetson
    elif platform_board == 'x86_64':
        return get_x86_64_variables()
    else:
        logger.warning("Unrecognized board {}".format(platform_board))
        return {}
# EOF
