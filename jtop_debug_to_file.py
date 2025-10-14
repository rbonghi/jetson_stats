#!/usr/bin/env python3
"""
Run jtop with debug logging enabled and save logs to a file.
This script sets the logging level to DEBUG and saves logs to jtop_debug.log
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

# Add the jtop directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

# Import and run jtop
from jtop.__main__ import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\nStopped. Check the log file: {log_file}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Check the log file: {log_file}")
