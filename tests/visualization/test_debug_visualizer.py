"""Tests for debug visualization system."""

import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtGui import QImage
from scout.visualization import DebugVisualizer, CoordinateVisualizer
from scout.core import WindowTracker, CoordinateManager, CoordinateSpace
from scout.capture import CaptureManager, PatternMatcher, OCRProcessor

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MagicMock(spec=WindowTracker)
    
    # Setup default window geometry
    window_rect = QRect(100, 100, 800, 600)
    client_rect = QRect(110, 120, 780, 580)
    
    tracker.get_window_rect.return_value = window_rect
    tracker.get_client_rect.return_value = client_rect
    tracker.get_debug_info.return_value = {
        "window_found": True,
        "window_handle": 12345,
        "window_rect": window_rect,
        "client_rect": client_rect,
        "dpi_scale": 1.0
    }
    
    return tracker

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    
    # Setup default regions
    manager.regions = {
        "test_region": {
            "rect": QRect(200, 200, 100, 100),
            "space": CoordinateSpace.SCREEN
        }
    }
    
    return manager

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock(spec=CaptureManager)
    
    # Setup default behavior
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    manager.capture_window.return_value = image
    manager.get_debug_info.return_value = {
        "metrics": {
            "total_captures": 10,
            "failed_captures": 1,
            "avg_capture_time": 0.1
        }
    }
    
    return manager

@pytest.fixture
def mock_pattern_matcher():
    """Create mock pattern matcher."""
    matcher = MagicMock(spec=PatternMatcher)
    
    # Setup default behavior
    matcher.get_template_info.return_value = {
        "test_template": {
            "size": (100, 100),
            "shape": (100, 100)
        }
    }
    
    return matcher

@pytest.fixture
def mock_ocr_processor():
    """Create mock OCR processor."""
    processor = MagicMock(spec=OCRProcessor)
    
    # Setup default behavior
    processor.get_debug_info.return_value = {
        "metrics": {
            "total_extractions": 5,
            "failed_extractions": 1,
            "avg_processing_time": 0.2
        }
    }
    
    return processor

@pytest.fixture
def debug_visualizer(
    mock_window_tracker,
    mock_coordinate_manager,
    mock_capture_manager,
    mock_pattern_matcher,
    mock_ocr_processor
):
    """Create DebugVisualizer instance."""
    return DebugVisualizer(
        mock_window_tracker,
        mock_coordinate_manager,
        mock_capture_manager,
        mock_pattern_matcher,
        mock_ocr_processor
    )

@pytest.fixture
def coordinate_visualizer(mock_window_tracker, mock_coordinate_manager):
    """Create CoordinateVisualizer instance."""
    from scout.visualization import CoordinateVisualizer
    return CoordinateVisualizer(mock_window_tracker, mock_coordinate_manager)

def test_debug_visualizer_initialization(debug_visualizer):
    """Test DebugVisualizer initialization."""
    assert not debug_visualizer.update_timer.isActive()
    assert len(debug_visualizer.last_matches) == 0
    assert len(debug_visualizer.last_ocr_text) == 0

def test_start_stop(debug_visualizer, qtbot):
    """Test starting and stopping debug visualization."""
    # Start visualization
    debug_visualizer.start()
    qtbot.wait(100)  # Wait for timer to start
    
    # Verify timer is active
    assert debug_visualizer.update_timer.isActive()
    
    # Stop visualization
    debug_visualizer.stop()
    qtbot.wait(100)  # Wait for timer to stop
    
    # Verify timer is stopped
    assert not debug_visualizer.update_timer.isActive()

def test_update_preview(debug_visualizer, mock_capture_manager):
    """Test preview update."""
    # Create test image
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    mock_capture_manager.capture_window.return_value = image
    
    # Setup signal tracking
    preview_updated = False
    preview_image = None
    
    def on_preview_updated(image):
        nonlocal preview_updated, preview_image
        preview_updated = True
        preview_image = image
    
    debug_visualizer.preview_updated.connect(on_preview_updated)
    
    # Update preview
    debug_visualizer._update_preview()
    
    assert preview_updated
    assert isinstance(preview_image, QImage)
    assert preview_image.width() == 800
    assert preview_image.height() == 600

def test_update_metrics(debug_visualizer):
    """Test metrics update."""
    # Setup signal tracking
    metrics_updated = False
    metrics_data = None
    
    def on_metrics_updated(metrics):
        nonlocal metrics_updated, metrics_data
        metrics_updated = True
        metrics_data = metrics
    
    debug_visualizer.metrics_updated.connect(on_metrics_updated)
    
    # Update metrics
    debug_visualizer._update_metrics()
    
    assert metrics_updated
    assert "window" in metrics_data
    assert "capture" in metrics_data
    assert "pattern" in metrics_data
    assert "ocr" in metrics_data

def test_capture_event_handling(debug_visualizer, mock_capture_manager):
    """Test handling capture events."""
    # Setup signal tracking
    preview_updated = False
    
    def on_preview_updated(image):
        nonlocal preview_updated
        preview_updated = True
    
    debug_visualizer.preview_updated.connect(on_preview_updated)
    
    # Simulate capture event
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    debug_visualizer._on_capture_complete(image, "window")
    
    assert preview_updated

def test_match_event_handling(debug_visualizer, mock_pattern_matcher):
    """Test handling pattern match events."""
    # Setup signal tracking
    preview_updated = False
    
    def on_preview_updated(image):
        nonlocal preview_updated
        preview_updated = True
    
    debug_visualizer.preview_updated.connect(on_preview_updated)
    
    # Simulate match event
    debug_visualizer._on_match_found(
        "test_template",
        0.9,
        QPoint(100, 100)
    )
    
    assert preview_updated

def test_text_event_handling(debug_visualizer):
    """Test handling OCR text events."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Track preview updates
    preview_updated = False
    def on_preview_updated(image):
        nonlocal preview_updated
        preview_updated = True
    
    debug_visualizer.preview_updated.connect(on_preview_updated)
    
    # Update preview
    debug_visualizer._update_preview()
    
    # Simulate text event
    debug_visualizer._on_text_found("test_region", "123")
    
    # Verify preview was updated and text was stored
    assert preview_updated
    assert "test_region" in debug_visualizer.last_ocr_text
    assert debug_visualizer.last_ocr_text["test_region"] == "123"

def test_draw_overlay_with_missing_window(coordinate_visualizer, mock_window_tracker):
    """Test drawing overlay when window is not found."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Set window tracker to return None for window rect
    mock_window_tracker.get_window_rect.return_value = None
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image.copy())
    
    # Verify no changes were made to the image
    assert np.array_equal(result, image)

def test_draw_overlay_with_missing_client_rect(coordinate_visualizer, mock_window_tracker):
    """Test drawing overlay when client rect is not found."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Set window tracker to return window rect but no client rect
    mock_window_tracker.get_window_rect.return_value = QRect(100, 100, 800, 600)
    mock_window_tracker.get_client_rect.return_value = None
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image.copy())
    
    # Verify only window rect was drawn
    window_rect = mock_window_tracker.get_window_rect()
    assert np.all(result[window_rect.top():window_rect.bottom(), window_rect.left():window_rect.right()] == 0) 