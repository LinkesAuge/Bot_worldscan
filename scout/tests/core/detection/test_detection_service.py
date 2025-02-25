"""
Tests for the Detection Service.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import numpy as np
import os
import time
import tempfile

from scout.core.events.event_bus import EventBus
from scout.core.events.event import Event
from scout.core.detection.detection_service import DetectionService
from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy
from scout.core.detection.strategies.ocr_strategy import OCRStrategy
from scout.core.detection.strategies.yolo_strategy import YOLOStrategy


class TestDetectionService(unittest.TestCase):
    """
    Test suite for the Detection Service.
    
    These tests mock the underlying dependencies to isolate the
    detection service functionality.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_window_service = MagicMock()
        self.mock_event_bus = MagicMock(spec=EventBus)
        
        # Create sample image for testing
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        
        # Set up screenshot return value
        self.mock_window_service.capture_screenshot.return_value = self.test_image
        
        # Create temp directory for templates
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create detection service
        self.detection_service = DetectionService(
            window_service=self.mock_window_service,
            event_bus=self.mock_event_bus
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()
    
    @patch('scout.core.detection.strategies.template_strategy.TemplateMatchingStrategy')
    def test_register_template_strategy(self, mock_template_strategy_class):
        """Test registering a template matching strategy."""
        # Mock template strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'template'
        mock_template_strategy_class.return_value = mock_strategy
        
        # Register template strategy
        self.detection_service.register_template_strategy(self.temp_dir.name)
        
        # Verify strategy was registered
        self.assertIn('template', self.detection_service.get_available_strategies())
        
        # Verify template strategy was created with correct parameters
        mock_template_strategy_class.assert_called_once_with(self.temp_dir.name)
    
    @patch('scout.core.detection.strategies.ocr_strategy.OCRStrategy')
    def test_register_ocr_strategy(self, mock_ocr_strategy_class):
        """Test registering an OCR strategy."""
        # Mock OCR strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'ocr'
        mock_ocr_strategy_class.return_value = mock_strategy
        
        # Register OCR strategy
        self.detection_service.register_ocr_strategy()
        
        # Verify strategy was registered
        self.assertIn('ocr', self.detection_service.get_available_strategies())
        
        # Verify OCR strategy was created
        mock_ocr_strategy_class.assert_called_once()
    
    @patch('scout.core.detection.strategies.yolo_strategy.YOLOStrategy')
    def test_register_yolo_strategy(self, mock_yolo_strategy_class):
        """Test registering a YOLO strategy."""
        # Mock YOLO strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'yolo'
        mock_yolo_strategy_class.return_value = mock_strategy
        
        # Create a temporary model file
        model_path = os.path.join(self.temp_dir.name, "model.weights")
        with open(model_path, 'w') as f:
            f.write("fake model data")
        
        # Register YOLO strategy
        self.detection_service.register_yolo_strategy(
            model_path=model_path,
            framework='opencv'
        )
        
        # Verify strategy was registered
        self.assertIn('yolo', self.detection_service.get_available_strategies())
        
        # Verify YOLO strategy was created with correct parameters
        mock_yolo_strategy_class.assert_called_once_with(
            model_path=model_path,
            config_path=None,
            class_names_path=None,
            framework='opencv'
        )
    
    def test_detect_unknown_strategy(self):
        """Test detecting with an unknown strategy."""
        with self.assertRaises(ValueError):
            self.detection_service.detect('unknown', self.test_image)
    
    def test_detect_with_custom_strategy(self):
        """Test detecting with a custom strategy."""
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'custom'
        mock_strategy.detect.return_value = [{'type': 'test', 'x': 10, 'y': 20}]
        
        # Register mock strategy
        self.detection_service.register_strategy(mock_strategy)
        
        # Perform detection
        results = self.detection_service.detect('custom', self.test_image)
        
        # Verify strategy was called
        mock_strategy.detect.assert_called_once_with(self.test_image, {})
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'test')
        
        # Verify event was published
        self.mock_event_bus.publish.assert_called_once()
    
    def test_detect_with_region(self):
        """Test detecting with a region specification."""
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'custom'
        mock_strategy.detect.return_value = [{'type': 'test', 'x': 10, 'y': 20}]
        
        # Register mock strategy
        self.detection_service.register_strategy(mock_strategy)
        
        # Define region
        region = {'left': 50, 'top': 40, 'width': 100, 'height': 60}
        
        # Perform detection without providing image (should use window service)
        results = self.detection_service.detect('custom', region=region)
        
        # Verify window service was called with region
        self.mock_window_service.capture_screenshot.assert_called_once_with(
            region=(50, 40, 100, 60)
        )
        
        # Verify strategy was called with parameters
        mock_strategy.detect.assert_called_once_with(self.test_image, {})
        
        # Verify results
        self.assertEqual(len(results), 1)
    
    def test_detect_without_image(self):
        """Test detecting without providing an image."""
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'custom'
        mock_strategy.detect.return_value = [{'type': 'test', 'x': 10, 'y': 20}]
        
        # Register mock strategy
        self.detection_service.register_strategy(mock_strategy)
        
        # Perform detection without providing image
        results = self.detection_service.detect('custom')
        
        # Verify window service was called to capture screenshot
        self.mock_window_service.capture_screenshot.assert_called_once()
        
        # Verify strategy was called with captured image
        mock_strategy.detect.assert_called_once_with(self.test_image, {})
        
        # Verify results
        self.assertEqual(len(results), 1)
    
    def test_detect_with_caching(self):
        """Test detection result caching."""
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'custom'
        mock_strategy.detect.return_value = [{'type': 'test', 'x': 10, 'y': 20}]
        
        # Register mock strategy
        self.detection_service.register_strategy(mock_strategy)
        
        # Set a longer cache timeout for testing
        self.detection_service.set_cache_timeout(10.0)
        
        # Perform detection twice
        results1 = self.detection_service.detect('custom', self.test_image, use_cache=True)
        results2 = self.detection_service.detect('custom', self.test_image, use_cache=True)
        
        # Verify strategy was called only once
        mock_strategy.detect.assert_called_once()
        
        # Verify results
        self.assertEqual(results1, results2)
        
        # Clear cache
        self.detection_service.clear_cache()
        
        # Perform detection again
        results3 = self.detection_service.detect('custom', self.test_image, use_cache=True)
        
        # Verify strategy was called again
        self.assertEqual(mock_strategy.detect.call_count, 2)
    
    def test_detect_without_caching(self):
        """Test detection without caching."""
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'custom'
        mock_strategy.detect.return_value = [{'type': 'test', 'x': 10, 'y': 20}]
        
        # Register mock strategy
        self.detection_service.register_strategy(mock_strategy)
        
        # Perform detection twice without caching
        results1 = self.detection_service.detect('custom', self.test_image, use_cache=False)
        results2 = self.detection_service.detect('custom', self.test_image, use_cache=False)
        
        # Verify strategy was called twice
        self.assertEqual(mock_strategy.detect.call_count, 2)
    
    @patch('scout.core.detection.strategies.template_strategy.TemplateMatchingStrategy')
    def test_detect_template(self, mock_template_strategy_class):
        """Test template detection convenience method."""
        # Mock template strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'template'
        mock_strategy.detect.return_value = [{'type': 'template', 'template_name': 'button', 'x': 10, 'y': 20}]
        mock_template_strategy_class.return_value = mock_strategy
        
        # Register template strategy
        self.detection_service.register_template_strategy(self.temp_dir.name)
        
        # Perform template detection
        results = self.detection_service.detect_template('button', self.test_image)
        
        # Verify strategy was called with correct parameters
        mock_strategy.detect.assert_called_once()
        call_args = mock_strategy.detect.call_args[0]
        call_params = mock_strategy.detect.call_args[0][1]
        
        # Verify parameters
        self.assertEqual(call_params['template_names'], ['button'])
        self.assertEqual(call_params['confidence_threshold'], 0.8)
        self.assertEqual(call_params['max_matches'], 10)
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['template_name'], 'button')
    
    @patch('scout.core.detection.strategies.ocr_strategy.OCRStrategy')
    def test_detect_text(self, mock_ocr_strategy_class):
        """Test text detection convenience method."""
        # Mock OCR strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'ocr'
        mock_strategy.detect.return_value = [{'type': 'text', 'text': 'Hello', 'x': 10, 'y': 20}]
        mock_ocr_strategy_class.return_value = mock_strategy
        
        # Register OCR strategy
        self.detection_service.register_ocr_strategy()
        
        # Perform text detection with pattern
        results = self.detection_service.detect_text(
            self.test_image, 
            pattern='Hello', 
            confidence_threshold=50
        )
        
        # Verify strategy was called with correct parameters
        mock_strategy.detect.assert_called_once()
        call_params = mock_strategy.detect.call_args[0][1]
        
        # Verify parameters
        self.assertEqual(call_params['pattern'], 'Hello')
        self.assertEqual(call_params['confidence_threshold'], 50)
        self.assertEqual(call_params['preprocess'], 'none')
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], 'Hello')
    
    @patch('scout.core.detection.strategies.ocr_strategy.OCRStrategy')
    def test_get_text(self, mock_ocr_strategy_class):
        """Test get_text convenience method."""
        # Mock OCR strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'ocr'
        mock_strategy.get_text.return_value = 'Hello, World!'
        mock_ocr_strategy_class.return_value = mock_strategy
        
        # Register OCR strategy
        self.detection_service.register_ocr_strategy()
        
        # Get text
        text = self.detection_service.get_text(self.test_image)
        
        # Verify strategy was called with correct parameters
        mock_strategy.get_text.assert_called_once()
        
        # Verify result
        self.assertEqual(text, 'Hello, World!')
    
    @patch('scout.core.detection.strategies.yolo_strategy.YOLOStrategy')
    def test_detect_objects(self, mock_yolo_strategy_class):
        """Test object detection convenience method."""
        # Mock YOLO strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'yolo'
        mock_strategy.detect.return_value = [
            {'type': 'object', 'class_id': 0, 'class_name': 'person', 'x': 10, 'y': 20}
        ]
        mock_yolo_strategy_class.return_value = mock_strategy
        
        # Create a temporary model file
        model_path = os.path.join(self.temp_dir.name, "model.weights")
        with open(model_path, 'w') as f:
            f.write("fake model data")
        
        # Register YOLO strategy
        self.detection_service.register_yolo_strategy(model_path=model_path)
        
        # Perform object detection with specific class IDs
        results = self.detection_service.detect_objects(
            class_ids=[0],
            image=self.test_image,
            confidence_threshold=0.6
        )
        
        # Verify strategy was called with correct parameters
        mock_strategy.detect.assert_called_once()
        call_params = mock_strategy.detect.call_args[0][1]
        
        # Verify parameters
        self.assertEqual(call_params['class_ids'], [0])
        self.assertEqual(call_params['confidence_threshold'], 0.6)
        self.assertEqual(call_params['nms_threshold'], 0.4)
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['class_name'], 'person')
    
    @patch('scout.core.detection.strategies.template_strategy.TemplateMatchingStrategy')
    def test_get_template_names(self, mock_template_strategy_class):
        """Test getting template names."""
        # Mock template strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'template'
        mock_strategy.get_template_names.return_value = ['button', 'icon']
        mock_template_strategy_class.return_value = mock_strategy
        
        # Register template strategy
        self.detection_service.register_template_strategy(self.temp_dir.name)
        
        # Get template names
        names = self.detection_service.get_template_names()
        
        # Verify strategy was called
        mock_strategy.get_template_names.assert_called_once()
        
        # Verify result
        self.assertEqual(names, ['button', 'icon'])
    
    @patch('scout.core.detection.strategies.template_strategy.TemplateMatchingStrategy')
    def test_reload_templates(self, mock_template_strategy_class):
        """Test reloading templates."""
        # Mock template strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name.return_value = 'template'
        mock_template_strategy_class.return_value = mock_strategy
        
        # Register template strategy
        self.detection_service.register_template_strategy(self.temp_dir.name)
        
        # Reload templates
        self.detection_service.reload_templates()
        
        # Verify strategy was called
        mock_strategy.reload_templates.assert_called_once()


if __name__ == '__main__':
    unittest.main() 