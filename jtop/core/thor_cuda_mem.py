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

# jtop/core/thor_cuda_mem.py
import ctypes
from ctypes import byref, c_int, c_void_p, c_uint, c_size_t
from contextlib import contextmanager

# Lazy-loaded CUDA driver
_libcuda = None

def _cuda():
    global _libcuda
    if _libcuda is None:
        _libcuda = ctypes.CDLL("libcuda.so")

    # Prototypes (CUDA Driver API)
    _libcuda.cuInit.argtypes = [c_uint]
    _libcuda.cuInit.restype = c_int

    _libcuda.cuDeviceGet.argtypes = [ctypes.POINTER(c_int), c_int]
    _libcuda.cuDeviceGet.restype = c_int

    _libcuda.cuDevicePrimaryCtxRetain.argtypes = [ctypes.POINTER(c_void_p), c_int]
    _libcuda.cuDevicePrimaryCtxRetain.restype = c_int

    _libcuda.cuDevicePrimaryCtxRelease.argtypes = [c_int]
    _libcuda.cuDevicePrimaryCtxRelease.restype = c_int

    _libcuda.cuCtxPushCurrent_v2.argtypes = [c_void_p]
    _libcuda.cuCtxPushCurrent_v2.restype = c_int

    _libcuda.cuCtxPopCurrent_v2.argtypes = [ctypes.POINTER(c_void_p)]
    _libcuda.cuCtxPopCurrent_v2.restype = c_int

    _libcuda.cuMemGetInfo_v2.argtypes = [ctypes.POINTER(c_size_t), ctypes.POINTER(c_size_t)]
    _libcuda.cuMemGetInfo_v2.restype = c_int

    return _libcuda

@contextmanager
def _pushed_primary_ctx(device_index: int = 0):
    """Retains device's primary context and pushes it current; always pops/releases."""
    lib = _cuda()
    dev = c_int(device_index)
    ctx = c_void_p(0)

    # Init + device
    rc = lib.cuInit(0)  # CU_SUCCESS == 0
    if rc != 0:
        raise RuntimeError(f"cuInit rc={rc}")

    rc = lib.cuDeviceGet(byref(dev), device_index)
    if rc != 0:
        raise RuntimeError(f"cuDeviceGet rc={rc}")

    # Retain + push
    rc = lib.cuDevicePrimaryCtxRetain(byref(ctx), dev.value)
    if rc != 0:
        raise RuntimeError(f"cuDevicePrimaryCtxRetain rc={rc}")

    try:
        rc = lib.cuCtxPushCurrent_v2(ctx)
        if rc != 0:
            raise RuntimeError(f"cuCtxPushCurrent rc={rc}")
        try:
            yield
        finally:
            popped = c_void_p(0)
            lib.cuCtxPopCurrent_v2(byref(popped))
    finally:
        lib.cuDevicePrimaryCtxRelease(dev.value)

def cuda_gpu_mem_bytes(device_index: int = 0, verbose: bool = False):
    """
    Returns (used_bytes, total_bytes) via CUDA Driver API.
    Uses the device's PRIMARY context (safe to call while other apps run).
    """
    try:
        lib = _cuda()
    except OSError as e:
        if verbose:
            print(f"[cuda] libcuda.so not found: {e}")
        return None

    try:
        with _pushed_primary_ctx(device_index):
            free_b = c_size_t(0)
            total_b = c_size_t(0)
            rc = lib.cuMemGetInfo_v2(byref(free_b), byref(total_b))
            if rc != 0:
                if verbose:
                    print(f"[cuda] cuMemGetInfo rc={rc}")
                return None
            used = int(total_b.value) - int(free_b.value)
            return used, int(total_b.value)
    except Exception as e:
        if verbose:
            print(f"[cuda] exception: {e}")
        return None

# EOF

