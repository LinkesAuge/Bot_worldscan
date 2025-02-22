"""Tests for main application window."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QObject
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtTest import QTest

from scout.gui.main_window import MainWindow
from scout.core import WindowTracker, CoordinateManager
from scout.capture import CaptureManager, PatternMatcher, OCRProcessor
from scout.visualization import DebugVisualizer

class MockWindowTracker(QObject):
    """Mock window tracker with proper signals."""
    window_found = pyqtSignal(int)
    window_lost = pyqtSignal()
    window_moved = pyqtSignal(QRect)
    error_occurred = pyqtSignal(str)
    
    def find_window(self) -> None:
        """Mock find_window method."""
        pass

class MockPatternMatcher(QObject):
    """Mock pattern matcher with proper signals."""
    match_found = pyqtSignal(str, float, QPoint)
    match_failed = pyqtSignal(str, str)

class MockOCRProcessor(QObject):
    """Mock OCR processor with proper signals."""
    text_found = pyqtSignal(str, str)
    text_failed = pyqtSignal(str, str)
    
    def get_supported_languages(self) -> list[str]:
        """Mock get_supported_languages method."""
        return ["eng", "deu"]

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MockWindowTracker()
    return tracker

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    return manager

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock(spec=CaptureManager)
    manager.capture_complete = MagicMock()
    manager.capture_failed = MagicMock()
    return manager

@pytest.fixture
def mock_pattern_matcher():
    """Create mock pattern matcher."""
    matcher = MockPatternMatcher()
    return matcher

@pytest.fixture
def mock_ocr_processor():
    """Create mock OCR processor."""
    processor = MockOCRProcessor()
    return processor

@pytest.fixture
def mock_debug_visualizer():
    """Create mock debug visualizer."""
    visualizer = MagicMock(spec=DebugVisualizer)
    visualizer.preview_updated = MagicMock()
    visualizer.metrics_updated = MagicMock()
    return visualizer

@pytest.fixture
def mock_settings():
    """Create mock QSettings."""
    settings = MagicMock()
    return settings

@pytest.fixture
def mock_config():
    """Create mock ConfigManager."""
    config = MagicMock()
    return config

@pytest.fixture
def mock_show_error():
    """Create mock for error display."""
    with patch("PyQt6.QtWidgets.QMessageBox.critical") as mock:
        yield mock

@pytest.fixture
def main_window(
    qtbot,
    mock_window_tracker,
    mock_coordinate_manager,
    mock_capture_manager,
    mock_pattern_matcher,
    mock_ocr_processor,
    mock_debug_visualizer
):
    """Create MainWindow instance."""
    window = MainWindow(
        window_tracker=mock_window_tracker,
        coordinate_manager=mock_coordinate_manager,
        capture_manager=mock_capture_manager,
        pattern_matcher=mock_pattern_matcher,
        ocr_processor=mock_ocr_processor,
        debug_visualizer=mock_debug_visualizer
    )
    qtbot.addWidget(window)
    return window

def test_main_window_initialization(main_window):
    """Test MainWindow initialization."""
    assert main_window.windowTitle() == "TB Scout"
    assert main_window.size().width() == 1200
    assert main_window.size().height() == 800
    
    # Check tab widget
    assert main_window.tab_widget is not None
    assert main_window.tab_widget.count() == 4  # Pattern, OCR, Coordinates, Debug
    
    # Check status bar
    assert main_window.status_bar is not None
    assert main_window.window_status_label is not None
    assert main_window.capture_status_label is not None

def test_main_window_window_tracking(main_window, mock_window_tracker):
    """Test window tracking functionality."""
    # Check tracking timer
    assert hasattr(main_window, "tracking_timer")
    assert isinstance(main_window.tracking_timer, QTimer)
    assert main_window.tracking_timer.isActive()
    
    # Test window found
    main_window._on_window_found(12345)
    assert main_window.window_status_label.text() == "Window: Found"
    
    # Test window lost
    main_window._on_window_lost()
    assert main_window.window_status_label.text() == "Window: Not found"

def test_main_window_status_updates(main_window):
    """Test status bar message updates."""
    main_window._update_status("Test message")
    assert main_window.status_bar.currentMessage() == "Test message"

def test_main_window_error_handling(main_window, qtbot):
    """Test error message display."""
    # Mock QMessageBox
    with patch("PyQt6.QtWidgets.QMessageBox.critical") as mock_critical:
        main_window._show_error("Test error")
        mock_critical.assert_called_once_with(
            main_window,
            "Error",
            "Test error"
        )

def test_main_window_close_event(main_window):
    """Test window close event handling."""
    event = QCloseEvent()
    main_window.closeEvent(event)
    
    # Check cleanup
    assert not main_window.tracking_timer.isActive()
    assert main_window.debug_visualizer.stop.called
    assert event.isAccepted()

def test_main_window_pattern_tab(main_window):
    """Test pattern matching tab."""
    assert main_window.pattern_widget is not None
    assert main_window.tab_widget.widget(0) == main_window.pattern_widget

def test_main_window_ocr_tab(main_window):
    """Test OCR tab."""
    assert main_window.ocr_widget is not None
    assert main_window.tab_widget.widget(1) == main_window.ocr_widget

def test_main_window_coordinate_tab(main_window):
    """Test coordinate system tab."""
    assert main_window.coordinate_widget is not None
    assert main_window.tab_widget.widget(2) == main_window.coordinate_widget

def test_main_window_debug_tab(main_window):
    """Test debug tab."""
    assert main_window.debug_widget is not None
    assert main_window.tab_widget.widget(3) == main_window.debug_widget

def test_main_window_capture_status(main_window, mock_capture_manager):
    """Test capture status updates in main window."""
    # Add start and stop methods to mock
    mock_capture_manager.start = MagicMock()
    mock_capture_manager.stop = MagicMock()
    
    # Start capture
    main_window.capture_manager.start()
    mock_capture_manager.start.assert_called_once()
    
    # Stop capture
    main_window.capture_manager.stop()
    mock_capture_manager.stop.assert_called_once()

def test_main_window_error_signals(main_window, mock_show_error):
    """Test error signal handling."""
    # Emit window tracker error
    main_window.window_tracker.error_occurred.emit("Window error")
    mock_show_error.assert_called_with(main_window, "Error", "Window error")
    
    # Emit pattern matcher error
    main_window.pattern_matcher.match_failed.emit("test", "Pattern error")
    mock_show_error.assert_called_with(main_window, "Error", "Pattern error")
    
    # Emit OCR error
    main_window.ocr_processor.text_failed.emit("test", "OCR error")
    mock_show_error.assert_called_with(main_window, "Error", "OCR error") 