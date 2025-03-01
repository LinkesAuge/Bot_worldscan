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
import time
import mss
import win32api
import ctypes
import win32con
import json

from scout.window_manager import WindowManager
from scout.text_ocr import TextOCR
from scout.game_world_position import GameWorldPosition
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class GameWorldCoordinator:
    """
    Coordinates between screen coordinates and game world coordinates.
    
    This class manages the conversion between screen coordinates (pixels) and
    game world coordinates (K, X, Y). It also handles navigation, position tracking,
    and calibration.
    """
    
    def __init__(self, window_manager: WindowManager, text_ocr: TextOCR, game_state=None):
        """
        Initialize the game world coordinator.
        
        Args:
            window_manager: The window manager instance
            text_ocr: The text OCR instance
            game_state: Optional game state instance
        """
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_state = game_state
        
        # Current position in the game world
        self.current_position = GameWorldPosition(0, 0, 0)
        
        # Calibration data
        self.calibration_in_progress = False
        self.calibration_start_position = None
        self.calibration_start_screen = None
        self.pixels_per_game_unit_x = 10.0  # Default value
        self.pixels_per_game_unit_y = 10.0  # Default value
        
        # Initialize
        self._initialize()
        
    def _initialize(self) -> None:
        """Initialize the coordinator."""
        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Load calibration points if they exist
        self._load_calibration_data()
        
        logger.info(f"Game world coordinator initialized with pixels per game unit: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f}")

    def _save_calibration_data(self) -> None:
        """Save calibration data to disk."""
        try:
            # Create config directory if it doesn't exist
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            # Prepare calibration data
            calibration_data = {
                "pixels_per_game_unit_x": self.pixels_per_game_unit_x,
                "pixels_per_game_unit_y": self.pixels_per_game_unit_y,
            }
            
            # Save to file
            with open("config/calibration_data.json", "w") as f:
                json.dump(calibration_data, f, indent=4)
                
            logger.info(f"Saved calibration data: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f}")
            
        except Exception as e:
            logger.error(f"Error saving calibration data: {e}", exc_info=True)

    def _load_calibration_data(self) -> None:
        """Load calibration data from disk."""
        try:
            # Check if file exists
            if not Path("config/calibration_data.json").exists():
                logger.info("No calibration data found, using default values")
                return
                
            # Load from file
            with open("config/calibration_data.json", "r") as f:
                calibration_data = json.load(f)
                
            # Update calibration values
            self.pixels_per_game_unit_x = calibration_data.get("pixels_per_game_unit_x", 10.0)
            self.pixels_per_game_unit_y = calibration_data.get("pixels_per_game_unit_y", 10.0)
                
            logger.info(f"Loaded calibration data: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f}")
            
        except Exception as e:
            logger.error(f"Error loading calibration data: {e}", exc_info=True)
            # Use default values
            self.pixels_per_game_unit_x = 10.0
            self.pixels_per_game_unit_y = 10.0

    def start_calibration(self) -> bool:
        """
        Start the calibration process.
        
        This records the current position as the starting point for calibration.
        The user should then drag/scroll the map to a different position.
        
        Returns:
            True if calibration started successfully, False otherwise
        """
        try:
            # Update current position from OCR
            success = self.update_current_position_from_ocr()
            if not success:
                logger.warning("Failed to get current position for calibration start")
                return False
                
            # Get current position
            start_pos = self.current_position
            if not start_pos or start_pos.x is None or start_pos.y is None:
                logger.warning("Invalid position data for calibration start")
                return False
                
            # Get window center
            window_pos = self.window_manager.get_window_position()
            if not window_pos:
                logger.error("Failed to get window position for calibration")
                return False
                
            # Record starting position
            self.calibration_start_position = GameWorldPosition(
                start_pos.x, 
                start_pos.y, 
                start_pos.k
            )
            
            # Record screen center
            self.calibration_start_screen = (
                window_pos[0] + window_pos[2] // 2,
                window_pos[1] + window_pos[3] // 2
            )
            
            # Set calibration in progress
            self.calibration_in_progress = True
            
            logger.info(f"Started calibration at position {self.calibration_start_position}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting calibration: {e}", exc_info=True)
            self.calibration_in_progress = False
            return False
            
    def complete_calibration(self) -> bool:
        """
        Complete the calibration process.
        
        This records the current position as the ending point for calibration
        and calculates the pixels per game unit ratio.
        
        Returns:
            True if calibration completed successfully, False otherwise
        """
        try:
            # Check if calibration is in progress
            if not self.calibration_in_progress:
                logger.warning("No calibration in progress")
                return False
                
            # Update current position from OCR
            success = self.update_current_position_from_ocr()
            if not success:
                logger.warning("Failed to get current position for calibration end")
                return False
                
            # Get current position
            end_pos = self.current_position
            if not end_pos or end_pos.x is None or end_pos.y is None:
                logger.warning("Invalid position data for calibration end")
                return False
                
            # Get window center
            window_pos = self.window_manager.get_window_position()
            if not window_pos:
                logger.error("Failed to get window position for calibration end")
                return False
                
            # Get end screen position
            end_screen = (
                window_pos[0] + window_pos[2] // 2,
                window_pos[1] + window_pos[3] // 2
            )
            
            # Calculate game world distance
            dx_game = end_pos.x - self.calibration_start_position.x
            dy_game = end_pos.y - self.calibration_start_position.y
            
            # Check if we have a meaningful distance
            if abs(dx_game) < 5 and abs(dy_game) < 5:
                logger.warning("Calibration distance too small, please drag further")
                return False
                
            # Calculate screen distance (this will be 0 since we're using the center)
            # Instead, we need to calculate the drag distance
            # For this, we use the estimate_position_after_drag method in reverse
            
            # The drag vector is what we need to calculate
            # We know the start and end game positions, and we need to find the drag vector
            # that would cause this change
            
            # Calculate the drag distance based on the current pixels_per_game_unit values
            # This is an approximation that will be refined
            drag_x = -dx_game * self.pixels_per_game_unit_x
            drag_y = -dy_game * self.pixels_per_game_unit_y
            
            # Now update the pixels_per_game_unit values
            if dx_game != 0:
                self.pixels_per_game_unit_x = abs(drag_x / dx_game)
            
            if dy_game != 0:
                self.pixels_per_game_unit_y = abs(drag_y / dy_game)
                
            # Reset calibration state
            self.calibration_in_progress = False
            self.calibration_start_position = None
            self.calibration_start_screen = None
            
            # Save calibration data
            self._save_calibration_data()
            
            logger.info(f"Completed calibration: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing calibration: {e}", exc_info=True)
            self.calibration_in_progress = False
            return False
            
    def cancel_calibration(self) -> None:
        """Cancel the current calibration process."""
        self.calibration_in_progress = False
        self.calibration_start_position = None
        self.calibration_start_screen = None
        logger.info("Calibration cancelled")
        
    def is_calibration_in_progress(self) -> bool:
        """Check if calibration is in progress."""
        return self.calibration_in_progress
        
    def get_calibration_status(self) -> str:
        """
        Get the current calibration status.
        
        Returns:
            A string describing the current calibration status
        """
        if self.calibration_in_progress:
            return f"Calibration in progress. Started at {self.calibration_start_position}"
        else:
            return f"Calibration: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f} pixels per game unit"
    
    def update_current_position_from_ocr(self) -> bool:
        """
        Update the current position from OCR.
        
        This method:
        1. Takes a screenshot of the coordinate region
        2. Processes the image to extract text
        3. Extracts coordinates from the text
        4. Updates the current position
        
        Returns:
            True if coordinates were successfully updated, False otherwise
        """
        try:
            # Check if we're rate limited
            current_time = time.time()
            # Increase rate limiting from 0.5s to 2.0s to prevent excessive updates
            if hasattr(self, '_last_ocr_update') and current_time - self._last_ocr_update < 2.0:
                logger.debug(f"OCR update rate limited (last update: {current_time - self._last_ocr_update:.2f}s ago)")
                # If we have valid coordinates, consider this a success
                if self.current_position.x is not None or self.current_position.y is not None or self.current_position.k is not None:
                    return True
                return False
                
            # Update the last OCR update time
            self._last_ocr_update = current_time
            
            # Check if TextOCR has been cancelled
            if hasattr(self.text_ocr, '_cancellation_requested') and self.text_ocr._cancellation_requested:
                logger.info("OCR update cancelled due to cancellation request")
                return False
                
            # Get the game window position
            window_pos = self.window_manager.get_window_position()
            if not window_pos:
                logger.warning("Could not get game window position")
                # If we have valid coordinates in the game state, consider this a success
                if self.game_state and self.game_state.get_coordinates() and self.game_state.get_coordinates().is_valid():
                    return True
                return False
            
            # First check if we already have valid coordinates in the game state
            if self.game_state and self.game_state.get_coordinates():
                coords = self.game_state.get_coordinates()
                if coords.is_valid():
                    logger.info(f"Using existing valid coordinates from game state: {coords}")
                    # Update our current position with the game state coordinates
                    self.current_position.x = coords.x
                    self.current_position.y = coords.y
                    self.current_position.k = coords.k
                    # We'll still try to get fresh coordinates from OCR, but we have valid ones if that fails
            
            # Ensure the game window is active before trying to center the mouse
            if not self._ensure_window_active():
                logger.warning("Could not activate game window for OCR update")
                # If we have valid coordinates in the game state, consider this a success
                if self.game_state and self.game_state.get_coordinates() and self.game_state.get_coordinates().is_valid():
                    return True
                return False
            
            # Center the mouse to ensure consistent measurements
            logger.info("Centering mouse in game window...")
            self._center_mouse_for_measurement()
            
            # Force a delay to ensure the mouse movement is complete and the game UI has updated
            logger.info("Waiting for game UI to update after mouse centering...")
            time.sleep(0.5)  # Increased delay to ensure UI updates
            
            # Verify window position
            window_pos = self.window_manager.get_window_position()
            if not window_pos:
                logger.error("Could not get window position for OCR update")
                # If we have valid coordinates in the game state, consider this a success
                if self.game_state and self.game_state.get_coordinates() and self.game_state.get_coordinates().is_valid():
                    return True
                return False
                
            logger.info(f"Game window position: {window_pos}")
            
            # Check if TextOCR has a region set
            if not self.text_ocr.region:
                logger.warning("No OCR region set. Please select an OCR region in the overlay tab.")
                # If we have valid coordinates in the game state, consider this a success
                if self.game_state and self.game_state.get_coordinates() and self.game_state.get_coordinates().is_valid():
                    return True
                return False
            
            # Take a screenshot of the OCR region for debugging
            if self.text_ocr.region:
                # Get debug settings
                config = ConfigManager()
                debug_settings = config.get_debug_settings()
                debug_enabled = debug_settings["enabled"]
                
                # Only save debug screenshots if debug mode is enabled
                if debug_enabled:
                    # Ensure the debug directory exists
                    debug_dir = Path('scout/debug_screenshots')
                    debug_dir.mkdir(exist_ok=True, parents=True)
                    
                    # Capture the region
                    with mss.mss() as sct:
                        screenshot = np.array(sct.grab(self.text_ocr.region))
                        
                    # Save the screenshot for debugging
                    cv2.imwrite(str(debug_dir / 'ocr_region_from_game_world.png'), screenshot)
                    logger.info("Saved OCR region screenshot for debugging")
            
            # Trigger the TextOCR processing with a timeout
            logger.info("Triggering TextOCR processing...")
            
            # Use a simple timeout approach instead of threading
            start_time = time.time()
            ocr_timeout = 3.0  # 3 seconds timeout
            ocr_result = False
            
            try:
                # Process the OCR region directly
                self.text_ocr._process_region()
                ocr_result = True
                logger.info("OCR processing completed successfully")
            except Exception as e:
                logger.error(f"Error in OCR processing: {e}", exc_info=True)
                ocr_result = False
            
            # Check if the operation took too long
            elapsed_time = time.time() - start_time
            if elapsed_time > ocr_timeout:
                logger.warning(f"OCR processing took too long: {elapsed_time:.2f} seconds (timeout: {ocr_timeout} seconds)")
            
            if not ocr_result:
                logger.warning("OCR processing failed")
                # If we have valid coordinates in the game state, consider this a success
                if self.game_state and self.game_state.get_coordinates() and self.game_state.get_coordinates().is_valid():
                    return True
                # If we have valid coordinates in our current position, consider this a success
                if self.current_position.x is not None or self.current_position.y is not None or self.current_position.k is not None:
                    logger.info(f"Using existing coordinates after OCR failure: {self.current_position}")
                    return True
                return False
            
            # Check if coordinates were updated
            if self.game_state and self.game_state.get_coordinates():
                coords = self.game_state.get_coordinates()
                if coords.is_valid():
                    self.current_position.x = coords.x
                    self.current_position.y = coords.y
                    self.current_position.k = coords.k
                    logger.info(f"Successfully updated current position from OCR: {self.current_position}")
                    return True
                else:
                    logger.warning("Coordinates in game state are not fully valid")
                    # If we have partial coordinates, still use what we have
                    if coords.x is not None:
                        self.current_position.x = coords.x
                    if coords.y is not None:
                        self.current_position.y = coords.y
                    if coords.k is not None:
                        self.current_position.k = coords.k
                    
                    # Check if we have at least some valid coordinates
                    if self.current_position.x is not None or self.current_position.y is not None or self.current_position.k is not None:
                        logger.info(f"Using partial coordinates: {self.current_position}")
                        return True
                    return False
            else:
                logger.warning("No coordinates were extracted from OCR")
                # If we have valid coordinates in our current position, consider this a success
                if self.current_position.x is not None or self.current_position.y is not None or self.current_position.k is not None:
                    logger.info(f"Using existing coordinates: {self.current_position}")
                    return True
                return False
            
        except Exception as e:
            logger.error(f"Error updating position from OCR: {e}", exc_info=True)
            # If we have valid coordinates in our current position, consider this a success
            if self.current_position.x is not None or self.current_position.y is not None or self.current_position.k is not None:
                logger.info(f"Using existing coordinates after error: {self.current_position}")
                return True
            return False
    
    def _center_mouse_for_measurement(self) -> None:
        """
        Center the mouse in the game window to ensure consistent coordinate measurements.
        
        This is important because mouse position affects what part of the game world is visible,
        which in turn affects the coordinates displayed in the game UI.
        """
        try:
            # Get client area position and size
            client_rect = self.window_manager.get_client_rect()
            if not client_rect:
                logger.warning("Could not get client rect for mouse centering")
                # Fall back to window position
                window_pos = self.window_manager.get_window_position()
                if not window_pos:
                    logger.warning("Could not get window position for mouse centering")
                    return
                left, top, width, height = window_pos
                
                # Get window frame offset
                x_offset, y_offset = self.window_manager.get_window_frame_offset()
                
                # Adjust for window frame
                left += x_offset
                top += y_offset
                width -= x_offset * 2  # Approximate adjustment
                height -= y_offset + x_offset  # Approximate adjustment
            else:
                # Use client rect directly
                left, top, right, bottom = client_rect
                width = right - left
                height = bottom - top
            
            # Calculate center position of client area
            center_x = left + width // 2
            center_y = top + height // 2
            
            # Log current mouse position
            import pyautogui
            current_x, current_y = pyautogui.position()
            logger.info(f"Current mouse position: ({current_x}, {current_y})")
            logger.info(f"Target center position: ({center_x}, {center_y})")
            
            # Try multiple methods to move the mouse
            methods_tried = 0
            max_attempts = 3
            
            # Method 1: win32api.SetCursorPos
            if methods_tried < max_attempts:
                methods_tried += 1
                try:
                    logger.info(f"Method {methods_tried}: Moving mouse using win32api.SetCursorPos")
                    win32api.SetCursorPos((center_x, center_y))
                    time.sleep(0.1)  # Small delay
                    
                    # Verify position
                    new_x, new_y = pyautogui.position()
                    logger.info(f"New position after win32api: ({new_x}, {new_y})")
                    
                    if abs(new_x - center_x) <= 5 and abs(new_y - center_y) <= 5:
                        logger.info(f"Successfully centered mouse using win32api")
                        return
                    else:
                        logger.warning(f"win32api mouse movement not accurate. Expected: ({center_x}, {center_y}), Actual: ({new_x}, {new_y})")
                except Exception as e:
                    logger.warning(f"Error using win32api.SetCursorPos: {e}")
            
            # Method 2: ctypes.windll.user32.SetCursorPos
            if methods_tried < max_attempts:
                methods_tried += 1
                try:
                    logger.info(f"Method {methods_tried}: Moving mouse using ctypes.windll.user32.SetCursorPos")
                    ctypes.windll.user32.SetCursorPos(center_x, center_y)
                    time.sleep(0.1)  # Small delay
                    
                    # Verify position
                    new_x, new_y = pyautogui.position()
                    logger.info(f"New position after ctypes: ({new_x}, {new_y})")
                    
                    if abs(new_x - center_x) <= 5 and abs(new_y - center_y) <= 5:
                        logger.info(f"Successfully centered mouse using ctypes")
                        return
                    else:
                        logger.warning(f"ctypes mouse movement not accurate. Expected: ({center_x}, {center_y}), Actual: ({new_x}, {new_y})")
                except Exception as e:
                    logger.warning(f"Error using ctypes.windll.user32.SetCursorPos: {e}")
            
            # Method 3: pyautogui.moveTo
            if methods_tried < max_attempts:
                methods_tried += 1
                try:
                    logger.info(f"Method {methods_tried}: Moving mouse using pyautogui.moveTo")
                    pyautogui.moveTo(center_x, center_y)
                    time.sleep(0.1)  # Small delay
                    
                    # Verify position
                    new_x, new_y = pyautogui.position()
                    logger.info(f"New position after pyautogui: ({new_x}, {new_y})")
                    
                    if abs(new_x - center_x) <= 5 and abs(new_y - center_y) <= 5:
                        logger.info(f"Successfully centered mouse using pyautogui")
                        return
                    else:
                        logger.warning(f"pyautogui mouse movement not accurate. Expected: ({center_x}, {center_y}), Actual: ({new_x}, {new_y})")
                except Exception as e:
                    logger.warning(f"Error using pyautogui.moveTo: {e}")
            
            # If we get here, all methods failed or were inaccurate
            logger.warning("All mouse centering methods failed or were inaccurate")
            
            # Try one more approach: mouse_event
            try:
                logger.info("Final attempt: Using mouse_event to move mouse")
                # Get current position
                current_x, current_y = pyautogui.position()
                
                # Calculate relative movement
                dx = center_x - current_x
                dy = center_y - current_y
                
                # Use mouse_event to move relatively
                ctypes.windll.user32.mouse_event(
                    0x0001,  # MOUSEEVENTF_MOVE
                    dx, dy,
                    0, 0
                )
                
                time.sleep(0.1)  # Small delay
                
                # Verify position
                new_x, new_y = pyautogui.position()
                logger.info(f"New position after mouse_event: ({new_x}, {new_y})")
                
                if abs(new_x - center_x) <= 10 and abs(new_y - center_y) <= 10:
                    logger.info(f"Successfully centered mouse using mouse_event")
                else:
                    logger.warning(f"mouse_event movement not accurate. Expected: ({center_x}, {center_y}), Actual: ({new_x}, {new_y})")
            except Exception as e:
                logger.error(f"Error using mouse_event: {e}")
                
        except Exception as e:
            logger.error(f"Error centering mouse: {e}", exc_info=True)
            
    def _ensure_window_active(self) -> bool:
        """
        Ensure the game window is active (has focus).
        
        Returns:
            bool: True if window is active or was successfully activated, False otherwise
        """
        try:
            if not self.window_manager.find_window():
                logger.warning("Cannot activate window: Window not found")
                return False
                
            # Check if window is already active
            active_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if active_hwnd == self.window_manager.hwnd:
                logger.debug("Window is already active")
                return True
                
            # Try to activate the window
            logger.info("Activating game window")
            
            # Show window if minimized
            if self.window_manager.is_window_minimized_or_hidden():
                ctypes.windll.user32.ShowWindow(self.window_manager.hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)  # Give time for window to restore
            
            # Set foreground window
            ctypes.windll.user32.SetForegroundWindow(self.window_manager.hwnd)
            time.sleep(0.2)  # Give time for window to activate
            
            # Verify activation
            active_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if active_hwnd == self.window_manager.hwnd:
                logger.info("Successfully activated game window")
                return True
            else:
                logger.warning("Failed to activate game window")
                return False
                
        except Exception as e:
            logger.error(f"Error activating window: {e}")
            return False
    
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
    
    def screen_to_game_coords(self, screen_x: int, screen_y: int) -> GameWorldPosition:
        """
        Convert screen coordinates to game world coordinates.
        
        Args:
            screen_x: X coordinate on screen in pixels
            screen_y: Y coordinate on screen in pixels
            
        Returns:
            Game world position
        """
        # Get window center
        window_pos = self.window_manager.get_window_position()
        if not window_pos:
            logger.error("Failed to get window position")
            return GameWorldPosition(0, 0, 0)
            
        center_x = window_pos[0] + window_pos[2] // 2
        center_y = window_pos[1] + window_pos[3] // 2
        
        # Calculate offset from center in pixels
        dx_pixels = screen_x - center_x
        dy_pixels = screen_y - center_y
        
        # Convert to game units using calibration
        dx_game = dx_pixels / self.pixels_per_game_unit_x
        dy_game = dy_pixels / self.pixels_per_game_unit_y
        
        # Get current position
        current_pos = self.current_position
        
        # Calculate game world coordinates
        # Note: In game world, increasing Y is down, so we negate dy_game
        game_x = current_pos.x + dx_game
        game_y = current_pos.y - dy_game
        
        return GameWorldPosition(game_x, game_y, current_pos.k)
    
    def game_to_screen_coords(self, game_x: float, game_y: float, game_k: int = None) -> Tuple[int, int]:
        """
        Convert game world coordinates to screen coordinates.
        
        Args:
            game_x: X coordinate in game world
            game_y: Y coordinate in game world
            game_k: K coordinate in game world (optional)
            
        Returns:
            (screen_x, screen_y) tuple of screen coordinates
        """
        # Get window center
        window_pos = self.window_manager.get_window_position()
        if not window_pos:
            logger.error("Failed to get window position")
            return (0, 0)
            
        center_x = window_pos[0] + window_pos[2] // 2
        center_y = window_pos[1] + window_pos[3] // 2
        
        # Get current position
        current_pos = self.current_position
        
        # Calculate offset in game units
        dx_game = game_x - current_pos.x
        dy_game = game_y - current_pos.y
        
        # Convert to pixels using calibration
        dx_pixels = dx_game * self.pixels_per_game_unit_x
        dy_pixels = dy_game * self.pixels_per_game_unit_y
        
        # Calculate screen coordinates
        # Note: In game world, increasing Y is down, so we negate dy_pixels
        screen_x = int(center_x + dx_pixels)
        screen_y = int(center_y - dy_pixels)
        
        return (screen_x, screen_y)
    
    def calculate_drag_vector(self, target_x: float, target_y: float) -> Tuple[int, int]:
        """
        Calculate the drag vector needed to move to target coordinates.
        
        Args:
            target_x: Target X coordinate in game world
            target_y: Target Y coordinate in game world
            
        Returns:
            (drag_x, drag_y) tuple representing the drag vector in pixels
        """
        # Get current position
        current_pos = self.current_position
        
        # Calculate offset in game units
        dx_game = target_x - current_pos.x
        dy_game = target_y - current_pos.y
        
        # Convert to pixels using calibration
        # Note: Drag is in opposite direction of coordinate change
        drag_x = -int(dx_game * self.pixels_per_game_unit_x)
        drag_y = int(dy_game * self.pixels_per_game_unit_y)
        
        logger.info(f"Calculated drag vector: ({drag_x}, {drag_y}) for target ({target_x}, {target_y})")
        return (drag_x, drag_y)
    
    def estimate_position_after_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> GameWorldPosition:
        """
        Estimate the new position after a drag operation.
        
        Args:
            start_x: Start X coordinate of drag (screen pixels)
            start_y: Start Y coordinate of drag (screen pixels)
            end_x: End X coordinate of drag (screen pixels)
            end_y: End Y coordinate of drag (screen pixels)
            
        Returns:
            Estimated new position in game world coordinates
        """
        # Calculate drag distance in pixels
        drag_x = end_x - start_x
        drag_y = end_y - start_y
        
        # Convert to game units
        # Note: Drag is in opposite direction of coordinate change
        dx_game = -drag_x / self.pixels_per_game_unit_x
        dy_game = drag_y / self.pixels_per_game_unit_y
        
        # Calculate new position
        new_x = self.current_position.x + dx_game
        new_y = self.current_position.y + dy_game
        
        logger.info(f"Estimated position after drag: ({new_x:.2f}, {new_y:.2f})")
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
    
    def is_position_on_screen(self, game_x: float, game_y: float) -> bool:
        """
        Check if a game world position is visible on the current screen.
        
        Args:
            game_x: X coordinate in game world
            game_y: Y coordinate in game world
            
        Returns:
            True if the position is on screen, False otherwise
        """
        # Convert to screen coordinates
        screen_coords = self.game_to_screen_coords(game_x, game_y)
        
        # Get window position
        window_pos = self.window_manager.get_window_position()
        if not window_pos:
            logger.error("Failed to get window position")
            return False
            
        # Check if coordinates are within window bounds
        x_min = window_pos[0]
        y_min = window_pos[1]
        x_max = window_pos[0] + window_pos[2]
        y_max = window_pos[1] + window_pos[3]
        
        return (x_min <= screen_coords[0] <= x_max and 
                y_min <= screen_coords[1] <= y_max)
    
    def get_visible_game_area(self) -> Tuple[float, float, float, float]:
        """
        Get the visible game area in game world coordinates.
        
        Returns:
            (min_x, min_y, max_x, max_y) tuple representing the visible area
        """
        # Get window position
        window_pos = self.window_manager.get_window_position()
        if not window_pos:
            logger.error("Failed to get window position")
            return (0, 0, 0, 0)
            
        # Get screen corners
        top_left = (window_pos[0], window_pos[1])
        bottom_right = (window_pos[0] + window_pos[2], window_pos[1] + window_pos[3])
        
        # Convert to game coordinates
        top_left_game = self.screen_to_game_coords(top_left[0], top_left[1])
        bottom_right_game = self.screen_to_game_coords(bottom_right[0], bottom_right[1])
        
        # Return visible area
        return (
            top_left_game.x,
            top_left_game.y,
            bottom_right_game.x,
            bottom_right_game.y
        )
    
    def get_calibration_point(self, index: int) -> Optional[Tuple[GameWorldPosition, GameWorldPosition]]:
        """
        Get a calibration point by index.
        
        Args:
            index: Index of the calibration point
            
        Returns:
            Tuple of (screen_position, game_position) or None if index is invalid
        """
        try:
            if 0 <= index < len(self.calibration_points):
                return self.calibration_points[index]
            else:
                logger.warning(f"Invalid calibration point index: {index}")
                return None
        except Exception as e:
            logger.error(f"Error getting calibration point: {e}", exc_info=True)
            return None 