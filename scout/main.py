#!/usr/bin/env python
"""
Scout - Game Automation Assistant

This is the main entry point for the Scout application.
It initializes the application, sets up logging, and launches the UI.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QDir, Qt

from scout.ui.main_window import MainWindow
from scout.core.services.service_locator import ServiceLocator


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
    """
    # Convert string level to numeric level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    handlers = []
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    handlers.append(console_handler)
    
    # Add file handler if log file is specified
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    # Set level for specific modules
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="Scout - Game Automation Assistant")
    
    # Logging options
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to log file (defaults to console only)"
    )
    
    # Application options
    parser.add_argument(
        "--window-title",
        type=str,
        default=None,
        help="Game window title to find"
    )
    
    parser.add_argument(
        "--templates-dir",
        type=str,
        default=None,
        help="Directory containing template images"
    )
    
    # Development options
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Enable development mode"
    )
    
    return parser.parse_args()


def create_resource_directories() -> None:
    """Create necessary resource directories if they don't exist."""
    # List of directories to create
    directories = [
        Path("scout/resources/templates"),
        Path("scout/resources/sequences"),
        Path("scout/resources/logs"),
        Path("scout/resources/states")
    ]
    
    # Create each directory
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Ensured directory exists: {directory}")


def setup_application_style(app: QApplication) -> None:
    """
    Set up application style and appearance.
    
    Args:
        app: QApplication instance
    """
    # Set application style to Fusion (cross-platform modern look)
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Set default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Set application icon
    # TODO: Replace with actual icon when available
    # app.setWindowIcon(QIcon("path/to/icon.png"))
    
    # Configure high-DPI scaling
    # Note: AA_EnableHighDpiScaling is deprecated in newer PyQt6 versions and enabled by default
    # Use try-except to handle different PyQt6 versions
    try:
        # For older PyQt6 versions
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    except AttributeError:
        # In newer PyQt6 versions, high DPI scaling is enabled by default
        logging.info("High DPI scaling is enabled by default in this PyQt6 version")
    
    # AA_UseHighDpiPixmaps should still be available in newer versions
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        logging.info("High DPI pixmaps are enabled by default in this PyQt6 version")


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Application exit code
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging
    default_log_file = None
    if not args.log_file:
        log_dir = Path.home() / '.scout' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        default_log_file = str(log_dir / 'scout.log')
    
    setup_logging(args.log_level, args.log_file or default_log_file)
    
    # Log startup information
    logging.info("Starting Scout application")
    logging.debug(f"Arguments: {args}")
    
    # Create resource directories
    create_resource_directories()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Scout")
    app.setApplicationVersion("0.1.0")  # TODO: Use version from package
    
    # Set up application style
    setup_application_style(app)
    
    # Create main window
    main_window = MainWindow()
    
    # Apply command-line settings if provided
    if args.window_title:
        logging.info(f"Setting window title from command line: {args.window_title}")
        main_window.window_service.set_window_title(args.window_title)
    
    if args.templates_dir:
        logging.info(f"Setting templates directory from command line: {args.templates_dir}")
        template_path = Path(args.templates_dir)
        if template_path.exists() and template_path.is_dir():
            main_window.detection_service.register_template_strategy(str(template_path))
        else:
            logging.warning(f"Templates directory not found: {args.templates_dir}")
    
    # Show the main window
    main_window.show()
    
    # Start the application event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main()) 