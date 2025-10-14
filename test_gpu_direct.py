#!/usr/bin/env python3
"""
Direct test of GPU frequency detection without jtop module imports.
"""

import logging
import sys
import os

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s - %(message)s')

# Add the jtop directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

def test_gpu_direct():
    """Test GPU detection directly without jtop module"""
    print("=== Direct GPU Frequency Test ===")
    
    try:
        # Import only the specific functions we need
        from jtop.core.jetson_variables import get_jetson_variables
        from jtop.core.gpu import find_igpu, igpu_read_freq
        
        # Get Jetson info
        print("\n1. Getting Jetson hardware info...")
        jetson_vars = get_jetson_variables()
        soc = jetson_vars.get('SoC', '')
        is_thor = 'tegra264' in soc or 'tegra26x' in soc
        print(f"   SoC: {soc}")
        print(f"   Is Thor: {is_thor}")
        
        if not is_thor:
            print("   ❌ This is not a Jetson Thor device")
            return
        
        print("\n2. Testing traditional GPU device detection...")
        gpu_devices = find_igpu("/sys/class/devfreq/")
        print(f"   Found {len(gpu_devices)} GPU devices in /sys/class/devfreq/")
        
        for gpu_name, gpu_data in gpu_devices.items():
            print(f"   GPU: {gpu_name}")
            print(f"     Type: {gpu_data.get('type')}")
            print(f"     Path: {gpu_data.get('path')}")
            print(f"     Freq Path: {gpu_data.get('frq_path')}")
            
            if gpu_data.get('type') == 'integrated':
                print(f"     Testing frequency reading...")
                freq_info = igpu_read_freq(gpu_data.get('frq_path', ''))
                print(f"     Frequency info: {freq_info}")
                
                if freq_info and freq_info.get('cur', 0) > 0:
                    print(f"     ✅ SUCCESS: Current frequency = {freq_info.get('cur')} MHz")
                else:
                    print(f"     ❌ FAILED: No valid frequency data")
        
        # Try alternative paths
        print("\n3. Testing alternative GPU paths...")
        alt_paths = [
            "/sys/devices/platform/17000000.gpu",
            "/sys/devices/platform/17000000.gv11b", 
            "/sys/devices/platform/17000000.tegra264"
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                print(f"   Found: {alt_path}")
                devfreq_subdir = os.path.join(alt_path, "devfreq")
                if os.path.exists(devfreq_subdir):
                    print(f"     Found devfreq: {devfreq_subdir}")
                    alt_devices = find_igpu(devfreq_subdir)
                    print(f"     Found {len(alt_devices)} devices in alternative path")
                    
                    for gpu_name, gpu_data in alt_devices.items():
                        print(f"     GPU: {gpu_name}")
                        if gpu_data.get('type') == 'integrated':
                            freq_info = igpu_read_freq(gpu_data.get('frq_path', ''))
                            print(f"     Frequency info: {freq_info}")
            else:
                print(f"   Not found: {alt_path}")
        
        print("\n4. Test completed.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gpu_direct()
