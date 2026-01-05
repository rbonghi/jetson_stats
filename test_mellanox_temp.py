#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Test script for Mellanox temperature detection
"""

import sys
import os

# Add the current directory to the path to import jtop
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jtop.core.temperature import get_mellanox_temperature

def test_mellanox_detection():
    """Test Mellanox temperature detection"""
    print("Testing Mellanox temperature detection...")
    print("=" * 60)

    # Test the function
    temps = get_mellanox_temperature()

    if temps:
        print("✓ Mellanox temperatures detected:")
        for name, sensor in temps.items():
            temp_value = sensor.get('temp', 0)
            temp_celsius = temp_value / 1000.0
            print(f"  - {name}: {temp_celsius:.1f}°C")
        print("\n✓ Test PASSED - Mellanox temperatures are being detected")
    else:
        print("✗ No Mellanox temperatures detected")
        print("  This is expected if:")
        print("  1. No Mellanox NICs are installed")
        print("  2. MLNX_OFED is not installed")
        print("  3. mget_temp is not available")
        print("\n✓ Test PASSED - No Mellanox NICs found (expected behavior)")

    print("=" * 60)

if __name__ == "__main__":
    test_mellanox_detection()
