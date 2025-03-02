"""
Game World Grid

This module provides a widget for visualizing the game world search areas.
It handles:
- Overlapping view rectangles representing screenshot areas
- Movement path visualization
- Status updates and zoom control
"""

from typing import Optional, Tuple, List, Dict, Set
import logging
from enum import Enum, auto
import math

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel, QHBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer, QRectF

from scout.game_world_position import GameWorldPosition

logger = logging.getLogger(__name__)

class ViewState(Enum):
    """Enum for tracking the state of each view rectangle."""
    EMPTY = auto()      # Default state
    CURRENT = auto()    # Current active view
    VISITED = auto()    # View has been visited
    MATCH = auto()      # View contains a match
    PATH = auto()       # View is part of the path

class Direction(Enum):
    """Enum for movement directions."""
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
    NORTHEAST = auto()
    NORTHWEST = auto()
    SOUTHEAST = auto()
    SOUTHWEST = auto()

class GameWorldGrid(QWidget):
    """
    Widget for visualizing the game world search areas.
    
    Instead of a grid, this widget displays overlapping rectangles that represent
    actual screenshot areas. Each rectangle shows the coordinates where the
    screenshot was taken, and rectangles can overlap to show the true nature
    of the search pattern.
    """
    
    # Signals
    status_updated = pyqtSignal(str)  # Signal for status updates
    
    # Game world constants
    WORLD_SIZE = 999  # Maximum coordinate value in game world
    
    # Modern color scheme with updated colors
    COLORS = {
        'background': QColor(230, 255, 230, 40),     # Very light pastel green background
        'current': QColor(135, 206, 235, 180),       # Light blue for current view
        'visited': QColor(230, 230, 250, 120),       # Light purple for visited
        'match': QColor(139, 0, 0, 150),            # Dark red for matches
        'path': QColor(224, 108, 117, 180),         # Soft red for path
        'text': QColor(40, 40, 40),                 # Dark gray for text
        'arrow': QColor(255, 255, 255, 180),        # White with transparency for arrows
        'message': QColor(100, 100, 100)            # Gray for messages
    }
    
    # View rectangle parameters
    VIEW_PADDING = 10  # Pixels of padding between view rectangles
    MIN_VIEW_SIZE = 150  # Minimum size for view rectangles in pixels
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game world visualization widget."""
        super().__init__(parent)
        
        # Game world state
        self.current_game_pos: Optional[GameWorldPosition] = None
        self.drag_distances = (0, 0)  # X, Y distance covered by one drag
        self.is_calibrated = False
        self.search_in_progress = False
        
        # View state
        self.current_view = None  # Current view position in game coordinates
        self.view_states: Dict[Tuple[int, int], ViewState] = {}  # Track state of each view
        self.view_positions: Dict[Tuple[int, int], GameWorldPosition] = {}  # Store positions
        self.match_counts: Dict[Tuple[int, int], int] = {}  # Track match counts
        self.path_sequence: List[Tuple[int, int]] = []  # Track order of path views
        self.path_directions: Dict[Tuple[Tuple[int, int], Tuple[int, int]], Direction] = {}
        self.last_movement_direction: Optional[Direction] = None
        
        # View control
        self.zoom_level = 0.8  # Start slightly zoomed out
        self.min_zoom = 0.2
        self.max_zoom = 2.0
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
        
        # Create a widget for the grid view
        self.grid_view = QWidget()
        layout.addWidget(self.grid_view, stretch=1)
        
        # Add zoom control at the bottom with horizontal layout
        zoom_layout = QHBoxLayout()
        
        # Create zoom value label
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setStyleSheet("color: #dcdfe4; min-width: 40px;")
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(int(self.min_zoom * 100))
        self.zoom_slider.setMaximum(int(self.max_zoom * 100))
        self.zoom_slider.setValue(int(self.zoom_level * 100))
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #90EE90;
                height: 8px;
                background: #2c313a;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #90EE90;
                border: 1px solid #90EE90;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        zoom_layout.addWidget(QLabel("Zoom:"))
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_value_label)
        
        layout.addLayout(zoom_layout)
        
        # Set minimum size
        self.setMinimumSize(800, 600)
        
    def update_grid_parameters(self, drag_distances: Tuple[float, float]) -> None:
        """Update view parameters based on drag distances."""
        if not all(drag_distances):
            logger.warning("Invalid drag distances")
            return
            
        self.drag_distances = drag_distances
        self.is_calibrated = True
        
        logger.info(f"Updated view parameters - Drag distances: {self.drag_distances}")
        
        # Update current view if we have a game position
        if self.current_game_pos:
            view_id = (self.current_game_pos.x // int(self.drag_distances[0]),
                      self.current_game_pos.y // int(self.drag_distances[1]))
            self.current_view = view_id
            self.view_positions[view_id] = self.current_game_pos
            self.view_states[view_id] = ViewState.CURRENT
            self._center_on_current_view()
            
        self.update()
        self._update_status()
        
    def set_grid_parameters(self, grid_size: Tuple[int, int], start_pos: GameWorldPosition,
                          drag_distances: Tuple[float, float], current_cell: Tuple[int, int]) -> None:
        """
        Set view parameters and initialize the state.
        
        Args:
            grid_size: Ignored (kept for compatibility)
            start_pos: Initial game world position
            drag_distances: Tuple of (x, y) distances for one drag movement
            current_cell: Initial current view position
        """
        self.current_game_pos = start_pos
        if start_pos and start_pos.is_valid():
            view_id = (start_pos.x // int(drag_distances[0]),
                      start_pos.y // int(drag_distances[1]))
            self.current_view = view_id
            self.view_positions[view_id] = start_pos
            self.view_states[view_id] = ViewState.CURRENT
            
        self.update_grid_parameters(drag_distances)
        # Ensure we center on the initial view
        self._center_on_current_view()

    def paintEvent(self, event) -> None:
        """Paint the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.COLORS['background'])
        
        if not self.is_calibrated:
            self._draw_uncalibrated_message(painter)
            return
            
        # Apply view transform
        painter.save()
        
        # Apply transformations in correct order
        painter.scale(self.zoom_level, self.zoom_level)  # Scale first
        painter.translate(-self.view_offset_x, -self.view_offset_y)  # Then translate
        
        # Draw all view rectangles in specific order
        drawn_positions = set()
        
        # Draw visited views first (with lowest opacity)
        for pos, state in self.view_states.items():
            if state == ViewState.VISITED and pos in self.view_positions:
                self._draw_view_rectangle(painter, pos, ViewState.VISITED, 0.7)
                drawn_positions.add(pos)
        
        # Draw path views next (with medium opacity)
        for pos in self.path_sequence:
            if pos not in drawn_positions and pos in self.view_positions:
                self._draw_view_rectangle(painter, pos, ViewState.PATH, 0.8)
                drawn_positions.add(pos)
        
        # Draw match views (with high opacity)
        for pos, state in self.view_states.items():
            if state == ViewState.MATCH and pos not in drawn_positions and pos in self.view_positions:
                self._draw_view_rectangle(painter, pos, ViewState.MATCH, 0.9)
                drawn_positions.add(pos)
        
        # Draw path connections
        if len(self.path_sequence) > 1:
            self._draw_path(painter)
        
        # Draw current view last (with full opacity)
        if self.current_view and self.current_view in self.view_positions:
            self._draw_view_rectangle(painter, self.current_view, ViewState.CURRENT, 1.0)
            
        painter.restore()
        
    def _draw_cell(self, painter: QPainter, x: int, y: int) -> None:
        """Draw a single cell with improved visuals."""
        # Calculate cell rectangle with padding
        rect_x = x * self.cell_width + self.CELL_PADDING
        rect_y = y * self.cell_height + self.CELL_PADDING
        rect_width = self.cell_width - 2 * self.CELL_PADDING
        rect_height = self.cell_height - 2 * self.CELL_PADDING
        
        # Create rounded rectangle path with floating point values
        path = QPainterPath()
        path.addRoundedRect(
            float(rect_x), float(rect_y),
            float(rect_width), float(rect_height),
            6.0, 6.0  # Slightly reduced corner radius
        )
        
        # Get cell state and apply appropriate color
        cell_state = self.cell_states.get((x, y), CellState.EMPTY)
        
        # Fill cell based on state with semi-transparent colors
        if cell_state == CellState.CURRENT or (x, y) == self.current_cell:
            painter.fillPath(path, self.COLORS['current'])
        elif cell_state == CellState.MATCH:
            painter.fillPath(path, self.COLORS['match'])
        elif cell_state == CellState.VISITED:
            painter.fillPath(path, self.COLORS['visited'])
            
        # Draw cell border with slightly thicker pen
        painter.setPen(QPen(self.COLORS['cell_border'], 2.5))
        painter.drawPath(path)
        
        # Create QRect for text drawing
        cell_rect = QRect(
            int(rect_x), int(rect_y),
            int(rect_width), int(rect_height)
        )
        
        # Draw cell content
        self._draw_cell_content(painter, cell_rect, x, y)

    def _draw_cell_content(self, painter: QPainter, rect: QRect, x: int, y: int) -> None:
        """Draw the content of a cell with improved formatting."""
        # Set up text drawing
        painter.setPen(QPen(self.COLORS['text']))
        
        # Calculate font size based on cell size (further reduced size)
        base_font_size = min(rect.width(), rect.height()) / 12  # Reduced from /8 to /12
        
        # Draw cell coordinates
        pos_font = QFont("Arial", int(base_font_size), QFont.Weight.Bold)
        painter.setFont(pos_font)
        pos_text = f"{x+1},{y+1}"  # Simplified text
        
        # Draw game coordinates if available
        if (x, y) in self.cell_game_positions:
            pos = self.cell_game_positions[(x, y)]
            # For visited cells, only show X,Y coordinates
            if self.cell_states.get((x, y)) == CellState.VISITED:
                coord_text = f"X:{pos.x}\nY:{pos.y}"
            else:
                coord_text = f"K:{pos.k}\nX:{pos.x}\nY:{pos.y}"
            
            # Draw both position and coordinates with smaller text
            text_rect = QRect(
                rect.x() + rect.width() // 6,  # Adjusted margins
                rect.y() + rect.height() // 3,  # Adjusted vertical position
                rect.width() * 2 // 3,  # Reduced width
                rect.height() * 1 // 2   # Reduced height
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{pos_text}\n{coord_text}")
        else:
            # Only draw position if no coordinates available
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, pos_text)

    def _draw_path(self, painter: QPainter) -> None:
        """Draw the path between views with direction arrows."""
        if len(self.path_sequence) < 2:
            return
            
        # Set up path drawing style
        path_pen = QPen(self.COLORS['path'], 
                       max(3, int(min(self.drag_distances) * self.zoom_level / 25)))
        path_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(path_pen)
        
        # Calculate base size and ratio
        base_size = 200.0
        ratio = self.drag_distances[1] / self.drag_distances[0]
        
        if ratio > 1:
            rect_height = base_size
            rect_width = base_size / ratio
        else:
            rect_width = base_size
            rect_height = base_size * ratio
        
        # Draw lines between consecutive path views
        for i in range(len(self.path_sequence) - 1):
            from_pos = self.path_sequence[i]
            to_pos = self.path_sequence[i + 1]
            
            # Calculate center points
            from_x = from_pos[0] * rect_width + rect_width / 2
            from_y = from_pos[1] * rect_height + rect_height / 2
            to_x = to_pos[0] * rect_width + rect_width / 2
            to_y = to_pos[1] * rect_height + rect_height / 2
            
            # Draw path line with glow effect
            for thickness in [5, 3, 1]:  # Create a glowing effect
                glow_pen = QPen(self.COLORS['path'])
                glow_pen.setWidth(thickness)
                painter.setPen(glow_pen)
                painter.drawLine(int(from_x), int(from_y), int(to_x), int(to_y))
            
            # Draw direction arrow
            direction = self._determine_direction(from_pos, to_pos)
            self._draw_direction_arrow(painter, (from_x, from_y), (to_x, to_y), direction)

    def _draw_uncalibrated_message(self, painter: QPainter) -> None:
        """Draw the uncalibrated message with improved styling."""
        painter.setPen(QPen(self.COLORS['message']))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        message = "Preview Grid - Calibration needed"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, message)
        
    def _center_on_current_view(self) -> None:
        """Center the visualization with bias towards movement direction."""
        if not self.current_view or not self.is_calibrated or not self.current_game_pos:
            return
            
        # Calculate base size and ratio
        base_size = 200.0
        ratio = self.drag_distances[1] / self.drag_distances[0]
        
        if ratio > 1:
            rect_height = base_size
            rect_width = base_size / ratio
        else:
            rect_width = base_size
            rect_height = base_size * ratio
            
        # Calculate the center of the current view in view space using game coordinates
        view_center_x = (self.current_game_pos.x * rect_width) / self.drag_distances[0]
        view_center_y = (self.current_game_pos.y * rect_height) / self.drag_distances[1]
        
        # Add half rectangle size to get to center
        view_center_x += rect_width / 2
        view_center_y += rect_height / 2
        
        # Calculate bias based on last movement direction
        bias_x = 0
        bias_y = 0
        if self.last_movement_direction:
            if self.last_movement_direction in [Direction.EAST, Direction.NORTHEAST, Direction.SOUTHEAST]:
                bias_x = rect_width * 0.5  # Bias half a view width
            elif self.last_movement_direction in [Direction.WEST, Direction.NORTHWEST, Direction.SOUTHWEST]:
                bias_x = -rect_width * 0.5
            if self.last_movement_direction in [Direction.SOUTH, Direction.SOUTHEAST, Direction.SOUTHWEST]:
                bias_y = rect_height * 0.5  # Bias half a view height
            elif self.last_movement_direction in [Direction.NORTH, Direction.NORTHEAST, Direction.NORTHWEST]:
                bias_y = -rect_height * 0.5
        
        # Calculate the target center point with bias
        target_x = view_center_x + bias_x
        target_y = view_center_y + bias_y
        
        # Calculate the widget center in view space
        widget_center_x = self.width() / (2 * self.zoom_level)
        widget_center_y = self.height() / (2 * self.zoom_level)
        
        # Set the view offset to center the target point
        self.view_offset_x = target_x - widget_center_x
        self.view_offset_y = target_y - widget_center_y
        
        # Ensure immediate update
        self.update()
        self._update_status()
        
    def _update_status(self) -> None:
        """Update and emit the current status."""
        if not self.is_calibrated:
            self.status_updated.emit("Not Calibrated")
            return
            
        status_parts = []
        
        # View size
        status_parts.append(f"View Size: {self.drag_distances[0]:.1f}x{self.drag_distances[1]:.1f} units")
        
        # Zoom level
        status_parts.append(f"Zoom: {self.zoom_level:.1f}x")
        
        # Current position
        if self.current_game_pos and self.current_game_pos.is_valid():
            status_parts.append(f"Position: X:{self.current_game_pos.x} Y:{self.current_game_pos.y}")
        
        # Join all parts with separator
        status = " | ".join(status_parts)
        self.status_updated.emit(status)
        
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider value changes."""
        self.zoom_level = value / 100.0
        self.zoom_value_label.setText(f"{self.zoom_level:.1f}x")
        self._center_on_current_view()
        self._update_status()
        
    def add_searched_view(self, position: GameWorldPosition) -> None:
        """Add a view to the searched list."""
        view_id = (position.x, position.y)
        
        if view_id not in self.view_states or self.view_states[view_id] != ViewState.MATCH:
            self.view_states[view_id] = ViewState.VISITED
            self.view_positions[view_id] = position
            self.update()
            
    def add_path_view(self, position: GameWorldPosition) -> None:
        """Add a view to the path sequence."""
        view_id = (position.x, position.y)
        
        # Add to path sequence if not already the last view
        if not self.path_sequence or self.path_sequence[-1] != view_id:
            if self.path_sequence:
                # Store the direction between the last view and this one
                from_view = self.path_sequence[-1]
                self.path_directions[(from_view, view_id)] = self._determine_direction(from_view, view_id)
                # Update last movement direction
                self.last_movement_direction = self.path_directions[(from_view, view_id)]
            
            self.path_sequence.append(view_id)
            self.view_states[view_id] = ViewState.PATH
            self.view_positions[view_id] = position
            self.update()
            
    def set_view_match(self, position: GameWorldPosition, count: int) -> None:
        """Set the match count for a view."""
        view_id = (position.x, position.y)
        
        self.view_states[view_id] = ViewState.MATCH
        self.match_counts[view_id] = count
        self.view_positions[view_id] = position
        self.update()
        
    def clear_search_data(self) -> None:
        """Clear all search-related data."""
        self.view_states.clear()
        self.match_counts.clear()
        self.path_sequence.clear()
        self.path_directions.clear()
        self.last_movement_direction = None
        # Keep current view state
        if self.current_view:
            self.view_states[self.current_view] = ViewState.CURRENT
        self.update()

    def set_search_in_progress(self, in_progress: bool) -> None:
        """Set whether a search is currently in progress."""
        self.search_in_progress = in_progress
        self._update_status()
        self.update()

    def _determine_direction(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> Direction:
        """Determine the direction of movement between two positions."""
        # Get actual game positions
        from_game_pos = self.view_positions[from_pos]
        to_game_pos = self.view_positions[to_pos]
        
        # Calculate direction based on actual coordinates
        dx = to_game_pos.x - from_game_pos.x
        dy = to_game_pos.y - from_game_pos.y
        
        if dx == 0:
            return Direction.SOUTH if dy > 0 else Direction.NORTH
        elif dy == 0:
            return Direction.EAST if dx > 0 else Direction.WEST
        elif dx > 0:
            return Direction.SOUTHEAST if dy > 0 else Direction.NORTHEAST
        else:
            return Direction.SOUTHWEST if dy > 0 else Direction.NORTHWEST

    def _draw_direction_arrow(self, painter: QPainter, from_pos: Tuple[float, float], 
                             to_pos: Tuple[float, float], direction: Direction) -> None:
        """Draw an arrow indicating movement direction."""
        # Set up arrow drawing style
        painter.setPen(QPen(self.COLORS['arrow'], 2))
        
        # Calculate arrow parameters
        arrow_size = min(self.cell_width, self.cell_height) / 6
        angle = math.atan2(to_pos[1] - from_pos[1], to_pos[0] - from_pos[0])
        
        # Calculate arrow head points
        arrow_head_1 = (
            to_pos[0] - arrow_size * math.cos(angle + math.pi/6),
            to_pos[1] - arrow_size * math.sin(angle + math.pi/6)
        )
        arrow_head_2 = (
            to_pos[0] - arrow_size * math.cos(angle - math.pi/6),
            to_pos[1] - arrow_size * math.sin(angle - math.pi/6)
        )
        
        # Draw arrow line and head
        painter.drawLine(int(from_pos[0]), int(from_pos[1]), int(to_pos[0]), int(to_pos[1]))
        painter.drawLine(int(to_pos[0]), int(to_pos[1]), int(arrow_head_1[0]), int(arrow_head_1[1]))
        painter.drawLine(int(to_pos[0]), int(to_pos[1]), int(arrow_head_2[0]), int(arrow_head_2[1]))

    def _draw_view_rectangle(self, painter: QPainter, pos: Tuple[int, int], 
                           state: ViewState, base_opacity: float = 1.0) -> None:
        """Draw a single view rectangle with potential overlap effects."""
        if pos not in self.view_positions:
            return
            
        # Get the actual game position for this view
        game_pos = self.view_positions[pos]
        
        # Calculate base size for view rectangles (200 pixels for larger dimension)
        base_size = 200.0
        ratio = self.drag_distances[1] / self.drag_distances[0]  # Y/X ratio
        
        if ratio > 1:
            # Taller than wide
            rect_height = base_size
            rect_width = base_size / ratio
        else:
            # Wider than tall or square
            rect_width = base_size
            rect_height = base_size * ratio
            
        # Calculate position based on actual game coordinates and drag distances
        screen_x = (game_pos.x * rect_width) / self.drag_distances[0]
        screen_y = (game_pos.y * rect_height) / self.drag_distances[1]
        
        # Create rectangle with padding
        rect = QRectF(
            screen_x + self.VIEW_PADDING,
            screen_y + self.VIEW_PADDING,
            rect_width - 2 * self.VIEW_PADDING,
            rect_height - 2 * self.VIEW_PADDING
        )
        
        # Determine color based on state
        if state == ViewState.CURRENT:
            color = self.COLORS['current']
        elif state == ViewState.MATCH:
            color = self.COLORS['match']
        elif state == ViewState.PATH:
            color = self.COLORS['path']
        else:  # ViewState.VISITED or ViewState.EMPTY
            color = self.COLORS['visited']
            
        # Adjust opacity for overlap effect
        color = QColor(color)  # Create a copy to modify
        color.setAlpha(int(color.alpha() * base_opacity))
        
        # Draw rectangle with rounded corners
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 2))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Draw game world coordinates
        self._draw_view_coordinates(painter, rect, game_pos)

    def _draw_view_coordinates(self, painter: QPainter, rect: QRectF, 
                             position: GameWorldPosition) -> None:
        """Draw game world coordinates in the view rectangle."""
        painter.setPen(QPen(self.COLORS['text']))
        font = QFont("Arial", int(min(rect.width(), rect.height()) / 12))
        painter.setFont(font)
        
        # Show the actual game world coordinates
        coord_text = f"X:{position.x}\nY:{position.y}"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, coord_text)

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
            
            # Create a unique identifier based on actual game coordinates
            view_id = (position.x, position.y)
            
            if view_id != self.current_view:
                # Update previous view state if it was current
                if self.current_view and self.current_view in self.view_states:
                    if self.view_states[self.current_view] == ViewState.CURRENT:
                        self.view_states[self.current_view] = ViewState.VISITED
                
                self.current_view = view_id
                self.view_states[view_id] = ViewState.CURRENT
                self.view_positions[view_id] = position
                self._center_on_current_view()
            else:
                # Update position even if view hasn't changed
                self.view_positions[view_id] = position
                self._update_status()
                self.update()
            
    def _on_coordinates_reset(self) -> None:
        """Handle coordinate reset from game state."""
        self.current_game_pos = None
        self.view_positions.clear()
        self.update()
        self.repaint() 