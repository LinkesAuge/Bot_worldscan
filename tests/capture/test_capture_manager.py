"""Tests for screen capture system."""

import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtCore import QRect
from scout.capture import CaptureManager
from scout.core import WindowTracker, CoordinateManager, CoordinateSpace

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MagicMock(spec=WindowTracker)
    
    # Setup default window geometry
    window_rect = QRect(100, 100, 800, 600)
    tracker.get_window_rect.return_value = window_rect
    
    return tracker

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    
    # Setup default region
    region_rect = QRect(200, 200, 100, 100)
    manager.get_region.return_value = region_rect
    
    return manager

@pytest.fixture
def mock_mss():
    """Mock mss screen capture."""
    with patch("mss.mss") as mock:
        instance = mock.return_value
        # Create a mock screenshot
        screenshot = MagicMock()
        screenshot.size = (800, 600)
        screenshot.rgb = np.zeros((600, 800, 4), dtype=np.uint8)  # BGRA format
        instance.grab.return_value = screenshot
        yield instance

@pytest.fixture
def capture_manager(mock_window_tracker, mock_coordinate_manager, tmp_path):
    """Create CaptureManager instance."""
    debug_dir = tmp_path / "debug_screenshots"
    return CaptureManager(
        mock_window_tracker,
        mock_coordinate_manager,
        str(debug_dir)
    )

def test_capture_manager_initialization(capture_manager, tmp_path):
    """Test CaptureManager initialization."""
    assert capture_manager.debug_dir == tmp_path / "debug_screenshots"
    assert capture_manager.debug_dir.exists()
    assert capture_manager.last_capture_time is None
    assert capture_manager.capture_metrics["total_captures"] == 0
    assert capture_manager.capture_metrics["failed_captures"] == 0
    assert capture_manager.capture_metrics["avg_capture_time"] == 0.0

def test_capture_window(capture_manager, mock_mss, mock_window_tracker):
    """Test capturing entire window."""
    # Track signal emission
    capture_complete = False
    captured_image = None
    capture_type = None
    
    def on_capture_complete(image, ctype):
        nonlocal capture_complete, captured_image, capture_type
        capture_complete = True
        captured_image = image
        capture_type = ctype
    
    capture_manager.capture_complete.connect(on_capture_complete)
    
    # Capture window
    image = capture_manager.capture_window()
    
    assert image is not None
    assert isinstance(image, np.ndarray)
    assert len(image.shape) == 3  # Should be BGR image
    
    # Check metrics
    assert capture_manager.capture_metrics["total_captures"] == 1
    assert capture_manager.capture_metrics["failed_captures"] == 0
    assert capture_manager.last_capture_time is not None
    
    # Check signal was emitted
    assert capture_complete
    assert captured_image is not None
    assert capture_type == "window"

def test_capture_window_failure(capture_manager, mock_window_tracker):
    """Test handling window capture failure."""
    # Track signal emission
    capture_failed = False
    error_msg = None
    failure_type = None
    
    def on_capture_failed(msg, ftype):
        nonlocal capture_failed, error_msg, failure_type
        capture_failed = True
        error_msg = msg
        failure_type = ftype
    
    capture_manager.capture_failed.connect(on_capture_failed)
    
    # Make window rect unavailable
    mock_window_tracker.get_window_rect.return_value = None
    
    # Try capture
    image = capture_manager.capture_window()
    
    assert image is None
    assert capture_manager.capture_metrics["failed_captures"] == 1
    
    # Check signal was emitted
    assert capture_failed
    assert "Window not found" in error_msg
    assert failure_type == "window"

def test_capture_region(capture_manager, mock_mss, mock_coordinate_manager):
    """Test capturing specific region."""
    # Track signal emission
    capture_complete = False
    captured_image = None
    capture_type = None
    
    def on_capture_complete(image, ctype):
        nonlocal capture_complete, captured_image, capture_type
        capture_complete = True
        captured_image = image
        capture_type = ctype
    
    capture_manager.capture_complete.connect(on_capture_complete)
    
    # Capture region
    image = capture_manager.capture_region("test_region")
    
    assert image is not None
    assert isinstance(image, np.ndarray)
    assert len(image.shape) == 3  # Should be BGR image
    
    # Check region was requested
    mock_coordinate_manager.get_region.assert_called_with(
        "test_region",
        CoordinateSpace.SCREEN
    )
    
    # Check signal was emitted
    assert capture_complete
    assert captured_image is not None
    assert capture_type == "region_test_region"

