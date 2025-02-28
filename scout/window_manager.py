from typing import Optional, Tuple, List, Any
import win32gui
import logging
import ctypes
from ctypes.wintypes import RECT, POINT
import numpy as np
import cv2
import mss
import time
import pywintypes
import win32con

logger = logging.getLogger(__name__)

class WindowManager:
    """
    Manages the tracking and interaction with the game window.
    
    This class is responsible for:
    1. Finding the game window by its title
    2. Tracking the window's position and size
    3. Handling window state changes (moved, resized)
    4. Providing window information to other components
    
    The window manager is a critical component that enables:
    - The overlay to stay aligned with the game window
    - Screen capture for pattern matching
    - Coordinate system calculations
    
    It uses the Windows API to interact with window properties and
    maintains the connection between the game window and our application.
    """
    
    def __init__(self, window_title: str) -> None:
        """
        Initialize the window manager for a specific game window.
        
        Sets up tracking for a window with the given title. The manager
        will continuously try to find and maintain a connection to this
        window throughout the application's lifetime.
        
        Args:
            window_title: Title or partial title of the game window to track
        """
        self.window_title = window_title
        self.hwnd = None  # Windows handle to the game window
        logger.debug(f"WindowManager initialized to track window: {window_title}")
    
    def find_window(self) -> bool:
        """
        Find the game window by title.
        
        Returns:
            True if window found, False otherwise
        """
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            # Window already found, check if it's still valid
            try:
                if self.window_title in win32gui.GetWindowText(self.hwnd):
                    return True
            except Exception as e:
                logger.debug(f"Error checking existing window: {e}")
                self.hwnd = None  # Reset handle if error

        # Need to find the window
        self.windows = []
        self.hwnd = None
        
        def enum_windows_callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                
                window_title = win32gui.GetWindowText(hwnd)
                if not window_title:
                    return
                    
                # Skip our own windows
                if window_title.startswith("TB Scout"):
                    logger.debug(f"Skipping our own window: {window_title}")
                    return
                    
                # Found a potential match
                if self.window_title.lower() in window_title.lower():
                    logger.debug(f"Found matching window: {window_title} (hwnd: {hwnd})")
                    self.windows.append((hwnd, window_title))
                    
                    # Use the first match as the active window
                    if not self.hwnd:
                        self.hwnd = hwnd
            except Exception as e:
                # Log and continue if there's an error with a specific window
                logger.debug(f"Error processing window in callback: {e}")
        
        try:
            logger.debug(f"Starting window search for title containing: {self.window_title}")
            win32gui.EnumWindows(enum_windows_callback, None)
            
            if not self.windows:
                logger.debug("No matching windows found")
                return False
                
            # Log found windows
            logger.info("Found matching windows:")
            for _, title in self.windows:
                logger.info(f"  • {title}")
                
            return self.hwnd is not None
            
        except Exception as e:
            logger.error(f"Error enumerating windows: {e}")
            
            # Try an alternative approach if EnumWindows fails
            try:
                logger.debug("Trying alternative window finding approach")
                # Look for known windows that might be Total Battle
                possible_titles = ["Total Battle", "TB", "Battle"]
                
                for title in possible_titles:
                    try:
                        hwnd = win32gui.FindWindow(None, title)
                        if hwnd:
                            self.hwnd = hwnd
                            self.windows = [(hwnd, title)]
                            logger.info(f"Found window using alternative method: {title}")
                            return True
                    except Exception:
                        continue
                        
                return False
            except Exception as ex:
                logger.error(f"Alternative window finding also failed: {ex}")
                return False
    
    def is_window_minimized_or_hidden(self) -> bool:
        """Check if window is minimized or hidden."""
        try:
            if not self.hwnd:
                return True
            rect = win32gui.GetWindowRect(self.hwnd)
            return rect[0] <= -32000 or rect[1] <= -32000
        except Exception as e:
            logger.error(f"Error checking window state: {e}")
            return True

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the position and size of the game window.
        
        Returns:
            Tuple of (x, y, width, height) or None if window not found
        """
        try:
            if not self.find_window():
                logger.warning("Window not found")
                return None
                
            # Get window rectangle (includes frame, borders etc)
            rect = win32gui.GetWindowRect(self.hwnd)
            x, y, right, bottom = rect
            
            # Check if window is minimized/hidden
            if x <= -32000 or y <= -32000:
                logger.debug("Window is minimized or hidden")
                return None
                
            width = right - x
            height = bottom - y
            
            # Ensure positive dimensions
            if width <= 0 or height <= 0:
                logger.warning(f"Invalid window dimensions: {width}x{height}")
                return None
            
            logger.debug(f"Window position: x={x}, y={y}, width={width}, height={height}")
            return (x, y, width, height)
            
        except Exception as e:
            logger.error(f"Error getting window position: {e}", exc_info=True)
            return None

    def get_window_frame_offset(self) -> Tuple[int, int]:
        """
        Get the offset between window frame and client area.
        This is needed to properly align coordinates between window and client space.
        
        Returns:
            Tuple[int, int]: (x_offset, y_offset) between window frame and client area
        """
        try:
            if not self.hwnd:
                return (0, 0)
                
            # Get window rect
            window_rect = win32gui.GetWindowRect(self.hwnd)
            
            # Get client rect in screen coordinates
            client_rect = RECT()
            win32gui.GetClientRect(self.hwnd, ctypes.byref(client_rect))
            point = POINT(0, 0)
            win32gui.ClientToScreen(self.hwnd, ctypes.byref(point))
            
            # Calculate offset
            x_offset = point.x - window_rect[0]
            y_offset = point.y - window_rect[1]
            
            logger.debug(f"Window frame offset: x={x_offset}, y={y_offset}")
            return (x_offset, y_offset)
            
        except Exception as e:
            logger.error(f"Error getting window frame offset: {e}")
            return (0, 0)

    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the client area rectangle of the window.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: (left, top, right, bottom) of client area,
            or None if window not found or error occurs
        """
        try:
            if not self.find_window():
                logger.warning("Window not found when getting client rect")
                return None
                
            # Check if window is minimized/hidden
            if self.is_window_minimized_or_hidden():
                logger.debug("Window is minimized or hidden")
                return None
                
            # Get client rect
            client_rect = RECT()
            if not ctypes.windll.user32.GetClientRect(self.hwnd, ctypes.byref(client_rect)):
                logger.error("Failed to get client rect")
                return None
                
            # Get client area position
            client_point = POINT(0, 0)
            if not ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(client_point)):
                logger.error("Failed to convert client coordinates")
                return None
                
            # Calculate client area in screen coordinates
            client_left = client_point.x
            client_top = client_point.y
            client_right = client_left + (client_rect.right - client_rect.left)
            client_bottom = client_top + (client_rect.bottom - client_rect.top)
            
            # Ensure positive dimensions
            width = client_right - client_left
            height = client_bottom - client_top
            if width <= 0 or height <= 0:
                logger.warning(f"Invalid client dimensions: {width}x{height}")
                return None
            
            logger.debug(f"Client rect: ({client_left}, {client_top}, {client_right}, {client_bottom})")
            return (client_left, client_top, client_right, client_bottom)
            
        except Exception as e:
            logger.error(f"Error getting client rect: {e}")
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
        try:
            if not self.find_window():
                logger.warning("Window not found when converting coordinates")
                return x, y
                
            # Get client area position
            point = POINT(x, y)
            if not ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(point)):
                logger.error("Failed to convert client coordinates")
                return x, y
                
            return point.x, point.y
            
        except Exception as e:
            logger.error(f"Error converting coordinates: {e}")
            return x, y

    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to client (window-relative) coordinates.
        
        Args:
            screen_x: X coordinate on screen
            screen_y: Y coordinate on screen
            
        Returns:
            Tuple[int, int]: Client coordinates (x, y)
        """
        try:
            if not self.find_window():
                logger.warning("Window not found when converting coordinates")
                return screen_x, screen_y
                
            # Get client area position
            point = POINT(screen_x, screen_y)
            if not ctypes.windll.user32.ScreenToClient(self.hwnd, ctypes.byref(point)):
                logger.error("Failed to convert screen coordinates")
                return screen_x, screen_y
                
            return point.x, point.y
            
        except Exception as e:
            logger.error(f"Error converting coordinates: {e}")
            return screen_x, screen_y

    def is_window_maximized(self) -> bool:
        """Check if the window is maximized."""
        try:
            if not self.hwnd:
                return False
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            return bool(style & win32con.WS_MAXIMIZE)
        except Exception as e:
            logger.error(f"Error checking window state: {e}")
            return False

    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window.
        
        Returns:
            Screenshot as numpy array in BGR format (OpenCV), or None if failed
        """
        try:
            if not self.find_window():
                return None
                
            # Get the client area rectangle - these are already in screen coordinates
            client_rect = self.get_client_rect()
            if not client_rect:
                return None
                
            left, top, right, bottom = client_rect
            width = right - left
            height = bottom - top
            
            logger.debug(f"Capturing client area: ({left}, {top}) with size {width}x{height}")
            
            # Check if window is maximized for logging purposes
            is_maximized = self.is_window_maximized()
            if is_maximized:
                logger.debug("Window is maximized")
            
            # Capture the screen
            with mss.mss() as sct:
                # Define capture region using client coordinates directly
                monitor = {
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height
                }
                
                logger.debug(f"Capturing with monitor settings: {monitor}")
                
                # Grab screenshot using MSS
                screenshot = np.array(sct.grab(monitor))
                
                # Convert from BGRA to BGR (drop alpha channel)
                logger.debug(f"Captured image shape before conversion: {screenshot.shape}")
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                logger.debug(f"Converted image shape: {screenshot.shape}")
                
                return screenshot
                
        except pywintypes.error as e:
            # Special handling for common Windows API errors
            logger.error(f"Error capturing screenshot: {e}")
            
            # If access denied (5), waiting could help
            if e.winerror == 5:  # ERROR_ACCESS_DENIED
                logger.debug("Access denied error - waiting and will retry on next call")
                time.sleep(0.5)  # Wait a bit before next attempt
                return None
                
            return None
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}", exc_info=True)
            return None 