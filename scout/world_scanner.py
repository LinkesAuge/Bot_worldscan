from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any
import pyautogui
import cv2
import numpy as np
import logging
from time import sleep
from pathlib import Path
import pytesseract
from mss import mss
import time
from PyQt6.QtCore import QObject, pyqtSignal
from scout.template_matcher import TemplateMatcher
from scout.config_manager import ConfigManager
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager
from scout.game_state import GameState

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust path if needed

logger = logging.getLogger(__name__)

class WorldScanner(QObject):
    """
    Scans the game world for points of interest.
    
    This class provides functionality to:
    - Track current position in the game world
    - Navigate to specific coordinates
    - Scan regions for points of interest
    - Process and analyze scan results
    """
    
    # Signals
    scan_started = pyqtSignal()
    scan_completed = pyqtSignal()
    scan_progress = pyqtSignal(int)  # Progress percentage
    scan_error = pyqtSignal(str)  # Error message
    
    def __init__(self, window_manager: WindowManager, template_matcher: TemplateMatcher,
                 debug_window: DebugWindow, game_state: GameState):
        """
        Initialize the world scanner.
        
        Args:
            window_manager: Window manager instance for window tracking
            template_matcher: Template matcher instance for finding game elements
            debug_window: Debug window for visualization
            game_state: Game state instance for coordinate tracking
        """
        super().__init__()
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.debug_window = debug_window
        self.game_state = game_state
        
        # Load configuration
        self.config = ConfigManager()
        scanner_settings = self.config.get_scanner_settings()
        
        # Initialize scanning parameters
        self.minimap_left = scanner_settings.get('minimap_left', 0)
        self.minimap_top = scanner_settings.get('minimap_top', 0)
        self.minimap_width = scanner_settings.get('minimap_width', 100)
        self.minimap_height = scanner_settings.get('minimap_height', 100)
        self.dpi_scale = scanner_settings.get('dpi_scale', 1.0)
        
        # Scanning state
        self.is_scanning = False
        self.scan_cancelled = False
        
    def get_current_position(self) -> None:
        """
        Get the current position from the minimap coordinates.
        Updates the game state with the current position.
        """
        try:
            # Calculate coordinate regions (scaled for DPI)
            coord_height = int(20 * self.dpi_scale)  # Height for coordinate regions
            coord_spacing = int(5 * self.dpi_scale)  # Space between regions
            
            # Define regions for each coordinate type
            coordinate_regions = {
                'x': {
                    'left': self.minimap_left,
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(50 * self.dpi_scale),
                    'height': coord_height
                },
                'y': {
                    'left': self.minimap_left + int(60 * self.dpi_scale),
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(50 * self.dpi_scale),
                    'height': coord_height
                },
                'k': {
                    'left': self.minimap_left + int(120 * self.dpi_scale),
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(30 * self.dpi_scale),
                    'height': coord_height
                }
            }
            
            # Add visual debug for coordinate regions
            with mss.mss() as sct:
                # Get debug settings
                config = ConfigManager()
                debug_settings = config.get_debug_settings()
                debug_enabled = debug_settings["enabled"]
                
                if debug_enabled:
                    # Take screenshot of entire minimap area plus coordinates
                    context_region = {
                        'left': self.minimap_left,
                        'top': self.minimap_top,
                        'width': self.minimap_width,
                        'height': self.minimap_height + int(30 * self.dpi_scale)  # Add scaled space for coordinates below
                    }
                    context_shot = np.array(sct.grab(context_region))
                    
                    # Draw rectangles around coordinate regions
                    for coord_type, region in coordinate_regions.items():
                        # Calculate relative positions to context region
                        x1 = region['left'] - context_region['left']
                        y1 = region['top'] - context_region['top']
                        x2 = x1 + region['width']
                        y2 = y1 + region['height']
                        
                        # Only draw if within bounds
                        if (0 <= x1 < context_shot.shape[1] and 
                            0 <= y1 < context_shot.shape[0] and 
                            0 <= x2 < context_shot.shape[1] and 
                            0 <= y2 < context_shot.shape[0]):
                            cv2.rectangle(context_shot, (x1, y1), (x2, y2), (0, 255, 0), 1)
                            cv2.putText(context_shot, coord_type, (x1, y1-5), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5 * self.dpi_scale, (0, 255, 0), 1)
                    
                    # Update debug window with context image
                    self.debug_window.update_image(
                        "Coordinate Regions",
                        context_shot,
                        metadata={
                            "dpi_scale": self.dpi_scale,
                            "minimap_size": f"{self.minimap_width}x{self.minimap_height}"
                        },
                        save=True
                    )
                
                # Process each coordinate region
                coordinates = {}
                for coord_type, region in coordinate_regions.items():
                    # Capture and process image
                    screenshot = np.array(sct.grab(region))
                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
                    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                    thresh = cv2.adaptiveThreshold(
                        blurred, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11, 2
                    )
                    
                    # Try OCR
                    text = pytesseract.image_to_string(
                        thresh,
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
                    )
                    
                    # Clean text and get value
                    try:
                        value = int(''.join(filter(str.isdigit, text.strip())))
                        coordinates[coord_type] = value
                    except ValueError:
                        coordinates[coord_type] = None
                        logger.warning(f"Failed to parse {coord_type} coordinate")
                    
                    # Update debug window with processed image
                    self.debug_window.update_image(
                        f"Coordinate {coord_type}",
                        thresh,
                        metadata={
                            "raw_text": text.strip(),
                            "value": coordinates[coord_type]
                        },
                        save=True
                    )
                
                # Update game state with coordinates
                self.game_state.update_coordinates(
                    coordinates.get('k'),
                    coordinates.get('x'),
                    coordinates.get('y')
                )
                
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            
    def navigate_to(self, x: int, y: int) -> bool:
        """
        Navigate to specific coordinates in the game world.
        
        Args:
            x: X coordinate to navigate to
            y: Y coordinate to navigate to
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Get input field position from config
            scanner_settings = self.config.get_scanner_settings()
            input_x = scanner_settings.get('input_field_x', 0)
            input_y = scanner_settings.get('input_field_y', 0)
            
            # Click input field
            pyautogui.click(input_x, input_y)
            sleep(0.1)  # Wait for click to register
            
            # Clear existing text
            pyautogui.hotkey('ctrl', 'a')
            sleep(0.1)
            pyautogui.press('backspace')
            sleep(0.1)
            
            # Input new coordinates
            pyautogui.write(f"{x},{y}")
            pyautogui.press('enter')
            
            # Wait for navigation
            sleep(1.0)
            
            # Verify position
            self.get_current_position()
            current_coords = self.game_state.get_coordinates()
            
            if current_coords.x == x and current_coords.y == y:
                logger.info(f"Successfully navigated to ({x}, {y})")
                return True
            else:
                logger.warning(f"Navigation failed - current position: {current_coords}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to coordinates: {e}")
            return False
            
    def start_scan(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """
        Start scanning a region of the game world.
        
        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return
            
        self.is_scanning = True
        self.scan_cancelled = False
        self.scan_started.emit()
        
        try:
            # Calculate scan grid
            x_range = range(min(start_x, end_x), max(start_x, end_x) + 1)
            y_range = range(min(start_y, end_y), max(start_y, end_y) + 1)
            total_points = len(x_range) * len(y_range)
            points_scanned = 0
            
            # Scan each point
            for x in x_range:
                for y in y_range:
                    if self.scan_cancelled:
                        logger.info("Scan cancelled")
                        break
                        
                    # Navigate to point
                    if not self.navigate_to(x, y):
                        logger.warning(f"Failed to navigate to ({x}, {y})")
                        continue
                        
                    # Process point
                    self._process_scan_point()
                    
                    # Update progress
                    points_scanned += 1
                    progress = int((points_scanned / total_points) * 100)
                    self.scan_progress.emit(progress)
                    
                if self.scan_cancelled:
                    break
                    
            if not self.scan_cancelled:
                logger.info("Scan completed successfully")
                self.scan_completed.emit()
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            self.scan_error.emit(str(e))
            
        finally:
            self.is_scanning = False
            
    def stop_scan(self) -> None:
        """Stop the current scan."""
        if self.is_scanning:
            self.scan_cancelled = True
            logger.info("Scan stop requested")
            
    def _process_scan_point(self) -> None:
        """Process the current scan point for points of interest."""
        try:
            # Take screenshot
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is None:
                logger.warning("Failed to capture screenshot")
                return
                
            # Find templates
            matches = self.template_matcher.find_matches(screenshot)
            
            # Process matches
            if matches:
                logger.info(f"Found {len(matches)} matches at current position")
                current_coords = self.game_state.get_coordinates()
                
                # Log matches with coordinates
                for match in matches:
                    logger.info(
                        f"Match: {match.template_name} at "
                        f"K:{current_coords.k} X:{current_coords.x} Y:{current_coords.y} "
                        f"(confidence: {match.confidence:.2f})"
                    )
                    
        except Exception as e:
            logger.error(f"Error processing scan point: {e}")

