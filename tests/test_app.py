"""Tests for main application class."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from scout.app import TBScoutApp

@pytest.fixture
def mock_window_tracker():
    """Create mock window tracker."""
    tracker = MagicMock()
    tracker.error_occurred = MagicMock()
    return tracker

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    return MagicMock()

@pytest.fixture
def mock_capture_manager():
    """Create mock capture manager."""
    manager = MagicMock()
    manager.capture_failed = MagicMock()
    return manager

@pytest.fixture
def mock_pattern_matcher():
    """Create mock pattern matcher."""
    matcher = MagicMock()
    matcher.match_failed = MagicMock()
    return matcher

@pytest.fixture
def mock_ocr_processor():
    """Create mock OCR processor."""
    processor = MagicMock()
    processor.text_failed = MagicMock()
    return processor

@pytest.fixture
def mock_debug_visualizer():
    """Create mock debug visualizer."""
    return MagicMock()

@pytest.fixture
def mock_main_window():
    """Create mock main window."""
    window = MagicMock()
    window.show = MagicMock()
    return window

@pytest.fixture
def mock_config():
    """Create mock config manager."""
    config = MagicMock()
    debug_config = MagicMock()
    debug_config.enabled = False
    config.get_debug_config.return_value = debug_config
    return config

@pytest.fixture
def app(
    mock_window_tracker,
    mock_coordinate_manager,
    mock_capture_manager,
    mock_pattern_matcher,
    mock_ocr_processor,
    mock_debug_visualizer,
    mock_main_window,
    mock_config
):
    """Create TBScoutApp instance."""
    with patch("scout.app.WindowTracker", return_value=mock_window_tracker), \
         patch("scout.app.CoordinateManager", return_value=mock_coordinate_manager), \
         patch("scout.app.CaptureManager", return_value=mock_capture_manager), \
         patch("scout.app.PatternMatcher", return_value=mock_pattern_matcher), \
         patch("scout.app.OCRProcessor", return_value=mock_ocr_processor), \
         patch("scout.app.DebugVisualizer", return_value=mock_debug_visualizer), \
         patch("scout.app.MainWindow", return_value=mock_main_window), \
         patch("scout.app.QApplication") as mock_qapp:
        
        # Setup QApplication mock
        instance = mock_qapp.return_value
        instance.exec.return_value = 0
        mock_qapp.instance.return_value = instance
        
        app = TBScoutApp(config_path="tests/data/test_config.ini", debug=True)
        app.config = mock_config  # Inject mock config
        return app

def test_app_initialization(app):
    """Test TBScoutApp initialization."""
    assert app.window_tracker is not None
    assert app.coordinate_manager is not None
    assert app.capture_manager is not None
    assert app.pattern_matcher is not None
    assert app.ocr_processor is not None
    assert app.debug_visualizer is not None
    assert app.main_window is not None

def test_app_error_signals(mock_window_tracker):
    """Test error signal handling."""
    app = TBScoutApp()
    
    # Track errors
    errors = []
    def on_error(msg):
        errors.append(msg)
    
    app.error_occurred.connect(on_error)
    
    # Trigger error
    app.window_tracker.error_occurred.emit("Test error")
    
    assert len(errors) == 1
    assert errors[0] == "Test error"

def test_app_error_handling(mock_window_tracker):
    """Test error handling."""
    app = TBScoutApp()
    
    # Track errors
    errors = []
    def on_error(msg):
        errors.append(msg)
    
    app.error_occurred.connect(on_error)
    
    # Trigger error
    app._handle_error("Test error")
    
    assert len(errors) == 1
    assert errors[0] == "Test error"

def test_app_run(app, mock_window_tracker):
    """Test normal app execution."""
    # Setup window tracker
    mock_window_tracker.window_found.emit()
    
    # Run app
    app.run()
    
    # Verify app is running
    assert app.running

def test_app_run_with_error(app, mock_window_tracker):
    """Test app execution with error."""
    # Setup error tracking
    errors = []
    
    def on_error(error):
        errors.append(error)
    
    app.error.connect(on_error)
    
    # Simulate error during run
    mock_window_tracker.window_error.emit("Test error")
    app.run()
    
    # Verify error was handled
    assert len(errors) == 1
    assert "Test error" in errors[0]
    assert not app.running

def test_app_run_with_debug(app, mock_window_tracker):
    """Test app execution with debug mode."""
    # Enable debug mode
    app.debug = True
    
    # Run app
    app.run()
    
    # Verify debug components are active
    assert app.debug_window.isVisible()
    assert app.debug_visualizer.active

def test_app_debug_info(app):
    """Test getting debug information."""
    debug_info = app.get_debug_info()
    
    assert "window" in debug_info
    assert "capture" in debug_info
    assert "pattern" in debug_info
    assert "ocr" in debug_info

def test_app_run_with_error(app):
    """Test running the application with error."""
    # Setup error
    app.app.exec.side_effect = Exception("Test error")
    
    # Run app
    exit_code = app.run()
    
    # Check error was handled
    assert exit_code == 1

def test_app_run_with_debug(app):
    """Test running the application in debug mode."""
    # Enable debug mode
    app.config.get_debug_config().enabled = True
    
    # Run app
    app.run()
    
    # Check debug visualizer was started
    assert app.debug_visualizer.start.called

def test_app_run(app):
    """Test running the application."""
    # Run app
    exit_code = app.run()
    
    # Check app was started
    assert app.main_window.show.called
    assert app.app.exec.called
    assert exit_code == 0 