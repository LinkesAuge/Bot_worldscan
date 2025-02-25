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
    QTreeWidgetItem, QProgressBar, QStackedWidget, QToolBar, QCheckBox
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
from scout.ui.utils.language_manager import tr

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
        self.resources_group = QGroupBox(tr("Resources"))
        resources_layout = QGridLayout(self.resources_group)
        
        # Headers
        resources_layout.addWidget(QLabel(tr("Resource")), 0, 0)
        resources_layout.addWidget(QLabel(tr("Amount")), 0, 1)
        resources_layout.addWidget(QLabel(tr("Production")), 0, 2)
        resources_layout.addWidget(QLabel(tr("Trend")), 0, 3)
        
        # Set up grid for standard resources
        self.resource_labels = {}
        self.production_labels = {}
        self.trend_indicators = {}
        
        standard_resources = [tr("Gold"), tr("Food"), tr("Wood"), tr("Stone"), tr("Iron")]
        
        for i, resource_name in enumerate(standard_resources):
            # Resource name
            resources_layout.addWidget(QLabel(resource_name), i + 1, 0)
            
            # Resource amount
            amount_label = QLabel("0")
            amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            resources_layout.addWidget(amount_label, i + 1, 1)
            self.resource_labels[resource_name] = amount_label
            
            # Resource production
            production_label = QLabel("+0/h")
            production_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            resources_layout.addWidget(production_label, i + 1, 2)
            self.production_labels[resource_name] = production_label
            
            # Trend indicator
            trend_label = QLabel("→")
            trend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            resources_layout.addWidget(trend_label, i + 1, 3)
            self.trend_indicators[resource_name] = trend_label
        
        # Add resource grid to main layout
        main_layout.addWidget(self.resources_group)
        
        # Create chart container
        chart_group = QGroupBox(tr("Resource Trends"))
        chart_layout = QVBoxLayout(chart_group)
        
        # Create toolbar for chart
        chart_toolbar = QHBoxLayout()
        
        # Chart type selector
        chart_toolbar.addWidget(QLabel(tr("View:")))
        self.chart_type = QComboBox()
        self.chart_type.addItems([tr("All Resources"), tr("Gold"), tr("Food"), tr("Wood"), tr("Stone"), tr("Iron")])
        self.chart_type.currentIndexChanged.connect(self._update_chart)
        chart_toolbar.addWidget(self.chart_type)
        
        # Time range selector
        chart_toolbar.addWidget(QLabel(tr("Time Range:")))
        self.time_range = QComboBox()
        self.time_range.addItems([tr("Last Hour"), tr("Last 24 Hours"), tr("Last Week")])
        self.time_range.currentIndexChanged.connect(self._update_chart)
        chart_toolbar.addWidget(self.time_range)
        
        chart_layout.addLayout(chart_toolbar)
        
        # Add placeholder for chart
        self.chart_label = QLabel(tr("No resource data available"))
        self.chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_label.setFixedHeight(200)
        self.chart_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        chart_layout.addWidget(self.chart_label)
        
        # Add chart to main layout
        main_layout.addWidget(chart_group)
        
        # Add spacer to push everything up
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
            resource_name = self.chart_type.currentText()
            
            # Get selected time range
            time_range = self.time_range.currentText()
            
            # Determine how many data points to show
            if time_range == tr("Last Hour"):
                cutoff_time = datetime.now() - timedelta(hours=1)
                start_idx = next((i for i, t in enumerate(self._timestamps) if t >= cutoff_time), 0)
            elif time_range == tr("Last 24 Hours"):
                cutoff_time = datetime.now() - timedelta(days=1)
                start_idx = next((i for i, t in enumerate(self._timestamps) if t >= cutoff_time), 0)
            elif time_range == tr("Last Week"):
                cutoff_time = datetime.now() - timedelta(days=7)
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
        
        # Initialize map state
        self._map_data = {}
        self._entities = {}
        self._territory = []
        self._selected_entity = None
        
        # View transformation
        self._offset_x = 0
        self._offset_y = 0
        self._scale = 1.0
        self._drag_start = None
        
        # Set up styles
        self._setup_styles()
        
        # Create UI layout
        self._create_ui()
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Set focus policy to receive key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _setup_styles(self) -> None:
        """Set up styles for map drawing."""
        # Entity colors
        self.entity_colors = {
            'city': QColor(0, 0, 255, 180),      # Blue
            'village': QColor(0, 128, 0, 180),   # Green
            'resource': QColor(255, 165, 0, 180), # Orange
            'army': QColor(255, 0, 0, 180),      # Red
            'npc': QColor(128, 128, 128, 180),   # Gray
            'player': QColor(255, 255, 0, 180),  # Yellow
            'ally': QColor(0, 255, 255, 180),    # Cyan
            'enemy': QColor(255, 0, 255, 180),   # Magenta
            'unknown': QColor(0, 0, 0, 180)      # Black
        }
        
        # Grid style
        self.grid_pen = QPen(QColor(200, 200, 200, 100))
        self.grid_pen.setWidth(1)
        
        # Territory style
        self.territory_brush = QBrush(QColor(0, 200, 0, 50))
        self.territory_pen = QPen(QColor(0, 100, 0, 150))
        self.territory_pen.setWidth(2)
        
        # Selection style
        self.selection_pen = QPen(QColor(255, 255, 0, 255))
        self.selection_pen.setWidth(3)
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create map controls
        controls_layout = QHBoxLayout()
        
        # Zoom controls
        zoom_group = QGroupBox(tr("Zoom"))
        zoom_layout = QHBoxLayout(zoom_group)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.clicked.connect(lambda: self._zoom(-0.1))
        zoom_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.clicked.connect(lambda: self._zoom(0.1))
        zoom_layout.addWidget(self.zoom_in_btn)
        
        controls_layout.addWidget(zoom_group)
        
        # Filter controls
        filter_group = QGroupBox(tr("Filters"))
        filter_layout = QHBoxLayout(filter_group)
        
        self.show_cities_cb = QCheckBox(tr("Cities"))
        self.show_cities_cb.setChecked(True)
        self.show_cities_cb.stateChanged.connect(self.update)
        filter_layout.addWidget(self.show_cities_cb)
        
        self.show_resources_cb = QCheckBox(tr("Resources"))
        self.show_resources_cb.setChecked(True)
        self.show_resources_cb.stateChanged.connect(self.update)
        filter_layout.addWidget(self.show_resources_cb)
        
        self.show_armies_cb = QCheckBox(tr("Armies"))
        self.show_armies_cb.setChecked(True)
        self.show_armies_cb.stateChanged.connect(self.update)
        filter_layout.addWidget(self.show_armies_cb)
        
        controls_layout.addWidget(filter_group)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        
        # Create info panel for selected entity
        self.info_panel = QGroupBox(tr("Selection Info"))
        info_layout = QGridLayout(self.info_panel)
        
        info_layout.addWidget(QLabel(tr("Type:")), 0, 0)
        self.entity_type_label = QLabel("")
        info_layout.addWidget(self.entity_type_label, 0, 1)
        
        info_layout.addWidget(QLabel(tr("Name:")), 1, 0)
        self.entity_name_label = QLabel("")
        info_layout.addWidget(self.entity_name_label, 1, 1)
        
        info_layout.addWidget(QLabel(tr("Coordinates:")), 2, 0)
        self.entity_coords_label = QLabel("")
        info_layout.addWidget(self.entity_coords_label, 2, 1)
        
        info_layout.addWidget(QLabel(tr("Details:")), 3, 0)
        self.entity_details_label = QLabel("")
        info_layout.addWidget(self.entity_details_label, 3, 1)
        
        # Add info panel to main layout
        main_layout.addWidget(self.info_panel)
        self.info_panel.setVisible(False)  # Hide initially
        
        # Set minimum size for map display
        self.setMinimumSize(400, 300)
    
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
            self._entities = entities
            
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
            entity for entity in self._entities.values()
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
        if not self._entities:
            return
        
        # Set up font for entity symbols
        font_size = max(10, min(18, int(12 * self._zoom_level)))
        painter.setFont(QFont("Arial", font_size))
        
        # Draw each entity
        for entity_id, entity in self._entities.items():
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
        if self._selected_entity_id and self._selected_entity_id in self._entities:
            entity = self._entities[self._selected_entity_id]
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
                self.entity_selected.emit(self._entities[entity_id])
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
        for entity_id, entity in self._entities.items():
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
    Widget for visualizing game buildings.
    
    Displays a list of buildings with their types, levels,
    and current status.
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
        
        # Create buildings table
        self.buildings_table = QTableWidget()
        self.buildings_table.setColumnCount(5)
        self.buildings_table.setHorizontalHeaderLabels([
            tr("Name"), tr("Type"), tr("Level"), tr("Status"), tr("Actions")
        ])
        self.buildings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.buildings_table)
        
        # Create filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel(tr("Filter:")))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([tr("All"), tr("Military"), tr("Economic"), tr("Infrastructure")])
        self.filter_combo.currentIndexChanged.connect(self._update_buildings)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        
        # Sort options
        filter_layout.addWidget(QLabel(tr("Sort by:")))
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([tr("Name"), tr("Type"), tr("Level")])
        self.sort_combo.currentIndexChanged.connect(self._update_buildings)
        filter_layout.addWidget(self.sort_combo)
        
        main_layout.addLayout(filter_layout)
    
    def _update_buildings(self) -> None:
        """Update the buildings table with current data."""
        try:
            # Get buildings data
            buildings_data = self.game_state_service.get_buildings()
            
            if not buildings_data:
                # No data available
                self._buildings = {}
                self.buildings_table.setRowCount(0)
                return
            
            # Store buildings data
            self._buildings = buildings_data
            
            # Get filter and sort options
            filter_option = self.filter_combo.currentText()
            sort_option = self.sort_combo.currentText()
            
            # Filter buildings
            filtered_buildings = []
            for building_id, building in buildings_data.items():
                if filter_option == tr("All"):
                    filtered_buildings.append((building_id, building))
                elif filter_option == tr("Military") and building.get("category") == "military":
                    filtered_buildings.append((building_id, building))
                elif filter_option == tr("Economic") and building.get("category") == "economic":
                    filtered_buildings.append((building_id, building))
                elif filter_option == tr("Infrastructure") and building.get("category") == "infrastructure":
                    filtered_buildings.append((building_id, building))
            
            # Sort buildings
            if sort_option == tr("Name"):
                filtered_buildings.sort(key=lambda b: b[1].get("name", ""))
            elif sort_option == tr("Type"):
                filtered_buildings.sort(key=lambda b: b[1].get("type", ""))
            elif sort_option == tr("Level"):
                filtered_buildings.sort(key=lambda b: b[1].get("level", 0), reverse=True)
            
            # Update table
            self.buildings_table.setRowCount(len(filtered_buildings))
            
            for row, (building_id, building) in enumerate(filtered_buildings):
                # Name
                name_item = QTableWidgetItem(building.get("name", f"Building {building_id}"))
                self.buildings_table.setItem(row, 0, name_item)
                
                # Type
                type_item = QTableWidgetItem(building.get("type", "Unknown"))
                self.buildings_table.setItem(row, 1, type_item)
                
                # Level
                level_item = QTableWidgetItem(str(building.get("level", 0)))
                self.buildings_table.setItem(row, 2, level_item)
                
                # Status
                status = building.get("status", "idle")
                status_item = QTableWidgetItem(status)
                
                # Color code status
                if status == "upgrading":
                    status_item.setBackground(QBrush(QColor(0, 200, 0)))  # Green
                elif status == "constructing":
                    status_item.setBackground(QBrush(QColor(0, 0, 200)))  # Blue
                elif status == "damaged":
                    status_item.setBackground(QBrush(QColor(200, 0, 0)))  # Red
                
                self.buildings_table.setItem(row, 3, status_item)
                
                # Actions button
                actions_btn = QPushButton(tr("Details"))
                actions_btn.setProperty("building_id", building_id)
                actions_btn.clicked.connect(self._on_details_clicked)
                self.buildings_table.setCellWidget(row, 4, actions_btn)
            
        except Exception as e:
            logger.error(f"Error updating buildings view: {e}")
    
    def _on_details_clicked(self) -> None:
        """Handle building details button click."""
        # Get building ID from sender
        sender = self.sender()
        building_id = sender.property("building_id")
        
        if building_id in self._buildings:
            # Show building details
            building = self._buildings[building_id]
            
            details = QMessageBox()
            details.setWindowTitle(tr("Building Details"))
            details.setText(f"{building.get('name', 'Building')}")
            
            # Build details message
            details_text = f"""
            <b>{tr("Type")}:</b> {building.get('type', tr('Unknown'))}<br>
            <b>{tr("Level")}:</b> {building.get('level', 0)}<br>
            <b>{tr("Status")}:</b> {building.get('status', tr('Idle'))}<br>
            <b>{tr("Health")}:</b> {building.get('health', 100)}%<br>
            """
            
            # Add production info if available
            if "production" in building:
                details_text += f"<b>{tr('Production')}:</b><br>"
                for resource, amount in building["production"].items():
                    details_text += f"- {resource}: {amount}/h<br>"
            
            details.setInformativeText(details_text)
            details.setStandardButtons(QMessageBox.StandardButton.Ok)
            details.exec()
    
    def refresh(self) -> None:
        """Refresh the buildings view."""
        self._update_buildings()
    
    def update_data(self, buildings_data: Dict) -> None:
        """Update with new buildings data."""
        self._buildings = buildings_data
        self._update_buildings()


