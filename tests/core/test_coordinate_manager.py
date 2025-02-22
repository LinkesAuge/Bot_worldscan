"""Tests for coordinate management system."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QPoint, QRect
from scout.core import CoordinateManager, CoordinateSpace, WindowTracker

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MagicMock(spec=WindowTracker)
    
    # Setup default window geometry
    window_rect = QRect(100, 100, 800, 600)
    client_rect = QRect(110, 120, 780, 580)
    
    tracker.get_window_rect.return_value = window_rect
    tracker.get_client_rect.return_value = client_rect
    tracker.to_logical_pos.return_value = (50, 50)
    tracker.to_physical_pos.return_value = (100, 100)
    
    return tracker

@pytest.fixture
def coordinate_manager(mock_window_tracker):
    """Create CoordinateManager instance."""
    return CoordinateManager(mock_window_tracker)

def test_coordinate_manager_initialization(coordinate_manager):
    """Test CoordinateManager initialization."""
    assert coordinate_manager.window_tracker is not None
    assert isinstance(coordinate_manager.regions, dict)
    assert len(coordinate_manager.regions) == 0
    assert len(coordinate_manager.active_spaces) == 3
    assert CoordinateSpace.SCREEN in coordinate_manager.active_spaces
    assert CoordinateSpace.WINDOW in coordinate_manager.active_spaces
    assert CoordinateSpace.CLIENT in coordinate_manager.active_spaces

def test_transform_point_screen_to_window(coordinate_manager, mock_window_tracker):
    """Test transforming point from screen to window space."""
    # Point in screen coordinates
    screen_point = QPoint(200, 200)
    
    # Transform to window space
    window_point = coordinate_manager.transform_point(
        screen_point,
        CoordinateSpace.SCREEN,
        CoordinateSpace.WINDOW
    )
    
    # Window coordinates should be relative to window origin (100, 100)
    assert window_point.x() == 100  # 200 - 100
    assert window_point.y() == 100  # 200 - 100

def test_transform_point_window_to_client(coordinate_manager, mock_window_tracker):
    """Test transforming point from window to client space."""
    # Point in window coordinates
    window_point = QPoint(50, 50)
    
    # Transform to client space
    client_point = coordinate_manager.transform_point(
        window_point,
        CoordinateSpace.WINDOW,
        CoordinateSpace.CLIENT
    )
    
    # Client coordinates should be relative to client origin (110, 120)
    assert client_point.x() == 40  # 50 - (110 - 100)
    assert client_point.y() == 30  # 50 - (120 - 100)

def test_transform_point_screen_to_logical(coordinate_manager, mock_window_tracker):
    """Test transforming point from screen to logical space."""
    # Point in screen coordinates
    screen_point = QPoint(200, 200)
    
    # Transform to logical space
    logical_point = coordinate_manager.transform_point(
        screen_point,
        CoordinateSpace.SCREEN,
        CoordinateSpace.LOGICAL
    )
    
    # Verify logical coordinates
    assert logical_point.x() == 50  # From mock to_logical_pos
    assert logical_point.y() == 50

def test_transform_point_logical_to_screen(coordinate_manager, mock_window_tracker):
    """Test transforming point from logical to screen space."""
    # Point in logical coordinates
    logical_point = QPoint(50, 50)
    
    # Transform to screen space
    screen_point = coordinate_manager.transform_point(
        logical_point,
        CoordinateSpace.LOGICAL,
        CoordinateSpace.SCREEN
    )
    
    # Verify screen coordinates
    assert screen_point.x() == 100  # From mock to_physical_pos
    assert screen_point.y() == 100

def test_transform_point_error_handling(coordinate_manager, mock_window_tracker):
    """Test error handling in coordinate transformation."""
    # Test invalid source space
    with pytest.raises(RuntimeError) as exc_info:
        coordinate_manager.transform_point(
            QPoint(0, 0),
            "INVALID",
            CoordinateSpace.SCREEN
        )
    assert "Invalid coordinate space" in str(exc_info.value)
    
    # Test invalid target space
    with pytest.raises(RuntimeError) as exc_info:
        coordinate_manager.transform_point(
            QPoint(0, 0),
            CoordinateSpace.SCREEN,
            "INVALID"
        )
    assert "Invalid coordinate space" in str(exc_info.value)
    
    # Test missing window geometry
    mock_window_tracker.get_window_rect.return_value = None
    with pytest.raises(RuntimeError) as exc_info:
        coordinate_manager.transform_point(
            QPoint(0, 0),
            CoordinateSpace.SCREEN,
            CoordinateSpace.WINDOW
        )
    assert "Window geometry not available" in str(exc_info.value)

def test_transform_point_all_combinations(coordinate_manager, mock_window_tracker):
    """Test all valid coordinate space transformations."""
    test_point = QPoint(200, 200)
    spaces = [
        CoordinateSpace.SCREEN,
        CoordinateSpace.WINDOW,
        CoordinateSpace.CLIENT,
        CoordinateSpace.LOGICAL
    ]
    
    # Setup mock window tracker to return consistent values
    window_rect = QRect(100, 100, 800, 600)
    client_rect = QRect(110, 120, 780, 580)
    mock_window_tracker.get_window_rect.return_value = window_rect
    mock_window_tracker.get_client_rect.return_value = client_rect
    mock_window_tracker.to_logical_pos.return_value = (100, 100)
    mock_window_tracker.to_physical_pos.return_value = (200, 200)
    
    for from_space in spaces:
        for to_space in spaces:
            if from_space != to_space:
                result = coordinate_manager.transform_point(test_point, from_space, to_space)
                assert isinstance(result, QPoint)
                # Don't check for non-negative coordinates as some transformations may produce negative values

def test_transform_point_special_cases(coordinate_manager, mock_window_tracker):
    """Test special cases in coordinate transformation."""
    # Test identity transformation (same space)
    point = QPoint(100, 100)
    result = coordinate_manager.transform_point(
        point,
        CoordinateSpace.SCREEN,
        CoordinateSpace.SCREEN
    )
    assert result == point
    
    # Test client to window with no client rect
    mock_window_tracker.get_client_rect.return_value = None
    with pytest.raises(RuntimeError):
        coordinate_manager.transform_point(
            QPoint(0, 0),
            CoordinateSpace.CLIENT,
            CoordinateSpace.WINDOW
        )

def test_add_remove_region(coordinate_manager):
    """Test adding and removing regions."""
    # Add region
    test_rect = QRect(0, 0, 100, 100)
    coordinate_manager.add_region("test", test_rect, CoordinateSpace.SCREEN)
    assert "test" in coordinate_manager.regions
    assert coordinate_manager.regions["test"]["rect"] == test_rect
    assert coordinate_manager.regions["test"]["space"] == CoordinateSpace.SCREEN
    
    # Remove region
    coordinate_manager.remove_region("test")
    assert "test" not in coordinate_manager.regions
    
    # Remove non-existent region (should not raise)
    coordinate_manager.remove_region("nonexistent")

def test_get_region_with_transform(coordinate_manager, mock_window_tracker):
    """Test getting region with coordinate transformation."""
    # Add region in screen space
    screen_rect = QRect(200, 200, 100, 100)
    coordinate_manager.add_region("test", screen_rect, CoordinateSpace.SCREEN)
    
    # Get region in window space
    window_rect = coordinate_manager.get_region("test", CoordinateSpace.WINDOW)
    assert isinstance(window_rect, QRect)
    assert window_rect.x() == 100  # 200 - 100 (window origin)
    assert window_rect.y() == 100
    assert window_rect.width() == screen_rect.width()
    assert window_rect.height() == screen_rect.height()
    
    # Test getting non-existent region
    with pytest.raises(ValueError) as exc_info:
        coordinate_manager.get_region("nonexistent")
    assert "not found" in str(exc_info.value)

def test_is_valid_coordinate(coordinate_manager, mock_window_tracker):
    """Test coordinate validation."""
    # Test negative coordinates (invalid)
    assert not coordinate_manager.is_valid_coordinate(QPoint(-1, -1), CoordinateSpace.SCREEN)
    
    # Test window space validation
    window_rect = mock_window_tracker.get_window_rect()
    assert coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.WINDOW
    )
    assert coordinate_manager.is_valid_coordinate(
        QPoint(window_rect.width() - 1, window_rect.height() - 1),
        CoordinateSpace.WINDOW
    )
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(window_rect.width() + 1, window_rect.height() + 1),
        CoordinateSpace.WINDOW
    )
    
    # Test client space validation
    client_rect = mock_window_tracker.get_client_rect()
    assert coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.CLIENT
    )
    assert coordinate_manager.is_valid_coordinate(
        QPoint(client_rect.width() - 1, client_rect.height() - 1),
        CoordinateSpace.CLIENT
    )
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(client_rect.width() + 1, client_rect.height() + 1),
        CoordinateSpace.CLIENT
    )
    
    # Test with missing window/client rect
    mock_window_tracker.get_window_rect.return_value = None
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.WINDOW
    )
    
    mock_window_tracker.get_client_rect.return_value = None
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.CLIENT
    )

def test_active_spaces(coordinate_manager):
    """Test active coordinate spaces management."""
    # Set active spaces
    new_spaces = [CoordinateSpace.SCREEN, CoordinateSpace.WINDOW]
    coordinate_manager.set_active_spaces(new_spaces)
    
    # Get active spaces
    active = coordinate_manager.get_active_spaces()
    assert active == new_spaces
    assert len(active) == 2
    assert CoordinateSpace.SCREEN in active
    assert CoordinateSpace.WINDOW in active
    assert CoordinateSpace.CLIENT not in active

def test_window_events(coordinate_manager, mock_window_tracker):
    """Test window event handling."""
    # Test window found
    hwnd = 12345
    coordinate_manager.on_window_found(hwnd)
    
    # Test window lost
    coordinate_manager.on_window_lost()
    
    # Test window moved
    new_rect = QRect(200, 200, 800, 600)
    coordinate_manager.on_window_moved(new_rect)

def test_region_error_handling(coordinate_manager):
    """Test error handling in region management."""
    # Test adding region with invalid rect
    coordinate_manager.add_region("test", None, CoordinateSpace.SCREEN)  # type: ignore
    assert "test" in coordinate_manager.regions  # Region is added but with None rect
    
    # Test removing region with error
    coordinate_manager.regions["test"] = {"rect": QRect(), "space": CoordinateSpace.SCREEN}
    with patch.object(coordinate_manager, "regions", None):  # type: ignore
        coordinate_manager.remove_region("test")  # Should handle error gracefully

def test_coordinate_validation_edge_cases(coordinate_manager, mock_window_tracker):
    """Test edge cases in coordinate validation."""
    # Test screen space (always valid if non-negative)
    assert coordinate_manager.is_valid_coordinate(
        QPoint(10000, 10000),
        CoordinateSpace.SCREEN
    )
    
    # Test window space with zero dimensions
    mock_window_tracker.get_window_rect.return_value = QRect(0, 0, 0, 0)
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.WINDOW
    )
    
    # Test client space with zero dimensions
    mock_window_tracker.get_client_rect.return_value = QRect(0, 0, 0, 0)
    assert not coordinate_manager.is_valid_coordinate(
        QPoint(0, 0),
        CoordinateSpace.CLIENT
    )

def test_error_handling_edge_cases(coordinate_manager, mock_window_tracker):
    """Test error handling edge cases."""
    # Test transform_point with None point
    with pytest.raises(RuntimeError):
        coordinate_manager.transform_point(
            None,  # type: ignore
            CoordinateSpace.SCREEN,
            CoordinateSpace.WINDOW
        )
    
    # Test get_region with None name
    with pytest.raises(ValueError):
        coordinate_manager.get_region(None)  # type: ignore
    
    # Test is_valid_coordinate with None point
    assert not coordinate_manager.is_valid_coordinate(
        None,  # type: ignore
        CoordinateSpace.SCREEN
    )

def test_region_management_error_handling(coordinate_manager):
    """Test error handling in region management."""
    # Test add_region with None as name
    coordinate_manager.add_region(None, QRect(), CoordinateSpace.SCREEN)  # type: ignore
    assert None not in coordinate_manager.regions
    assert len(coordinate_manager.regions) == 0
    
    # Test add_region with empty name
    coordinate_manager.add_region("", QRect(), CoordinateSpace.SCREEN)
    assert "" not in coordinate_manager.regions
    assert len(coordinate_manager.regions) == 0
    
    # Test add_region with whitespace name
    coordinate_manager.add_region("   ", QRect(), CoordinateSpace.SCREEN)
    assert "   " not in coordinate_manager.regions
    assert len(coordinate_manager.regions) == 0
    
    # Test add_region with invalid coordinate space
    coordinate_manager.add_region("test", QRect(), "INVALID_SPACE")
    assert "test" not in coordinate_manager.regions
    assert len(coordinate_manager.regions) == 0
    
    # Test remove_region with non-existent region
    coordinate_manager.remove_region("non_existent")
    assert "non_existent" not in coordinate_manager.regions
    assert len(coordinate_manager.regions) == 0

def test_transform_point_invalid_window_rect(coordinate_manager, mock_window_tracker):
    """Test transform_point when window rect is invalid."""
    # Setup window tracker to return invalid rect
    mock_window_tracker.get_window_rect.return_value = QRect()
    mock_window_tracker.get_client_rect.return_value = QRect()
    
    # Try to transform point
    point = QPoint(100, 100)
    
    # Should raise RuntimeError when window geometry is not available
    with pytest.raises(RuntimeError, match="Window geometry not available"):
        coordinate_manager.transform_point(point, CoordinateSpace.SCREEN, CoordinateSpace.WINDOW)

def test_add_region_validation(coordinate_manager):
    """Test region validation during addition."""
    # Add region with empty name
    coordinate_manager.add_region("", QRect(0, 0, 100, 100), CoordinateSpace.SCREEN)
    assert "" not in coordinate_manager.regions
    
    # Add region with None name
    coordinate_manager.add_region(None, QRect(0, 0, 100, 100), CoordinateSpace.SCREEN)
    assert None not in coordinate_manager.regions
    
    # Add region with invalid space
    coordinate_manager.add_region("test", QRect(0, 0, 100, 100), "INVALID")
    assert "test" not in coordinate_manager.regions
    
    # Add valid region
    coordinate_manager.add_region("test", QRect(0, 0, 100, 100), CoordinateSpace.SCREEN)
    assert "test" in coordinate_manager.regions

def test_is_valid_coordinate_physical_space(coordinate_manager, mock_window_tracker):
    """Test coordinate validation in physical space."""
    # Setup window tracker
    window_rect = QRect(0, 0, 800, 600)
    mock_window_tracker.get_window_rect.return_value = window_rect
    mock_window_tracker.dpi_scale = 2.0  # Set DPI scale
    
    # Test physical coordinates
    # Note: Physical coordinates are validated against the screen resolution,
    # not the window rect. Since we can't mock the screen resolution easily,
    # we'll test the basic validation logic.
    point = QPoint(100, 100)
    assert coordinate_manager.is_valid_coordinate(point, CoordinateSpace.PHYSICAL)
    
    # Test invalid coordinates (negative)
    invalid_point = QPoint(-100, -100)
    assert not coordinate_manager.is_valid_coordinate(invalid_point, CoordinateSpace.PHYSICAL) 