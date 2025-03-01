"""
Search Grid Widget

This module provides a widget for visualizing the search grid and progress.
It shows:
- The grid pattern layout
- Current search position
- Search progress
- Already searched areas
"""

from typing import List, Tuple, Optional
import logging
import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QRect, QPoint

logger = logging.getLogger(__name__)

class SearchGridWidget(QWidget):
    """
    Widget for visualizing the search grid and progress.
    
    This widget provides a visual representation of:
    - The grid pattern layout
    - Current search position
    - Search progress
    - Already searched areas
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the search grid widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Grid settings
        self.grid_size = (10, 10)  # Width x Height in cells
        self.cell_padding = 2  # Pixels between cells
        
        # Search state
        self.current_position = (0, 0)  # Current position in grid coordinates
        self.searched_positions: List[Tuple[int, int]] = []  # List of searched positions
        self.search_in_progress = False
        
        # Colors
        self.grid_color = QColor(100, 100, 100)  # Gray
        self.cell_color = QColor(50, 50, 50)  # Dark gray
        self.searched_color = QColor(0, 100, 0)  # Dark green
        self.current_color = QColor(200, 0, 0)  # Red
        
        # Set minimum size
        self.setMinimumSize(300, 300)
    
    def set_grid_size(self, width: int, height: int) -> None:
        """
        Set the grid size.
        
        Args:
            width: Number of cells horizontally
            height: Number of cells vertically
        """
        self.grid_size = (width, height)
        self.update()
    
    def set_current_position(self, x: int, y: int) -> None:
        """
        Set the current search position.
        
        Args:
            x: Grid X coordinate
            y: Grid Y coordinate
        """
        self.current_position = (x, y)
        self.update()
    
    def add_searched_position(self, x: int, y: int) -> None:
        """
        Add a position to the list of searched positions.
        
        Args:
            x: Grid X coordinate
            y: Grid Y coordinate
        """
        if (x, y) not in self.searched_positions:
            self.searched_positions.append((x, y))
            self.update()
    
    def clear_searched_positions(self) -> None:
        """Clear the list of searched positions."""
        self.searched_positions.clear()
        self.update()
    
    def set_search_in_progress(self, in_progress: bool) -> None:
        """
        Set whether a search is in progress.
        
        Args:
            in_progress: Whether search is in progress
        """
        self.search_in_progress = in_progress
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate cell size
        width = self.width()
        height = self.height()
        cell_width = (width - (self.grid_size[0] + 1) * self.cell_padding) / self.grid_size[0]
        cell_height = (height - (self.grid_size[1] + 1) * self.cell_padding) / self.grid_size[1]
        
        # Draw grid
        for y in range(self.grid_size[1]):
            for x in range(self.grid_size[0]):
                # Calculate cell rectangle
                cell_x = x * (cell_width + self.cell_padding) + self.cell_padding
                cell_y = y * (cell_height + self.cell_padding) + self.cell_padding
                cell_rect = QRect(
                    int(cell_x),
                    int(cell_y),
                    int(cell_width),
                    int(cell_height)
                )
                
                # Determine cell color
                if (x, y) == self.current_position:
                    color = self.current_color
                elif (x, y) in self.searched_positions:
                    color = self.searched_color
                else:
                    color = self.cell_color
                
                # Draw cell
                painter.fillRect(cell_rect, color)
                painter.setPen(QPen(self.grid_color))
                painter.drawRect(cell_rect)
        
        # Draw search in progress indicator
        if self.search_in_progress:
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QBrush(QColor(255, 165, 0, 100)))  # Semi-transparent orange
            painter.drawRect(self.rect())
    
    def get_cell_at_pos(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        """
        Get the grid coordinates at a screen position.
        
        Args:
            pos: Screen position
            
        Returns:
            Optional tuple of (x, y) grid coordinates
        """
        # Calculate cell size
        width = self.width()
        height = self.height()
        cell_width = (width - (self.grid_size[0] + 1) * self.cell_padding) / self.grid_size[0]
        cell_height = (height - (self.grid_size[1] + 1) * self.cell_padding) / self.grid_size[1]
        
        # Calculate grid coordinates
        x = int((pos.x() - self.cell_padding) / (cell_width + self.cell_padding))
        y = int((pos.y() - self.cell_padding) / (cell_height + self.cell_padding))
        
        # Check if coordinates are valid
        if 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]:
            return (x, y)
        return None
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            cell = self.get_cell_at_pos(event.pos())
            if cell:
                self.set_current_position(*cell) 