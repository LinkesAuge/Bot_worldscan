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

logger = logging.getLogger(__name__)

@dataclass
class DirectionDefinition:
    """
    Represents a cardinal direction movement definition.
    
    Stores the screen coordinates for the drag operation and the game world
    coordinates at start and end points.
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
        config_dir: str = "scout/config"
    ):
        """
        Initialize the direction system.
        
        Args:
            window_manager: For capturing screenshots and window info
            text_ocr: For reading game coordinates
            game_actions: For performing mouse actions
            config_dir: Directory for saving/loading definitions
        """
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.config_dir = Path(config_dir)
        
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
                logger.info(f"North measurements: {north_measurements}")
                    
                # Calibrate East
                logger.info("Starting East calibration...")
                if not self._calibrate_direction(self.east_definition, east_measurements):
                    logger.error("East calibration failed")
                    return False
                logger.info(f"East measurements: {east_measurements}")
                
            # Calculate average ratios
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
                
                self.pixels_per_game_unit_y = np.mean(y_values)
                self.pixels_per_game_unit_x = np.mean(x_values)
                
                # Calculate screen distances
                north_screen_dy = abs(self.north_definition.screen_end[1] - self.north_definition.screen_start[1])
                east_screen_dx = abs(self.east_definition.screen_end[0] - self.east_definition.screen_start[0])
                
                # Validate screen distances
                if north_screen_dy > max_screen_distance or east_screen_dx > max_screen_distance:
                    logger.error(f"Screen distances exceed window size - North: {north_screen_dy}, East: {east_screen_dx}")
                    return False
                
                logger.info(f"Screen distances - North: {north_screen_dy} pixels, East: {east_screen_dx} pixels")
                
                # Calculate game units moved (with wrapping)
                north_game_dy = 0
                east_game_dx = 0
                
                # Safely check North movement
                if (self.north_definition.game_start and self.north_definition.game_end and 
                    self.north_definition.game_start.is_valid() and self.north_definition.game_end.is_valid()):
                    # Calculate wrapped distance considering direction
                    y_diff = self.north_definition.game_end.y - self.north_definition.game_start.y
                    north_game_dy = y_diff % 1000
                    # If the wrapped distance is more than half the world size, it's shorter to go the other way
                    if north_game_dy > 500:
                        north_game_dy = -(1000 - north_game_dy)
                    logger.info(f"North movement details:")
                    logger.info(f"  Start: {self.north_definition.game_start}")
                    logger.info(f"  End: {self.north_definition.game_end}")
                    logger.info(f"  Raw Y diff: {y_diff}")
                    logger.info(f"  Wrapped Y diff: {north_game_dy}")
                    logger.info(f"  Screen Y distance: {north_screen_dy}")
                else:
                    logger.error("Invalid North game positions")
                    return False
                    
                # Safely check East movement
                if (self.east_definition.game_start and self.east_definition.game_end and 
                    self.east_definition.game_start.is_valid() and self.east_definition.game_end.is_valid()):
                    # Calculate wrapped distance considering direction
                    x_diff = self.east_definition.game_end.x - self.east_definition.game_start.x
                    east_game_dx = x_diff % 1000
                    # If the wrapped distance is more than half the world size, it's shorter to go the other way
                    if east_game_dx > 500:
                        east_game_dx = -(1000 - east_game_dx)
                    logger.info(f"East movement details:")
                    logger.info(f"  Start: {self.east_definition.game_start}")
                    logger.info(f"  End: {self.east_definition.game_end}")
                    logger.info(f"  Raw X diff: {x_diff}")
                    logger.info(f"  Wrapped X diff: {east_game_dx}")
                    logger.info(f"  Screen X distance: {east_screen_dx}")
                else:
                    logger.error("Invalid East game positions")
                    return False
                
                # Log calibration results
                logger.info("Calibration Results:")
                logger.info(f"X Ratio (pixels per game unit): {self.pixels_per_game_unit_x:.2f}")
                logger.info(f"Y Ratio (pixels per game unit): {self.pixels_per_game_unit_y:.2f}")
                logger.info(f"Map to Pixel Translation:")
                logger.info(f"  North: {north_screen_dy} pixels = {abs(north_game_dy)} game units (ratio: {north_screen_dy/abs(north_game_dy):.2f})")
                logger.info(f"  East: {east_screen_dx} pixels = {abs(east_game_dx)} game units (ratio: {east_screen_dx/abs(east_game_dx):.2f})")
                
                # Save definitions with updated game positions
                self._save_definitions()
                
                return True
            
            logger.error("No valid measurements collected")
            return False
            
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
    
    def _get_current_position(self) -> Optional[GameWorldPosition]:
        """
        Get current game world position with retries.
        
        Returns:
            GameWorldPosition if valid coordinates were obtained, None otherwise
        """
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            # Process OCR region to get fresh coordinates
            self.text_ocr._process_region()
            
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
            
            logger.warning(f"Failed to get valid position (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
            
        logger.error("Failed to get valid position after all retries")
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
            # Convert window-relative coordinates to screen coordinates
            start_screen_x, start_screen_y = self.window_manager.client_to_screen(start[0], start[1])
            end_screen_x, end_screen_y = self.window_manager.client_to_screen(end[0], end[1])
            
            logger.debug(f"Dragging from window ({start[0]}, {start[1]}) to ({end[0]}, {end[1]})")
            logger.debug(f"Screen coordinates: ({start_screen_x}, {start_screen_y}) to ({end_screen_x}, {end_screen_y})")
            
            # Store initial position for validation
            initial_pos = self._get_current_position()
            if not initial_pos:
                logger.error("Failed to get initial position before drag")
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
                
            logger.debug(f"Drag complete: {initial_pos} -> {final_pos}")
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
            time.sleep(1.0)
            
            # Get start position with retries
            start_pos = self._get_current_position()
            if not start_pos:
                logger.error("Failed to get valid start position")
                return False
            
            logger.info(f"Start position: {start_pos}")
            
            # Store game start position
            definition.game_start = start_pos
            
            # Perform drag
            if not self._perform_drag(definition.screen_start, definition.screen_end):
                logger.error("Failed to perform drag")
                return False
            
            # Wait for movement and OCR to stabilize
            time.sleep(1.5)
            
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
                    # Use absolute values for ratio calculation
                    measurements.append((0, screen_distance / abs(game_distance)))
                    logger.info(f"North movement: {game_distance} game units ({abs(game_distance)} absolute), {screen_distance} pixels")
                    logger.info(f"North ratio: {screen_distance / abs(game_distance):.2f} pixels per game unit")
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
                    # Use absolute values for ratio calculation
                    measurements.append((screen_distance / abs(game_distance), 0))
                    logger.info(f"East movement: {game_distance} game units ({abs(game_distance)} absolute), {screen_distance} pixels")
                    logger.info(f"East ratio: {screen_distance / abs(game_distance):.2f} pixels per game unit")
                else:
                    logger.warning("No X movement detected for East direction")
            
            # Return to start
            if not self._perform_drag(definition.screen_end, definition.screen_start):
                logger.error("Failed to return to start")
                return False
            
            # Wait for movement to complete
            time.sleep(1.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during direction calibration: {e}")
            return False
    
    def _save_definitions(self) -> None:
        """Save direction definitions to file."""
        try:
            definitions = {
                'north': self.north_definition.to_dict() if self.north_definition else None,
                'east': self.east_definition.to_dict() if self.east_definition else None,
                'calibration': {
                    'pixels_per_game_unit_x': self.pixels_per_game_unit_x,
                    'pixels_per_game_unit_y': self.pixels_per_game_unit_y
                }
            }
            
            with open(self.config_dir / 'direction_definitions.json', 'w') as f:
                json.dump(definitions, f)
                
            logger.info("Saved direction definitions to scout/config/direction_definitions.json")
            
        except Exception as e:
            logger.error(f"Error saving definitions: {e}")
    
    def _load_definitions(self) -> None:
        """Load direction definitions from file."""
        try:
            if (self.config_dir / 'direction_definitions.json').exists():
                with open(self.config_dir / 'direction_definitions.json', 'r') as f:
                    definitions = json.load(f)
                    
                if definitions.get('north'):
                    self.north_definition = DirectionDefinition.from_dict(definitions['north'])
                    
                if definitions.get('east'):
                    self.east_definition = DirectionDefinition.from_dict(definitions['east'])
                    
                if definitions.get('calibration'):
                    self.pixels_per_game_unit_x = definitions['calibration']['pixels_per_game_unit_x']
                    self.pixels_per_game_unit_y = definitions['calibration']['pixels_per_game_unit_y']
                    
                logger.info("Loaded direction definitions from scout/config/direction_definitions.json")
                
        except Exception as e:
            logger.error(f"Error loading definitions: {e}") 