"""Main entry point for TB Scout application."""

import sys
import logging
from pathlib import Path
from typing import NoReturn, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from scout import (
    APP_NAME,
    APP_DESCRIPTION,
    APP_ORGANIZATION,
    APP_DOMAIN,
    CONFIG_FILE,
    LOG_DIR,
)
from scout.core.config import ConfigManager
from scout.core.logging import setup_logging
from scout.gui.main_window import MainWindow
from scout.core import WindowTracker, CoordinateManager
from scout.capture import CaptureManager, PatternMatcher, OCRProcessor
from scout.visualization import DebugVisualizer


def init_logging() -> None:
    """Initialize logging configuration.
    
    Creates the log directory if it doesn't exist and sets up logging with
    both file and console handlers.
    """
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    setup_logging(
        log_dir=log_dir,
        console_level=logging.INFO,
        file_level=logging.DEBUG,
    )


def init_settings() -> QSettings:
    """Initialize application settings.
    
    Returns:
        QSettings: The application settings object.
    """
    return QSettings(APP_ORGANIZATION, APP_NAME)


def init_config() -> ConfigManager:
    """Initialize configuration manager.
    
    Returns:
        ConfigManager: The configuration manager instance.
    """
    return ConfigManager(CONFIG_FILE)


def run_app(app: QApplication, window: MainWindow) -> int:
    """Run the application main loop.
    
    Args:
        app: The QApplication instance.
        window: The main window instance.
    
    Returns:
        int: The application exit code.
    """
    window.show()
    return app.exec()


def main(argv: Optional[list[str]] = None) -> NoReturn:
    """Application main entry point.
    
    Args:
        argv: Command line arguments (defaults to sys.argv if not provided).
    """
    # Initialize logging first
    init_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create application
        app = QApplication(argv if argv is not None else sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationDisplayName(APP_DESCRIPTION)
        app.setOrganizationName(APP_ORGANIZATION)
        app.setOrganizationDomain(APP_DOMAIN)
        
        # Initialize components
        config = init_config()
        
        # Initialize core components
        window_tracker = WindowTracker(config)
        coordinate_manager = CoordinateManager(window_tracker)
        
        # Initialize capture components
        capture_manager = CaptureManager(
            window_tracker,
            coordinate_manager
        )
        
        pattern_matcher = PatternMatcher(
            capture_manager
        )
        
        ocr_processor = OCRProcessor(
            capture_manager
        )
        
        # Initialize debug visualizer
        debug_visualizer = DebugVisualizer(
            window_tracker,
            coordinate_manager,
            capture_manager,
            pattern_matcher,
            ocr_processor
        )
        
        # Create and show main window
        window = MainWindow(
            window_tracker=window_tracker,
            coordinate_manager=coordinate_manager,
            capture_manager=capture_manager,
            pattern_matcher=pattern_matcher,
            ocr_processor=ocr_processor,
            debug_visualizer=debug_visualizer
        )
        
        # Run application
        exit_code = run_app(app, window)
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception("Unhandled exception in main: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main() 