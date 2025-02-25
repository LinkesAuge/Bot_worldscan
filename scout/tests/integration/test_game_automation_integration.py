"""
GameService and AutomationService Integration Tests

This module contains integration tests that verify the interaction between
the GameService and AutomationService components.
"""

import unittest
import os
import tempfile
import shutil
import time
import cv2
import numpy as np
from unittest.mock import MagicMock, patch

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.game.game_service import GameService
from scout.core.game.game_state import Coordinates, Resource
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import TaskStatus
from scout.core.automation.tasks.basic_tasks import ClickTask, WaitTask, DetectTask
from scout.core.automation.tasks.game_tasks import NavigateToCoordinatesTask, CollectResourcesTask

class MockActionsService:
    """Mock implementation of an actions service for testing."""
    
    def __init__(self):
        self.actions_log = []
    
    def click_at(self, x, y, relative_to_window=True, button='left', clicks=1):
        """Log click actions."""
        self.actions_log.append(('click', x, y, relative_to_window, button, clicks))
        return True
    
    def drag_mouse(self, start_x, start_y, end_x, end_y, relative_to_window=True, duration=0.5):
        """Log drag actions."""
        self.actions_log.append(('drag', start_x, start_y, end_x, end_y, relative_to_window, duration))
        return True
    
    def input_text(self, text):
        """Log text input actions."""
        self.actions_log.append(('input_text', text))
        return True
    
    def get_actions(self):
        """Get all logged actions."""
        return self.actions_log
    
    def clear_log(self):
        """Clear action log."""
        self.actions_log = []


