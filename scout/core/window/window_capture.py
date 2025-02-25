"""
Window Capture

This module provides classes for capturing window content using different methods.
It abstracts the details of capturing screenshots from windows.
"""

from typing import Optional, Dict, Any, Tuple
import win32gui
import win32con
import win32ui
import numpy as np
import mss
import logging

logger = logging.getLogger(__name__)

class CaptureStrategy:
    """Base class for different window capture strategies."""
    
    def capture(self, hwnd: int, rect: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Capture a screenshot using this strategy.
        
        Args:
            hwnd: Window handle
            rect: Window rectangle (left, top, width, height)
            
        Returns:
            Screenshot as numpy array in BGR format or None if failed
        """
        raise NotImplementedError("Capture strategy must implement capture method")

class MSSCaptureStrategy(CaptureStrategy):
    """
    Capture strategy using MSS (fast screen grabber).
    
    This strategy uses the MSS library to capture screenshots, which is generally
    faster than other methods but captures the entire region including window decorations.
    """
    
    def capture(self, hwnd: int, rect: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Capture a screenshot using MSS.
        
        Args:
            hwnd: Window handle (not used for MSS)
            rect: Window rectangle (left, top, width, height)
            
        Returns:
            Screenshot as numpy array in BGR format or None if failed
        """
        try:
            x, y, width, height = rect
            
            with mss.mss() as sct:
                monitor = {
                    'left': x,
                    'top': y,
                    'width': width,
                    'height': height
                }
                
                # Grab screenshot
                screenshot = np.array(sct.grab(monitor))
                
                # Convert from BGRA to BGR
                screenshot = screenshot[:, :, :3]
                
                return screenshot
                
        except Exception as e:
            logger.error(f"MSS capture error: {e}")
            return None

class Win32CaptureStrategy(CaptureStrategy):
    """
    Capture strategy using Win32 API.
    
    This strategy uses the Win32 API to capture screenshots, which allows for
    capturing just the client area but may be slower than other methods.
    """
    
    def capture(self, hwnd: int, rect: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Capture a screenshot using Win32 API.
        
        Args:
            hwnd: Window handle
            rect: Window rectangle (left, top, width, height)
            
        Returns:
            Screenshot as numpy array in BGR format or None if failed
        """
        try:
            # Get window and client details
            x, y, width, height = rect
            
            # Create device contexts and bitmap
            wdc = win32gui.GetWindowDC(hwnd)
            dcObj = win32ui.CreateDCFromHandle(wdc)
            cdc = dcObj.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(dcObj, width, height)
            cdc.SelectObject(bitmap)
            
            # Copy window content
            cdc.BitBlt((0, 0), (width, height), dcObj, (0, 0), win32con.SRCCOPY)
            
            # Convert to numpy array
            signed_ints_array = bitmap.GetBitmapBits(True)
            img = np.frombuffer(signed_ints_array, dtype='uint8')
            img.shape = (height, width, 4)
            
            # Clean up
            dcObj.DeleteDC()
            cdc.DeleteDC()
            win32gui.ReleaseDC(hwnd, wdc)
            win32gui.DeleteObject(bitmap.GetHandle())
            
            # Remove alpha channel
            img = img[:, :, :3]
            
            return img
            
        except Exception as e:
            logger.error(f"Win32 capture error: {e}")
            return None

class WindowCapture:
    """
    Provides methods for capturing window content with different strategies.
    
    This class selects an appropriate capture strategy based on the requirements
    and handles the details of capturing screenshots from windows.
    """
    
    def __init__(self):
        """Initialize window capture with available strategies."""
        self.strategies = {
            'mss': MSSCaptureStrategy(),
            'win32': Win32CaptureStrategy()
        }
        
        # Set default strategy
        self.default_strategy = 'mss'
        
    def capture(self, hwnd: int, rect: Tuple[int, int, int, int], 
               strategy_name: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Capture a screenshot of a window.
        
        Args:
            hwnd: Window handle
            rect: Window rectangle (left, top, width, height)
            strategy_name: Name of capture strategy to use (default will be used if None)
            
        Returns:
            Screenshot as numpy array in BGR format or None if failed
        """
        # Use specified strategy or default
        strategy_name = strategy_name or self.default_strategy
        
        if strategy_name not in self.strategies:
            logger.error(f"Unknown capture strategy: {strategy_name}")
            return None
            
        strategy = self.strategies[strategy_name]
        return strategy.capture(hwnd, rect)
    
    def capture_client_area(self, hwnd: int, client_rect: Tuple[int, int, int, int],
                           strategy_name: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Capture a screenshot of a window's client area.
        
        Args:
            hwnd: Window handle
            client_rect: Client rectangle (left, top, right, bottom)
            strategy_name: Name of capture strategy to use (default will be used if None)
            
        Returns:
            Screenshot as numpy array in BGR format or None if failed
        """
        left, top, right, bottom = client_rect
        width = right - left
        height = bottom - top
        
        return self.capture(hwnd, (left, top, width, height), strategy_name) 