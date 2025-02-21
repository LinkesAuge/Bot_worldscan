from typing import Optional, List, Tuple, Dict, Any
import cv2
import numpy as np
import win32gui
import win32con
import win32api
from window_manager import WindowManager
from pattern_matcher import MatchResult, GroupedMatch, PatternMatcher
import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer

logger = logging.getLogger(__name__)

class Overlay(QWidget):
    """
    Creates a transparent overlay window to visualize detected game elements.
    
    This class provides real-time visual feedback by drawing on top of the game window:
    - Rectangles around detected elements
    - Text labels showing what was detected and confidence levels
    - Cross markers at the center of detected elements
    - Color-coded indicators based on detection type
    
    The overlay is:
    - Transparent to mouse clicks (passes through to game)
    - Always on top of the game window
    - Automatically repositioned when the game window moves
    - Configurable in terms of colors, sizes, and display options
    
    Key Features:
    - Real-time pattern match visualization
    - Click-through transparency
    - Automatic window tracking
    - Configurable visual elements
    """
    
    def __init__(self, target_window_title: str, window_manager: WindowManager, 
                 settings: Dict[str, Any], pattern_settings: Dict[str, Any]) -> None:
        """
        Initialize the overlay window with specified settings.
        
        Creates a transparent window that tracks and draws over the game window.
        The overlay uses OpenCV for drawing and Win32 API for window management.
        
        Args:
            target_window_title: Title of the game window to overlay
            window_manager: Manager for tracking the game window
            settings: Visual settings (colors, sizes, etc.)
            pattern_settings: Pattern matching configuration
        """
        super().__init__()
        self.window_manager = window_manager
        self.window_name = "Overlay"
        self.active = False
        self.pattern_matching_active = False
        self.pattern_matching_timer = QTimer()
        self.pattern_matching_timer.timeout.connect(self._update_pattern_matching)
        
        # Drawing settings (in BGR format for OpenCV)
        self.rect_color = (0, 0, 255)  # Red in BGR
        self.rect_thickness = 2  # Reduced thickness to make it more visible
        self.rect_scale = 1.0  # Add scale attribute with default value
        self.font_color = (255, 255, 255)  # White in BGR (B, G, R)
        self.font_size = 16
        self.text_thickness = 2  # Add text thickness property
        self.cross_color = (0, 255, 0)  # Green in BGR
        self.cross_size = 10
        self.cross_thickness = 1  # Add thickness attribute
        
        # Create pattern matcher and make it accessible
        self.pattern_matcher = PatternMatcher(
            window_manager=self.window_manager,
            confidence=pattern_settings["confidence"],
            target_fps=pattern_settings["target_fps"],
            sound_enabled=pattern_settings["sound_enabled"]
        )
        
        # Ensure templates are loaded
        self.pattern_matcher.reload_templates()
        template_count = len(self.pattern_matcher.templates)
        logger.info(f"Loaded {template_count} templates for pattern matching")
        if template_count == 0:
            logger.warning("No templates found! Pattern matching will not work without templates")

        logger.debug(f"Initialized overlay with rect_color={self.rect_color}, "
                    f"font_color={self.font_color}, "
                    f"thickness={self.rect_thickness}, "
                    f"font_size={self.font_size}, "
                    f"rect_scale={self.rect_scale}")

    def create_overlay_window(self) -> None:
        """Create the overlay window with transparency."""
        logger.info("Creating overlay window")
        
        pos = self.window_manager.get_window_position()
        if not pos:
            logger.warning("Target window not found, cannot create overlay")
            return
        
        x, y, width, height = pos
        logger.debug(f"Creating overlay window at ({x}, {y}) with size {width}x{height}")
        
        # Create window with proper style
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        hwnd = win32gui.FindWindow(None, self.window_name)
        
        if not hwnd:
            logger.error("Failed to create overlay window")
            return
        
        # Remove window decorations
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        
        # Set window extended styles
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style |= (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        
        # Set transparency color (magenta)
        win32gui.SetLayeredWindowAttributes(
            hwnd,
            win32api.RGB(255, 0, 255),
            255,
            win32con.LWA_COLORKEY
        )
        
        logger.debug("Overlay window created")

    def start_pattern_matching(self) -> None:
        """Start pattern matching."""
        logger.info("Starting pattern matching")
        self.pattern_matching_active = True
        self.active = True  # Also activate overlay
        self.create_overlay_window()
        
        # Start timer for pattern matching updates
        interval = int(1000 / self.pattern_matcher.target_fps)  # Convert FPS to milliseconds
        self.pattern_matching_timer.start(interval)
        logger.debug(f"Pattern matching timer started with interval: {interval}ms")

    def stop_pattern_matching(self) -> None:
        """Stop pattern matching."""
        logger.info("Stopping pattern matching")
        self.pattern_matching_active = False
        self.pattern_matching_timer.stop()
        # Clear any existing matches from display
        self.update([])

    def _update_pattern_matching(self) -> None:
        """Update pattern matching results."""
        if not self.pattern_matching_active:
            return
            
        try:
            logger.debug("Running pattern matching update")
            matches = self.pattern_matcher.find_matches()
            if matches:
                logger.info(f"Found {len(matches)} matches")
                for match in matches:
                    logger.debug(f"Match: {match.template_name} at {match.position} with confidence {match.confidence:.2f}")
            else:
                logger.debug("No matches found")
            self.update(matches)
        except Exception as e:
            logger.error(f"Error in pattern matching update: {e}", exc_info=True)

    def update(self, matches: List[GroupedMatch]) -> None:
        """Update the overlay window with pattern matching results."""
        if not self.active or not self.pattern_matching_active:
            logger.debug("Update skipped - active: {self.active}, pattern matching: {self.pattern_matching_active}")
            return
        
        if not self.window_manager.find_window():
            logger.warning("Target window not found during update")
            return
        
        pos = self.window_manager.get_window_position()
        if not pos:
            logger.warning("Could not get window position")
            return
        
        x, y, width, height = pos
        window_title = win32gui.GetWindowText(self.window_manager.hwnd)
        
        # Try to get the actual client area for Chrome
        client_offset_x = 0
        client_offset_y = 0
        if "Chrome" in window_title:
            try:
                import ctypes
                from ctypes.wintypes import RECT
                
                # Get client rect (actual content area)
                rect = RECT()
                ctypes.windll.user32.GetClientRect(self.window_manager.hwnd, ctypes.byref(rect))
                client_width = rect.right - rect.left
                client_height = rect.bottom - rect.top
                
                # Get client area position
                point = ctypes.wintypes.POINT(0, 0)
                ctypes.windll.user32.ClientToScreen(self.window_manager.hwnd, ctypes.byref(point))
                client_x, client_y = point.x, point.y
                
                # Calculate offset from window to client
                client_offset_x = client_x - x
                client_offset_y = client_y - y
                
                # Update coordinates to use client area
                x, y = client_x, client_y
                width, height = client_width, client_height
                
            except Exception as e:
                logger.warning(f"Failed to get client area: {e}")
        
        try:
            # Create magenta background (will be transparent)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Only draw matches if we have any
            if matches:
                logger.debug(f"Drawing {len(matches)} matches on overlay")
                # Draw matches
                for match in matches:
                    # Adjust match position by client offset (in reverse)
                    match_x = match.bounds[0] - client_offset_x
                    match_y = match.bounds[1] - client_offset_y
                    match_x2 = match.bounds[2] - client_offset_x
                    match_y2 = match.bounds[3] - client_offset_y
                    
                    # Calculate scaled dimensions
                    template_width = match_x2 - match_x
                    template_height = match_y2 - match_y
                    
                    # Calculate center point
                    center_x = (match_x + match_x2) // 2
                    center_y = (match_y + match_y2) // 2
                    
                    # Calculate scaled dimensions
                    scaled_width = int(template_width * self.rect_scale)
                    scaled_height = int(template_height * self.rect_scale)
                    
                    # Calculate new bounds ensuring they're integers
                    new_x1 = int(center_x - scaled_width // 2)
                    new_y1 = int(center_y - scaled_height // 2)
                    new_x2 = int(new_x1 + scaled_width)
                    new_y2 = int(new_y1 + scaled_height)
                    
                    # Ensure color values are tuples of integers
                    rect_color = tuple(map(int, self.rect_color))
                    font_color = tuple(map(int, self.font_color))
                    cross_color = tuple(map(int, self.cross_color))
                    
                    # Draw rectangle
                    cv2.rectangle(
                        overlay,
                        (new_x1, new_y1),
                        (new_x2, new_y2),
                        rect_color,
                        self.rect_thickness
                    )
                    
                    # Draw text above the rectangle
                    text = f"{match.template_name} ({match.confidence:.2f})"
                    cv2.putText(
                        overlay,
                        text,
                        (new_x1, new_y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.font_size / 30,
                        font_color,
                        self.text_thickness  # Use the configurable text thickness
                    )
                    
                    # Draw cross at center
                    half_size = self.cross_size // 2
                    cv2.line(
                        overlay,
                        (center_x - half_size, center_y),
                        (center_x + half_size, center_y),
                        cross_color,
                        self.cross_thickness
                    )
                    cv2.line(
                        overlay,
                        (center_x, center_y - half_size),
                        (center_x, center_y + half_size),
                        cross_color,
                        self.cross_thickness
                    )
            
            # Show and position the window
            cv2.imshow(self.window_name, overlay)
            logger.debug(f"Updated overlay window with size {width}x{height}")
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                # Set window position and make it click-through
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    x, y, width, height,  # Use adjusted coordinates
                    win32con.SWP_NOACTIVATE
                )
                
                # Make sure window is transparent and click-through
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex_style |= (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                
                # Set transparency color (magenta)
                win32gui.SetLayeredWindowAttributes(
                    hwnd,
                    win32api.RGB(255, 0, 255),  # Magenta
                    255,  # Alpha
                    win32con.LWA_COLORKEY
                )
            
            cv2.waitKey(1)
            
        except Exception as e:
            logger.error(f"Error updating overlay: {str(e)}", exc_info=True)

    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        self.active = not self.active
        
        if self.active:
            self.create_overlay_window()
        else:
            cv2.destroyWindow(self.window_name)
            logger.info("Overlay window destroyed") 