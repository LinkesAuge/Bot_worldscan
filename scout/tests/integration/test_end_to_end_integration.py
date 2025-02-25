"""
End-to-End Integration Tests

This module contains comprehensive end-to-end integration tests that verify
the full workflow of the Scout application, from window detection to
task execution.
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


class TestEndToEndIntegration(unittest.TestCase):
    """
    End-to-end integration tests for the Scout application.
    
    These tests verify the complete workflow:
    1. Window detection and screenshot capture
    2. Game element detection using different strategies
    3. Game state updates based on detection results
    4. Automation task execution using game state
    5. Event propagation between all components
    """
    
    def setUp(self):
        """Set up test fixture."""
        # Create event bus - shared between all components
        self.event_bus = EventBus()
        
        # Set up event listeners to track events
        self.all_events = []
        self.window_events = []
        self.detection_events = []
        self.game_events = []
        self.automation_events = []
        
        # Subscribe to all relevant events
        self.event_bus.subscribe(EventType.WINDOW_FOUND, 
                                 lambda e: (self.all_events.append(e), self.window_events.append(e)))
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, 
                                 lambda e: (self.all_events.append(e), self.detection_events.append(e)))
        self.event_bus.subscribe(EventType.GAME_STATE_CHANGED, 
                                 lambda e: (self.all_events.append(e), self.game_events.append(e)))
        self.event_bus.subscribe(EventType.AUTOMATION_TASK_COMPLETED, 
                                 lambda e: (self.all_events.append(e), self.automation_events.append(e)))
        
        # Create temporary directory for templates and state
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        self.state_dir = os.path.join(self.temp_dir, 'state')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create test templates
        self._create_test_templates()
        
        # Create test game image
        self.test_game_image = self._create_test_game_image()
        
        # Create mock window title for tracking
        self.window_title = "Total Battle - Test Window"
        
        # Initialize services
        self._init_services()
    
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
        gold_img[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_img, (20, 20), 15, (0, 165, 255), -1)  # Darker gold circle
        cv2.imwrite(gold_path, gold_img)
        
        # Create building template (castle)
        castle_path = os.path.join(self.templates_dir, 'castle.png')
        castle_img = np.zeros((60, 60, 3), dtype=np.uint8)
        castle_img[:, :] = [90, 90, 90]  # Gray background
        # Simple castle shape
        cv2.rectangle(castle_img, (10, 30), (50, 59), (50, 50, 120), -1)  # Base
        cv2.rectangle(castle_img, (20, 10), (40, 30), (50, 50, 120), -1)  # Top
        cv2.imwrite(castle_path, castle_img)
        
        # Create resource collection button template
        collect_path = os.path.join(self.templates_dir, 'collect_button.png')
        collect_img = np.zeros((60, 100, 3), dtype=np.uint8)
        collect_img[:, :] = [50, 50, 200]  # Red button
        cv2.putText(collect_img, "Collect", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(collect_path, collect_img)
    
    def _create_test_game_image(self):
        """Create a test game screenshot with various elements."""
        # Create a 800x600 test image
        game_image = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add background
        game_image[:, :] = [50, 120, 50]  # Dark green background
        
        # Add gold resource icon at top right
        gold_region = game_image[10:50, 600:640]
        gold_region[:, :] = [0, 215, 255]  # BGR for gold color
        cv2.circle(gold_region, (20, 20), 15, (0, 165, 255), -1)
        
        # Add castle in center
        castle_region = game_image[250:310, 370:430]
        castle_region[:, :] = [90, 90, 90]  # Gray background
        cv2.rectangle(castle_region, (10, 30), (50, 59), (50, 50, 120), -1)
        cv2.rectangle(castle_region, (20, 10), (40, 30), (50, 50, 120), -1)
        
        # Add coordinates text
        cv2.putText(game_image, "K1 (123,456)", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add resource counters
        cv2.putText(game_image, "Gold: 10000/20000", (650, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(game_image, "Food: 5000/10000", (650, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add resource collection buttons at bottom
        for i in range(3):
            button_img = np.zeros((60, 100, 3), dtype=np.uint8)
            button_img[:, :] = [50, 50, 200]  # Red button
            cv2.putText(button_img, "Collect", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            x_pos = 100 + i * 250
            game_image[500:560, x_pos:x_pos+100] = button_img
        
        return game_image
    
    def _init_services(self):
        """Initialize all services with appropriate mocks."""
        # Create window service with mock find_window and capture_screenshot
        self.window_service = WindowService(self.event_bus)
        self.window_service.find_window = MagicMock(return_value=True)
        self.window_service.get_window_position = MagicMock(return_value=(0, 0, 800, 600))
        self.window_service.capture_screenshot = MagicMock(return_value=self.test_game_image)
        
        # Create template strategy
        template_strategy = TemplateMatchingStrategy(templates_dir=self.templates_dir)
        
        # Create detection service
        self.detection_service = DetectionService(self.event_bus, self.window_service)
        self.detection_service.register_strategy('template', template_strategy)
        
        # Create OCR mock that returns predefined results for specific regions
        def mock_detect_ocr(image, **kwargs):
            height, width = image.shape[:2]
            
            # Coordinates at top left
            if width < 200 and height < 50:
                return [{'text': 'K1 (123,456)', 'confidence': 0.95, 'x': 20, 'y': 10, 'width': 150, 'height': 30}]
            
            # Resource counters at top right
            elif width < 200 and 10 <= height <= 100:
                if 20 <= height <= 40:
                    return [{'text': 'Gold: 10000/20000', 'confidence': 0.92, 'x': 650, 'y': 20, 'width': 140, 'height': 20}]
                else:
                    return [{'text': 'Food: 5000/10000', 'confidence': 0.90, 'x': 650, 'y': 50, 'width': 140, 'height': 20}]
            
            # Full screen OCR should find all text
            elif width > 700:
                return [
                    {'text': 'K1 (123,456)', 'confidence': 0.95, 'x': 20, 'y': 10, 'width': 150, 'height': 30},
                    {'text': 'Gold: 10000/20000', 'confidence': 0.92, 'x': 650, 'y': 20, 'width': 140, 'height': 20},
                    {'text': 'Food: 5000/10000', 'confidence': 0.90, 'x': 650, 'y': 50, 'width': 140, 'height': 20},
                    {'text': 'Collect', 'confidence': 0.96, 'x': 110, 'y': 520, 'width': 80, 'height': 30},
                    {'text': 'Collect', 'confidence': 0.95, 'x': 360, 'y': 520, 'width': 80, 'height': 30},
                    {'text': 'Collect', 'confidence': 0.94, 'x': 610, 'y': 520, 'width': 80, 'height': 30}
                ]
            
            return []
        
        # Register OCR strategy mock
        ocr_strategy = MagicMock()
        ocr_strategy.detect.side_effect = mock_detect_ocr
        ocr_strategy.get_name.return_value = 'OCR Strategy'
        self.detection_service.register_strategy('ocr', ocr_strategy)
        
        # Create game service
        self.game_service = GameService(
            self.event_bus,
            self.detection_service,
            state_file_path=os.path.join(self.state_dir, 'game_state.json')
        )
        
        # Create actions service
        self.actions_service = MockActionsService()
        
        # Create automation service
        self.automation_service = AutomationService(self.event_bus)
        
        # Set up execution context for automation tasks
        self.automation_service.set_execution_context({
            'window_service': self.window_service,
            'detection_service': self.detection_service,
            'game_service': self.game_service,
            'actions_service': self.actions_service
        })
    
    def test_complete_workflow(self):
        """
        Test the complete workflow from window detection to task execution.
        
        This test verifies that:
        1. The window service can find and capture the game window
        2. The detection service can process the screenshot
        3. The game service can update state based on detection
        4. The automation service can execute tasks using the game state
        5. Events propagate correctly between all components
        """
        # Initialize test
        self.detection_service.set_context({'window_title': self.window_title})
        
        # Step 1: Find the game window and capture screenshot
        self.window_service.find_window(self.window_title)
        screenshot = self.window_service.capture_screenshot()
        
        # Verify window was found and screenshot captured
        self.assertIsNotNone(screenshot)
        self.assertEqual(screenshot.shape, (600, 800, 3))
        
        # Verify window events were published
        self.assertGreater(len(self.window_events), 0)
        
        # Step 2: Update game state using detection
        self.game_service.update_current_position()
        self.game_service.update_resources()
        
        # Verify game state was updated correctly
        self.assertIsNotNone(self.game_service.state.current_position)
        self.assertEqual(self.game_service.state.current_position.kingdom, 1)
        self.assertEqual(self.game_service.state.current_position.x, 123)
        self.assertEqual(self.game_service.state.current_position.y, 456)
        
        # Check resources
        resources = self.game_service.state.resources
        self.assertIsNotNone(resources)
        self.assertIn('gold', resources)
        self.assertEqual(resources['gold'].amount, 10000)
        self.assertEqual(resources['gold'].capacity, 20000)
        
        # Verify game state events were published
        self.assertGreater(len(self.game_events), 0)
        
        # Step 3: Create and execute an automation task
        # First create a detect task to find resource buttons
        detect_task = DetectTask(
            "detect_resources",
            strategy="template",
            templates=["collect_button"],
            confidence=0.7
        )
        
        # Execute detection task
        self.automation_service.execute_task_synchronously(detect_task)
        
        # Verify detection task succeeded
        self.assertEqual(detect_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(detect_task.result)
        self.assertGreater(len(detect_task.result), 0)
        
        # Create a click task to click the first resource button
        first_result = detect_task.result[0]
        click_x = first_result['x'] + first_result['width'] // 2
        click_y = first_result['y'] + first_result['height'] // 2
        click_task = ClickTask("click_resource", click_x, click_y)
        
        # Execute click task
        self.automation_service.execute_task_synchronously(click_task)
        
        # Verify click task succeeded
        self.assertEqual(click_task.status, TaskStatus.COMPLETED)
        
        # Verify actions were recorded
        actions = self.actions_service.get_actions()
        self.assertEqual(len(actions), 1)
        
        action = actions[0]
        self.assertEqual(action[0], 'click')
        self.assertEqual(action[1], click_x)
        self.assertEqual(action[2], click_y)
        
        # Step 4: Verify event propagation
        # Check that we received events from all components
        self.assertGreater(len(self.all_events), 0)
        self.assertGreater(len(self.window_events), 0)
        self.assertGreater(len(self.detection_events), 0)
        self.assertGreater(len(self.game_events), 0)
        self.assertGreater(len(self.automation_events), 0)
        
        # Verify event order
        # Window events should come before detection events
        window_timestamp = self.window_events[0].timestamp
        detection_timestamp = self.detection_events[0].timestamp
        self.assertLessEqual(window_timestamp, detection_timestamp)
        
        # Step 5: Test a higher-level game-specific task
        # Create a collect resources task
        collect_task = CollectResourcesTask(
            "collect_all_resources",
            resource_templates=["collect_button"],
            max_collections=5
        )
        
        # Clear previous actions
        self.actions_service.clear_log()
        
        # Execute collection task
        self.automation_service.execute_task_synchronously(collect_task)
        
        # Verify task completed
        self.assertEqual(collect_task.status, TaskStatus.COMPLETED)
        
        # Verify actions were recorded
        actions = self.actions_service.get_actions()
        
        # Should have multiple click actions for resource buttons
        click_actions = [a for a in actions if a[0] == 'click']
        self.assertGreater(len(click_actions), 0)
        
        # Verify result contains number of collected resources
        self.assertIsNotNone(collect_task.result)
        self.assertGreater(collect_task.result, 0)
    
    def test_workflow_with_task_dependencies(self):
        """
        Test the workflow with task dependencies.
        
        This test verifies that tasks can depend on each other
        and share data between detection and action.
        """
        # Initialize test
        self.detection_service.set_context({'window_title': self.window_title})
        
        # Create a sequence of dependent tasks:
        # 1. Detect resource buttons
        # 2. Click on the first one
        # 3. Wait a short time
        # 4. Click on the second one
        
        # First task: detect resources
        detect_task = DetectTask(
            "detect_resources",
            strategy="template",
            templates=["collect_button"],
            confidence=0.7
        )
        
        # Second task: click first resource (depends on detection)
        click_task1 = ClickTask("click_first_resource", 0, 0)  # Coordinates will be updated by callback
        click_task1.add_dependency(detect_task)
        
        # Third task: wait
        wait_task = WaitTask("wait_after_click", 0.1)  # Short wait for testing
        wait_task.add_dependency(click_task1)
        
        # Fourth task: click second resource (depends on detection)
        click_task2 = ClickTask("click_second_resource", 0, 0)  # Coordinates will be updated by callback
        click_task2.add_dependency(wait_task)
        
        # Add completion callback to update click coordinates
        def update_click_coordinates(task):
            if task.result and len(task.result) >= 2:
                # Update first click task with first button coordinates
                first_result = task.result[0]
                click_task1.params['x'] = first_result['x'] + first_result['width'] // 2
                click_task1.params['y'] = first_result['y'] + first_result['height'] // 2
                
                # Update second click task with second button coordinates
                second_result = task.result[1]
                click_task2.params['x'] = second_result['x'] + second_result['width'] // 2
                click_task2.params['y'] = second_result['y'] + second_result['height'] // 2
        
        detect_task.add_completion_callback(update_click_coordinates)
        
        # Add tasks to automation service
        self.automation_service.add_task(detect_task)
        self.automation_service.add_task(click_task1)
        self.automation_service.add_task(wait_task)
        self.automation_service.add_task(click_task2)
        
        # Start automation
        self.automation_service.start_execution()
        
        # Wait for tasks to complete (with timeout)
        timeout = 2.0  # seconds
        start_time = time.time()
        while (any(task.status != TaskStatus.COMPLETED for task in 
                  [detect_task, click_task1, wait_task, click_task2]) and
               time.time() - start_time < timeout):
            time.sleep(0.1)
        
        # Stop automation
        self.automation_service.stop_execution()
        
        # Verify all tasks completed
        self.assertEqual(detect_task.status, TaskStatus.COMPLETED)
        self.assertEqual(click_task1.status, TaskStatus.COMPLETED)
        self.assertEqual(wait_task.status, TaskStatus.COMPLETED)
        self.assertEqual(click_task2.status, TaskStatus.COMPLETED)
        
        # Verify actions were performed in correct order
        actions = self.actions_service.get_actions()
        self.assertEqual(len(actions), 2)  # Two clicks
        
        # Both should be clicks
        self.assertEqual(actions[0][0], 'click')
        self.assertEqual(actions[1][0], 'click')
        
        # Clicks should be at different positions
        self.assertNotEqual(actions[0][1], actions[1][1])  # Different x positions
    
    def test_event_based_workflow(self):
        """
        Test event-based workflow where system reacts to events.
        
        This test verifies that components can react to events
        from other components.
        """
        # Initialize test
        self.detection_service.set_context({'window_title': self.window_title})
        
        # Track callbacks executed
        callback_executed = {'detection': False, 'game': False, 'task': False}
        
        # Create a callback that reacts to window events
        def on_window_found(event):
            # When window is found, trigger detection
            detection_results = self.detection_service.detect_template(
                template_name="castle",
                confidence_threshold=0.7
            )
            callback_executed['detection'] = True
        
        # Create a callback that reacts to detection events
        def on_detection_completed(event):
            # When detection completes, update game state
            self.game_service.update_current_position()
            callback_executed['game'] = True
        
        # Create a callback that reacts to game state events
        def on_game_state_changed(event):
            # When game state changes, create and execute a task
            if 'coordinates' in event.data:
                click_task = ClickTask("click_castle", 400, 280)
                self.automation_service.execute_task_synchronously(click_task)
                callback_executed['task'] = True
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.WINDOW_FOUND, on_window_found)
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, on_detection_completed)
        self.event_bus.subscribe(EventType.GAME_STATE_CHANGED, on_game_state_changed)
        
        # Trigger the workflow by finding the window
        self.window_service.find_window(self.window_title)
        
        # Short wait to allow all callbacks to execute
        time.sleep(0.5)
        
        # Verify all callbacks were executed
        self.assertTrue(callback_executed['detection'])
        self.assertTrue(callback_executed['game'])
        self.assertTrue(callback_executed['task'])
        
        # Verify actions were performed
        actions = self.actions_service.get_actions()
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0][0], 'click')


if __name__ == '__main__':
    unittest.main() 