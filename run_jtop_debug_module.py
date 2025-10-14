#!/usr/bin/env python3
"""
Run jtop with debug logging using module execution.
"""

import logging
import sys
import os
import subprocess
from datetime import datetime

# Create a log file with timestamp
log_file = f"jtop_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

print(f"Debug logs will be saved to: {log_file}")
print("Starting jtop with debug logging...")
print("Press Ctrl+C to stop and check the log file")

# Set up environment for debug logging
env = os.environ.copy()
env['PYTHONPATH'] = os.path.dirname(__file__) + ':' + env.get('PYTHONPATH', '')

# Create a Python script that sets up logging and runs jtop as a module
python_script = f"""
import logging
import sys
import os

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('{log_file}'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the current directory to Python path
sys.path.insert(0, '{os.path.dirname(__file__)}')

# Run jtop as a module
try:
    import jtop
    jtop.main()
except Exception as e:
    print(f"Error: {{e}}")
    import traceback
    traceback.print_exc()
"""

# Write the script to a temporary file
script_file = 'temp_jtop_debug_module.py'
with open(script_file, 'w') as f:
    f.write(python_script)

try:
    # Run the script
    subprocess.run([sys.executable, script_file], env=env)
finally:
    # Clean up
    if os.path.exists(script_file):
        os.remove(script_file)

    print(f"\nCheck the log file: {log_file}")
