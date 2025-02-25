"""
UI Integration Tests

These tests verify that the UI components of the Scout application
integrate correctly with the core services.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
import time
import cv2
import numpy as np

# Add parent directory to path to allow running as standalone
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import PyQt6 for UI testing
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

# Import core services
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.game.game_service import GameService
from scout.core.automation.automation_service import AutomationService
from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.services.service_locator import ServiceLocator

# Import UI components
from scout.ui.main_window import MainWindow
from scout.ui.controllers.main_controller import MainController
from scout.ui.views.detection_tab import DetectionTab
from scout.ui.views.automation_tab import AutomationTab
from scout.ui.views.game_tab import GameTab
from scout.ui.views.settings_tab import SettingsTab


class TestUIIntegration(unittest.TestCase):
    """Test the integration between UI components and core services."""
    
    @classmethod
    def setUpClass(cls):
        """Set up once before all tests."""
        # Create QApplication instance if not exists
        cls.app = QApplication.instance() or QApplication(sys.argv)
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create event bus for communication
        self.event_bus = EventBus()
        
        # Create mock service locator
        self.service_locator = MagicMock(spec=ServiceLocator)
        self.service_locator.get_event_bus.return_value = self.event_bus
        
        # Create core services with mocks
        self.window_service = WindowService(self.service_locator)
        self.detection_service = DetectionService(self.service_locator)
        self.game_service = GameService(self.service_locator)
        self.automation_service = AutomationService(self.service_locator)
        
        # Register services with service locator
        self.service_locator.get_window_service.return_value = self.window_service
        self.service_locator.get_detection_service.return_value = self.detection_service
        self.service_locator.get_game_service.return_value = self.game_service
        self.service_locator.get_automation_service.return_value = self.automation_service
        
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test images
        self.create_test_images()
        
        # Track events
        self.received_events = []
        self.event_bus.subscribe(EventType.SETTINGS_CHANGED, self._on_event)
        self.event_bus.subscribe(EventType.DETECTION_REQUESTED, self._on_event)
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_event)
        self.event_bus.subscribe(EventType.AUTOMATION_STARTED, self._on_event)
        self.event_bus.subscribe(EventType.AUTOMATION_STOPPED, self._on_event)
        
        # Create and show main window for testing
        self.main_controller = MainController(self.service_locator)
        self.main_window = MainWindow(self.main_controller)
        
        # Avoid actually showing the window for unit tests
        # self.main_window.show()

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
        self.main_window.close()
        
    def _on_event(self, event):
        """Store received events for verification."""
        self.received_events.append(event)
    
    def create_test_images(self):
        """Create test images for UI testing."""
        # Create a test screenshot
        self.test_screenshot = np.zeros((600, 800, 3), dtype=np.uint8)
        cv2.rectangle(self.test_screenshot, (50, 50), (100, 100), (0, 255, 0), 2)
        cv2.putText(self.test_screenshot, "Test Window", (200, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Save the test screenshot
        self.screenshot_path = self.temp_path / "test_screenshot.png"
        cv2.imwrite(str(self.screenshot_path), self.test_screenshot)
        
        # Create a test template
        self.test_template = self.test_screenshot[45:105, 45:105].copy()
        self.template_path = self.temp_path / "test_template.png"
        cv2.imwrite(str(self.template_path), self.test_template)

    def test_settings_changes_affect_services(self):
        """
        Test UI-INT-001: Settings changes affect services.
        
        Verify that changes to settings in the UI affect the core services.
        """
        # Access settings tab
        settings_tab = self.main_window.findChild(SettingsTab)
        self.assertIsNotNone(settings_tab, "Settings tab not found")
        
        # Mock settings update function
        original_update_settings = self.main_controller.update_settings
        
        # Create a mock to track settings changes
        settings_updated = False
        
        def mock_update_settings(setting_name, value):
            nonlocal settings_updated
            settings_updated = True
            return original_update_settings(setting_name, value)
            
        self.main_controller.update_settings = mock_update_settings
        
        # Simulate changing a setting
        # This is a minimal example - in reality we'd interact with specific UI elements
        self.main_controller.update_settings("detection_threshold", 0.85)
        
        # Verify settings were updated
        self.assertTrue(settings_updated)
        
        # Verify event was published
        self.assertGreaterEqual(len(self.received_events), 1)
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.SETTINGS_CHANGED, event_types)
        
        # Verify service received the new settings
        # This would depend on specific implementation of how settings are propagated
        # For now, we'll just verify the event was published

    def test_service_events_update_ui(self):
        """
        Test UI-INT-002: Service events update UI.
        
        Verify that events from core services update the UI appropriately.
        """
        # Mock the detection result
        detection_result = {
            "matches": [
                {
                    "template": str(self.template_path),
                    "confidence": 0.95,
                    "rectangle": {"x": 50, "y": 50, "width": 50, "height": 50}
                }
            ],
            "screenshot": str(self.screenshot_path)
        }
        
        # Access detection tab
        detection_tab = self.main_window.findChild(DetectionTab)
        self.assertIsNotNone(detection_tab, "Detection tab not found")
        
        # Record initial state
        initial_state = detection_tab.property("has_results")
        
        # Mock update function to track UI updates
        ui_updated = False
        original_update_detection_results = detection_tab.update_detection_results
        
        def mock_update_detection_results(results):
            nonlocal ui_updated
            ui_updated = True
            detection_tab.setProperty("has_results", True)
            return original_update_detection_results(results)
            
        detection_tab.update_detection_results = mock_update_detection_results
        
        # Publish detection completed event
        self.event_bus.publish(EventType.DETECTION_COMPLETED, {
            "results": detection_result
        })
        
        # Process events to allow UI update
        QApplication.processEvents()
        
        # Verify UI was updated
        self.assertTrue(ui_updated)
        self.assertEqual(detection_tab.property("has_results"), True)

    def test_error_reporting_in_ui(self):
        """
        Test UI-INT-003: Error reporting in UI.
        
        Verify that errors are properly reported in the UI.
        """
        # Create a test error message
        test_error = "Test error message"
        
        # Track error dialog display
        error_dialog_shown = False
        
        # Mock the error dialog
        with patch('scout.ui.main_window.QMessageBox.critical') as mock_error_dialog:
            # Set up the mock to track dialog display
            mock_error_dialog.return_value = 0  # OK button
            
            # Simulate an error event
            self.event_bus.publish(EventType.ERROR_OCCURRED, {
                "message": test_error,
                "severity": "critical"
            })
            
            # Process events to allow UI update
            QApplication.processEvents()
            
            # Verify error dialog was shown
            mock_error_dialog.assert_called_once()
            args, kwargs = mock_error_dialog.call_args
            self.assertIn(test_error, args[2])  # text argument should contain error message

    def test_ui_components_communicate_correctly(self):
        """
        Test that UI components communicate correctly with each other.
        
        Verify that actions in one UI component properly affect other components.
        """
        # Access tabs
        detection_tab = self.main_window.findChild(DetectionTab)
        game_tab = self.main_window.findChild(GameTab)
        
        self.assertIsNotNone(detection_tab, "Detection tab not found")
        self.assertIsNotNone(game_tab, "Game tab not found")
        
        # Set up mock functions to track updates
        detection_tab_updated = False
        game_tab_updated = False
        
        original_detection_update = detection_tab.update_detection_results
        original_game_update = game_tab.update_game_state
        
        def mock_detection_update(results):
            nonlocal detection_tab_updated
            detection_tab_updated = True
            return original_detection_update(results)
            
        def mock_game_update(state):
            nonlocal game_tab_updated
            game_tab_updated = True
            return original_game_update(state)
            
        detection_tab.update_detection_results = mock_detection_update
        game_tab.update_game_state = mock_game_update
        
        # Mock detection result that updates game state
        detection_result = {
            "matches": [
                {
                    "template": str(self.template_path),
                    "confidence": 0.95,
                    "rectangle": {"x": 50, "y": 50, "width": 50, "height": 50},
                    "resource": "gold"
                }
            ],
            "screenshot": str(self.screenshot_path)
        }
        
        # Mock game state
        game_state = {
            "resources": [
                {"name": "gold", "value": 1000}
            ]
        }
        
        # Simulate detection completed event
        self.event_bus.publish(EventType.DETECTION_COMPLETED, {
            "results": detection_result
        })
        
        # Process events
        QApplication.processEvents()
        
        # Verify detection tab was updated
        self.assertTrue(detection_tab_updated)
        
        # Simulate game state updated event
        self.event_bus.publish(EventType.GAME_STATE_UPDATED, {
            "state": game_state
        })
        
        # Process events
        QApplication.processEvents()
        
        # Verify game tab was updated
        self.assertTrue(game_tab_updated)

    def test_ui_triggers_detection(self):
        """
        Test that UI can trigger detection.
        
        Verify that user actions in the UI can trigger detection service.
        """
        # Access detection tab
        detection_tab = self.main_window.findChild(DetectionTab)
        self.assertIsNotNone(detection_tab, "Detection tab not found")
        
        # Mock detection service
        detection_triggered = False
        
        original_detect = self.detection_service.detect
        
        def mock_detect(image_path, strategy, config):
            nonlocal detection_triggered
            detection_triggered = True
            # Return mock result
            return {
                "matches": [
                    {
                        "template": str(self.template_path),
                        "confidence": 0.95,
                        "rectangle": {"x": 50, "y": 50, "width": 50, "height": 50}
                    }
                ]
            }
            
        self.detection_service.detect = mock_detect
        
        # Mock window service to return test screenshot
        self.window_service.capture_window = MagicMock(return_value=str(self.screenshot_path))
        
        # Simulate user triggering detection
        self.main_controller.run_detection()
        
        # Process events
        QApplication.processEvents()
        
        # Verify detection was triggered
        self.assertTrue(detection_triggered)
        
        # Verify event was published
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.DETECTION_REQUESTED, event_types)

    def test_ui_triggers_automation(self):
        """
        Test that UI can trigger automation.
        
        Verify that user actions in the UI can trigger automation service.
        """
        # Access automation tab
        automation_tab = self.main_window.findChild(AutomationTab)
        self.assertIsNotNone(automation_tab, "Automation tab not found")
        
        # Mock automation service
        automation_triggered = False
        
        original_execute_sequence = self.automation_service.execute_sequence
        
        def mock_execute_sequence(sequence, continue_on_error=False):
            nonlocal automation_triggered
            automation_triggered = True
            # Simulate sequence execution
            self.event_bus.publish(EventType.AUTOMATION_STARTED, {
                "sequence_name": "Test Sequence"
            })
            return True
            
        self.automation_service.execute_sequence = mock_execute_sequence
        
        # Simulate user triggering automation
        self.main_controller.run_automation()
        
        # Process events
        QApplication.processEvents()
        
        # Verify automation was triggered
        self.assertTrue(automation_triggered)
        
        # Verify event was published
        event_types = [e.type for e in self.received_events]
        self.assertIn(EventType.AUTOMATION_STARTED, event_types)


if __name__ == "__main__":
    unittest.main() 