"""
Game State Visualization Widget

This module provides a widget for visualizing game state information,
including resources, map entities, buildings, and army units.
It offers multiple visualization modes to understand the game state
at a glance.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime, timedelta
import cv2
from collections import defaultdict
from pathlib import Path
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QSplitter,
    QHeaderView, QComboBox, QMessageBox, QGroupBox, QRadioButton,
    QButtonGroup, QSlider, QTabWidget, QGridLayout, QTreeWidget,
    QTreeWidgetItem, QProgressBar, QStackedWidget, QToolBar
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont,
    QMouseEvent, QResizeEvent, QPaintEvent, QAction, QIcon,
    QPolygon, QTransform, QPainterPath
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRect, QSize, QPoint, QTimer, QRectF, QPointF
)

from scout.core.game.game_service_interface import GameServiceInterface

# Set up logging
logger = logging.getLogger(__name__)

class ResourcesView(QWidget):
    """
    Widget for visualizing game resources.
    
    Displays resource levels, production rates, and trends
    with graphical indicators.
    """
    
    def __init__(self, game_state_service: GameServiceInterface):
        """
        Initialize the resources view.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        self.game_state_service = game_state_service
        
        # Initialize state
        self._resources = {}
        self._resource_history = defaultdict(list)
        self._timestamps = []
        
        # Create UI layout
        self._create_ui()
        
        # Start update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_resources)
        self._update_timer.start(5000)  # Update every 5 seconds
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create resource grid
        self.resources_group = QGroupBox("Resources")
        resources_layout = QGridLayout(self.resources_group)
        
        # Headers
        resources_layout.addWidget(QLabel("Resource"), 0, 0)
        resources_layout.addWidget(QLabel("Amount"), 0, 1)
        resources_layout.addWidget(QLabel("Production"), 0, 2)
        resources_layout.addWidget(QLabel("Trend"), 0, 3)
        
        # Set up grid for standard resources
        self.resource_labels = {}
        self.production_labels = {}
        self.trend_indicators = {}
        
        standard_resources = ["Gold", "Food", "Wood", "Stone", "Iron"]
        
        for i, resource_name in enumerate(standard_resources):
            # Resource name
            resources_layout.addWidget(QLabel(resource_name), i + 1, 0)
            
            # Resource amount
            amount_label = QLabel("0")
            amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            resources_layout.addWidget(amount_label, i + 1, 1)
            self.resource_labels[resource_name.lower()] = amount_label
            
            # Production rate
            production_label = QLabel("0/h")
            production_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            resources_layout.addWidget(production_label, i + 1, 2)
            self.production_labels[resource_name.lower()] = production_label
            
            # Trend indicator (will be a custom widget)
            trend_indicator = QLabel("↑")
            trend_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            resources_layout.addWidget(trend_indicator, i + 1, 3)
            self.trend_indicators[resource_name.lower()] = trend_indicator
        
        main_layout.addWidget(self.resources_group)
        
        # Add resource history graph
        history_group = QGroupBox("Resource History")
        history_layout = QVBoxLayout(history_group)
        
        # Set up matplotlib for resource history graph
        import matplotlib
        matplotlib.use('Qt5Agg')  # Use Qt5Agg backend for PyQt6 compatibility
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        
        # Create figure and canvas
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(200)
        
        # Create axes for plotting
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title('Resource History')
        self.axes.set_xlabel('Time')
        self.axes.set_ylabel('Amount')
        
        # Add chart to layout
        history_layout.addWidget(self.canvas)
        
        # Add control panel for the chart
        control_layout = QHBoxLayout()
        
        # Resource selection for chart
        self.chart_resource_combo = QComboBox()
        self.chart_resource_combo.addItems(standard_resources)
        self.chart_resource_combo.currentIndexChanged.connect(self._update_chart)
        control_layout.addWidget(QLabel("Resource:"))
        control_layout.addWidget(self.chart_resource_combo)
        
        # Time range for chart
        self.chart_timerange_combo = QComboBox()
        self.chart_timerange_combo.addItems(["Last 10 minutes", "Last hour", "Last day", "All"])
        self.chart_timerange_combo.currentIndexChanged.connect(self._update_chart)
        control_layout.addWidget(QLabel("Time Range:"))
        control_layout.addWidget(self.chart_timerange_combo)
        
        history_layout.addLayout(control_layout)
        main_layout.addWidget(history_group)
        
        # Add stretcher to keep widgets at top
        main_layout.addStretch()
    
    def _update_resources(self) -> None:
        """Update resource data from the game state service."""
        try:
            # Get current game state
            game_state = self.game_state_service.get_game_state()
            if not game_state:
                return
            
            # Get resources
            resources = game_state.get('resources', {})
            
            # Store timestamp
            current_time = datetime.now()
            self._timestamps.append(current_time)
            
            # Update UI with resource data
            for resource_name, resource_data in resources.items():
                # Get amount
                amount = resource_data.get('amount', 0)
                
                # Get production rate
                production = resource_data.get('production_rate', 0)
                
                # Update resource labels if they exist
                if resource_name in self.resource_labels:
                    self.resource_labels[resource_name].setText(f"{amount:,}")
                    
                    self.production_labels[resource_name].setText(f"{production:+,}/h")
                    
                    # Update trend indicator
                    if production > 0:
                        self.trend_indicators[resource_name].setText("↑")
                        self.trend_indicators[resource_name].setStyleSheet("color: green;")
                    elif production < 0:
                        self.trend_indicators[resource_name].setText("↓")
                        self.trend_indicators[resource_name].setStyleSheet("color: red;")
                    else:
                        self.trend_indicators[resource_name].setText("→")
                        self.trend_indicators[resource_name].setStyleSheet("color: gray;")
                
                # Add to history
                self._resource_history[resource_name].append(amount)
                
                # Limit history size
                if len(self._resource_history[resource_name]) > 100:
                    self._resource_history[resource_name].pop(0)
                    self._timestamps.pop(0)
            
            # Store resources for other use
            self._resources = resources
            
            # Update chart
            self._update_chart()
            
        except Exception as e:
            logger.error(f"Error updating resources: {e}")
    
    def _update_chart(self) -> None:
        """Update the resource history chart."""
        try:
            # Check if we have any data
            if not self._resource_history or not self._timestamps:
                return
            
            # Get selected resource
            resource_name = self.chart_resource_combo.currentText().lower()
            
            # Get selected time range
            time_range = self.chart_timerange_combo.currentText()
            
            # Determine how many data points to show
            if time_range == "Last 10 minutes":
                cutoff_time = datetime.now() - timedelta(minutes=10)
                start_idx = next((i for i, t in enumerate(self._timestamps) if t >= cutoff_time), 0)
            elif time_range == "Last hour":
                cutoff_time = datetime.now() - timedelta(hours=1)
                start_idx = next((i for i, t in enumerate(self._timestamps) if t >= cutoff_time), 0)
            elif time_range == "Last day":
                cutoff_time = datetime.now() - timedelta(days=1)
                start_idx = next((i for i, t in enumerate(self._timestamps) if t >= cutoff_time), 0)
            else:  # All
                start_idx = 0
            
            # Get data to plot
            if resource_name in self._resource_history:
                resource_data = self._resource_history[resource_name][start_idx:]
                timestamps = self._timestamps[start_idx:]
                
                # Clear previous plot
                self.axes.clear()
                
                # Plot data
                if resource_data and timestamps:
                    self.axes.plot(timestamps, resource_data, 'b-')
                    
                    # Format the x-axis as time
                    self.figure.autofmt_xdate()
                    
                    # Set labels
                    self.axes.set_title(f'{resource_name.capitalize()} History')
                    self.axes.set_xlabel('Time')
                    self.axes.set_ylabel('Amount')
                    
                    # Update canvas
                    self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error updating resource chart: {e}")
    
    def refresh(self) -> None:
        """Refresh the view with the latest data."""
        self._update_resources()
    
    def update_data(self, resources_data: Dict[str, Any]) -> None:
        """
        Update the view with provided resource data.
        
        Args:
            resources_data: Resource data dictionary
        """
        # Create a formatted resources dictionary
        resources = {}
        
        # Extract resources and production rates
        for resource_name in self.resource_labels.keys():
            # Get amount (check different possible structures)
            amount = 0
            if resource_name in resources_data:
                if isinstance(resources_data[resource_name], dict):
                    amount = resources_data[resource_name].get('amount', 0)
                else:
                    amount = resources_data[resource_name]
            
            # Get production rate
            production = 0
            if 'production' in resources_data and resource_name in resources_data['production']:
                production = resources_data['production'][resource_name]
            
            # Create resource entry
            resources[resource_name] = {
                'amount': amount,
                'production_rate': production
            }
        
        # Store resources
        self._resources = resources
        
        # Store timestamp and history
        current_time = datetime.now()
        self._timestamps.append(current_time)
        
        for resource_name, data in resources.items():
            self._resource_history[resource_name].append(data['amount'])
        
        # Update UI
        for resource_name, resource_data in resources.items():
            # Update resource labels if they exist
            if resource_name in self.resource_labels:
                amount = resource_data.get('amount', 0)
                production = resource_data.get('production_rate', 0)
                
                self.resource_labels[resource_name].setText(f"{amount:,}")
                
                self.production_labels[resource_name].setText(f"{production:+,}/h")
                
                # Update trend indicator
                if production > 0:
                    self.trend_indicators[resource_name].setText("↑")
                    self.trend_indicators[resource_name].setStyleSheet("color: green;")
                elif production < 0:
                    self.trend_indicators[resource_name].setText("↓")
                    self.trend_indicators[resource_name].setStyleSheet("color: red;")
                else:
                    self.trend_indicators[resource_name].setText("→")
                    self.trend_indicators[resource_name].setStyleSheet("color: gray;")
        
        # Update chart
        self._update_chart()


