#!/usr/bin/env python3
"""
Run jtop with debug logging using environment variables.
"""

import os
import sys
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

# Create a Python script that sets up logging and runs jtop
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

# Add the jtop directory to the path
sys.path.insert(0, '{os.path.dirname(__file__)}/jtop')

# Import and run jtop
try:
    from jtop.__main__ import main
    main()
except Exception as e:
    print(f"Error: {{e}}")
    import traceback
    traceback.print_exc()
"""

# Write the script to a temporary file
script_file = 'temp_jtop_debug.py'
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
