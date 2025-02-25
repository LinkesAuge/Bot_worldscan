#!/usr/bin/env python3
"""
Debug script for the Scout application.

This script runs the main application with additional error handling to diagnose issues.
"""

import sys
import traceback
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("debug")

def main():
    """Run the application with error handling."""
    try:
        logger.info("Starting Scout application in debug mode")
        
        # Import and run the application
        from scout.ui.main_window import run_application
        run_application()
        
        return 0
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(traceback.format_exc())
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 