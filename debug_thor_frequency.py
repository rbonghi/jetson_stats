#!/usr/bin/env python3
"""
Debug script for Jetson Thor frequency detection.
This script can be run directly on the Jetson Thor to debug the frequency issue.
"""

import os
import sys


def debug_thor_frequency():
    """Debug Jetson Thor frequency detection step by step"""
    print("=== Jetson Thor Frequency Debug ===")

    # Check if we're on a Jetson device
    if not os.path.exists('/sys/firmware/devicetree/base/model'):
        print("❌ Not running on a Jetson device")
        return

    model = open('/sys/firmware/devicetree/base/model', 'r').read().strip()
    print(f"📱 Model: {model}")

    # Check SoC
    if os.path.exists('/proc/device-tree/compatible'):
        compatible = open('/proc/device-tree/compatible', 'r').read().strip()
        soc = compatible.split(',')[-1]
        print(f"🔧 SoC: {soc}")
        is_thor = 'tegra264' in soc or 'tegra26x' in soc
        print(f"🎯 Is Jetson Thor: {is_thor}")
    else:
        print("❌ Cannot determine SoC")
        return

    if not is_thor:
        print("⚠️  This script is designed for Jetson Thor")
        return

    # Check devfreq directory
    devfreq_path = "/sys/class/devfreq/"
    print(f"\n📁 Checking devfreq directory: {devfreq_path}")
    if os.path.exists(devfreq_path):
        devices = os.listdir(devfreq_path)
        print(f"   Found {len(devices)} devices: {devices}")

        for device in devices:
            device_path = os.path.join(devfreq_path, device)
            print(f"\n🔍 Device: {device}")
            print(f"   Path: {device_path}")

            # Check if it's a directory
            if not os.path.isdir(device_path):
                print("   ❌ Not a directory, skipping")
                continue

            # Check device name
            name_path = os.path.join(device_path, "device", "of_node", "name")
            if os.path.exists(name_path):
                name = open(name_path, 'r').read().strip()
                print(f"   📛 Name: {name}")

                # Check frequency files
                freq_files = ['cur_freq', 'max_freq', 'min_freq', 'governor']
                for freq_file in freq_files:
                    file_path = os.path.join(device_path, freq_file)
                    if os.path.exists(file_path):
                        try:
                            value = open(file_path, 'r').read().strip()
                            print(f"   📊 {freq_file}: {value}")
                        except Exception as e:
                            print(f"   ❌ Error reading {freq_file}: {e}")
                    else:
                        print(f"   ❌ Missing {freq_file}")
            else:
                print("   ❌ No device name found")
    else:
        print("❌ devfreq directory not found")

    # Check NVML availability
    print(f"\n🔧 Checking NVML availability...")
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        print(f"   ✅ NVML available, {device_count} devices")

        for idx in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
            name = pynvml.nvmlDeviceGetName(handle)
            print(f"   📱 Device {idx}: {name}")

            # Try to get clock info
            try:
                sm_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_SM)
                print(f"   📊 SM Clock: {sm_clock} MHz")
            except Exception as e:
                print(f"   ❌ SM Clock error: {e}")

            try:
                max_sm_clock = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_SM)
                print(f"   📊 Max SM Clock: {max_sm_clock} MHz")
            except Exception as e:
                print(f"   ❌ Max SM Clock error: {e}")

        pynvml.nvmlShutdown()
    except ImportError:
        print("   ❌ NVML not available")
    except Exception as e:
        print(f"   ❌ NVML error: {e}")

    # Check for alternative GPU frequency sources
    print(f"\n🔍 Checking alternative GPU frequency sources...")
    alt_paths = [
        "/sys/kernel/debug/clk",
        "/sys/devices/platform/17000000.gpu",
        "/sys/devices/platform/17000000.gv11b",
        "/sys/devices/platform/17000000.tegra264",
    ]

    for path in alt_paths:
        if os.path.exists(path):
            print(f"   ✅ Found: {path}")
            if os.path.isdir(path):
                try:
                    contents = os.listdir(path)
                    print(f"      Contents: {contents[:10]}...")  # Show first 10 items
                except Exception as e:
                    print(f"      Error listing: {e}")
        else:
            print(f"   ❌ Not found: {path}")


if __name__ == "__main__":
    debug_thor_frequency()
