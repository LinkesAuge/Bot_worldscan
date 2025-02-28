"""
Spinning Indicator Widget

This module provides a modern spinning indicator widget for showing loading/refresh states.
It creates a smooth, animated circular progress indicator similar to those seen in modern applications.
"""

from typing import Optional
from math import cos, sin
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
import logging

logger = logging.getLogger(__name__)

class SpinningIndicator(QWidget):
    """
    A modern spinning indicator widget that shows an animated loading state.
    
    This widget creates a smooth circular animation with fading dots, similar to
    modern loading indicators. It's highly customizable in terms of colors,
    size, and animation speed.
    
    Attributes:
        color (QColor): The base color of the spinning indicator
        num_dots (int): Number of dots in the circle
        dot_size (int): Size of each dot in pixels
        speed (int): Animation speed in milliseconds per frame
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the spinning indicator.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Customizable properties
        self.color = QColor(255, 0, 0)  # Changed to red to match template matching theme
        self.num_dots = 8  # Reduced number of dots for better visibility
        self.dot_size = 10  # Increased dot size
        self.speed = 80  # Animation speed (ms)
        
        # Animation state
        self.current_angle = 0
        self.is_spinning = False
        
        # Setup animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        
        # Set size policy and make it bigger
        self.setFixedSize(80, 80)  # Made even bigger
        
        # Make sure widget is visible and on top
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        logger.debug("SpinningIndicator initialized")
        
    def start(self) -> None:
        """Start the spinning animation."""
        if not self.is_spinning:
            self.is_spinning = True
            self.timer.start(self.speed)
            self.show()
            self.raise_()
            logger.debug("SpinningIndicator started")
            
    def stop(self) -> None:
        """Stop the spinning animation."""
        self.is_spinning = False
        self.timer.stop()
        self.current_angle = 0
        self.hide()
        self.update()
        logger.debug("SpinningIndicator stopped")
        
    def rotate(self) -> None:
        """Update the rotation angle and trigger a repaint."""
        self.current_angle = (self.current_angle + 30) % 360
        self.update()
        
    def paintEvent(self, event) -> None:
        """
        Paint the spinning indicator.
        
        Creates a circular arrangement of dots with varying opacity to create
        a smooth spinning effect.
        """
        if not self.is_spinning:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center and radius
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - self.dot_size
        
        # Draw background circle with light blue color
        painter.setPen(Qt.PenStyle.NoPen)
        bg_color = QColor(173, 216, 230, 25)  # Light blue with some transparency
        painter.setBrush(QBrush(bg_color))
        painter.drawEllipse(QRectF(0, 0, self.width(), self.height()))
        
        for i in range(self.num_dots):
            # Calculate dot position and opacity
            angle = i * (360 / self.num_dots) + self.current_angle
            opacity = 1.0 - (i / self.num_dots)
            
            # Set dot color with opacity
            dot_color = QColor(self.color)
            dot_color.setAlphaF(opacity)
            
            # Calculate dot position
            x = center_x + radius * cos(angle * 3.14159 / 180)
            y = center_y + radius * sin(angle * 3.14159 / 180)
            
            # Draw dot with glow effect
            # Draw outer glow
            glow_color = QColor(self.color)
            glow_color.setAlphaF(opacity * 0.3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(QRectF(x - self.dot_size*0.8,
                                     y - self.dot_size*0.8,
                                     self.dot_size*1.6,
                                     self.dot_size*1.6))
            
            # Draw main dot
            painter.setPen(QPen(QColor(0, 0, 0), 1))  # Black outline
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(QRectF(x - self.dot_size/2,
                                     y - self.dot_size/2,
                                     self.dot_size,
                                     self.dot_size))
            
    def showEvent(self, event) -> None:
        """Handle show event."""
        super().showEvent(event)
        self.raise_()  # Ensure we're on top
        logger.debug(f"SpinningIndicator shown at position: ({self.x()}, {self.y()})")
        
    def hideEvent(self, event) -> None:
        """Handle hide event."""
        super().hideEvent(event)
        logger.debug("SpinningIndicator hidden") 