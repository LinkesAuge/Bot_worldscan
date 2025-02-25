"""
Window Service

This module provides the WindowService class which implements the WindowServiceInterface.
It handles window detection, tracking, and screenshot capture functionality.
"""

from typing import Optional, Tuple, Dict, Any, Protocol
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
from PyQt6.QtCore import QObject, pyqtSignal

from ..interfaces.service_interfaces import WindowServiceInterface
from ..services.event_bus import EventBus
from .window_capture import WindowCapture

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
                if self._window_title in win32gui.GetWindowText(self._hwnd):
                    return True
            except Exception as e:
                logger.debug(f"Error checking existing window: {e}")
                self._hwnd = None  # Reset handle if error
                
        # Need to find the window
        matching_windows = []
        
        def enum_windows_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
                
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return
                
            # Skip Scout application windows
            if window_title.startswith("Scout") or window_title.startswith("TB Scout"):
                return
                
            # Found a potential match
            if self._window_title.lower() in window_title.lower():
                matching_windows.append((hwnd, window_title))
                
        try:
            logger.debug(f"Searching for window with title containing: '{self._window_title}'")
            win32gui.EnumWindows(enum_windows_callback, None)
            
            if not matching_windows:
                logger.debug("No matching windows found")
                return False
                
            # Use the first match
            self._hwnd = matching_windows[0][0]
            logger.info(f"Found window: '{matching_windows[0][1]}' (hwnd: {self._hwnd})")
            
            # Update window metrics
            self._update_window_metrics()
            
            # Emit window found event
            self._publish_window_changed_event()
            
            return True
            
        except Exception as e:
            logger.error(f"Error finding window: {e}")
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
            return
            
        # Emit signal
        self.window_moved.emit(*position)
        
        # Publish event to event bus if available
        if self._event_bus:
            window_state = self.get_window_state()
            
            self._event_bus.publish(
                'window_change',
                {
                    'position': position,
                    'state': window_state,
                    'client_offset': (self._client_offset_x, self._client_offset_y),
                    'dpi_scale': self._dpi_scale
                }
            )
            
            # Also emit state changed signal
            self.window_state_changed.emit(window_state) 