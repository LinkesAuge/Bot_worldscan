"""
Game World Search

This module provides search functionality for finding templates in the game world.
It implements various search patterns and coordinates the movement between search positions.
"""

from typing import List, Tuple, Dict, Optional, Any, Set, Callable, Generator
import logging
import time
import json
from pathlib import Path
import numpy as np
import cv2
import math
from dataclasses import dataclass
from enum import Enum

from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher, GroupedMatch
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition
from scout.automation.search_patterns import (
    spiral_pattern, grid_pattern, 
    expanding_circles_pattern, quadtree_pattern
)
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class SearchPattern(Enum):
    """Available search patterns."""
    SPIRAL = "spiral"
    GRID = "grid"
    EXPANDING_CIRCLES = "expanding_circles"

@dataclass
class SearchResult:
    """Result of a template search operation."""
    template_name: str
    screen_position: Tuple[int, int]
    game_position: Optional[GameWorldPosition]
    confidence: float
    positions_checked: int = 0
    search_time: float = 0.0
    success: bool = False
    screenshot_path: Optional[str] = None

class GameWorldSearch:
    """
    Implements search functionality for finding templates in the game world.
    
    This class coordinates between the template matcher and game world coordinator
    to systematically search for templates using various patterns.
    """
    
    def __init__(
        self, 
        window_manager: WindowManager,
        template_matcher: TemplateMatcher,
        text_ocr: TextOCR,
        game_actions: GameActions,
        game_coordinator: GameWorldCoordinator,
        game_state=None
    ):
        """
        Initialize the game world search.
        
        Args:
            window_manager: The window manager instance
            template_matcher: The template matcher instance
            text_ocr: The text OCR instance
            game_actions: The game actions instance
            game_coordinator: The game world coordinator instance
            game_state: Optional GameState instance for coordinate tracking
        """
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.game_coordinator = game_coordinator
        self.game_state = game_state
        
        # Search history
        self.search_history: List[SearchResult] = []
        
        # Visited positions (to avoid revisiting)
        self.visited_positions: Set[Tuple[int, int]] = set()
        
        # Search configuration
        self.min_confidence = 0.8
        self.save_screenshots = False
        self.screenshot_dir = Path('search_screenshots')
        self.max_positions = 100  # Maximum number of positions to check
        self.position_visit_radius = 50  # Game units
        self.drag_delay = 1.0  # Seconds to wait after drag
        self.template_search_delay = 0.5  # Seconds to wait after template search
        
        # Search state variables
        self.templates = []
        self.grid_size = (0, 0)
        self.start_pos = None
        self.drag_distances = (0, 0)
        self.positions_checked = 0
        self.matches = []
        self.current_position = (0, 0)
        self.is_searching = False
        self.stop_requested = False
        
        # Get the view area dimensions based on 2:1 ratio
        window_pos = self.game_coordinator.window_manager.get_window_position()
        if window_pos:
            self.view_width_pixels = window_pos[2]
            self.view_height_pixels = window_pos[3]
        else:
            # Default to a reasonable size if window not found
            self.view_width_pixels = 1600
            self.view_height_pixels = 800
            
        # Calculate game world units per view
        self.view_width_units = self.view_width_pixels / self.game_coordinator.pixels_per_game_unit_x
        self.view_height_units = self.view_height_pixels / self.game_coordinator.pixels_per_game_unit_y
        
        logger.info(f"View dimensions: {self.view_width_units:.1f}x{self.view_height_units:.1f} game units")
        
        # Initialize
        if self.save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_spiral_pattern(self, max_distance: float) -> Generator[Tuple[float, float], None, None]:
        """
        Generate positions in a spiral pattern, accounting for 2:1 view ratio.
        
        Args:
            max_distance: Maximum distance from center in game units
            
        Yields:
            (x, y) tuples of game world coordinates to search
        """
        # Start at center
        x, y = 0, 0
        yield (x, y)
        
        # Calculate step sizes based on view dimensions
        # Use 80% overlap between views to ensure we don't miss anything
        step_x = self.view_width_units * 0.2
        step_y = self.view_height_units * 0.2
        
        # Spiral outward
        layer = 1
        while max(abs(x), abs(y)) < max_distance:
            # Move right
            for _ in range(layer):
                x += step_x
                if max(abs(x), abs(y)) >= max_distance:
                    return
                yield (x, y)
            
            # Move down
            for _ in range(layer):
                y += step_y
                if max(abs(x), abs(y)) >= max_distance:
                    return
                yield (x, y)
            
            # Move left
            for _ in range(layer + 1):
                x -= step_x
                if max(abs(x), abs(y)) >= max_distance:
                    return
                yield (x, y)
            
            # Move up
            for _ in range(layer + 1):
                y -= step_y
                if max(abs(x), abs(y)) >= max_distance:
                    return
                yield (x, y)
            
            layer += 2
            
    def _generate_grid_pattern(self, max_distance: float) -> Generator[Tuple[float, float], None, None]:
        """
        Generate positions in a grid pattern, accounting for 2:1 view ratio.
        
        Args:
            max_distance: Maximum distance from center in game units
            
        Yields:
            (x, y) tuples of game world coordinates to search
        """
        # Calculate step sizes based on view dimensions with 80% overlap
        step_x = self.view_width_units * 0.2
        step_y = self.view_height_units * 0.2
        
        # Calculate grid dimensions
        grid_size = math.ceil(max_distance * 2 / min(step_x, step_y))
        start_pos = -max_distance
        
        # Generate grid positions in a snake pattern for efficiency
        for row in range(grid_size):
            y = start_pos + row * step_y
            # Alternate direction for each row
            x_range = range(grid_size) if row % 2 == 0 else range(grid_size - 1, -1, -1)
            for col in x_range:
                x = start_pos + col * step_x
                if max(abs(x), abs(y)) <= max_distance:
                    yield (x, y)
                    
    def _generate_expanding_circles_pattern(self, max_distance: float) -> Generator[Tuple[float, float], None, None]:
        """
        Generate positions in expanding circles, accounting for 2:1 view ratio.
        
        Args:
            max_distance: Maximum distance from center in game units
            
        Yields:
            (x, y) tuples of game world coordinates to search
        """
        # Start at center
        yield (0, 0)
        
        # Calculate step sizes for circles based on view dimensions
        step_radius = min(self.view_width_units, self.view_height_units) * 0.2
        
        # Generate circles with increasing radius
        radius = step_radius
        while radius <= max_distance:
            # Calculate number of points based on circle circumference
            circumference = 2 * math.pi * radius
            num_points = max(8, int(circumference / min(step_radius, step_radius)))
            
            # Generate points around the circle
            for i in range(num_points):
                angle = (2 * math.pi * i) / num_points
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                yield (x, y)
                
            radius += step_radius
            
    def _move_to_position(self, target_x: float, target_y: float) -> bool:
        """
        Move to a target position using calibrated drag operations.
        
        Args:
            target_x: Target X coordinate in game world units
            target_y: Target Y coordinate in game world units
            
        Returns:
            bool: True if movement was successful
        """
        try:
            # Get current position
            current_pos = self.game_coordinator.current_position
            if not current_pos:
                logger.error("Failed to get current position")
                return False
                
            # Get direction system
            if not self.game_coordinator.direction_system:
                logger.error("No direction system available")
                return False
                
            # Calculate distances using direction system's method
            dx, dy = self.game_coordinator.direction_system.calculate_wrapped_distance(
                current_pos,
                GameWorldPosition(current_pos.k, target_x, target_y)
            )
            
            # Get direction definitions
            north_def = self.game_coordinator.direction_system.north_definition
            east_def = self.game_coordinator.direction_system.east_definition
            
            if not north_def or not east_def:
                logger.error("Missing direction definitions")
                return False
                
            # Get drag distances from direction system
            east_drag_dist, north_drag_dist = self.game_coordinator.direction_system.get_drag_distances()
            if not east_drag_dist or not north_drag_dist:
                logger.error("Invalid drag distances")
                return False
            
            # Calculate number of drags needed
            east_drags = int(abs(dx) / east_drag_dist) if east_drag_dist > 0 else 0
            north_drags = int(abs(dy) / north_drag_dist) if north_drag_dist > 0 else 0
            
            logger.info(f"Moving to ({target_x}, {target_y}) - Drags needed: E:{east_drags}, N:{north_drags}")
            
            # Perform east/west movement
            if abs(dx) > 0.1:  # Only move if significant distance
                for _ in range(east_drags):
                    if dx > 0:
                        # Move east
                        if not self._perform_drag(east_def.screen_start, east_def.screen_end):
                            return False
                    else:
                        # Move west (inverse of east)
                        if not self._perform_drag(east_def.screen_end, east_def.screen_start):
                            return False
                    time.sleep(self.drag_delay)
            
            # Perform north/south movement
            if abs(dy) > 0.1:  # Only move if significant distance
                for _ in range(north_drags):
                    if dy > 0:
                        # Move north
                        if not self._perform_drag(north_def.screen_start, north_def.screen_end):
                            return False
                    else:
                        # Move south (inverse of north)
                        if not self._perform_drag(north_def.screen_end, north_def.screen_start):
                            return False
                    time.sleep(self.drag_delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}")
            return False
            
    def _check_for_templates(self, templates: List[str]) -> Optional[SearchResult]:
        """
        Check for templates at the current position.
        
        Args:
            templates: List of template names to search for
            
        Returns:
            SearchResult if a template is found, None otherwise
        """
        try:
            # Take screenshot for template matching
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is None:
                logger.error("Failed to capture screenshot for template matching")
                return None
                
            # Convert screenshot to numpy array if needed
            if not isinstance(screenshot, np.ndarray):
                screenshot = np.array(screenshot)
            
            # Perform template matching
            matches = self.template_matcher.find_matches(templates, screenshot)
            if not matches:
                return None
                
            # Get the best match
            best_match = max(matches, key=lambda m: m.confidence)
            
            # Convert screen position to game position
            game_pos = self.game_coordinator.screen_to_game_coords(
                best_match.center[0],
                best_match.center[1]
            )
            
            # Save screenshot if enabled
            screenshot_path = None
            if self.save_screenshots:
                try:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"search_{best_match.template_name}_{timestamp}.png"
                    screenshot_path = str(self.screenshot_dir / filename)
                    cv2.imwrite(screenshot_path, screenshot)
                except Exception as e:
                    logger.error(f"Error saving search screenshot: {e}")
            
            return SearchResult(
                template_name=best_match.template_name,
                screen_position=best_match.center,
                game_position=game_pos,
                confidence=best_match.confidence,
                success=True,
                screenshot_path=screenshot_path
            )
            
        except Exception as e:
            logger.error(f"Error checking for templates: {e}")
            return None
            
    def search_templates(self, templates: List[str], pattern: SearchPattern = SearchPattern.SPIRAL,
                        max_distance: float = 100.0) -> Optional[SearchResult]:
        """
        Search for templates using the specified pattern.
        
        Args:
            templates: List of template names to search for
            pattern: Search pattern to use
            max_distance: Maximum distance from current position to search
            
        Returns:
            SearchResult if a template is found, None otherwise
        """
        try:
            # Get pattern generator
            if pattern == SearchPattern.SPIRAL:
                positions = self._generate_spiral_pattern(max_distance)
            elif pattern == SearchPattern.GRID:
                positions = self._generate_grid_pattern(max_distance)
            else:  # EXPANDING_CIRCLES
                positions = self._generate_expanding_circles_pattern(max_distance)
                
            # Get current position as reference
            start_pos = self.game_coordinator.current_position
            if not start_pos:
                logger.error("No current position available")
                return None
                
            # Search at each position
            for dx, dy in positions:
                # Calculate target position
                target_x = start_pos.x + dx
                target_y = start_pos.y + dy
                
                logger.info(f"Searching at position ({target_x:.1f}, {target_y:.1f})")
                
                # Move to position if not already there
                if not self.game_coordinator.is_position_on_screen(target_x, target_y):
                    if not self._move_to_position(target_x, target_y):
                        logger.warning(f"Failed to move to position ({target_x:.1f}, {target_y:.1f})")
                        continue
                
                # Check for templates
                result = self._check_for_templates(templates)
                if result:
                    logger.info(f"Found template {result.template_name} at {result.game_position}")
                    return result
                    
            logger.info("No templates found within search area")
            return None
            
        except Exception as e:
            logger.error(f"Error during template search: {e}")
            return None
    
    def save_search_history(self, file_path: str) -> None:
        """
        Save search history to a file.
        
        Args:
            file_path: Path to save the search history
        """
        try:
            history_data = [result.__dict__ for result in self.search_history]
            
            with open(file_path, 'w') as f:
                json.dump(history_data, f, indent=4)
                
            logger.info(f"Saved search history to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving search history: {e}", exc_info=True)
    
    def load_search_history(self, file_path: str) -> None:
        """
        Load search history from a file.
        
        Args:
            file_path: Path to load the search history from
        """
        try:
            with open(file_path, 'r') as f:
                history_data = json.load(f)
                
            self.search_history = [SearchResult(**data) for data in history_data]
            
            logger.info(f"Loaded search history from {file_path} ({len(self.search_history)} entries)")
            
        except Exception as e:
            logger.error(f"Error loading search history: {e}", exc_info=True)
    
    def clear_search_history(self) -> None:
        """Clear search history."""
        self.search_history = []
        self.visited_positions = set()
        logger.info("Cleared search history")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the search history.
        
        Returns:
            Dictionary with search statistics
        """
        if not self.search_history:
            return {
                'total_searches': 0,
                'successful_searches': 0,
                'success_rate': 0.0,
                'avg_positions_checked': 0,
                'avg_search_time': 0.0,
                'templates_found': {}
            }
            
        # Calculate statistics
        total_searches = len(self.search_history)
        successful_searches = sum(1 for result in self.search_history if result.success)
        success_rate = successful_searches / total_searches if total_searches > 0 else 0.0
        
        avg_positions_checked = sum(result.positions_checked for result in self.search_history) / total_searches
        avg_search_time = sum(result.search_time for result in self.search_history) / total_searches
        
        # Count templates found
        templates_found = {}
        for result in self.search_history:
            if result.success and result.template_name:
                templates_found[result.template_name] = templates_found.get(result.template_name, 0) + 1
                
        return {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': success_rate,
            'avg_positions_checked': avg_positions_checked,
            'avg_search_time': avg_search_time,
            'templates_found': templates_found
        }
    
    def configure(
        self,
        templates: List[str],
        min_confidence: float,
        save_screenshots: bool,
        grid_size: Tuple[int, int],
        start_pos: GameWorldPosition,
        start_cell: Tuple[int, int],
        drag_distances: Tuple[float, float]
    ) -> None:
        """Configure the search parameters.
        
        Args:
            templates: List of template names to search for
            min_confidence: Minimum confidence threshold for matches
            save_screenshots: Whether to save screenshots of matches
            grid_size: Size of the search grid (width, height)
            start_pos: Starting position in game world coordinates
            start_cell: Starting cell coordinates (x, y) in the grid
            drag_distances: Distance covered by each drag (east, south) in game units
        """
        self.templates = templates
        self.min_confidence = min_confidence
        self.save_screenshots = save_screenshots
        self.grid_size = grid_size
        self.start_pos = start_pos
        self.start_cell = start_cell
        self.drag_distances = drag_distances
        self.total_cells = grid_size[0] * grid_size[1]
        self.positions_checked = 0
        self.matches = []
        self.current_position = None
        self.stop_requested = False
        self.is_searching = False
        
        logger.info(f"Search configured with parameters: templates={templates}, "
                   f"min_confidence={min_confidence}, save_screenshots={save_screenshots}, "
                   f"grid_size={grid_size}, start_pos={start_pos}, start_cell={start_cell}, "
                   f"drag_distances={drag_distances}")
        
    def get_game_position(self, x: int, y: int) -> Optional[GameWorldPosition]:
        """
        Calculate game world position from grid coordinates.
        
        Args:
            x: Grid X coordinate
            y: Grid Y coordinate
            
        Returns:
            GameWorldPosition: Position in game world coordinates
        """
        try:
            # Get current position
            current_pos = self.start_pos
            if not current_pos:
                logger.error("No start position set")
                return None
                
            # Get drag distances from direction system
            if not self.game_coordinator.direction_system:
                logger.error("No direction system available")
                return None
                
            east_drag_dist, south_drag_dist = self.game_coordinator.direction_system.get_drag_distances()
            if not east_drag_dist or not south_drag_dist:
                logger.error("Invalid drag distances")
                return None
                
            # Calculate target position
            target_x = (current_pos.x + (x * east_drag_dist)) % 1000
            target_y = (current_pos.y + (y * south_drag_dist)) % 1000
            
            # Create new position with same kingdom but updated coordinates
            return GameWorldPosition(
                k=current_pos.k,
                x=target_x,
                y=target_y
            )
            
        except Exception as e:
            logger.error(f"Error calculating game position: {e}")
            return None

    def start(self) -> None:
        """Start the search process from the configured start position."""
        try:
            if not self.templates:
                logger.error("No templates configured")
                return
                
            if not all(self.grid_size):
                logger.error("Invalid grid size")
                return
                
            if not all(self.drag_distances):
                logger.error("Invalid drag distances")
                return
                
            if not self.start_pos:
                logger.error("No start position configured")
                return
                
            if not self.start_cell:
                logger.error("No start cell configured")
                return
                
            logger.info(f"Starting search from cell {self.start_cell} at position {self.start_pos}")
            
            # Initialize search state
            self.is_searching = True
            self.stop_requested = False
            self.current_position = self.start_cell
            
            # Start from configured cell
            current_x, current_y = self.start_cell
            
            while current_y < self.grid_size[1] and not self.stop_requested:
                while current_x < self.grid_size[0] and not self.stop_requested:
                    try:
                        # Get game world position for current cell
                        game_pos = self.get_game_position(current_x, current_y)
                        if not game_pos:
                            logger.error(f"Could not get game position for cell ({current_x}, {current_y})")
                            continue
                            
                        # Move to position
                        if not self._move_to_position(game_pos.x, game_pos.y):
                            logger.error(f"Failed to move to position {game_pos}")
                            continue
                            
                        # Search at current position
                        self._search_at_position(game_pos)
                        
                        # Update progress
                        self.positions_checked += 1
                        self.current_position = (current_x, current_y)
                        
                    except Exception as e:
                        logger.error(f"Error searching at position ({current_x}, {current_y}): {e}")
                        
                    current_x += 1
                    
                current_x = 0
                current_y += 1
                
            self.is_searching = False
            logger.info("Search completed")
            
        except Exception as e:
            self.is_searching = False
            logger.error(f"Error during search: {e}", exc_info=True)

    def _perform_drag(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> bool:
        """
        Perform a drag operation between two points.
        
        Args:
            start_pos: Start position (x, y) in screen coordinates
            end_pos: End position (x, y) in screen coordinates
            
        Returns:
            bool: True if drag was successful
        """
        try:
            # Perform drag
            if not self.game_actions.drag_mouse(
                start_pos[0], start_pos[1],
                end_pos[0], end_pos[1],
                relative_to_window=True,
                duration=0.5
            ):
                logger.error("Failed to perform drag")
                return False
                
            # Update game coordinator's position
            self.game_coordinator.update_position_after_drag(
                start_pos[0], start_pos[1],
                end_pos[0], end_pos[1]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error performing drag: {e}")
            return False

    def _search_at_position(self, game_pos: GameWorldPosition) -> None:
        """Search for templates at the current position.
        
        Args:
            game_pos: Current game world position to search at
        """
        try:
            # Check for templates
            result = self._check_for_templates(self.templates)
            if result:
                result.game_position = game_pos
                self.matches.append(result)
                logger.info(f"Found match at position {game_pos}: {result}")
                
        except Exception as e:
            logger.error(f"Error searching at position {game_pos}: {e}") 