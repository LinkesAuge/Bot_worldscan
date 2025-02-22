"""Tests for screen region selection widget."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QPoint, QRect, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent, QKeyEvent
from PyQt6.QtWidgets import QApplication
from scout.gui.widgets.selector import SelectorWidget
from ctypes import cast, POINTER

@pytest.fixture
def mock_screen():
    """Create mock screen with DPI scaling."""
    screen = MagicMock()
    screen_rect = QRect(0, 0, 1920, 1080)
    screen.virtualGeometry.return_value = screen_rect
    screen.geometry.return_value = screen_rect
    screen.devicePixelRatio.return_value = 2.0  # Set DPI scale to 2.0 for all tests
    return screen

@pytest.fixture
def mock_win32gui():
    """Mock win32gui functions."""
    with patch("win32gui.FindWindow") as mock_find, \
         patch("win32gui.GetWindowRect") as mock_rect, \
         patch("win32gui.GetClientRect") as mock_client, \
         patch("win32gui.ClientToScreen") as mock_screen, \
         patch("win32gui.EnumWindows") as mock_enum, \
         patch("win32gui.GetWindowText") as mock_text, \
         patch("win32gui.IsWindowVisible") as mock_visible:
        
        mock_find.return_value = 12345
        mock_rect.return_value = (100, 100, 900, 700)
        mock_client.return_value = (0, 0, 780, 580)
        mock_screen.return_value = (110, 120)
        mock_text.return_value = "Total Battle"
        mock_visible.return_value = True
        
        def enum_callback(callback, data):
            callback(12345, data)
            return True
        
        mock_enum.side_effect = enum_callback
        
        yield {
            "find": mock_find,
            "rect": mock_rect,
            "client": mock_client,
            "screen": mock_screen,
            "enum": mock_enum,
            "text": mock_text,
            "visible": mock_visible
        }

@pytest.fixture
def selector_widget(qtbot, mock_screen):
    """Create a selector widget for testing."""
    # Configure united() method
    mock_united = MagicMock()
    mock_united.return_value = mock_screen.geometry()
    mock_screen.virtualGeometry.return_value.united = mock_united

    # Mock QApplication methods
    with patch('PyQt6.QtWidgets.QApplication.primaryScreen', return_value=mock_screen), \
         patch('PyQt6.QtWidgets.QApplication.screens', return_value=[mock_screen]), \
         patch('PyQt6.QtWidgets.QApplication.screenAt', return_value=mock_screen):
        widget = SelectorWidget()
        qtbot.addWidget(widget)
        return widget

def test_selector_widget_initialization(selector_widget):
    """Test SelectorWidget initialization."""
    assert selector_widget.start_pos is None
    assert selector_widget.current_pos is None
    assert not selector_widget.is_selecting
    assert selector_widget.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert selector_widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert selector_widget.cursor().shape() == Qt.CursorShape.CrossCursor

def test_selector_widget_mouse_press(selector_widget, qtbot):
    """Test mouse press event handling."""
    pos = QPointF(100, 100)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    selector_widget.mousePressEvent(event)
    assert selector_widget.start_pos == pos.toPoint()

def test_selector_widget_mouse_move(selector_widget, qtbot):
    """Test mouse move event handling."""
    # Start selection
    start_pos = QPointF(100, 100)
    selector_widget.start_pos = QPoint(100, 100)
    selector_widget.current_pos = QPoint(100, 100)
    selector_widget.is_selecting = True
    
    # Move mouse
    move_pos = QPointF(200, 200)
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        move_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.mouseMoveEvent(event)
    
    assert selector_widget.current_pos == QPoint(200, 200)

def test_selector_widget_mouse_release(selector_widget, qtbot, mock_win32gui):
    """Test mouse release event handling."""
    # Setup signal tracking
    region_selected = False
    region_data = None
    
    def on_region_selected(data):
        nonlocal region_selected, region_data
        region_selected = True
        region_data = data
    
    selector_widget.region_selected.connect(on_region_selected)
    
    # Start selection
    selector_widget.start_pos = QPoint(100, 100)
    selector_widget.current_pos = QPoint(200, 200)
    selector_widget.is_selecting = True
    
    # Release mouse
    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(200, 200),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.mouseReleaseEvent(event)
    
    assert not selector_widget.is_selecting
    assert region_selected
    assert region_data is not None
    assert "left" in region_data
    assert "top" in region_data
    assert "width" in region_data
    assert "height" in region_data
    assert "dpi_scale" in region_data
    assert "logical_coords" in region_data

def test_selector_widget_cancel_selection(selector_widget, qtbot):
    """Test canceling region selection."""
    # Connect signal
    selection_cancelled = False
    def on_selection_cancelled():
        nonlocal selection_cancelled
        selection_cancelled = True
    selector_widget.selection_cancelled.connect(on_selection_cancelled)
    
    # Simulate escape key press
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.keyPressEvent(event)
    
    assert selection_cancelled

def test_selector_widget_client_area_adjustment(qtbot):
    """Test that the selector widget correctly adjusts coordinates for client area."""
    # Mock win32gui functions
    mock_win32gui = {
        'visible': MagicMock(return_value=True),
        'text': MagicMock(return_value='Total Battle'),
        'find': MagicMock(return_value=12345),
        'enum': MagicMock(),
        'rect': MagicMock(return_value=(100, 100, 900, 700)),  # Window rect
        'client': MagicMock(),  # Client rect
        'screen': MagicMock()  # ClientToScreen
    }

    # Create selector widget with mocked functions
    selector_widget = SelectorWidget()
    selector_widget._win32gui = mock_win32gui
    
    # Mock client area functions
    def mock_get_client_rect(hwnd, rect_ptr):
        rect = cast(rect_ptr, POINTER(RECT)).contents
        rect.left = 0
        rect.top = 0
        rect.right = 800
        rect.bottom = 600
        return True
        
    def mock_client_to_screen(hwnd, point_ptr):
        point = cast(point_ptr, POINTER(POINT)).contents
        point.x = 100  # Client area starts at window left (100)
        point.y = 100  # Client area starts at window top (100)
        return True
    
    selector_widget._get_client_rect = mock_get_client_rect
    selector_widget._client_to_screen = mock_client_to_screen
    
    # Track region selection
    region_data = None
    def on_region_selected(data):
        nonlocal region_data
        region_data = data
    
    selector_widget.region_selected.connect(on_region_selected)
    
    # Simulate selection
    start_pos = QPointF(150, 150)
    end_pos = QPointF(250, 250)
    
    # Start selection
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        start_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.mousePressEvent(event)
    
    # Move mouse to update current position
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        end_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.mouseMoveEvent(event)
    
    # End selection
    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        end_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    selector_widget.mouseReleaseEvent(event)
    
    # Verify results
    assert region_data is not None
    # The widget first applies DPI scaling to the raw coordinates:
    # left = 150 * 1.5 = 225
    # width = (250 - 150) * 1.5 = 150
    # Then it would subtract the client area offset * DPI scale,
    # but in this case the client area offset is (0,0) because
    # we mocked ClientToScreen to return the window position
    assert region_data["left"] == 225
    assert region_data["top"] == 225
    assert region_data["width"] == 150
    assert region_data["height"] == 150
    assert region_data["dpi_scale"] == 1.5
    
    # Check logical coordinates are preserved
    assert region_data["logical_coords"]["left"] == 150
    assert region_data["logical_coords"]["top"] == 150
    assert region_data["logical_coords"]["width"] == 100
    assert region_data["logical_coords"]["height"] == 100

def test_selector_widget_dpi_scaling(selector_widget, mock_screen, mock_win32gui, qtbot):
    """Test DPI scaling handling."""
    # Mock win32gui functions to return game window
    def mock_enum_windows(callback, data):
        callback(12345, data)  # Call with fake window handle
        return True
    mock_win32gui["enum"].side_effect = mock_enum_windows
    mock_win32gui["text"].return_value = "Total Battle"
    mock_win32gui["visible"].return_value = True
    mock_win32gui["rect"].return_value = (0, 0, 800, 600)
    mock_win32gui["client"].return_value = (0, 0, 780, 580)
    mock_win32gui["screen"].return_value = (0, 0)  # Client area offset
    
    # Mock RECT and POINT structures
    class MockRECT:
        def __init__(self):
            self.left = 0
            self.top = 0
            self.right = 780
            self.bottom = 580
    
    class MockPOINT:
        def __init__(self, x=0, y=0):
            self.x = x
            self.y = y
    
    mock_rect = MockRECT()
    mock_point = MockPOINT()
    
    # Mock ctypes calls
    with patch('ctypes.wintypes.RECT', return_value=mock_rect), \
         patch('ctypes.wintypes.POINT', return_value=mock_point), \
         patch('ctypes.windll.user32.GetClientRect', return_value=1), \
         patch('ctypes.windll.user32.ClientToScreen', side_effect=lambda hwnd, point: setattr(point, 'x', 0) or setattr(point, 'y', 0) or 1), \
         patch('ctypes.byref', side_effect=lambda x: x), \
         patch('PyQt6.QtWidgets.QApplication.screenAt', return_value=mock_screen):
        
        # Track region selection
        region_data = None
        def on_region_selected(data):
            nonlocal region_data
            region_data = data
        selector_widget.region_selected.connect(on_region_selected)
        
        # Simulate selection
        # Press at (100, 100)
        start_pos = QPointF(100, 100)
        selector_widget.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonPress,
            start_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        ))
        
        # Set selection state
        selector_widget.start_pos = start_pos.toPoint()
        selector_widget.current_pos = start_pos.toPoint()
        selector_widget.is_selecting = True
        
        # Move to (200, 200)
        end_pos = QPointF(200, 200)
        selector_widget.mouseMoveEvent(QMouseEvent(
            QEvent.Type.MouseMove,
            end_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        ))
        
        # Update current position
        selector_widget.current_pos = end_pos.toPoint()
        
        # Release at (200, 200)
        selector_widget.mouseReleaseEvent(QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            end_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        ))
        
        # Verify scaling was applied
        assert region_data is not None
        assert region_data["left"] == 200  # 100 * 2.0
        assert region_data["top"] == 200  # 100 * 2.0
        assert region_data["width"] == 200  # (200 - 100) * 2.0
        assert region_data["height"] == 200  # (200 - 100) * 2.0
        assert region_data["dpi_scale"] == 2.0
        # Check that logical coordinates are unscaled
        assert region_data["logical_coords"]["left"] == 100
        assert region_data["logical_coords"]["top"] == 100
        assert region_data["logical_coords"]["width"] == 100
        assert region_data["logical_coords"]["height"] == 100 