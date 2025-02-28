"""
Game World Search

This module provides intelligent search strategies for finding templates in the game world.
It combines the search patterns with the game world coordinator to efficiently search for templates.
"""

from typing import List, Tuple, Dict, Optional, Any, Set, Callable
import logging
import time
import json
from pathlib import Path
import numpy as np
import cv2

from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher, GroupedMatch
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition
from scout.automation.search_patterns import (
    spiral_pattern, grid_pattern, 
    expanding_circles_pattern, quadtree_pattern
)

logger = logging.getLogger(__name__)

class SearchResult:
    """
    Result of a template search operation.
    
    Attributes:
        success: Whether the search was successful
        template_name: Name of the template that was found
        screen_position: Position on screen where the template was found
        game_position: Position in game world coordinates
        confidence: Confidence level of the match
        search_time: Time taken for the search in seconds
        positions_checked: Number of positions checked during the search
        screenshot_path: Path to the screenshot where the template was found (if saved)
    """
    
    def __init__(self, success: bool = False):
        """Initialize a search result."""
        self.success = success
        self.template_name: Optional[str] = None
        self.screen_position: Optional[Tuple[int, int]] = None
        self.game_position: Optional[GameWorldPosition] = None
        self.confidence: float = 0.0
        self.search_time: float = 0.0
        self.positions_checked: int = 0
        self.screenshot_path: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            'success': self.success,
            'template_name': self.template_name,
            'confidence': self.confidence,
            'search_time': self.search_time,
            'positions_checked': self.positions_checked,
            'screenshot_path': self.screenshot_path
        }
        
        if self.screen_position:
            result['screen_position'] = {
                'x': self.screen_position[0],
                'y': self.screen_position[1]
            }
            
        if self.game_position:
            result['game_position'] = {
                'x': self.game_position.x,
                'y': self.game_position.y,
                'k': self.game_position.k
            }
            
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create from dictionary."""
        result = cls(data.get('success', False))
        result.template_name = data.get('template_name')
        result.confidence = data.get('confidence', 0.0)
        result.search_time = data.get('search_time', 0.0)
        result.positions_checked = data.get('positions_checked', 0)
        result.screenshot_path = data.get('screenshot_path')
        
        if 'screen_position' in data:
            result.screen_position = (
                data['screen_position'].get('x', 0),
                data['screen_position'].get('y', 0)
            )
            
        if 'game_position' in data:
            result.game_position = GameWorldPosition(
                data['game_position'].get('x', 0),
                data['game_position'].get('y', 0),
                data['game_position'].get('k', 0)
            )
            
        return result
        
    def __str__(self) -> str:
        """String representation of the search result."""
        if not self.success:
            return "SearchResult(success=False)"
            
        return (f"SearchResult(success=True, template={self.template_name}, "
                f"position={self.game_position}, confidence={self.confidence:.2f})")


class GameWorldSearch:
    """
    Intelligent search strategies for finding templates in the game world.
    
    This class combines the search patterns with the game world coordinator
    to efficiently search for templates in the game world.
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
        
        # Initialize
        if self.save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def search_templates(
        self, 
        template_names: List[str],
        start_position: Optional[GameWorldPosition] = None,
        pattern: str = 'spiral',
        pattern_params: Optional[Dict[str, Any]] = None,
        max_positions: Optional[int] = None,
        min_confidence: Optional[float] = None,
        callback: Optional[Callable[[SearchResult], None]] = None
    ) -> SearchResult:
        """
        Search for templates using a specified pattern.
        
        Args:
            template_names: List of template names to search for
            start_position: Starting position for the search (default: current position)
            pattern: Search pattern to use ('spiral', 'grid', 'circles', 'quadtree')
            pattern_params: Parameters for the search pattern
            max_positions: Maximum number of positions to check
            min_confidence: Minimum confidence level for template matches
            callback: Optional callback function to call after each position check
            
        Returns:
            SearchResult object with the search results
        """
        # Initialize result
        result = SearchResult()
        
        # Set search parameters
        if max_positions is not None:
            self.max_positions = max_positions
        if min_confidence is not None:
            self.min_confidence = min_confidence
            
        # Use current position if no start position is provided
        if start_position is None:
            # Update current position from OCR
            self.game_coordinator.update_current_position_from_ocr()
            start_position = self.game_coordinator.current_position
            
        # Initialize pattern parameters
        if pattern_params is None:
            pattern_params = {}
            
        # Set default pattern parameters based on pattern type
        if pattern == 'spiral':
            pattern_params.setdefault('center_x', start_position.x)
            pattern_params.setdefault('center_y', start_position.y)
            pattern_params.setdefault('max_radius', 1000)
            pattern_params.setdefault('step_size', 100)
        elif pattern == 'grid':
            pattern_params.setdefault('start_x', start_position.x - 500)
            pattern_params.setdefault('start_y', start_position.y - 500)
            pattern_params.setdefault('width', 1000)
            pattern_params.setdefault('height', 1000)
            pattern_params.setdefault('step_size', 100)
            pattern_params.setdefault('snake', True)
        elif pattern == 'circles':
            pattern_params.setdefault('center_x', start_position.x)
            pattern_params.setdefault('center_y', start_position.y)
            pattern_params.setdefault('max_radius', 1000)
            pattern_params.setdefault('step_size', 100)
            pattern_params.setdefault('points_per_circle', 8)
        elif pattern == 'quadtree':
            pattern_params.setdefault('start_x', start_position.x - 500)
            pattern_params.setdefault('start_y', start_position.y - 500)
            pattern_params.setdefault('width', 1000)
            pattern_params.setdefault('height', 1000)
            pattern_params.setdefault('min_cell_size', 100)
        else:
            logger.warning(f"Unknown pattern: {pattern}, using spiral")
            pattern = 'spiral'
            pattern_params = {
                'center_x': start_position.x,
                'center_y': start_position.y,
                'max_radius': 1000,
                'step_size': 100
            }
            
        # Generate pattern
        if pattern == 'spiral':
            positions = spiral_pattern(**pattern_params)
        elif pattern == 'grid':
            positions = grid_pattern(**pattern_params)
        elif pattern == 'circles':
            positions = expanding_circles_pattern(**pattern_params)
        elif pattern == 'quadtree':
            positions = quadtree_pattern(**pattern_params)
        else:
            # This should never happen due to the check above
            positions = spiral_pattern(**pattern_params)
            
        # Start search
        start_time = time.time()
        positions_checked = 0
        
        logger.info(f"Starting search for templates: {template_names} using {pattern} pattern")
        
        # Check each position in the pattern
        for game_x, game_y in positions:
            # Check if we've reached the maximum number of positions
            if positions_checked >= self.max_positions:
                logger.info(f"Reached maximum number of positions ({self.max_positions})")
                break
                
            # Check if we've already visited this position (within radius)
            position_key = (game_x // self.position_visit_radius, 
                           game_y // self.position_visit_radius)
            if position_key in self.visited_positions:
                continue
                
            # Mark position as visited
            self.visited_positions.add(position_key)
            
            # Check if the position is on screen
            if self.game_coordinator.is_position_on_screen(game_x, game_y):
                # Position is on screen, check for templates
                match_result = self._check_for_templates(template_names)
                positions_checked += 1
                
                if match_result.success:
                    # Found a match, update result and return
                    result = match_result
                    result.search_time = time.time() - start_time
                    result.positions_checked = positions_checked
                    
                    # Add to search history
                    self.search_history.append(result)
                    
                    logger.info(f"Found template {result.template_name} at {result.game_position}")
                    
                    # Call callback if provided
                    if callback:
                        callback(result)
                        
                    return result
            else:
                # Position is not on screen, move to it
                self._move_to_position(game_x, game_y)
                
                # Check for templates after moving
                match_result = self._check_for_templates(template_names)
                positions_checked += 1
                
                if match_result.success:
                    # Found a match, update result and return
                    result = match_result
                    result.search_time = time.time() - start_time
                    result.positions_checked = positions_checked
                    
                    # Add to search history
                    self.search_history.append(result)
                    
                    logger.info(f"Found template {result.template_name} at {result.game_position}")
                    
                    # Call callback if provided
                    if callback:
                        callback(result)
                        
                    return result
                    
            # Call callback with progress update
            if callback:
                progress_result = SearchResult(False)
                progress_result.positions_checked = positions_checked
                progress_result.search_time = time.time() - start_time
                callback(progress_result)
                
        # If we get here, we didn't find any matches
        result.success = False
        result.search_time = time.time() - start_time
        result.positions_checked = positions_checked
        
        # Add to search history
        self.search_history.append(result)
        
        logger.info(f"Search completed, no matches found after checking {positions_checked} positions")
        
        # Call callback with final result
        if callback:
            callback(result)
            
        return result
    
    def _check_for_templates(self, template_names: List[str]) -> SearchResult:
        """
        Check for templates at the current position.
        
        Args:
            template_names: List of template names to check for
            
        Returns:
            SearchResult object with the search results
        """
        result = SearchResult()
        
        try:
            # Take a screenshot
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is None:
                logger.error("Failed to capture screenshot for template matching")
                return result
                
            # Always save screenshot for debugging purposes
            timestamp = int(time.time())
            debug_dir = Path('scout/debug_screenshots')
            debug_dir.mkdir(exist_ok=True, parents=True)
            debug_screenshot_path = str(debug_dir / f"search_debug_{timestamp}.png")
            cv2.imwrite(debug_screenshot_path, screenshot)
            
            # Save screenshot to search results directory if enabled
            screenshot_path = None
            if self.save_screenshots:
                screenshot_path = str(self.screenshot_dir / f"search_{timestamp}.png")
                cv2.imwrite(screenshot_path, screenshot)
            else:
                # Even if save_screenshots is disabled, we still want to have a path for the result
                screenshot_path = debug_screenshot_path
                
            # Find matches
            matches = self.template_matcher.find_matches(screenshot, template_names)
            
            # Check if we found any matches
            if matches:
                # Get the match with the highest confidence
                best_match = max(matches, key=lambda m: m.confidence)
                
                # Check if the confidence is high enough
                if best_match.confidence >= self.min_confidence:
                    # Update current position from OCR
                    self.game_coordinator.update_current_position_from_ocr()
                    
                    # Calculate screen position (center of match)
                    screen_x = best_match.bounds[0] + best_match.bounds[2] // 2
                    screen_y = best_match.bounds[1] + best_match.bounds[3] // 2
                    
                    # Convert to game world coordinates
                    game_position = self.game_coordinator.screen_to_game_coords(screen_x, screen_y)
                    
                    # Update result
                    result.success = True
                    result.template_name = best_match.template_name
                    result.screen_position = (screen_x, screen_y)
                    result.game_position = game_position
                    result.confidence = best_match.confidence
                    result.screenshot_path = screenshot_path
                    
                    logger.info(f"Found template {best_match.template_name} with confidence {best_match.confidence:.2f}")
            else:
                # Even if no matches were found, still set the screenshot path for debugging
                result.screenshot_path = screenshot_path
                    
            # Wait a bit to avoid overloading the system
            time.sleep(self.template_search_delay)
                
        except Exception as e:
            logger.error(f"Error checking for templates: {e}", exc_info=True)
            
        return result
    
    def _move_to_position(self, game_x: int, game_y: int) -> None:
        """
        Move the view to a specific game world position.
        
        Args:
            game_x: X coordinate in game world
            game_y: Y coordinate in game world
        """
        try:
            # Calculate drag vector
            start_x, start_y, end_x, end_y = self.game_coordinator.calculate_drag_vector(game_x, game_y)
            
            # Perform drag
            self.game_actions.drag_mouse(start_x, start_y, end_x, end_y)
            
            # Update position after drag
            self.game_coordinator.update_position_after_drag(start_x, start_y, end_x, end_y)
            
            # Wait for the view to settle
            time.sleep(self.drag_delay)
            
            # Update position from OCR for accuracy
            self.game_coordinator.update_current_position_from_ocr()
            
            logger.debug(f"Moved to position ({game_x}, {game_y})")
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}", exc_info=True)
    
    def save_search_history(self, file_path: str) -> None:
        """
        Save search history to a file.
        
        Args:
            file_path: Path to save the search history
        """
        try:
            history_data = [result.to_dict() for result in self.search_history]
            
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
                
            self.search_history = [SearchResult.from_dict(data) for data in history_data]
            
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