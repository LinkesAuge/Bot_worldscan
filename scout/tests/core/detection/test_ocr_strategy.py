"""
Tests for the OCR detection strategy.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import numpy as np
import cv2
import os

from scout.core.detection.strategies.ocr_strategy import OCRStrategy


class TestOCRStrategy(unittest.TestCase):
    """
    Test suite for the OCR detection strategy.
    
    These tests mock the pytesseract library to avoid dependency on actual
    Tesseract installation in the test environment.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock for pytesseract
        self.pytesseract_patcher = patch('scout.core.detection.strategies.ocr_strategy.pytesseract')
        self.mock_pytesseract = self.pytesseract_patcher.start()
        
        # Mock the tesseract version check
        self.mock_pytesseract.get_tesseract_version.return_value = '4.1.1'
        
        # Create an OCR strategy instance
        self.ocr_strategy = OCRStrategy()
        
        # Create a sample image for testing
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        # Add some text-like shapes to the image (white rectangle)
        cv2.rectangle(self.test_image, (50, 40), (150, 60), (255, 255, 255), -1)
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.pytesseract_patcher.stop()
    
    def test_initialization(self):
        """Test OCRStrategy initialization."""
        # Test default initialization
        self.assertEqual(self.ocr_strategy.get_name(), "ocr")
        self.assertEqual(self.ocr_strategy.get_required_params(), [])
        
        # Test with custom tesseract path
        custom_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        with patch('scout.core.detection.strategies.ocr_strategy.pytesseract') as mock_tesseract:
            ocr = OCRStrategy(tesseract_cmd=custom_path)
            self.assertEqual(mock_tesseract.pytesseract.tesseract_cmd, custom_path)
    
    def test_detect_basic(self):
        """Test basic text detection functionality."""
        # Mock the pytesseract image_to_data response
        self.mock_pytesseract.Output.DICT = 'DICT'
        self.mock_pytesseract.image_to_data.return_value = {
            'text': ['Sample', 'Text'],
            'conf': [90.5, 85.2],
            'left': [10, 100],
            'top': [20, 30],
            'width': [50, 40],
            'height': [15, 10]
        }
        
        # Call detect method
        results = self.ocr_strategy.detect(self.test_image, {})
        
        # Check that pytesseract was called correctly
        self.mock_pytesseract.image_to_data.assert_called_once()
        
        # Verify the results
        self.assertEqual(len(results), 2)
        
        # Check first result
        self.assertEqual(results[0]['type'], 'text')
        self.assertEqual(results[0]['text'], 'Sample')
        self.assertEqual(results[0]['x'], 10)
        self.assertEqual(results[0]['y'], 20)
        self.assertEqual(results[0]['width'], 50)
        self.assertEqual(results[0]['height'], 15)
        self.assertEqual(results[0]['confidence'], 90.5)
        
        # Check second result
        self.assertEqual(results[1]['type'], 'text')
        self.assertEqual(results[1]['text'], 'Text')
    
    def test_detect_with_confidence_threshold(self):
        """Test detection with confidence threshold filtering."""
        # Mock the pytesseract image_to_data response
        self.mock_pytesseract.Output.DICT = 'DICT'
        self.mock_pytesseract.image_to_data.return_value = {
            'text': ['High', 'Medium', 'Low'],
            'conf': [95.0, 75.0, 30.0],
            'left': [10, 100, 150],
            'top': [20, 30, 40],
            'width': [50, 40, 30],
            'height': [15, 10, 10]
        }
        
        # Call detect method with confidence threshold
        results = self.ocr_strategy.detect(self.test_image, {'confidence_threshold': 70})
        
        # Verify only results above threshold are returned
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['text'], 'High')
        self.assertEqual(results[1]['text'], 'Medium')
    
    def test_detect_with_pattern_filter(self):
        """Test detection with regex pattern filtering."""
        # Mock the pytesseract image_to_data response
        self.mock_pytesseract.Output.DICT = 'DICT'
        self.mock_pytesseract.image_to_data.return_value = {
            'text': ['ABC123', 'DEF456', 'GHI789'],
            'conf': [90.0, 90.0, 90.0],
            'left': [10, 100, 150],
            'top': [20, 30, 40],
            'width': [50, 40, 30],
            'height': [15, 10, 10]
        }
        
        # Call detect method with pattern filter for numbers ending in 6
        results = self.ocr_strategy.detect(self.test_image, {'pattern': '.*6$'})
        
        # Verify only matching results are returned
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['text'], 'DEF456')
    
    def test_detect_with_region(self):
        """Test detection with region specification."""
        # Mock the pytesseract image_to_data response
        self.mock_pytesseract.Output.DICT = 'DICT'
        self.mock_pytesseract.image_to_data.return_value = {
            'text': ['Region Text'],
            'conf': [90.0],
            'left': [10],
            'top': [20],
            'width': [50],
            'height': [15]
        }
        
        # Define region
        region = {'left': 50, 'top': 40, 'width': 100, 'height': 20}
        
        # Call detect method with region
        results = self.ocr_strategy.detect(self.test_image, {'region': region})
        
        # Verify the results have coordinates adjusted for the region
        self.assertEqual(results[0]['x'], 10 + 50)  # left + region.left
        self.assertEqual(results[0]['y'], 20 + 40)  # top + region.top
    
    def test_detect_with_error(self):
        """Test detection handling when OCR raises an exception."""
        # Force pytesseract to raise an exception
        self.mock_pytesseract.image_to_data.side_effect = Exception("OCR error")
        
        # Call detect method
        results = self.ocr_strategy.detect(self.test_image, {})
        
        # Verify empty results are returned
        self.assertEqual(results, [])
    
    def test_preprocess_image(self):
        """Test image preprocessing for different methods."""
        # Test each preprocessing method
        for method in ['none', 'thresh', 'blur', 'adaptive', 'invalid']:
            # Call the private preprocessing method
            processed = self.ocr_strategy._preprocess_image(self.test_image, method)
            
            # Verify result is a valid image
            self.assertIsInstance(processed, np.ndarray)
            self.assertEqual(len(processed.shape), 2)  # Should be grayscale
            
    def test_get_text(self):
        """Test the convenience get_text method."""
        # Mock pytesseract.image_to_string
        self.mock_pytesseract.image_to_string.return_value = "Simple text extraction"
        
        # Call get_text
        text = self.ocr_strategy.get_text(self.test_image)
        
        # Verify result
        self.assertEqual(text, "Simple text extraction")
        self.mock_pytesseract.image_to_string.assert_called_once()
        
    def test_get_text_with_error(self):
        """Test error handling in get_text method."""
        # Force pytesseract to raise an exception
        self.mock_pytesseract.image_to_string.side_effect = Exception("OCR error")
        
        # Call get_text
        text = self.ocr_strategy.get_text(self.test_image)
        
        # Verify empty string is returned
        self.assertEqual(text, "")


if __name__ == '__main__':
    unittest.main() 