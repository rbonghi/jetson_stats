#!/bin/bash
# Run jtop with debug logging enabled using environment variables

# Set Python logging level to DEBUG
export PYTHONPATH="/Users/johnunez/Projects/jetson_stats:$PYTHONPATH"

# Run jtop with debug logging
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s - %(message)s')
import sys
sys.path.insert(0, '/Users/johnunez/Projects/jetson_stats/jtop')
from jtop.__main__ import main
main()
"
