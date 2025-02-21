from typing import Optional, Tuple, Any
import win32gui
import logging

logger = logging.getLogger(__name__)

class WindowManager:
    """
    Manages window finding and position tracking.
    """
    
    def __init__(self, window_title: str) -> None:
        """
        Initialize the window manager.
        
        Args:
            window_title: Title of the window to find
        """
        self.window_title = window_title
        self.hwnd = None  # Add this to store the window handle
        logger.debug(f"WindowManager initialized for window: {window_title}")
    
    def find_window(self) -> bool:
        """
        Find the target window by title.
        
        Returns:
            bool: True if window was found, False otherwise
        """
        matching_windows = []  # List to store all matching windows
        
        def enum_windows_callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            window_title = win32gui.GetWindowText(hwnd)
            
            # Skip our own application windows
            if window_title == "Total Battle Scout" or window_title == "Overlay":
                return True
            
            # Look for "Total Battle" anywhere in the window title
            if self.window_title in window_title:
                matching_windows.append(window_title)  # Add to list of matches
                self.hwnd = hwnd
                return False
            return True
        
        self.hwnd = None
        win32gui.EnumWindows(enum_windows_callback, None)
        
        # Log all matching windows
        if matching_windows:
            logger.info("Found matching windows:")
            for window in matching_windows:
                logger.info(f"  • {window}")
        else:
            logger.warning(f"No window found matching '{self.window_title}'")
        
        return self.hwnd is not None
    
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the window position and size.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: (x, y, width, height) if window found, None otherwise
        """
        try:
            if not self.find_window():  # Use find_window to get the correct hwnd
                logger.warning(f"Window '{self.window_title}' not found")
                return None
                
            rect = win32gui.GetWindowRect(self.hwnd)  # Use stored hwnd
            x = rect[0]
            y = rect[1]
            width = rect[2] - x
            height = rect[3] - y
            
            logger.debug(f"Window found at ({x}, {y}) with size {width}x{height}")
            return x, y, width, height
            
        except Exception as e:
            logger.error(f"Error getting window position: {str(e)}", exc_info=True)
            return None 