"""
Overlay View

This module provides the overlay view for visualizing detection results in real-time.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

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
    
    def __init__(self, window_service: WindowServiceInterface):
        """
        Initialize the overlay view.
        
        Args:
            window_service: Service for window management
        """
        super().__init__(None, Qt.WindowType.FramelessWindowHint | 
                        Qt.WindowType.WindowStaysOnTopHint | 
                        Qt.WindowType.Tool)
        
        # Store services
        self.window_service = window_service
        
        # Initialize state
        self._results = []
        self._target_window_rect = None
        self._visible = False
        
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
        
        # Configure window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        
        # Create update timer
        self._create_update_timer()
        
        logger.info("Overlay view initialized")
    
    def _create_update_timer(self):
        """Create timer for updating overlay position and content."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_position)
        self.update_timer.start(100)  # 10 fps
    
    def _update_position(self):
        """Update overlay position to match target window."""
        if self._visible:
            # Get target window position and size
            target_rect = self.window_service.get_window_rect()
            
            if target_rect and target_rect != self._target_window_rect:
                # Update overlay position and size
                self.setGeometry(target_rect)
                self._target_window_rect = target_rect
                self.update()
    
    def update_results(self, results: List[Dict[str, Any]]):
        """
        Update detection results to display.
        
        Args:
            results: List of detection result dictionaries
        """
        self._results = results
        self.update()
        
        logger.debug(f"Updated overlay with {len(results)} results")
    
    def show_overlay(self, show: bool):
        """
        Show or hide the overlay.
        
        Args:
            show: Whether to show the overlay
        """
        if self._visible == show:
            return
            
        self._visible = show
        
        if show:
            # Update position before showing
            self._update_position()
            self.show()
        else:
            self.hide()
            
        # Emit signal
        self.visibility_changed.emit(show)
        
        logger.debug(f"Overlay visibility changed to {show}")
    
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
        if not self._visible or not self._results:
            return
        
        # Create painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw results ourselves if window_service doesn't have the method
        if hasattr(self.window_service, 'draw_detection_results'):
            self.window_service.draw_detection_results(painter, self._results)
        else:
            self._draw_detection_results(painter)
    
    def _draw_detection_results(self, painter: QPainter):
        """
        Draw detection results on the overlay.
        
        Args:
            painter: QPainter instance to draw with
        """
        # Get options
        show_boxes = self._options["show_bounding_boxes"]
        show_labels = self._options["show_labels"]
        show_confidence = self._options["show_confidence"]
        box_color = self._options["box_color"]
        text_color = self._options["text_color"]
        line_width = self._options["line_width"]
        
        # Set up painter
        box_pen = QPen(box_color)
        box_pen.setWidth(line_width)
        
        # Draw each result
        for result in self._results:
            # Get bounding box
            x = result.get("x", 0)
            y = result.get("y", 0)
            width = result.get("width", 0)
            height = result.get("height", 0)
            
            if show_boxes and width > 0 and height > 0:
                # Draw bounding box
                painter.setPen(box_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(x, y, width, height)
            
            if show_labels:
                # Get label
                label = result.get("label", "")
                confidence = result.get("confidence", 0.0)
                
                if label:
                    # Create label text
                    if show_confidence and confidence > 0:
                        text = f"{label} ({confidence:.2f})"
                    else:
                        text = label
                    
                    # Draw label background
                    text_rect = painter.fontMetrics().boundingRect(text)
                    text_rect.moveTo(x, y - text_rect.height())
                    background_rect = text_rect.adjusted(-4, -2, 4, 2)
                    
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
                    painter.drawRect(background_rect)
                    
                    # Draw label text
                    painter.setPen(text_color)
                    painter.drawText(text_rect, text)