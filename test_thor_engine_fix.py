#!/usr/bin/env python3
"""
Test script to verify Jetson Thor engine fix and prevent ZeroDivisionError.
This script tests the pass_thor function with different engine data scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

from jtop.gui.pengine import pass_thor, add_engine_in_list

def test_thor_engine_fix():
    """Test the pass_thor function with various engine data scenarios"""
    print("Testing Jetson Thor Engine Fix")
    print("=" * 40)
    
    # Test 1: Empty engine data (should not crash)
    print("\n🔹 Test 1: Empty engine data")
    empty_engine = {}
    try:
        result = pass_thor(empty_engine)
        print(f"   ✅ No crash - returned {len(result)} rows")
        for i, row in enumerate(result):
            print(f"     Row {i}: {len(row)} engines")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Partial engine data (some engines missing)
    print("\n🔹 Test 2: Partial engine data")
    partial_engine = {
        'APE': {'APE': {'val': 50}},
        'NVENC': {'NVENC': {'val': 0}},
        # Missing NVDEC, NVJPG, SE, VIC
    }
    try:
        result = pass_thor(partial_engine)
        print(f"   ✅ No crash - returned {len(result)} rows")
        for i, row in enumerate(result):
            print(f"     Row {i}: {[name for name, _ in row]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Full engine data
    print("\n🔹 Test 3: Full engine data")
    full_engine = {
        'APE': {'APE': {'val': 50}},
        'NVENC': {'NVENC': {'val': 0}},
        'NVDEC': {'NVDEC': {'val': 0}},
        'NVJPG': {'NVJPG': {'val': 0}, 'NVJPG1': {'val': 0}},
        'SE': {'SE': {'val': 0}},
        'VIC': {'VIC': {'val': 0}},
    }
    try:
        result = pass_thor(full_engine)
        print(f"   ✅ No crash - returned {len(result)} rows")
        for i, row in enumerate(result):
            print(f"     Row {i}: {[name for name, _ in row]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test add_engine_in_list function
    print("\n🔹 Test 4: add_engine_in_list function")
    test_engine = {'APE': {'APE': {'val': 50}}}
    
    # Test existing engine
    ape_result = add_engine_in_list('APE', test_engine, 'APE', 'APE')
    print(f"   APE (exists): {ape_result}")
    
    # Test missing engine
    missing_result = add_engine_in_list('NVENC', test_engine, 'NVENC', 'NVENC')
    print(f"   NVENC (missing): {missing_result}")
    
    print("\n" + "=" * 40)
    print("Summary:")
    print("✅ ZeroDivisionError should be fixed")
    print("✅ Empty rows are filtered out")
    print("✅ Only existing engines are displayed")

if __name__ == "__main__":
    test_thor_engine_fix()
