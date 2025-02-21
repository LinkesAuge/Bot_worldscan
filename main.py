from typing import NoReturn
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import cv2
import time
import win32api
import win32con
from overlay import Overlay
from gui import OverlayController
from pattern_matcher import PatternMatcher
import logging
from config_manager import ConfigManager
from sound_manager import SoundManager
from window_manager import WindowManager

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

def is_key_pressed(key_code: int) -> bool:
    """
    Check if a key is pressed using Windows API.
    
    Args:
        key_code: Virtual key code to check
        
    Returns:
        bool: True if key is pressed, False otherwise
    """
    return win32api.GetAsyncKeyState(key_code) & 0x8000 != 0

def main() -> None:
    """Main application entry point."""
    logger.info("Starting application")
    
    try:
        app = QApplication(sys.argv)
        
        logger.info("Initializing components")
        config_manager = ConfigManager()
        
        # Load settings
        overlay_settings = config_manager.get_overlay_settings()
        pattern_settings = config_manager.get_pattern_matching_settings()
        
        # Initialize window manager first
        window_manager = WindowManager("Total Battle")
        
        # Create overlay with window manager and settings
        overlay = Overlay(
            target_window_title="Total Battle",
            window_manager=window_manager,
            settings=overlay_settings,
            pattern_settings=pattern_settings
        )
        
        # Create controller
        controller = OverlayController(
            overlay=overlay,
            overlay_settings=overlay_settings,
            pattern_settings=pattern_settings
        )
        
        # Set up callbacks
        controller.set_toggle_callback(overlay.toggle)
        controller.set_quit_callback(app.quit)
        
        # Show the controller window
        controller.show()
        
        # Start the application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 