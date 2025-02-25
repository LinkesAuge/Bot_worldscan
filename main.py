#!/usr/bin/env python3
"""
Scout - Game Automation and Detection Tool

This is the main entry point for the Scout application.
It handles command-line arguments, logging setup, and launching the application.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
import traceback
from PyQt6.QtWidgets import QApplication

# Import the main window class
from scout.ui.main_window import run_application
from scout.core.utils.codes import Codes


def setup_logging(log_level: str, log_file: str = None) -> None:
    """
    Set up logging for the application.
    
    Args:
        log_level: The log level (debug, info, warning, error, critical)
        log_file: Optional path to log file
    """
    # Convert log level string to logging constant
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = level_map.get(log_level.lower(), logging.INFO)
    
    # Create log formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        try:
            # Create directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
            
            root_logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            root_logger.error(f"Failed to set up file logging: {e}")
    
    # Log basic info
    root_logger.info(f"Logging initialized with level: {log_level}")


def create_default_directories() -> None:
    """Create default directories for templates, sequences, etc."""
    logger = logging.getLogger(__name__)
    
    try:
        # Create resource directories
        resource_dirs = [
            "resources/templates",
            "resources/sequences",
            "resources/logs",
            "resources/states",
        ]
        
        for dir_path in resource_dirs:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
        
        logger.info("Default directories created successfully")
    except Exception as e:
        logger.error(f"Failed to create default directories: {e}")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Scout - Game Automation and Detection Tool"
    )
    
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level"
    )
    
    parser.add_argument(
        "--log-file",
        default="resources/logs/scout.log",
        help="Path to log file"
    )
    
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run in headless mode (no GUI)"
    )
    
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Check for updates on startup (even if disabled in settings)"
    )
    
    parser.add_argument(
        "--no-check-updates",
        action="store_true",
        help="Don't check for updates on startup (overrides settings)"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command-line arguments
        args = parse_args()
        
        # Set up logging
        setup_logging(args.log_level, args.log_file)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Scout application")
        
        # Create default directories
        create_default_directories()
        
        # Run the application
        if args.no_gui:
            logger.info("Running in headless mode")
            # TODO: Implement headless mode
            return Codes.SUCCESS
        else:
            logger.info("Starting GUI application")
            
            # Set update flags based on command-line arguments
            update_check_flags = {}
            if args.check_updates:
                update_check_flags["force_check"] = True
            if args.no_check_updates:
                update_check_flags["skip_check"] = True
            
            # Run the application and get exit code
            exit_code = run_application(**update_check_flags)
            
            # Handle special exit codes
            if exit_code == Codes.UPDATE_CODE:
                logger.info("Application exited for update")
                # Could add additional actions here if needed
                
            return exit_code
        
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        return Codes.GENERAL_ERROR


if __name__ == "__main__":
    sys.exit(main()) 