def test_coordinate_reading():
    """Test function to check coordinate reading."""
    scanner = WorldScanner(WindowManager(), TemplateMatcher(), DebugWindow(), GameState())
    
    logger.info("Starting coordinate reading test...")
    scanner.get_current_position()
    
    current_coords = scanner.game_state.get_coordinates()
    if current_coords:
        logger.info(f"Test successful! Found position: X={current_coords.x}, Y={current_coords.y}, K={current_coords.k}")
    else:
        logger.error("Test failed! Could not read coordinates")

class ScanLogHandler:
    """Handles logging for the world scanner."""
    
    def __init__(self) -> None:
        self.log_dir = Path("scan_logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create new log file with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.log_file = self.log_dir / f"scan_log_{timestamp}.txt"
        
        # Create and configure file handler
        self.file_handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.file_handler.setLevel(logging.DEBUG)
        
        # Create console handler with the same formatter
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(formatter)
        self.console_handler.setLevel(logging.DEBUG)
        
        # Add handlers to logger
        logger.addHandler(self.file_handler)
        logger.addHandler(self.console_handler)
        
        # Log initial message
        logger.info("=== Starting new scan session ===")
        logger.info(f"Log file created at: {self.log_file}")
        
    def cleanup(self) -> None:
        """Clean up logging handlers."""
        logger.info("=== Ending scan session ===")
        logger.removeHandler(self.file_handler)
        logger.removeHandler(self.console_handler)
        self.file_handler.close()
        self.console_handler.close()

class ScanWorker(QObject):
    """Worker for running the world scan in a separate thread."""
    position_found = pyqtSignal(object)  # Emits WorldPosition
    error = pyqtSignal(str)
    finished = pyqtSignal()
    debug_image = pyqtSignal(object, str, int)  # image, coord_type, value
    
    def __init__(self, scanner: WorldScanner, template_matcher: 'TemplateMatcher') -> None:
        """
        Initialize scan worker.
        
        Args:
            scanner: WorldScanner instance
            template_matcher: TemplateMatcher instance
        """
        super().__init__()
        self.scanner = scanner
        self.template_matcher = template_matcher
        self.should_stop = False
        # Pass the debug signal to the scanner
        self.scanner.debug_image = self.debug_image
        self.last_debug_update = 0
        self.debug_update_interval = 0.5  # Update debug images every 0.5 seconds
        
    def run(self) -> None:
        """Run the scanning process."""
        try:
            logger.info("Starting continuous scan...")
            while not self.should_stop:
                try:
                    # Update debug images periodically
                    current_time = time.time()
                    if current_time - self.last_debug_update >= self.debug_update_interval:
                        self.update_debug_images()
                        self.last_debug_update = current_time
                    
                    # Try to read current position
                    self.scanner.get_current_position()
                    
                    # Start scanning from current position
                    found_pos = self.scanner.scan_world_until_match(
                        self.template_matcher,
                        max_attempts=10
                    )
                    
                    if found_pos:
                        logger.info(f"Match found at position: {found_pos}")
                        self.position_found.emit(found_pos)
                        break
                    
                    # If no match found, continue scanning from a new position
                    logger.info("No match found in current area, moving to next area...")
                    # Move to a new starting position
                    new_x = (found_pos[0] + 100) % 1000  # Move 100 units right, wrap around at 1000
                    new_y = found_pos[1]
                    new_pos = (new_x, new_y)
                    
                    move_success = False
                    retry_count = 0
                    while not move_success and retry_count < 3 and not self.should_stop:
                        move_success = self.scanner.navigate_to(new_x, new_y)
                        if not move_success:
                            retry_count += 1
                            logger.warning(f"Failed to move to new position, retry {retry_count}/3")
                            sleep(1)
                    
                    if move_success:
                        logger.info(f"Successfully moved to new position: X={new_x}, Y={new_y}")
                        sleep(2)  # Wait before next scan attempt
                    else:
                        logger.warning("Failed to move after retries, will try new coordinates")
                        sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error during scan: {e}")
                    sleep(2)  # Wait before retry
                    continue
                
            logger.info("Scan stopped by user" if self.should_stop else "Scan completed")
            
        except Exception as e:
            logger.error(f"Fatal error in scan worker: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            if self.should_stop:
                logger.info("Scan worker stopped by user")
            self.finished.emit()

    def update_debug_images(self) -> None:
        """Capture and update debug images."""
        try:
            # Get debug settings
            config = ConfigManager()
            debug_settings = config.get_debug_settings()
            debug_enabled = debug_settings["enabled"]
            
            if not debug_enabled:
                return
                
            # Get scanner settings
            scanner_settings = config.get_scanner_settings()
            
            # Get minimap dimensions
            minimap_left = scanner_settings.get('minimap_left', 0)
            minimap_top = scanner_settings.get('minimap_top', 0)
            minimap_width = scanner_settings.get('minimap_width', 0)
            minimap_height = scanner_settings.get('minimap_height', 0)
            
            # Define regions relative to minimap
            coordinate_regions = {
                'x': {
                    'left': minimap_left,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                },
                'y': {
                    'left': minimap_left + minimap_width // 3,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                },
                'k': {
                    'left': minimap_left + (2 * minimap_width) // 3,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                }
            }
            
            with mss() as sct:
                for coord_type, region in coordinate_regions.items():
                    # Capture and process image
                    screenshot = np.array(sct.grab(region))
                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
                    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                    thresh = cv2.adaptiveThreshold(
                        blurred, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11, 2
                    )
                    
                    # Try OCR
                    text = pytesseract.image_to_string(
                        thresh,
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
                    )
                    
                    # Clean text and get value
                    try:
                        value = int(''.join(filter(str.isdigit, text.strip())))
                    except ValueError:
                        value = 0
                    
                    # Emit image and value
                    self.debug_image.emit(thresh, coord_type, value)
                    
        except Exception as e:
            logger.error(f"Error updating debug images: {e}")
    
    def stop(self) -> None:
        """Signal the worker to stop."""
        self.should_stop = True

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Run test
    test_coordinate_reading() 