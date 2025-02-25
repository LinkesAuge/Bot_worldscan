#!/usr/bin/env python3
"""
Translator Launcher

This script provides a simple way to launch the translator application
that helps with testing translations and visualizing layout issues.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure that the scout package is in the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scout.translations.translator_app import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main() 