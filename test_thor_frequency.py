#!/usr/bin/env python3
"""
Test script to verify Jetson Thor frequency detection fix.
This script tests both NVML and traditional frequency detection methods.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

from jtop.core.gpu import nvml_read_gpu_status, find_igpu, igpu_read_freq
from jtop.core.jetson_variables import get_jetson_variables

def test_thor_frequency_detection():
    """Test frequency detection on Jetson Thor"""
    print("Testing Jetson Thor frequency detection...")
    
    # Get Jetson hardware info
    jetson_vars = get_jetson_variables()
    print(f"Detected SoC: {jetson_vars.get('SoC', 'Unknown')}")
    print(f"Detected Module: {jetson_vars.get('Module', 'Unknown')}")
    print(f"Detected L4T: {jetson_vars.get('L4T', 'Unknown')}")
    print(f"Detected JetPack: {jetson_vars.get('Jetpack', 'Unknown')}")
    
    # Check if this is Jetson Thor
    soc = jetson_vars.get('SoC', '')
    is_thor = 'tegra264' in soc or 'tegra26x' in soc
    print(f"Is Jetson Thor: {is_thor}")
    
    if is_thor:
        print("\n=== Testing NVML Method ===")
        try:
            gpu_data = nvml_read_gpu_status()
            for gpu_name, gpu_info in gpu_data.items():
                print(f"GPU: {gpu_name}")
                freq_info = gpu_info.get('freq', {})
                print(f"  Current Frequency: {freq_info.get('cur', 'N/A')} MHz")
                print(f"  Max Frequency: {freq_info.get('max', 'N/A')} MHz")
                print(f"  Min Frequency: {freq_info.get('min', 'N/A')} MHz")
                print(f"  Governor: {freq_info.get('governor', 'N/A')}")
                if 'GPC' in freq_info:
                    print(f"  GPC Frequencies: {freq_info['GPC']} MHz")
        except Exception as e:
            print(f"NVML method failed: {e}")
        
        print("\n=== Testing Traditional Method ===")
        try:
            gpu_devices = find_igpu("/sys/class/devfreq/")
            for gpu_name, gpu_data in gpu_devices.items():
                print(f"GPU Device: {gpu_name}")
                print(f"  Type: {gpu_data.get('type', 'Unknown')}")
                print(f"  Path: {gpu_data.get('path', 'Unknown')}")
                print(f"  Freq Path: {gpu_data.get('frq_path', 'Unknown')}")
                
                if gpu_data.get('type') == 'integrated':
                    freq_info = igpu_read_freq(gpu_data.get('frq_path', ''))
                    if freq_info:
                        print(f"  Current Frequency: {freq_info.get('cur', 'N/A')} MHz")
                        print(f"  Max Frequency: {freq_info.get('max', 'N/A')} MHz")
                        print(f"  Min Frequency: {freq_info.get('min', 'N/A')} MHz")
                        print(f"  Governor: {freq_info.get('governor', 'N/A')}")
                        if 'GPC' in freq_info:
                            print(f"  GPC Frequencies: {freq_info['GPC']} MHz")
                    else:
                        print("  No frequency information available")
        except Exception as e:
            print(f"Traditional method failed: {e}")
    else:
        print("This is not a Jetson Thor device. The fix is specifically for Jetson Thor.")

if __name__ == "__main__":
    test_thor_frequency_detection()
