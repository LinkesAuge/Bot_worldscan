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
        Move to a target position using drag operations.
        
        Args:
            target_x: Target X coordinate in game world units
            target_y: Target Y coordinate in game world units
            
        Returns:
            bool: True if movement was successful, False otherwise
        """
        try:
            # Calculate drag vector
            drag_x, drag_y = self.game_coordinator.calculate_drag_vector(target_x, target_y)
            
            # Get window center for drag operation
            window_pos = self.game_coordinator.window_manager.get_window_position()
            if not window_pos:
                logger.error("Failed to get window position")
                return False
                
            center_x = window_pos[0] + window_pos[2] // 2
            center_y = window_pos[1] + window_pos[3] // 2
            
            # Perform drag operation
            self.game_actions.drag_mouse(
                center_x, center_y,
                center_x + drag_x, center_y + drag_y
            )
            
            # Wait for view to settle
            time.sleep(0.5)
            
            # Update position from OCR
            if not self.game_coordinator.update_current_position_from_ocr():
                logger.warning("Failed to update position after movement")
                return False
                
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
        drag_distances: Tuple[int, int]
    ) -> None:
        """
        Configure the search parameters.
        
        Args:
            templates: List of template names to search for
            min_confidence: Minimum confidence threshold for matches
            save_screenshots: Whether to save screenshots of matches
            grid_size: (width, height) of the search grid in drag movements
            start_pos: Starting game world position
            drag_distances: (east_distance, south_distance) in game units
        """
        self.templates = templates
        self.min_confidence = min_confidence
        self.save_screenshots = save_screenshots
        self.grid_size = grid_size
        self.start_pos = start_pos
        self.drag_distances = drag_distances
        self.total_cells = grid_size[0] * grid_size[1]
        self.positions_checked = 0
        self.matches.clear()
        self.current_position = (0, 0)
        
    def start(self):
        """
        Start the search process.
        
        This method begins the search using the configured parameters.
        It searches through the grid systematically, checking for templates
        at each position.
        """
        try:
            if not self.templates or not self.start_pos or not self.drag_distances:
                logger.error("Search not properly configured")
                return
                
            logger.info(f"Starting search with grid size {self.grid_size}")
            logger.info(f"Starting position: {self.start_pos}")
            logger.info(f"Drag distances: {self.drag_distances}")
            
            self.positions_checked = 0
            self.matches.clear()
            self.current_position = (0, 0)
            
            # Move to start position if needed
            if not self.game_coordinator.is_position_on_screen(
                self.start_pos.x, self.start_pos.y
            ):
                if not self._move_to_position(self.start_pos.x, self.start_pos.y):
                    logger.error("Failed to move to start position")
                    return
                    
            # Search through grid
            for y in range(self.grid_size[1]):
                for x in range(self.grid_size[0]):
                    # Update current position
                    self.current_position = (x, y)
                    
                    # Calculate target game position
                    target_pos = self.get_game_position(x, y)
                    if not target_pos:
                        continue
                        
                    # Move to position if not on screen
                    if not self.game_coordinator.is_position_on_screen(
                        target_pos.x, target_pos.y
                    ):
                        if not self._move_to_position(target_pos.x, target_pos.y):
                            logger.warning(f"Failed to move to position ({x}, {y})")
                            continue
                            
                    # Check for templates
                    result = self._check_for_templates(self.templates)
                    if result:
                        self.matches.append(result)
                        
                    # Update progress
                    self.positions_checked += 1
                    
                    # Check if search should stop
                    if hasattr(self, 'stop_requested') and self.stop_requested:
                        logger.info("Search stopped by user")
                        return
                        
                    # Wait between moves
                    time.sleep(self.template_search_delay)
                    
            logger.info(f"Search complete. Checked {self.positions_checked} positions, "
                       f"found {len(self.matches)} matches")
                       
        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            
        finally:
            # Ensure search is marked as complete
            self.is_searching = False 