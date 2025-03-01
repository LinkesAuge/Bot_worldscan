"""
Game World Grid

This module provides a widget for visualizing and managing the game world grid.
It handles:
- Grid based on actual drag movements
- Game world coordinate system (0-999 with wrapping)
- Visual representation of both screen and game coordinates
- Status updates and zoom control
"""

from typing import Optional, Tuple, List, Dict
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal

from scout.game_world_position import GameWorldPosition

logger = logging.getLogger(__name__)

class GameWorldGrid(QWidget):
    """
    Widget for visualizing the game world grid.
    
    The grid is based on actual drag movements and shows both:
    - Screen space grid (based on drag movements)
    - Game world coordinates (0-999 with wrapping)
    - Search progress with path tracking
    - Match information per cell
    - Zoom control for detailed view
    """
    
    # Signals
    status_updated = pyqtSignal(str)  # Signal for status updates
    
    # Game world constants
    WORLD_SIZE = 999  # Maximum coordinate value in game world
    
    # Colors
    GRID_COLOR = QColor(100, 100, 100)  # Darker grid lines
    BACKGROUND_COLOR = QColor(240, 240, 240)  # Light gray background
    VISITED_COLOR = QColor(255, 200, 200, 150)  # Semi-transparent light red
    MATCH_COLOR = QColor(150, 255, 150, 150)  # Semi-transparent light green
    CURRENT_COLOR = QColor(255, 255, 0, 150)  # Semi-transparent yellow
    PATH_COLOR = QColor(255, 0, 0, 200)  # Semi-transparent red
    TEXT_COLOR = QColor(0, 0, 0)  # Black text
    MESSAGE_COLOR = QColor(128, 128, 128)  # Gray for messages
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game world grid widget."""
        super().__init__(parent)
        
        # Grid state
        self.grid_size = (5, 5)  # Width x Height in drag movements
        self.current_position = (0, 0)  # Current position in grid coordinates
        self.searched_positions: List[Tuple[int, int]] = []  # List of searched positions
        self.search_in_progress = False
        
        # Search path tracking
        self.path_points: List[Tuple[int, int]] = []  # List of grid positions in search path
        
        # Match tracking
        self.matches_per_cell: Dict[Tuple[int, int], int] = {}  # Number of matches per cell
        self.cell_coordinates: Dict[Tuple[int, int], GameWorldPosition] = {}  # Coordinates per cell
        
        # Game world state
        self.start_game_pos: Optional[GameWorldPosition] = None  # Starting game world position
        self.drag_distances = (0, 0)  # X, Y distance covered by one drag
        self.is_calibrated = False  # Whether valid calibration exists
        
        # View ratio (width:height = 2:1)
        self.view_ratio = 2.0
        
        # Zoom control
        self.zoom_level = 1.0  # Default zoom level
        self.min_zoom = 0.5
        self.max_zoom = 4.0
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add zoom slider
        zoom_layout = QVBoxLayout()
        zoom_label = QLabel("Zoom Level:")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(int(self.min_zoom * 100))
        self.zoom_slider.setMaximum(int(self.max_zoom * 100))
        self.zoom_slider.setValue(int(self.zoom_level * 100))
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        layout.addLayout(zoom_layout)
        
        # Set minimum size
        self.setMinimumSize(400, 200)  # Maintain 2:1 ratio
        
        # Initialize status
        self._update_status()
        
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider value changes."""
        self.zoom_level = value / 100.0
        self.update()
        self._update_status()
        
    def _update_status(self) -> None:
        """Update and emit the current status."""
        status = f"Grid Size: {self.grid_size[0]}x{self.grid_size[1]} | "
        status += f"Zoom: {self.zoom_level:.1f}x | "
        if self.is_calibrated:
            status += f"Drag Distances: E:{self.drag_distances[0]:.1f}, S:{self.drag_distances[1]:.1f} | "
            if self.current_position:
                status += f"Current Cell: ({self.current_position[0]}, {self.current_position[1]}) | "
            if self.start_game_pos:
                status += f"Start: K:{self.start_game_pos.k} X:{self.start_game_pos.x} Y:{self.start_game_pos.y}"
        else:
            status += "Not Calibrated"
            
        self.status_updated.emit(status)
        
    def set_grid_parameters(
        self,
        grid_size: Tuple[int, int],
        start_pos: GameWorldPosition,
        drag_distances: Tuple[float, float],
        current_cell: Optional[Tuple[int, int]] = None
    ) -> None:
        """Set the grid parameters."""
        self.grid_size = grid_size
        self.start_game_pos = start_pos
        self.drag_distances = drag_distances
        self.is_calibrated = all(drag_distances) and start_pos is not None
        
        # Update current position if provided
        if current_cell is not None:
            self.current_position = current_cell
            
        self._update_status()
        self.update()
        
    def paintEvent(self, event) -> None:
        """Paint the widget with zoom support."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.BACKGROUND_COLOR)
        
        # Calculate cell size based on grid dimensions and zoom level
        width = self.width() * self.zoom_level
        height = self.height() * self.zoom_level
        cell_width = width / self.grid_size[0]
        cell_height = height / self.grid_size[1]
        
        # Calculate offset to center the zoomed view
        offset_x = (self.width() - width) / 2
        offset_y = (self.height() - height) / 2
        
        # Save current transform
        painter.save()
        
        # Apply zoom transform
        painter.translate(offset_x, offset_y)
        painter.scale(self.zoom_level, self.zoom_level)
        
        # Draw grid cells
        for y in range(self.grid_size[1]):
            for x in range(self.grid_size[0]):
                # Calculate cell rectangle
                cell_rect = QRect(
                    int(x * cell_width / self.zoom_level),
                    int(y * cell_height / self.zoom_level),
                    int(cell_width / self.zoom_level),
                    int(cell_height / self.zoom_level)
                )
                
                # Fill cell based on state (only if calibrated)
                if self.is_calibrated:
                    if (x, y) == self.current_position:
                        painter.fillRect(cell_rect, self.CURRENT_COLOR)
                    elif (x, y) in self.matches_per_cell:
                        painter.fillRect(cell_rect, self.MATCH_COLOR)
                    elif (x, y) in self.searched_positions:
                        painter.fillRect(cell_rect, self.VISITED_COLOR)
                
                # Draw grid lines
                painter.setPen(QPen(self.GRID_COLOR))
                painter.drawRect(cell_rect)
                
                # Draw grid coordinates in bottom right of each cell
                grid_text = f"[{x},{y}]"
                painter.setPen(QPen(self.GRID_COLOR))
                font_size = min(cell_width, cell_height) / (10 * self.zoom_level)
                painter.setFont(QFont("Arial", int(font_size)))
                grid_rect = QRect(
                    int(cell_rect.x() + cell_rect.width() * 0.6),
                    int(cell_rect.y() + cell_rect.height() * 0.8),
                    int(cell_rect.width() * 0.4),
                    int(cell_rect.height() * 0.2)
                )
                painter.drawText(grid_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, grid_text)
                
                # Draw coordinates and match count if available and calibrated
                if self.is_calibrated and (x, y) in self.cell_coordinates:
                    coords = self.cell_coordinates[(x, y)]
                    matches = self.matches_per_cell.get((x, y), 0)
                    
                    painter.setPen(QPen(self.TEXT_COLOR))
                    
                    # Calculate font size based on cell size and zoom
                    font_size = min(cell_width, cell_height) / (8 * self.zoom_level)
                    painter.setFont(QFont("Arial", int(font_size)))
                    
                    # Draw coordinates on first line
                    coord_text = f"({coords.x}, {coords.y})"
                    coord_rect = QRect(
                        cell_rect.x(),
                        cell_rect.y(),
                        cell_rect.width(),
                        cell_rect.height() // 2
                    )
                    painter.drawText(coord_rect, Qt.AlignmentFlag.AlignCenter, coord_text)
                    
                    # Draw match count on second line if there are matches
                    if matches > 0:
                        match_text = f"Matches: {matches}"
                        match_rect = QRect(
                            cell_rect.x(),
                            cell_rect.y() + cell_rect.height() // 2,
                            cell_rect.width(),
                            cell_rect.height() // 2
                        )
                        painter.drawText(match_rect, Qt.AlignmentFlag.AlignCenter, match_text)
        
        # Draw search path if calibrated
        if self.is_calibrated and len(self.path_points) > 1:
            painter.setPen(QPen(self.PATH_COLOR, max(2, int(min(cell_width, cell_height) / (20 * self.zoom_level)))))
            for i in range(len(self.path_points) - 1):
                x1, y1 = self.path_points[i]
                x2, y2 = self.path_points[i + 1]
                
                # Calculate center points of cells
                start_x = int((x1 + 0.5) * cell_width / self.zoom_level)
                start_y = int((y1 + 0.5) * cell_height / self.zoom_level)
                end_x = int((x2 + 0.5) * cell_width / self.zoom_level)
                end_y = int((y2 + 0.5) * cell_height / self.zoom_level)
                
                painter.drawLine(start_x, start_y, end_x, end_y)
        
        # Restore transform
        painter.restore()
        
        # Draw legend (not affected by zoom)
        self._draw_legend(painter)
        
        # Draw calibration needed message if not calibrated
        if not self.is_calibrated:
            painter.setPen(QPen(self.MESSAGE_COLOR))
            font = QFont("Arial", 12)
            painter.setFont(font)
            message = "Preview Grid - Calibration needed for full functionality"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, message)
        
    def set_current_position(self, x: int, y: int) -> None:
        """Set the current search position in grid coordinates."""
        self.current_position = (x, y)
        self._update_status()
        self.update()
        
    def add_searched_position(self, x: int, y: int) -> None:
        """Add a position to the list of searched positions."""
        if (x, y) not in self.searched_positions:
            self.searched_positions.append((x, y))
            self._update_status()
            self.update()
            
    def clear_searched_positions(self) -> None:
        """Clear the list of searched positions."""
        self.searched_positions.clear()
        self._update_status()
        self.update()
        
    def set_search_in_progress(self, in_progress: bool) -> None:
        """Set whether a search is in progress."""
        self.search_in_progress = in_progress
        self._update_status()
        self.update()
        
    def add_path_point(self, x: int, y: int) -> None:
        """Add a point to the search path."""
        if (x, y) not in self.path_points:
            self.path_points.append((x, y))
            self._update_status()
            self.update()
            
    def set_cell_matches(self, x: int, y: int, num_matches: int, coords: GameWorldPosition) -> None:
        """Set the number of matches and coordinates for a cell."""
        self.matches_per_cell[(x, y)] = num_matches
        self.cell_coordinates[(x, y)] = coords
        self._update_status()
        self.update()
        
    def clear_search_data(self) -> None:
        """Clear all search-related data."""
        self.searched_positions.clear()
        self.path_points.clear()
        self.matches_per_cell.clear()
        self.cell_coordinates.clear()
        self._update_status()
        self.update()
        
    def _draw_legend(self, painter: QPainter) -> None:
        """Draw a legend explaining the colors and symbols."""
        legend_items = [
            (self.CURRENT_COLOR, "Current Position"),
            (self.VISITED_COLOR, "Searched"),
            (self.MATCH_COLOR, "Match Found"),
            (self.PATH_COLOR, "Search Path")
        ]
        
        # Calculate legend position and size
        padding = 10
        item_height = 20
        total_height = len(legend_items) * item_height + 2 * padding
        legend_width = 150
        
        legend_rect = QRect(
            self.width() - legend_width - padding,
            padding,
            legend_width,
            total_height
        )
        
        # Draw legend background
        painter.fillRect(legend_rect, QColor(255, 255, 255, 200))
        painter.setPen(QPen(self.GRID_COLOR))
        painter.drawRect(legend_rect)
        
        # Draw legend items
        painter.setFont(QFont("Arial", 8))
        for i, (color, text) in enumerate(legend_items):
            # Draw color box
            box_rect = QRect(
                legend_rect.x() + padding,
                legend_rect.y() + padding + i * item_height,
                item_height,
                item_height
            )
            painter.fillRect(box_rect, color)
            painter.setPen(QPen(self.GRID_COLOR))
            painter.drawRect(box_rect)
            
            # Draw text
            text_rect = QRect(
                box_rect.right() + padding,
                box_rect.y(),
                legend_rect.width() - box_rect.width() - 3 * padding,
                item_height
            )
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, text)
        
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