"""
WindowService and DetectionService Integration Tests

This module contains integration tests that verify the interaction between
the WindowService and DetectionService components.
"""

import unittest
import os
import tempfile
import shutil
import cv2
import numpy as np
from unittest.mock import MagicMock, patch

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy


class TestWindowDetectionIntegration(unittest.TestCase):
    """
    Integration tests for WindowService and DetectionService.
    
    These tests verify that:
    1. WindowService can provide screenshots to DetectionService
    2. DetectionService can process screenshots from WindowService
    3. Events are properly published between the two components
    """
    
    def setUp(self):
        """Set up test fixture."""
        # Create event bus
        self.event_bus = EventBus()
        
        # Set up event listener to track events
        self.received_events = []
        self.event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_detection_event)
        self.event_bus.subscribe(EventType.DETECTION_FAILED, self._on_detection_event)
        
        # Create temporary directory for templates
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, 'templates')
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Create a test template image
        self.test_template_path = os.path.join(self.templates_dir, 'test_button.png')
        self._create_test_template()
        
        # Create a mock window service with a fixed test image
        self.window_service = self._create_mock_window_service()
        
        # Create actual detection service with template strategy
        template_strategy = TemplateMatchingStrategy(templates_dir=self.templates_dir)
        self.detection_service = DetectionService(self.event_bus, self.window_service)
        self.detection_service.register_strategy('template', template_strategy)
    
    def tearDown(self):
        """Clean up after the test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def _on_detection_event(self, event):
        """Store received events for later verification."""
        self.received_events.append(event)
    
    def _create_test_template(self):
        """Create a simple test template image."""
        # Create a 50x50 template with a red square
        template = np.zeros((50, 50, 3), dtype=np.uint8)
        template[10:40, 10:40] = [0, 0, 255]  # Red square in BGR
        cv2.imwrite(self.test_template_path, template)
    
    def _create_mock_window_service(self):
        """Create a mock window service that returns a test screenshot."""
        # Create WindowService with mocked find_window and capture methods
        window_service = WindowService(self.event_bus)
        
        # Create a 200x200 test image with the template in the center
        test_image = np.zeros((200, 200, 3), dtype=np.uint8)
        test_image[75:125, 75:125] = [0, 0, 255]  # Red square in BGR
        
        # Mock the capture_screenshot method
        window_service.capture_screenshot = MagicMock(return_value=test_image)
        window_service.find_window = MagicMock(return_value=True)
        window_service.get_window_position = MagicMock(return_value=(0, 0, 200, 200))
        
        return window_service
    
    def test_template_detection_integration(self):
        """
        Test that DetectionService can use WindowService to capture
        and process screenshots with template matching.
        """
        # Configure services
        self.detection_service.set_context({'window_title': 'Test Window'})
        
        # Perform detection
        results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8
        )
        
        # Verify that WindowService was called to capture a screenshot
        self.window_service.capture_screenshot.assert_called_once()
        
        # Verify detection results
        self.assertIsNotNone(results)
        self.assertGreater(len(results), 0)
        
        # Check the first result
        result = results[0]
        self.assertEqual(result['template_name'], 'test_button')
        self.assertGreaterEqual(result['confidence'], 0.8)
        self.assertTrue(70 <= result['x'] <= 80)  # Approximate position
        self.assertTrue(70 <= result['y'] <= 80)  # Approximate position
        
        # Verify that events were published
        self.assertEqual(len(self.received_events), 1)
        event = self.received_events[0]
        self.assertEqual(event.type, EventType.DETECTION_COMPLETED)
    
    def test_detection_with_region(self):
        """
        Test that DetectionService can use WindowService to capture
        and process screenshots within a specific region.
        """
        # Configure services
        self.detection_service.set_context({'window_title': 'Test Window'})
        
        # Define a region that includes the template
        region = {'left': 50, 'top': 50, 'width': 100, 'height': 100}
        
        # Perform detection with region
        results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8,
            region=region
        )
        
        # Verify detection results
        self.assertIsNotNone(results)
        self.assertGreater(len(results), 0)
        
        # Verify that events were published
        self.assertEqual(len(self.received_events), 1)
        event = self.received_events[0]
        self.assertEqual(event.type, EventType.DETECTION_COMPLETED)
    
    def test_detection_with_invalid_region(self):
        """
        Test that DetectionService handles invalid regions correctly.
        """
        # Configure services
        self.detection_service.set_context({'window_title': 'Test Window'})
        
        # Define a region that does NOT include the template
        region = {'left': 0, 'top': 0, 'width': 50, 'height': 50}
        
        # Perform detection with region
        results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8,
            region=region
        )
        
        # Verify no results were found
        self.assertEqual(len(results), 0)
        
        # Verify that events were published
        self.assertEqual(len(self.received_events), 1)
        event = self.received_events[0]
        self.assertEqual(event.type, EventType.DETECTION_COMPLETED)
    
    def test_caching_functionality(self):
        """
        Test that the DetectionService caching works properly.
        """
        # Configure services
        self.detection_service.set_context({'window_title': 'Test Window'})
        
        # Perform first detection with caching enabled
        first_results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8,
            use_cache=True
        )
        
        # Reset the mock to verify it's not called again
        self.window_service.capture_screenshot.reset_mock()
        
        # Perform second detection with caching enabled
        second_results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8,
            use_cache=True
        )
        
        # Verify that WindowService was NOT called for the second detection
        self.window_service.capture_screenshot.assert_not_called()
        
        # Verify both results match
        self.assertEqual(len(first_results), len(second_results))
        
        # Perform third detection with caching disabled
        self.window_service.capture_screenshot.reset_mock()
        third_results = self.detection_service.detect_template(
            template_name='test_button',
            confidence_threshold=0.8,
            use_cache=False
        )
        
        # Verify that WindowService WAS called for the third detection
        self.window_service.capture_screenshot.assert_called_once()
        
        # Verify we still got matching results
        self.assertEqual(len(first_results), len(third_results))


if __name__ == '__main__':
    unittest.main() 