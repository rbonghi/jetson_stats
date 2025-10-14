#!/usr/bin/env python3
"""
Test script to verify Jetson Thor GUI warning fix.
This script tests the engine_model function to ensure Jetson Thor is properly recognized.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

from jtop.gui.pengine import engine_model
from jtop.core.jetson_variables import get_jetson_variables

def test_thor_gui_recognition():
    """Test that Jetson Thor is properly recognized by the GUI engine model function"""
    print("Testing Jetson Thor GUI recognition...")
    
    # Get Jetson hardware info
    jetson_vars = get_jetson_variables()
    module = jetson_vars.get('Module', '')
    print(f"Detected Module: {module}")
    
    if module:
        # Test the engine_model function
        engine_func = engine_model(module)
        
        if engine_func:
            print(f"✅ SUCCESS: Module '{module}' is recognized by GUI engine model")
            print(f"   Engine function: {engine_func.__name__}")
            
            # Check if it's using the correct Thor-specific function
            if engine_func.__name__ == 'pass_thor':
                print("   ✅ Using Thor-specific engine mapping (no DLA)")
            elif engine_func.__name__ == 'pass_orin':
                print("   ⚠️  Using Orin engine mapping (may include DLA)")
            else:
                print(f"   ℹ️  Using {engine_func.__name__} engine mapping")
        else:
            print(f"❌ FAILED: Module '{module}' is NOT recognized by GUI engine model")
            print("   This will cause the 'Module missing in jtop GUI' warning")
            
        # Test various module name variations
        test_names = [
            "NVIDIA Jetson AGX Thor (Developer kit)",
            "NVIDIA Jetson AGX Thor",
            "AGX Thor",
            "Thor",
            "Jetson Thor"
        ]
        
        print("\nTesting various module name variations:")
        for test_name in test_names:
            result = engine_model(test_name)
            status = "✅" if result else "❌"
            func_name = result.__name__ if result else "None"
            print(f"   {status} '{test_name}': {'Recognized' if result else 'Not recognized'} ({func_name})")
    else:
        print("❌ No module detected. This might indicate a hardware detection issue.")

if __name__ == "__main__":
    test_thor_gui_recognition()
