"""Tests for OCR processing system."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from scout.capture import OCRProcessor, CaptureManager

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock(spec=CaptureManager)
    
    # Setup default behavior
    image = np.zeros((100, 30, 3), dtype=np.uint8)
    manager.capture_region.return_value = image
    manager.preprocess_image.return_value = image
    
    return manager

@pytest.fixture
def mock_tesseract():
    """Mock pytesseract."""
    with patch("pytesseract.image_to_string") as mock_string, \
         patch("pytesseract.get_languages") as mock_langs:
        # Setup default behavior
        mock_string.return_value = "123"
        mock_langs.return_value = ["eng", "deu", "fra"]
        yield {
            "image_to_string": mock_string,
            "get_languages": mock_langs
        }

@pytest.fixture
def ocr_processor(mock_capture_manager):
    """Create OCRProcessor instance."""
    return OCRProcessor(mock_capture_manager)

def test_ocr_processor_initialization(ocr_processor):
    """Test OCRProcessor initialization."""
    assert ocr_processor.lang == "eng"
    assert ocr_processor.config["lang"] == "eng"
    assert "--psm 7" in ocr_processor.config["tesseract_config"]
    assert "--oem 3" in ocr_processor.config["tesseract_config"]
    assert "tessedit_char_whitelist=0123456789" in ocr_processor.config["tesseract_config"]
    assert ocr_processor.ocr_metrics["total_extractions"] == 0
    assert ocr_processor.ocr_metrics["failed_extractions"] == 0
    assert ocr_processor.ocr_metrics["avg_processing_time"] == 0.0
    assert ocr_processor.ocr_metrics["last_extraction"] is None

def test_ocr_processor_with_custom_config():
    """Test OCRProcessor initialization with custom config."""
    mock_capture_manager = MagicMock(spec=CaptureManager)
    processor = OCRProcessor(
        mock_capture_manager,
        tesseract_cmd="path/to/tesseract",
        lang="deu"
    )
    
    assert processor.lang == "deu"
    assert processor.config["lang"] == "deu"

def test_process_region(ocr_processor, mock_capture_manager, mock_tesseract):
    """Test processing OCR region."""
    # Track signal emission
    text_found = False
    found_text = None
    found_region = None
    
    def on_text_found(region, text):
        nonlocal text_found, found_text, found_region
        text_found = True
        found_text = text
        found_region = region
    
    ocr_processor.text_found.connect(on_text_found)
    
    # Process region
    text = ocr_processor._process_region("test_region")
    
    assert text == "123"  # Default mock value
    assert text_found
    assert found_text == "123"
    assert found_region == "test_region"
    
    # Check capture was requested
    mock_capture_manager.capture_region.assert_called_once_with(
        "test_region",
        False
    )
    
    # Check preprocessing was requested
    mock_capture_manager.preprocess_image.assert_called_once_with(
        mock_capture_manager.capture_region.return_value,
        for_ocr=True
    )
    
    # Check OCR was performed
    mock_tesseract["image_to_string"].assert_called_once()

def test_process_region_no_text(ocr_processor, mock_tesseract):
    """Test processing region with no text found."""
    # Make OCR return empty string
    mock_tesseract["image_to_string"].return_value = ""
    
    # Track signal emission
    text_found = False
    def on_text_found(region, text):
        nonlocal text_found
        text_found = True
    
    ocr_processor.text_found.connect(on_text_found)
    
    # Process region
    text = ocr_processor._process_region("test_region")
    
    assert text == ""
    assert not text_found  # Signal should not be emitted for empty text

def test_process_region_capture_failure(ocr_processor, mock_capture_manager):
    """Test handling region capture failure."""
    # Make capture fail
    mock_capture_manager.capture_region.return_value = None
    
    # Track signal emission
    text_failed = False
    error_msg = None
    failed_region = None
    
    def on_text_failed(region, error):
        nonlocal text_failed, error_msg, failed_region
        text_failed = True
        error_msg = error
        failed_region = region
    
    ocr_processor.text_failed.connect(on_text_failed)
    
    # Process region
    text = ocr_processor._process_region("test_region")
    
    assert text is None
    assert text_failed
    assert "Region capture failed" in error_msg
    assert failed_region == "test_region"

def test_process_region_ocr_failure(ocr_processor, mock_tesseract):
    """Test handling OCR failure."""
    # Make OCR fail
    mock_tesseract["image_to_string"].side_effect = Exception("OCR error")
    
    # Track signal emission
    text_failed = False
    error_msg = None
    
    def on_text_failed(region, error):
        nonlocal text_failed, error_msg
        text_failed = True
        error_msg = error
    
    ocr_processor.text_failed.connect(on_text_failed)
    
    # Process region
    text = ocr_processor._process_region("test_region")
    
    assert text is None
    assert text_failed
    assert "OCR error" in error_msg

def test_clean_text(ocr_processor):
    """Test text cleaning function."""
    # Test various input cases
    assert ocr_processor._clean_text("123") == "123"
    assert ocr_processor._clean_text("abc123def") == "123"
    assert ocr_processor._clean_text("12.34") == "1234"
    assert ocr_processor._clean_text("1,234") == "1234"
    assert ocr_processor._clean_text("") == ""
    assert ocr_processor._clean_text("abc") == ""

def test_clean_text_error_handling(ocr_processor):
    """Test error handling in text cleaning."""
    # Test with invalid input
    text = None  # type: ignore
    result = ocr_processor._clean_text(text)
    assert result == text  # Should return original text on error

def test_update_metrics(ocr_processor):
    """Test metrics update."""
    initial_time = datetime.now()
    with patch('scout.capture.ocr_processor.datetime') as mock_datetime:
        # Set initial time
        mock_datetime.now.return_value = initial_time
        start_time = initial_time
        
        # Simulate successful extraction
        next_time = initial_time + timedelta(seconds=1)
        mock_datetime.now.return_value = next_time
        ocr_processor._update_metrics(True, start_time)
        
        assert ocr_processor.ocr_metrics["total_extractions"] == 1
        assert ocr_processor.ocr_metrics["failed_extractions"] == 0
        assert ocr_processor.ocr_metrics["avg_processing_time"] == 0.1  # 10% of 1 second
        assert ocr_processor.ocr_metrics["last_extraction"] == next_time
        
        # Simulate failed extraction
        final_time = next_time + timedelta(seconds=1)
        mock_datetime.now.return_value = final_time
        ocr_processor._update_metrics(False, next_time)
        
        assert ocr_processor.ocr_metrics["total_extractions"] == 2
        assert ocr_processor.ocr_metrics["failed_extractions"] == 1
        assert ocr_processor.ocr_metrics["last_extraction"] == final_time

def test_update_metrics_error_handling(ocr_processor):
    """Test error handling in metrics update."""
    # Test with invalid start time
    start_time = None  # type: ignore
    ocr_processor._update_metrics(True, start_time)  # Should handle error gracefully

def test_get_debug_info(ocr_processor):
    """Test getting debug information."""
    # Process a region to generate some metrics
    ocr_processor._process_region("test_region")
    
    debug_info = ocr_processor.get_debug_info()
    
    assert "metrics" in debug_info
    assert "config" in debug_info
    assert debug_info["metrics"]["total_extractions"] == 1
    assert debug_info["config"]["lang"] == "eng"

def test_set_tesseract_config(ocr_processor):
    """Test updating tesseract configuration."""
    new_config = {
        "lang": "deu",
        "tesseract_config": "--psm 6 --oem 2"
    }
    
    ocr_processor.set_tesseract_config(new_config)
    
    assert ocr_processor.config["lang"] == "deu"
    assert ocr_processor.config["tesseract_config"] == "--psm 6 --oem 2"

def test_set_tesseract_config_error(ocr_processor):
    """Test error handling in tesseract config update."""
    # Test with invalid config
    invalid_config = None  # type: ignore
    ocr_processor.set_tesseract_config(invalid_config)  # Should handle error gracefully
    assert ocr_processor.config["lang"] == "eng"  # Config should remain unchanged

def test_get_supported_languages(ocr_processor, mock_tesseract):
    """Test getting supported languages."""
    languages = ocr_processor.get_supported_languages()
    assert languages == ["eng", "deu", "fra"]
    mock_tesseract["get_languages"].assert_called_once()

def test_get_supported_languages_empty(ocr_processor, mock_tesseract):
    """Test handling no available languages."""
    # Make get_languages return empty list
    mock_tesseract["get_languages"].return_value = []
    
    languages = ocr_processor.get_supported_languages()
    assert languages == ["eng"]  # Should fall back to English

def test_get_supported_languages_error(ocr_processor, mock_tesseract):
    """Test error handling in language detection."""
    # Make get_languages fail
    mock_tesseract["get_languages"].side_effect = Exception("Language error")
    
    languages = ocr_processor.get_supported_languages()
    assert languages == ["eng"]  # Should fall back to English 