class MapView(QWidget):
    """
    Widget for visualizing the game map and entities.
    
    Displays a tactical overview of the game map with discovered
    entities, locations, and territories.
    """
    
    entity_selected = pyqtSignal(dict)  # Signal when an entity is selected
    
    def __init__(self, game_state_service: GameServiceInterface):
        """
        Initialize the map view.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        self.game_state_service = game_state_service
        
        # Initialize state
        self._map_entities = {}
        self._selected_entity_id = None
        self._map_size = (1000, 1000)  # Default map size
        self._view_center = QPointF(500, 500)  # Center view at map center
        self._zoom_level = 1.0
        self._drag_start = None
        
        # Configure widget
        self.setMinimumSize(400, 400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # To receive key events
        self.setMouseTracking(True)  # To receive mouse move events
        
        # Configure colors and styles
        self._setup_styles()
        
        # Start update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_map_data)
        self._update_timer.start(10000)  # Update every 10 seconds
    
    def _setup_styles(self) -> None:
        """Set up colors and styles for map rendering."""
        self._colors = {
            "background": QColor(30, 30, 50),  # Dark blue-gray
            "grid": QColor(50, 50, 70, 128),  # Light blue-gray, semi-transparent
            "territory": QColor(0, 100, 0, 50),  # Dark green, very transparent
            "own_city": QColor(0, 200, 0),  # Bright green
            "enemy_city": QColor(200, 0, 0),  # Bright red
            "resource_node": QColor(200, 200, 0),  # Yellow
            "army": QColor(0, 100, 200),  # Blue
            "enemy_army": QColor(200, 50, 50),  # Red
            "selection": QColor(255, 255, 255, 180),  # White, semi-transparent
            "text": QColor(255, 255, 255),  # White
            "grid_text": QColor(150, 150, 170, 128)  # Light gray, semi-transparent
        }
        
        self._entity_symbols = {
            "city": "🏰",
            "enemy_city": "🏯",
            "resource_node": "🌲",
            "mine": "⛏️",
            "army": "⚔️",
            "enemy_army": "☠️",
            "camp": "⛺"
        }
    
    def _update_map_data(self) -> None:
        """Update map data from the game state service."""
        try:
            # Get current game state
            game_state = self.game_state_service.get_game_state()
            if not game_state:
                return
            
            # Get map entities
            entities = game_state.get('map_entities', {})
            
            # Get map size
            map_info = game_state.get('map_info', {})
            map_width = map_info.get('width', 1000)
            map_height = map_info.get('height', 1000)
            self._map_size = (map_width, map_height)
            
            # Store entity data
            self._map_entities = entities
            
            # Force redraw
            self.update()
            
        except Exception as e:
            logger.error(f"Error updating map data: {e}")
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Handle paint event to draw the map.
        
        Args:
            event: Paint event
        """
        # Initialize painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self._colors["background"])
        
        # Create transformation based on zoom and center
        transform = QTransform()
        transform.translate(self.width() / 2, self.height() / 2)
        transform.scale(self._zoom_level, self._zoom_level)
        transform.translate(-self._view_center.x(), -self._view_center.y())
        
        # Apply transformation
        painter.setTransform(transform)
        
        # Draw map grid
        self._draw_grid(painter)
        
        # Draw territory
        self._draw_territory(painter)
        
        # Draw entities
        self._draw_entities(painter)
        
        # Reset transformation for screen-space drawing
        painter.resetTransform()
        
        # Draw zoom indicator
        self._draw_info_overlay(painter)
    
    def _draw_grid(self, painter: QPainter) -> None:
        """
        Draw the map grid.
        
        Args:
            painter: QPainter instance
        """
        # Get map dimensions
        map_width, map_height = self._map_size
        
        # Calculate grid spacing based on zoom level
        grid_spacing = 100  # Default grid size
        
        # Adjust grid spacing based on zoom level
        if self._zoom_level < 0.5:
            grid_spacing = 200
        elif self._zoom_level > 2.0:
            grid_spacing = 50
        
        # Calculate visible range
        view_width = self.width() / self._zoom_level
        view_height = self.height() / self._zoom_level
        
        min_x = max(0, int(self._view_center.x() - view_width / 2))
        min_y = max(0, int(self._view_center.y() - view_height / 2))
        max_x = min(map_width, int(self._view_center.x() + view_width / 2))
        max_y = min(map_height, int(self._view_center.y() + view_height / 2))
        
        # Round to grid intervals
        min_x = (min_x // grid_spacing) * grid_spacing
        min_y = (min_y // grid_spacing) * grid_spacing
        
        # Set up grid pen
        painter.setPen(QPen(self._colors["grid"], 1))
        
        # Draw vertical grid lines
        for x in range(min_x, max_x + grid_spacing, grid_spacing):
            painter.drawLine(x, min_y, x, max_y)
            
            # Draw coordinate labels if zoom level is high enough
            if self._zoom_level > 0.7:
                painter.setPen(QPen(self._colors["grid_text"], 1))
                for y in range(min_y, max_y + grid_spacing, grid_spacing):
                    painter.drawText(x + 5, y - 5, f"{x},{y}")
                painter.setPen(QPen(self._colors["grid"], 1))
        
        # Draw horizontal grid lines
        for y in range(min_y, max_y + grid_spacing, grid_spacing):
            painter.drawLine(min_x, y, max_x, y)
    
    def _draw_territory(self, painter: QPainter) -> None:
        """
        Draw territory areas.
        
        Args:
            painter: QPainter instance
        """
        # Get territory data from game state
        # This is a simplified implementation - real one would use actual territory data
        
        # Draw own territory as a circle around own cities
        own_cities = [
            entity for entity in self._map_entities.values()
            if entity.get('type') == 'city' and entity.get('owner') == 'player'
        ]
        
        for city in own_cities:
            x = city.get('x', 0)
            y = city.get('y', 0)
            
            # Draw territory influence
            territory_radius = city.get('influence_radius', 100)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._colors["territory"]))
            painter.drawEllipse(QPointF(x, y), territory_radius, territory_radius)
    
    def _draw_entities(self, painter: QPainter) -> None:
        """
        Draw map entities.
        
        Args:
            painter: QPainter instance
        """
        # Skip if no entities
        if not self._map_entities:
            return
        
        # Set up font for entity symbols
        font_size = max(10, min(18, int(12 * self._zoom_level)))
        painter.setFont(QFont("Arial", font_size))
        
        # Draw each entity
        for entity_id, entity in self._map_entities.items():
            entity_type = entity.get('type', 'unknown')
            x = entity.get('x', 0)
            y = entity.get('y', 0)
            
            # Determine symbol and color based on entity type
            symbol = self._entity_symbols.get(entity_type, "❓")
            
            if entity_type == 'city':
                if entity.get('owner') == 'player':
                    color = self._colors["own_city"]
                else:
                    color = self._colors["enemy_city"]
                    symbol = self._entity_symbols["enemy_city"]
            elif entity_type in ('resource_node', 'mine'):
                color = self._colors["resource_node"]
            elif entity_type == 'army':
                if entity.get('owner') == 'player':
                    color = self._colors["army"]
                else:
                    color = self._colors["enemy_army"]
                    symbol = self._entity_symbols["enemy_army"]
            else:
                # Default color
                color = QColor(150, 150, 150)
            
            # Draw entity
            painter.setPen(QPen(color, 2))
            
            # Draw symbol
            text_rect = QRectF(x - 10, y - 10, 20, 20)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, symbol)
            
            # If entity is selected, draw selection highlight
            if entity_id == self._selected_entity_id:
                painter.setPen(QPen(self._colors["selection"], 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(x, y), 15, 15)
                
                # Draw entity name
                name = entity.get('name', f"{entity_type.capitalize()} {entity_id}")
                painter.drawText(x - 50, y + 20, 100, 20, 
                              Qt.AlignmentFlag.AlignCenter, name)
    
    def _draw_info_overlay(self, painter: QPainter) -> None:
        """
        Draw information overlay with zoom level and coordinates.
        
        Args:
            painter: QPainter instance
        """
        # Set text color
        painter.setPen(QPen(self._colors["text"], 1))
        painter.setFont(QFont("Arial", 9))
        
        # Draw zoom level
        zoom_text = f"Zoom: {self._zoom_level:.1f}x"
        painter.drawText(10, 20, zoom_text)
        
        # Draw center coordinates
        coord_text = f"Center: ({int(self._view_center.x())}, {int(self._view_center.y())})"
        painter.drawText(10, 40, coord_text)
        
        # Draw info about selection if any
        if self._selected_entity_id and self._selected_entity_id in self._map_entities:
            entity = self._map_entities[self._selected_entity_id]
            entity_type = entity.get('type', 'unknown')
            name = entity.get('name', f"{entity_type.capitalize()} {self._selected_entity_id}")
            
            info_text = f"Selected: {name} ({entity_type})"
            painter.drawText(10, self.height() - 20, info_text)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on an entity
            map_pos = self._screen_to_map(event.position().toPoint())
            entity_id = self._find_entity_at(map_pos)
            
            if entity_id:
                # Select entity
                self._selected_entity_id = entity_id
                self.entity_selected.emit(self._map_entities[entity_id])
                self.update()
            else:
                # Deselect
                self._selected_entity_id = None
                self.update()
        
        elif event.button() == Qt.MouseButton.RightButton:
            # Start drag
            self._drag_start = event.position().toPoint()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move events.
        
        Args:
            event: Mouse event
        """
        if event.buttons() & Qt.MouseButton.RightButton and self._drag_start:
            # Pan the view
            delta = event.position().toPoint() - self._drag_start
            self._drag_start = event.position().toPoint()
            
            # Scale delta by zoom level
            delta_x = delta.x() / self._zoom_level
            delta_y = delta.y() / self._zoom_level
            
            # Update view center
            self._view_center -= QPointF(delta_x, delta_y)
            
            # Clamp to map bounds
            map_width, map_height = self._map_size
            self._view_center.setX(max(0, min(map_width, self._view_center.x())))
            self._view_center.setY(max(0, min(map_height, self._view_center.y())))
            
            # Redraw
            self.update()
    
    def wheelEvent(self, event) -> None:
        """
        Handle mouse wheel events for zooming.
        
        Args:
            event: Wheel event
        """
        # Calculate zoom delta
        delta = event.angleDelta().y() / 120  # Number of steps
        
        # Calculate new zoom level
        new_zoom = self._zoom_level * (1 + delta * 0.1)
        
        # Clamp zoom level
        new_zoom = max(0.2, min(5.0, new_zoom))
        
        # Apply new zoom level
        self._zoom_level = new_zoom
        
        # Redraw
        self.update()
    
    def keyPressEvent(self, event) -> None:
        """
        Handle key press events.
        
        Args:
            event: Key event
        """
        if event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            # Zoom in
            self._zoom_level = min(5.0, self._zoom_level * 1.1)
            self.update()
            
        elif event.key() == Qt.Key.Key_Minus:
            # Zoom out
            self._zoom_level = max(0.2, self._zoom_level / 1.1)
            self.update()
            
        elif event.key() == Qt.Key.Key_0:
            # Reset zoom and center
            self._zoom_level = 1.0
            map_width, map_height = self._map_size
            self._view_center = QPointF(map_width / 2, map_height / 2)
            self.update()
            
        elif event.key() == Qt.Key.Key_Left:
            # Pan left
            self._view_center.setX(self._view_center.x() - 50 / self._zoom_level)
            self.update()
            
        elif event.key() == Qt.Key.Key_Right:
            # Pan right
            self._view_center.setX(self._view_center.x() + 50 / self._zoom_level)
            self.update()
            
        elif event.key() == Qt.Key.Key_Up:
            # Pan up
            self._view_center.setY(self._view_center.y() - 50 / self._zoom_level)
            self.update()
            
        elif event.key() == Qt.Key.Key_Down:
            # Pan down
            self._view_center.setY(self._view_center.y() + 50 / self._zoom_level)
            self.update()
            
        else:
            # Let parent handle other keys
            super().keyPressEvent(event)
    
    def _screen_to_map(self, screen_pos: QPoint) -> QPointF:
        """
        Convert screen coordinates to map coordinates.
        
        Args:
            screen_pos: Screen position
            
        Returns:
            Corresponding map position
        """
        # Calculate offset from center
        offset_x = screen_pos.x() - self.width() / 2
        offset_y = screen_pos.y() - self.height() / 2
        
        # Scale by zoom level
        map_offset_x = offset_x / self._zoom_level
        map_offset_y = offset_y / self._zoom_level
        
        # Add to view center
        map_x = self._view_center.x() + map_offset_x
        map_y = self._view_center.y() + map_offset_y
        
        return QPointF(map_x, map_y)
    
    def _find_entity_at(self, map_pos: QPointF) -> Optional[str]:
        """
        Find entity at the given map position.
        
        Args:
            map_pos: Map position
            
        Returns:
            Entity ID if an entity is at the position, None otherwise
        """
        # Search radius (adjust based on zoom level)
        radius = 15 / self._zoom_level
        
        # Check each entity
        for entity_id, entity in self._map_entities.items():
            entity_x = entity.get('x', 0)
            entity_y = entity.get('y', 0)
            
            # Calculate distance
            dx = entity_x - map_pos.x()
            dy = entity_y - map_pos.y()
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Check if close enough
            if distance <= radius:
                return entity_id
        
        return None


class BuildingsView(QWidget):
    """
    Widget for visualizing buildings and their status.
    
    Displays buildings, their levels, upgrade status,
    and production information.
    """
    
    def __init__(self, game_state_service: GameServiceInterface):
        """
        Initialize the buildings view.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        self.game_state_service = game_state_service
        
        # Initialize state
        self._buildings = {}
        
        # Create UI layout
        self._create_ui()
        
        # Start update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_buildings)
        self._update_timer.start(5000)  # Update every 5 seconds
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create buildings tree
        self.buildings_tree = QTreeWidget()
        self.buildings_tree.setHeaderLabels(["Building", "Level", "Status", "Production"])
        self.buildings_tree.setColumnWidth(0, 150)
        self.buildings_tree.setColumnWidth(1, 50)
        self.buildings_tree.setColumnWidth(2, 150)
        
        main_layout.addWidget(self.buildings_tree)
    
    def _update_buildings(self) -> None:
        """Update buildings data from the game state service."""
        try:
            # Get current game state
            game_state = self.game_state_service.get_game_state()
            if not game_state:
                return
            
            # Get buildings
            buildings = game_state.get('buildings', {})
            
            # Store for later use
            self._buildings = buildings
            
            # Clear tree
            self.buildings_tree.clear()
            
            # Group buildings by type
            building_types = defaultdict(list)
            for building_id, building in buildings.items():
                building_type = building.get('type', 'unknown')
                building_types[building_type].append((building_id, building))
            
            # Add buildings to tree
            for building_type, buildings_list in building_types.items():
                # Create type group
                type_item = QTreeWidgetItem(self.buildings_tree, [building_type.capitalize(), "", "", ""])
                type_item.setExpanded(True)
                
                # Add buildings of this type
                for building_id, building in buildings_list:
                    # Get building info
                    level = building.get('level', 0)
                    status = building.get('status', 'idle')
                    production_type = building.get('production_type', '')
                    production_amount = building.get('production_amount', 0)
                    
                    # Format production text
                    if production_type and production_amount:
                        production_text = f"{production_type}: {production_amount}/h"
                    else:
                        production_text = ""
                    
                    # Create building item
                    name = building.get('name', f"{building_type.capitalize()} {building_id}")
                    building_item = QTreeWidgetItem(type_item, [
                        name,
                        str(level),
                        status.capitalize(),
                        production_text
                    ])
                    
                    # Set status color
                    if status == 'upgrading':
                        building_item.setForeground(2, QColor(0, 150, 0))  # Green
                    elif status == 'producing':
                        building_item.setForeground(2, QColor(0, 0, 150))  # Blue
                    elif status == 'damaged':
                        building_item.setForeground(2, QColor(150, 0, 0))  # Red
            
        except Exception as e:
            logger.error(f"Error updating buildings: {e}")


class ArmyView(QWidget):
    """
    Widget for visualizing army units and their status.
    
    Displays units, their stats, locations, and status.
    """
    
    def __init__(self, game_state_service: GameServiceInterface):
        """
        Initialize the army view.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        self.game_state_service = game_state_service
        
        # Initialize state
        self._armies = {}
        
        # Create UI layout
        self._create_ui()
        
        # Start update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_armies)
        self._update_timer.start(5000)  # Update every 5 seconds
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs for different views
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs)
        
        # Units tab
        units_tab = QWidget()
        units_layout = QVBoxLayout(units_tab)
        
        # Create units table
        self.units_table = QTableWidget()
        self.units_table.setColumnCount(6)
        self.units_table.setHorizontalHeaderLabels([
            "Type", "Count", "Attack", "Defense", "Health", "Status"
        ])
        
        # Configure table
        self.units_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch)
        
        units_layout.addWidget(self.units_table)
        
        self._tabs.addTab(units_tab, "Units")
        
        # Armies tab
        armies_tab = QWidget()
        armies_layout = QVBoxLayout(armies_tab)
        
        # Create armies tree
        self.armies_tree = QTreeWidget()
        self.armies_tree.setHeaderLabels([
            "Army", "Status", "Units", "Location"
        ])
        
        armies_layout.addWidget(self.armies_tree)
        
        self._tabs.addTab(armies_tab, "Armies")
    
    def _update_armies(self) -> None:
        """Update armies data from the game state service."""
        try:
            # Get current game state
            game_state = self.game_state_service.get_game_state()
            if not game_state:
                return
            
            # Get armies
            armies = game_state.get('armies', {})
            
            # Store for later use
            self._armies = armies
            
            # Update units table
            self._update_units_table(armies)
            
            # Update armies tree
            self._update_armies_tree(armies)
            
        except Exception as e:
            logger.error(f"Error updating armies: {e}")
    
    def _update_units_table(self, armies: Dict) -> None:
        """
        Update the units table with aggregated unit data.
        
        Args:
            armies: Armies data
        """
        # Aggregate units across all armies
        unit_totals = defaultdict(int)
        unit_stats = {}
        
        for army_id, army in armies.items():
            units = army.get('units', {})
            
            for unit_type, unit_data in units.items():
                count = unit_data.get('count', 0)
                unit_totals[unit_type] += count
                
                # Store stats (use the last one seen for each unit type)
                if unit_type not in unit_stats:
                    unit_stats[unit_type] = {
                        'attack': unit_data.get('attack', 0),
                        'defense': unit_data.get('defense', 0),
                        'health': unit_data.get('health', 0),
                        'status': unit_data.get('status', 'ready')
                    }
        
        # Update table
        self.units_table.setRowCount(len(unit_totals))
        
        for i, (unit_type, count) in enumerate(unit_totals.items()):
            # Unit type
            self.units_table.setItem(i, 0, QTableWidgetItem(unit_type.capitalize()))
            
            # Count
            self.units_table.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # Stats
            if unit_type in unit_stats:
                stats = unit_stats[unit_type]
                
                self.units_table.setItem(i, 2, QTableWidgetItem(str(stats['attack'])))
                self.units_table.setItem(i, 3, QTableWidgetItem(str(stats['defense'])))
                self.units_table.setItem(i, 4, QTableWidgetItem(str(stats['health'])))
                
                status_item = QTableWidgetItem(stats['status'].capitalize())
                
                # Set status color
                if stats['status'] == 'ready':
                    status_item.setForeground(QColor(0, 150, 0))  # Green
                elif stats['status'] == 'marching':
                    status_item.setForeground(QColor(0, 0, 150))  # Blue
                elif stats['status'] == 'fighting':
                    status_item.setForeground(QColor(150, 0, 0))  # Red
                elif stats['status'] == 'returning':
                    status_item.setForeground(QColor(150, 150, 0))  # Yellow
                
                self.units_table.setItem(i, 5, status_item)
    
    def _update_armies_tree(self, armies: Dict) -> None:
        """
        Update the armies tree with army data.
        
        Args:
            armies: Armies data
        """
        # Clear tree
        self.armies_tree.clear()
        
        # Add each army
        for army_id, army in armies.items():
            # Get army info
            name = army.get('name', f"Army {army_id}")
            status = army.get('status', 'idle')
            units = army.get('units', {})
            location = army.get('location', {})
            
            # Format units text
            total_units = sum(unit.get('count', 0) for unit in units.values())
            units_text = f"{total_units} units"
            
            # Format location text
            x = location.get('x', 0)
            y = location.get('y', 0)
            location_text = f"({x}, {y})"
            
            # Create army item
            army_item = QTreeWidgetItem(self.armies_tree, [
                name,
                status.capitalize(),
                units_text,
                location_text
            ])
            
            # Set status color
            if status == 'idle':
                army_item.setForeground(1, QColor(150, 150, 150))  # Gray
            elif status == 'marching':
                army_item.setForeground(1, QColor(0, 0, 150))  # Blue
            elif status == 'fighting':
                army_item.setForeground(1, QColor(150, 0, 0))  # Red
            elif status == 'returning':
                army_item.setForeground(1, QColor(150, 150, 0))  # Yellow
            
            # Add units as children
            for unit_type, unit_data in units.items():
                count = unit_data.get('count', 0)
                unit_status = unit_data.get('status', 'ready')
                health_percent = unit_data.get('health_percent', 100)
                attack = unit_data.get('attack', 0)
                defense = unit_data.get('defense', 0)
                
                # Create unit item
                unit_item = QTreeWidgetItem(army_item, [
                    unit_type.capitalize(),
                    unit_status.capitalize(),
                    f"{count} units",
                    f"A:{attack} D:{defense} H:{health_percent}%"
                ])
                
                # Set unit status color
                if unit_status == 'ready':
                    unit_item.setForeground(1, QColor(0, 150, 0))  # Green
                elif unit_status == 'marching':
                    unit_item.setForeground(1, QColor(0, 0, 150))  # Blue
                elif unit_status == 'fighting':
                    unit_item.setForeground(1, QColor(150, 0, 0))  # Red
                elif unit_status == 'wounded':
                    unit_item.setForeground(1, QColor(150, 75, 0))  # Orange
                
                # Set health color based on percentage
                if health_percent < 25:
                    unit_item.setForeground(3, QColor(255, 0, 0))  # Red
                elif health_percent < 50:
                    unit_item.setForeground(3, QColor(255, 165, 0))  # Orange
                elif health_percent < 75:
                    unit_item.setForeground(3, QColor(255, 255, 0))  # Yellow
                else:
                    unit_item.setForeground(3, QColor(0, 255, 0))  # Green


class GameStateVisualizationWidget(QWidget):
    """
    Widget for visualizing game state information.
    
    This widget provides:
    - Resource visualization
    - Map visualization with entity positions
    - Buildings and their status
    - Army units and their status
    """
    
    def __init__(self, game_state_service: GameServiceInterface):
        """
        Initialize the game state visualization widget.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        self.game_state_service = game_state_service
        
        # Create UI layout
        self._create_ui()
        
        logger.info("Game state visualization widget initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs for different views
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs)
        
        # Create resources view
        self._resources_view = ResourcesView(self.game_state_service)
        self._tabs.addTab(self._resources_view, "Resources")
        
        # Create map view
        self._map_view = MapView(self.game_state_service)
        self._tabs.addTab(self._map_view, "Map")
        
        # Create buildings view
        self._buildings_view = BuildingsView(self.game_state_service)
        self._tabs.addTab(self._buildings_view, "Buildings")
        
        # Create army view
        self._army_view = ArmyView(self.game_state_service)
        self._tabs.addTab(self._army_view, "Army")
        
        # Connect tab changed signal
        self._tabs.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index: int) -> None:
        """
        Handle tab change event.
        
        Args:
            index: New tab index
        """
        # Refresh the selected view
        if index == 0:
            self._resources_view.refresh()
        elif index == 1:
            self._map_view.refresh()
        elif index == 2:
            self._buildings_view.refresh()
        elif index == 3:
            self._army_view.refresh()
    
    def refresh(self) -> None:
        """Refresh the visualization with the latest game state."""
        # Get game state from service
        game_state = self.game_state_service.get_game_state()
        if not game_state:
            return
        
        # Update all views
        self._resources_view.refresh()
        self._map_view.refresh()
        self._buildings_view.refresh()
        self._army_view.refresh()
    
    def set_game_data(self, game_data: Dict[str, Any]) -> None:
        """
        Set game data directly for visualization.
        
        Args:
            game_data: Game state data dictionary
        """
        # Update each view with relevant data
        if 'resources' in game_data:
            self._resources_view.update_data(game_data['resources'])
        
        if 'map' in game_data:
            self._map_view.update_data(game_data['map'])
        
        if 'buildings' in game_data:
            self._buildings_view.update_data(game_data['buildings'])
        
        if 'army' in game_data:
            self._army_view.update_data(game_data['army'])

    @property
    def entity_selected(self) -> pyqtSignal:
        """
        Signal emitted when an entity is selected.
        
        Returns:
            The entity_selected signal from the map view
        """
        return self._map_view.entity_selected 