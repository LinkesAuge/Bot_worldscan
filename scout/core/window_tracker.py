from typing import Optional, Tuple, Dict, Any
import win32gui
import win32con
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QRect, QPoint
from ..config import ConfigManager

logger = logging.getLogger(__name__)

class WindowTracker(QObject):
    """
    Tracks and manages the game window.
    
    This class provides:
    - Window detection (standalone and browser)
    - Window metrics tracking
    - DPI scaling handling
    - Window state notifications
    """
    
    # Signals
    window_found = pyqtSignal(int)  # hwnd
    window_lost = pyqtSignal()
    window_moved = pyqtSignal(QRect)  # new geometry
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, config: Optional[ConfigManager] = None) -> None:
        """
        Initialize window tracker.
        
        Args:
            config: Optional configuration manager
        """
        super().__init__()
        
        # Load configuration
        self.config = config or ConfigManager()
        window_config = self.config.get_window_config()
        
        # Initialize state
        self.hwnd = 0
        self.window_type = ""
        self.dpi_scale = 1.0
        self.standalone_priority = window_config.standalone_priority
        self.browser_detection = window_config.browser_detection
        self.update_interval = window_config.update_interval
        
        logger.debug("Window tracker initialized")
        
    def find_window(self) -> bool:
        """
        Find the game window.
        
        Returns:
            bool: True if window found, False otherwise
        """
        old_hwnd = self.hwnd
        temp_hwnd = 0  # Use temporary variable for searching
        error_occurred = False
        
        # Try standalone first if prioritized
        if self.standalone_priority:
            try:
                temp_hwnd = win32gui.FindWindow(None, "Total Battle")
                if temp_hwnd:
                    self.hwnd = temp_hwnd
                    self.window_type = "STANDALONE"
                    self._on_window_found()
                    return True
            except Exception as e:
                error_msg = f"Error finding window: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                error_occurred = True
        
        # Try browsers if enabled
        if self.browser_detection:
            browsers = ["Chrome", "Firefox", "Edge", "Opera"]
            for browser in browsers:
                try:
                    temp_hwnd = win32gui.FindWindow(None, f"Total Battle - {browser}")
                    if temp_hwnd:
                        self.hwnd = temp_hwnd
                        self.window_type = "BROWSER"
                        self._on_window_found()
                        return True
                except Exception as e:
                    error_msg = f"Error finding window: {e}"
                    logger.error(error_msg)
                    self.error_occurred.emit(error_msg)
                    error_occurred = True
                    continue  # Try next browser
        
        # Try standalone as fallback
        if not self.standalone_priority:
            try:
                temp_hwnd = win32gui.FindWindow(None, "Total Battle")
                if temp_hwnd:
                    self.hwnd = temp_hwnd
                    self.window_type = "STANDALONE"
                    self._on_window_found()
                    return True
            except Exception as e:
                error_msg = f"Error finding window: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                error_occurred = True
        
        # Window not found
        if old_hwnd != 0:  # Only emit if we previously had a window
            self._on_window_lost()
        return False
        
    def get_window_rect(self) -> Optional[QRect]:
        """
        Get the window rectangle.
        
        Returns:
            QRect: Window geometry or None if window not found
        """
        try:
            if not self.hwnd:
                return None
                
            # Get window rect
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            
            # Normalize coordinates if inverted
            if right < left:
                left, right = right, left
            if bottom < top:
                top, bottom = bottom, top
            
            # Convert to QRect
            rect = QRect(left, top, right - left, bottom - top)
            
            # Check if window moved
            if hasattr(self, 'last_rect'):
                if rect != self.last_rect:
                    self.window_moved.emit(rect)
                    
            self.last_rect = rect
            return rect
            
        except Exception as e:
            logger.error(f"Error getting window rect: {e}")
            return None
            
    def get_client_rect(self) -> Optional[QRect]:
        """
        Get the client area rectangle.
        
        Returns:
            QRect: Client area geometry or None if window not found
        """
        try:
            if not self.hwnd:
                return None
                
            # Get client rect in window coordinates
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
            
            # Convert to screen coordinates
            screen_left, screen_top = win32gui.ClientToScreen(self.hwnd, (left, top))
            screen_right, screen_bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))
            
            # Create QRect with correct dimensions
            width = right - left  # Use original width
            height = bottom - top  # Use original height
            return QRect(screen_left, screen_top, width, height)
            
        except Exception as e:
            logger.error(f"Error getting client rect: {e}")
            return None
            
    def to_logical_pos(self, physical_pos: Tuple[int, int]) -> Tuple[int, int]:
        """
        Convert physical to logical coordinates.
        
        Args:
            physical_pos: Physical screen coordinates
            
        Returns:
            Logical coordinates
        """
        try:
            x, y = physical_pos
            if x is None or y is None:
                return (0, 0)
            # Handle negative coordinates
            x = max(0, x)
            y = max(0, y)
            return (int(x / self.dpi_scale), int(y / self.dpi_scale))
        except Exception as e:
            logger.error(f"Error converting to logical coordinates: {e}")
            return (0, 0)
        
    def to_physical_pos(self, logical_pos: Tuple[int, int]) -> Tuple[int, int]:
        """
        Convert logical to physical coordinates.
        
        Args:
            logical_pos: Logical coordinates
            
        Returns:
            Physical screen coordinates
        """
        try:
            x, y = logical_pos
            if x is None or y is None:
                return (0, 0)
            # Handle negative coordinates
            x = max(0, x)
            y = max(0, y)
            return (int(x * self.dpi_scale), int(y * self.dpi_scale))
        except Exception as e:
            logger.error(f"Error converting to physical coordinates: {e}")
            return (0, 0)
        
    def is_window_found(self) -> bool:
        """Check if window is currently found."""
        return self.hwnd != 0
        
    def get_window_type(self) -> str:
        """Get current window type (STANDALONE/BROWSER)."""
        return self.window_type
        
    def _on_window_found(self) -> None:
        """Handle window found event."""
        logger.info(f"Game window found: {self.hwnd} ({self.window_type})")
        self.window_found.emit(self.hwnd)
        
    def _on_window_lost(self) -> None:
        """Handle window lost event."""
        if self.hwnd != 0:
            logger.info("Game window lost")
            self.window_lost.emit()  # Emit signal before resetting state
            self.hwnd = 0
            self.window_type = ""

    def get_debug_info(self) -> Dict[str, Any]:
        """Get current window state for debugging.
        
        Returns:
            Dict[str, Any]: Dictionary containing debug information.
        """
        return {
            "window_found": self.is_window_found(),
            "window_handle": self.hwnd,
            "window_type": self.window_type,
            "window_rect": self.get_window_rect() or QRect(),
            "client_rect": self.get_client_rect() or QRect(),
            "dpi_scale": self.dpi_scale
        } 