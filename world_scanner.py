from dataclasses import dataclass
from typing import Tuple, Optional, List
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
from pattern_matcher import PatternMatcher
from config_manager import ConfigManager

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust path if needed

logger = logging.getLogger(__name__)

@dataclass
class WorldPosition:
    """Represents a position in the game world."""
    x: int  # 0-999
    y: int  # 0-999
    k: int  # World number
    
class WorldScanner:
    """
    Handles systematic scanning of the game world.
    """
    
    def __init__(self, 
                 start_pos: WorldPosition,
                 scan_step: int = 50,  # How many coordinates to move each step
                 move_delay: float = 1.0  # Delay after each move
                 ) -> None:
        """
        Initialize the world scanner.
        
        Args:
            start_pos: Starting position (usually player's city)
            scan_step: Distance to move each step
            move_delay: Delay between moves to allow game to update
        """
        self.current_pos = start_pos
        self.start_pos = start_pos
        self.scan_step = scan_step
        self.move_delay = move_delay
        self.visited_positions: List[WorldPosition] = []
        
    def get_current_position(self) -> Optional[WorldPosition]:
        """
        Read current position from minimap coordinates.
        Uses OCR to read the X, Y, and K values.
        """
        try:
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
            except pytesseract.TesseractNotFoundError:
                logger.error("Tesseract OCR is not installed or not found in PATH")
                logger.error("Please install Tesseract OCR and set the correct path")
                return None
            
            logger.info("Starting coordinate detection...")
            
            # Get scanner settings from config
            config = ConfigManager()
            scanner_settings = config.get_scanner_settings()
            logger.info(f"Using scanner settings: {scanner_settings}")
            
            # Define regions for coordinates based on minimap region
            minimap_left = scanner_settings.get('minimap_left', 0)
            minimap_top = scanner_settings.get('minimap_top', 0)
            minimap_width = scanner_settings.get('minimap_width', 0)
            minimap_height = scanner_settings.get('minimap_height', 0)
            
            # Calculate coordinate regions relative to minimap
            coordinate_regions = {
                'x': {
                    'left': minimap_left,  # Start at minimap left edge
                    'top': minimap_top + minimap_height,  # Just below minimap
                    'width': minimap_width // 3,  # One third of minimap width
                    'height': 20
                },
                'y': {
                    'left': minimap_left + minimap_width // 3,  # Second third
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                },
                'k': {
                    'left': minimap_left + (2 * minimap_width) // 3,  # Last third
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                }
            }
            
            logger.debug("Coordinate regions defined:")
            for coord_type, region in coordinate_regions.items():
                logger.debug(f"{coord_type}: {region}")
            
            # Add visual debug for coordinate regions
            with mss() as sct:
                # Take screenshot of entire minimap area plus coordinates
                context_region = {
                    'left': minimap_left,
                    'top': minimap_top,
                    'width': minimap_width,
                    'height': minimap_height + 30  # Add space for coordinates below
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
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Save debug image
                debug_dir = Path("debug_screenshots")
                debug_dir.mkdir(exist_ok=True)
                cv2.imwrite(str(debug_dir / "coordinate_regions.png"), context_shot)
                
                # Process each coordinate region
                coordinates = {}
                for coord_type, region in coordinate_regions.items():
                    logger.debug(f"Processing {coord_type} coordinate region")
                    
                    # Capture the region
                    screenshot = np.array(sct.grab(region))
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    
                    # Enhanced preprocessing
                    # 1. Increase contrast
                    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
                    
                    # 2. Apply Gaussian blur to reduce noise
                    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                    
                    # 3. Adaptive thresholding for better text isolation
                    thresh = cv2.adaptiveThreshold(
                        blurred, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11, 2
                    )
                    
                    # 4. Dilate to make text more prominent
                    kernel = np.ones((2,2), np.uint8)
                    thresh = cv2.dilate(thresh, kernel, iterations=1)
                    
                    # Save all preprocessing steps for debugging
                    cv2.imwrite(str(debug_dir / f"coord_{coord_type}_original.png"), screenshot)
                    cv2.imwrite(str(debug_dir / f"coord_{coord_type}_gray.png"), gray)
                    cv2.imwrite(str(debug_dir / f"coord_{coord_type}_thresh.png"), thresh)
                    
                    # Emit the processed image for debug viewer
                    if hasattr(self, 'debug_image'):
                        self.debug_image.emit(thresh, coord_type, 0)  # 0 as placeholder value
                    
                    # OCR with enhanced configuration
                    text = pytesseract.image_to_string(
                        thresh,
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789 -c tessedit_char_height_range="10-30"'
                    )
                    logger.debug(f"Raw OCR text for {coord_type}: '{text}'")
                    
                    # Clean and convert to int
                    try:
                        # Remove any non-digit characters
                        clean_text = ''.join(filter(str.isdigit, text.strip()))
                        if not clean_text:
                            logger.error(f"No digits found in OCR text for {coord_type}")
                            return None
                            
                        value = int(clean_text)
                        coordinates[coord_type] = value
                        logger.info(f"Detected {coord_type} coordinate: {value}")
                        
                        # Emit the processed image with the detected value
                        if hasattr(self, 'debug_image'):
                            self.debug_image.emit(thresh, coord_type, value)
                            
                    except ValueError as e:
                        logger.error(f"Failed to parse {coord_type} coordinate: {e}")
                        return None
            
            # Validate coordinates
            for coord_type in ['x', 'y', 'k']:
                if coord_type not in coordinates:
                    logger.error(f"Missing {coord_type} coordinate")
                    return None
                if not (0 <= coordinates[coord_type] <= 999):
                    logger.error(f"Invalid {coord_type} coordinate: {coordinates[coord_type]}")
                    return None
            
            position = WorldPosition(
                x=coordinates['x'],
                y=coordinates['y'],
                k=coordinates['k']
            )
            logger.info(f"Successfully detected position: X={position.x}, Y={position.y}, K={position.k}")
            return position
            
        except Exception as e:
            logger.error(f"Error reading coordinates: {e}", exc_info=True)
            return None
            
    def move_to_position(self, target: WorldPosition) -> bool:
        """
        Move camera to specific coordinates.
        
        Args:
            target: Target position to move to
            
        Returns:
            bool: True if move successful
        """
        try:
            logger.info(f"Moving to position: X={target.x}, Y={target.y}, K={target.k}")
            
            # Get input field coordinates from config
            config = ConfigManager()
            input_settings = config.get_scanner_settings()
            input_x = input_settings.get('input_field_x', 0)
            input_y = input_settings.get('input_field_y', 0)
            
            # Click on coordinate input field
            logger.debug(f"Clicking input field at ({input_x}, {input_y})")
            pyautogui.click(x=input_x, y=input_y)
            sleep(0.2)  # Small delay to ensure click registered
            
            # Clear existing text
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            
            # Type coordinates
            coord_text = f"{target.x},{target.y}"
            logger.debug(f"Entering coordinates: {coord_text}")
            pyautogui.write(coord_text)
            pyautogui.press('enter')
            
            # Wait for movement and verify position
            sleep(self.move_delay)
            current_pos = self.get_current_position()
            
            if current_pos:
                success = (current_pos.x == target.x and 
                          current_pos.y == target.y and 
                          current_pos.k == target.k)
                if success:
                    logger.info("Successfully moved to target position")
                else:
                    logger.warning(
                        f"Position mismatch - Target: ({target.x}, {target.y}, {target.k}), "
                        f"Current: ({current_pos.x}, {current_pos.y}, {current_pos.k})"
                    )
                return success
            else:
                logger.error("Failed to verify position after movement")
                return False
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}", exc_info=True)
            return False
            
    def generate_spiral_pattern(self, max_distance: int) -> List[WorldPosition]:
        """
        Generate spiral search pattern starting from current position.
        This ensures methodical coverage of the map.
        """
        positions = []
        x, y = 0, 0
        dx, dy = self.scan_step, 0
        steps = 1
        
        while abs(x) <= max_distance and abs(y) <= max_distance:
            if -1 <= x <= 999 and -1 <= y <= 999:  # Check world boundaries
                new_pos = WorldPosition(
                    x=self.start_pos.x + x,
                    y=self.start_pos.y + y,
                    k=self.start_pos.k
                )
                positions.append(new_pos)
            
            x, y = x + dx, y + dy
            
            if steps % 2 == 0:
                dx, dy = -dy, dx  # Turn 90 degrees
                steps = 0
            steps += 1
            
        return positions
        
    def scan_world_until_match(self, pattern_matcher: 'PatternMatcher', 
                             max_distance: int = 500) -> Optional[WorldPosition]:
        """
        Scan the world in a spiral pattern until a match is found.
        
        Args:
            pattern_matcher: PatternMatcher instance to detect matches
            max_distance: Maximum distance from start position to search
            
        Returns:
            Optional[WorldPosition]: Position where match was found
        """
        logger.info(f"Starting world scan with max distance: {max_distance}")
        positions = self.generate_spiral_pattern(max_distance)
        logger.info(f"Generated {len(positions)} positions to scan")
        
        for pos in positions:
            logger.info(f"Scanning position: X={pos.x}, Y={pos.y}, K={pos.k}")
            
            if self.move_to_position(pos):
                self.visited_positions.append(pos)
                logger.debug(f"Moved to position: X={pos.x}, Y={pos.y}, K={pos.k}")
                
                # Wait for any game animations
                sleep(self.move_delay)
                
                # Check for matches
                matches = pattern_matcher.find_matches()
                if matches:
                    logger.info(f"Found match at position: X={pos.x}, Y={pos.y}, K={pos.k}")
                    return pos
                else:
                    logger.debug("No match found at current position")
                    
        logger.info("No matches found in search area")
        return None 

