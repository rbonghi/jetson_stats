#!/usr/bin/env python3
"""
Test script to show Jetson Thor engine layout and compare with other Jetson devices.
This demonstrates the difference between Thor (no DLA) and Orin (with DLA).
"""

from jtop.gui.pengine import pass_thor, pass_orin, pass_orin_nano, map_xavier, map_jetson_nano
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))


def simulate_engine_data():
    """Simulate engine data structure for testing"""
    return {
        'APE': {'APE': {'val': 50}},
        'NVENC': {'NVENC': {'val': 0}},
        'NVDEC': {'NVDEC': {'val': 0}},
        'NVJPG': {'NVJPG': {'val': 0}, 'NVJPG1': {'val': 0}},
        'SE': {'SE': {'val': 0}},
        'VIC': {'VIC': {'val': 0}},
        'DLA0': {'DLA0_CORE': {'val': 0}},  # This won't be shown for Thor
        'DLA1': {'DLA1_CORE': {'val': 0}},  # This won't be shown for Thor
        'PVA0': {'PVA0_CPU_AXI': {'val': 0}},  # This won't be shown for Thor
    }


def test_engine_mappings():
    """Test and compare different engine mappings"""
    print("Testing Jetson Engine Mappings")
    print("=" * 50)

    # Simulate engine data
    engine_data = simulate_engine_data()

    # Test Thor mapping
    print("\n🔹 Jetson Thor Engine Layout (pass_thor):")
    print("   Architecture: Blackwell GPU with 2560 cores, 96 Tensor Cores")
    print("   Note: NO DLA (Deep Learning Accelerator)")
    print("   Engines shown:")
    try:
        thor_engines = pass_thor(engine_data)
        for row in thor_engines:
            for engine_name, engine_data in row:
                print(f"     - {engine_name}")
    except Exception as e:
        print(f"     Error: {e}")

    # Test Orin mapping for comparison
    print("\n🔹 Jetson Orin Engine Layout (pass_orin):")
    print("   Architecture: Ampere GPU with DLA support")
    print("   Note: INCLUDES DLA (Deep Learning Accelerator)")
    print("   Engines shown:")
    try:
        orin_engines = pass_orin(engine_data)
        for row in orin_engines:
            for engine_name, engine_data in row:
                print(f"     - {engine_name}")
    except Exception as e:
        print(f"     Error: {e}")

    # Test Xavier mapping for comparison
    print("\n🔹 Jetson Xavier Engine Layout (map_xavier):")
    print("   Architecture: Volta GPU with DLA support")
    print("   Note: INCLUDES DLA and CVNAS")
    print("   Engines shown:")
    try:
        xavier_engines = map_xavier(engine_data)
        for row in xavier_engines:
            for engine_name, engine_data in row:
                print(f"     - {engine_name}")
    except Exception as e:
        print(f"     Error: {e}")

    # Test Nano mapping for comparison
    print("\n🔹 Jetson Nano Engine Layout (map_jetson_nano):")
    print("   Architecture: Maxwell GPU")
    print("   Note: Basic engines only")
    print("   Engines shown:")
    try:
        nano_engines = map_jetson_nano(engine_data)
        for row in nano_engines:
            for engine_name, engine_data in row:
                print(f"     - {engine_name}")
    except Exception as e:
        print(f"     Error: {e}")

    print("\n" + "=" * 50)
    print("Key Differences:")
    print("✅ Thor: No DLA, no PVA - focuses on GPU compute and video")
    print("✅ Orin: Has DLA, PVA - full AI acceleration suite")
    print("✅ Xavier: Has DLA, CVNAS - older AI acceleration")
    print("✅ Nano: Basic engines - minimal AI acceleration")


if __name__ == "__main__":
    test_engine_mappings()
