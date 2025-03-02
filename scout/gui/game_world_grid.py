"""
Game World Grid

This module provides a widget for visualizing the game world grid.
It handles:
- Grid based on screen-sized areas (one drag movement)
- Game world coordinate system (0-999 with wrapping)
- Visual representation of search progress
- Status updates and zoom control
"""

from typing import Optional, Tuple, List, Dict
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer

from scout.game_world_position import GameWorldPosition

logger = logging.getLogger(__name__)

class GameWorldGrid(QWidget):
    """
    Widget for visualizing the game world grid.
    
    Each cell represents one screen view (the area visible after one drag).
    The grid maps between:
    1. Game World (0-999, 0-999)
    2. Screen Views (based on drag distances)
    3. Widget Space (pixels)
    """
    
    # Signals
    status_updated = pyqtSignal(str)  # Signal for status updates
    
    # Game world constants
    WORLD_SIZE = 999  # Maximum coordinate value in game world
    
    # Colors
    GRID_COLOR = QColor(100, 100, 100)  # Grid lines
    BACKGROUND_COLOR = QColor(30, 30, 30)  # Dark background
    VISITED_COLOR = QColor(60, 100, 60, 150)  # Semi-transparent green for visited
    MATCH_COLOR = QColor(100, 150, 100, 150)  # Brighter green for matches
    CURRENT_COLOR = QColor(255, 215, 0, 150)  # Semi-transparent gold for current
    PATH_COLOR = QColor(200, 50, 50, 200)  # Semi-transparent red for path
    TEXT_COLOR = QColor(220, 220, 220)  # Light gray text
    MESSAGE_COLOR = QColor(128, 128, 128)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game world grid widget."""
        super().__init__(parent)
        
        # Game world state
        self.current_game_pos: Optional[GameWorldPosition] = None
        self.drag_distances = (0, 0)  # X, Y distance covered by one drag
        self.is_calibrated = False
        self.search_in_progress = False
        
        # Grid state
        self.grid_size = (0, 0)  # Number of screen views needed to cover world
        self.current_cell = (0, 0)  # Current screen view position
        self.searched_cells: List[Tuple[int, int]] = []
        self.path_cells: List[Tuple[int, int]] = []
        self.matches: Dict[Tuple[int, int], int] = {}
        self.cell_game_positions: Dict[Tuple[int, int], GameWorldPosition] = {}
        
        # View control
        self.zoom_level = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 4.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0
        
        # Setup UI
        self._setup_ui()
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        self.panning = False
        self.last_mouse_pos = None
        
        # Game state reference
        self.game_state = None
        
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add zoom control
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
        self.setMinimumSize(800, 600)
        
    def game_to_grid(self, game_x: int, game_y: int) -> Tuple[int, int]:
        """Convert game world coordinates to grid cell coordinates."""
        if not all(self.drag_distances):
            return (0, 0)
            
        # Calculate grid coordinates based on drag distances
        grid_x = int(game_x / self.drag_distances[0])
        grid_y = int(game_y / self.drag_distances[1])
        
        logger.debug(f"Converting game ({game_x}, {game_y}) to grid ({grid_x}, {grid_y})")
        return (grid_x, grid_y)
        
    def grid_to_game(self, grid_x: int, grid_y: int) -> Tuple[int, int]:
        """Convert grid cell coordinates to game world coordinates."""
        if not all(self.drag_distances):
            return (0, 0)
            
        # Calculate game coordinates based on drag distances
        game_x = int(grid_x * self.drag_distances[0])
        game_y = int(grid_y * self.drag_distances[1])
        
        # Wrap coordinates to game world bounds
        game_x = game_x % (self.WORLD_SIZE + 1)
        game_y = game_y % (self.WORLD_SIZE + 1)
        
        logger.debug(f"Converting grid ({grid_x}, {grid_y}) to game ({game_x}, {game_y})")
        return (game_x, game_y)
        
    def grid_to_screen(self, grid_x: float, grid_y: float) -> Tuple[float, float]:
        """Convert grid coordinates to screen coordinates."""
        screen_x = grid_x * self.cell_width
        screen_y = grid_y * self.cell_height
        return (screen_x, screen_y)
        
    def screen_to_grid(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to grid coordinates."""
        grid_x = screen_x / self.cell_width
        grid_y = screen_y / self.cell_height
        return (grid_x, grid_y)
        
    @property
    def cell_width(self) -> float:
        """Get the width of a grid cell in screen pixels."""
        if self.grid_size[0] == 0:
            return 0
        return self.width() / (self.grid_size[0] * self.zoom_level)
        
    @property
    def cell_height(self) -> float:
        """Get the height of a grid cell in screen pixels."""
        if self.grid_size[1] == 0:
            return 0
        return self.height() / (self.grid_size[1] * self.zoom_level)
        
    def set_game_state(self, game_state) -> None:
        """Set the game state and connect to its signals."""
        self.game_state = game_state
        if game_state:
            game_state.coordinates_updated.connect(self._on_coordinates_updated)
            game_state.coordinates_reset.connect(self._on_coordinates_reset)
            
    def _on_coordinates_updated(self, position: GameWorldPosition) -> None:
        """Handle coordinate updates from game state."""
        if position and position.is_valid():
            logger.debug(f"Received new game position: {position}")
            self.current_game_pos = position
            
            # Update current cell
            grid_x, grid_y = self.game_to_grid(position.x, position.y)
            if (grid_x, grid_y) != self.current_cell:
                self.current_cell = (grid_x, grid_y)
                self._center_on_current_cell()
                
            # Store game position for current cell
            self.cell_game_positions[self.current_cell] = position
            
            # Force update
            self.update()
            self.repaint()
            
    def _on_coordinates_reset(self) -> None:
        """Handle coordinate reset from game state."""
        self.current_game_pos = None
        self.cell_game_positions.clear()
        self.update()
        self.repaint()
        
    def update_grid_parameters(self, drag_distances: Tuple[float, float]) -> None:
        """Update grid parameters based on drag distances."""
        if not all(drag_distances):
            logger.warning("Invalid drag distances")
            return
            
        self.drag_distances = drag_distances
        
        # Calculate grid size based on screen views needed
        grid_width = (self.WORLD_SIZE + 1) // int(drag_distances[0])
        if (self.WORLD_SIZE + 1) % int(drag_distances[0]):
            grid_width += 1
            
        grid_height = (self.WORLD_SIZE + 1) // int(drag_distances[1])
        if (self.WORLD_SIZE + 1) % int(drag_distances[1]):
            grid_height += 1
            
        self.grid_size = (grid_width, grid_height)
        self.is_calibrated = True
        
        logger.info(f"Updated grid parameters - Size: {self.grid_size} screens, Drag distances: {self.drag_distances}")
        
        # Update current cell if we have a game position
        if self.current_game_pos:
            self.current_cell = self.game_to_grid(self.current_game_pos.x, self.current_game_pos.y)
            self._center_on_current_cell()
            
        self.update()
        self._update_status()
        
    def set_grid_parameters(self, grid_size: Tuple[int, int], start_pos: GameWorldPosition,
                          drag_distances: Tuple[float, float], current_cell: Tuple[int, int]) -> None:
        """
        Set grid parameters and initialize the grid state.
        
        Args:
            grid_size: Tuple of (width, height) for initial grid size
            start_pos: Initial game world position
            drag_distances: Tuple of (x, y) distances for one drag movement
            current_cell: Initial current cell position
        """
        self.current_game_pos = start_pos
        self.current_cell = current_cell
        self.update_grid_parameters(drag_distances)
        
    def paintEvent(self, event) -> None:
        """Paint the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.BACKGROUND_COLOR)
        
        if not self.is_calibrated:
            self._draw_uncalibrated_message(painter)
            return
            
        # Apply view transform
        painter.save()
        painter.scale(self.zoom_level, self.zoom_level)
        painter.translate(-self.view_offset_x * self.cell_width, -self.view_offset_y * self.cell_height)
        
        # Calculate visible range
        view_width = self.width() / (self.cell_width * self.zoom_level)
        view_height = self.height() / (self.cell_height * self.zoom_level)
        
        visible_left = int(self.view_offset_x - 1)
        visible_top = int(self.view_offset_y - 1)
        visible_right = int(self.view_offset_x + view_width + 2)
        visible_bottom = int(self.view_offset_y + view_height + 2)
        
        # Clamp to grid bounds
        visible_left = max(0, visible_left)
        visible_top = max(0, visible_top)
        visible_right = min(self.grid_size[0], visible_right)
        visible_bottom = min(self.grid_size[1], visible_bottom)
        
        # Draw cells
        cells_drawn = 0
        for y in range(visible_top, visible_bottom):
            for x in range(visible_left, visible_right):
                cells_drawn += 1
                cell_rect = QRect(
                    int(x * self.cell_width),
                    int(y * self.cell_height),
                    int(self.cell_width + 1),
                    int(self.cell_height + 1)
                )
                
                # Fill cell based on state
                if (x, y) == self.current_cell:
                    painter.fillRect(cell_rect, self.CURRENT_COLOR)
                elif (x, y) in self.matches:
                    painter.fillRect(cell_rect, self.MATCH_COLOR)
                elif (x, y) in self.searched_cells:
                    painter.fillRect(cell_rect, self.VISITED_COLOR)
                    
                # Draw grid lines with thicker borders
                painter.setPen(QPen(self.GRID_COLOR, 2))
                painter.drawRect(cell_rect)
                
                # Draw cell info with better formatting
                game_x, game_y = self.grid_to_game(x, y)
                cell_text = f"Screen {x+1},{y+1}"
                
                if (x, y) in self.cell_game_positions:
                    pos = self.cell_game_positions[(x, y)]
                    cell_text += f"\nK:{pos.k} X:{pos.x} Y:{pos.y}"
                    
                # Draw text with better visibility
                painter.setPen(QPen(self.TEXT_COLOR))
                font_size = min(self.cell_width, self.cell_height) / 10
                painter.setFont(QFont("Arial", int(font_size), QFont.Weight.Bold))
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, cell_text)
                
        # Draw path with thicker lines
        if len(self.path_cells) > 1:
            painter.setPen(QPen(self.PATH_COLOR, max(3, int(min(self.cell_width, self.cell_height) / 15))))
            for i in range(len(self.path_cells) - 1):
                x1, y1 = self.path_cells[i]
                x2, y2 = self.path_cells[i + 1]
                start_x, start_y = self.grid_to_screen(x1 + 0.5, y1 + 0.5)
                end_x, end_y = self.grid_to_screen(x2 + 0.5, y2 + 0.5)
                painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
                
        painter.restore()
        
    def _draw_uncalibrated_message(self, painter: QPainter) -> None:
        """Draw the uncalibrated message."""
        painter.setPen(QPen(self.MESSAGE_COLOR))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        message = "Preview Grid - Calibration needed"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, message)
        
    def _center_on_current_cell(self) -> None:
        """Center the view on the current cell."""
        if not self.current_cell:
            return
            
        # Calculate view dimensions in grid units
        view_width = self.width() / (self.cell_width * self.zoom_level)
        view_height = self.height() / (self.cell_height * self.zoom_level)
        
        # Center on current cell
        self.view_offset_x = max(0, min(
            self.grid_size[0] - view_width,
            self.current_cell[0] - view_width / 2
        ))
        self.view_offset_y = max(0, min(
            self.grid_size[1] - view_height,
            self.current_cell[1] - view_height / 2
        ))
        
        logger.debug(f"Centered view on cell {self.current_cell} - Offset: ({self.view_offset_x:.2f}, {self.view_offset_y:.2f})")
        
        self.update()
        
    def _update_status(self) -> None:
        """Update and emit the current status."""
        status = f"Grid Size: {self.grid_size[0]}x{self.grid_size[1]} screens | "
        status += f"Zoom: {self.zoom_level:.1f}x | "
        if self.is_calibrated:
            status += f"Screen Size: E:{self.drag_distances[0]:.1f}, S:{self.drag_distances[1]:.1f} units | "
            if self.current_cell:
                status += f"Current Screen: ({self.current_cell[0]+1}, {self.current_cell[1]+1}) | "
            if self.current_game_pos:
                status += f"Game Pos: K:{self.current_game_pos.k} X:{self.current_game_pos.x} Y:{self.current_game_pos.y}"
        else:
            status += "Not Calibrated"
            
        self.status_updated.emit(status)
        
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider value changes."""
        self.zoom_level = value / 100.0
        self._center_on_current_cell()
        self._update_status()
        
    def add_searched_cell(self, x: int, y: int) -> None:
        """Add a cell to the searched list."""
        if (x, y) not in self.searched_cells:
            self.searched_cells.append((x, y))
            self.update()
            
    def add_path_cell(self, x: int, y: int) -> None:
        """Add a cell to the path."""
        if (x, y) not in self.path_cells:
            self.path_cells.append((x, y))
            self.update()
            
    def set_cell_match(self, x: int, y: int, count: int) -> None:
        """Set the match count for a cell."""
        self.matches[(x, y)] = count
        self.update()
        
    def clear_search_data(self) -> None:
        """Clear all search-related data."""
        self.searched_cells.clear()
        self.path_cells.clear()
        self.matches.clear()
        self.update()

    def set_search_in_progress(self, in_progress: bool) -> None:
        """Set whether a search is currently in progress."""
        self.search_in_progress = in_progress
        self._update_status()
        self.update() 