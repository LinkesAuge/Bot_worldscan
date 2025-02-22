"""Tests for coordinate visualization system."""

import pytest
import numpy as np
import cv2
from unittest.mock import MagicMock
from PyQt6.QtCore import QRect
from scout.visualization import CoordinateVisualizer
from scout.core import WindowTracker, CoordinateManager, CoordinateSpace

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MagicMock(spec=WindowTracker)
    
    # Setup default window geometry
    window_rect = QRect(100, 100, 800, 600)
    client_rect = QRect(110, 120, 780, 580)
    
    tracker.get_window_rect.return_value = window_rect
    tracker.get_client_rect.return_value = client_rect
    
    return tracker

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    
    # Setup default regions
    manager.regions = {
        "pattern_region": {
            "rect": QRect(200, 200, 100, 100),
            "space": CoordinateSpace.SCREEN
        },
        "ocr_region": {
            "rect": QRect(300, 300, 100, 30),
            "space": CoordinateSpace.SCREEN
        }
    }
    
    return manager

@pytest.fixture
def coordinate_visualizer(mock_window_tracker, mock_coordinate_manager):
    """Create CoordinateVisualizer instance."""
    return CoordinateVisualizer(mock_window_tracker, mock_coordinate_manager)

def test_coordinate_visualizer_initialization(coordinate_visualizer):
    """Test CoordinateVisualizer initialization."""
    assert "window" in coordinate_visualizer.colors
    assert "client" in coordinate_visualizer.colors
    assert "pattern" in coordinate_visualizer.colors
    assert "ocr" in coordinate_visualizer.colors

def test_draw_overlay_window_rect(coordinate_visualizer):
    """Test drawing window rectangle."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Check window rectangle was drawn
    # Window rect should be green (0, 255, 0)
    assert np.any(result[100:700, 100:900] != 0)  # Some pixels changed
    assert np.any(result[100, 100:900, 1] == 255)  # Green border

def test_draw_overlay_client_rect(coordinate_visualizer):
    """Test drawing client rectangle."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Check client rectangle was drawn
    # Client rect should be red (255, 0, 0)
    assert np.any(result[120:700, 110:890] != 0)  # Some pixels changed
    assert np.any(result[120, 110:890, 2] == 255)  # Red border

def test_draw_overlay_regions(coordinate_visualizer):
    """Test drawing regions."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Check pattern region was drawn
    # Pattern region should be blue (0, 0, 255)
    assert np.any(result[200:300, 200:300] != 0)  # Some pixels changed
    assert np.any(result[200, 200:300, 0] == 255)  # Blue border
    
    # Check OCR region was drawn
    # OCR region should be yellow (255, 255, 0)
    assert np.any(result[300:330, 300:400] != 0)  # Some pixels changed
    assert np.any(result[300, 300:400, 2] == 255)  # Yellow border

def test_draw_overlay_with_transformed_regions(coordinate_visualizer, mock_coordinate_manager):
    """Test drawing regions with coordinate transformation."""
    # Setup region in window space
    mock_coordinate_manager.regions["window_region"] = {
        "rect": QRect(50, 50, 100, 100),
        "space": CoordinateSpace.WINDOW
    }
    
    # Setup get_region to transform coordinates
    def get_region(name, space):
        if name == "window_region" and space == CoordinateSpace.SCREEN:
            return QRect(150, 150, 100, 100)  # Transformed to screen space
        return mock_coordinate_manager.regions[name]["rect"]
    
    mock_coordinate_manager.get_region.side_effect = get_region
    
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Check transformed region was drawn
    assert np.any(result[150:250, 150:250] != 0)  # Some pixels changed

def test_draw_overlay_with_missing_window(coordinate_visualizer, mock_window_tracker):
    """Test drawing overlay when window is not found."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    original_image = image.copy()
    
    # Set up window tracker to return None for window rect
    mock_window_tracker.get_window_rect.return_value = None
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Image should be unmodified when window is not found
    assert np.array_equal(result, original_image)

def test_draw_overlay_with_missing_client_rect(coordinate_visualizer, mock_window_tracker):
    """Test drawing overlay when client rect is not found."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Set up window tracker mocks
    window_rect = QRect(100, 100, 800, 600)
    mock_window_tracker.get_window_rect.return_value = window_rect
    mock_window_tracker.get_client_rect.return_value = None
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Window rect should still be drawn
    assert not np.array_equal(result, image)
    assert np.any(result[window_rect.top():window_rect.bottom(), window_rect.left():window_rect.right()] > 0)

def test_draw_overlay_window_rect(coordinate_visualizer, mock_window_tracker):
    """Test drawing window rectangle overlay."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Set up window tracker mocks
    window_rect = QRect(100, 100, 800, 600)
    mock_window_tracker.get_window_rect.return_value = window_rect
    mock_window_tracker.get_client_rect.return_value = None
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Verify window rect was drawn
    assert not np.array_equal(result, image)
    assert np.any(result[window_rect.top():window_rect.bottom(), window_rect.left():window_rect.right()] > 0)

def test_draw_overlay_client_rect(coordinate_visualizer, mock_window_tracker):
    """Test drawing client rectangle overlay."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Set up window tracker mocks
    window_rect = QRect(100, 100, 800, 600)
    client_rect = QRect(120, 140, 760, 520)
    mock_window_tracker.get_window_rect.return_value = window_rect
    mock_window_tracker.get_client_rect.return_value = client_rect
    
    # Draw overlay
    result = coordinate_visualizer.draw_overlay(image)
    
    # Verify client rect was drawn
    assert not np.array_equal(result, image)
    assert np.any(result[client_rect.top():client_rect.bottom(), client_rect.left():client_rect.right()] > 0)

def test_draw_rect(coordinate_visualizer):
    """Test drawing rectangle with label."""
    # Create test image
    image = np.zeros((800, 1000, 3), dtype=np.uint8)
    
    # Draw test rectangle
    rect = QRect(100, 100, 200, 200)
    color = (0, 255, 0)  # Green
    label = "Test"
    
    coordinate_visualizer._draw_rect(image, rect, color, label)
    
    # Check rectangle was drawn
    assert np.any(image[100:300, 100:300] != 0)  # Some pixels changed
    assert np.any(image[100, 100:300, 1] == 255)  # Green border
    
    # Check label was drawn (text pixels should be non-zero)
    assert np.any(image[95:100, 100:150] != 0)  # Label area changed 