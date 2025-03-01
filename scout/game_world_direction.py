"""
Game World Direction System

This module provides functionality for defining and managing cardinal direction movements
in the game world. It handles:
- Direction definitions (North/East with their inverses South/West)
- Direction-based calibration
- Movement testing and validation
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import logging
import time
from pathlib import Path
import numpy as np

from scout.window_manager import WindowManager
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_position import GameWorldPosition
from scout.game_world_coordinator import GameWorldCoordinator
from scout.game_state import GameState
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class DirectionDefinition:
    """
    Represents a cardinal direction movement definition.
    
    Stores the screen coordinates for the drag operation and the game world
    coordinates at start and end points.
    
    Attributes:
        name: Direction name ("North" or "East")
        screen_start: Start point for drag (x, y)
        screen_end: End point for drag (x, y)
        game_start: Game position at start
        game_end: Game position at end
    """
    name: str  # "North" or "East"
    screen_start: Tuple[int, int]  # Start point for drag (x, y)
    screen_end: Tuple[int, int]  # End point for drag (x, y)
    game_start: Optional[GameWorldPosition] = None  # Game position at start
    game_end: Optional[GameWorldPosition] = None  # Game position at end
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        # Create game position dictionaries with only essential coordinates
        game_start_dict = None
        if self.game_start:
            game_start_dict = {
                'k': self.game_start.k,
                'x': self.game_start.x,
                'y': self.game_start.y
            }
            
        game_end_dict = None
        if self.game_end:
            game_end_dict = {
                'k': self.game_end.k,
                'x': self.game_end.x,
                'y': self.game_end.y
            }
        
        return {
            'name': self.name,
            'screen_start': self.screen_start,
            'screen_end': self.screen_end,
            'game_start': game_start_dict,
            'game_end': game_end_dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DirectionDefinition':
        """Create from dictionary."""
        # Create game positions with only k, x, y coordinates
        game_start = None
        if data.get('game_start'):
            start_data = data['game_start']
            game_start = GameWorldPosition(
                k=start_data.get('k'),
                x=start_data.get('x'),
                y=start_data.get('y')
            )
            
        game_end = None
        if data.get('game_end'):
            end_data = data['game_end']
            game_end = GameWorldPosition(
                k=end_data.get('k'),
                x=end_data.get('x'),
                y=end_data.get('y')
            )
        
        return cls(
            name=data['name'],
            screen_start=tuple(data['screen_start']),
            screen_end=tuple(data['screen_end']),
            game_start=game_start,
            game_end=game_end
        )

class GameWorldDirection:
    """
    Manages cardinal direction movements and direction-based calibration.
    
    This class provides functionality to:
    - Define North and East movements (with automatic South/West as inverses)
    - Test direction movements with multiple runs
    - Calculate calibration values from direction movements
    - Save and load direction definitions
    """
    
    def __init__(
        self,
        window_manager: WindowManager,
        text_ocr: TextOCR,
        game_actions: GameActions,
        config_manager: ConfigManager
    ):
        """
        Initialize the direction system.
        
        Args:
            window_manager: For capturing screenshots and window info
            text_ocr: For reading game coordinates
            game_actions: For performing mouse actions
            config_manager: For managing configuration settings
        """
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.config_manager = config_manager
        
        # Use game_state from text_ocr
        self.game_state = text_ocr.game_state
        self.game_coordinator = GameWorldCoordinator(window_manager, text_ocr, self.game_state, game_actions)
        
        # Set OCR preferences
        self.text_ocr.preferred_method = 'thresh3'  # Use thresh3 method for best results
        
        # Direction definitions
        self.north_definition: Optional[DirectionDefinition] = None
        self.east_definition: Optional[DirectionDefinition] = None
        
        # Calibration state
        self.calibration_runs = 3  # Default number of runs
        self.pixels_per_game_unit_x = 0.0
        self.pixels_per_game_unit_y = 0.0
        
        # Ensure config directory exists
        self.config_dir = Path('scout/config')  # Use fixed path relative to workspace
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load saved definitions
        self._load_definitions()
    
    def define_direction(
        self,
        name: str,
        screen_start: Tuple[int, int],
        screen_end: Tuple[int, int]
    ) -> bool:
        """
        Define a cardinal direction movement.
        
        Args:
            name: Direction name ("North" or "East")
            screen_start: Start point for drag (x, y)
            screen_end: End point for drag (x, y)
            
        Returns:
            bool: True if definition was successful
        """
        try:
            # Create definition
            definition = DirectionDefinition(
                name=name,
                screen_start=screen_start,
                screen_end=screen_end
            )
            
            # Store definition
            if name == "North":
                self.north_definition = definition
            elif name == "East":
                self.east_definition = definition
            else:
                logger.error(f"Invalid direction name: {name}")
                return False
            
            # Save definitions
            self._save_definitions()
            
            logger.info(f"Defined {name} direction: {screen_start} -> {screen_end}")
            return True
            
        except Exception as e:
            logger.error(f"Error defining direction: {e}")
            return False
    
    def test_direction(self, name: str, num_runs: int = 3) -> bool:
        """
        Test a direction definition with multiple runs.
        
        Args:
            name: Direction name ("North" or "East")
            num_runs: Number of test runs to perform
            
        Returns:
            bool: True if testing was successful
        """
        try:
            # Get definition
            definition = self._get_definition(name)
            if not definition:
                logger.error(f"No definition found for direction: {name}")
                return False
            
            # Store original position
            original_pos = self._get_current_position()
            if not original_pos:
                logger.error("Failed to get current position")
                return False
            
            # Perform test runs
            for i in range(num_runs):
                logger.info(f"Test run {i+1}/{num_runs} for {name}")
                
                # Get start position
                start_pos = self._get_current_position()
                if not start_pos:
                    logger.error("Failed to get start position")
                    return False
                
                # Perform drag
                if not self._perform_drag(definition.screen_start, definition.screen_end):
                    logger.error("Failed to perform drag")
                    return False
                
                # Wait for movement to complete
                time.sleep(0.5)
                
                # Get end position
                end_pos = self._get_current_position()
                if not end_pos:
                    logger.error("Failed to get end position")
                    return False
                
                # Return to start (inverse drag)
                if not self._perform_drag(definition.screen_end, definition.screen_start):
                    logger.error("Failed to return to start")
                    return False
                
                # Wait for movement to complete
                time.sleep(0.5)
                
                # Verify return position
                current_pos = self._get_current_position()
                if not current_pos or not self._positions_match(current_pos, original_pos):
                    logger.error("Failed to return to original position")
                    return False
                
                logger.info(f"Test run {i+1} successful")
            
            logger.info(f"All test runs successful for {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error testing direction: {e}")
            return False
    
    def calibrate(self, num_runs: int = 3) -> bool:
        """
        Perform calibration using direction definitions.
        
        Args:
            num_runs: Number of calibration runs to perform
            
        Returns:
            bool: True if calibration was successful
        """
        try:
            self.calibration_runs = num_runs
            
            # Verify we have both directions
            if not self.north_definition or not self.east_definition:
                logger.error("Missing direction definitions")
                return False
            
            # Store OCR state to restore later
            was_ocr_active = self.text_ocr.active
            
            try:
                # Activate OCR if not already active
                if not self.text_ocr.active:
                    logger.info("Activating OCR for calibration")
                    self.text_ocr.start()
                    time.sleep(1.0)  # Wait for OCR to initialize
                    
                    # Force several OCR updates to ensure stability
                    for _ in range(3):
                        self.text_ocr._process_region()
                        time.sleep(0.5)
                        
                    # Get initial position to verify OCR is working
                    test_pos = self._get_current_position()
                    if not test_pos or not test_pos.is_valid():
                        logger.error("OCR not providing valid coordinates after activation")
                        return False
                    logger.info("OCR stabilized and providing valid coordinates")
                
                # Lists to store measurements
                north_measurements = []
                east_measurements = []
                
                # Store initial position for reference
                initial_pos = self._get_current_position()
                if not initial_pos:
                    logger.error("Failed to get initial position")
                    return False
                    
                if not initial_pos.is_valid():
                    logger.error(f"Invalid initial position: {initial_pos}")
                    return False
                
                logger.info(f"Initial position: {initial_pos}")
                
                # Get screen dimensions for validation
                window_rect = self.window_manager.get_window_position()
                if not window_rect:
                    logger.error("Failed to get window dimensions")
                    return False
                max_screen_distance = max(window_rect[2], window_rect[3])  # Use larger window dimension
                logger.info(f"Window dimensions: {window_rect}, Max screen distance: {max_screen_distance}")
                
                # Perform calibration runs
                for i in range(num_runs):
                    logger.info(f"Calibration run {i+1}/{num_runs}")
                    
                    # Calibrate North
                    logger.info("Starting North calibration...")
                    if not self._calibrate_direction(self.north_definition, north_measurements):
                        logger.error("North calibration failed")
                        return False
                    
                    # Log intermediate results
                    if north_measurements:
                        y_values = [m[1] for m in north_measurements if m[1] > 0]
                        logger.info(f"North measurements after run {i+1}: {y_values}")
                        
                    # Calibrate East
                    logger.info("Starting East calibration...")
                    if not self._calibrate_direction(self.east_definition, east_measurements):
                        logger.error("East calibration failed")
                        return False
                    
                    # Log intermediate results
                    if east_measurements:
                        x_values = [m[0] for m in east_measurements if m[0] > 0]
                        logger.info(f"East measurements after run {i+1}: {x_values}")
                
                # Calculate final results
                if north_measurements and east_measurements:
                    # Calculate Y ratio from North measurements (only use Y values)
                    y_values = [m[1] for m in north_measurements if m[1] > 0]
                    x_values = [m[0] for m in east_measurements if m[0] > 0]
                    
                    if not y_values:
                        logger.error("No valid Y measurements for North direction")
                        return False
                        
                    if not x_values:
                        logger.error("No valid X measurements for East direction")
                        return False
                    
                    # Verify measurement consistency
                    y_std = np.std(y_values)
                    x_std = np.std(x_values)
                    y_mean = np.mean(y_values)
                    x_mean = np.mean(x_values)
                    
                    # Check if measurements are consistent (within 10% of mean)
                    if y_std > y_mean * 0.1 or x_std > x_mean * 0.1:
                        logger.error(f"Inconsistent measurements detected:")
                        logger.error(f"Y values (mean: {y_mean:.2f}, std: {y_std:.2f}): {y_values}")
                        logger.error(f"X values (mean: {x_mean:.2f}, std: {x_std:.2f}): {x_values}")
                        return False
                    
                    # Store final calibration values
                    self.pixels_per_game_unit_y = y_mean
                    self.pixels_per_game_unit_x = x_mean
                    
                    # Log final results
                    logger.info("Final Calibration Results:")
                    logger.info(f"X Ratio: {self.pixels_per_game_unit_x:.2f} pixels per game unit (std: {x_std:.2f})")
                    logger.info(f"Y Ratio: {self.pixels_per_game_unit_y:.2f} pixels per game unit (std: {y_std:.2f})")
                    logger.info(f"Measurements:")
                    logger.info(f"  North: {y_values}")
                    logger.info(f"  East: {x_values}")
                    
                    # Save definitions with updated game positions
                    self._save_definitions()
                    
                    return True
                
                logger.error("No valid measurements collected")
                return False
                
            finally:
                # Restore original OCR state
                if self.text_ocr.active != was_ocr_active:
                    logger.info("Restoring original OCR state")
                    if was_ocr_active:
                        self.text_ocr.start()
                    else:
                        self.text_ocr.stop()
                
        except Exception as e:
            logger.error(f"Error during calibration: {e}", exc_info=True)
            return False
    
    def get_inverse_direction(self, name: str) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Get the inverse of a direction (South for North, West for East).
        
        Args:
            name: Direction name ("North" or "East")
            
        Returns:
            Optional[Tuple[Tuple[int, int], Tuple[int, int]]]: Start and end points for inverse drag
        """
        definition = self._get_definition(name)
        if definition:
            return (definition.screen_end, definition.screen_start)
        return None
    
    def _get_definition(self, name: str) -> Optional[DirectionDefinition]:
        """Get direction definition by name."""
        if name == "North":
            return self.north_definition
        elif name == "East":
            return self.east_definition
        return None
    
    def get_current_position(self) -> Optional[GameWorldPosition]:
        """
        Get the current game world position.
        
        Returns:
            The current GameWorldPosition or None if not available
        """
        return self._get_current_position()

    def _get_current_position(self) -> Optional[GameWorldPosition]:
        """
        Get current game world position with retries.
        
        Returns:
            GameWorldPosition if valid coordinates were obtained, None otherwise
        """
        max_retries = 3
        retry_delay = 0.5
        
        # Check if we have a valid OCR region
        if not self.text_ocr.region:
            logger.error("No OCR region set - please set an OCR region in the overlay tab first")
            return None
            
        # Log current OCR region for debugging
        logger.info(f"Current OCR region: {self.text_ocr.region}")
        
        for attempt in range(max_retries):
            # Force OCR to process region and wait for result
            self.text_ocr._process_region()
            time.sleep(0.5)  # Wait for OCR to complete
            
            # Get coordinates from game state
            coords = self.game_state.coordinates
            if coords and coords.k is not None and coords.x is not None and coords.y is not None:
                # Create GameWorldPosition from coordinates
                position = GameWorldPosition(
                    k=coords.k,
                    x=coords.x,
                    y=coords.y
                )
                # Verify position is valid
                if position.is_valid():
                    logger.info(f"Got valid position: {position}")
                    return position
                else:
                    logger.warning(f"Invalid position values: k={coords.k}, x={coords.x}, y={coords.y}")
            else:
                logger.warning(f"Missing coordinate values: k={coords.k if coords else None}, x={coords.x if coords else None}, y={coords.y if coords else None}")
                logger.info("Please ensure coordinates are visible in the game window and OCR region is correctly positioned")
            
            if attempt < max_retries - 1:  # Don't wait after last attempt
                logger.warning(f"Failed to get valid position (attempt {attempt + 1}/{max_retries}) - retrying in {retry_delay} seconds")
                time.sleep(retry_delay)
            
        logger.error("Failed to get valid position after all retries")
        logger.error("Please check:")
        logger.error("1. OCR region is correctly positioned over the coordinates")
        logger.error("2. Game window is active and coordinates are visible")
        logger.error("3. No other windows are covering the coordinate display")
        return None
    
    def _perform_drag(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """
        Perform a drag operation.
        
        Args:
            start: Start point for drag (window-relative coordinates)
            end: End point for drag (window-relative coordinates)
            
        Returns:
            bool: True if drag was successful
        """
        try:
            # Get current window position and ensure it's active
            window_rect = self.window_manager.get_window_position()
            if not window_rect:
                logger.error("Could not get window position")
                return False
                
            # Get client area for proper bounds checking
            client_rect = self.window_manager.get_client_rect()
            if not client_rect:
                logger.error("Could not get client area")
                return False
                
            # Ensure window is active before performing drag
            if not self.window_manager.activate_window():
                logger.error("Failed to activate game window")
                return False
                
            # Wait a short moment for window activation
            time.sleep(0.1)
            
            # Convert client rect to relative coordinates
            client_left, client_top, client_right, client_bottom = client_rect
            client_width = client_right - client_left
            client_height = client_bottom - client_top
            
            # Log coordinates for debugging
            logger.info(f"Window-relative coordinates - Start: {start}, End: {end}")
            logger.info(f"Client area dimensions: {client_width}x{client_height}")
            
            # Convert window-relative coordinates to screen coordinates
            start_screen_x, start_screen_y = self.window_manager.client_to_screen(start[0], start[1])
            end_screen_x, end_screen_y = self.window_manager.client_to_screen(end[0], end[1])
            
            # Log converted screen coordinates
            logger.info(f"Screen coordinates - Start: ({start_screen_x}, {start_screen_y}), End: ({end_screen_x}, {end_screen_y})")
            
            # Store initial position for validation
            initial_pos = self._get_current_position()
            if not initial_pos:
                logger.error("Failed to get initial position before drag")
                return False
            
            logger.info(f"Initial game position: {initial_pos}")
            
            # Double-check window is still active
            if not self.window_manager.is_window_active():
                logger.error("Game window lost focus before drag")
                return False
            
            # Perform drag using screen coordinates
            drag_success = self.game_actions.drag_mouse(
                start_screen_x, start_screen_y,
                end_screen_x, end_screen_y,
                relative_to_window=False,  # Using screen coordinates
                duration=0.5  # Add consistent duration
            )
            
            if not drag_success:
                logger.error("Drag operation failed")
                return False
            
            # Wait for movement to settle
            time.sleep(0.5)
            
            # Update game coordinator's position
            self.game_coordinator.update_position_after_drag(
                start_screen_x, start_screen_y,
                end_screen_x, end_screen_y
            )
            
            # Verify movement occurred
            final_pos = self._get_current_position()
            if not final_pos:
                logger.error("Failed to get final position after drag")
                return False
                
            if final_pos.k == initial_pos.k and final_pos.x == initial_pos.x and final_pos.y == initial_pos.y:
                logger.warning("No position change detected after drag")
            
            logger.info(f"Final game position: {final_pos}")
            return True
            
        except Exception as e:
            logger.error(f"Error performing drag: {e}", exc_info=True)
            return False
    
    def _positions_match(self, pos1: GameWorldPosition, pos2: GameWorldPosition, tolerance: int = 1) -> bool:
        """
        Check if two positions match within tolerance.
        
        Args:
            pos1: First position
            pos2: Second position
            tolerance: Maximum allowed difference in coordinates
            
        Returns:
            bool: True if positions match within tolerance
        """
        try:
            # Check if both positions exist
            if pos1 is None or pos2 is None:
                return False
                
            # Check if both positions have valid coordinates
            if not pos1.is_valid() or not pos2.is_valid():
                return False
                
            # Check if positions are in the same kingdom
            if pos1.k != pos2.k:
                return False
                
            # Calculate wrapped distances
            distances = pos1.distance_to(pos2)
            if distances is None:
                return False
                
            dx, dy = distances
            
            # Check if distances are within tolerance
            return abs(dx) <= tolerance and abs(dy) <= tolerance
            
        except Exception as e:
            logger.error(f"Error comparing positions: {e}")
            return False
    
    def _calibrate_direction(self, definition: DirectionDefinition, measurements: List[Tuple[float, float]]) -> bool:
        """
        Calibrate a direction by measuring game unit distances.
        
        Args:
            definition: Direction definition to calibrate
            measurements: List to store measurements
            
        Returns:
            bool: True if calibration was successful
        """
        try:
            # Wait for OCR to stabilize
            time.sleep(1.5)  # Increased initial wait
            
            # Force multiple OCR updates to ensure stability
            for _ in range(3):
                self.text_ocr._process_region()
                time.sleep(0.5)
            
            # Get start position with retries
            start_pos = self._get_current_position()
            if not start_pos:
                logger.error("Failed to get valid start position")
                return False
            
            logger.info(f"Start position: {start_pos}")
            
            # Store game start position
            definition.game_start = start_pos
            
            # Get window dimensions for validation
            window_rect = self.window_manager.get_window_position()
            if not window_rect:
                logger.error("Failed to get window dimensions")
                return False
            
            # Perform drag
            if not self._perform_drag(definition.screen_start, definition.screen_end):
                logger.error("Failed to perform drag")
                return False
            
            # Wait longer for movement and OCR to stabilize
            time.sleep(2.0)  # Increased wait after drag
            
            # Force multiple OCR updates to ensure stability
            for _ in range(3):
                self.text_ocr._process_region()
                time.sleep(0.5)
            
            # Get end position with retries
            end_pos = self._get_current_position()
            if not end_pos:
                logger.error("Failed to get valid end position")
                return False
                
            logger.info(f"End position: {end_pos}")
            
            # Store game end position
            definition.game_end = end_pos
            
            # Calculate distances in game units (with wrapping)
            if definition.name == "North":
                # For North, we care about Y distance
                # Calculate wrapped distance considering direction
                y_diff = end_pos.y - start_pos.y
                game_distance = y_diff % 1000  # Game world is 0-999
                # If the wrapped distance is more than half the world size, it's shorter to go the other way
                if game_distance > 500:
                    game_distance = -(1000 - game_distance)
                
                screen_distance = abs(definition.screen_end[1] - definition.screen_start[1])
                # Store pixels per game unit
                if abs(game_distance) > 0:  # Only store if we actually moved
                    # Calculate ratio
                    ratio = screen_distance / abs(game_distance)
                    
                    # Check if this ratio is significantly different from previous measurements
                    if measurements:
                        prev_ratios = [m[1] for m in measurements if m[1] > 0]
                        avg_ratio = np.mean(prev_ratios)
                        # Increase tolerance to 20%
                        if abs(ratio - avg_ratio) > avg_ratio * 0.2:  # 20% tolerance
                            logger.warning(f"Inconsistent Y ratio detected: {ratio:.2f} vs average {avg_ratio:.2f}")
                            # Don't fail immediately, just log warning
                            logger.warning("Continuing with calibration despite ratio difference")
                    
                    # Store measurement
                    measurements.append((0, ratio))
                    logger.info(f"North movement: {game_distance} game units ({abs(game_distance)} absolute), {screen_distance} pixels")
                    logger.info(f"North ratio: {ratio:.2f} pixels per game unit")
                else:
                    logger.warning("No Y movement detected for North direction")
            else:  # East
                # For East, we care about X distance
                # Calculate wrapped distance considering direction
                x_diff = end_pos.x - start_pos.x
                game_distance = x_diff % 1000
                # If the wrapped distance is more than half the world size, it's shorter to go the other way
                if game_distance > 500:
                    game_distance = -(1000 - game_distance)
                
                screen_distance = abs(definition.screen_end[0] - definition.screen_start[0])
                # Store pixels per game unit
                if abs(game_distance) > 0:  # Only store if we actually moved
                    # Calculate ratio
                    ratio = screen_distance / abs(game_distance)
                    
                    # Check if this ratio is significantly different from previous measurements
                    if measurements:
                        prev_ratios = [m[0] for m in measurements if m[0] > 0]
                        avg_ratio = np.mean(prev_ratios)
                        # Increase tolerance to 20%
                        if abs(ratio - avg_ratio) > avg_ratio * 0.2:  # 20% tolerance
                            logger.warning(f"Inconsistent X ratio detected: {ratio:.2f} vs average {avg_ratio:.2f}")
                            # Don't fail immediately, just log warning
                            logger.warning("Continuing with calibration despite ratio difference")
                    
                    # Store measurement
                    measurements.append((ratio, 0))
                    logger.info(f"East movement: {game_distance} game units ({abs(game_distance)} absolute), {screen_distance} pixels")
                    logger.info(f"East ratio: {ratio:.2f} pixels per game unit")
                else:
                    logger.warning("No X movement detected for East direction")
            
            # Return to start
            if not self._perform_drag(definition.screen_end, definition.screen_start):
                logger.error("Failed to return to start")
                return False
            
            # Wait longer for return movement to complete
            time.sleep(2.0)  # Increased wait after return drag
            
            # Force multiple OCR updates to ensure stability
            for _ in range(3):
                self.text_ocr._process_region()
                time.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during direction calibration: {e}")
            return False
    
    def _save_definitions(self) -> None:
        """Save direction definitions to config."""
        try:
            # Convert definitions to serializable format
            data = {
                'north': {
                    'screen_start': self.north_definition.screen_start if self.north_definition else None,
                    'screen_end': self.north_definition.screen_end if self.north_definition else None,
                    'game_start': self._game_coords_to_dict(self.north_definition.game_start) if self.north_definition else None,
                    'game_end': self._game_coords_to_dict(self.north_definition.game_end) if self.north_definition else None
                },
                'east': {
                    'screen_start': self.east_definition.screen_start if self.east_definition else None,
                    'screen_end': self.east_definition.screen_end if self.east_definition else None,
                    'game_start': self._game_coords_to_dict(self.east_definition.game_start) if self.east_definition else None,
                    'game_end': self._game_coords_to_dict(self.east_definition.game_end) if self.east_definition else None
                },
                'calibration': {
                    'pixels_per_game_unit_x': self.pixels_per_game_unit_x,
                    'pixels_per_game_unit_y': self.pixels_per_game_unit_y
                }
            }
            
            # Save to file
            definitions_file = self.config_dir / 'direction_definitions.json'
            with open(definitions_file, 'w') as f:
                json.dump(data, f, indent=4)
                
            logger.info("Saved direction definitions to config")
            
        except Exception as e:
            logger.error(f"Error saving direction definitions: {e}", exc_info=True)
            
    def _load_definitions(self) -> None:
        """Load direction definitions from config."""
        try:
            definitions_file = self.config_dir / 'direction_definitions.json'
            if definitions_file.exists():
                with open(definitions_file, 'r') as f:
                    data = json.load(f)
                    
                # Load North definition
                if data.get('north'):
                    north = data['north']
                    if all(v is not None for v in [north['screen_start'], north['screen_end']]):
                        self.north_definition = DirectionDefinition(
                            name="North",
                            screen_start=tuple(north['screen_start']),
                            screen_end=tuple(north['screen_end']),
                            game_start=self._dict_to_game_coords(north['game_start']),
                            game_end=self._dict_to_game_coords(north['game_end'])
                        )
                        
                # Load East definition
                if data.get('east'):
                    east = data['east']
                    if all(v is not None for v in [east['screen_start'], east['screen_end']]):
                        self.east_definition = DirectionDefinition(
                            name="East",
                            screen_start=tuple(east['screen_start']),
                            screen_end=tuple(east['screen_end']),
                            game_start=self._dict_to_game_coords(east['game_start']),
                            game_end=self._dict_to_game_coords(east['game_end'])
                        )
                        
                # Load calibration values
                if data.get('calibration'):
                    self.pixels_per_game_unit_x = data['calibration']['pixels_per_game_unit_x']
                    self.pixels_per_game_unit_y = data['calibration']['pixels_per_game_unit_y']
                    
                logger.info("Loaded direction definitions from config")
                
        except Exception as e:
            logger.error(f"Error loading direction definitions: {e}", exc_info=True)
            
    def _game_coords_to_dict(self, position: Optional[GameWorldPosition]) -> Optional[Dict[str, int]]:
        """
        Convert GameWorldPosition to dictionary format.
        
        Args:
            position: GameWorldPosition to convert
            
        Returns:
            Dictionary with k, x, y coordinates or None if position is None
        """
        if position is None:
            return None
        return {'k': position.k, 'x': position.x, 'y': position.y}
        
    def _dict_to_game_coords(self, data: Optional[Dict[str, int]]) -> Optional[GameWorldPosition]:
        """
        Convert dictionary to GameWorldPosition.
        
        Args:
            data: Dictionary containing k, x, y coordinates
            
        Returns:
            GameWorldPosition instance or None if data is None
        """
        if data is None:
            return None
        return GameWorldPosition(k=data['k'], x=data['x'], y=data['y'])

    def perform_drag(self, direction: str) -> bool:
        """
        Perform a drag operation in the specified direction.
        
        Args:
            direction: Direction name ("North", "South", "East", or "West")
            
        Returns:
            bool: True if drag was successful
        """
        try:
            # Get current window position
            window_rect = self.window_manager.get_window_position()
            if not window_rect:
                logger.error("Could not get window position")
                return False
            
            # Get direction definition and window-relative coordinates
            if direction == "North":
                if not self.north_definition:
                    logger.error("North direction not defined")
                    return False
                # Use screen coordinates directly
                start = self.north_definition.screen_start
                end = self.north_definition.screen_end
                logger.info(f"Using North definition - Start: {start}, End: {end}")
            elif direction == "South":
                if not self.north_definition:
                    logger.error("North direction not defined (needed for South)")
                    return False
                # Use inverse of North coordinates
                start = self.north_definition.screen_end
                end = self.north_definition.screen_start
                logger.info(f"Using South (inverse North) - Start: {start}, End: {end}")
            elif direction == "East":
                if not self.east_definition:
                    logger.error("East direction not defined")
                    return False
                # Use screen coordinates directly
                start = self.east_definition.screen_start
                end = self.east_definition.screen_end
                logger.info(f"Using East definition - Start: {start}, End: {end}")
            elif direction == "West":
                if not self.east_definition:
                    logger.error("East direction not defined (needed for West)")
                    return False
                # Use inverse of East coordinates
                start = self.east_definition.screen_end
                end = self.east_definition.screen_start
                logger.info(f"Using West (inverse East) - Start: {start}, End: {end}")
            else:
                logger.error(f"Invalid direction: {direction}")
                return False
            
            # Log window position for reference
            logger.info(f"Current window position: {window_rect}")
            
            # Perform drag with screen coordinates
            return self._perform_drag(start, end)
            
        except Exception as e:
            logger.error(f"Error performing drag in direction {direction}: {e}")
            return False

    def calculate_wrapped_distance(self, start_pos: GameWorldPosition, end_pos: GameWorldPosition) -> Tuple[int, int]:
        """
        Calculate wrapped distances between two positions in both X and Y directions.
        
        Args:
            start_pos: Starting position
            end_pos: Ending position
            
        Returns:
            Tuple[int, int]: (x_distance, y_distance) where each is the shortest wrapped distance
                            Positive values indicate East/South movement, negative for West/North
        """
        try:
            if not (start_pos and end_pos and start_pos.is_valid() and end_pos.is_valid()):
                logger.error("Invalid positions for distance calculation")
                return (0, 0)
                
            # Calculate X distance with wrapping
            x_diff = end_pos.x - start_pos.x
            x_distance = x_diff % 1000
            if x_distance > 500:
                x_distance = -(1000 - x_distance)
                
            # Calculate Y distance with wrapping
            y_diff = end_pos.y - start_pos.y
            y_distance = y_diff % 1000
            if y_distance > 500:
                y_distance = -(1000 - y_distance)
                
            logger.debug(f"Wrapped distances from {start_pos} to {end_pos}: dx={x_distance}, dy={y_distance}")
            return (x_distance, y_distance)
            
        except Exception as e:
            logger.error(f"Error calculating wrapped distances: {e}")
            return (0, 0)

    def get_drag_distances(self) -> Tuple[int, int]:
        """
        Get the current drag distances for East and South movements.
        
        Returns:
            Tuple[int, int]: (east_distance, south_distance) in game units
        """
        try:
            east_distance = 0
            south_distance = 0
            
            # Calculate East distance
            if (self.east_definition and self.east_definition.game_start and 
                self.east_definition.game_end):
                x_distance, _ = self.calculate_wrapped_distance(
                    self.east_definition.game_start,
                    self.east_definition.game_end
                )
                east_distance = abs(x_distance)  # Use absolute value for grid movement
                
            # Calculate South distance (inverse of North)
            if (self.north_definition and self.north_definition.game_start and 
                self.north_definition.game_end):
                _, y_distance = self.calculate_wrapped_distance(
                    self.north_definition.game_start,
                    self.north_definition.game_end
                )
                south_distance = abs(y_distance)  # Use absolute value for grid movement
                
            return (east_distance, south_distance)
            
        except Exception as e:
            logger.error(f"Error getting drag distances: {e}")
            return (0, 0) 