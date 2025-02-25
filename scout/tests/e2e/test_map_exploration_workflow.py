"""
Map Exploration End-to-End Test

This module contains comprehensive end-to-end tests for the map exploration
workflow in the Total Battle game. It simulates a complete workflow where the
application navigates through the world map, discovers entities, and maintains
a database of discovered locations.
"""

import unittest
import os
import tempfile
import shutil
import time
import logging
import cv2
import numpy as np
from unittest.mock import MagicMock, patch

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import Coordinates, MapEntity
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import TaskStatus, CompositeTask
from scout.core.automation.tasks.basic_tasks import ClickTask, WaitTask, DetectTask, DragTask
from scout.core.automation.tasks.game_tasks import NavigateToCoordinatesTask, ScanAreaTask

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockActionsService:
    """Mock implementation of an actions service for testing."""
    
    def __init__(self):
        self.actions_log = []
    
    def click_at(self, x, y, relative_to_window=True, button='left', clicks=1):
        """Log click actions."""
        self.actions_log.append(('click', x, y, relative_to_window, button, clicks))
        logger.debug(f"Clicked at ({x}, {y})")
        return True
    
    def drag_mouse(self, start_x, start_y, end_x, end_y, relative_to_window=True, duration=0.5):
        """Log drag actions."""
        self.actions_log.append(('drag', start_x, start_y, end_x, end_y, relative_to_window, duration))
        logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return True
    
    def input_text(self, text):
        """Log text input actions."""
        self.actions_log.append(('input_text', text))
        logger.debug(f"Typed text: '{text}'")
        return True
    
    def get_actions(self):
        """Get all logged actions."""
        return self.actions_log
    
    def clear_log(self):
        """Clear action log."""
        self.actions_log = []