def test_coordinate_reading():
    """Test function to check coordinate reading."""
    scanner = WorldScanner(WorldPosition(x=0, y=0, k=0))
    
    logger.info("Starting coordinate reading test...")
    position = scanner.get_current_position()
    
    if position:
        logger.info(f"Test successful! Found position: X={position.x}, Y={position.y}, K={position.k}")
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
    
    def __init__(self, scanner: 'WorldScanner', pattern_matcher: 'PatternMatcher') -> None:
        super().__init__()
        self.scanner = scanner
        self.pattern_matcher = pattern_matcher
        self.should_stop = False
        # Pass the debug signal to the scanner
        self.scanner.debug_image = self.debug_image
        self.last_debug_update = 0
        self.debug_update_interval = 0.5  # Update debug images every 0.5 seconds
        
    def update_debug_images(self) -> None:
        """Capture and update debug images."""
        try:
            # Get scanner settings
            config = ConfigManager()
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
                    current_pos = self.scanner.get_current_position()
                    if not current_pos:
                        logger.warning("Failed to read coordinates, retrying in 2 seconds...")
                        sleep(2)  # Wait before retry
                        continue
                    
                    # Update scanner start position
                    self.scanner.start_pos = current_pos
                    logger.info(f"Current position: X={current_pos.x}, Y={current_pos.y}, K={current_pos.k}")
                    
                    # Start scanning from current position
                    found_pos = self.scanner.scan_world_until_match(
                        self.pattern_matcher,
                        max_distance=500
                    )
                    
                    if found_pos:
                        logger.info(f"Match found at position: {found_pos}")
                        self.position_found.emit(found_pos)
                        break
                    
                    # If no match found, continue scanning from a new position
                    logger.info("No match found in current area, moving to next area...")
                    # Move to a new starting position
                    new_x = (current_pos.x + 100) % 1000  # Move 100 units right, wrap around at 1000
                    new_y = current_pos.y
                    new_pos = WorldPosition(x=new_x, y=new_y, k=current_pos.k)
                    
                    move_success = False
                    retry_count = 0
                    while not move_success and retry_count < 3 and not self.should_stop:
                        move_success = self.scanner.move_to_position(new_pos)
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

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Run test
    test_coordinate_reading() 