class ArmyView(QWidget):
    """
    Widget for visualizing army units and groups.
    
    Displays a hierarchical view of army units organized by 
    groups, showing their status, strength, and movement.
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
        
        # Create tab widget for different views
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create units table view
        self.units_widget = QWidget()
        units_layout = QVBoxLayout(self.units_widget)
        
        # Units filter
        units_filter_layout = QHBoxLayout()
        
        units_filter_layout.addWidget(QLabel(tr("Filter Units:")))
        
        self.units_filter = QComboBox()
        self.units_filter.addItems([tr("All"), tr("Infantry"), tr("Cavalry"), tr("Ranged"), tr("Siege")])
        self.units_filter.currentIndexChanged.connect(self._update_units_table)
        units_filter_layout.addWidget(self.units_filter)
        
        units_filter_layout.addStretch()
        
        units_layout.addLayout(units_filter_layout)
        
        # Units table
        self.units_table = QTableWidget()
        self.units_table.setColumnCount(4)
        self.units_table.setHorizontalHeaderLabels([
            tr("Unit Type"), tr("Count"), tr("Status"), tr("Location")
        ])
        self.units_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        units_layout.addWidget(self.units_table)
        
        # Add units tab
        self.tabs.addTab(self.units_widget, tr("Units"))
        
        # Create armies hierarchical view
        self.armies_widget = QWidget()
        armies_layout = QVBoxLayout(self.armies_widget)
        
        # Armies tree
        self.armies_tree = QTreeWidget()
        self.armies_tree.setHeaderLabels([
            tr("Army/Group"), tr("Status"), tr("Strength"), tr("Location")
        ])
        self.armies_tree.setColumnWidth(0, 150)
        self.armies_tree.setAlternatingRowColors(True)
        armies_layout.addWidget(self.armies_tree)
        
        # Add armies tab
        self.tabs.addTab(self.armies_widget, tr("Armies"))
        
        # Create movement map view
        self.movement_widget = QWidget()
        movement_layout = QVBoxLayout(self.movement_widget)
        
        # Map placeholder
        self.movement_map = QLabel(tr("Army movement map will be displayed here"))
        self.movement_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movement_map.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.movement_map.setMinimumHeight(300)
        movement_layout.addWidget(self.movement_map)
        
        # Add movement tab
        self.tabs.addTab(self.movement_widget, tr("Movement"))
    
    def _update_armies(self) -> None:
        """Update army data from the game state service."""
        try:
            # Get armies data
            armies_data = self.game_state_service.get_armies()
            
            if not armies_data:
                # Clear and return if no data
                self.units_table.setRowCount(0)
                self.armies_tree.clear()
                self._armies = {}
                return
            
            # Store armies data
            self._armies = armies_data
            
            # Update units table
            self._update_units_table(armies_data)
            
            # Update armies tree
            self._update_armies_tree(armies_data)
            
        except Exception as e:
            logger.error(f"Error updating armies view: {e}")
    
    def _update_units_table(self, armies: Dict) -> None:
        """
        Update the units table.
        
        Args:
            armies: Army data dictionary
        """
        # Get filter
        unit_filter = self.units_filter.currentText()
        
        # Aggregate units by type
        units_by_type = defaultdict(int)
        unit_status = {}
        unit_location = {}
        
        # Process all armies
        for army_id, army in armies.items():
            # Skip if not an army with units
            if not army.get('units'):
                continue
            
            # Process each unit type
            for unit_type, count in army['units'].items():
                # Apply filter
                unit_category = unit_type.split('_')[0] if '_' in unit_type else 'infantry'
                
                if unit_filter == tr("All") or \
                   (unit_filter == tr("Infantry") and unit_category == 'infantry') or \
                   (unit_filter == tr("Cavalry") and unit_category == 'cavalry') or \
                   (unit_filter == tr("Ranged") and unit_category == 'ranged') or \
                   (unit_filter == tr("Siege") and unit_category == 'siege'):
                    # Count units
                    units_by_type[unit_type] += count
                    
                    # Track status and location
                    unit_status[unit_type] = army.get('status', tr('Idle'))
                    unit_location[unit_type] = f"{army.get('x', 0)}, {army.get('y', 0)}"
        
        # Update table
        self.units_table.setRowCount(len(units_by_type))
        
        for row, (unit_type, count) in enumerate(sorted(units_by_type.items())):
            # Unit type
            type_item = QTableWidgetItem(unit_type.replace('_', ' ').title())
            self.units_table.setItem(row, 0, type_item)
            
            # Count
            count_item = QTableWidgetItem(str(count))
            self.units_table.setItem(row, 1, count_item)
            
            # Status
            status_item = QTableWidgetItem(unit_status.get(unit_type, ''))
            
            # Color code by status
            status = unit_status.get(unit_type, '')
            if status == 'marching':
                status_item.setBackground(QBrush(QColor(0, 0, 200)))  # Blue
                status_item.setForeground(QBrush(QColor(255, 255, 255)))  # White text
            elif status == 'fighting':
                status_item.setBackground(QBrush(QColor(200, 0, 0)))  # Red
                status_item.setForeground(QBrush(QColor(255, 255, 255)))  # White text
            
            self.units_table.setItem(row, 2, status_item)
            
            # Location
            location_item = QTableWidgetItem(unit_location.get(unit_type, ''))
            self.units_table.setItem(row, 3, location_item)
    
    def _update_armies_tree(self, armies: Dict) -> None:
        """
        Update the armies tree.
        
        Args:
            armies: Army data dictionary
        """
        # Clear tree
        self.armies_tree.clear()
        
        # Group armies by status
        status_groups = defaultdict(list)
        
        for army_id, army in armies.items():
            # Get army info
            name = army.get('name', f"Army {army_id}")
            status = army.get('status', 'idle')
            units = army.get('units', {})
            location = army.get('location', {})
            
            # Add armies in this status group
            for army_id, army in army_list:
                # Calculate strength
                total_units = sum(army.get('units', {}).values())
                
                # Format location
                location = f"{army.get('x', 0)}, {army.get('y', 0)}"
                
                # Create army item
                army_name = army.get('name', f"{tr('Army')} {army_id}")
                army_item = QTreeWidgetItem(status_item, [
                    army_name,
                    tr(army.get('activity', '')),
                    str(total_units),
                    location
                ])
                
                # Add units as children
                for unit_type, count in sorted(army.get('units', {}).items()):
                    unit_name = unit_type.replace('_', ' ').title()
                    QTreeWidgetItem(army_item, [
                        f"{unit_name}",
                        "",
                        str(count),
                        ""
                    ])
    
    def refresh(self) -> None:
        """Refresh the army view."""
        self._update_armies()
    
    def update_data(self, armies_data: Dict) -> None:
        """
        Update with new army data.
        
        Args:
            armies_data: Army data dictionary
        """
        self._armies = armies_data
        self._update_armies()


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
        self._tabs.addTab(self._resources_view, tr("Resources"))
        
        # Create map view
        self._map_view = MapView(self.game_state_service)
        self._tabs.addTab(self._map_view, tr("Map"))
        
        # Create buildings view
        self._buildings_view = BuildingsView(self.game_state_service)
        self._tabs.addTab(self._buildings_view, tr("Buildings"))
        
        # Create army view
        self._army_view = ArmyView(self.game_state_service)
        self._tabs.addTab(self._army_view, tr("Army"))
        
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