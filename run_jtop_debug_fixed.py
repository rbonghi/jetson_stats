#!/usr/bin/env python3
"""
Run jtop with debug logging enabled using the proper module import method.
"""

import logging
import sys
import os
from datetime import datetime

# Create a log file with timestamp
log_file = f"jtop_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

print(f"Debug logs will be saved to: {log_file}")
print("Starting jtop with debug logging...")
print("Press Ctrl+C to stop and check the log file")

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Run jtop as a module
if __name__ == "__main__":
    try:
        # Import and run jtop as a module
        import jtop
        jtop.main()
    except KeyboardInterrupt:
        print(f"\nStopped. Check the log file: {log_file}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Check the log file: {log_file}")