def test_capture_region_failure(capture_manager, mock_coordinate_manager):
    """Test handling region capture failure."""
    # Track signal emission
    capture_failed = False
    error_msg = None
    failure_type = None
    
    def on_capture_failed(msg, ftype):
        nonlocal capture_failed, error_msg, failure_type
        capture_failed = True
        error_msg = msg
        failure_type = ftype
    
    capture_manager.capture_failed.connect(on_capture_failed)
    
    # Make region unavailable
    mock_coordinate_manager.get_region.return_value = None
    
    # Try capture
    image = capture_manager.capture_region("test_region")
    
    assert image is None
    assert capture_manager.capture_metrics["failed_captures"] == 1
    
    # Check signal was emitted
    assert capture_failed
    assert "Region 'test_region' not found" in error_msg
    assert failure_type == "region_test_region"

def test_preprocess_image_for_ocr(capture_manager):
    """Test image preprocessing for OCR."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[25:75, 25:75] = 255  # White rectangle
    
    # Preprocess for OCR
    processed = capture_manager.preprocess_image(image, for_ocr=True)
    
    assert processed is not None
    assert len(processed.shape) == 2  # Should be grayscale
    assert processed.dtype == np.uint8

def test_preprocess_image_for_pattern_matching(capture_manager):
    """Test image preprocessing for pattern matching."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[25:75, 25:75] = 255  # White rectangle
    
    # Preprocess for pattern matching
    processed = capture_manager.preprocess_image(image, for_ocr=False)
    
    assert processed is not None
    assert len(processed.shape) == 2  # Should be grayscale
    assert processed.dtype == np.uint8

def test_preprocess_image_error_handling(capture_manager):
    """Test error handling in image preprocessing."""
    # Create invalid image
    image = np.zeros((0, 0), dtype=np.uint8)  # Empty image
    
    # Test OCR preprocessing
    processed = capture_manager.preprocess_image(image, for_ocr=True)
    assert processed is image  # Should return original image on error
    
    # Test pattern matching preprocessing
    processed = capture_manager.preprocess_image(image, for_ocr=False)
    assert processed is image  # Should return original image on error

def test_metrics_update(capture_manager):
    """Test capture metrics update."""
    # Set initial time
    initial_time = datetime.now()
    with patch('scout.capture.capture_manager.datetime') as mock_datetime:
        mock_datetime.now.return_value = initial_time
        capture_manager.last_capture_time = initial_time
        
        # Simulate successful capture
        next_time = initial_time + timedelta(seconds=1)
        mock_datetime.now.return_value = next_time
        capture_manager._update_metrics(True)
        assert capture_manager.capture_metrics["total_captures"] == 1
        assert capture_manager.capture_metrics["failed_captures"] == 0
        assert capture_manager.last_capture_time == next_time
        
        # Simulate failed capture
        final_time = next_time + timedelta(seconds=1)
        mock_datetime.now.return_value = final_time
        capture_manager._update_metrics(False)
        assert capture_manager.capture_metrics["total_captures"] == 2
        assert capture_manager.capture_metrics["failed_captures"] == 1
        assert capture_manager.last_capture_time == final_time

def test_metrics_timing(capture_manager):
    """Test capture timing metrics."""
    initial_time = datetime.now()
    with patch('scout.capture.capture_manager.datetime') as mock_datetime:
        # Simulate first capture
        mock_datetime.now.return_value = initial_time
        capture_manager._update_metrics(True)
        first_time = capture_manager.last_capture_time
        
        # Simulate second capture after 1 second
        next_time = initial_time + timedelta(seconds=1)
        mock_datetime.now.return_value = next_time
        capture_manager._update_metrics(True)
        second_time = capture_manager.last_capture_time
        
        # Check timing was updated
        # First capture sets initial time, second capture adds 0.1 seconds to avg
        assert capture_manager.capture_metrics["avg_capture_time"] == 0.1
        assert second_time > first_time

