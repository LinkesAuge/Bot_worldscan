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
        return {
            'name': self.name,
            'screen_start': self.screen_start,
            'screen_end': self.screen_end,
            'game_start': self.game_start.__dict__ if self.game_start else None,
            'game_end': self.game_end.__dict__ if self.game_end else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DirectionDefinition':
        """Create from dictionary."""
        game_start = GameWorldPosition(**data['game_start']) if data.get('game_start') else None
        game_end = GameWorldPosition(**data['game_end']) if data.get('game_end') else None
        
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
            
            # Perform calibration runs
            for i in range(num_runs):
                logger.info(f"Calibration run {i+1}/{num_runs}")
                
                # Test North direction
                if not self._calibrate_direction(self.north_definition, north_measurements):
                    logger.error("North calibration failed")
                    return False
                
                # Test East direction
                if not self._calibrate_direction(self.east_definition, east_measurements):
                    logger.error("East calibration failed")
                    return False
            
            # Calculate averages
            if north_measurements and east_measurements:
                # Calculate Y calibration from North measurements
                y_ratios = [m[0] / m[1] for m in north_measurements if m[1] != 0]
                if y_ratios:
                    self.pixels_per_game_unit_y = np.mean(y_ratios)
                
                # Calculate X calibration from East measurements
                x_ratios = [m[0] / m[1] for m in east_measurements if m[1] != 0]
                if x_ratios:
                    self.pixels_per_game_unit_x = np.mean(x_ratios)
                
                logger.info(f"Calibration successful: X={self.pixels_per_game_unit_x:.2f}, Y={self.pixels_per_game_unit_y:.2f}")
                return True
            
            logger.error("No valid measurements for calibration")
            return False
            
        except Exception as e:
            logger.error(f"Error during calibration: {e}")
            return False
    
    def get_inverse_direction(self, name: str) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Get the inverse movement for a direction.
        
        Args:
            name: Direction name ("North" or "East")
            
        Returns:
            Optional[Tuple[Tuple[int, int], Tuple[int, int]]]: (start, end) points for inverse movement
        """
        definition = self._get_definition(name)
        if not definition:
            return None
            
        # Inverse is just swapping start and end points
        return (definition.screen_end, definition.screen_start)
    
    def _get_definition(self, name: str) -> Optional[DirectionDefinition]:
        """Get direction definition by name."""
        if name == "North":
            return self.north_definition
        elif name == "East":
            return self.east_definition
        return None
    
    def _get_current_position(self) -> Optional[GameWorldPosition]:
        """Get current game world position."""
        # Update position from OCR
        if not self.text_ocr.update_current_position_from_ocr():
            return None
        return self.text_ocr.current_position
    
    def _perform_drag(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Perform a drag operation."""
        try:
            self.game_actions.drag_mouse(start[0], start[1], end[0], end[1])
            return True
        except Exception as e:
            logger.error(f"Error performing drag: {e}")
            return False
    
    def _positions_match(self, pos1: GameWorldPosition, pos2: GameWorldPosition, tolerance: int = 1) -> bool:
        """Check if two positions match within tolerance."""
        return (
            abs(pos1.x - pos2.x) <= tolerance and
            abs(pos1.y - pos2.y) <= tolerance and
            pos1.k == pos2.k
        )
    
    def _calibrate_direction(self, definition: DirectionDefinition, measurements: List[Tuple[float, float]]) -> bool:
        """
        Perform calibration measurement for a direction.
        
        Args:
            definition: Direction definition to test
            measurements: List to store (pixel_distance, game_unit_distance) measurements
            
        Returns:
            bool: True if measurement was successful
        """
        try:
            # Get start position
            start_pos = self._get_current_position()
            if not start_pos:
                return False
            
            # Perform drag
            if not self._perform_drag(definition.screen_start, definition.screen_end):
                return False
            
            # Wait for movement to complete
            time.sleep(0.5)
            
            # Get end position
            end_pos = self._get_current_position()
            if not end_pos:
                return False
            
            # Calculate distances
            pixel_distance = ((definition.screen_end[0] - definition.screen_start[0]) ** 2 +
                            (definition.screen_end[1] - definition.screen_start[1]) ** 2) ** 0.5
            
            game_unit_distance = ((end_pos.x - start_pos.x) ** 2 +
                                (end_pos.y - start_pos.y) ** 2) ** 0.5
            
            # Store measurement
            if game_unit_distance > 0:
                measurements.append((pixel_distance, game_unit_distance))
            
            # Return to start (inverse drag)
            if not self._perform_drag(definition.screen_end, definition.screen_start):
                return False
            
            # Wait for movement to complete
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during direction calibration: {e}")
            return False
    
    def _save_definitions(self) -> None:
        """Save direction definitions to file."""
        try:
            data = {
                'north': self.north_definition.to_dict() if self.north_definition else None,
                'east': self.east_definition.to_dict() if self.east_definition else None,
                'calibration': {
                    'runs': self.calibration_runs,
                    'pixels_per_game_unit_x': self.pixels_per_game_unit_x,
                    'pixels_per_game_unit_y': self.pixels_per_game_unit_y
                }
            }
            
            file_path = self.config_dir / "direction_definitions.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            logger.info(f"Saved direction definitions to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving direction definitions: {e}")
    
    def _load_definitions(self) -> None:
        """Load direction definitions from file."""
        try:
            file_path = self.config_dir / "direction_definitions.json"
            if not file_path.exists():
                logger.info("No saved direction definitions found")
                return
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Load direction definitions
            if data.get('north'):
                self.north_definition = DirectionDefinition.from_dict(data['north'])
            if data.get('east'):
                self.east_definition = DirectionDefinition.from_dict(data['east'])
                
            # Load calibration data
            if 'calibration' in data:
                self.calibration_runs = data['calibration'].get('runs', 3)
                self.pixels_per_game_unit_x = data['calibration'].get('pixels_per_game_unit_x', 0.0)
                self.pixels_per_game_unit_y = data['calibration'].get('pixels_per_game_unit_y', 0.0)
                
            logger.info(f"Loaded direction definitions from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading direction definitions: {e}") 