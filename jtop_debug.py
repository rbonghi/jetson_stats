#!/usr/bin/env python3
"""
Run jtop with debug logging enabled.
This script sets the logging level to DEBUG before starting jtop.
"""

import logging
import sys
import os

# Set logging level to DEBUG
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s - %(message)s')

# Add the jtop directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jtop'))

# Import and run jtop
from jtop.__main__ import main

if __name__ == "__main__":
    main()