class MapExplorationWorkflowTest(unittest.TestCase):
    """
    End-to-end test for the map exploration workflow.
    
    This test simulates the complete process of:
    1. Navigating to different regions of the game map
    2. Scanning each region for entities (resources, enemies, landmarks)
    3. Recording discovered entities in the game state
    4. Creating a map of explored areas
    
    It verifies that all components of the system work together to
    automate a complete real-world scenario.
    """
    
    def setUp(self):
        """Set up test environment."""
        # Create shared event bus
        self.event_bus = EventBus()
        
        # Create temporary directory for templates and state
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        self.state_dir = os.path.join(self.temp_dir, 'state')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create test template images
        self._create_test_templates()
        
        # Create test game world map
        self.world_map = self._create_world_map()
        
        # Initialize core services
        self._init_services()
        
        # Set up initial game state for testing
        self._setup_initial_game_state()
        
        # Configure exploration path
        self.exploration_coordinates = [
            Coordinates(1, 100, 100),  # Starting position
            Coordinates(1, 150, 100),  # East
            Coordinates(1, 150, 150),  # South
            Coordinates(1, 100, 150),  # West
            Coordinates(1, 50, 150),   # Further west
            Coordinates(1, 50, 100),   # North
            Coordinates(1, 50, 50),    # Further north
            Coordinates(1, 100, 50),   # East
            Coordinates(1, 150, 50)    # Further east
        ]
    
    def tearDown(self):
        """Clean up after test."""
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_templates(self):
        """Create test template images for entity detection."""
        # Create entity templates
        entity_types = [
            ("gold_mine", (0, 215, 255)),      # Gold (BGR)
            ("wood_resource", (32, 80, 140)),  # Wood (BGR)
            ("stone_quarry", (120, 120, 120)), # Stone (BGR)
            ("enemy_camp", (30, 30, 200)),     # Enemy (red)
            ("friendly_city", (50, 200, 50)),  # Friendly (green)
            ("neutral_village", (200, 200, 50)), # Neutral (cyan)
            ("treasure", (0, 165, 255))        # Treasure (golden)
        ]
        
        for name, color in entity_types:
            # Create entity template
            entity_path = os.path.join(self.templates_dir, f'{name}.png')
            entity_img = np.zeros((40, 40, 3), dtype=np.uint8)
            entity_img[:, :] = color
            
            # Add some distinguishing features
            if "mine" in name or "resource" in name or "quarry" in name:
                # Resource nodes have circular shape
                cv2.circle(entity_img, (20, 20), 15, (np.array(color) * 0.7).astype(np.uint8), -1)
            elif "camp" in name:
                # Enemy camps have triangular shape
                pts = np.array([[20, 5], [5, 35], [35, 35]], np.int32)
                cv2.fillPoly(entity_img, [pts], (np.array(color) * 0.7).astype(np.uint8))
            elif "city" in name or "village" in name:
                # Settlements have square with roof
                cv2.rectangle(entity_img, (10, 15), (30, 35), (np.array(color) * 0.7).astype(np.uint8), -1)
                pts = np.array([[10, 15], [20, 5], [30, 15]], np.int32)
                cv2.fillPoly(entity_img, [pts], (np.array(color) * 0.7).astype(np.uint8))
            elif "treasure" in name:
                # Treasure chests are rectangles
                cv2.rectangle(entity_img, (10, 15), (30, 35), (np.array(color) * 0.7).astype(np.uint8), -1)
                
            cv2.imwrite(entity_path, entity_img)
        
        # Create coordinate input field template
        coord_input_path = os.path.join(self.templates_dir, 'coordinate_input.png')
        coord_input_img = np.zeros((30, 100, 3), dtype=np.uint8)
        coord_input_img[:, :] = (200, 200, 200)  # Gray background
        cv2.rectangle(coord_input_img, (0, 0), (99, 29), (150, 150, 150), 1)
        cv2.imwrite(coord_input_path, coord_input_img)
    
    def _create_world_map(self):
        """Create a virtual game world map with various entities."""
        # World map is a dictionary where keys are coordinate tuples and values are entities
        world_map = {}
        
        # Add various entities to the map
        entities = [
            # Resources
            {"type": "gold_mine", "coords": Coordinates(1, 120, 110), "level": 3},
            {"type": "gold_mine", "coords": Coordinates(1, 160, 140), "level": 5},
            {"type": "wood_resource", "coords": Coordinates(1, 90, 130), "level": 4},
            {"type": "wood_resource", "coords": Coordinates(1, 135, 65), "level": 6},
            {"type": "stone_quarry", "coords": Coordinates(1, 45, 85), "level": 2},
            {"type": "stone_quarry", "coords": Coordinates(1, 70, 145), "level": 7},
            
            # Settlements
            {"type": "enemy_camp", "coords": Coordinates(1, 110, 160), "level": 8},
            {"type": "enemy_camp", "coords": Coordinates(1, 165, 95), "level": 6},
            {"type": "friendly_city", "coords": Coordinates(1, 75, 60), "level": 10},
            {"type": "neutral_village", "coords": Coordinates(1, 40, 120), "level": 5},
            
            # Treasures
            {"type": "treasure", "coords": Coordinates(1, 130, 90), "level": 2},
            {"type": "treasure", "coords": Coordinates(1, 55, 140), "level": 4}
        ]
        
        # Add entities to world map
        for entity in entities:
            coords = entity["coords"]
            key = (coords.kingdom, coords.x, coords.y)
            world_map[key] = entity
            
        return world_map
    
    def _init_services(self):
        """Initialize all services required for testing."""
        # Create window service (mocked)
        self.window_service = WindowService(self.event_bus)
        self.window_service.find_window = MagicMock(return_value=True)
        self.window_service.get_window_position = MagicMock(return_value=(0, 0, 800, 600))
        
        # Create world view based on current position
        self.current_view_coords = Coordinates(1, 100, 100)
        self._update_map_view()
        
        # Create detection service with template strategy
        self.detection_service = DetectionService(self.event_bus, self.window_service)
        template_strategy = TemplateMatchingStrategy(templates_dir=self.templates_dir)
        self.detection_service.register_strategy('template', template_strategy)
        
        # Create game service
        self.game_service = GameService(
            self.event_bus,
            self.detection_service,
            state_file_path=os.path.join(self.state_dir, 'game_state.json')
        )
        
        # Create actions service (mocked)
        self.actions_service = MockActionsService()
        
        # Create automation service
        self.automation_service = AutomationService(self.event_bus)
        
        # Set up execution context
        self.automation_service.set_execution_context({
            'window_service': self.window_service,
            'detection_service': self.detection_service,
            'game_service': self.game_service,
            'actions_service': self.actions_service
        })
        
        # Hook navigation to update the view
        self._hook_navigation()
    
    def _hook_navigation(self):
        """
        Hook into navigation actions to update the game view.
        
        When navigation tasks are executed, we need to update our simulated 
        game view to match the new coordinates.
        """
        # Store original methods
        self._original_click = self.actions_service.click_at
        self._original_input = self.actions_service.input_text
        
        # Override click method to check for coordinate input field click
        def mock_click(x, y, relative_to_window=True, button='left', clicks=1):
            result = self._original_click(x, y, relative_to_window, button, clicks)
            
            # Check if clicking coordinate input field (upper region of screen)
            if 350 <= x <= 450 and 10 <= y <= 40:
                # Mark that we're clicking the coordinate field (will be used by input_text)
                self.actions_service._clicking_coord_field = True
                
            return result
            
        # Override input text to check for coordinate navigation
        def mock_input(text):
            result = self._original_input(text)
            
            # If we previously clicked the coordinate field, parse coordinates
            if hasattr(self.actions_service, '_clicking_coord_field') and self.actions_service._clicking_coord_field:
                try:
                    # Parse the coordinate text (expected format: "x,y")
                    parts = text.split(',')
                    if len(parts) == 2:
                        x, y = int(parts[0]), int(parts[1])
                        # Update current view to the new coordinates
                        self.current_view_coords = Coordinates(1, x, y)
                        self._update_map_view()
                        logger.info(f"Navigated to coordinates: K1 ({x}, {y})")
                except ValueError:
                    logger.warning(f"Failed to parse coordinates from text: {text}")
                    
                # Reset the flag
                self.actions_service._clicking_coord_field = False
                
            return result
            
        # Apply our mock functions
        self.actions_service.click_at = mock_click
        self.actions_service.input_text = mock_input
    
    def _update_map_view(self):
        """
        Update the simulated game view based on current coordinates.
        
        This creates a screenshot showing entities that would be visible
        at the current map coordinates.
        """
        # Create base map view image (800x600)
        map_view = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add background (terrain pattern)
        for i in range(0, 800, 20):
            for j in range(0, 600, 20):
                color_variation = ((i + j) % 10) - 5
                map_view[j:j+20, i:i+20] = [80 + color_variation, 120 + color_variation, 80 + color_variation]
        
        # Add coordinate display at top left
        cv2.putText(
            map_view, 
            f"K1 ({self.current_view_coords.x}, {self.current_view_coords.y})", 
            (20, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (255, 255, 255), 
            2
        )
        
        # Add coordinate input field at top center
        cv2.rectangle(map_view, (350, 10), (450, 40), (200, 200, 200), -1)
        cv2.rectangle(map_view, (350, 10), (450, 40), (150, 150, 150), 1)
        cv2.putText(
            map_view, 
            "Go to", 
            (290, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (255, 255, 255), 
            1
        )
        
        # Calculate view boundaries (what's visible on screen)
        # Assume each map view shows a 150x120 unit area of the game world
        view_min_x = self.current_view_coords.x - 75
        view_max_x = self.current_view_coords.x + 75
        view_min_y = self.current_view_coords.y - 60
        view_max_y = self.current_view_coords.y + 60
        
        # Add visible entities to the view
        for coord_key, entity in self.world_map.items():
            kingdom, x, y = coord_key
            
            # Skip entities from different kingdoms
            if kingdom != self.current_view_coords.kingdom:
                continue
                
            # Check if entity is in view
            if (view_min_x <= x <= view_max_x and 
                view_min_y <= y <= view_max_y):
                
                # Calculate screen position based on game coordinates
                screen_x = 400 + (x - self.current_view_coords.x) * 4
                screen_y = 300 + (y - self.current_view_coords.y) * 4
                
                # Add entity icon based on type
                entity_type = entity["type"]
                level = entity["level"]
                
                if "gold_mine" in entity_type:
                    color = (0, 215, 255)  # Gold (BGR)
                    shape = "circle"
                elif "wood_resource" in entity_type:
                    color = (32, 80, 140)  # Wood (BGR)
                    shape = "circle"
                elif "stone_quarry" in entity_type:
                    color = (120, 120, 120)  # Stone (BGR)
                    shape = "circle"
                elif "enemy_camp" in entity_type:
                    color = (30, 30, 200)  # Enemy (red)
                    shape = "triangle"
                elif "friendly_city" in entity_type:
                    color = (50, 200, 50)  # Friendly (green)
                    shape = "house"
                elif "neutral_village" in entity_type:
                    color = (200, 200, 50)  # Neutral (cyan)
                    shape = "house"
                elif "treasure" in entity_type:
                    color = (0, 165, 255)  # Treasure (golden)
                    shape = "rectangle"
                else:
                    color = (200, 200, 200)  # Unknown (gray)
                    shape = "circle"
                
                # Draw entity shape
                if shape == "circle":
                    cv2.circle(map_view, (int(screen_x), int(screen_y)), 15, color, -1)
                elif shape == "triangle":
                    pts = np.array([
                        [int(screen_x), int(screen_y - 15)],
                        [int(screen_x - 15), int(screen_y + 15)],
                        [int(screen_x + 15), int(screen_y + 15)]
                    ], np.int32)
                    cv2.fillPoly(map_view, [pts], color)
                elif shape == "house":
                    cv2.rectangle(
                        map_view,
                        (int(screen_x - 10), int(screen_y - 5)),
                        (int(screen_x + 10), int(screen_y + 15)),
                        color,
                        -1
                    )
                    pts = np.array([
                        [int(screen_x - 10), int(screen_y - 5)],
                        [int(screen_x), int(screen_y - 15)],
                        [int(screen_x + 10), int(screen_y - 5)]
                    ], np.int32)
                    cv2.fillPoly(map_view, [pts], color)
                elif shape == "rectangle":
                    cv2.rectangle(
                        map_view,
                        (int(screen_x - 10), int(screen_y - 10)),
                        (int(screen_x + 10), int(screen_y + 10)),
                        color,
                        -1
                    )
                
                # Add level indicator
                cv2.putText(
                    map_view,
                    f"{level}",
                    (int(screen_x - 5), int(screen_y + 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )
        
        # Update the window service to return this view
        self.window_service.capture_screenshot = MagicMock(return_value=map_view)
    
    def _setup_initial_game_state(self):
        """Set up initial game state for testing."""
        # Set current position
        self.game_service.state.current_position = self.current_view_coords
        
        # Initialize the map entity tracking
        self.game_service.state.known_entities = {}
        
        # Add explored areas (none initially)
        self.game_service.state.explored_areas = set()
        
        # Save state
        self.game_service.save_state()
    
    def test_map_exploration_workflow(self):
        """
        Test complete map exploration workflow.
        
        This tests the following workflow:
        1. Navigate to a series of coordinates
        2. At each location, scan for entities
        3. Record discovered entities in the game state
        4. Track explored areas
        5. Generate a map of discovered entities
        """
        # Store explored areas
        explored_areas = set()
        
        # Record initial state
        initial_known_entities_count = len(self.game_service.state.known_entities)
        logger.info(f"Starting exploration with {initial_known_entities_count} known entities")
        
        # Create composite task for the entire exploration
        exploration_task = CompositeTask("map_exploration")
        
        # For each coordinate in our exploration path
        for i, coords in enumerate(self.exploration_coordinates):
            logger.info(f"Step {i+1}: Exploring coordinates K{coords.kingdom} ({coords.x}, {coords.y})")
            
            # a. Navigate to the coordinates
            navigate_task = NavigateToCoordinatesTask(
                f"navigate_to_{i}",
                coordinates=coords,
                input_field_position=(400, 25)  # Coordinate input field
            )
            exploration_task.add_task(navigate_task)
            
            # Add wait after navigation
            wait_task1 = WaitTask(f"wait_after_nav_{i}", 0.5)
            exploration_task.add_task(wait_task1)
            
            # b. Scan the area for entities
            scan_task = ScanAreaTask(
                f"scan_area_{i}",
                strategy="template",
                area_size=5,  # Small area for testing
                object_templates=[
                    "gold_mine", "wood_resource", "stone_quarry",
                    "enemy_camp", "friendly_city", "neutral_village",
                    "treasure"
                ],
                confidence=0.7
            )
            exploration_task.add_task(scan_task)
            
            # Add callback to track explored area
            def create_exploration_callback(coord):
                def callback(task):
                    if task.status == TaskStatus.COMPLETED:
                        # Mark this area as explored
                        explored_area = (coord.kingdom, coord.x, coord.y)
                        explored_areas.add(explored_area)
                        self.game_service.state.explored_areas.add(explored_area)
                        
                        # Update the game state with discovered entities
                        entities_count = len(self.game_service.state.known_entities)
                        logger.info(f"Explored area K{coord.kingdom} ({coord.x}, {coord.y}) - "
                                   f"Now tracking {entities_count} entities")
                return callback
                
            scan_task.add_completion_callback(create_exploration_callback(coords))
            
            # Add wait after scanning
            wait_task2 = WaitTask(f"wait_after_scan_{i}", 0.5)
            exploration_task.add_task(wait_task2)
        
        # Execute the exploration plan
        self.automation_service.execute_task_synchronously(exploration_task)
        
        # Verify exploration task completed successfully
        self.assertEqual(exploration_task.status, TaskStatus.COMPLETED)
        
        # Verify we have explored all planned areas
        self.assertEqual(len(explored_areas), len(self.exploration_coordinates))
        
        # Verify entities were discovered
        final_known_entities_count = len(self.game_service.state.known_entities)
        logger.info(f"Exploration complete! Discovered {final_known_entities_count - initial_known_entities_count} new entities")
        self.assertGreater(final_known_entities_count, initial_known_entities_count)
        
        # Verify that the discovered entities match entities in our simulated world
        for entity_id, entity in self.game_service.state.known_entities.items():
            # Convert to the format used in our world map
            coords = entity.coordinates
            world_key = (coords.kingdom, coords.x, coords.y)
            
            # Check that this entity exists in our world map
            if world_key in self.world_map:
                world_entity = self.world_map[world_key]
                self.assertEqual(entity.entity_type, world_entity["type"])
                self.assertEqual(entity.level, world_entity["level"])
                logger.info(f"Verified entity: {entity.entity_type} at {coords}")
        
        # Verify navigation actions were performed
        actions = self.actions_service.get_actions()
        
        # Count navigation-related actions
        click_actions = [a for a in actions if a[0] == 'click']
        input_actions = [a for a in actions if a[0] == 'input_text']
        
        # We should have at least one navigation per coordinate (click + input)
        self.assertGreaterEqual(len(click_actions), len(self.exploration_coordinates))
        self.assertGreaterEqual(len(input_actions), len(self.exploration_coordinates))
        
        # Generate exploration stats
        resources_found = 0
        settlements_found = 0
        treasures_found = 0
        
        for entity in self.game_service.state.known_entities.values():
            if any(res_type in entity.entity_type for res_type in ['mine', 'resource', 'quarry']):
                resources_found += 1
            elif any(settle_type in entity.entity_type for settle_type in ['camp', 'city', 'village']):
                settlements_found += 1
            elif 'treasure' in entity.entity_type:
                treasures_found += 1
                
        logger.info(f"Exploration Summary:")
        logger.info(f"- Resources found: {resources_found}")
        logger.info(f"- Settlements found: {settlements_found}")
        logger.info(f"- Treasures found: {treasures_found}")
        logger.info(f"- Total areas explored: {len(explored_areas)}")


if __name__ == '__main__':
    unittest.main() 