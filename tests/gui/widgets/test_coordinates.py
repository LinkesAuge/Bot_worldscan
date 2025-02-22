"""Tests for coordinate system widget."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QPoint, QRect
from scout.gui.widgets.coordinates import CoordinateWidget
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
    manager.regions = {
        "test_region": {
            "rect": QRect(200, 200, 100, 100),
            "space": CoordinateSpace.SCREEN
        }
    }
    return manager

@pytest.fixture
def coordinate_widget(qtbot, mock_window_tracker, mock_coordinate_manager):
    """Create CoordinateWidget instance."""
    widget = CoordinateWidget(
        mock_window_tracker,
        mock_coordinate_manager
    )
    qtbot.addWidget(widget)
    return widget

def test_coordinate_widget_initialization(coordinate_widget):
    """Test CoordinateWidget initialization."""
    # Check controls
    assert coordinate_widget.space_combo is not None
    assert coordinate_widget.x_input is not None
    assert coordinate_widget.y_input is not None
    assert coordinate_widget.from_space is not None
    assert coordinate_widget.to_space is not None
    assert coordinate_widget.transform_button is not None
    assert coordinate_widget.region_name is not None
    assert coordinate_widget.region_list is not None
    
    # Check initial values
    assert coordinate_widget.space_combo.currentText() == CoordinateSpace.SCREEN
    assert coordinate_widget.x_input.value() == 0
    assert coordinate_widget.y_input.value() == 0
    assert coordinate_widget.from_space.currentText() == CoordinateSpace.SCREEN
    assert coordinate_widget.to_space.currentText() == CoordinateSpace.SCREEN

def test_coordinate_widget_space_change(coordinate_widget, mock_coordinate_manager):
    """Test coordinate space change."""
    coordinate_widget.space_combo.setCurrentText(CoordinateSpace.WINDOW)
    mock_coordinate_manager.set_active_spaces.assert_called_once_with([CoordinateSpace.WINDOW])

def test_coordinate_widget_coordinate_change(coordinate_widget):
    """Test coordinate input change."""
    # Setup signal tracking
    coordinate_changed = False
    changed_point = None
    changed_space = None
    
    def on_coordinate_changed(point, space):
        nonlocal coordinate_changed, changed_point, changed_space
        coordinate_changed = True
        changed_point = point
        changed_space = space
    
    coordinate_widget.coordinate_changed.connect(on_coordinate_changed)
    
    # Change coordinates
    coordinate_widget.x_input.setValue(100)
    coordinate_widget.y_input.setValue(200)
    
    assert coordinate_changed
    assert changed_point == QPoint(100, 200)
    assert changed_space == CoordinateSpace.SCREEN

def test_coordinate_widget_transform(coordinate_widget, mock_coordinate_manager, qtbot):
    """Test coordinate transformation."""
    # Setup mock transformation
    mock_coordinate_manager.transform_point.return_value = QPoint(150, 250)
    
    # Set coordinates
    coordinate_widget.x_input.setValue(100)
    coordinate_widget.y_input.setValue(200)
    
    # Set spaces
    coordinate_widget.from_space.setCurrentText(CoordinateSpace.SCREEN)
    coordinate_widget.to_space.setCurrentText(CoordinateSpace.WINDOW)
    
    # Click transform button
    qtbot.mouseClick(coordinate_widget.transform_button, Qt.MouseButton.LeftButton)
    
    # Check transformation was called
    mock_coordinate_manager.transform_point.assert_called_once_with(
        QPoint(100, 200),
        CoordinateSpace.SCREEN,
        CoordinateSpace.WINDOW
    )
    
    # Check result display
    assert "Result: (150, 250)" in coordinate_widget.result_label.text()

def test_coordinate_widget_add_region(coordinate_widget, mock_coordinate_manager, qtbot):
    """Test adding a region to the coordinate widget."""
    # Set region name
    coordinate_widget.region_name.setText("test_region")
    
    # Get current space
    space = coordinate_widget.space_combo.currentText()
    
    # Add region
    qtbot.mouseClick(coordinate_widget.add_region, Qt.MouseButton.LeftButton)
    
    # Verify region was added
    mock_coordinate_manager.add_region.assert_called_once()
    args = mock_coordinate_manager.add_region.call_args[0]
    assert args[0] == "test_region"  # name
    assert isinstance(args[1], QRect)  # rect
    assert args[2] == space  # space
    
    # Verify UI was updated
    assert coordinate_widget.region_list.count() == 1
    assert coordinate_widget.region_list.item(0).text() == "test_region"
    assert coordinate_widget.region_name.text() == ""  # Input should be cleared

def test_coordinate_widget_remove_region(coordinate_widget, mock_coordinate_manager, qtbot):
    """Test removing a region from the coordinate widget."""
    # Add a test region
    test_region = QRect(0, 0, 100, 100)
    mock_coordinate_manager.regions = {"test_region": test_region}
    coordinate_widget.region_list.addItem("test_region")
    
    # Select the region
    coordinate_widget.region_list.setCurrentRow(0)
    
    # Remove the region
    qtbot.mouseClick(coordinate_widget.remove_region, Qt.MouseButton.LeftButton)
    
    # Verify region was removed
    mock_coordinate_manager.remove_region.assert_called_once_with("test_region")
    assert coordinate_widget.region_list.count() == 0

def test_coordinate_widget_region_selection(coordinate_widget, mock_coordinate_manager, qtbot):
    """Test region selection in the coordinate widget."""
    # Add a test region
    test_region = QRect(0, 0, 100, 100)
    mock_coordinate_manager.regions = {"test_region": test_region}
    coordinate_widget.region_list.addItem("test_region")
    
    # Track region selection signal
    region_selected = False
    selected_name = None
    
    def on_region_selected(name):
        nonlocal region_selected, selected_name
        region_selected = True
        selected_name = name
    
    coordinate_widget.region_selected.connect(on_region_selected)
    
    # Set up mock to return region
    mock_coordinate_manager.get_region.return_value = test_region
    
    # Select the region
    coordinate_widget.region_list.setCurrentRow(0)
    
    # Verify selection
    assert region_selected
    assert selected_name == "test_region"
    assert coordinate_widget.x_input.value() == 0
    assert coordinate_widget.y_input.value() == 0

def test_coordinate_widget_metrics(coordinate_widget, mock_window_tracker):
    """Test metrics display."""
    # Update metrics
    coordinate_widget._update_metrics()
    
    # Check metrics text
    metrics_text = coordinate_widget.metrics_label.text()
    assert "Window Found: True" in metrics_text
    assert "Window Handle: 12345" in metrics_text
    assert "Window Rect: " in metrics_text
    assert "Client Rect: " in metrics_text
    assert "DPI Scale: 1.0" in metrics_text
    assert "Active Space: SCREEN" in metrics_text
    assert "Regions: 1" in metrics_text 