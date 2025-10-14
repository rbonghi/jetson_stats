#!/usr/bin/env python3
"""
Run jtop with debug logging using the installed jtop package.
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

# Run the installed jtop with debug logging
if __name__ == "__main__":
    try:
        # Use subprocess to run jtop with our logging configuration
        import subprocess
        import signal

        def signal_handler(sig, frame):
            print(f"\nStopped. Check the log file: {log_file}")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # Run jtop
        subprocess.run(['jtop'], check=True)

    except KeyboardInterrupt:
        print(f"\nStopped. Check the log file: {log_file}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Check the log file: {log_file}")
