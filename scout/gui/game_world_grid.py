"""
Game World Grid

This module provides a widget for visualizing and managing the game world grid.
It handles:
- Grid based on actual drag movements
- Game world coordinate system (0-999 with wrapping)
- Visual representation of both screen and game coordinates
"""

from typing import Optional, Tuple, List
import logging

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect, QPoint, QSize

from scout.game_world_position import GameWorldPosition

logger = logging.getLogger(__name__)

class GameWorldGrid(QWidget):
    """
    Widget for visualizing the game world grid.
    
    The grid is based on actual drag movements and shows both:
    - Screen space grid (based on drag movements)
    - Game world coordinates (0-999 with wrapping)
    """
    
    # Game world constants
    WORLD_SIZE = 999  # Maximum coordinate value in game world
    
    # Colors
    GRID_COLOR = QColor(100, 100, 100)  # Gray
    CELL_COLOR = QColor(50, 50, 50)  # Dark gray
    SEARCHED_COLOR = QColor(0, 100, 0)  # Dark green
    CURRENT_COLOR = QColor(200, 0, 0)  # Red
    COORD_COLOR = QColor(255, 255, 0)  # Yellow
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game world grid widget."""
        super().__init__(parent)
        
        # Grid state
        self.grid_size = (5, 5)  # Width x Height in drag movements
        self.current_position = (0, 0)  # Current position in grid coordinates
        self.searched_positions: List[Tuple[int, int]] = []  # List of searched positions
        self.search_in_progress = False
        
        # Game world state
        self.start_game_pos: Optional[GameWorldPosition] = None  # Starting game world position
        self.drag_distances = (0, 0)  # X, Y distance covered by one drag
        
        # Set minimum size
        self.setMinimumSize(400, 400)
        
    def set_grid_parameters(
        self,
        grid_size: Tuple[int, int],
        start_pos: GameWorldPosition,
        drag_distances: Tuple[int, int]
    ) -> None:
        """
        Set the grid parameters.
        
        Args:
            grid_size: (width, height) in drag movements
            start_pos: Starting game world position
            drag_distances: (x, y) distance covered by one drag in game units
        """
        self.grid_size = grid_size
        self.start_game_pos = start_pos
        self.drag_distances = drag_distances
        self.update()
        
    def set_current_position(self, x: int, y: int) -> None:
        """Set the current search position in grid coordinates."""
        self.current_position = (x, y)
        self.update()
        
    def add_searched_position(self, x: int, y: int) -> None:
        """Add a position to the list of searched positions."""
        if (x, y) not in self.searched_positions:
            self.searched_positions.append((x, y))
            self.update()
            
    def clear_searched_positions(self) -> None:
        """Clear the list of searched positions."""
        self.searched_positions.clear()
        self.update()
        
    def set_search_in_progress(self, in_progress: bool) -> None:
        """Set whether a search is in progress."""
        self.search_in_progress = in_progress
        self.update()
        
    def get_game_position(self, grid_x: int, grid_y: int) -> Optional[GameWorldPosition]:
        """
        Get the game world position for a grid position.
        
        Args:
            grid_x: X position in grid coordinates
            grid_y: Y position in grid coordinates
            
        Returns:
            GameWorldPosition or None if no start position set
        """
        if not self.start_game_pos:
            return None
            
        # Calculate offset from start position
        x_offset = grid_x * self.drag_distances[0]
        y_offset = grid_y * self.drag_distances[1]
        
        # Calculate new position with wrapping
        new_x = (self.start_game_pos.x + x_offset) % (self.WORLD_SIZE + 1)
        new_y = (self.start_game_pos.y + y_offset) % (self.WORLD_SIZE + 1)
        
        return GameWorldPosition(
            k=self.start_game_pos.k,
            x=new_x,
            y=new_y
        )
        
    def paintEvent(self, event) -> None:
        """Paint the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate cell size
        width = self.width()
        height = self.height()
        cell_width = width / self.grid_size[0]
        cell_height = height / self.grid_size[1]
        
        # Draw grid
        for y in range(self.grid_size[1]):
            for x in range(self.grid_size[0]):
                # Calculate cell rectangle
                cell_rect = QRect(
                    int(x * cell_width),
                    int(y * cell_height),
                    int(cell_width),
                    int(cell_height)
                )
                
                # Determine cell color
                if (x, y) == self.current_position:
                    color = self.CURRENT_COLOR
                elif (x, y) in self.searched_positions:
                    color = self.SEARCHED_COLOR
                else:
                    color = self.CELL_COLOR
                    
                # Draw cell
                painter.fillRect(cell_rect, color)
                painter.setPen(QPen(self.GRID_COLOR))
                painter.drawRect(cell_rect)
                
                # Draw game world coordinates if available
                game_pos = self.get_game_position(x, y)
                if game_pos:
                    painter.setPen(QPen(self.COORD_COLOR))
                    painter.setFont(QFont("Arial", 8))
                    coord_text = f"({game_pos.x}, {game_pos.y})"
                    painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, coord_text)
        
        # Draw search in progress indicator
        if self.search_in_progress:
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QBrush(QColor(255, 165, 0, 100)))  # Semi-transparent orange
            painter.drawRect(self.rect())
            
    def get_cell_at_pos(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        """Get the grid coordinates at a screen position."""
        # Calculate cell size
        width = self.width()
        height = self.height()
        cell_width = width / self.grid_size[0]
        cell_height = height / self.grid_size[1]
        
        # Calculate grid coordinates
        x = int(pos.x() / cell_width)
        y = int(pos.y() / cell_height)
        
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