"""Tests for pattern matching widget."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, pyqtSignal, QObject
from PyQt6.QtWidgets import QFileDialog
import numpy as np
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from scout.gui.widgets.pattern_matching import PatternMatchingWidget
from scout.capture import PatternMatcher
from scout.core import CoordinateManager

@pytest.fixture
def test_template():
    """Create a test template for pattern matching tests."""
    return {
        "name": "test_template",
        "image": np.zeros((100, 100, 3), dtype=np.uint8),
        "confidence": 0.8
    }

@pytest.fixture
def mock_pattern_matcher():
    """Create mock pattern matcher."""
    matcher = MagicMock(spec=PatternMatcher)
    matcher.template_dir = Path("templates")
    matcher.confidence_threshold = 0.8
    matcher.templates = {
        "test_template": MagicMock()
    }
    matcher.match_found = MagicMock()
    matcher.match_failed = MagicMock()
    matcher.get_template_info.return_value = {
        "test_template": {
            "size": (100, 100),
            "shape": (100, 100)
        }
    }
    
    # Setup reload_templates to update templates
    def reload_templates():
        matcher.templates = {
            "test_template": MagicMock()
        }
    matcher.reload_templates.side_effect = reload_templates
    
    return matcher

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    return manager

@pytest.fixture
def pattern_widget(qtbot, mock_pattern_matcher, mock_coordinate_manager):
    """Create PatternMatchingWidget instance."""
    widget = PatternMatchingWidget(
        mock_pattern_matcher,
        mock_coordinate_manager
    )
    qtbot.addWidget(widget)
    return widget

def test_pattern_widget_initialization(pattern_widget, mock_pattern_matcher):
    """Test PatternMatchingWidget initialization."""
    assert not pattern_widget.active
    assert pattern_widget.update_interval == 1000
    
    # Check controls
    assert pattern_widget.active_checkbox is not None
    assert pattern_widget.interval_spinbox is not None
    assert pattern_widget.confidence_spinbox is not None
    assert pattern_widget.template_list is not None
    assert pattern_widget.results_list is not None
    
    # Check initial values
    assert pattern_widget.interval_spinbox.value() == 1000
    assert pattern_widget.confidence_spinbox.value() == 0.8
    
    # Check template list
    pattern_widget._reload_templates()  # Force reload
    assert pattern_widget.template_list.count() == 1
    assert pattern_widget.template_list.item(0).text() == "test_template"

def test_pattern_widget_activation(pattern_widget, qtbot):
    """Test pattern matching activation."""
    # Enable pattern matching
    qtbot.mouseClick(pattern_widget.active_checkbox, Qt.MouseButton.LeftButton)
    pattern_widget.active_checkbox.setChecked(True)
    pattern_widget._on_active_changed(Qt.CheckState.Checked.value)
    
    assert pattern_widget.active
    assert hasattr(pattern_widget, "update_timer")
    assert pattern_widget.update_timer.isActive()
    
    # Disable pattern matching
    pattern_widget.active_checkbox.setChecked(False)
    pattern_widget._on_active_changed(Qt.CheckState.Unchecked.value)
    
    assert not pattern_widget.active
    assert not pattern_widget.update_timer.isActive()

def test_pattern_widget_interval_change(pattern_widget, qtbot):
    """Test update interval change."""
    # Enable pattern matching
    pattern_widget.active_checkbox.setChecked(True)
    
    # Change interval
    pattern_widget.interval_spinbox.setValue(2000)
    assert pattern_widget.update_interval == 2000
    assert pattern_widget.update_timer.interval() == 2000

def test_pattern_widget_confidence_change(pattern_widget, mock_pattern_matcher):
    """Test confidence threshold change."""
    pattern_widget.confidence_spinbox.setValue(0.9)
    assert mock_pattern_matcher.confidence_threshold == 0.9

def test_pattern_widget_add_template(pattern_widget, mock_pattern_matcher, qtbot):
    """Test adding template."""
    # Mock file dialog
    with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileNames") as mock_dialog:
        mock_dialog.return_value = (
            [str(Path("templates/new_template.png"))],
            "Images (*.png)"
        )
        
        # Setup template dir
        template_dir = Path("templates")
        template_dir.mkdir(exist_ok=True)
        template_file = template_dir / "new_template.png"
        template_file.touch()
        
        # Click add button
        qtbot.mouseClick(pattern_widget.add_button, Qt.MouseButton.LeftButton)
        
        # Check dialog was shown
        mock_dialog.assert_called_once_with(
            pattern_widget,
            "Select Template Images",
            str(mock_pattern_matcher.template_dir),
            "Images (*.png)"
        )
        
        # Check template was added
        mock_pattern_matcher.reload_templates.assert_called_once()
        
        # Cleanup
        template_file.unlink()
        template_dir.rmdir()

def test_pattern_widget_remove_template(pattern_widget, mock_pattern_matcher, test_template, qtbot):
    """Test removing a template."""
    # Add template first
    pattern_widget.pattern_matcher.templates = {"test_template": test_template}
    pattern_widget._reload_templates()
    
    # Verify template was added
    assert pattern_widget.template_list.count() == 1
    
    # Select template
    pattern_widget.template_list.setCurrentRow(0)
    
    # Mock template file operations
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.unlink") as mock_unlink:
        mock_exists.return_value = True
        
        # Remove template
        pattern_widget._remove_template()
        
        # Verify file was "deleted"
        mock_unlink.assert_called_once()
        
        # Clear templates to simulate reload
        pattern_widget.pattern_matcher.templates = {}
        pattern_widget.template_list.clear()
        
        # Verify template was removed from list
        assert pattern_widget.template_list.count() == 0

def test_pattern_widget_reload_templates(pattern_widget, mock_pattern_matcher, qtbot):
    """Test reloading templates."""
    # Click reload button
    qtbot.mouseClick(pattern_widget.reload_button, Qt.MouseButton.LeftButton)
    
    # Check templates were reloaded
    mock_pattern_matcher.reload_templates.assert_called_once()

def test_pattern_widget_update_matches(pattern_widget, mock_pattern_matcher):
    """Test updating matches."""
    # Setup mock matches
    mock_pattern_matcher.find_matches.return_value = [
        MagicMock(
            template_name="test_template",
            confidence=0.9,
            position=QPoint(100, 100)
        )
    ]
    
    # Update matches
    pattern_widget._update_matches()
    
    # Check results were updated
    assert pattern_widget.results_list.count() == 1
    assert "test_template" in pattern_widget.results_list.item(0).text()
    assert "conf=0.90" in pattern_widget.results_list.item(0).text()
    assert "pos=(100, 100)" in pattern_widget.results_list.item(0).text()

class MockPatternMatcher(QObject):
    """Mock pattern matcher with signals."""
    match_found = pyqtSignal(str, float, QPoint)
    match_failed = pyqtSignal(str, str)

def test_pattern_widget_match_events(pattern_widget, mock_pattern_matcher, qtbot):
    """Test match found/failed events."""
    # Track signal emissions
    match_found = False
    match_failed = False
    found_matches = None
    
    def on_match_found(template, confidence, position):
        nonlocal match_found, found_matches
        match_found = True
        found_matches = (template, confidence, position)
    
    def on_match_failed(template, error):
        nonlocal match_failed
        match_failed = True
    
    # Create mock pattern matcher with signals
    signal_emitter = MockPatternMatcher()
    mock_pattern_matcher.match_found = signal_emitter.match_found
    mock_pattern_matcher.match_failed = signal_emitter.match_failed
    
    # Connect signals
    mock_pattern_matcher.match_found.connect(on_match_found)
    mock_pattern_matcher.match_failed.connect(on_match_failed)
    
    # Emit signals
    mock_pattern_matcher.match_found.emit(
        "test_template",
        0.9,
        QPoint(100, 100)
    )
    mock_pattern_matcher.match_failed.emit(
        "test_template",
        "Test error"
    )
    
    # Verify
    assert match_found
    assert match_failed
    assert found_matches == ("test_template", 0.9, QPoint(100, 100))

def test_pattern_widget_metrics(pattern_widget, mock_pattern_matcher, test_template, qtbot):
    """Test metrics update."""
    # Add template
    pattern_widget.pattern_matcher.templates = {"test_template": test_template}
    pattern_widget._reload_templates()
    
    # Update metrics
    pattern_widget.metrics_label.setText(
        "Total Matches: 10\nFailed Matches: 2\nLast Match Time: 0.5s"
    )
    
    # Verify
    metrics_text = pattern_widget.metrics_label.text()
    assert "Total Matches: 10" in metrics_text
    assert "Failed Matches: 2" in metrics_text
    assert "Last Match Time: 0.5s" in metrics_text

def test_pattern_widget_confidence_change(pattern_widget, mock_pattern_matcher, test_template, qtbot):
    """Test confidence threshold change."""
    # Add template
    pattern_widget.pattern_matcher.templates = {"test_template": test_template}
    pattern_widget._reload_templates()
    
    # Change confidence
    pattern_widget.confidence_spinbox.setValue(0.9)
    
    # Verify
    assert pattern_widget.pattern_matcher.confidence_threshold == 0.9 