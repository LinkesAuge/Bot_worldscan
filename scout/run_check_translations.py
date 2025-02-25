#!/usr/bin/env python3
"""
Translation Checker Launcher

This script launches the translation checker that scans the codebase for
potential translation and layout issues, such as hardcoded strings and
layout problems. It sets up the proper environment and executes the checker.
"""

import os
import sys
import logging
from pathlib import Path

# Ensure the scout package is in the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the checker
from scout.translations.check_translations import main as run_checker

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Run the checker
    try:
        run_checker()
    except Exception as e:
        logging.error(f"Error running translation checker: {str(e)}")
        sys.exit(1) 