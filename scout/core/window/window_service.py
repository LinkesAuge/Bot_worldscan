"""
Window Service

This module provides the WindowService class which implements the WindowServiceInterface.
It handles window detection, tracking, and screenshot capture functionality.
"""

from typing import Optional, Tuple, Dict, Any, Protocol, List
import win32gui
import win32con
import win32api
import ctypes
from ctypes.wintypes import RECT, POINT
import numpy as np
import cv2
import mss
import time
import logging
import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFontMetrics

from ..interfaces.service_interfaces import WindowServiceInterface
from ..services.event_bus import EventBus
from .window_capture import WindowCapture
from ..events.event_types import EventType

# Windows API structures for window operations
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# Set up logging
logger = logging.getLogger(__name__)

# Create a mixin class that implements the WindowServiceInterface methods
class WindowServiceMixin:
    """Mixin that implements WindowServiceInterface without inheritance."""
    
    def find_window(self) -> bool:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def capture_screenshot(self, use_strategy: Optional[str] = None) -> Optional[np.ndarray]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def capture_client_area(self, use_strategy: Optional[str] = None) -> Optional[np.ndarray]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Must be implemented by the actual class."""
        raise NotImplementedError()
    
    def get_window_state(self) -> str:
        """Must be implemented by the actual class."""
        raise NotImplementedError()

class WindowService(QObject, WindowServiceMixin):
    """
    Service for handling window-related operations.
    
    This service is responsible for:
    - Finding and tracking the game window
    - Capturing screenshots of the game window
    - Converting between screen and client coordinates
    - Notifying when window state changes
    
    The service uses Win32 API to interact with windows and MSS for
    efficient screen capture.
    """
    
    # Signals for window events
    window_moved = pyqtSignal(int, int, int, int)  # x, y, width, height
    window_state_changed = pyqtSignal(str)  # state name (e.g., 'minimized', 'maximized')
    screenshot_captured = pyqtSignal(object)  # numpy array image
    
    # Singleton instance
    _instance = None
    
    # Override __new__ to implement the singleton pattern
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WindowService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, window_title: str, event_bus: Optional[EventBus] = None):
        """
        Initialize the window service.
        
        Args:
            window_title: Title of the window to find and track
            event_bus: Event bus for publishing window events (optional)
        """
        # Only initialize once due to singleton pattern
        if getattr(self, '_initialized', False):
            return
            
        # Initialize QObject
        super().__init__()
        
        self._initialized = True
        self._window_title = window_title
        self._hwnd = None  # Window handle
        self._event_bus = event_bus
        self._window_rect = None  # (x, y, width, height)
        self._client_rect = None  # (x, y, width, height) - client area
        self._window_state = "unknown"
        self._window_capture = WindowCapture()
        
        # Try to find the window
        self.find_window()
        
        logger.info(f"Window service initialized for window: '{window_title}'")
    
    def find_window(self) -> bool:
        """
        Find the game window by title.
        
        Returns:
            bool: True if window found, False otherwise
        """
        if self._hwnd and win32gui.IsWindow(self._hwnd):
            # Window already found, check if it's still valid
            try:
                window_title = win32gui.GetWindowText(self._hwnd)
                if self._window_title in window_title:
                    logger.debug(f"Using existing window handle: {self._hwnd}, title: '{window_title}'")
                    return True
                else:
                    logger.debug(f"Existing window title changed from '{self._window_title}' to '{window_title}', searching again")
            except Exception as e:
                logger.debug(f"Error checking existing window: {e}")
                self._hwnd = None  # Reset handle if error
                
        # Need to find the window
        matching_windows = []
        all_windows = []
        
        def enum_windows_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
                
            window_title = win32gui.GetWindowText(hwnd)
            
            # Log all windows with non-empty titles for debugging
            if window_title:
                window_rect = win32gui.GetWindowRect(hwnd)
                window_info = {
                    'hwnd': hwnd, 
                    'title': window_title,
                    'rect': window_rect
                }
                all_windows.append(window_info)
                
                # Skip Scout application windows
                if window_title.startswith("Scout") or window_title.startswith("TB Scout"):
                    return
                    
                # Found a potential match
                if self._window_title.lower() in window_title.lower():
                    matching_windows.append((hwnd, window_title))
                
        try:
            logger.info(f"Searching for window with title containing: '{self._window_title}'")
            win32gui.EnumWindows(enum_windows_callback, None)
            
            # Log all visible windows for debugging
            logger.debug(f"All visible windows ({len(all_windows)}):")
            for i, window in enumerate(all_windows[:10]):  # Limit to first 10 for brevity
                rect = window['rect']
                size = (rect[2] - rect[0], rect[3] - rect[1])
                logger.debug(f"  {i+1}. HWND: {window['hwnd']}, Title: '{window['title']}', Size: {size}")
            if len(all_windows) > 10:
                logger.debug(f"  ... and {len(all_windows) - 10} more windows")
            
            if not matching_windows:
                logger.warning(f"No windows found matching title: '{self._window_title}'")
                return False
                
            # Log matching windows
            logger.info(f"Found {len(matching_windows)} matching windows:")
            for i, (hwnd, title) in enumerate(matching_windows):
                rect = win32gui.GetWindowRect(hwnd)
                size = (rect[2] - rect[0], rect[3] - rect[1])
                logger.info(f"  {i+1}. HWND: {hwnd}, Title: '{title}', Size: {size}")
            
            # Use the first match
            self._hwnd = matching_windows[0][0]
            logger.info(f"Selected window: '{matching_windows[0][1]}' (hwnd: {self._hwnd})")
            
            # Update window metrics
            self._update_window_metrics()
            
            # Emit window found event
            self._publish_window_changed_event()
            
            return True
            
        except Exception as e:
            logger.error(f"Error finding window: {e}", exc_info=True)
            return False
    
    def _update_window_metrics(self) -> None:
        """Update window position, client area, and DPI scaling information."""
        if not self._hwnd:
            return
            
        try:
            # Get DPI scale
            dc = win32gui.GetDC(self._hwnd)
            try:
                self._dpi_scale = ctypes.windll.gdi32.GetDeviceCaps(dc, 88) / 96.0  # LOGPIXELSX = 88
            finally:
                win32gui.ReleaseDC(self._hwnd, dc)
                
            # Get window rect
            window_rect = win32gui.GetWindowRect(self._hwnd)
            
            # Get client rect
            client_rect = RECT()
            ctypes.windll.user32.GetClientRect(self._hwnd, ctypes.byref(client_rect))
            
            # Get client position
            client_point = POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(self._hwnd, ctypes.byref(client_point))
            
            # Calculate client offset
            self._client_offset_x = client_point.x - window_rect[0]
            self._client_offset_y = client_point.y - window_rect[1]
            
            logger.debug(f"Window metrics updated - DPI scale: {self._dpi_scale}, "
                        f"Client offset: ({self._client_offset_x}, {self._client_offset_y})")
                        
        except Exception as e:
            logger.error(f"Error updating window metrics: {e}")
    
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the position and size of the game window.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: Tuple of (x, y, width, height) or None if window not found
        """
        if not self.find_window():
            return None
            
        try:
            rect = win32gui.GetWindowRect(self._hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            position = (x, y, width, height)
            
            # Check if position changed
            if position != self._window_rect:
                self._window_rect = position
                self._publish_window_changed_event()
                
            return position
            
        except Exception as e:
            logger.error(f"Error getting window position: {e}")
            return None
    
    def capture_screenshot(self, use_strategy: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window.
        
        Args:
            use_strategy: Capture strategy to use ('mss' or 'win32', None for default)
            
        Returns:
            Optional[np.ndarray]: Screenshot as numpy array in BGR format, or None if failed
        """
        if not self.find_window():
            return None
            
        try:
            # Get the window position
            position = self.get_window_position()
            if not position:
                return None
                
            x, y, width, height = position
            
            # Use WindowCapture to capture the window
            screenshot = self._window_capture.capture(
                self._hwnd, 
                (x, y, width, height), 
                use_strategy
            )
            
            if screenshot is None:
                logger.warning("Failed to capture screenshot with WindowCapture")
                return None
                
            # Emit screenshot captured signal
            self.screenshot_captured.emit(screenshot)
            
            # Publish event if event bus is available
            if self._event_bus:
                self._event_bus.publish(
                    'screenshot_captured',
                    {'image': screenshot, 'window_position': position}
                )
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None
    
    def capture_client_area(self, use_strategy: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Capture only the client area of the window.
        
        Args:
            use_strategy: Capture strategy to use ('mss' or 'win32', None for default)
            
        Returns:
            Optional[np.ndarray]: Screenshot of client area or None if failed
        """
        if not self.find_window():
            return None
            
        try:
            # Get client rect
            client_rect = self.get_client_rect()
            if not client_rect:
                return None
                
            # Use WindowCapture to capture the client area
            screenshot = self._window_capture.capture_client_area(
                self._hwnd,
                client_rect,
                use_strategy
            )
            
            if screenshot is None:
                logger.warning("Failed to capture client area with WindowCapture")
                return None
                
            # Emit screenshot captured signal
            self.screenshot_captured.emit(screenshot)
            
            # Publish event if event bus is available
            if self._event_bus:
                self._event_bus.publish(
                    'screenshot_captured',
                    {'image': screenshot, 'client_rect': client_rect}
                )
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Error capturing client area: {e}")
            return None
    
    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert client (window-relative) coordinates to screen coordinates.
        
        Args:
            x: X coordinate relative to window client area
            y: Y coordinate relative to window client area
            
        Returns:
            Tuple[int, int]: Screen coordinates (x, y)
        """
        if not self.find_window():
            return (x, y)  # Return input if window not found
            
        try:
            # Get window position
            position = self.get_window_position()
            if not position:
                return (x, y)
                
            window_x, window_y, _, _ = position
            
            # Add client offset and window position
            screen_x = x + window_x + self._client_offset_x
            screen_y = y + window_y + self._client_offset_y
            
            return (screen_x, screen_y)
            
        except Exception as e:
            logger.error(f"Error converting client to screen coordinates: {e}")
            return (x, y)
    
    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to client (window-relative) coordinates.
        
        Args:
            screen_x: X coordinate on screen
            screen_y: Y coordinate on screen
            
        Returns:
            Tuple[int, int]: Client coordinates (x, y)
        """
        if not self.find_window():
            return (screen_x, screen_y)  # Return input if window not found
            
        try:
            # Get window position
            position = self.get_window_position()
            if not position:
                return (screen_x, screen_y)
                
            window_x, window_y, _, _ = position
            
            # Subtract window position and client offset
            client_x = screen_x - window_x - self._client_offset_x
            client_y = screen_y - window_y - self._client_offset_y
            
            return (client_x, client_y)
            
        except Exception as e:
            logger.error(f"Error converting screen to client coordinates: {e}")
            return (screen_x, screen_y)
    
    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the client area rectangle of the window.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: Tuple of (left, top, right, bottom) or None if window not found
        """
        if not self.find_window():
            return None
            
        try:
            window_pos = self.get_window_position()
            if not window_pos:
                return None
                
            window_x, window_y, _, _ = window_pos
            
            # Get client rect
            client_rect = RECT()
            ctypes.windll.user32.GetClientRect(self._hwnd, ctypes.byref(client_rect))
            
            # Calculate client area in screen coordinates
            client_left = window_x + self._client_offset_x
            client_top = window_y + self._client_offset_y
            client_right = client_left + client_rect.right
            client_bottom = client_top + client_rect.bottom
            
            return (client_left, client_top, client_right, client_bottom)
            
        except Exception as e:
            logger.error(f"Error getting client rect: {e}")
            return None
    
    def get_window_state(self) -> str:
        """
        Get the current state of the window.
        
        Returns:
            str: Window state ('normal', 'minimized', 'maximized', or 'unknown')
        """
        if not self.find_window():
            return 'unknown'
            
        try:
            placement = win32gui.GetWindowPlacement(self._hwnd)
            show_cmd = placement[1]
            
            if show_cmd == win32con.SW_SHOWMINIMIZED:
                return 'minimized'
            elif show_cmd == win32con.SW_SHOWMAXIMIZED:
                return 'maximized'
            else:
                return 'normal'
                
        except Exception as e:
            logger.error(f"Error getting window state: {e}")
            return 'unknown'
    
    def _publish_window_changed_event(self) -> None:
        """Publish a window changed event to the event bus."""
        position = self._window_rect
        if not position:
            logger.debug("Not publishing window change event - no position information available")
            return
            
        try:
            # Log the event being emitted
            logger.debug(f"Publishing window moved event: {position}")
            
            # Emit signal
            self.window_moved.emit(*position)
            
            # Publish event to event bus if available
            if self._event_bus:
                # Convert EventType enum to string
                event_type_str = 'window_change'  # Use the expected string value
                
                logger.debug(f"Publishing event bus event: {event_type_str} with position {position}")
                
                self._event_bus.publish(
                    event_type_str,
                    {
                        "x": position[0],
                        "y": position[1],
                        "width": position[2],
                        "height": position[3]
                    }
                )
                
                # Also emit state changed signal
                window_state = self.get_window_state()
                logger.debug(f"Publishing window state changed event: {window_state}")
                self.window_state_changed.emit(window_state)
        except Exception as e:
            logger.error(f"Error publishing window changed event: {e}", exc_info=True)
        
    def create_overlay_painter(self, widget) -> QPainter:
        """
        Create a painter for overlay drawing.
        
        Args:
            widget: Widget to paint on
            
        Returns:
            QPainter object configured for overlay drawing
        """
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        return painter
        
    def draw_detection_results(self, painter: QPainter, results: List[Dict[str, Any]]) -> None:
        """
        Draw detection results on the overlay.
        
        Args:
            painter: QPainter to use for drawing
            results: List of detection result dictionaries
        """
        if not results:
            return
            
        # Set up styles
        bounding_box_pen = QPen(QColor(0, 255, 0))
        bounding_box_pen.setWidth(2)
        
        text_box_brush = QBrush(QColor(0, 0, 0, 180))
        text_pen = QPen(QColor(255, 255, 255))
        
        # Draw each result
        for result in results:
            # Get bounding box
            if 'bbox' in result:
                x, y, w, h = result['bbox']
                
                # Draw bounding box
                painter.setPen(bounding_box_pen)
                painter.drawRect(x, y, w, h)
                
                # Draw label if available
                if 'label' in result:
                    label = result['label']
                    
                    # Get confidence if available
                    if 'confidence' in result:
                        confidence = result['confidence']
                        label = f"{label} ({confidence:.2f})"
                    
                    # Draw text background
                    font = painter.font()
                    font_metrics = QFontMetrics(font)
                    text_width = font_metrics.horizontalAdvance(label)
                    text_height = font_metrics.height()
                    
                    text_rect = QRect(x, y - text_height - 4, text_width + 6, text_height + 4)
                    painter.setBrush(text_box_brush)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(text_rect)
                    
                    # Draw text
                    painter.setPen(text_pen)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label) 