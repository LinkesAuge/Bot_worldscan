"""
Test Overlay View

This module contains tests for the OverlayView class, which provides 
a transparent overlay for real-time visualization of detection results.
"""

import unittest
from unittest.mock import MagicMock, patch
import pytest
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import QApplication

from scout.ui.views.overlay_view import OverlayView, DetectionMarker, VisualizationStyle
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface

# Initialize QApplication for tests
app = QApplication([])

class TestOverlayView(unittest.TestCase):
    """Test suite for the OverlayView class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Mock window service
        self.window_service = MagicMock(spec=WindowServiceInterface)
        self.window_service.get_window_rect.return_value = QRect(100, 100, 800, 600)
        
        # Mock detection service
        self.detection_service = MagicMock(spec=DetectionServiceInterface)
        
        # Create overlay view
        self.overlay = OverlayView(self.window_service, self.detection_service)
    
    def tearDown(self):
        """Clean up after each test."""
        self.overlay.hide_overlay()
        self.overlay.deleteLater()
    
    def test_initialization(self):
        """Test that overlay view initializes correctly."""
        self.assertIsNotNone(self.overlay)
        self.assertEqual(self.overlay.window_service, self.window_service)
        self.assertEqual(self.overlay.detection_service, self.detection_service)
        self.assertFalse(self.overlay._active)
        self.assertEqual(self.overlay._min_confidence, 0.0)
        
        # Check strategy visibility defaults
        self.assertTrue(self.overlay._visible_strategies.get('template', False))
        self.assertTrue(self.overlay._visible_strategies.get('ocr', False))
        self.assertTrue(self.overlay._visible_strategies.get('yolo', False))
    
    def test_show_over_game(self):
        """Test showing overlay over the game window."""
        # Test successful show
        result = self.overlay.show_over_game()
        self.assertTrue(result)
        self.assertTrue(self.overlay._active)
        self.assertEqual(self.overlay.geometry(), self.window_service.get_window_rect())
        
        # Test failure when window not found
        self.window_service.get_window_rect.return_value = None
        result = self.overlay.show_over_game()
        self.assertFalse(result)
    
    def test_hide_overlay(self):
        """Test hiding the overlay."""
        # First show the overlay
        self.overlay.show_over_game()
        self.assertTrue(self.overlay._active)
        
        # Then hide it
        self.overlay.hide_overlay()
        self.assertFalse(self.overlay._active)
        self.assertFalse(self.overlay.isVisible())
    
    def test_toggle_visibility(self):
        """Test toggling overlay visibility."""
        # Initially not active
        self.assertFalse(self.overlay._active)
        
        # Toggle to show
        result = self.overlay.toggle_visibility()
        self.assertTrue(result)
        self.assertTrue(self.overlay._active)
        
        # Toggle to hide
        result = self.overlay.toggle_visibility()
        self.assertFalse(result)
        self.assertFalse(self.overlay._active)
    
    def test_control_bar_toggle(self):
        """Test toggling the control bar."""
        # Control bar should be initially hidden
        self.assertFalse(self.overlay.control_bar.isVisible())
        
        # Toggle to show
        self.overlay.toggle_control_bar()
        self.assertTrue(self.overlay.control_bar.isVisible())
        
        # Toggle to hide
        self.overlay.toggle_control_bar()
        self.assertFalse(self.overlay.control_bar.isVisible())
    
    def test_set_strategy_visibility(self):
        """Test setting strategy visibility."""
        # Set template strategy to invisible
        self.overlay.set_strategy_visibility('template', False)
        self.assertFalse(self.overlay._visible_strategies['template'])
        
        # Set OCR strategy to visible
        self.overlay.set_strategy_visibility('ocr', True)
        self.assertTrue(self.overlay._visible_strategies['ocr'])
    
    def test_set_min_confidence(self):
        """Test setting minimum confidence threshold."""
        # Set valid confidence
        self.overlay.set_min_confidence(0.5)
        self.assertEqual(self.overlay._min_confidence, 0.5)
        self.assertEqual(self.overlay.confidence_slider.value(), 50)
        self.assertEqual(self.overlay.confidence_value.text(), "0.50")
        
        # Set invalid confidence (should be clamped)
        self.overlay.set_min_confidence(1.5)
        self.assertEqual(self.overlay._min_confidence, 0.5)  # Unchanged
    
    def test_detection_results_filtering(self):
        """Test filtering of detection results by strategy and confidence."""
        # Prepare test data
        results = [
            {'x': 10, 'y': 20, 'width': 30, 'height': 40, 'label': 'Test1', 'confidence': 0.3},
            {'x': 50, 'y': 60, 'width': 30, 'height': 40, 'label': 'Test2', 'confidence': 0.7},
            {'x': 90, 'y': 100, 'width': 30, 'height': 40, 'label': 'Test3', 'confidence': 0.9}
        ]
        
        # Show overlay and set confidence threshold
        self.overlay.show_over_game()
        self.overlay.set_min_confidence(0.5)
        
        # Add detection results
        self.overlay.set_detection_results(results, 'template')
        
        # Give time for batch processing
        QApplication.processEvents()
        
        # Only 2 of 3 markers should be added (confidence >= 0.5)
        self.assertEqual(len([m for m in self.overlay._markers if isinstance(m, DetectionMarker)]), 2)
        
        # Test strategy filtering
        self.overlay.set_strategy_visibility('template', False)
        self.overlay.set_detection_results(results, 'template')
        
        # Give time for batch processing
        QApplication.processEvents()
        
        # No markers should be visible for template strategy
        visible_markers = [m for m in self.overlay._markers 
                          if isinstance(m, DetectionMarker) and m.isVisible()]
        self.assertEqual(len(visible_markers), 0)
    
    def test_performance_optimization(self):
        """Test performance optimization based on marker count."""
        # Create a small number of markers
        for i in range(5):
            self.overlay._markers.append(MagicMock())
        
        # Run optimization
        self.overlay.optimize_performance()
        
        # Check settings for small number of markers
        self.assertEqual(self.overlay._batch_size, 10)
        self.assertEqual(self.overlay._update_throttle_ms, 100)
        
        # Create many more markers
        for i in range(100):
            self.overlay._markers.append(MagicMock())
        
        # Run optimization again
        self.overlay.optimize_performance()
        
        # Check settings for large number of markers
        self.assertEqual(self.overlay._batch_size, 3)
        self.assertEqual(self.overlay._update_throttle_ms, 300)


class TestDetectionMarker(unittest.TestCase):
    """Test suite for the DetectionMarker class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a detection marker
        self.marker = DetectionMarker(10, 20, 30, 40, "Test", 0.8, "template")
    
    def test_initialization(self):
        """Test that detection marker initializes correctly."""
        self.assertEqual(self.marker.x(), 10)
        self.assertEqual(self.marker.y(), 20)
        self.assertEqual(self.marker.rect().width(), 30)
        self.assertEqual(self.marker.rect().height(), 40)
        self.assertEqual(self.marker.label, "Test")
        self.assertEqual(self.marker.confidence, 0.8)
        self.assertEqual(self.marker.strategy, "template")
        self.assertFalse(self.marker.selected)
    
    def test_strategy_specific_styling(self):
        """Test that markers have different styles based on detection strategy."""
        # Create markers with different strategies
        template_marker = DetectionMarker(10, 20, 30, 40, "Template", 0.8, "template")
        ocr_marker = DetectionMarker(10, 20, 30, 40, "OCR", 0.8, "ocr")
        yolo_marker = DetectionMarker(10, 20, 30, 40, "YOLO", 0.8, "yolo")
        
        # Check that the markers have different colors
        self.assertNotEqual(template_marker.pen().color(), ocr_marker.pen().color())
        self.assertNotEqual(template_marker.pen().color(), yolo_marker.pen().color())
        self.assertNotEqual(ocr_marker.pen().color(), yolo_marker.pen().color())
    
    def test_confidence_styling(self):
        """Test that markers have different styles based on confidence."""
        # Create markers with different confidence levels
        low_conf_marker = DetectionMarker(10, 20, 30, 40, "Low", 0.3, "template")
        high_conf_marker = DetectionMarker(10, 20, 30, 40, "High", 0.9, "template")
        
        # Check that the markers have different colors
        self.assertNotEqual(low_conf_marker.pen().color(), high_conf_marker.pen().color())


if __name__ == '__main__':
    unittest.main() 