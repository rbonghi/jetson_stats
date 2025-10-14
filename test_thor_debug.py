#!/usr/bin/env python3
"""
Test Jetson Thor frequency detection with debug logging.
This script runs the GPU detection once and shows the debug output.
"""

import logging
import sys
import os

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s - %(message)s')

# Add the jtop directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))


def test_thor_frequency_debug():
    """Test Thor frequency detection with debug output"""
    print("=== Jetson Thor Frequency Debug Test ===")

    try:
        from jtop.core.gpu import nvml_read_gpu_status
        from jtop.core.jetson_variables import get_jetson_variables

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

        print("\n2. Testing NVML GPU status detection...")
        gpu_data = nvml_read_gpu_status()
        print(f"   Found {len(gpu_data)} GPU devices")

        for gpu_name, gpu_info in gpu_data.items():
            print(f"\n   GPU: {gpu_name}")
            freq_info = gpu_info.get('freq', {})
            print(f"     Current: {freq_info.get('cur', 'N/A')} MHz")
            print(f"     Max: {freq_info.get('max', 'N/A')} MHz")
            print(f"     Min: {freq_info.get('min', 'N/A')} MHz")
            print(f"     Governor: {freq_info.get('governor', 'N/A')}")

            if freq_info.get('cur', 0) > 0:
                print("     ✅ SUCCESS: Frequency detected!")
            else:
                print("     ❌ FAILED: Still showing 0 frequency")

        print("\n3. Test completed. Check the debug messages above for details.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_thor_frequency_debug()
