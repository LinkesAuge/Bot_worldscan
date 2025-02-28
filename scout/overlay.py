"""
Overlay System

This module provides a transparent overlay for visualizing detected game elements.
It handles:
- Template matching visualization
- Real-time updates
- Visual feedback
"""

from typing import Optional, List, Tuple, Dict, Any
import cv2
import numpy as np
import win32gui
import win32con
import win32api
from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatch, GroupedMatch, TemplateMatcher
import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt
from scout.automation.gui.spinning_indicator import SpinningIndicator
import time
from scout.game_state import GameState

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
    - Real-time template match visualization
    - Click-through transparency
    - Automatic window tracking
    - Configurable visual elements
    """
    
    def __init__(self, window_manager: WindowManager, 
                 template_settings: Dict[str, Any], overlay_settings: Dict[str, Any]) -> None:
        """
        Initialize the overlay window with specified settings.
        
        Creates a transparent window that tracks and draws over the game window.
        The overlay uses OpenCV for drawing and Win32 API for window management.
        
        Args:
            window_manager: Manager for tracking the game window
            template_settings: Template matching configuration
            overlay_settings: Visual settings (colors, sizes, etc.)
        """
        super().__init__()
        self.window_manager = window_manager
        self.window_name = "TB Scout Overlay"
        self.active = overlay_settings.get("active", False)
        self.template_matching_active = False
        self.window_hwnd = None  # Store window handle
        self.window_created = False  # Flag to track if window has been created
        
        # Create game state tracker
        self.game_state = GameState(window_manager)
        
        # Animation state
        self.refreshing = False
        self.refresh_start_time = 0.0
        
        # Separate timers for template matching and drawing
        self.template_matching_timer = QTimer()
        self.template_matching_timer.timeout.connect(self._update_template_matching)
        
        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self._draw_overlay)
        self.draw_timer.setInterval(33)  # ~30 FPS for drawing
        
        # Add match caching with group persistence
        self.cached_matches: List[Tuple[str, int, int, int, int, float]] = []  # Current cached matches
        self.match_counters: Dict[str, int] = {}  # Cache counters for groups
        # Load persistence and distance settings from config
        self.match_persistence = template_settings.get("match_persistence", 3)  # Default to 3 frames if not in config
        self.distance_threshold = template_settings.get("distance_threshold", 100)  # Default to 100 pixels if not in config
        
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
        
        # Create template matcher and make it accessible
        self.template_matcher = TemplateMatcher(
            window_manager=self.window_manager,
            confidence=template_settings["confidence"],
            target_frequency=template_settings["target_frequency"],
            sound_enabled=template_settings["sound_enabled"]
        )
        
        # Ensure templates are loaded
        self.template_matcher.reload_templates()
        template_count = len(self.template_matcher.templates)
        logger.info(f"Loaded {template_count} templates for template matching")
        if template_count == 0:
            logger.warning("No templates found! Template matching will not work without templates")

        logger.debug(f"Initialized overlay with rect_color={self.rect_color}, "
                    f"font_color={self.font_color}, "
                    f"thickness={self.rect_thickness}, "
                    f"font_size={self.font_size}, "
                    f"rect_scale={self.rect_scale}")

        # Create the overlay window now, but keep it hidden
        logger.info("Creating overlay window at initialization")
        self.create_overlay_window()
        if not self.active:
            self._hide_window()

        # Create spinning indicator
        self.spinning_indicator = SpinningIndicator(self)
        self.spinning_indicator.hide()  # Initially hidden
        self.spinning_indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # Allow click-through

    def create_overlay_window(self) -> None:
        """Create the overlay window with transparency."""
        # Check if we already have a valid window
        if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
            logger.info(f"Window already exists with handle {self.window_hwnd} - updating position")
            self._update_window_position()
            return
            
        logger.info("Creating overlay window")
        
        # Get client area position and size
        client_rect = self.window_manager.get_client_rect()
        if not client_rect:
            logger.warning("Target window not found, cannot create overlay")
            return
        
        left, top, right, bottom = client_rect
        width = right - left
        height = bottom - top
        
        # Validate dimensions
        if width <= 0 or height <= 0:
            logger.error(f"Invalid window dimensions: {width}x{height}")
            return
        
        logger.debug(f"Creating overlay window at ({left}, {top}) with size {width}x{height}")
        
        try:
            # Create initial transparent overlay
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Magenta background for transparency
            
            # Create window with proper style - initially invisible
            window_style = cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO
            cv2.namedWindow(self.window_name, window_style)
            
            # Get window handle before showing anything
            hwnd = win32gui.FindWindow(None, self.window_name)
            if not hwnd:
                logger.error("Failed to create overlay window")
                return
                
            # Store the new window handle
            self.window_hwnd = hwnd
            self.window_created = True
            logger.debug(f"Created window with handle: {hwnd}")
            
            # Set window styles for transparency BEFORE showing content
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER | win32con.WS_SYSMENU)
            style |= win32con.WS_POPUP
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            # Set extended window styles for transparency and click-through
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            # Position window off-screen initially to prevent flash
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                -10000, -10000, width, height,  # Position off-screen initially
                win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW
            )
            
            # Apply transparency color key
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha (0 = fully transparent for non-magenta pixels)
                win32con.LWA_COLORKEY
            )
            
            # Now show the content with transparency 
            cv2.imshow(self.window_name, overlay)
            cv2.waitKey(1)  # Process events
            
            # Wait a tiny bit for window to initialize transparency
            time.sleep(0.05)
            
            # Move window to proper position
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                left, top, width, height,
                win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW
            )
            
            # Initially hide the window if overlay is not active
            if not self.active:
                self._hide_window()
                logger.debug("Window initially hidden as overlay is not active")
            else:
                # Make sure transparency settings are applied
                self._draw_empty_overlay()
                logger.debug("Window initially shown with transparency")
            
            logger.debug("Overlay window created with transparency settings")
            
        except Exception as e:
            logger.error(f"Error creating overlay window: {e}")
            return

    def _draw_empty_overlay(self) -> None:
        """Draw an empty transparent overlay to ensure window is properly initialized."""
        if not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
            return
            
        try:
            # Get current window size from client area
            client_rect = self.window_manager.get_client_rect()
            if not client_rect:
                return
                
            left, top, right, bottom = client_rect
            width = right - left
            height = bottom - top
            
            # Create empty magenta background (for transparency)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Show the empty overlay without forcing a redraw
            cv2.imshow(self.window_name, overlay)
            cv2.waitKey(1)
            
            # Ensure window is positioned correctly
            win32gui.SetWindowPos(
                self.window_hwnd,
                win32con.HWND_TOPMOST,
                left, top, width, height,
                win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW
            )
            
            # Refresh transparency settings
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
        except Exception as e:
            logger.error(f"Error drawing empty overlay: {e}")

    def _update_window_position(self) -> None:
        """Update the overlay window position and size to match the game window."""
        if not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Cannot update position - window handle is invalid")
            return
            
        pos = self.window_manager.get_window_position()
        if not pos:
            logger.warning("Target window not found, cannot update overlay position")
            return
            
        x, y, width, height = pos
        
        try:
            # Update window position, size and ensure it's topmost
            win32gui.SetWindowPos(
                self.window_hwnd, win32con.HWND_TOPMOST,
                x, y, width, height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            logger.debug(f"Updated window position to ({x}, {y}) with size {width}x{height}")
        except Exception as e:
            logger.error(f"Error updating window position: {e}")

    def _hide_window(self) -> None:
        """Hide the overlay window."""
        if not self.window_created or not self.window_hwnd:
            return
            
        if not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Invalid window handle in hide_window - marking as not created")
            self.window_hwnd = None
            self.window_created = False
            return
            
        try:
            win32gui.ShowWindow(self.window_hwnd, win32con.SW_HIDE)
            logger.debug("Window hidden")
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
            # Even if hiding fails, we keep the handle since we might be able to use it later

    def _show_window(self) -> None:
        """Show the overlay window."""
        if not self.window_created or not self.window_hwnd:
            # Create window if it doesn't exist
            self.create_overlay_window()
            return
            
        if not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Invalid window handle - recreating window")
            self.window_hwnd = None
            self.window_created = False
            self.create_overlay_window()
            return
            
        try:
            # Update position before showing
            self._update_window_position()
            
            # Draw something immediately to ensure proper transparency
            self._draw_empty_overlay()
            
            # Show window and make it topmost
            win32gui.ShowWindow(self.window_hwnd, win32con.SW_SHOW)
            win32gui.SetWindowPos(
                self.window_hwnd, win32con.HWND_TOPMOST,
                0, 0, 0, 0,  # Ignore position/size parameters
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            
            # Refresh transparency
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
            
            logger.debug("Window shown and set as topmost with transparency")
        except Exception as e:
            logger.error(f"Error showing window: {e}")
            # If we encounter an error, try recreating the window
            self.window_hwnd = None
            self.window_created = False
            self.create_overlay_window()

    def start_template_matching(self) -> None:
        """Start template matching."""
        logger.info("Starting template matching")
        
        # If template matching is already active, just make sure window is shown
        if self.template_matching_active:
            logger.debug("Template matching is already active")
            if self.active:
                self._show_window()
            return
            
        self.template_matching_active = True
        
        # Show overlay window if both overlay and template matching are active
        if self.active:
            self._show_window()
            logger.debug("Showing overlay window for template matching")
        else:
            logger.debug(f"Not showing overlay window - active: {self.active}")
        
        # Clear match cache before starting new matching session
        self.cached_matches = []
        self.match_counters.clear()
        
        # Start both timers if not already running
        logger.debug(f"Starting timers - draw timer active: {self.draw_timer.isActive()}, template timer active: {self.template_matching_timer.isActive()}")
        
        # Always stop timers first to ensure a clean restart
        if self.template_matching_timer.isActive():
            self.template_matching_timer.stop()
            logger.debug("Stopped template matching timer before restart")
            
        if self.draw_timer.isActive():
            self.draw_timer.stop()
            logger.debug("Stopped draw timer before restart")
        
        # Start template matching timer with updated interval
        self.update_timer_interval()  # This will start the template matching timer
        logger.debug(f"Template matching timer started with interval: {self.template_matching_timer.interval()} ms")
            
        # Start draw timer with fixed interval
        self.draw_timer.setInterval(33)  # ~30 FPS
        self.draw_timer.start()
        logger.debug("Draw timer started with 33ms interval")
        
        # Force an immediate draw to ensure everything is working
        self._draw_overlay()
        
        logger.debug("Template matching started successfully")

    def update_timer_interval(self) -> None:
        """Update the template matching timer interval based on target frequency."""
        if not hasattr(self.template_matcher, 'target_frequency'):
            logger.warning("Template matcher has no target_frequency attribute")
            return
            
        interval = max(int(1000 / self.template_matcher.target_frequency), 16)  # Minimum 16ms (60 FPS max)
        logger.debug(
            f"Updating template matching timer interval: "
            f"target_frequency={self.template_matcher.target_frequency:.2f} updates/sec -> "
            f"interval={interval}ms"
        )
        
        if self.template_matching_active:
            # Stop the timer if it's running
            if self.template_matching_timer.isActive():
                self.template_matching_timer.stop()
            
            # Set new interval and start timer
            self.template_matching_timer.setInterval(interval)
            self.template_matching_timer.start()
            logger.info(f"Template matching timer restarted with new interval: {interval}ms")

    def _destroy_window_safely(self) -> None:
        """Safely destroy the overlay window if it exists."""
        try:
            # First check if we have a stored handle
            if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
                logger.debug(f"Hiding window with stored handle: {self.window_hwnd}")
                self._hide_window()
                # Don't destroy window, just hide it
                # cv2.destroyWindow(self.window_name)
                # self.window_hwnd = None
                # self.window_created = False
                # logger.info("Overlay window destroyed (using stored handle)")
                return
                
            # If not, try to find by name
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                logger.debug(f"Hiding window with found handle: {hwnd}")
                self.window_hwnd = hwnd
                self._hide_window()
                # Don't destroy window, just hide it
                # cv2.destroyWindow(self.window_name)
                # logger.info("Overlay window destroyed (using found handle)")
        except Exception as e:
            logger.debug(f"Window hide skipped: {e}")

    def _get_group_key(self, match: Tuple[str, int, int, int, int, float]) -> str:
        """Get the cache key for a match based on approximate position only (not template name)."""
        _, x, y, _, _, _ = match
        # Use grid-based position to allow for small movements
        grid_size = self.distance_threshold
        grid_x = x // grid_size
        grid_y = y // grid_size
        # No longer include template name in key since we want to group across templates
        return f"pos_{grid_x}_{grid_y}"

    def _is_same_group(self, match1: Tuple[str, int, int, int, int, float],
                      match2: Tuple[str, int, int, int, int, float]) -> bool:
        """
        Check if two matches belong to the same group based on position.
        Matches from different templates can be grouped if they are close enough.
        
        Args:
            match1: First match tuple (name, x, y, w, h, conf)
            match2: Second match tuple (name, x, y, w, h, conf)
            
        Returns:
            bool: True if matches are in the same group
        """
        # Extract positions and dimensions
        name1, x1, y1, w1, h1, _ = match1
        name2, x2, y2, w2, h2, _ = match2
        
        # Calculate centers
        center1_x = x1 + w1 // 2
        center1_y = y1 + h1 // 2
        center2_x = x2 + w2 // 2
        center2_y = y2 + h2 // 2
        
        # Check if centers are within threshold
        return (abs(center1_x - center2_x) <= self.distance_threshold and
                abs(center1_y - center2_y) <= self.distance_threshold)

    def _update_template_matching(self) -> None:
        """Run template matching update cycle."""
        try:
            # Calculate actual update frequency
            current_time = time.time()
            if self.template_matcher.last_update_time > 0:
                time_diff = current_time - self.template_matcher.last_update_time
                if time_diff > 0:
                    self.template_matcher.update_frequency = 1.0 / time_diff
            self.template_matcher.last_update_time = current_time
            
            # If refreshing and past initial delay, update matches
            if self.refreshing and time.time() - self.refresh_start_time > self.game_state.drag_start_delay:
                self.refreshing = False
                
            logger.debug("Running template matching update")
            
            # Capture window image
            image = self.template_matcher.capture_window()
            if image is None:
                logger.warning("Failed to capture window for template matching")
                return
                
            logger.debug(f"Captured image with shape: {image.shape}")
            
            # First get all matches in GroupedMatch format
            matches = self.template_matcher.find_matches(image)
            logger.debug(f"Found {len(matches)} match groups")
            
            # Convert grouped matches to tuple format with averaged positions
            current_matches = []
            
            for group in matches:
                # Calculate average position for the group
                avg_x = sum(m.bounds[0] for m in group.matches) // len(group.matches)
                avg_y = sum(m.bounds[1] for m in group.matches) // len(group.matches)
                # Use width and height from first match since they should be the same
                width = group.matches[0].bounds[2]
                height = group.matches[0].bounds[3]
                # Use highest confidence from the group
                confidence = max(m.confidence for m in group.matches)
                
                match_tuple = (
                    group.template_name,
                    avg_x,
                    avg_y,
                    width,
                    height,
                    confidence
                )
                current_matches.append(match_tuple)
                
                logger.debug(
                    f"Group for {group.template_name}: {len(group.matches)} matches, "
                    f"average position: ({avg_x}, {avg_y}), confidence: {confidence:.2f}"
                )
            
            # Check if we have any new matches that weren't in the cache
            new_matches_found = False
            for current_match in current_matches:
                if not any(self._is_same_group(current_match, cached) for cached in self.cached_matches):
                    new_matches_found = True
                    break
            
            # Play sound if we found new matches and sound is enabled
            if new_matches_found and self.template_matcher.sound_enabled:
                logger.debug("New matches found - playing sound alert")
                self.template_matcher.sound_manager.play_if_ready()
            
            # Handle match persistence based on groups
            all_matches = []
            new_counters = {}
            
            # First, add all current matches
            for current_match in current_matches:
                group_key = self._get_group_key(current_match)
                # Check if we already have a match in this group
                existing_match = None
                for match in all_matches:
                    if self._is_same_group(current_match, match):
                        existing_match = match
                        break
                
                if existing_match:
                    # If existing match has lower confidence, replace it
                    if current_match[5] > existing_match[5]:
                        all_matches.remove(existing_match)
                        all_matches.append(current_match)
                        new_counters[group_key] = 0
                else:
                    # No existing match in this group, add new match
                    all_matches.append(current_match)
                    new_counters[group_key] = 0
                
                logger.debug(f"Added current match for group {group_key}")
            
            # Then check cached matches
            for cached_match in self.cached_matches:
                group_key = self._get_group_key(cached_match)
                
                # Skip if this group already has a match
                if group_key in new_counters:
                    continue
                
                # Check if this cached match is close to any current match
                # Skip if it's too close to avoid duplicates
                if any(self._is_same_group(cached_match, current) for current in current_matches):
                    continue
                
                # Increment counter for this group
                counter = self.match_counters.get(group_key, 0) + 1
                
                if counter < self.match_persistence:
                    # Keep the match if within persistence window
                    all_matches.append(cached_match)
                    new_counters[group_key] = counter
                    logger.debug(f"Using cached match for group {group_key} (frame {counter}/{self.match_persistence})")
                else:
                    logger.debug(f"Cache cleared for group {group_key}")
            
            # Update cache and counters
            self.cached_matches = all_matches
            self.match_counters = new_counters
            
            # Update game state with new matches
            self.game_state.update_template_matches(self.cached_matches)
            
        except Exception as e:
            logger.error(f"Error in template matching update: {e}", exc_info=True)
            # Reset frequency tracking on error
            self.template_matcher.update_frequency = 0.0
            self.template_matcher.last_update_time = 0.0

    def _draw_overlay(self) -> None:
        """Draw the overlay with current matches."""
        try:
            # Update game state
            self.game_state.update()
            
            # Check if we need to start refreshing
            if self.game_state.is_dragging() and not self.refreshing:
                self._start_refresh()
            
            # First log whether conditions for drawing are met
            if not self.active:
                logger.debug("Not drawing overlay - overlay is not active")
                return
                
            if not self.window_created or not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
                logger.debug("Window not valid for drawing - recreating")
                self.window_hwnd = None
                self.window_created = False
                self.create_overlay_window()
                if not self.window_hwnd:
                    logger.error("Failed to create overlay window for drawing")
                    return
            
            # Check if target window is minimized or hidden
            if self.window_manager.is_window_minimized_or_hidden():
                logger.debug("Target window is minimized or hidden - not drawing overlay")
                self._hide_window()
                return
            
            # Get client area for drawing
            client_rect = self.window_manager.get_client_rect()
            if not client_rect:
                logger.warning("Target window not found during draw")
                return
            
            left, top, right, bottom = client_rect
            width = right - left
            height = bottom - top
            
            # Only update window position if it has changed significantly
            try:
                current_rect = win32gui.GetWindowRect(self.window_hwnd)
                current_left, current_top, current_right, current_bottom = current_rect
                current_width = current_right - current_left
                current_height = current_bottom - current_top
                
                # Check if position or size has changed by more than 2 pixels
                position_changed = (
                    abs(left - current_left) > 2 or
                    abs(top - current_top) > 2 or
                    abs(width - current_width) > 2 or
                    abs(height - current_height) > 2
                )
                
                if position_changed:
                    logger.debug("Window position/size changed - updating overlay")
                    win32gui.SetWindowPos(
                        self.window_hwnd, win32con.HWND_TOPMOST,
                        left, top, width, height,
                        win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW
                    )
            except Exception as e:
                logger.error(f"Error updating window position: {e}")
                # Try to recreate window if this fails
                self.window_hwnd = None
                self.window_created = False
                self.create_overlay_window()
                return
                
            # Create magenta background (will be transparent)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Draw status indicators at top center
            status_y = 30
            
            # Calculate total width of all elements to center them as a group
            debug_text = "Overlay Active"
            refresh_text = "Refreshing Overlay"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5  # Smaller font for debug text
            refresh_font_scale = 1.0  # Larger font for refresh text
            thickness = 1
            refresh_thickness = 2
            
            # Get text sizes
            (debug_width, debug_height), _ = cv2.getTextSize(debug_text, font, font_scale, thickness)
            (refresh_width, refresh_height), _ = cv2.getTextSize(refresh_text, font, refresh_font_scale, refresh_thickness)
            
            # Calculate total width including match count if needed
            total_width = debug_width + 40  # Add space for circle and gaps
            match_text = ""
            match_width = 0
            
            if self.template_matching_active and not self.refreshing:
                match_count = len(self.cached_matches)
                match_text = f"{match_count} Match{'es' if match_count > 1 else ''} Found"
                (match_width, _), _ = cv2.getTextSize(match_text, font, font_scale, thickness)
                total_width += match_width + 40  # Add space for match text
            
            if self.refreshing:
                total_width += refresh_width + self.spinning_indicator.width() + 20  # Add space for refresh text and indicator
            
            # Start position for debug elements (shifted left from center)
            start_x = (width - total_width) // 2
            
            # Draw debug circle and "Overlay Active" text
            circle_x = start_x + 10  # Add some padding
            cv2.circle(overlay, (circle_x, status_y), 10, (0, 255, 0), -1)  # Keep circle green
            cv2.putText(
                overlay,
                debug_text,
                (circle_x + 20, status_y + 5),  # Position text next to circle
                font,
                font_scale,
                (0, 255, 0),  # Keep debug text green
                thickness,
                cv2.LINE_AA
            )
            
            # Draw template match count if we have matches
            if self.template_matching_active and not self.refreshing:
                match_x = start_x + debug_width + 40  # Position after debug text
                cv2.putText(
                    overlay,
                    match_text,
                    (match_x, status_y + 5),  # Align with debug text
                    font,
                    font_scale,
                    (0, 0, 255),  # Red color
                    thickness,
                    cv2.LINE_AA
                )
            
            # Handle refreshing state
            if self.refreshing:
                # Calculate position for refresh text (to the right of other elements)
                refresh_x = start_x + debug_width + 40
                if match_width > 0:
                    refresh_x += match_width + 40  # Add space after match text if present
                
                # Draw "Refreshing Overlay" text in red
                cv2.putText(
                    overlay,
                    refresh_text,
                    (refresh_x, status_y + 5),  # Align with other text
                    font,
                    refresh_font_scale,
                    (0, 0, 255),  # Red color
                    refresh_thickness,
                    cv2.LINE_AA
                )
                
                # Position spinning indicator next to the text
                if self.spinning_indicator and self.window_hwnd:
                    try:
                        # Get window position
                        window_rect = win32gui.GetWindowRect(self.window_hwnd)
                        window_x = window_rect[0]
                        window_y = window_rect[1]
                        
                        # Position indicator to the right of the text
                        indicator_x = window_x + refresh_x + refresh_width + 10  # Add small gap
                        indicator_y = window_y + status_y - (self.spinning_indicator.height() // 2) + 5  # Center vertically with text
                        
                        logger.debug(f"Positioning spinner at ({indicator_x}, {indicator_y})")
                        self.spinning_indicator.move(indicator_x, indicator_y)
                        self.spinning_indicator.show()
                        self.spinning_indicator.raise_()
                    except Exception as e:
                        logger.error(f"Error positioning spinning indicator: {e}")
            else:
                self.spinning_indicator.hide()
            
            # Draw matches if template matching is active and we're not refreshing
            if self.template_matching_active and not self.refreshing and self.cached_matches:
                match_count = len(self.cached_matches)
                logger.debug(f"Drawing {match_count} matches on overlay")
                
                # Draw each match
                for i, match_data in enumerate(self.cached_matches):
                    if not isinstance(match_data, tuple) or len(match_data) != 6:
                        continue
                        
                    name, match_x, match_y, match_width, match_height, confidence = match_data
                    
                    # Calculate center point and scaled dimensions
                    center_x = match_x + match_width // 2
                    center_y = match_y + match_height // 2
                    scaled_width = int(match_width * self.rect_scale)
                    scaled_height = int(match_height * self.rect_scale)
                    
                    # Calculate bounds relative to client area
                    new_x1 = max(0, min(int(center_x - scaled_width // 2), width - 1))
                    new_y1 = max(0, min(int(center_y - scaled_height // 2), height - 1))
                    new_x2 = max(0, min(int(new_x1 + scaled_width), width - 1))
                    new_y2 = max(0, min(int(new_y1 + scaled_height), height - 1))
                    
                    # Skip if rectangle is too small
                    if new_x2 - new_x1 < 10 or new_y2 - new_y1 < 10:
                        continue
                    
                    # Draw rectangle
                    cv2.rectangle(
                        overlay,
                        (new_x1, new_y1),
                        (new_x2, new_y2),
                        self.rect_color,
                        self.rect_thickness
                    )
                    
                    # Draw text
                    text = f"{name} ({confidence:.2f})"
                    cv2.putText(
                        overlay,
                        text,
                        (new_x1, max(5, new_y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.font_size / 30,
                        self.font_color,
                        self.text_thickness
                    )
                    
                    # Draw cross
                    scaled_cross_size = int(self.cross_size * self.cross_scale)
                    half_size = scaled_cross_size // 2
                    cv2.line(
                        overlay,
                        (center_x - half_size, center_y),
                        (center_x + half_size, center_y),
                        self.cross_color,
                        self.cross_thickness
                    )
                    cv2.line(
                        overlay,
                        (center_x, center_y - half_size),
                        (center_x, center_y + half_size),
                        self.cross_color,
                        self.cross_thickness
                    )
            
            # Show overlay
            cv2.imshow(self.window_name, overlay)
            cv2.waitKey(1)
            
            # Ensure transparency is maintained
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
            
        except Exception as e:
            logger.error(f"Error updating overlay: {str(e)}", exc_info=True)

    def _start_refresh(self) -> None:
        """Start the refresh process."""
        self.refreshing = True
        self.refresh_start_time = time.time()
        self.cached_matches = []  # Clear cached matches
        
        # Start spinning indicator
        self.spinning_indicator.start()
        
        # Force immediate template matching update
        self._update_template_matching()
        
    def stop_template_matching(self) -> None:
        """Stop template matching."""
        logger.info("Stopping template matching")
        self.template_matching_active = False
        
        # Stop timers and spinning indicator
        if self.template_matching_timer.isActive():
            self.template_matching_timer.stop()
        
        if self.draw_timer.isActive():
            self.draw_timer.stop()
            
        self.spinning_indicator.stop()
        
        # Reset template matcher frequency
        self.template_matcher.update_frequency = 0.0
        self.template_matcher.last_update_time = 0.0
        
        # Clear match cache
        self.cached_matches = []
        self.match_counters.clear()
        
        # Hide window but never destroy it
        if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
            self._hide_window()
            
        logger.debug("Template matching stopped, window hidden")

    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        previous_state = self.active
        self.active = not self.active
        logger.info(f"Overlay {'activated' if self.active else 'deactivated'}")
        
        if self.active:
            # Show window if template matching is also active
            if self.template_matching_active:
                self._show_window()
        else:
            # Hide window 
            self._hide_window() 