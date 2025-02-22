"""World scanning and navigation system."""

from typing import List, Optional, Dict, Any
import logging
import time
from PyQt6.QtCore import QObject, pyqtSignal
import pytesseract
import cv2
import numpy as np

from .world_position import WorldPosition
from ..capture import CaptureManager, PatternMatcher
from ..core import CoordinateManager, CoordinateSpace

logger = logging.getLogger(__name__)

class WorldScanner(QObject):
    """
    Automated system for exploring and scanning the game world.
    
    This class provides systematic exploration of the game world by:
    1. Reading current coordinates using OCR (Optical Character Recognition)
    2. Moving to new positions by simulating coordinate input
    3. Generating efficient search patterns for exploration
    4. Working with pattern matching to find specific game elements
    
    The scanner uses a spiral search pattern to methodically cover an area
    around the starting position, ensuring thorough exploration while
    minimizing travel distance.
    
    Signals:
        position_found: Emits when current position is detected
        position_changed: Emits when position changes
        scan_complete: Emits when scan is finished
        error_occurred: Emits when an error occurs
    """
    
    # Signals
    position_found = pyqtSignal(object)  # WorldPosition
    position_changed = pyqtSignal(object)  # WorldPosition
    scan_complete = pyqtSignal(bool)  # success
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(
        self,
        capture_manager: CaptureManager,
        coordinate_manager: CoordinateManager,
        start_pos: WorldPosition,
        scan_step: int = 50,
        move_delay: float = 1.0
    ) -> None:
        """
        Initialize the world scanner.
        
        Args:
            capture_manager: Capture manager instance
            coordinate_manager: Coordinate manager instance
            start_pos: Initial position to start scanning from
            scan_step: Distance between each scan position
            move_delay: Time to wait after moving (seconds)
        """
        super().__init__()
        
        self.capture_manager = capture_manager
        self.coordinate_manager = coordinate_manager
        self.current_pos = start_pos
        self.start_pos = start_pos
        self.scan_step = scan_step
        self.move_delay = move_delay
        self.visited_positions: List[WorldPosition] = []
        
        # OCR regions
        self.coord_regions = {
            'x': 'world_coord_x',
            'y': 'world_coord_y',
            'k': 'world_coord_k'
        }
        
        # Initialize state
        self.is_scanning = False
        self.should_stop = False
        
        logger.debug("World scanner initialized")
        
    def get_current_position(self) -> Optional[WorldPosition]:
        """
        Get the current position from coordinate regions.
        
        Returns:
            WorldPosition if coordinates found, None otherwise
        """
        try:
            coordinates = {}
            
            # Process each coordinate region
            for coord_type, region_name in self.coord_regions.items():
                # Capture and process region
                image = self.capture_manager.capture_region(
                    region_name,
                    save_debug=True
                )
                if image is None:
                    continue
                    
                # Preprocess for OCR
                image = self.capture_manager.preprocess_image(
                    image,
                    for_ocr=True
                )
                
                # Perform OCR
                text = pytesseract.image_to_string(
                    image,
                    config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
                )
                
                # Clean text and get value
                try:
                    value = int(''.join(filter(str.isdigit, text.strip())))
                    coordinates[coord_type] = value
                except ValueError:
                    logger.warning(f"Failed to parse {coord_type} coordinate")
                    coordinates[coord_type] = 0
                    
            if all(coord in coordinates for coord in ['x', 'y', 'k']):
                position = WorldPosition(
                    x=coordinates['x'],
                    y=coordinates['y'],
                    k=coordinates['k']
                )
                logger.info(f"Successfully detected position: {position}")
                return position
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            self.error_occurred.emit(str(e))
            return None
            
    def move_to_position(self, target: WorldPosition) -> bool:
        """
        Move to specific coordinates.
        
        Args:
            target: Target position to move to
            
        Returns:
            bool: True if move successful
        """
        try:
            logger.info(f"Moving to position: {target}")
            
            # Get input regions
            x_input = self.coordinate_manager.get_region(
                'world_input_x',
                CoordinateSpace.SCREEN
            )
            y_input = self.coordinate_manager.get_region(
                'world_input_y',
                CoordinateSpace.SCREEN
            )
            k_input = self.coordinate_manager.get_region(
                'world_input_k',
                CoordinateSpace.SCREEN
            )
            
            if not all([x_input, y_input, k_input]):
                raise RuntimeError("Could not find coordinate input regions")
                
            # TODO: Implement coordinate input simulation
            # This will require mouse/keyboard control implementation
            
            # Wait for move to complete
            time.sleep(self.move_delay)
            
            # Verify position
            current = self.get_current_position()
            if current == target:
                self.current_pos = target
                self.visited_positions.append(target)
                self.position_changed.emit(target)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}")
            self.error_occurred.emit(str(e))
            return False
            
    def generate_spiral_pattern(self, max_distance: int) -> List[WorldPosition]:
        """
        Generate spiral search pattern positions.
        
        Args:
            max_distance: Maximum distance from start position
            
        Returns:
            List of positions to visit
        """
        positions = []
        x, y = self.start_pos.x, self.start_pos.y
        dx, dy = 0, -self.scan_step
        steps = 1
        step_count = 0
        
        while abs(x - self.start_pos.x) <= max_distance and abs(y - self.start_pos.y) <= max_distance:
            x += dx
            y += dy
            
            # Keep coordinates in valid range
            x = max(0, min(x, 999))
            y = max(0, min(y, 999))
            
            positions.append(WorldPosition(x, y, self.start_pos.k))
            
            step_count += 1
            if step_count == steps:
                step_count = 0
                # Rotate 90 degrees
                dx, dy = -dy, dx
                if dy == 0:  # Completed a line
                    steps += 1
                    
        return positions
        
    def scan_world_until_match(
        self,
        pattern_matcher: PatternMatcher,
        max_distance: int = 500
    ) -> Optional[WorldPosition]:
        """
        Scan world until pattern is found.
        
        Args:
            pattern_matcher: Pattern matcher to use
            max_distance: Maximum distance to search
            
        Returns:
            Position where pattern was found, or None
        """
        try:
            self.is_scanning = True
            self.should_stop = False
            
            # Generate search pattern
            positions = self.generate_spiral_pattern(max_distance)
            logger.info(f"Generated {len(positions)} positions to scan")
            
            # Visit each position
            for pos in positions:
                if self.should_stop:
                    logger.info("Scan stopped by request")
                    break
                    
                # Move to position
                if not self.move_to_position(pos):
                    continue
                    
                # Look for pattern
                matches = pattern_matcher.find_matches(save_debug=True)
                if matches:
                    logger.info(f"Found pattern at position: {pos}")
                    self.scan_complete.emit(True)
                    return pos
                    
            logger.info("Scan complete - no matches found")
            self.scan_complete.emit(False)
            return None
            
        except Exception as e:
            logger.error(f"Error during world scan: {e}")
            self.error_occurred.emit(str(e))
            return None
            
        finally:
            self.is_scanning = False
            
    def stop_scan(self) -> None:
        """Stop current scan operation."""
        self.should_stop = True
        logger.info("Scan stop requested")
        
    def get_debug_info(self) -> Dict[str, Any]:
        """Get current scanner state for debugging."""
        return {
            "current_position": str(self.current_pos),
            "start_position": str(self.start_pos),
            "scan_step": self.scan_step,
            "move_delay": self.move_delay,
            "is_scanning": self.is_scanning,
            "visited_positions": len(self.visited_positions),
            "coord_regions": self.coord_regions
        } 