"""
Game World Coordinator

This module provides coordination between screen coordinates and game world coordinates.
It handles the mapping between pixel positions on screen and the game's internal coordinate system.
"""

from typing import Tuple, Dict, Optional, List, Any
import logging
import math
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import cv2
import pytesseract

from scout.window_manager import WindowManager
from scout.text_ocr import TextOCR

logger = logging.getLogger(__name__)

@dataclass
class GameWorldPosition:
    """
    Represents a position in the game world.
    
    Attributes:
        x: X coordinate in the game world
        y: Y coordinate in the game world
        k: K coordinate (world number) in the game
        screen_x: Optional X coordinate on screen (pixels)
        screen_y: Optional Y coordinate on screen (pixels)
    """
    x: int
    y: int
    k: int = 0
    screen_x: Optional[int] = None
    screen_y: Optional[int] = None
    
    def __str__(self) -> str:
        """String representation of the position."""
        # Format coordinates with a maximum of 3 digits
        k_str = f"{self.k:03d}" if self.k is not None else "---"
        x_str = f"{self.x:03d}" if self.x is not None else "---"
        y_str = f"{self.y:03d}" if self.y is not None else "---"
        return f"GameWorldPosition(K: {k_str}, X: {x_str}, Y: {y_str})"


class GameWorldCoordinator:
    """
    Coordinates between screen coordinates and game world coordinates.
    
    This class handles:
    - Tracking the current view position in game world coordinates
    - Converting between screen coordinates and game world coordinates
    - Calculating drag operations to move to specific game world coordinates
    - Updating the current position based on OCR readings
    """
    
    def __init__(self, window_manager: WindowManager, text_ocr: TextOCR, game_state=None):
        """
        Initialize the game world coordinator.
        
        Args:
            window_manager: The window manager instance
            text_ocr: The text OCR instance
            game_state: Optional GameState instance for coordinate tracking
        """
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_state = game_state
        
        # Current view position in game world coordinates
        self.current_position = GameWorldPosition(0, 0, 0)
        
        # Screen dimensions
        self.screen_width = 0
        self.screen_height = 0
        
        # Calibration data
        self.calibration_points: List[Tuple[GameWorldPosition, GameWorldPosition]] = []
        self.pixels_per_game_unit_x = 1.0  # Will be calibrated
        self.pixels_per_game_unit_y = 1.0  # Will be calibrated
        
        # Coordinate display region (where to look for coordinates in OCR)
        self.coord_region = (0, 0, 0, 0)  # (x, y, width, height)
        
        # Initialize with default values
        self._initialize()
        
    def _initialize(self) -> None:
        """Initialize with default values."""
        # Get screen dimensions
        window_pos = self.window_manager.get_window_position()
        if window_pos:
            self.screen_width = window_pos[2]
            self.screen_height = window_pos[3]
            
            # Set default coordinate region (bottom center of the screen)
            # Coordinates are typically displayed at the bottom of the game UI
            self.coord_region = (
                self.screen_width // 2 - 150,  # x - centered horizontally
                self.screen_height - 100,      # y - near the bottom
                300,                           # width - wide enough to capture coordinates
                50                             # height - tall enough for the text
            )
            
            logger.info(f"Initialized game world coordinator with screen size: {self.screen_width}x{self.screen_height}")
            logger.info(f"Default coordinate region set to: {self.coord_region}")
        else:
            logger.warning("Could not get window position, using default values")
            self.screen_width = 3900
            self.screen_height = 1800
            self.coord_region = (1800, 1700, 300, 50)
    
    def update_current_position_from_ocr(self) -> bool:
        """
        Update the current position by reading coordinates from the game screen.
        
        This method:
        1. Centers the mouse to ensure consistent measurements
        2. Takes a screenshot of the game window
        3. Crops it to the coordinate region
        4. Passes the cropped image to TextOCR for text extraction
        5. Parses coordinates from the extracted text
        6. Updates the current position with the parsed coordinates
        
        Returns:
            True if coordinates were successfully read, False otherwise
        """
        try:
            # First center the mouse to ensure consistent measurements
            self._center_mouse_for_measurement()
            
            # Instead of duplicating the OCR logic, use the TextOCR's region and processing method
            # This ensures we're using the same OCR processing path as the "old" OCR system
            
            # If TextOCR doesn't have a region set, set it to our coordinate region
            if not self.text_ocr.region:
                x, y, width, height = self.coord_region
                window_pos = self.window_manager.get_window_position()
                if window_pos:
                    # Convert to screen coordinates
                    screen_x = window_pos[0] + x
                    screen_y = window_pos[1] + y
                    self.text_ocr.set_region({
                        'left': screen_x,
                        'top': screen_y,
                        'width': width,
                        'height': height
                    })
                    logger.info(f"Set TextOCR region to match coordinate region: {self.text_ocr.region}")
            
            # Trigger the TextOCR processing
            self.text_ocr._process_region()
            
            # The coordinates will be updated via the TextOCR's _extract_coordinates method
            # which emits the coordinates_updated signal and updates the game state
            
            # Check if coordinates were updated
            if self.game_state and self.game_state.get_coordinates():
                coords = self.game_state.get_coordinates()
                self.current_position.x = coords.x
                self.current_position.y = coords.y
                self.current_position.k = coords.k
                logger.info(f"Updated current position from OCR: {self.current_position}")
                return True
            else:
                logger.warning("No coordinates were extracted from OCR")
                return False
            
        except Exception as e:
            logger.error(f"Error updating position from OCR: {e}", exc_info=True)
            return False
    
    def _center_mouse_for_measurement(self) -> None:
        """
        Center the mouse in the game window to ensure consistent coordinate measurements.
        
        This is important because mouse position affects what part of the game world is visible,
        which in turn affects the coordinates displayed in the game UI.
        """
        try:
            # Get window position
            window_pos = self.window_manager.get_window_position()
            if not window_pos:
                logger.warning("Could not get window position for mouse centering")
                return
                
            left, top, width, height = window_pos
            
            # Calculate center position
            center_x = left + width // 2
            center_y = top + height // 2
            
            # Move mouse to center
            import pyautogui
            pyautogui.moveTo(center_x, center_y)
            logger.debug(f"Centered mouse at ({center_x}, {center_y}) for coordinate measurement")
            
        except Exception as e:
            logger.error(f"Error centering mouse: {e}", exc_info=True)
    
    def _parse_coordinates(self, text: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse coordinates from OCR text.
        
        Args:
            text: Text from OCR
            
        Returns:
            Tuple of (x, y, k) coordinates if found, None otherwise
        """
        try:
            # Log the original text for debugging
            logger.debug(f"Parsing coordinates from text: '{text}'")
            
            # Try multiple approaches to extract coordinates
            
            # Approach 1: Look for patterns like "K:123 X:456 Y:789"
            import re
            k_pattern = re.compile(r'[kK]\s*:?\s*(\d+)')
            x_pattern = re.compile(r'[xX]\s*:?\s*(\d+)')
            y_pattern = re.compile(r'[yY]\s*:?\s*(\d+)')
            
            k_match = k_pattern.search(text)
            x_match = x_pattern.search(text)
            y_match = y_pattern.search(text)
            
            k, x, y = None, None, None
            
            if k_match:
                k = int(k_match.group(1))
                logger.debug(f"Found K coordinate with pattern: {k}")
            if x_match:
                x = int(x_match.group(1))
                logger.debug(f"Found X coordinate with pattern: {x}")
            if y_match:
                y = int(y_match.group(1))
                logger.debug(f"Found Y coordinate with pattern: {y}")
            
            # Approach 2: If we couldn't find labeled coordinates, try to extract just numbers
            if k is None and x is None and y is None:
                # Look for sequences of digits
                digit_pattern = re.compile(r'\d+')
                numbers = digit_pattern.findall(text)
                logger.debug(f"Found numbers: {numbers}")
                
                # If we have exactly 3 numbers, assume they are K, X, Y in that order
                if len(numbers) == 3:
                    k, x, y = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    logger.debug(f"Assuming numbers are K, X, Y: {k}, {x}, {y}")
                # If we have exactly 2 numbers, assume they are X, Y
                elif len(numbers) == 2:
                    x, y = int(numbers[0]), int(numbers[1])
                    logger.debug(f"Assuming numbers are X, Y: {x}, {y}")
            
            # Approach 3: Try to extract coordinates from common OCR misrecognitions
            if k is None and x is None and y is None:
                # Check for common OCR misrecognitions like 'O' for '0', 'l' for '1', etc.
                cleaned_text = text.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
                
                # Try again with cleaned text
                numbers = digit_pattern.findall(cleaned_text)
                logger.debug(f"Found numbers after cleaning: {numbers}")
                
                if len(numbers) == 3:
                    k, x, y = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    logger.debug(f"Extracted from cleaned text - K: {k}, X: {x}, Y: {y}")
                elif len(numbers) == 2:
                    x, y = int(numbers[0]), int(numbers[1])
                    logger.debug(f"Extracted from cleaned text - X: {x}, Y: {y}")
            
            # Log the parsed values for debugging
            logger.debug(f"Parsed coordinates - K: {k}, X: {x}, Y: {y}")
            
            # Validate coordinates (ensure they are within valid range)
            if x is not None and (x < 0 or x > 999):
                logger.warning(f"X coordinate out of range: {x}")
                x = None
                
            if y is not None and (y < 0 or y > 999):
                logger.warning(f"Y coordinate out of range: {y}")
                y = None
                
            if k is not None and (k < 0 or k > 999):
                logger.warning(f"K coordinate out of range: {k}")
                k = None
            
            # Return coordinates even if some are missing
            # This allows partial updates to the position
            return (x, y, k)
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}", exc_info=True)
            return None
    
    def set_coord_region(self, x: int, y: int, width: int, height: int) -> None:
        """
        Set the region where coordinates are displayed.
        
        Args:
            x: X coordinate of the region
            y: Y coordinate of the region
            width: Width of the region
            height: Height of the region
        """
        self.coord_region = (x, y, width, height)
        logger.info(f"Set coordinate region to: {self.coord_region}")
    
    def add_calibration_point(self, screen_pos: Tuple[int, int], game_pos: Tuple[int, int]) -> None:
        """
        Add a calibration point to improve coordinate conversion accuracy.
        
        Args:
            screen_pos: (x, y) position on screen in pixels
            game_pos: (x, y) position in game world coordinates
        """
        screen_position = GameWorldPosition(0, 0, 0, screen_pos[0], screen_pos[1])
        game_position = GameWorldPosition(game_pos[0], game_pos[1], 0)
        
        self.calibration_points.append((screen_position, game_position))
        
        # Recalculate calibration
        self._calibrate()
        
        logger.info(f"Added calibration point: {screen_pos} -> {game_pos}")
    
    def _calibrate(self) -> None:
        """Calibrate the coordinate conversion based on collected points."""
        if len(self.calibration_points) < 2:
            logger.warning("Not enough calibration points, using default values")
            return
            
        # Calculate pixels per game unit
        try:
            # Extract screen and game coordinates
            screen_xs = [p[0].screen_x for p in self.calibration_points]
            screen_ys = [p[0].screen_y for p in self.calibration_points]
            game_xs = [p[1].x for p in self.calibration_points]
            game_ys = [p[1].y for p in self.calibration_points]
            
            # Calculate differences
            screen_x_diffs = [abs(screen_xs[i] - screen_xs[j]) 
                             for i in range(len(screen_xs)) 
                             for j in range(i+1, len(screen_xs))]
            
            screen_y_diffs = [abs(screen_ys[i] - screen_ys[j]) 
                             for i in range(len(screen_ys)) 
                             for j in range(i+1, len(screen_ys))]
            
            game_x_diffs = [abs(game_xs[i] - game_xs[j]) 
                           for i in range(len(game_xs)) 
                           for j in range(i+1, len(game_xs))]
            
            game_y_diffs = [abs(game_ys[i] - game_ys[j]) 
                           for i in range(len(game_ys)) 
                           for j in range(i+1, len(game_ys))]
            
            # Calculate ratios
            x_ratios = [s/g if g != 0 else 0 for s, g in zip(screen_x_diffs, game_x_diffs)]
            y_ratios = [s/g if g != 0 else 0 for s, g in zip(screen_y_diffs, game_y_diffs)]
            
            # Filter out zeros and calculate average
            x_ratios = [r for r in x_ratios if r > 0]
            y_ratios = [r for r in y_ratios if r > 0]
            
            if x_ratios:
                self.pixels_per_game_unit_x = sum(x_ratios) / len(x_ratios)
            
            if y_ratios:
                self.pixels_per_game_unit_y = sum(y_ratios) / len(y_ratios)
                
            logger.info(f"Calibrated: {self.pixels_per_game_unit_x:.2f} pixels/unit X, "
                       f"{self.pixels_per_game_unit_y:.2f} pixels/unit Y")
                
        except Exception as e:
            logger.error(f"Error during calibration: {e}", exc_info=True)
    
    def screen_to_game_coords(self, screen_x: int, screen_y: int) -> GameWorldPosition:
        """
        Convert screen coordinates to game world coordinates.
        
        Args:
            screen_x: X coordinate on screen (pixels)
            screen_y: Y coordinate on screen (pixels)
            
        Returns:
            Position in game world coordinates
        """
        # Calculate center of screen
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        # Calculate offset from center in pixels
        offset_x = screen_x - center_x
        offset_y = screen_y - center_y
        
        # Convert to game units
        game_offset_x = offset_x / self.pixels_per_game_unit_x if self.pixels_per_game_unit_x != 0 else 0
        game_offset_y = offset_y / self.pixels_per_game_unit_y if self.pixels_per_game_unit_y != 0 else 0
        
        # Add to current position
        game_x = self.current_position.x + int(game_offset_x)
        game_y = self.current_position.y + int(game_offset_y)
        
        return GameWorldPosition(game_x, game_y, self.current_position.k, screen_x, screen_y)
    
    def game_to_screen_coords(self, game_x: int, game_y: int) -> Tuple[int, int]:
        """
        Convert game world coordinates to screen coordinates.
        
        Args:
            game_x: X coordinate in game world
            game_y: Y coordinate in game world
            
        Returns:
            (x, y) position on screen in pixels
        """
        # Calculate offset from current position in game units
        offset_x = game_x - self.current_position.x
        offset_y = game_y - self.current_position.y
        
        # Convert to pixels
        pixel_offset_x = offset_x * self.pixels_per_game_unit_x
        pixel_offset_y = offset_y * self.pixels_per_game_unit_y
        
        # Add to center of screen
        screen_x = self.screen_width // 2 + int(pixel_offset_x)
        screen_y = self.screen_height // 2 + int(pixel_offset_y)
        
        return (screen_x, screen_y)
    
    def calculate_drag_vector(self, target_x: int, target_y: int) -> Tuple[int, int, int, int]:
        """
        Calculate drag vector to move to target game coordinates.
        
        Args:
            target_x: Target X coordinate in game world
            target_y: Target Y coordinate in game world
            
        Returns:
            (start_x, start_y, end_x, end_y) for drag operation
        """
        # Calculate offset from current position in game units
        offset_x = self.current_position.x - target_x
        offset_y = self.current_position.y - target_y
        
        # Convert to pixels
        pixel_offset_x = offset_x * self.pixels_per_game_unit_x
        pixel_offset_y = offset_y * self.pixels_per_game_unit_y
        
        # Calculate drag distance (limited to avoid too large drags)
        max_drag = min(self.screen_width, self.screen_height) // 3
        drag_distance = math.sqrt(pixel_offset_x**2 + pixel_offset_y**2)
        
        if drag_distance > max_drag:
            # Scale down to max_drag
            scale = max_drag / drag_distance
            pixel_offset_x *= scale
            pixel_offset_y *= scale
        
        # Calculate drag start and end points
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        start_x = center_x
        start_y = center_y
        end_x = center_x + int(pixel_offset_x)
        end_y = center_y + int(pixel_offset_y)
        
        return (start_x, start_y, end_x, end_y)
    
    def estimate_position_after_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> GameWorldPosition:
        """
        Estimate the new position after a drag operation.
        
        Args:
            start_x: Start X coordinate for drag
            start_y: Start Y coordinate for drag
            end_x: End X coordinate for drag
            end_y: End Y coordinate for drag
            
        Returns:
            Estimated new position in game world coordinates
        """
        # Calculate pixel offset
        pixel_offset_x = end_x - start_x
        pixel_offset_y = end_y - start_y
        
        # Convert to game units
        game_offset_x = pixel_offset_x / self.pixels_per_game_unit_x if self.pixels_per_game_unit_x != 0 else 0
        game_offset_y = pixel_offset_y / self.pixels_per_game_unit_y if self.pixels_per_game_unit_y != 0 else 0
        
        # Calculate new position
        new_x = self.current_position.x - int(game_offset_x)
        new_y = self.current_position.y - int(game_offset_y)
        
        return GameWorldPosition(new_x, new_y, self.current_position.k)
    
    def update_position_after_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """
        Update the current position after a drag operation.
        
        Args:
            start_x: Start X coordinate for drag
            start_y: Start Y coordinate for drag
            end_x: End X coordinate for drag
            end_y: End Y coordinate for drag
        """
        new_position = self.estimate_position_after_drag(start_x, start_y, end_x, end_y)
        self.current_position = new_position
        logger.info(f"Updated position after drag: {self.current_position}")
    
    def is_position_on_screen(self, game_x: int, game_y: int) -> bool:
        """
        Check if a game world position is currently visible on screen.
        
        Args:
            game_x: X coordinate in game world
            game_y: Y coordinate in game world
            
        Returns:
            True if the position is visible on screen, False otherwise
        """
        screen_x, screen_y = self.game_to_screen_coords(game_x, game_y)
        
        # Add some margin
        margin = 50
        
        return (margin <= screen_x <= self.screen_width - margin and 
                margin <= screen_y <= self.screen_height - margin)
    
    def get_visible_game_area(self) -> Tuple[int, int, int, int]:
        """
        Get the game world coordinates of the visible area.
        
        Returns:
            (min_x, min_y, max_x, max_y) in game world coordinates
        """
        # Convert screen corners to game coordinates
        top_left = self.screen_to_game_coords(0, 0)
        bottom_right = self.screen_to_game_coords(self.screen_width, self.screen_height)
        
        return (top_left.x, top_left.y, bottom_right.x, bottom_right.y) 