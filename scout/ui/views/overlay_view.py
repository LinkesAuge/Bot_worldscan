"""
Overlay View

This module provides an overlay window that displays detection results
directly on top of the game window, providing real-time visual feedback
on template matches, OCR results, and object detections.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QGroupBox
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer, QPoint, QSize

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.events.event_types import EventType
from scout.core.events.event import Event

# Set up logging
logger = logging.getLogger(__name__)

class OverlayView(QWidget):
    """
    Transparent overlay window for displaying detection results.
    
    This class creates a transparent window that sits on top of the game window
    and displays visualizations of detection results such as:
    - Bounding boxes for template matches
    - Text areas for OCR results
    - Object detection results with labels
    
    The overlay automatically updates its position when the game window moves
    and can be toggled on/off.
    """
    
    def __init__(self, window_service: WindowServiceInterface, 
                detection_service: DetectionServiceInterface):
        """
        Initialize the overlay view.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
        """
        super().__init__()
        
        self.window_service = window_service
        self.detection_service = detection_service
        
        # Initialize state
        self._visible = False
        self._detection_results: List[Dict] = []
        self._highlight_color = QColor(0, 255, 0, 128)  # Semi-transparent green
        self._text_color = QColor(255, 255, 0)  # Yellow
        self._refresh_interval = 100  # ms
        
        # Configure overlay window
        self._setup_window()
        
        # Create refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_overlay)
        
        # Subscribe to detection events
        self._setup_event_listeners()
        
        logger.info("Overlay view initialized")
    
    def _setup_window(self) -> None:
        """Set up the overlay window properties."""
        # Set window flags to make this a tool window that stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )
        
        # Make the window background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Set initial size (will be updated based on game window)
        self.resize(800, 600)
    
    def _setup_event_listeners(self) -> None:
        """Set up event listeners for detection events."""
        # We'll use the detection service to get events
        if hasattr(self.detection_service, 'event_bus'):
            event_bus = self.detection_service.event_bus
            event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_detection_completed)
    
    def _on_detection_completed(self, event: Event) -> None:
        """
        Handle detection completed event.
        
        Args:
            event: Detection completed event with results
        """
        if event.type != EventType.DETECTION_COMPLETED:
            return
            
        # Extract detection results
        data = event.data or {}
        self._detection_results = data.get('results', [])
        
        # Update overlay if visible
        if self._visible:
            self.update()
    
    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        if self._visible:
            self.hide()
        else:
            self.show()
    
    def is_visible(self) -> bool:
        """
        Check if the overlay is currently visible.
        
        Returns:
            True if the overlay is visible, False otherwise
        """
        return self._visible
    
    def show(self) -> None:
        """Show the overlay window."""
        # Update position and size before showing
        self.update_position()
        
        # Show the window
        super().show()
        self._visible = True
        
        # Start refresh timer
        self._refresh_timer.start(self._refresh_interval)
        
        logger.info("Overlay shown")
    
    def hide(self) -> None:
        """Hide the overlay window."""
        # Stop refresh timer
        self._refresh_timer.stop()
        
        # Hide the window
        super().hide()
        self._visible = False
        
        logger.info("Overlay hidden")
    
    def update_position(self) -> None:
        """Update the overlay position to match the game window."""
        # Get game window position
        game_pos = self.window_service.get_window_position()
        if game_pos:
            x, y, width, height = game_pos
            self.setGeometry(x, y, width, height)
    
    def _update_overlay(self) -> None:
        """Update the overlay position and content."""
        if not self._visible:
            return
            
        # Update position
        self.update_position()
        
        # Request a redraw
        self.update()
    
    def paintEvent(self, event) -> None:
        """
        Handle paint event to draw detection visualizations.
        
        Args:
            event: Paint event
        """
        # Initialize painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw detection results
        self._draw_detection_results(painter)
        
        # Finish painting
        painter.end()
    
    def _draw_detection_results(self, painter: QPainter) -> None:
        """
        Draw detection results on the overlay.
        
        Args:
            painter: QPainter instance to use for drawing
        """
        if not self._detection_results:
            return
        
        # Set up pens and brushes for different result types
        template_pen = QPen(QColor(0, 255, 0))
        template_pen.setWidth(2)
        
        text_pen = QPen(QColor(255, 255, 0))
        text_pen.setWidth(2)
        
        object_pen = QPen(QColor(0, 0, 255))
        object_pen.setWidth(2)
        
        # Draw each detection result
        for result in self._detection_results:
            # Determine result type and draw appropriately
            if 'template_name' in result:
                # Template match
                self._draw_template_match(painter, result, template_pen)
            elif 'text' in result:
                # OCR result
                self._draw_ocr_result(painter, result, text_pen)
            elif 'class_name' in result or 'bbox' in result:
                # Object detection
                self._draw_object_detection(painter, result, object_pen)
    
    def _draw_template_match(self, painter: QPainter, result: Dict, pen: QPen) -> None:
        """
        Draw a template match result.
        
        Args:
            painter: QPainter instance to use for drawing
            result: Template match result data
            pen: Pen to use for drawing
        """
        # Extract position and size
        x = result.get('x', 0)
        y = result.get('y', 0)
        width = result.get('width', 0)
        height = result.get('height', 0)
        confidence = result.get('confidence', 0)
        template_name = result.get('template_name', 'unknown')
        
        # Draw bounding box
        painter.setPen(pen)
        painter.drawRect(x, y, width, height)
        
        # Draw template name and confidence
        painter.setFont(QFont('Arial', 10))
        text = f"{template_name} ({confidence:.2f})"
        painter.drawText(x, y - 5, text)
    
    def _draw_ocr_result(self, painter: QPainter, result: Dict, pen: QPen) -> None:
        """
        Draw an OCR result.
        
        Args:
            painter: QPainter instance to use for drawing
            result: OCR result data
            pen: Pen to use for drawing
        """
        # Extract position and size
        x = result.get('x', 0)
        y = result.get('y', 0)
        width = result.get('width', 0)
        height = result.get('height', 0)
        text = result.get('text', '')
        confidence = result.get('confidence', 0)
        
        # Draw bounding box
        painter.setPen(pen)
        painter.drawRect(x, y, width, height)
        
        # Draw background for text
        text_rect = QRect(x, y - 20, width, 20)
        painter.fillRect(text_rect, QBrush(QColor(0, 0, 0, 180)))
        
        # Draw text and confidence
        painter.setFont(QFont('Arial', 9))
        painter.setPen(Qt.GlobalColor.white)
        display_text = f"{text} ({confidence:.2f})"
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, display_text)
    
    def _draw_object_detection(self, painter: QPainter, result: Dict, pen: QPen) -> None:
        """
        Draw an object detection result.
        
        Args:
            painter: QPainter instance to use for drawing
            result: Object detection result data
            pen: Pen to use for drawing
        """
        # Extract position and size
        if 'bbox' in result:
            # YOLO format: [x, y, w, h]
            bbox = result.get('bbox', [0, 0, 0, 0])
            x, y, w, h = bbox
        else:
            # Standard format with x, y, width, height
            x = result.get('x', 0)
            y = result.get('y', 0)
            w = result.get('width', 0)
            h = result.get('height', 0)
        
        class_name = result.get('class_name', 'object')
        confidence = result.get('confidence', 0)
        
        # Draw bounding box
        painter.setPen(pen)
        painter.drawRect(int(x), int(y), int(w), int(h))
        
        # Draw class name and confidence
        label_bg_rect = QRect(int(x), int(y) - 20, int(w), 20)
        painter.fillRect(label_bg_rect, QBrush(QColor(0, 0, 128, 180)))
        
        painter.setFont(QFont('Arial', 9))
        painter.setPen(Qt.GlobalColor.white)
        label_text = f"{class_name} ({confidence:.2f})"
        painter.drawText(label_bg_rect, Qt.AlignmentFlag.AlignCenter, label_text)
    
    def set_highlight_color(self, color: QColor) -> None:
        """
        Set the color used for highlighting detections.
        
        Args:
            color: Color to use for highlights
        """
        self._highlight_color = color
        if self._visible:
            self.update()
    
    def set_text_color(self, color: QColor) -> None:
        """
        Set the color used for text in the overlay.
        
        Args:
            color: Color to use for text
        """
        self._text_color = color
        if self._visible:
            self.update()
    
    def set_refresh_interval(self, interval_ms: int) -> None:
        """
        Set the refresh interval for the overlay.
        
        Args:
            interval_ms: Refresh interval in milliseconds
        """
        self._refresh_interval = max(50, interval_ms)  # Minimum 50ms
        
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
            self._refresh_timer.start(self._refresh_interval)
    
    def clear_results(self) -> None:
        """Clear all detection results from the overlay."""
        self._detection_results = []
        if self._visible:
            self.update() 