def test_save_debug_image(capture_manager):
    """Test saving debug screenshots."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Save debug image
    capture_manager._save_debug_image(image, "test")
    
    # Check debug directory
    screenshots = list(capture_manager.debug_dir.glob("test_*.png"))
    assert len(screenshots) == 1

def test_save_debug_image_failure(capture_manager):
    """Test handling debug image save failure."""
    # Create invalid image
    image = np.zeros((0, 0), dtype=np.uint8)  # Empty image
    
    # Try to save debug image
    capture_manager._save_debug_image(image, "test")
    
    # Check no files were created
    screenshots = list(capture_manager.debug_dir.glob("test_*.png"))
    assert len(screenshots) == 0

def test_get_debug_info(capture_manager):
    """Test getting debug information."""
    # Perform some captures
    capture_manager.capture_window()
    capture_manager.capture_region("test_region")
    
    debug_info = capture_manager.get_debug_info()
    
    assert "metrics" in debug_info
    assert "last_capture" in debug_info
    assert "debug_dir" in debug_info
    assert debug_info["metrics"]["total_captures"] == 2
    assert isinstance(debug_info["last_capture"], datetime)
    assert isinstance(debug_info["debug_dir"], str)

def test_capture_window_mss_error(capture_manager, mock_window_tracker):
    """Test handling MSS capture error."""
    # Make window rect unavailable to trigger error
    mock_window_tracker.get_window_rect.return_value = None
    
    # Track signal emission
    capture_failed = False
    error_msg = None
    
    def on_capture_failed(msg, _):
        nonlocal capture_failed, error_msg
        capture_failed = True
        error_msg = msg
    
    capture_manager.capture_failed.connect(on_capture_failed)
    
    # Try capture
    image = capture_manager.capture_window()
    
    assert image is None
    assert capture_failed
    assert "Window not found" in error_msg

def test_capture_region_conversion_error(capture_manager, mock_mss):
    """Test handling color conversion error."""
    # Create invalid screenshot that will cause cvtColor to fail
    screenshot = MagicMock()
    screenshot.size = (100, 100)
    # Create a 3D array with wrong number of channels (3 instead of 4 for BGRA)
    screenshot.rgb = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_mss.grab.return_value = screenshot
    
    # Track signal emission
    capture_failed = False
    error_msg = None
    
    def on_capture_failed(msg, _):
        nonlocal capture_failed, error_msg
        capture_failed = True
        error_msg = msg
    
    capture_manager.capture_failed.connect(on_capture_failed)
    
    # Try capture
    with patch('cv2.cvtColor', side_effect=Exception("Invalid number of channels")):
        image = capture_manager.capture_region("test_region")
        
        assert image is None
        assert capture_failed
        assert "Invalid number of channels" in error_msg 

def test_capture_window_with_debug(capture_manager, mock_mss):
    """Test window capture with debug enabled."""
    # Capture with debug
    image = capture_manager.capture_window(save_debug=True)
    
    # Check debug image was saved
    screenshots = list(capture_manager.debug_dir.glob("window_*.png"))
    assert len(screenshots) == 1

def test_capture_region_with_debug(capture_manager, mock_mss):
    """Test region capture with debug enabled."""
    # Capture with debug
    image = capture_manager.capture_region("test_region", save_debug=True)
    
    # Check debug image was saved
    screenshots = list(capture_manager.debug_dir.glob("region_test_region_*.png"))
    assert len(screenshots) == 1

def test_preprocess_image_invalid_type(capture_manager):
    """Test preprocessing with invalid image type."""
    # Create invalid image types
    invalid_images = [
        None,
        "not an image",
        np.zeros((100, 100), dtype=np.float32),  # Wrong data type
        np.zeros((100,), dtype=np.uint8),  # Wrong dimensions
    ]
    
    for image in invalid_images:
        # Test OCR preprocessing
        processed = capture_manager.preprocess_image(image, for_ocr=True)
        assert processed is image  # Should return original image on error
        
        # Test pattern matching preprocessing
        processed = capture_manager.preprocess_image(image, for_ocr=False)
        assert processed is image  # Should return original image on error

def test_capture_window_color_conversion(capture_manager, mock_mss):
    """Test color space conversion during window capture."""
    # Create BGRA test image
    screenshot = MagicMock()
    screenshot.size = (100, 100)
    screenshot.rgb = np.zeros((100, 100, 4), dtype=np.uint8)
    screenshot.rgb[:, :, 3] = 255  # Set alpha channel
    mock_mss.return_value.grab.return_value = screenshot
    
    # Mock window rect to match screenshot size
    capture_manager.window_tracker.get_window_rect.return_value = QRect(0, 0, 100, 100)
    
    # Capture window
    image = capture_manager.capture_window()
    
    assert image is not None
    assert image.shape == (100, 100, 3)  # Should be BGR
    assert image.dtype == np.uint8

def test_capture_region_color_conversion(capture_manager, mock_mss):
    """Test color space conversion during region capture."""
    # Create BGRA test image
    screenshot = MagicMock()
    screenshot.size = (100, 100)
    screenshot.rgb = np.zeros((100, 100, 4), dtype=np.uint8)
    screenshot.rgb[:, :, 3] = 255  # Set alpha channel
    mock_mss.return_value.grab.return_value = screenshot
    
    # Capture region
    image = capture_manager.capture_region("test_region")
    
    assert image is not None
    assert image.shape == (100, 100, 3)  # Should be BGR
    assert image.dtype == np.uint8

def test_capture_metrics_reset(capture_manager):
    """Test metrics reset functionality."""
    # Perform some captures
    capture_manager.capture_window()
    capture_manager.capture_region("test_region")
    
    # Reset metrics
    capture_manager.capture_metrics = {
        "total_captures": 0,
        "failed_captures": 0,
        "avg_capture_time": 0.0
    }
    
    assert capture_manager.capture_metrics["total_captures"] == 0
    assert capture_manager.capture_metrics["failed_captures"] == 0
    assert capture_manager.capture_metrics["avg_capture_time"] == 0.0

def test_capture_metrics_overflow(capture_manager):
    """Test metrics handling with large numbers."""
    # Set very large values
    capture_manager.capture_metrics["total_captures"] = 1000000
    capture_manager.capture_metrics["failed_captures"] = 500000
    capture_manager.capture_metrics["avg_capture_time"] = 1000.0
    
    # Perform capture
    capture_manager.capture_window()
    
    # Check metrics still work
    assert capture_manager.capture_metrics["total_captures"] == 1000001
    assert isinstance(capture_manager.capture_metrics["avg_capture_time"], float)

def test_debug_dir_creation(tmp_path):
    """Test debug directory creation."""
    # Create manager with non-existent directory
    debug_dir = tmp_path / "new_debug_dir"
    manager = CaptureManager(
        MagicMock(spec=WindowTracker),
        MagicMock(spec=CoordinateManager),
        str(debug_dir)
    )
    
    assert debug_dir.exists()
    assert debug_dir.is_dir()

def test_debug_dir_permissions(tmp_path):
    """Test debug directory with restricted permissions."""
    debug_dir = tmp_path / "restricted_dir"
    debug_dir.mkdir()
    
    # Create manager
    manager = CaptureManager(
        MagicMock(spec=WindowTracker),
        MagicMock(spec=CoordinateManager),
        str(debug_dir)
    )
    
    # Make directory read-only after creation
    debug_dir.chmod(0o444)  # Read-only
    
    # Try to save debug image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch('cv2.imwrite', side_effect=PermissionError("Permission denied")):
        manager._save_debug_image(image, "test")
    
    # Should handle permission error gracefully
    screenshots = list(debug_dir.glob("test_*.png"))
    assert len(screenshots) == 0

def test_capture_window_large_resolution(capture_manager, mock_mss):
    """Test capturing large resolution window."""
    # Create large screenshot
    screenshot = MagicMock()
    screenshot.size = (3840, 2160)  # 4K resolution
    screenshot.rgb = np.zeros((2160, 3840, 4), dtype=np.uint8)
    mock_mss.return_value.grab.return_value = screenshot
    
    # Mock window rect to match screenshot size
    capture_manager.window_tracker.get_window_rect.return_value = QRect(0, 0, 3840, 2160)
    
    # Capture window
    image = capture_manager.capture_window()
    
    assert image is not None
    assert image.shape == (2160, 3840, 3)
    assert image.dtype == np.uint8

def test_capture_region_zero_size(capture_manager, mock_coordinate_manager):
    """Test capturing region with zero size."""
    # Setup zero-size region
    mock_coordinate_manager.get_region.return_value = QRect(0, 0, 0, 0)
    
    # Try capture
    image = capture_manager.capture_region("test_region")
    
    assert image is None

def test_capture_region_negative_size(capture_manager, mock_coordinate_manager):
    """Test capturing region with negative size."""
    # Setup negative-size region
    mock_coordinate_manager.get_region.return_value = QRect(100, 100, -50, -30)
    
    # Try capture
    image = capture_manager.capture_region("test_region")
    
    assert image is None

def test_capture_region_outside_screen(capture_manager, mock_coordinate_manager):
    """Test capturing a region that is outside the screen bounds."""
    # Create a new MSS instance with mocked grab method
    mock_sct = MagicMock()
    mock_sct.grab.side_effect = Exception("Region out of bounds")
    capture_manager.sct = mock_sct
    
    # Test capturing region outside screen bounds
    result = capture_manager.capture_region("test_region")
    
    # Verify the result is None and error is logged
    assert result is None
    mock_coordinate_manager.get_region.assert_called_once()

def test_capture_metrics_timing_precision(capture_manager):
    """Test capture timing metrics precision."""
    initial_time = datetime.now()
    with patch('scout.capture.capture_manager.datetime') as mock_datetime:
        # Simulate captures with precise timing
        times = [
            initial_time,
            initial_time + timedelta(microseconds=100),
            initial_time + timedelta(microseconds=200),
            initial_time + timedelta(microseconds=300)
        ]
        
        for t in times:
            mock_datetime.now.return_value = t
            capture_manager._update_metrics(True)
        
        # Check timing precision
        assert isinstance(capture_manager.capture_metrics["avg_capture_time"], float)
        assert capture_manager.capture_metrics["avg_capture_time"] > 0

def test_preprocess_image_empty(capture_manager):
    """Test preprocessing empty image."""
    # Create empty image
    image = np.zeros((0, 0, 3), dtype=np.uint8)
    
    # Test OCR preprocessing
    ocr_result = capture_manager.preprocess_image(image, for_ocr=True)
    assert ocr_result.size == 0
    
    # Test pattern matching preprocessing
    pattern_result = capture_manager.preprocess_image(image, for_ocr=False)
    assert pattern_result.size == 0

def test_save_debug_image_formats(capture_manager):
    """Test saving debug images in different formats."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Test different image types
    image_types = [
        ("grayscale", np.zeros((100, 100), dtype=np.uint8)),
        ("rgb", np.zeros((100, 100, 3), dtype=np.uint8)),
        ("rgba", np.zeros((100, 100, 4), dtype=np.uint8))
    ]
    
    for name, img in image_types:
        capture_manager._save_debug_image(img, f"test_{name}")
        
        # Check image was saved
        screenshots = list(capture_manager.debug_dir.glob(f"test_{name}_*.png"))
        assert len(screenshots) == 1

def test_capture_metrics_concurrent_updates(capture_manager):
    """Test concurrent metrics updates."""
    from threading import Thread
    
    def update_metrics():
        for _ in range(100):
            capture_manager._update_metrics(True)
    
    # Create threads
    threads = [Thread(target=update_metrics) for _ in range(5)]
    
    # Start threads
    for t in threads:
        t.start()
    
    # Wait for threads
    for t in threads:
        t.join()
    
    # Check final count
    assert capture_manager.capture_metrics["total_captures"] == 500

def test_capture_window_multiple_monitors(capture_manager, mock_window_tracker):
    """Test window capture with multiple monitors."""
    # Setup window on second monitor
    mock_window_tracker.get_window_rect.return_value = QRect(1920, 0, 800, 600)  # Offset by primary monitor width
    
    # Capture window
    image = capture_manager.capture_window()
    
    assert image is not None
    assert isinstance(image, np.ndarray)
    assert image.shape == (600, 800, 3) 