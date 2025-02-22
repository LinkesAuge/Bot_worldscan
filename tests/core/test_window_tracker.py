"""Tests for window tracking system."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QRect, QPoint
from scout.core import WindowTracker
from scout.config import ConfigManager

@pytest.fixture
def mock_win32gui():
    """Mock win32gui functions."""
    with patch("win32gui.FindWindow") as mock_find, \
         patch("win32gui.GetWindowRect") as mock_rect, \
         patch("win32gui.GetClientRect") as mock_client, \
         patch("win32gui.ClientToScreen") as mock_screen, \
         patch("win32gui.IsWindowVisible") as mock_visible:
        
        # Setup default behavior
        mock_find.return_value = 12345
        mock_rect.return_value = (100, 100, 900, 700)  # x1, y1, x2, y2
        mock_client.return_value = (0, 0, 780, 580)  # left, top, right, bottom
        mock_screen.return_value = (110, 120)  # Client area offset
        mock_visible.return_value = True
        
        yield {
            "find": mock_find,
            "rect": mock_rect,
            "client": mock_client,
            "screen": mock_screen,
            "visible": mock_visible
        }

@pytest.fixture
def config():
    """Create mock config."""
    config = MagicMock(spec=ConfigManager)
    window_config = MagicMock()
    window_config.standalone_priority = True
    window_config.browser_detection = True
    window_config.update_interval = 1000
    config.get_window_config.return_value = window_config
    return config

@pytest.fixture
def window_tracker(config):
    """Create WindowTracker instance."""
    return WindowTracker(config)

def test_window_tracker_initialization(window_tracker):
    """Test WindowTracker initialization."""
    assert window_tracker.hwnd == 0
    assert window_tracker.window_type == ""
    assert window_tracker.dpi_scale == 1.0
    assert window_tracker.standalone_priority is True
    assert window_tracker.browser_detection is True
    assert window_tracker.update_interval == 1000

def test_find_standalone_window(window_tracker, mock_win32gui):
    """Test finding standalone window."""
    # Setup mock to find standalone window
    mock_win32gui["find"].side_effect = lambda cls, title: 12345 if title == "Total Battle" else 0
    
    # Track window found signal
    window_found = False
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    window_tracker.window_found.connect(on_window_found)
    
    # Find window
    success = window_tracker.find_window()
    
    assert success
    assert window_found
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"

def test_find_browser_window(window_tracker, mock_win32gui):
    """Test finding browser window."""
    # Setup mock to find browser window
    def find_window(cls, title):
        if title == "Total Battle - Chrome":
            return 12345
        return 0
    mock_win32gui["find"].side_effect = find_window
    
    # Disable standalone priority
    window_tracker.standalone_priority = False
    
    # Find window
    success = window_tracker.find_window()
    
    assert success
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "BROWSER"

def test_window_not_found(window_tracker, mock_win32gui):
    """Test handling when no window is found."""
    # Setup mock to find no window
    mock_win32gui["find"].return_value = 0
    
    # Track window lost signal
    window_lost = False
    def on_window_lost():
        nonlocal window_lost
        window_lost = True
    window_tracker.window_lost.connect(on_window_lost)
    
    # Try to find window
    success = window_tracker.find_window()
    
    assert not success
    assert window_tracker.hwnd == 0
    assert window_tracker.window_type == ""
    assert not window_lost  # Should not emit lost signal if no window was found before

def test_get_window_rect(window_tracker, mock_win32gui):
    """Test getting window rectangle."""
    # Setup window handle
    window_tracker.hwnd = 12345
    
    # Get window rect
    rect = window_tracker.get_window_rect()
    
    assert isinstance(rect, QRect)
    assert rect.left() == 100
    assert rect.top() == 100
    assert rect.width() == 800  # 900 - 100
    assert rect.height() == 600  # 700 - 100
    
    # Test with no window
    window_tracker.hwnd = 0
    assert window_tracker.get_window_rect() is None

def test_get_client_rect(window_tracker, mock_win32gui):
    """Test getting client rectangle."""
    # Setup window handle
    window_tracker.hwnd = 12345
    
    # Get client rect
    rect = window_tracker.get_client_rect()
    
    assert isinstance(rect, QRect)
    assert rect.left() == 110  # Client area offset
    assert rect.top() == 120  # Client area offset
    assert rect.width() == 780  # From GetClientRect
    assert rect.height() == 580  # From GetClientRect
    
    # Test with no window
    window_tracker.hwnd = 0
    assert window_tracker.get_client_rect() is None

def test_coordinate_conversion():
    """Test coordinate conversion with DPI scaling."""
    tracker = WindowTracker()
    tracker.dpi_scale = 1.5  # Set custom DPI scale
    
    # Test logical to physical
    physical = tracker.to_physical_pos((100, 100))
    assert physical == (150, 150)  # Scaled up by 1.5
    
    # Test physical to logical
    logical = tracker.to_logical_pos((150, 150))
    assert logical == (100, 100)  # Scaled down by 1.5
    
    # Test negative coordinates
    assert tracker.to_physical_pos((-10, -10)) == (0, 0)
    assert tracker.to_logical_pos((-10, -10)) == (0, 0)
    
    # Test None values
    assert tracker.to_physical_pos((None, None)) == (0, 0)  # type: ignore
    assert tracker.to_logical_pos((None, None)) == (0, 0)  # type: ignore

def test_window_state_signals(window_tracker, mock_win32gui, qtbot):
    """Test window state change signals."""
    # Setup signal tracking
    window_found = False
    window_lost = False
    window_moved = False
    moved_rect = None
    
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    
    def on_window_lost():
        nonlocal window_lost
        window_lost = True
    
    def on_window_moved(rect):
        nonlocal window_moved, moved_rect
        window_moved = True
        moved_rect = rect
    
    window_tracker.window_found.connect(on_window_found)
    window_tracker.window_lost.connect(on_window_lost)
    window_tracker.window_moved.connect(on_window_moved)
    
    # Find window
    window_tracker.find_window()
    assert window_found
    
    # Move window - need to get initial rect first
    rect1 = window_tracker.get_window_rect()
    window_tracker.last_rect = rect1  # Set initial rect
    
    # Now change window position
    mock_win32gui["rect"].return_value = (200, 200, 1000, 800)  # New position
    rect2 = window_tracker.get_window_rect()
    
    assert window_moved
    assert moved_rect == rect2
    
    # Lose window
    mock_win32gui["find"].return_value = 0
    window_tracker.find_window()
    assert window_lost

def test_debug_info(window_tracker, mock_win32gui):
    """Test getting debug information."""
    # Setup window state
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    window_tracker.dpi_scale = 1.5
    
    # Get debug info
    info = window_tracker.get_debug_info()
    
    assert info["window_found"] is True
    assert info["window_handle"] == 12345
    assert info["window_type"] == "STANDALONE"
    assert isinstance(info["window_rect"], QRect)
    assert isinstance(info["client_rect"], QRect)
    assert info["dpi_scale"] == 1.5

def test_find_standalone_window_with_priority(window_tracker, mock_win32gui):
    """Test finding standalone window with priority enabled."""
    # Setup mock to find both standalone and browser windows
    def find_window(cls, title):
        if title == "Total Battle":
            return 12345
        if title == "Total Battle - Chrome":
            return 67890
        return 0
    mock_win32gui["find"].side_effect = find_window
    
    # Find window with standalone priority
    window_tracker.standalone_priority = True
    success = window_tracker.find_window()
    
    assert success
    assert window_tracker.hwnd == 12345  # Should find standalone window
    assert window_tracker.window_type == "STANDALONE"

def test_find_browser_window_fallback(window_tracker, mock_win32gui):
    """Test finding browser window as fallback."""
    # Setup mock to find only browser window
    def find_window(cls, title):
        if title == "Total Battle - Chrome":
            return 12345
        return 0
    mock_win32gui["find"].side_effect = find_window
    
    # Find window with standalone priority
    window_tracker.standalone_priority = True
    success = window_tracker.find_window()
    
    assert success
    assert window_tracker.hwnd == 12345  # Should fall back to browser window
    assert window_tracker.window_type == "BROWSER"

def test_find_window_lost(window_tracker, mock_win32gui, qtbot):
    """Test window lost detection."""
    # Setup signal tracking
    window_lost = False
    def on_window_lost():
        nonlocal window_lost
        window_lost = True
    window_tracker.window_lost.connect(on_window_lost)
    
    # First find window
    mock_win32gui["find"].return_value = 12345
    window_tracker.find_window()
    
    # Then lose window
    mock_win32gui["find"].return_value = 0
    window_tracker.find_window()
    
    assert window_lost
    assert window_tracker.hwnd == 0
    assert window_tracker.window_type == ""

def test_find_window_error_handling(window_tracker, mock_win32gui, qtbot):
    """Test error handling in window finding."""
    # Setup error tracking
    error_occurred = False
    error_msg = None
    def on_error(msg):
        nonlocal error_occurred, error_msg
        error_occurred = True
        error_msg = msg
    window_tracker.error_occurred.connect(on_error)
    
    # Make FindWindow raise an error
    mock_win32gui["find"].side_effect = Exception("Test error")
    
    # Try to find window
    success = window_tracker.find_window()
    
    assert not success
    assert error_occurred
    assert "Test error" in error_msg

def test_get_window_rect_error():
    """Test error handling in getting window rectangle."""
    tracker = WindowTracker()
    tracker.hwnd = 12345  # Set invalid handle
    
    with patch("win32gui.GetWindowRect") as mock_rect:
        mock_rect.side_effect = Exception("Test error")
        
        # Try to get window rect
        rect = tracker.get_window_rect()
        
        assert rect is None

def test_get_client_rect_error():
    """Test error handling in getting client rectangle."""
    tracker = WindowTracker()
    tracker.hwnd = 12345  # Set invalid handle
    
    with patch("win32gui.GetClientRect") as mock_client:
        mock_client.side_effect = Exception("Test error")
        
        # Try to get client rect
        rect = tracker.get_client_rect()
        
        assert rect is None

def test_dpi_scaling():
    """Test DPI scaling calculations."""
    tracker = WindowTracker()
    
    # Test different DPI scales
    scales = [1.0, 1.25, 1.5, 2.0]
    for scale in scales:
        tracker.dpi_scale = scale
        
        # Test logical to physical
        logical = (100, 100)
        physical = tracker.to_physical_pos(logical)
        assert physical == (int(100 * scale), int(100 * scale))
        
        # Test physical to logical
        logical_back = tracker.to_logical_pos(physical)
        assert logical_back == logical  # Should round-trip correctly

def test_debug_info_detailed():
    """Test detailed debug information."""
    tracker = WindowTracker()
    
    # Test with no window
    info = tracker.get_debug_info()
    assert info["window_found"] is False
    assert info["window_handle"] == 0
    assert info["window_type"] == ""
    assert isinstance(info["window_rect"], QRect)
    assert isinstance(info["client_rect"], QRect)
    assert info["dpi_scale"] == 1.0
    
    # Test with window
    tracker.hwnd = 12345
    tracker.window_type = "STANDALONE"
    tracker.dpi_scale = 1.5
    
    info = tracker.get_debug_info()
    assert info["window_found"] is True
    assert info["window_handle"] == 12345
    assert info["window_type"] == "STANDALONE"
    assert isinstance(info["window_rect"], QRect)
    assert isinstance(info["client_rect"], QRect)
    assert info["dpi_scale"] == 1.5

def test_window_rect_edge_cases(qtbot):
    """Test window rectangle edge cases."""
    tracker = WindowTracker()
    tracker.hwnd = 12345
    
    with patch("win32gui.GetWindowRect") as mock_rect:
        # Test inverted coordinates
        mock_rect.return_value = (900, 700, 100, 100)  # x2 < x1, y2 < y1
        rect = tracker.get_window_rect()
        assert rect is not None
        assert rect.left() == 100
        assert rect.top() == 100
        assert rect.width() == 800
        assert rect.height() == 600
        
        # Test zero size
        mock_rect.return_value = (100, 100, 100, 100)
        rect = tracker.get_window_rect()
        assert rect is not None
        assert rect.width() == 0
        assert rect.height() == 0

def test_window_rect_conversion(qtbot):
    """Test window rectangle coordinate conversion."""
    tracker = WindowTracker()
    tracker.hwnd = 12345
    tracker.dpi_scale = 2.0  # Set high DPI scale
    
    with patch("win32gui.GetWindowRect") as mock_rect, \
         patch("win32gui.GetClientRect") as mock_client, \
         patch("win32gui.ClientToScreen") as mock_screen:
        
        # Setup mocks
        mock_rect.return_value = (100, 100, 900, 700)
        mock_client.return_value = (0, 0, 780, 580)
        mock_screen.return_value = (110, 120)
        
        # Get rectangles
        window_rect = tracker.get_window_rect()
        client_rect = tracker.get_client_rect()
        
        assert window_rect is not None
        assert client_rect is not None
        
        # Check DPI scaling is not applied (should be raw coordinates)
        assert window_rect.left() == 100
        assert window_rect.top() == 100
        assert client_rect.left() == 110
        assert client_rect.top() == 120

def test_error_handling_edge_cases(qtbot):
    """Test error handling edge cases."""
    tracker = WindowTracker()
    
    # Test coordinate conversion with None values
    assert tracker.to_physical_pos((None, None)) == (0, 0)  # type: ignore
    assert tracker.to_logical_pos((None, None)) == (0, 0)  # type: ignore
    
    # Test coordinate conversion with negative values
    assert tracker.to_physical_pos((-100, -100)) == (0, 0)
    assert tracker.to_logical_pos((-100, -100)) == (0, 0)
    
    # Test window rect with invalid handle
    tracker.hwnd = -1
    assert tracker.get_window_rect() is None
    assert tracker.get_client_rect() is None

def test_find_window_error_handling_complete(window_tracker, mock_win32gui, qtbot):
    """Test complete error handling in window finding."""
    # Setup error tracking
    errors = []
    def on_error(msg):
        nonlocal errors
        errors.append(msg)
    window_tracker.error_occurred.connect(on_error)
    
    # Test standalone window errors
    mock_win32gui["find"].side_effect = [
        Exception("Standalone error"),  # First call for standalone
        12345,  # Second call for browser
    ]
    
    success = window_tracker.find_window()
    assert success  # Should still find browser window
    assert len(errors) == 1
    assert "Standalone error" in errors[0]
    
    # Test browser window errors
    mock_win32gui["find"].side_effect = [
        0,  # No standalone window
        Exception("Browser error"),  # Error finding browser window
        0,  # Firefox not found
        0,  # Edge not found
        0   # Opera not found
    ]
    
    success = window_tracker.find_window()
    assert not success
    assert len(errors) == 2  # Only actual errors should be counted
    assert "Browser error" in errors[1]

def test_window_rect_error_handling_complete(window_tracker, mock_win32gui):
    """Test complete error handling in window rectangles."""
    window_tracker.hwnd = 12345
    
    # Test window rect errors
    mock_win32gui["rect"].side_effect = Exception("Window rect error")
    window_rect = window_tracker.get_window_rect()
    assert window_rect is None
    
    # Test client rect errors
    mock_win32gui["client"].side_effect = Exception("Client rect error")
    client_rect = window_tracker.get_client_rect()
    assert client_rect is None
    
    # Test client to screen errors
    mock_win32gui["client"].side_effect = None
    mock_win32gui["client"].return_value = (0, 0, 100, 100)
    mock_win32gui["screen"].side_effect = Exception("Screen conversion error")
    client_rect = window_tracker.get_client_rect()
    assert client_rect is None
    
    # Test window moved signal
    window_moved = False
    moved_rect = None
    def on_window_moved(rect):
        nonlocal window_moved, moved_rect
        window_moved = True
        moved_rect = rect
    window_tracker.window_moved.connect(on_window_moved)
    
    # Reset mock and get rect twice
    mock_win32gui["rect"].side_effect = None
    mock_win32gui["rect"].return_value = (100, 100, 900, 700)
    rect1 = window_tracker.get_window_rect()
    mock_win32gui["rect"].return_value = (200, 200, 1000, 800)
    rect2 = window_tracker.get_window_rect()
    
    assert window_moved
    assert moved_rect == rect2

def test_window_event_error_handling_complete(window_tracker, mock_win32gui, qtbot):
    """Test complete error handling in window events."""
    # Setup signal tracking
    window_found = False
    window_lost = False
    
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    
    def on_window_lost():
        nonlocal window_lost
        window_lost = True
    
    window_tracker.window_found.connect(on_window_found)
    window_tracker.window_lost.connect(on_window_lost)
    
    # Test error during window found
    mock_win32gui["find"].return_value = 12345
    mock_win32gui["rect"].side_effect = Exception("Window rect error")
    window_tracker.find_window()
    
    assert window_found  # Event should still be emitted
    
    # Test error during window lost
    mock_win32gui["find"].return_value = 0
    mock_win32gui["rect"].side_effect = Exception("Window rect error")
    window_tracker.find_window()
    
    assert window_lost  # Event should still be emitted

def test_find_standalone_window_as_fallback(window_tracker, mock_win32gui):
    """Test finding standalone window as fallback when browser detection fails."""
    # Disable standalone priority
    window_tracker.standalone_priority = False
    
    # Setup mock to find standalone window after browser detection fails
    mock_win32gui["find"].side_effect = [
        0,  # Chrome not found
        0,  # Firefox not found
        0,  # Edge not found
        0,  # Opera not found
        12345  # Standalone window found
    ]
    
    # Find window
    success = window_tracker.find_window()
    
    assert success
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"

def test_find_standalone_window_as_fallback_error(window_tracker, mock_win32gui):
    """Test error handling when finding standalone window as fallback."""
    # Disable standalone priority
    window_tracker.standalone_priority = False
    
    # Setup mock to fail finding standalone window after browser detection fails
    mock_win32gui["find"].side_effect = [
        0,  # Chrome not found
        0,  # Firefox not found
        0,  # Edge not found
        0,  # Opera not found
        Exception("Standalone error")  # Error finding standalone window
    ]
    
    # Track error signal
    errors = []
    def on_error(msg):
        nonlocal errors
        errors.append(msg)
    window_tracker.error_occurred.connect(on_error)
    
    # Find window
    success = window_tracker.find_window()
    
    assert not success
    assert len(errors) == 1
    assert "Standalone error" in errors[0]

def test_window_rect_inverted_coordinates(window_tracker, mock_win32gui):
    """Test handling inverted coordinates in window rectangle."""
    window_tracker.hwnd = 12345
    
    # Test with inverted coordinates
    mock_win32gui["rect"].return_value = (900, 700, 100, 100)  # right < left, bottom < top
    
    rect = window_tracker.get_window_rect()
    
    assert rect is not None
    assert rect.left() == 100
    assert rect.top() == 100
    assert rect.width() == 800
    assert rect.height() == 600

def test_coordinate_conversion_error_handling_detailed(window_tracker):
    """Test detailed error handling in coordinate conversion."""
    # Test logical to physical conversion errors
    with patch.object(window_tracker, 'dpi_scale', None):  # Cause attribute error
        pos = window_tracker.to_physical_pos((100, 100))
        assert pos == (0, 0)
    
    # Test physical to logical conversion errors
    with patch.object(window_tracker, 'dpi_scale', None):  # Cause attribute error
        pos = window_tracker.to_logical_pos((100, 100))
        assert pos == (0, 0)

def test_window_event_handling_detailed(window_tracker, mock_win32gui):
    """Test detailed window event handling."""
    # Track signals
    window_found = False
    window_lost = False
    
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    
    def on_window_lost():
        nonlocal window_lost
        window_lost = True
    
    window_tracker.window_found.connect(on_window_found)
    window_tracker.window_lost.connect(on_window_lost)
    
    # Test window found with no previous window
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    window_tracker._on_window_found()
    assert window_found
    
    # Test window lost with no previous window
    window_tracker.hwnd = 0
    window_tracker._on_window_lost()
    assert not window_lost  # Should not emit if no window was found
    
    # Test window lost with previous window
    window_tracker.hwnd = 12345
    window_lost = False
    window_tracker._on_window_lost()
    assert window_lost
    assert window_tracker.hwnd == 0
    assert window_tracker.window_type == ""

def test_find_window_all_branches(window_tracker, mock_win32gui):
    """Test all branches in window finding logic."""
    # Test standalone priority disabled and browser detection enabled
    window_tracker.standalone_priority = False
    window_tracker.browser_detection = True
    
    # First test: Find browser window
    mock_win32gui["find"].side_effect = [
        12345,  # Chrome window found
        0,      # Firefox not found (shouldn't be called)
        0,      # Edge not found (shouldn't be called)
        0       # Opera not found (shouldn't be called)
    ]
    
    success = window_tracker.find_window()
    assert success
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "BROWSER"
    
    # Second test: No window found
    mock_win32gui["find"].side_effect = [
        0,  # Chrome not found
        0,  # Firefox not found
        0,  # Edge not found
        0,  # Opera not found
        0   # Standalone not found
    ]
    
    success = window_tracker.find_window()
    assert not success
    assert window_tracker.hwnd == 0
    assert window_tracker.window_type == ""
    
    # Third test: Window rect with no previous rect
    window_tracker.hwnd = 12345
    if hasattr(window_tracker, 'last_rect'):
        delattr(window_tracker, 'last_rect')
    
    mock_win32gui["rect"].return_value = (100, 100, 900, 700)
    rect = window_tracker.get_window_rect()
    
    assert rect is not None
    assert rect.left() == 100
    assert rect.top() == 100
    assert rect.width() == 800
    assert rect.height() == 600

def test_find_window_final_branches(window_tracker, mock_win32gui):
    """Test final uncovered branches in window finding logic."""
    # Test standalone priority disabled and browser detection enabled
    window_tracker.standalone_priority = False
    window_tracker.browser_detection = True
    
    # Test finding standalone window when browser detection is disabled
    window_tracker.browser_detection = False
    mock_win32gui["find"].return_value = 12345
    
    success = window_tracker.find_window()
    assert success
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"
    
    # Test window rect with no window handle
    window_tracker.hwnd = 0
    rect = window_tracker.get_window_rect()
    assert rect is None
    
    # Test window found event with empty window type
    window_tracker.hwnd = 12345
    window_tracker.window_type = ""
    window_tracker._on_window_found()
    assert window_tracker.window_type == ""

def test_window_rect_error_with_previous_rect(window_tracker, mock_win32gui):
    """Test window rect error handling with previous rect."""
    # Setup window handle and initial rect
    window_tracker.hwnd = 12345
    initial_rect = QRect(100, 100, 800, 600)
    window_tracker.last_rect = initial_rect
    
    # Make GetWindowRect raise error
    mock_win32gui["rect"].side_effect = Exception("Window rect error")
    
    # Get window rect
    rect = window_tracker.get_window_rect()
    assert rect is None

def test_window_found_with_error(window_tracker, mock_win32gui):
    """Test window found event with error."""
    # Setup window handle
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    
    # Track window found signal
    window_found = False
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    window_tracker.window_found.connect(on_window_found)
    
    # Make GetWindowRect raise error
    mock_win32gui["rect"].side_effect = Exception("Window rect error")
    
    # Trigger window found event
    window_tracker._on_window_found()
    
    assert window_found
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"

def test_window_rect_inverted_coordinates_with_previous_rect(window_tracker, mock_win32gui):
    """Test window rect with inverted coordinates and previous rect."""
    # Setup window handle and initial rect
    window_tracker.hwnd = 12345
    initial_rect = QRect(100, 100, 800, 600)
    window_tracker.last_rect = initial_rect
    
    # Setup inverted coordinates
    mock_win32gui["rect"].return_value = (900, 700, 100, 100)  # right < left, bottom < top
    
    # Get window rect
    rect = window_tracker.get_window_rect()
    
    assert rect is not None
    assert rect.left() == 100
    assert rect.top() == 100
    assert rect.width() == 800
    assert rect.height() == 600
    assert window_tracker.last_rect == rect  # Check that last_rect was updated

def test_window_found_signal_emission(window_tracker, mock_win32gui):
    """Test window found signal emission."""
    # Setup window handle
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    
    # Track window found signal
    window_found = False
    found_hwnd = None
    def on_window_found(hwnd):
        nonlocal window_found, found_hwnd
        window_found = True
        found_hwnd = hwnd
    window_tracker.window_found.connect(on_window_found)
    
    # Trigger window found event
    window_tracker._on_window_found()
    
    assert window_found
    assert found_hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"

def test_window_found_with_logging(window_tracker, mock_win32gui, caplog):
    """Test window found event with logging."""
    # Setup window handle
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    
    # Track window found signal
    window_found = False
    def on_window_found(hwnd):
        nonlocal window_found
        window_found = True
    window_tracker.window_found.connect(on_window_found)
    
    # Trigger window found event
    window_tracker._on_window_found()
    
    assert window_found
    assert window_tracker.hwnd == 12345
    assert window_tracker.window_type == "STANDALONE"
    assert "Game window found: 12345 (STANDALONE)" in caplog.text

def test_window_found_logging_message(window_tracker, mock_win32gui, caplog):
    """Test window found event logging message."""
    # Setup window handle
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    
    # Trigger window found event
    window_tracker._on_window_found()
    
    # Check log message
    assert "Game window found: 12345 (STANDALONE)" in caplog.text

def test_window_found_logging_with_caplog(window_tracker, mock_win32gui, caplog):
    """Test window found event logging with caplog."""
    # Setup window handle
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    
    # Set caplog level to INFO
    caplog.set_level("INFO")
    
    # Trigger window found event
    window_tracker._on_window_found()
    
    # Check log message
    assert "Game window found: 12345 (STANDALONE)" in caplog.text

def test_window_found_logging_with_empty_type(window_tracker, mock_win32gui, caplog):
    """Test logging message when window is found with empty type."""
    # Set window handle and empty type
    window_tracker.hwnd = 12345
    window_tracker.window_type = ""
    
    # Call the method
    window_tracker._on_window_found()
    
    # Check log message
    assert "Game window found: 12345 ()" in caplog.text

def test_window_found_signal_emission_types(window_tracker, mock_win32gui, qtbot):
    """Test window_found signal emission with different window types."""
    # Track signal emissions
    signals_received = []
    
    def on_window_found(hwnd):
        signals_received.append((hwnd, window_tracker.window_type))
    
    window_tracker.window_found.connect(on_window_found)
    
    # Test STANDALONE window
    window_tracker.hwnd = 12345
    window_tracker.window_type = "STANDALONE"
    window_tracker._on_window_found()
    
    # Test BROWSER window
    window_tracker.hwnd = 67890
    window_tracker.window_type = "BROWSER"
    window_tracker._on_window_found()
    
    # Verify signals
    assert len(signals_received) == 2
    assert signals_received[0] == (12345, "STANDALONE")
    assert signals_received[1] == (67890, "BROWSER")