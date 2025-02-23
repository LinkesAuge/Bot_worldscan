"""
Position Marker Overlay

This module provides a transparent overlay for marking and visualizing positions
in the game window. It allows users to:
- Click to mark new positions
- See existing marked positions
- Get visual feedback during position selection
"""

from typing import Optional, Tuple, Dict
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QPaintEvent
import logging
from scout.window_manager import WindowManager
from scout.automation.core import AutomationPosition

logger = logging.getLogger(__name__)

class PositionMarker(QWidget):
    """
    Transparent overlay for marking and displaying positions.
    
    This widget creates a transparent overlay that:
    - Shows marked positions with crosses
    - Allows clicking to mark new positions
    - Provides visual feedback during marking
    - Updates position coordinates relative to game window
    """
    
    # Signal emitted when a new position is marked
    position_marked = pyqtSignal(QPoint)
    
    def __init__(self, window_manager: WindowManager):
        """
        Initialize the position marker overlay.
        
        Args:
            window_manager: WindowManager instance for coordinate conversion
        """
        super().__init__()
        self.window_manager = window_manager
        
        # Configure window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Visual settings
        self.cross_size = 20
        self.cross_color = QColor(255, 165, 0)  # Orange
        self.cross_width = 2
        self.font_color = QColor(255, 255, 255)  # White
        self.font_size = 10
        
        # State
        self.marked_positions: Dict[str, AutomationPosition] = {}
        self.current_position: Optional[QPoint] = None
        self.is_marking = False
        
    def start_marking(self) -> None:
        """Enter position marking mode."""
        self.is_marking = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.update()
        
    def stop_marking(self) -> None:
        """Exit position marking mode."""
        self.is_marking = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.update()
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """
        Update the displayed positions.
        
        Args:
            positions: Dictionary of position name to AutomationPosition
        """
        self.marked_positions = positions
        self.update()
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events for position marking."""
        if self.is_marking and event.button() == Qt.MouseButton.LeftButton:
            try:
                # Convert screen coordinates to window-relative
                screen_pos = event.globalPosition().toPoint()
                window_x, window_y = self.window_manager.screen_to_client(
                    screen_pos.x(), screen_pos.y()
                )
                
                # Validate coordinates
                if window_x < 0 or window_y < 0:
                    logger.warning(f"Invalid position coordinates: ({window_x}, {window_y})")
                    return
                    
                self.current_position = QPoint(window_x, window_y)
                self.position_marked.emit(self.current_position)
                logger.debug(f"Position marked at window coordinates: ({window_x}, {window_y})")
                
            except Exception as e:
                logger.error(f"Error marking position: {e}")
            
    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the overlay with crosses and coordinates."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw existing positions
        for name, pos in self.marked_positions.items():
            screen_x, screen_y = self.window_manager.client_to_screen(pos.x, pos.y)
            self._draw_position(painter, screen_x, screen_y, name)
            
        # Draw current position if marking
        if self.is_marking and self.current_position:
            screen_x, screen_y = self.window_manager.client_to_screen(
                self.current_position.x(), self.current_position.y()
            )
            self._draw_position(painter, screen_x, screen_y, "Current")
            
    def _draw_position(self, painter: QPainter, x: int, y: int, label: str) -> None:
        """
        Draw a position marker with coordinates.
        
        Args:
            painter: QPainter instance
            x: Screen X coordinate
            y: Screen Y coordinate
            label: Label to display
        """
        # Draw cross
        pen = QPen(self.cross_color)
        pen.setWidth(self.cross_width)
        painter.setPen(pen)
        
        half_size = self.cross_size // 2
        # Horizontal line
        painter.drawLine(x - half_size, y, x + half_size, y)
        # Vertical line
        painter.drawLine(x, y - half_size, x, y + half_size)
        
        # Draw coordinates
        painter.setPen(QPen(self.font_color))
        window_x, window_y = self.window_manager.screen_to_client(x, y)
        coord_text = f"{label} ({window_x}, {window_y})"
        painter.drawText(x + half_size + 5, y, coord_text) 