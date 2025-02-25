"""
Window-Detection Integration Tests

These tests verify that the Window Service and Detection Service
components integrate correctly and work together properly.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
import cv2
import numpy as np

# Add parent directory to path to allow running as standalone
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from scout.core.window.window_service import WindowService
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateStrategy
from scout.core.events.event_bus import EventBus
from scout.core.services.service_locator import ServiceLocator


class TestWindowDetectionIntegration(unittest.TestCase):
    """Test the integration between WindowService and DetectionService."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create event bus
        self.event_bus = EventBus()
        
        # Create mock service locator
        self.service_locator = MagicMock(spec=ServiceLocator)
        self.service_locator.get_event_bus.return_value = self.event_bus
        
        # Create window service
        self.window_service = WindowService(self.service_locator)
        
        # Create detection service with real template strategy
        self.detection_service = DetectionService(self.service_locator)
        self.detection_service.register_strategy("template", TemplateStrategy())
        
        # Mock service locator to return our services
        self.service_locator.get_window_service.return_value = self.window_service
        self.service_locator.get_detection_service.return_value = self.detection_service
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test image and template
        self.create_test_images()

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()

    def create_test_images(self):
        """Create test image and template for detection."""
        # Create a test window capture image (500x300 with a rectangle)
        self.window_image = np.zeros((300, 500, 3), dtype=np.uint8)
        cv2.rectangle(self.window_image, (50, 50), (150, 100), (0, 255, 0), 3)
        cv2.putText(self.window_image, "Test Window", (200, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Save the window image
        self.window_image_path = self.temp_path / "window_capture.png"
        cv2.imwrite(str(self.window_image_path), self.window_image)
        
        # Create a template from the rectangle in the window image
        self.template_image = self.window_image[45:105, 45:155].copy()
        
        # Save the template image
        self.template_path = self.temp_path / "template.png"
        cv2.imwrite(str(self.template_path), self.template_image)

    def test_basic_window_capture_to_detection_flow(self):
        """
        Test WD-INT-001: Basic window capture to detection flow.
        
        Verify that a window can be captured and used for detection.
        """
        # Mock window service to return our test image
        with patch.object(self.window_service, 'capture_window', return_value=str(self.window_image_path)):
            # Select a window
            window_handle = 12345  # Dummy window handle
            self.window_service.select_window(window_handle)
            
            # Capture window
            capture_path = self.window_service.capture_window()
            self.assertEqual(capture_path, str(self.window_image_path))
            
            # Run template detection
            detection_config = {
                "templates": [str(self.template_path)],
                "threshold": 0.8,
                "limit": 1,
                "visualize": False
            }
            
            detection_results = self.detection_service.detect(
                capture_path, 
                strategy="template",
                config=detection_config
            )
            
            # Verify detection results
            self.assertIsNotNone(detection_results)
            self.assertIn("matches", detection_results)
            self.assertEqual(len(detection_results["matches"]), 1)
            
            # Verify match details
            match = detection_results["matches"][0]
            self.assertIn("confidence", match)
            self.assertIn("rectangle", match)
            self.assertGreaterEqual(match["confidence"], 0.8)

    def test_window_resize_handling(self):
        """
        Test WD-INT-002: Window resize handling.
        
        Verify that detection correctly handles resized windows.
        """
        # Create a resized version of the window image (different dimensions)
        resized_window = cv2.resize(self.window_image, (750, 450))
        resized_path = self.temp_path / "window_resized.png"
        cv2.imwrite(str(resized_path), resized_window)
        
        # Mock window service to return our resized image
        with patch.object(self.window_service, 'capture_window', return_value=str(resized_path)):
            # Select and capture window
            self.window_service.select_window(12345)
            capture_path = self.window_service.capture_window()
            
            # Run template detection with multi-scale
            detection_config = {
                "templates": [str(self.template_path)],
                "threshold": 0.7,  # Lower threshold for scale differences
                "limit": 1,
                "visualize": False,
                "multi_scale": True,  # Enable multi-scale detection
                "scale_range": (0.5, 1.5),  # Scale range to accommodate resized window
                "scale_steps": 5  # Number of scales to try
            }
            
            detection_results = self.detection_service.detect(
                capture_path, 
                strategy="template",
                config=detection_config
            )
            
            # Verify detection results
            self.assertIsNotNone(detection_results)
            self.assertIn("matches", detection_results)
            self.assertGreaterEqual(len(detection_results["matches"]), 1)
            
            # Verify at least one good match
            self.assertGreaterEqual(detection_results["matches"][0]["confidence"], 0.7)

    def test_window_lost_handling(self):
        """
        Test WD-INT-003: Window lost handling.
        
        Verify appropriate error handling when a window is lost.
        """
        # First select a window
        self.window_service.select_window(12345)
        
        # Mock window service to raise an exception (window lost)
        with patch.object(self.window_service, 'capture_window', 
                         side_effect=ValueError("Window not found")):
            
            # Attempt to run detection (should handle the exception)
            try:
                # Capture window (should raise exception)
                capture_path = self.window_service.capture_window()
                
                # This code should not be reached
                self.fail("Expected ValueError was not raised")
            except ValueError as e:
                self.assertEqual(str(e), "Window not found")
                
                # Now verify detection service handles this properly
                with self.assertRaises(ValueError):
                    detection_config = {
                        "templates": [str(self.template_path)],
                        "threshold": 0.8
                    }
                    
                    # This should propagate the error or handle it gracefully
                    self.detection_service.detect(
                        "nonexistent_path.png",  # This path doesn't exist
                        strategy="template",
                        config=detection_config
                    )

    def test_detection_visualization_integration(self):
        """
        Test detection results visualization integration.
        
        Verify that detection results can be visualized on the captured window.
        """
        # Mock window service to return our test image
        with patch.object(self.window_service, 'capture_window', return_value=str(self.window_image_path)):
            # Select and capture window
            self.window_service.select_window(12345)
            capture_path = self.window_service.capture_window()
            
            # Run template detection with visualization
            visualization_path = self.temp_path / "visualization.png"
            
            detection_config = {
                "templates": [str(self.template_path)],
                "threshold": 0.8,
                "limit": 1,
                "visualize": True,
                "visualization_path": str(visualization_path)
            }
            
            detection_results = self.detection_service.detect(
                capture_path, 
                strategy="template",
                config=detection_config
            )
            
            # Verify detection results include visualization
            self.assertIsNotNone(detection_results)
            self.assertIn("visualization", detection_results)
            self.assertEqual(detection_results["visualization"], str(visualization_path))
            
            # Verify the visualization file exists
            self.assertTrue(visualization_path.exists())
            
            # Load and verify the visualization image
            viz_image = cv2.imread(str(visualization_path))
            self.assertIsNotNone(viz_image)
            self.assertEqual(viz_image.shape[:2], self.window_image.shape[:2])

    def test_multiple_template_detection(self):
        """
        Test detection with multiple templates.
        
        Verify that multiple templates can be detected in a single window.
        """
        # Create a second template (the text part of the window)
        text_template = self.window_image[140:160, 195:320].copy()
        text_template_path = self.temp_path / "text_template.png"
        cv2.imwrite(str(text_template_path), text_template)
        
        # Mock window service to return our test image
        with patch.object(self.window_service, 'capture_window', return_value=str(self.window_image_path)):
            # Select and capture window
            self.window_service.select_window(12345)
            capture_path = self.window_service.capture_window()
            
            # Run template detection with multiple templates
            detection_config = {
                "templates": [str(self.template_path), str(text_template_path)],
                "threshold": 0.7,
                "limit": 5,  # Allow multiple matches
                "visualize": False
            }
            
            detection_results = self.detection_service.detect(
                capture_path, 
                strategy="template",
                config=detection_config
            )
            
            # Verify detection results
            self.assertIsNotNone(detection_results)
            self.assertIn("matches", detection_results)
            
            # Should find at least 2 matches (one for each template)
            self.assertGreaterEqual(len(detection_results["matches"]), 2)


if __name__ == "__main__":
    unittest.main() 