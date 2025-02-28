"""
Text OCR Processor

This module provides OCR functionality for extracting text from the game window.
It handles:
- Region selection
- Text extraction
- Coordinate parsing
- Debug visualization
"""

from typing import Optional, Dict, Any
import numpy as np
import cv2
import logging
import pytesseract
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import re
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager
from scout.game_state import GameState
import mss

logger = logging.getLogger(__name__)

class TextOCR(QObject):
    """
    Handles continuous OCR processing of a selected screen region.
    
    This class provides:
    - Continuous capture of a specified screen region
    - OCR processing of the captured region
    - Coordinate extraction and validation
    - Debug visualization of the captured region and OCR results
    - Configurable update frequency
    """
    
    # Signals
    debug_image = pyqtSignal(str, object, dict)  # name, image, metadata
    coordinates_updated = pyqtSignal(object)  # Emits GameCoordinates from GameState
    
    def __init__(self, debug_window: DebugWindow, window_manager: WindowManager, game_state: GameState) -> None:
        """
        Initialize Text OCR processor.
        
        Args:
            debug_window: Debug window for visualization
            window_manager: Window manager instance for window tracking and coordinate handling
            game_state: Game state instance for coordinate tracking
        """
        super().__init__()
        self.debug_window = debug_window
        self.window_manager = window_manager
        self.game_state = game_state
        self.active = False
        self.region: Optional[Dict[str, int]] = None
        self.update_frequency = 0.5  # Default 0.5 updates/sec
        
        # Create timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_region)
        
        logger.debug("TextOCR initialized")
    
    def set_region(self, region: Dict[str, int]) -> None:
        """
        Set the region to process.
        
        Args:
            region: Dictionary with left, top, width, height in physical coordinates
        """
        self.region = region
        logger.info(f"OCR region set to: {region}")
        
        # If active, force an immediate capture
        if self.active:
            self._process_region()
            
    def set_frequency(self, frequency: float) -> None:
        """
        Set the update frequency.
        
        Args:
            frequency: Updates per second
        """
        self.update_frequency = frequency
        if self.active:
            interval = int(1000 / frequency)  # Convert to milliseconds
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval}ms ({frequency} updates/sec)")
            
    def start(self) -> None:
        """Start OCR processing."""
        if self.active:
            return
            
        self.active = True
        interval = int(1000 / self.update_frequency)  # Convert to milliseconds
        self.update_timer.start(interval)
        logger.info(f"OCR started with {self.update_frequency} updates/sec")
        
    def stop(self) -> None:
        """Stop OCR processing."""
        if not self.active:
            return
            
        self.active = False
        self.update_timer.stop()
        logger.info("OCR stopped")
        
    def _process_region(self) -> None:
        """Process the selected region for text."""
        if not self.active or not self.region:
            return
            
        try:
            # Take screenshot of region
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(self.region))
                
            # Convert to grayscale
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)  # Increase contrast
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)  # Reduce noise
            thresh = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # Extract text
            text = pytesseract.image_to_string(thresh)
            
            # Update debug window
            self.debug_window.update_image(
                "OCR Region",
                thresh,
                metadata={"raw_text": text.strip()},
                save=True
            )
            
            # Extract and validate coordinates
            self._extract_coordinates(text)
            
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}")
            
    def _extract_coordinates(self, text: str) -> None:
        """
        Extract coordinates from OCR text, handling noise and invalid characters.
        
        Uses strict regex patterns to find coordinates in the format:
        K: number, X: number, Y: number
        Ignores any additional characters or noise in the text.
        
        Args:
            text: The OCR text to parse
        """
        try:
            # Clean text by removing common OCR artifacts and normalizing separators
            cleaned_text = text.replace(';', ':').replace('|', ':')
            
            # Use more precise regex patterns that ignore surrounding noise
            # Look for numbers that appear after K:, X:, or Y: (allowing for optional space)
            k_match = re.search(r'K:?\s*(\d+)(?:\D|$)', cleaned_text)
            x_match = re.search(r'X:?\s*(\d+)(?:\D|$)', cleaned_text)
            y_match = re.search(r'Y:?\s*(\d+)(?:\D|$)', cleaned_text)
            
            # Log the regex matches for debugging
            logger.debug(f"Regex matches - K: {k_match.group(1) if k_match else 'None'}, "
                        f"X: {x_match.group(1) if x_match else 'None'}, "
                        f"Y: {y_match.group(1) if y_match else 'None'}")
            
            # Extract and validate each coordinate
            k_val = None
            x_val = None
            y_val = None
            
            if k_match:
                try:
                    k_val = self._validate_coordinate(int(k_match.group(1)), "K")
                except ValueError:
                    logger.warning(f"Invalid K value found: {k_match.group(1)}")
            
            if x_match:
                try:
                    x_val = self._validate_coordinate(int(x_match.group(1)), "X")
                except ValueError:
                    logger.warning(f"Invalid X value found: {x_match.group(1)}")
            
            if y_match:
                try:
                    y_val = self._validate_coordinate(int(y_match.group(1)), "Y")
                except ValueError:
                    logger.warning(f"Invalid Y value found: {y_match.group(1)}")
            
            # Update game state with new coordinates
            self.game_state.update_coordinates(k_val, x_val, y_val)
            
            # Emit updated coordinates
            self.coordinates_updated.emit(self.game_state.get_coordinates())
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}")
            
    def _validate_coordinate(self, value: int, coord_type: str) -> Optional[int]:
        """
        Validate a coordinate value.
        
        Args:
            value: Value to validate
            coord_type: Type of coordinate ('K', 'X', or 'Y')
            
        Returns:
            Validated value or None if invalid
        """
        try:
            if coord_type == 'K':
                if 1 <= value <= 999:  # Assuming kingdoms are numbered 1-999
                    return value
            elif coord_type in ('X', 'Y'):
                if 0 <= value <= 999:  # Game world coordinates are 0-999
                    return value
            return None
        except Exception:
            return None 