class TestGameAutomationIntegration(unittest.TestCase):
    """
    Integration tests for GameService and AutomationService.
    
    These tests verify that:
    1. AutomationService can execute tasks based on game state
    2. Game-specific tasks can properly use game service information
    3. Events flow correctly between components
    """
    
    def setUp(self):
        """Set up test fixture."""
        # Create event bus
        self.event_bus = EventBus()
        
        # Set up event listener to track events
        self.automation_events = []
        self.game_events = []
        self.event_bus.subscribe(EventType.AUTOMATION_TASK_COMPLETED, 
                                 lambda e: self.automation_events.append(e))
        self.event_bus.subscribe(EventType.GAME_STATE_CHANGED, 
                                 lambda e: self.game_events.append(e))
        
        # Create temporary directory for templates and cache
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        self.state_dir = os.path.join(self.temp_dir, 'state')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create test template images
        self._create_test_templates()
        
        # Create mock services
        self.window_service = self._create_mock_window_service()
        self.detection_service = self._create_mock_detection_service()
        self.game_service = self._create_mock_game_service()
        self.actions_service = MockActionsService()
        
        # Create automation service
        self.automation_service = AutomationService(self.event_bus)
        
        # Set up execution context for tasks
        self.automation_service.set_execution_context({
            'window_service': self.window_service,
            'detection_service': self.detection_service,
            'game_service': self.game_service,
            'actions_service': self.actions_service
        })
    
    def tearDown(self):
        """Clean up after the test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _create_test_templates(self):
        """Create test template images for detection."""
        # Create resource template (gold coin)
        gold_path = os.path.join(self.templates_dir, 'gold_resource.png')
        gold_img = np.zeros((40, 40, 3), dtype=np.uint8)
        gold_img[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_img, (20, 20), 15, (0, 165, 255), -1)  # Darker gold circle
        cv2.imwrite(gold_path, gold_img)
        
        # Create resource collection button template
        collect_path = os.path.join(self.templates_dir, 'collect_button.png')
        collect_img = np.zeros((60, 100, 3), dtype=np.uint8)
        collect_img[:, :] = [50, 50, 200]  # Red button
        cv2.putText(collect_img, "Collect", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(collect_path, collect_img)
    
    def _create_mock_window_service(self):
        """Create a mock window service."""
        window_service = MagicMock(spec=WindowService)
        window_service.find_window.return_value = True
        window_service.get_window_position.return_value = (0, 0, 800, 600)
        
        # Create a test screenshot with resource buttons
        test_image = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add some resource collection buttons
        for i in range(3):
            button_img = np.zeros((60, 100, 3), dtype=np.uint8)
            button_img[:, :] = [50, 50, 200]  # Red button
            cv2.putText(button_img, "Collect", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            x_pos = 100 + i * 150
            test_image[100:160, x_pos:x_pos+100] = button_img
        
        window_service.capture_screenshot.return_value = test_image
        return window_service
    
    def _create_mock_detection_service(self):
        """Create a mock detection service."""
        detection_service = MagicMock(spec=DetectionService)
        
        # Configure detect_template to return matching results
        def mock_detect_template(**kwargs):
            template_name = kwargs.get('template_name')
            if template_name == 'collect_button':
                # Return 3 resource buttons
                return [
                    {
                        'template_name': 'collect_button',
                        'confidence': 0.95,
                        'x': 100, 'y': 100,
                        'width': 100, 'height': 60
                    },
                    {
                        'template_name': 'collect_button',
                        'confidence': 0.93,
                        'x': 250, 'y': 100,
                        'width': 100, 'height': 60
                    },
                    {
                        'template_name': 'collect_button',
                        'confidence': 0.91,
                        'x': 400, 'y': 100,
                        'width': 100, 'height': 60
                    }
                ]
            return []
        
        detection_service.detect_template.side_effect = mock_detect_template
        
        # Configure detect_text to return coordinate text
        def mock_detect_text(**kwargs):
            return [
                {
                    'text': 'K1 (123,456)',
                    'confidence': 0.9,
                    'x': 400, 'y': 30,
                    'width': 120, 'height': 30
                }
            ]
        
        detection_service.detect_text.side_effect = mock_detect_text
        
        return detection_service
    
    def _create_mock_game_service(self):
        """Create a mock game service with pre-defined state."""
        game_service = MagicMock(spec=GameService)
        
        # Create game state
        game_service.state = MagicMock()
        game_service.state.current_position = Coordinates(1, 123, 456)
        game_service.state.resources = {
            'gold': Resource('gold', 10000, 20000),
            'food': Resource('food', 5000, 10000)
        }
        
        # Mock the convert screen to game coordinates method
        game_service._screen_to_game_coords.return_value = Coordinates(1, 125, 458)
        
        return game_service
    
    def test_basic_click_task(self):
        """Test that basic click task works with game coordinates."""
        # Create a click task
        click_task = ClickTask("test_click", 200, 150, relative_to_window=True)
        
        # Execute task synchronously
        result = self.automation_service.execute_task_synchronously(click_task)
        
        # Verify task executed successfully
        self.assertTrue(result)
        self.assertEqual(click_task.status, TaskStatus.COMPLETED)
        
        # Check that the click was recorded by the actions service
        actions = self.actions_service.get_actions()
        self.assertEqual(len(actions), 1)
        
        action = actions[0]
        self.assertEqual(action[0], 'click')
        self.assertEqual(action[1], 200)  # x
        self.assertEqual(action[2], 150)  # y
    
    def test_detect_task_with_game_service(self):
        """Test that detect task works with game and detection services."""
        # Create a detect task using template strategy
        detect_task = DetectTask(
            "test_detect",
            strategy="template",
            templates=["collect_button"],
            confidence=0.8
        )
        
        # Execute task synchronously
        result = self.automation_service.execute_task_synchronously(detect_task)
        
        # Verify task executed successfully
        self.assertTrue(result)
        self.assertEqual(detect_task.status, TaskStatus.COMPLETED)
        
        # Check detection results
        detection_results = detect_task.result
        self.assertIsNotNone(detection_results)
        self.assertEqual(len(detection_results), 3)  # 3 collect buttons
    
    def test_collect_resources_task(self):
        """Test the collect resources game task."""
        # Create a collection task
        collect_task = CollectResourcesTask(
            "test_collect",
            resource_templates=["collect_button"],
            max_collections=5
        )
        
        # Execute task synchronously
        result = self.automation_service.execute_task_synchronously(collect_task)
        
        # Verify task executed successfully
        self.assertTrue(result)
        self.assertEqual(collect_task.status, TaskStatus.COMPLETED)
        
        # Check that clicks were recorded by the actions service
        actions = self.actions_service.get_actions()
        
        # Should have 3 click actions (for each button) and wait actions in between
        click_actions = [a for a in actions if a[0] == 'click']
        self.assertEqual(len(click_actions), 3)
        
        # Verify result shows how many resources were collected
        self.assertEqual(collect_task.result, 3)
    
    def test_task_execution_sequence(self):
        """Test executing a sequence of tasks in order."""
        # Create tasks
        click_task = ClickTask("test_click", 200, 150)
        wait_task = WaitTask("test_wait", 0.1)  # Short wait for testing
        detect_task = DetectTask("test_detect", strategy="template", templates=["collect_button"])
        
        # Add tasks to automation service
        self.automation_service.add_task(click_task)
        self.automation_service.add_task(wait_task)
        self.automation_service.add_task(detect_task)
        
        # Start execution
        self.automation_service.start_execution()
        
        # Wait for all tasks to complete
        max_wait = 2.0  # seconds
        start = time.time()
        while (any(task.status != TaskStatus.COMPLETED for task in 
                  [click_task, wait_task, detect_task]) and 
               time.time() - start < max_wait):
            time.sleep(0.1)
        
        # Stop execution
        self.automation_service.stop_execution()
        
        # Verify all tasks completed
        self.assertEqual(click_task.status, TaskStatus.COMPLETED)
        self.assertEqual(wait_task.status, TaskStatus.COMPLETED)
        self.assertEqual(detect_task.status, TaskStatus.COMPLETED)
        
        # Verify actions were recorded in the right order
        actions = self.actions_service.get_actions()
        self.assertEqual(actions[0][0], 'click')  # First action should be click
    
    def test_navigate_to_coordinates_task(self):
        """Test the navigate to coordinates game task."""
        # Create a navigate task
        coords = Coordinates(1, 234, 567)
        input_field_position = (400, 50)
        
        navigate_task = NavigateToCoordinatesTask(
            "test_navigate",
            coordinates=coords,
            input_field_position=input_field_position
        )
        
        # Execute task synchronously
        result = self.automation_service.execute_task_synchronously(navigate_task)
        
        # Verify task executed successfully
        self.assertTrue(result)
        self.assertEqual(navigate_task.status, TaskStatus.COMPLETED)
        
        # Check that actions were recorded
        actions = self.actions_service.get_actions()
        
        # Should have click and text input actions
        click_actions = [a for a in actions if a[0] == 'click']
        text_actions = [a for a in actions if a[0] == 'input_text']
        
        self.assertEqual(len(click_actions), 1)
        self.assertEqual(len(text_actions), 1)
        
        # Verify click position
        self.assertEqual(click_actions[0][1], input_field_position[0])  # x
        self.assertEqual(click_actions[0][2], input_field_position[1])  # y
        
        # Verify text input
        self.assertEqual(text_actions[0][1], f"{coords.x},{coords.y}")
    
    def test_task_dependencies(self):
        """Test tasks with dependencies using game services."""
        # Create tasks with dependencies
        detect_task = DetectTask("detect_resources", strategy="template", templates=["collect_button"])
        
        # Create click task that depends on the detection result
        click_task = ClickTask("click_first_resource", 0, 0)  # Will set coordinates later
        click_task.add_dependency(detect_task)
        
        # Add custom completion callback to the detect task to update click coordinates
        def update_click_coordinates(task):
            if task.result and len(task.result) > 0:
                first_result = task.result[0]
                x = first_result['x'] + first_result['width'] // 2
                y = first_result['y'] + first_result['height'] // 2
                click_task.params['x'] = x
                click_task.params['y'] = y
        
        detect_task.add_completion_callback(update_click_coordinates)
        
        # Add tasks to automation service
        self.automation_service.add_task(detect_task)
        self.automation_service.add_task(click_task)
        
        # Start execution
        self.automation_service.start_execution()
        
        # Wait for all tasks to complete
        max_wait = 2.0  # seconds
        start = time.time()
        while (any(task.status != TaskStatus.COMPLETED for task in [detect_task, click_task]) and 
               time.time() - start < max_wait):
            time.sleep(0.1)
        
        # Stop execution
        self.automation_service.stop_execution()
        
        # Verify all tasks completed
        self.assertEqual(detect_task.status, TaskStatus.COMPLETED)
        self.assertEqual(click_task.status, TaskStatus.COMPLETED)
        
        # Verify actions were recorded in the right order
        actions = self.actions_service.get_actions()
        self.assertEqual(len(actions), 1)  # Should be one click
        
        # Check click coordinates - should match the first detected resource
        action = actions[0]
        self.assertEqual(action[0], 'click')
        self.assertEqual(action[1], 150)  # center x of first button
        self.assertEqual(action[2], 130)  # center y of first button
    
    def test_event_propagation(self):
        """Test event propagation between automation and game services."""
        # Create task
        detect_task = DetectTask("test_detect", strategy="template", templates=["collect_button"])
        
        # Execute task synchronously
        self.automation_service.execute_task_synchronously(detect_task)
        
        # Verify automation events were published
        self.assertGreater(len(self.automation_events), 0)
        
        # Extract the task name from the event
        task_name = self.automation_events[0].data.get('task_name')
        self.assertEqual(task_name, "test_detect")
        
        # Verify the event contains the required data
        self.assertIn('task_type', self.automation_events[0].data)
        self.assertIn('task_status', self.automation_events[0].data)
        self.assertIn('timestamp', self.automation_events[0].data)


if __name__ == '__main__':
    unittest.main() 