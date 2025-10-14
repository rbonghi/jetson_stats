#!/usr/bin/env python3
"""
Simple test for Jetson Thor frequency detection.
This script tests the NVML fallback logic directly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

def test_thor_frequency_simple():
    """Test the Thor frequency detection with simple logging"""
    print("Testing Jetson Thor frequency detection...")
    
    try:
        from jtop.core.gpu import nvml_read_gpu_status
        from jtop.core.jetson_variables import get_jetson_variables
        
        # Get Jetson info
        jetson_vars = get_jetson_variables()
        soc = jetson_vars.get('SoC', '')
        is_thor = 'tegra264' in soc or 'tegra26x' in soc
        print(f"SoC: {soc}")
        print(f"Is Thor: {is_thor}")
        
        if is_thor:
            print("\nTesting NVML GPU status...")
            gpu_data = nvml_read_gpu_status()
            print(f"Found {len(gpu_data)} GPU devices")
            
            for gpu_name, gpu_info in gpu_data.items():
                print(f"\nGPU: {gpu_name}")
                freq_info = gpu_info.get('freq', {})
                print(f"  Current: {freq_info.get('cur', 'N/A')} MHz")
                print(f"  Max: {freq_info.get('max', 'N/A')} MHz")
                print(f"  Min: {freq_info.get('min', 'N/A')} MHz")
                print(f"  Governor: {freq_info.get('governor', 'N/A')}")
                
                if freq_info.get('cur', 0) > 0:
                    print("  ✅ SUCCESS: Frequency detected!")
                else:
                    print("  ❌ FAILED: Still showing 0 frequency")
        else:
            print("Not a Jetson Thor device")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_thor_frequency_simple()
