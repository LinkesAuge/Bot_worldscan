"""
Unit tests for the ControlPanelWidget.

This module contains tests to verify the functionality of the ControlPanelWidget.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QEvent

from scout.ui.widgets.control_panel_widget import ControlPanelWidget
from scout.ui.main_window import ServiceLocator
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.core.game.game_state_service_interface import GameStateServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface


class TestControlPanelWidget(unittest.TestCase):
    """Test cases for the ControlPanelWidget."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test class."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
    
    def setUp(self):
        """Set up the test case."""
        # Create mock services
        self.mock_detection_service = MagicMock(spec=DetectionServiceInterface)
        self.mock_automation_service = MagicMock(spec=AutomationServiceInterface)
        self.mock_game_state_service = MagicMock(spec=GameStateServiceInterface)
        self.mock_window_service = MagicMock(spec=WindowServiceInterface)
        
        # Register mock services with ServiceLocator
        # Use patch to temporarily replace the get method of ServiceLocator
        self.service_locator_patcher = patch('scout.ui.main_window.ServiceLocator.get')
        self.mock_service_locator_get = self.service_locator_patcher.start()
        
        # Configure mock to return appropriate services based on interface
        def side_effect(interface):
            if interface == DetectionServiceInterface:
                return self.mock_detection_service
            elif interface == AutomationServiceInterface:
                return self.mock_automation_service
            elif interface == GameStateServiceInterface:
                return self.mock_game_state_service
            elif interface == WindowServiceInterface:
                return self.mock_window_service
            return None
        
        self.mock_service_locator_get.side_effect = side_effect
        
        # Create control panel widget
        self.control_panel = ControlPanelWidget()
    
    def tearDown(self):
        """Clean up after the test case."""
        # Stop patcher
        self.service_locator_patcher.stop()
        
        # Cleanup widget
        self.control_panel.deleteLater()
    
    def test_initialization(self):
        """Test that the control panel initializes correctly."""
        # Verify that the widget exists and has the correct type
        self.assertIsInstance(self.control_panel, ControlPanelWidget)
        
        # Verify that the current context is 'default'
        self.assertEqual(self.control_panel.current_context, "default")
        
        # Verify that the control panel has buttons for start, stop, and pause
        self.assertIsNotNone(self.control_panel.start_button)
        self.assertIsNotNone(self.control_panel.stop_button)
        self.assertIsNotNone(self.control_panel.pause_button)
        
        # Verify that the status label is set to "Ready"
        self.assertEqual(self.control_panel.status_label.text(), "Ready")
    
    def test_context_switching(self):
        """Test that the control panel can switch contexts."""
        # Test switching to each context
        for context in ["detection", "automation", "game_state", "default"]:
            # Switch context
            self.control_panel.set_context(context)
            
            # Verify that the current context is set correctly
            self.assertEqual(self.control_panel.current_context, context)
            
            # Verify that the current widget in the stack is the correct one
            self.assertEqual(self.control_panel.context_stack.currentWidget(), 
                             self.control_panel.context_panels[context])
    
    def test_set_status(self):
        """Test that the status label can be updated."""
        # Test updating status
        test_status = "Testing status"
        self.control_panel.set_status(test_status)
        
        # Verify that the status label is updated
        self.assertEqual(self.control_panel.status_label.text(), test_status)
    
    def test_action_enabled(self):
        """Test that actions can be enabled and disabled."""
        # Get an action
        action_id = "screenshot"
        self.assertIn(action_id, self.control_panel.actions)
        
        # Enable the action
        self.control_panel.set_action_enabled(action_id, True)
        self.assertTrue(self.control_panel.actions[action_id].isEnabled())
        
        # Disable the action
        self.control_panel.set_action_enabled(action_id, False)
        self.assertFalse(self.control_panel.actions[action_id].isEnabled())
    
    def test_action_checked(self):
        """Test that checkable actions can be checked and unchecked."""
        # Get a checkable action
        action_id = "toggle_overlay"
        self.assertIn(action_id, self.control_panel.actions)
        self.assertTrue(self.control_panel.actions[action_id].isCheckable())
        
        # Check the action
        self.control_panel.set_action_checked(action_id, True)
        self.assertTrue(self.control_panel.actions[action_id].isChecked())
        
        # Uncheck the action
        self.control_panel.set_action_checked(action_id, False)
        self.assertFalse(self.control_panel.actions[action_id].isChecked())
    
    def test_action_triggered(self):
        """Test that action signals are emitted correctly."""
        # Create a mock handler
        mock_handler = MagicMock()
        
        # Connect mock handler to action_triggered signal
        self.control_panel.action_triggered.connect(mock_handler)
        
        # Test action triggering
        action_id = "start"
        
        # Click the start button to trigger the action
        self.control_panel.start_button.click()
        
        # Verify that the handler was called with the correct action ID
        mock_handler.assert_called_once_with(action_id)
    
    def test_register_action_handler(self):
        """Test that action handlers can be registered."""
        # Create a mock handler
        mock_handler = MagicMock()
        
        # Register handler for a specific action
        action_id = "screenshot"
        self.control_panel.register_action_handler(action_id, mock_handler)
        
        # Emit the action_triggered signal with the action ID
        self.control_panel._on_action_triggered(action_id)
        
        # Verify that the handler was called
        mock_handler.assert_called_once()
        
        # Test that the handler is not called for other action IDs
        mock_handler.reset_mock()
        self.control_panel._on_action_triggered("different_action")
        mock_handler.assert_not_called()
    
    def test_detection_context_panel(self):
        """Test the detection context panel functionality."""
        # Switch to detection context
        self.control_panel.set_context("detection")
        
        # Verify that the detection panel has radio buttons for detection types
        detection_panel = self.control_panel.context_panels["detection"]
        
        # Find radio buttons in the panel
        template_radio = None
        ocr_radio = None
        yolo_radio = None
        
        # This is a simplified way to find the radio buttons - in a real test,
        # you might use Qt's test framework to navigate the widget hierarchy
        for child in detection_panel.findChildren(object):
            if hasattr(child, 'text'):
                if child.text() == "Template":
                    template_radio = child
                elif child.text() == "OCR":
                    ocr_radio = child
                elif child.text() == "YOLO":
                    yolo_radio = child
        
        # Verify that the radio buttons exist
        self.assertIsNotNone(template_radio)
        self.assertIsNotNone(ocr_radio)
        self.assertIsNotNone(yolo_radio)
        
        # Verify that the Template radio button is checked by default
        self.assertTrue(template_radio.isChecked())
        self.assertFalse(ocr_radio.isChecked())
        self.assertFalse(yolo_radio.isChecked())
    
    def test_automation_context_panel(self):
        """Test the automation context panel functionality."""
        # Switch to automation context
        self.control_panel.set_context("automation")
        
        # Verify that the automation panel has the sequence control buttons
        automation_panel = self.control_panel.context_panels["automation"]
        
        # Find buttons in the panel
        run_sequence_btn = None
        simulation_btn = None
        
        # This is a simplified way to find the buttons - in a real test,
        # you might use Qt's test framework to navigate the widget hierarchy
        for child in automation_panel.findChildren(object):
            if hasattr(child, 'text'):
                if child.text() == "Run Sequence":
                    run_sequence_btn = child
                elif child.text() == "Run Simulation":
                    simulation_btn = child
        
        # Verify that the buttons exist
        self.assertIsNotNone(run_sequence_btn)
        self.assertIsNotNone(simulation_btn)
    
    def test_game_state_context_panel(self):
        """Test the game state context panel functionality."""
        # Switch to game state context
        self.control_panel.set_context("game_state")
        
        # Verify that the game state panel has the state control buttons
        game_state_panel = self.control_panel.context_panels["game_state"]
        
        # Find buttons in the panel
        update_state_btn = None
        reset_state_btn = None
        
        # This is a simplified way to find the buttons - in a real test,
        # you might use Qt's test framework to navigate the widget hierarchy
        for child in game_state_panel.findChildren(object):
            if hasattr(child, 'text'):
                if child.text() == "Update State":
                    update_state_btn = child
                elif child.text() == "Reset State":
                    reset_state_btn = child
        
        # Verify that the buttons exist
        self.assertIsNotNone(update_state_btn)
        self.assertIsNotNone(reset_state_btn)


if __name__ == "__main__":
    unittest.main() 