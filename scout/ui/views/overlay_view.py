"""
Overlay View

This module provides the overlay view for visualizing detection results in real-time.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import ctypes

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRect, QTimer, pyqtSignal

from scout.core.window.window_service_interface import WindowServiceInterface

# Set up logging
logger = logging.getLogger(__name__)


class OverlayView(QWidget):
    """
    Transparent window for visualizing detection results in real-time.
    
    This window is overlaid on top of the target application window
    and shows detection results as they occur. It updates its position
    automatically to stay aligned with the target window, and displays
    detection results using customizable visual styles.
    """
    
    # Signal emitted when overlay visibility changes
    visibility_changed = pyqtSignal(bool)
    
    def __init__(self, parent):
        """
        Initialize the overlay view.
        
        Args:
            parent: Parent window containing the window service
        """
        # Use the most aggressive window flags to ensure visibility
        super().__init__(None, 
                       Qt.WindowType.Window |  # Changed from FramelessWindowHint to full Window
                       Qt.WindowType.WindowStaysOnTopHint |
                       Qt.WindowType.FramelessWindowHint |
                       Qt.WindowType.X11BypassWindowManagerHint |  # Try to bypass window manager
                       Qt.WindowType.BypassWindowManagerHint |     # Try to bypass window manager (alternative)
                       Qt.WindowType.Tool)
        
        # Get window service from parent
        if hasattr(parent, 'window_service'):
            self.window_service = parent.window_service
        else:
            # Fallback - parent is the window service
            self.window_service = parent
            
        # Store parent reference
        self.parent_window = parent
        
        # Initialize state
        self._results = []
        self._target_window_rect = None
        self._visible = False
        self._update_failure_count = 0
        self._max_failures = 5  # Hide after this many consecutive failures
        self.debug_mode = True  # Default to debug mode ON for now to help troubleshoot
        self._last_click_pos = None  # Store last click position for debugging
        
        # Overlay display options
        self._options = {
            "show_bounding_boxes": True,
            "show_labels": True,
            "show_confidence": True,
            "box_color": QColor(0, 255, 0, 128),  # Semi-transparent green
            "text_color": QColor(255, 255, 255),  # White
            "font_size": 10,
            "line_width": 2
        }
        
        # Configure window attributes - be very aggressive about transparency and staying on top
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)  # Try to always be on top
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        
        # Set window to be transparent to mouse events by default
        # Comment this out to allow interaction with the overlay for testing
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        logger.info("Overlay view initialized with enhanced visibility flags")
        
        # Create update timer - must be last to avoid accessing uninitialized members
        self._create_update_timer()
    
    def _create_update_timer(self):
        """Create timer for updating overlay position and content."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_position)
        self.update_timer.start(100)  # 10 fps
    
    def _update_position(self):
        """
        Update overlay position to match target window.
        
        Ensures the overlay stays aligned with the target window
        even when the window moves or changes size.
        """
        if not self._visible:
            return
            
        try:
            # Get target window position and size
            target_rect = self.window_service.get_window_position()
            
            if not target_rect:
                logger.warning("Failed to get target window position for overlay update")
                self._update_failure_count += 1
                
                # If we've had multiple consecutive failures, hide the overlay
                if self._update_failure_count >= self._max_failures:
                    logger.warning(f"Multiple failures finding target window ({self._update_failure_count}), hiding overlay")
                    self._visible = False
                    self.hide()
                return
            
            # Reset failure counter on success
            self._update_failure_count = 0
                
            # Convert position tuple to QRect if necessary
            if isinstance(target_rect, tuple) and len(target_rect) == 4:
                x, y, width, height = target_rect
                qt_rect = QRect(x, y, width, height)
            else:
                qt_rect = target_rect
                
            # Check if window rect has changed significantly
            significant_change = False
            if not self._target_window_rect:
                significant_change = True
            else:
                # Check if position or size has changed more than 1 pixel
                x_diff = abs(qt_rect.x() - self._target_window_rect.x())
                y_diff = abs(qt_rect.y() - self._target_window_rect.y())
                w_diff = abs(qt_rect.width() - self._target_window_rect.width())
                h_diff = abs(qt_rect.height() - self._target_window_rect.height())
                
                if x_diff > 1 or y_diff > 1 or w_diff > 1 or h_diff > 1:
                    significant_change = True
                    logger.debug(f"Window position changed: ({x_diff}, {y_diff}) size: ({w_diff}, {h_diff})")
            
            # Always update position, even for minor changes
            self.setGeometry(qt_rect)
            self._target_window_rect = qt_rect
            
            # Ensure overlay is visible and on top
            if not self.isVisible() and self._visible:
                logger.debug("Overlay should be visible but isn't - forcing show")
                self.show()
                
            # Force redraw if position changed significantly
            if significant_change and len(self._results) > 0:
                self.update()
                self.raise_()  # Ensure we stay on top
                
        except Exception as e:
            logger.error(f"Error updating overlay position: {str(e)}")
            # Increment failure counter
            self._update_failure_count += 1
            
            # Hide overlay after multiple consecutive failures
            if self._update_failure_count >= self._max_failures:
                logger.warning(f"Multiple failures updating overlay position ({self._update_failure_count}), hiding overlay")
                self._visible = False
                self.hide()
    
    def update_results(self, results: List[Dict[str, Any]]):
        """
        Update detection results to display.
        
        Args:
            results: List of detection result dictionaries
        """
        if results is None:
            results = []
            
        # Store results and update display
        self._results = results
        
        # Reset failure counter on successful update
        self._update_failure_count = 0
        
        # Force redraw
        if self._visible:
            self.update()
        
        logger.debug(f"Updated overlay with {len(results)} results")
    
    # Alias for update_results to match expected interface
    def set_results(self, results: List[Dict[str, Any]]):
        """
        Set detection results to display (alias for update_results).
        
        Args:
            results: List of detection result dictionaries
        """
        self.update_results(results)
    
    def show_overlay(self, show: bool):
        """
        Show or hide the overlay.
        
        Args:
            show: Whether to show the overlay
        """
        if self._visible == show:
            logger.debug(f"Overlay already {'visible' if show else 'hidden'}, no change needed")
            # Even if already in correct state, force update for visibility
            if show and not self.isVisible():
                logger.warning("Overlay should be visible but isn't - forcing visibility")
                self._force_visibility()
            return
            
        self._visible = show
        logger.info(f"Setting overlay visibility to {show}")
        
        try:
            if show:
                # Update position before showing
                target_rect = self.window_service.get_window_position()
                if not target_rect:
                    logger.warning("Cannot show overlay: target window not found")
                    self._visible = False
                    return
                
                # Convert position tuple to QRect if necessary
                if isinstance(target_rect, tuple) and len(target_rect) == 4:
                    x, y, width, height = target_rect
                    qt_rect = QRect(x, y, width, height)
                else:
                    qt_rect = target_rect
                
                # Set geometry and ensure proper window flags
                self.setGeometry(qt_rect)
                self._target_window_rect = qt_rect
                
                # Always reset window flags to ensure proper behavior
                logger.debug("Setting window flags to ensure overlay stays on top")
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint | 
                    Qt.WindowType.WindowStaysOnTopHint |
                    Qt.WindowType.Tool
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                
                # Show and activate the overlay
                self.show()
                self.raise_()
                
                # Force a repaint
                self.update()
                
                # Make another attempt if not visible
                if not self.isVisible():
                    logger.warning("Overlay still not visible after show() - additional attempt to force visibility")
                    self._force_visibility()
                
                logger.debug(f"Overlay shown at position: {qt_rect}")
            else:
                # Hide the overlay
                self.hide()
                logger.debug("Overlay hidden")
                
            # Emit signal
            self.visibility_changed.emit(show)
            
        except Exception as e:
            logger.error(f"Error changing overlay visibility to {show}: {str(e)}")
            self._visible = False
            self.hide()
            
    def _force_visibility(self):
        """Force the overlay to be visible using an aggressive approach."""
        try:
            # Get current position
            current_pos = self.geometry()
            logger.debug(f"Forcing overlay visibility at position: {current_pos}")
            
            # More aggressive approach to fix visibility issues
            
            # 1. First try hiding to reset state
            self.hide()
            
            # 2. Set even more aggressive window flags to stay on top
            flags = (Qt.WindowType.Window |  # Try with Window flag first
                    Qt.WindowType.FramelessWindowHint | 
                    Qt.WindowType.WindowStaysOnTopHint |
                    Qt.WindowType.Tool |
                    Qt.WindowType.BypassWindowManagerHint |
                    Qt.WindowType.X11BypassWindowManagerHint)
                    
            self.setWindowFlags(flags)
            
            # 3. Ensure necessary attributes are set
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
            
            # 4. If we have a target rect, ensure we're positioned correctly
            if self._target_window_rect:
                self.setGeometry(self._target_window_rect)
            elif current_pos.isValid():
                self.setGeometry(current_pos)
                
            # 5. Show and force to top
            self.show()
            self.raise_()
            self.repaint()  # Force immediate repaint
            
            # 6. Try to activate (might help with some window managers)
            self.activateWindow()
            
            # 7. Additional Windows-specific API call to force always-on-top
            try:
                if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'user32'):
                    # Get window handle
                    hwnd = self.winId()
                    # HWND_TOPMOST = -1
                    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 
                                                     0x0001 | 0x0002 | 0x0010 | 0x0040)
                    logger.debug("Used Windows SetWindowPos API to force topmost state")
            except Exception as e:
                logger.error(f"Error using Windows SetWindowPos API: {e}")
                
            logger.debug(f"Force visibility completed, is visible: {self.isVisible()}")
        except Exception as e:
            logger.error(f"Error forcing overlay visibility: {str(e)}")
    
    def is_visible(self) -> bool:
        """
        Check if the overlay is currently visible.
        
        Returns:
            True if the overlay is visible, False otherwise
        """
        return self._visible
    
    def set_options(self, options: Dict[str, Any]):
        """
        Set overlay display options.
        
        Args:
            options: Display options dictionary
        """
        # Update options
        self._options.update(options)
        
        # Redraw
        self.update()
        
        logger.debug("Overlay display options updated")
    
    def paintEvent(self, event):
        """
        Handle paint event.
        
        Args:
            event: Paint event
        """
        try:
            # Always create painter even if no results to draw background
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # In debug mode, make the overlay extremely visible
            if self.debug_mode:
                # Draw a highly visible background
                debug_color = QColor(255, 0, 0, 60)  # More intense red background for debug mode
                painter.fillRect(self.rect(), debug_color)
                
                # Draw a very visible border
                border_pen = QPen(QColor(255, 0, 0, 200))  # Bright red for debug
                border_pen.setWidth(6)
                painter.setPen(border_pen)
                painter.drawRect(self.rect().adjusted(3, 3, -3, -3))
                
                # Draw a diagonal cross to make debugging super obvious
                painter.drawLine(0, 0, self.width(), self.height())
                painter.drawLine(0, self.height(), self.width(), 0)
                
                # Add extensive debug info
                window_pos = f"{self.geometry().x()}, {self.geometry().y()}, {self.width()}x{self.height()}"
                window_handle = f"Window handle: {self.winId()}" if hasattr(self, 'winId') else "No window handle"
                debug_info = [
                    f"DEBUG MODE ON - Overlay Active",
                    f"Visible: {self._visible} | IsVisible: {self.isVisible()}",
                    f"Position: {window_pos}",
                    f"Results: {len(self._results)} items",
                    f"Failure count: {self._update_failure_count}",
                    window_handle,
                ]
                
                # Add click position info if we have it
                if self._last_click_pos:
                    debug_info.append(f"Last click: {self._last_click_pos[0]}, {self._last_click_pos[1]}")
                
                # Background for debug text
                text_rect = QRect(10, 10, 400, 30 * len(debug_info))
                painter.fillRect(text_rect, QColor(0, 0, 0, 200))
                
                # Draw each line of debug info
                painter.setPen(QColor(255, 255, 0))  # Bright yellow for visibility
                font = painter.font()
                font.setPointSize(12)  # Larger font for debug
                painter.setFont(font)
                
                for i, line in enumerate(debug_info):
                    line_rect = QRect(10, 10 + i * 30, 400, 30)
                    painter.drawText(line_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
                    
                # If we have a last click position, draw a marker
                if self._last_click_pos:
                    x, y = self._last_click_pos
                    # Draw a crosshair at click position
                    marker_size = 20
                    click_pen = QPen(QColor(0, 255, 255, 200))  # Cyan color
                    click_pen.setWidth(2)
                    painter.setPen(click_pen)
                    painter.drawLine(x - marker_size, y, x + marker_size, y)  # Horizontal
                    painter.drawLine(x, y - marker_size, x, y + marker_size)  # Vertical
                    # Draw circle
                    painter.drawEllipse(x - marker_size/2, y - marker_size/2, marker_size, marker_size)
                    
            else:
                # Standard mode - just draw a subtle indicator that the overlay is active
                debug_color = QColor(255, 0, 0, 10)  # Very light red background
                painter.fillRect(self.rect(), debug_color)
                
                # Draw subtle border
                border_pen = QPen(QColor(255, 0, 0, 40))  # Semi-transparent light red
                border_pen.setWidth(1)
                painter.setPen(border_pen)
                painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
                
                # Add minimal debug text
                debug_text = f"Overlay Active - Results: {len(self._results)}"
                text_rect = QRect(10, 10, 300, 30)
                painter.fillRect(text_rect, QColor(0, 0, 0, 80))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, debug_text)
            
            # If no results or not visible for drawing purposes, return after drawing debug elements
            if not self._visible or not self._results:
                return
                
            # Draw results if we have them
            if hasattr(self.window_service, 'draw_detection_results'):
                self.window_service.draw_detection_results(painter, self._results)
            else:
                self._draw_detection_results(painter)
                
        except Exception as e:
            logger.error(f"Error in overlay paintEvent: {e}", exc_info=True)
    
    def _draw_detection_results(self, painter: QPainter):
        """
        Draw detection results on the overlay.
        
        Args:
            painter: QPainter instance to draw with
        """
        # Get options with debug mode adjustments
        show_boxes = self._options["show_bounding_boxes"]
        show_labels = self._options["show_labels"]
        show_confidence = self._options["show_confidence"]
        
        # In debug mode, use more prominent colors
        if self.debug_mode:
            box_color = QColor(255, 255, 0, 200)  # Bright yellow in debug mode
            text_color = QColor(255, 255, 0)      # Bright yellow text
            line_width = 4                         # Thicker lines in debug mode
        else:
            box_color = self._options["box_color"]
            text_color = self._options["text_color"]
            line_width = self._options["line_width"]
        
        # Log detection results if in debug mode
        if self.debug_mode:
            result_info = []
            for i, result in enumerate(self._results[:5]):  # Limit to first 5 for brevity
                template = result.get("template_name", "unknown")
                conf = result.get("confidence", 0.0)
                x = result.get("x", 0)
                y = result.get("y", 0)
                result_info.append(f"Result {i+1}: {template} at ({x}, {y}) - conf: {conf:.2f}")
            
            if result_info:
                logger.debug("Detection results in overlay:")
                for info in result_info:
                    logger.debug(f"  {info}")
        
        # Set up painter
        box_pen = QPen(box_color)
        box_pen.setWidth(line_width)
        
        # Draw each result
        for idx, result in enumerate(self._results):
            # Get bounding box
            x = result.get("x", 0)
            y = result.get("y", 0)
            width = result.get("width", 0)
            height = result.get("height", 0)
            template_name = result.get("template_name", "Unknown")
            confidence = result.get("confidence", 0.0)
            
            if show_boxes and width > 0 and height > 0:
                # Draw bounding box
                painter.setPen(box_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
                # In debug mode, add a number to the beginning of each box
                if self.debug_mode:
                    # Adjust box slightly larger in debug mode for visibility
                    adjusted_rect = QRect(x-2, y-2, width+4, height+4)
                    painter.drawRect(adjusted_rect)
                    
                    # Draw a filled circle with the result number
                    circle_size = 24
                    painter.setBrush(QBrush(QColor(0, 0, 0, 200)))
                    painter.drawEllipse(x - circle_size/2, y - circle_size/2, circle_size, circle_size)
                    
                    # Draw the result number
                    painter.setPen(QColor(255, 255, 0))
                    number_rect = QRect(x - circle_size/2, y - circle_size/2, circle_size, circle_size)
                    painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter, str(idx + 1))
                    
                    # Draw connecting lines to make it super obvious where the detection is
                    dashed_pen = QPen(box_color)
                    dashed_pen.setWidth(1)
                    dashed_pen.setStyle(Qt.PenStyle.DashLine)
                    painter.setPen(dashed_pen)
                    
                    # Draw cross through center
                    center_x = x + width / 2
                    center_y = y + height / 2
                    painter.drawLine(0, center_y, self.width(), center_y)  # Horizontal
                    painter.drawLine(center_x, 0, center_x, self.height())  # Vertical
                else:
                    # Normal mode - simple rectangle
                    painter.drawRect(x, y, width, height)
            
            if show_labels:
                # Create label text
                if show_confidence and confidence > 0:
                    text = f"{template_name} ({confidence:.2f})"
                else:
                    text = template_name
                
                if self.debug_mode:
                    # More detailed label in debug mode
                    text = f"#{idx+1}: {text} at ({x}, {y})"
                    
                    # Use larger font in debug mode
                    font = painter.font()
                    font.setPointSize(10)  # Larger font
                    painter.setFont(font)
                
                # Draw label background
                text_rect = painter.fontMetrics().boundingRect(text)
                text_rect.moveTo(x, y - text_rect.height())
                background_rect = text_rect.adjusted(-4, -2, 4, 2)
                
                # In debug mode, use more prominent label
                if self.debug_mode:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 200)))  # More opaque in debug mode
                    painter.drawRect(background_rect)
                    
                    # Draw label text
                    painter.setPen(text_color)
                    painter.drawText(text_rect, text)
                    
                    # Reset font if we changed it
                    font.setPointSize(self._options["font_size"])
                    painter.setFont(font)
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
                    painter.drawRect(background_rect)
                    
                    # Draw label text
                    painter.setPen(text_color)
                    painter.drawText(text_rect, text)
    
    def get_window_rect(self):
        """
        Get the window rectangle, acts as compatibility function.
        
        Returns:
            QRect containing the window rectangle (x, y, width, height)
        """
        try:
            # Get target window position using the available method
            position = self.window_service.get_window_position()
            
            if not position:
                return None
                
            # Convert position tuple to QRect
            if isinstance(position, tuple) and len(position) == 4:
                x, y, width, height = position
                return QRect(x, y, width, height)
            
            # If it's already a QRect, return it directly
            if isinstance(position, QRect):
                return position
                
            # Fallback case - return None if unsupported type
            logger.warning(f"Unsupported position type: {type(position)}")
            return None
            
        except Exception as e:
            logger.error(f"Error in get_window_rect: {str(e)}")
            return None

    def mousePressEvent(self, event):
        """
        Handle mouse press event for debugging.
        
        Args:
            event: Mouse press event
        """
        # Store click position for debugging
        self._last_click_pos = (event.pos().x(), event.pos().y())
        logger.info(f"Mouse clicked on overlay at: {self._last_click_pos}")
        
        # In debug mode, log more details about the click
        if self.debug_mode:
            # Get window position
            window_pos = self.geometry()
            
            # Calculate relative position to window
            rel_x = event.pos().x()
            rel_y = event.pos().y()
            
            # Calculate global position
            global_x = window_pos.x() + rel_x
            global_y = window_pos.y() + rel_y
            
            logger.info(f"Overlay mouse click - relative: ({rel_x}, {rel_y}), global: ({global_x}, {global_y})")
            
            # Update window to show click position
            self.update()
            
        # Let event propagate to the window beneath (if not WA_TransparentForMouseEvents)
        event.ignore()
        
    def mouseReleaseEvent(self, event):
        """Ignore mouse release events to let them pass through."""
        event.ignore()