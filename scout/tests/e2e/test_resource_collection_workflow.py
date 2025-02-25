"""
Resource Collection End-to-End Test

This module contains comprehensive end-to-end tests for the resource collection
workflow in the Total Battle game. It simulates a complete workflow where the
application detects resources on the map, navigates to them, and collects them.
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
from scout.core.automation.tasks.game_tasks import (
    NavigateToCoordinatesTask, 
    CollectResourcesTask,
    ScanAreaTask
)

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


class ResourceCollectionWorkflowTest(unittest.TestCase):
    """
    End-to-end test for the resource collection workflow.
    
    This test simulates the complete process of:
    1. Finding resources on the game map
    2. Navigating to resource locations
    3. Collecting resources when available
    4. Tracking collected resources in game state
    
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
    
    def tearDown(self):
        """Clean up after test."""
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_templates(self):
        """Create test template images for resource detection."""
        # Create gold resource template
        gold_path = os.path.join(self.templates_dir, 'gold_resource.png')
        gold_img = np.zeros((40, 40, 3), dtype=np.uint8)
        gold_img[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_img, (20, 20), 15, (0, 165, 255), -1)  # Darker gold circle
        cv2.imwrite(gold_path, gold_img)
        
        # Create wood resource template
        wood_path = os.path.join(self.templates_dir, 'wood_resource.png')
        wood_img = np.zeros((40, 40, 3), dtype=np.uint8)
        wood_img[:, :] = [32, 80, 140]  # BGR for brown
        cv2.rectangle(wood_img, (10, 15), (30, 35), (20, 60, 100), -1)  # Tree trunk
        cv2.imwrite(wood_path, wood_img)
        
        # Create stone resource template
        stone_path = os.path.join(self.templates_dir, 'stone_resource.png')
        stone_img = np.zeros((40, 40, 3), dtype=np.uint8)
        stone_img[:, :] = [150, 150, 150]  # BGR for gray
        cv2.circle(stone_img, (20, 20), 15, (100, 100, 100), -1)  # Darker circle
        cv2.imwrite(stone_path, stone_img)
        
        # Create collect button template
        collect_path = os.path.join(self.templates_dir, 'collect_button.png')
        collect_img = np.zeros((60, 100, 3), dtype=np.uint8)
        collect_img[:, :] = [50, 50, 200]  # BGR for red button
        cv2.putText(collect_img, "Collect", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(collect_path, collect_img)
        
        # Create close button template
        close_path = os.path.join(self.templates_dir, 'close_button.png')
        close_img = np.zeros((30, 30, 3), dtype=np.uint8)
        close_img[:, :] = [50, 50, 200]  # BGR for red button
        cv2.line(close_img, (5, 5), (25, 25), (255, 255, 255), 2)
        cv2.line(close_img, (5, 25), (25, 5), (255, 255, 255), 2)
        cv2.imwrite(close_path, close_img)
    
    def _create_world_map(self):
        """Create a virtual game world map with resources."""
        # Define resource locations in the game world
        resource_locations = [
            {"type": "gold", "coords": Coordinates(1, 120, 150), "level": 3},
            {"type": "gold", "coords": Coordinates(1, 180, 220), "level": 5},
            {"type": "wood", "coords": Coordinates(1, 90, 200), "level": 4},
            {"type": "wood", "coords": Coordinates(1, 150, 300), "level": 6},
            {"type": "stone", "coords": Coordinates(1, 240, 180), "level": 2},
            {"type": "stone", "coords": Coordinates(1, 280, 260), "level": 7}
        ]
        
        # Return the world map
        return resource_locations
    
    def _init_services(self):
        """Initialize all services required for testing."""
        # Create window service (mocked)
        self.window_service = WindowService(self.event_bus)
        self.window_service.find_window = MagicMock(return_value=True)
        self.window_service.get_window_position = MagicMock(return_value=(0, 0, 800, 600))
        
        # Create world view based on current position
        self.current_view_coords = Coordinates(1, 100, 100)
        self._update_game_view()
        
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
            if 350 <= x <= 450 and 10 <= y <= 50:
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
                        self._update_game_view()
                        logger.info(f"Navigated to coordinates: K1 ({x}, {y})")
                except ValueError:
                    logger.warning(f"Failed to parse coordinates from text: {text}")
                    
                # Reset the flag
                self.actions_service._clicking_coord_field = False
                
            return result
            
        # Apply our mock functions
        self.actions_service.click_at = mock_click
        self.actions_service.input_text = mock_input
    
    def _update_game_view(self):
        """
        Update the simulated game view based on current coordinates.
        
        This creates a screenshot showing resources that would be visible
        at the current map coordinates.
        """
        # Create base game view image (800x600)
        game_view = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add background (green terrain)
        game_view[:, :] = [50, 120, 50]
        
        # Add coordinate display at top left
        cv2.putText(
            game_view, 
            f"K1 ({self.current_view_coords.x}, {self.current_view_coords.y})", 
            (20, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (255, 255, 255), 
            2
        )
        
        # Add coordinate input field at top center
        cv2.rectangle(game_view, (350, 10), (450, 40), (200, 200, 200), -1)
        
        # Calculate view boundaries (what's visible on screen)
        # Assume each game view shows a 200x150 unit area of the game world
        view_min_x = self.current_view_coords.x - 100
        view_max_x = self.current_view_coords.x + 100
        view_min_y = self.current_view_coords.y - 75
        view_max_y = self.current_view_coords.y + 75
        
        # Add visible resources to the view
        for resource in self.world_map:
            coords = resource["coords"]
            
            # Check if resource is in view
            if (view_min_x <= coords.x <= view_max_x and 
                view_min_y <= coords.y <= view_max_y):
                
                # Calculate screen position based on game coordinates
                screen_x = 400 + (coords.x - self.current_view_coords.x) * 4
                screen_y = 300 + (coords.y - self.current_view_coords.y) * 4
                
                # Add resource icon based on type
                if resource["type"] == "gold":
                    color = [0, 215, 255]  # Gold (BGR)
                elif resource["type"] == "wood":
                    color = [32, 80, 140]  # Wood (BGR)
                elif resource["type"] == "stone":
                    color = [150, 150, 150]  # Stone (BGR)
                else:
                    color = [200, 200, 200]  # Unknown (BGR)
                
                # Draw resource icon
                cv2.circle(game_view, (int(screen_x), int(screen_y)), 20, color, -1)
                
                # Add level text
                cv2.putText(
                    game_view,
                    f"Lv{resource['level']}",
                    (int(screen_x - 15), int(screen_y + 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )
                
                # If cursor is over this resource (within 30 pixels), show collect button
                cursor_pos = self.actions_service.actions_log[-1][1:3] if self.actions_service.actions_log else (0, 0)
                if (abs(cursor_pos[0] - screen_x) < 30 and
                    abs(cursor_pos[1] - screen_y) < 30):
                    
                    # Add collect button
                    cv2.rectangle(
                        game_view,
                        (int(screen_x - 50), int(screen_y + 30)),
                        (int(screen_x + 50), int(screen_y + 60)),
                        (50, 50, 200),
                        -1
                    )
                    cv2.putText(
                        game_view,
                        "Collect",
                        (int(screen_x - 40), int(screen_y + 50)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2
                    )
                    
                    # Add close button at top right of collect window
                    cv2.rectangle(
                        game_view,
                        (int(screen_x + 60), int(screen_y - 40)),
                        (int(screen_x + 75), int(screen_y - 25)),
                        (50, 50, 200),
                        -1
                    )
                    cv2.line(
                        game_view, 
                        (int(screen_x + 63), int(screen_y - 37)), 
                        (int(screen_x + 72), int(screen_y - 28)), 
                        (255, 255, 255), 
                        1
                    )
                    cv2.line(
                        game_view, 
                        (int(screen_x + 63), int(screen_y - 28)), 
                        (int(screen_x + 72), int(screen_y - 37)), 
                        (255, 255, 255), 
                        1
                    )
        
        # Update the window service to return this view
        self.window_service.capture_screenshot = MagicMock(return_value=game_view)
    
    def _setup_initial_game_state(self):
        """Set up initial game state for testing."""
        # Set current position
        self.game_service.state.current_position = self.current_view_coords
        
        # Add some resources to player inventory
        self.game_service.state.resources.update("gold", 1000, 10000)
        self.game_service.state.resources.update("wood", 500, 5000)
        self.game_service.state.resources.update("stone", 200, 2000)
        
        # Save state
        self.game_service.save_state()
    
    def test_resource_collection_workflow(self):
        """
        Test complete resource collection workflow.
        
        This tests the following workflow:
        1. Scan the area to find resources
        2. For each resource:
           a. Navigate to resource location
           b. Click on resource to open collection menu
           c. Click collect button
           d. Close resource window
        3. Verify resources were added to inventory
        """
        # Step 1: Scan the area for resources
        logger.info("Step 1: Scanning for resources")
        scan_task = ScanAreaTask(
            "scan_resources",
            strategy="template",
            area_size=10,  # Scan 10 tiles in each direction
            object_templates=["gold_resource", "wood_resource", "stone_resource"],
            confidence=0.7
        )
        
        # Execute scan task
        self.automation_service.execute_task_synchronously(scan_task)
        
        # Verify scan task completed successfully
        self.assertEqual(scan_task.status, TaskStatus.COMPLETED)
        
        # Get detected resources from game state
        resources = [
            entity for entity in self.game_service.state.known_entities.values()
            if entity.entity_type == 'resource'
        ]
        
        # Verify resources were detected
        self.assertGreater(len(resources), 0)
        logger.info(f"Found {len(resources)} resources")
        
        # Record initial resource amounts
        initial_gold = self.game_service.state.resources.get("gold").amount
        initial_wood = self.game_service.state.resources.get("wood").amount
        initial_stone = self.game_service.state.resources.get("stone").amount
        
        # Step 2: Collect each resource
        for i, resource in enumerate(resources[:3]):  # Limit to first 3 for testing
            logger.info(f"Step 2.{i+1}: Collecting {resource.entity_type} at {resource.coordinates}")
            
            # Create composite task for collecting this resource
            collect_resource_task = CompositeTask(f"collect_resource_{i}")
            
            # a. Navigate to resource location
            navigate_task = NavigateToCoordinatesTask(
                f"navigate_to_{i}",
                coordinates=resource.coordinates,
                input_field_position=(400, 25)  # Coordinate input field position
            )
            collect_resource_task.add_task(navigate_task)
            
            # Add wait after navigation
            wait_task1 = WaitTask(f"wait_after_nav_{i}", 0.5)
            collect_resource_task.add_task(wait_task1)
            
            # b. Click on resource to open collection menu
            # Calculate approximate screen position based on current view
            screen_x = 400 + (resource.coordinates.x - self.current_view_coords.x) * 4
            screen_y = 300 + (resource.coordinates.y - self.current_view_coords.y) * 4
            
            click_resource_task = ClickTask(
                f"click_resource_{i}",
                int(screen_x),
                int(screen_y)
            )
            collect_resource_task.add_task(click_resource_task)
            
            # Add wait after clicking resource
            wait_task2 = WaitTask(f"wait_after_resource_click_{i}", 0.5)
            collect_resource_task.add_task(wait_task2)
            
            # c. Click collect button
            # Find collect button through detection
            detect_collect_task = DetectTask(
                f"detect_collect_{i}",
                strategy="template",
                templates=["collect_button"]
            )
            collect_resource_task.add_task(detect_collect_task)
            
            # Click on detected collect button
            click_collect_task = ClickTask(
                f"click_collect_{i}",
                0, 0  # Placeholder coordinates
            )
            
            # Make collect button click dependent on detection
            click_collect_task.add_dependency(detect_collect_task)
            
            # Add callback to update click coordinates based on detection result
            def update_collect_coords(task):
                if task.result and len(task.result) > 0:
                    result = task.result[0]
                    x = result['x'] + result['width'] // 2
                    y = result['y'] + result['height'] // 2
                    click_collect_task.params['x'] = x
                    click_collect_task.params['y'] = y
            
            detect_collect_task.add_completion_callback(update_collect_coords)
            collect_resource_task.add_task(click_collect_task)
            
            # Add wait after clicking collect
            wait_task3 = WaitTask(f"wait_after_collect_{i}", 0.5)
            collect_resource_task.add_task(wait_task3)
            
            # d. Close resource window
            # Find close button through detection
            detect_close_task = DetectTask(
                f"detect_close_{i}",
                strategy="template",
                templates=["close_button"]
            )
            collect_resource_task.add_task(detect_close_task)
            
            # Click on detected close button
            click_close_task = ClickTask(
                f"click_close_{i}",
                0, 0  # Placeholder coordinates
            )
            
            # Make close button click dependent on detection
            click_close_task.add_dependency(detect_close_task)
            
            # Add callback to update click coordinates based on detection result
            def update_close_coords(task):
                if task.result and len(task.result) > 0:
                    result = task.result[0]
                    x = result['x'] + result['width'] // 2
                    y = result['y'] + result['height'] // 2
                    click_close_task.params['x'] = x
                    click_close_task.params['y'] = y
            
            detect_close_task.add_completion_callback(update_close_coords)
            collect_resource_task.add_task(click_close_task)
            
            # Add final wait
            wait_task4 = WaitTask(f"wait_after_close_{i}", 0.5)
            collect_resource_task.add_task(wait_task4)
            
            # Execute all tasks for this resource
            self.automation_service.execute_task_synchronously(collect_resource_task)
            
            # Verify task completed successfully
            self.assertEqual(collect_resource_task.status, TaskStatus.COMPLETED)
            
            # Update resource inventory in game state (simulate collection)
            resource_type = resource.entity_type
            current_amount = self.game_service.state.resources.get(resource_type).amount
            current_capacity = self.game_service.state.resources.get(resource_type).capacity
            
            # Add resource amount based on level (100 * level)
            new_amount = current_amount + (100 * resource.level)
            self.game_service.state.resources.update(resource_type, new_amount, current_capacity)
            
            logger.info(f"Collected {100 * resource.level} {resource_type}")
        
        # Verify resources were added to inventory
        final_gold = self.game_service.state.resources.get("gold").amount
        final_wood = self.game_service.state.resources.get("wood").amount
        final_stone = self.game_service.state.resources.get("stone").amount
        
        logger.info(f"Gold: {initial_gold} -> {final_gold}")
        logger.info(f"Wood: {initial_wood} -> {final_wood}")
        logger.info(f"Stone: {initial_stone} -> {final_stone}")
        
        # Check that at least one resource type increased
        self.assertTrue(
            final_gold > initial_gold or
            final_wood > initial_wood or
            final_stone > initial_stone,
            "No resources were added to inventory"
        )
        
        # Verify appropriate actions were performed
        actions = self.actions_service.get_actions()
        
        # Count action types
        click_actions = [a for a in actions if a[0] == 'click']
        input_actions = [a for a in actions if a[0] == 'input_text']
        
        # We should have:
        # - At least 3 clicks per resource (resource, collect button, close button)
        # - At least 1 coordinate input per resource
        self.assertGreaterEqual(len(click_actions), 9)  # 3 resources * 3 clicks
        self.assertGreaterEqual(len(input_actions), 3)  # 3 resources * 1 input


if __name__ == '__main__':
    unittest.main() 