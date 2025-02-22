"""Tests for debug visualization widget."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from scout.gui.widgets.debug import DebugWidget
from scout.visualization import DebugVisualizer

@pytest.fixture
def mock_debug_visualizer():
    """Create mock debug visualizer."""
    visualizer = MagicMock(spec=DebugVisualizer)
    visualizer.preview_updated = MagicMock()
    visualizer.metrics_updated = MagicMock()
    visualizer.update_timer = MagicMock()
    return visualizer

@pytest.fixture
def debug_widget(qtbot, mock_debug_visualizer):
    """Create DebugWidget instance."""
    widget = DebugWidget(mock_debug_visualizer)
    qtbot.addWidget(widget)
    return widget

def test_debug_widget_initialization(debug_widget):
    """Test DebugWidget initialization."""
    # Check controls
    assert debug_widget.active_checkbox is not None
    assert debug_widget.interval_spinbox is not None
    assert debug_widget.show_coords is not None
    assert debug_widget.show_regions is not None
    assert debug_widget.show_matches is not None
    assert debug_widget.preview_label is not None
    assert debug_widget.metrics_text is not None
    assert debug_widget.save_screenshot is not None
    assert debug_widget.clear_screenshots is not None
    
    # Check initial values
    assert debug_widget.interval_spinbox.value() == 1000
    assert debug_widget.show_coords.isChecked()
    assert debug_widget.show_regions.isChecked()
    assert debug_widget.show_matches.isChecked()

def test_debug_widget_activation(debug_widget, qtbot):
    """Test activating and deactivating the debug widget."""
    # Initially inactive
    assert not debug_widget.is_active
    
    # Activate
    debug_widget.activate()
    assert debug_widget.is_active
    assert debug_widget.timer.isActive()
    
    # Deactivate
    debug_widget.deactivate()
    assert not debug_widget.is_active
    assert not debug_widget.timer.isActive()

def test_debug_widget_text_event(debug_widget, qtbot):
    """Test handling text events in debug widget."""
    # Setup signal tracking
    text_received = False
    received_text = None
    
    def on_text_received(text):
        nonlocal text_received, received_text
        text_received = True
        received_text = text
    
    debug_widget.text_received.connect(on_text_received)
    
    # Emit text event
    test_text = "Test OCR Text"
    debug_widget.handle_text_event("test_region", test_text)
    
    assert text_received
    assert received_text == test_text
    assert debug_widget.text_history[-1] == test_text

def test_debug_widget_clear(debug_widget, qtbot):
    """Test clearing debug widget history."""
    # Add some test text
    debug_widget.handle_text_event("test_region", "Test 1")
    debug_widget.handle_text_event("test_region", "Test 2")
    
    assert len(debug_widget.text_history) == 2
    
    # Clear history
    debug_widget.clear_history()
    assert len(debug_widget.text_history) == 0
    assert debug_widget.text_display.toPlainText() == ""

def test_debug_widget_update_display(debug_widget, qtbot):
    """Test updating the debug widget display."""
    # Add test text
    test_text = "Test Display Text"
    debug_widget.handle_text_event("test_region", test_text)
    
    # Check display
    display_text = debug_widget.text_display.toPlainText()
    assert test_text in display_text
    assert debug_widget.text_history[-1] == test_text

def test_debug_widget_max_history(debug_widget, qtbot):
    """Test debug widget history limit."""
    max_history = debug_widget.max_history_size
    
    # Add more items than max history
    for i in range(max_history + 5):
        debug_widget.handle_text_event("test_region", f"Test {i}")
    
    assert len(debug_widget.text_history) == max_history
    assert debug_widget.text_history[0] == f"Test {5}"  # Oldest remaining entry
    assert debug_widget.text_history[-1] == f"Test {max_history + 4}"  # Latest entry

def test_debug_widget_interval_change(debug_widget, mock_debug_visualizer):
    """Test update interval change."""
    debug_widget.interval_spinbox.setValue(2000)
    mock_debug_visualizer.update_timer.setInterval.assert_called_once_with(2000)

def test_debug_widget_preview_update(debug_widget):
    """Test preview image update."""
    # Create test image
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    q_image = QImage(
        image.data,
        100,
        100,
        300,
        QImage.Format.Format_RGB888
    )
    
    # Update preview
    debug_widget._on_preview_updated(q_image)
    
    # Check preview was updated
    assert not debug_widget.preview_label.pixmap().isNull()

def test_debug_widget_metrics_update(debug_widget):
    """Test updating debug metrics display."""
    # Create test metrics
    metrics = {
        'window': {'window_found': True, 'window_handle': 12345},
        'capture': {'total_captures': 10, 'failed_captures': 1},
        'pattern': {'templates': {'test_template': {'size': (100, 100)}}},
        'ocr': {'metrics': {'total_extractions': 5, 'failed_extractions': 0}}
    }
    
    # Update metrics
    debug_widget._on_metrics_updated(metrics)
    
    # Get displayed text
    metrics_text = debug_widget.metrics_text.toPlainText()
    
    # Verify metrics are displayed correctly
    assert "window_found: True" in metrics_text
    assert "window_handle: 12345" in metrics_text
    assert "total_captures: 10" in metrics_text
    assert "failed_captures: 1" in metrics_text
    assert "'test_template': {'size': (100, 100)}" in metrics_text
    assert "total_extractions: 5" in metrics_text
    assert "failed_extractions: 0" in metrics_text

def test_debug_widget_save_screenshot(debug_widget, qtbot):
    """Test saving screenshot."""
    # Create test preview
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    q_image = QImage(
        image.data,
        100,
        100,
        300,
        QImage.Format.Format_RGB888
    )
    debug_widget.preview_label.setPixmap(QPixmap.fromImage(q_image))
    
    # Mock save
    with patch("PyQt6.QtGui.QPixmap.save") as mock_save:
        # Click save button
        qtbot.mouseClick(debug_widget.save_screenshot, Qt.MouseButton.LeftButton)
        
        # Check screenshot was saved
        mock_save.assert_called_once_with("debug_screenshots/manual_capture.png")

def test_debug_widget_clear_screenshots(debug_widget, qtbot):
    """Test clearing screenshots."""
    # Mock glob and remove
    with patch("glob.glob") as mock_glob, \
         patch("os.remove") as mock_remove:
        
        mock_glob.return_value = [
            "debug_screenshots/test1.png",
            "debug_screenshots/test2.png"
        ]
        
        # Click clear button
        qtbot.mouseClick(debug_widget.clear_screenshots, Qt.MouseButton.LeftButton)
        
        # Check screenshots were cleared
        mock_glob.assert_called_once_with("debug_screenshots/*.png")
        assert mock_remove.call_count == 2

def test_debug_widget_visualization_options(debug_widget):
    """Test visualization options."""
    # Create test preview
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    q_image = QImage(
        image.data,
        100,
        100,
        300,
        QImage.Format.Format_RGB888
    )
    debug_widget.preview_label.setPixmap(QPixmap.fromImage(q_image))
    
    # Toggle options
    debug_widget.show_coords.setChecked(False)
    debug_widget.show_regions.setChecked(False)
    debug_widget.show_matches.setChecked(False)
    
    # Update preview
    debug_widget._update_preview()
    
    # Check preview was updated
    assert not debug_widget.preview_label.pixmap().isNull() 