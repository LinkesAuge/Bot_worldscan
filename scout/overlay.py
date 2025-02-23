from typing import Optional, List, Tuple, Dict, Any
import cv2
import numpy as np
import win32gui
import win32con
import win32api
from scout.window_manager import WindowManager
from scout.pattern_matcher import MatchResult, GroupedMatch, PatternMatcher
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
    
    def __init__(self, window_manager: WindowManager, 
                 pattern_settings: Dict[str, Any], overlay_settings: Dict[str, Any]) -> None:
        """
        Initialize the overlay window with specified settings.
        
        Creates a transparent window that tracks and draws over the game window.
        The overlay uses OpenCV for drawing and Win32 API for window management.
        
        Args:
            window_manager: Manager for tracking the game window
            pattern_settings: Pattern matching configuration
            overlay_settings: Visual settings (colors, sizes, etc.)
        """
        super().__init__()
        self.window_manager = window_manager
        self.window_name = "TB Scout Overlay"
        self.active = overlay_settings.get("active", False)
        self.pattern_matching_active = False
        self.pattern_matching_timer = QTimer()
        self.pattern_matching_timer.timeout.connect(self._update_pattern_matching)
        
        # Convert QColor to BGR format for OpenCV
        rect_color = overlay_settings["rect_color"]
        font_color = overlay_settings["font_color"]
        cross_color = overlay_settings["cross_color"]
        
        # Drawing settings (in BGR format for OpenCV)
        self.rect_color = (rect_color.blue(), rect_color.green(), rect_color.red())
        self.rect_thickness = overlay_settings["rect_thickness"]
        self.rect_scale = overlay_settings["rect_scale"]
        self.font_color = (font_color.blue(), font_color.green(), font_color.red())
        self.font_size = overlay_settings["font_size"]
        self.text_thickness = overlay_settings["text_thickness"]
        self.cross_color = (cross_color.blue(), cross_color.green(), cross_color.red())
        self.cross_size = overlay_settings["cross_size"]
        self.cross_thickness = overlay_settings["cross_thickness"]
        self.cross_scale = overlay_settings.get("cross_scale", 1.0)  # Default to 1.0 if not set
        
        # Create pattern matcher and make it accessible
        self.pattern_matcher = PatternMatcher(
            window_manager=self.window_manager,
            confidence=pattern_settings["confidence"],
            target_frequency=pattern_settings["target_frequency"],
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
        
        # Create initial transparent overlay
        overlay = np.zeros((height, width, 3), dtype=np.uint8)
        overlay[:] = (255, 0, 255)  # Magenta background for transparency
        
        # Create window with proper style
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        cv2.imshow(self.window_name, overlay)
        cv2.waitKey(1)  # Process events
        
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
        
        # Position window
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            x, y, width, height,
            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
        )
        
        logger.debug("Overlay window created")

    def start_pattern_matching(self) -> None:
        """Start pattern matching."""
        logger.info("Starting pattern matching")
        self.pattern_matching_active = True
        
        # Create overlay window if both overlay and pattern matching are now active
        if self.active and self.pattern_matching_active:
            self.create_overlay_window()
        
        # Start timer for pattern matching updates
        self.update_timer_interval()
        logger.debug("Pattern matching timer started")

    def update_timer_interval(self) -> None:
        """Update the pattern matching timer interval based on target frequency."""
        if not hasattr(self.pattern_matcher, 'target_frequency'):
            logger.warning("Pattern matcher has no target_frequency attribute")
            return
            
        interval = max(int(1000 / self.pattern_matcher.target_frequency), 16)  # Minimum 16ms (60 FPS max)
        logger.debug(
            f"Updating pattern matching timer interval: "
            f"target_frequency={self.pattern_matcher.target_frequency:.2f} updates/sec -> "
            f"interval={interval}ms"
        )
        
        if self.pattern_matching_active:
            # Stop the timer if it's running
            if self.pattern_matching_timer.isActive():
                self.pattern_matching_timer.stop()
            
            # Set new interval and start timer
            self.pattern_matching_timer.setInterval(interval)
            self.pattern_matching_timer.start()
            logger.info(f"Timer restarted with new interval: {interval}ms")

    def _destroy_window_safely(self) -> None:
        """Safely destroy the overlay window if it exists."""
        try:
            # Check if window exists before destroying
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                cv2.destroyWindow(self.window_name)
                logger.info("Overlay window destroyed")
        except Exception as e:
            logger.debug(f"Window destruction skipped: {e}")

    def stop_pattern_matching(self) -> None:
        """Stop pattern matching."""
        logger.info("Stopping pattern matching")
        self.pattern_matching_active = False
        self.pattern_matching_timer.stop()
        
        # Reset pattern matcher frequency
        self.pattern_matcher.update_frequency = 0.0
        self.pattern_matcher.last_update_time = 0.0
        
        # Safely destroy window when pattern matching stops
        self._destroy_window_safely()
        
        # Clear any existing matches from display
        self.update([])

    def _update_pattern_matching(self) -> None:
        """Run pattern matching update cycle."""
        try:
            logger.debug("Running pattern matching update")
            
            # Capture window image
            image = self.pattern_matcher.capture_window()
            if image is None:
                logger.warning("Failed to capture window for pattern matching")
                return
            
            # Find matches in captured image
            matches = self.pattern_matcher.find_matches(image)
            
            # Update overlay with matches
            self.update(matches)
            
        except Exception as e:
            logger.error(f"Error in pattern matching update: {e}", exc_info=True)

    def update(self, matches: List[GroupedMatch]) -> None:
        """Update the overlay window with pattern matching results."""
        if not self.active or not self.pattern_matching_active:
            logger.debug(f"Update skipped - active: {self.active}, pattern matching: {self.pattern_matching_active}")
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
        
        # Handle browser-specific window adjustments
        client_offset_x = 0
        client_offset_y = 0
        try:
            # Check if running in a browser
            if any(browser in window_title for browser in ["Chrome", "Firefox", "Edge", "Opera"]):
                import ctypes
                from ctypes.wintypes import RECT, POINT
                
                # Get client rect (actual content area)
                rect = RECT()
                if ctypes.windll.user32.GetClientRect(self.window_manager.hwnd, ctypes.byref(rect)):
                    client_width = rect.right - rect.left
                    client_height = rect.bottom - rect.top
                    
                    # Get client area position
                    point = POINT(0, 0)
                    if ctypes.windll.user32.ClientToScreen(self.window_manager.hwnd, ctypes.byref(point)):
                        client_x, client_y = point.x, point.y
                        
                        # Calculate offset from window to client
                        client_offset_x = client_x - x
                        client_offset_y = client_y - y
                        
                        # Update coordinates to use client area
                        x, y = client_x, client_y
                        width, height = client_width, client_height
                        
                        logger.debug(f"Browser client area adjusted: pos=({x}, {y}), size={width}x{height}, offset=({client_offset_x}, {client_offset_y})")
                
        except Exception as e:
            logger.warning(f"Failed to adjust for browser client area: {e}")
        
        try:
            # Ensure window exists before drawing
            hwnd = win32gui.FindWindow(None, self.window_name)
            if not hwnd:
                logger.debug("Creating overlay window as it doesn't exist")
                self.create_overlay_window()
            
            # Create magenta background (will be transparent)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Only draw matches if we have any
            if matches:
                logger.debug(f"Drawing {len(matches)} matches on overlay")
                # Draw matches
                for match in matches:
                    # Adjust match position by client offset
                    match_x = match.bounds[0] - client_offset_x
                    match_y = match.bounds[1] - client_offset_y
                    match_x2 = match.bounds[2] - client_offset_x
                    match_y2 = match.bounds[3] - client_offset_y
                    
                    logger.debug(f"Drawing match - Original bounds: {match.bounds}")
                    logger.debug(f"Client offset being applied: ({client_offset_x}, {client_offset_y})")
                    logger.debug(f"Adjusted coordinates: ({match_x}, {match_y}) -> ({match_x2}, {match_y2})")
                    
                    # Calculate center point and dimensions
                    center_x = (match_x + match_x2) // 2
                    center_y = (match_y + match_y2) // 2
                    template_width = match_x2 - match_x
                    template_height = match_y2 - match_y
                    
                    # Calculate scaled dimensions
                    scaled_width = int(template_width * self.rect_scale)
                    scaled_height = int(template_height * self.rect_scale)
                    
                    # Calculate new bounds ensuring they're integers
                    new_x1 = int(center_x - scaled_width // 2)
                    new_y1 = int(center_y - scaled_height // 2)
                    new_x2 = int(new_x1 + scaled_width)
                    new_y2 = int(new_y1 + scaled_height)
                    
                    # Cache color tuples
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
                        self.text_thickness
                    )
                    
                    # Draw cross at center
                    half_size = int(self.cross_size * self.cross_scale) // 2
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
            cv2.waitKey(1)  # Process events
            
            # Find and update window properties
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                # Cache current window styles
                current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                current_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                
                # Update position and state with minimal redraw
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,  # Always on top
                    x, y, width, height,
                    win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOREDRAW
                )
                
                # Update styles only if needed
                new_style = current_style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
                if current_style != new_style:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
                
                new_ex_style = current_ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOPMOST
                if current_ex_style != new_ex_style:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
                
                # Ensure transparency is set
                win32gui.SetLayeredWindowAttributes(
                    hwnd,
                    win32api.RGB(255, 0, 255),  # Magenta
                    255,  # Alpha
                    win32con.LWA_COLORKEY
                )
            else:
                logger.warning("Overlay window not found after update, recreating...")
                self.create_overlay_window()
            
        except Exception as e:
            logger.error(f"Error updating overlay: {str(e)}", exc_info=True)
            try:
                self.create_overlay_window()
            except Exception as e2:
                logger.error(f"Failed to recreate overlay window: {str(e2)}", exc_info=True)

    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        previous_state = self.active
        self.active = not self.active
        logger.info(f"Overlay {'activated' if self.active else 'deactivated'}")
        
        # Only destroy window if we're turning off
        if not self.active:
            self._destroy_window_safely()
        # Only create window if we're turning on AND pattern matching is active
        elif self.pattern_matching_active:
            self.create_overlay_window() 