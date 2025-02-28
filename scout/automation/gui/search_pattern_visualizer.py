"""
Search Pattern Visualizer

This module provides a graphical visualization of search patterns to help users
understand how each pattern works before creating a sequence.
"""

from typing import List, Tuple, Dict, Any
import logging
import math
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDialog, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsRectItem, QComboBox, QSpinBox, QFormLayout,
    QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont

from scout.automation.search_patterns import (
    spiral_pattern, grid_pattern, 
    expanding_circles_pattern, quadtree_pattern
)

logger = logging.getLogger(__name__)

class PatternVisualizerScene(QGraphicsScene):
    """
    Graphics scene for visualizing search patterns.
    
    This scene displays the points generated by a search pattern and
    shows the order in which they will be visited.
    """
    
    def __init__(self, parent=None):
        """Initialize the pattern visualizer scene."""
        super().__init__(parent)
        self.setSceneRect(0, 0, 600, 600)
        self.points = []
        self.show_numbers = True
        self.show_lines = True
        self.scale_factor = 1.0
        self.offset_x = 300  # Center of the scene
        self.offset_y = 300  # Center of the scene
        
        # Add background grid
        self._draw_grid()
        
    def _draw_grid(self) -> None:
        """Draw a background grid to help with orientation."""
        # Draw major grid lines
        grid_pen = QPen(QColor(200, 200, 200, 100))
        grid_pen.setWidth(1)
        
        # Draw horizontal and vertical lines
        for i in range(0, 601, 50):
            # Horizontal line
            self.addLine(0, i, 600, i, grid_pen)
            # Vertical line
            self.addLine(i, 0, i, 600, grid_pen)
            
        # Draw center lines
        center_pen = QPen(QColor(150, 150, 150, 150))
        center_pen.setWidth(2)
        self.addLine(0, 300, 600, 300, center_pen)  # Horizontal center
        self.addLine(300, 0, 300, 600, center_pen)  # Vertical center
        
    def set_points(self, points: List[Tuple[int, int]]) -> None:
        """
        Set the points to visualize.
        
        Args:
            points: List of (x, y) coordinates
        """
        self.points = points
        self.update_visualization()
        
    def update_visualization(self) -> None:
        """Update the visualization with the current points."""
        # Clear existing items except the grid
        for item in self.items():
            if not isinstance(item, QGraphicsLineItem) or item.pen().color().alpha() != 100:
                self.removeItem(item)
                
        if not self.points:
            return
            
        # Calculate bounds for auto-scaling
        min_x = min(p[0] for p in self.points)
        max_x = max(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_y = max(p[1] for p in self.points)
        
        # Calculate scale to fit points in the view
        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
        
        # Determine scale factor (with some padding)
        scale_x = 500 / width if width > 0 else 1
        scale_y = 500 / height if height > 0 else 1
        self.scale_factor = min(scale_x, scale_y) * 0.9
        
        # Calculate center of points
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Draw connecting lines first (so they're behind the points)
        if self.show_lines and len(self.points) > 1:
            line_pen = QPen(QColor(100, 100, 255, 150))
            line_pen.setWidth(1)
            
            for i in range(len(self.points) - 1):
                x1, y1 = self.points[i]
                x2, y2 = self.points[i + 1]
                
                # Transform coordinates
                scene_x1 = (x1 - center_x) * self.scale_factor + self.offset_x
                scene_y1 = (y1 - center_y) * self.scale_factor + self.offset_y
                scene_x2 = (x2 - center_x) * self.scale_factor + self.offset_x
                scene_y2 = (y2 - center_y) * self.scale_factor + self.offset_y
                
                self.addLine(scene_x1, scene_y1, scene_x2, scene_y2, line_pen)
        
        # Draw points
        for i, (x, y) in enumerate(self.points):
            # Transform coordinates
            scene_x = (x - center_x) * self.scale_factor + self.offset_x
            scene_y = (y - center_y) * self.scale_factor + self.offset_y
            
            # Determine color based on position in sequence
            # Start with blue, gradually transition to red
            progress = i / max(1, len(self.points) - 1)
            color = QColor(
                int(255 * progress),      # Red component
                0,                        # Green component
                int(255 * (1 - progress)) # Blue component
            )
            
            # Create point
            point_size = 6
            ellipse = QGraphicsEllipseItem(
                scene_x - point_size/2, 
                scene_y - point_size/2,
                point_size, 
                point_size
            )
            ellipse.setBrush(QBrush(color))
            ellipse.setPen(QPen(Qt.PenStyle.NoPen))
            self.addItem(ellipse)
            
            # Add number if enabled
            if self.show_numbers:
                # Only show numbers for some points to avoid clutter
                if i == 0 or i == len(self.points) - 1 or i % max(1, len(self.points) // 20) == 0:
                    text = QGraphicsTextItem(str(i))
                    text.setPos(scene_x + 5, scene_y - 10)
                    text.setDefaultTextColor(QColor(50, 50, 50))
                    font = QFont()
                    font.setPointSize(8)
                    text.setFont(font)
                    self.addItem(text)
        
        # Add legend
        self._add_legend()
        
    def _add_legend(self) -> None:
        """Add a legend explaining the visualization."""
        # Create legend background
        legend_rect = QGraphicsRectItem(10, 10, 180, 80)
        legend_rect.setBrush(QBrush(QColor(255, 255, 255, 200)))
        legend_rect.setPen(QPen(QColor(100, 100, 100)))
        self.addItem(legend_rect)
        
        # Add title
        title = QGraphicsTextItem("Pattern Legend")
        title.setPos(15, 10)
        title.setDefaultTextColor(QColor(0, 0, 0))
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        self.addItem(title)
        
        # Add start point
        start_point = QGraphicsEllipseItem(20, 35, 6, 6)
        start_point.setBrush(QBrush(QColor(0, 0, 255)))
        start_point.setPen(QPen(Qt.PenStyle.NoPen))
        self.addItem(start_point)
        
        start_text = QGraphicsTextItem("Start Point (0)")
        start_text.setPos(35, 30)
        self.addItem(start_text)
        
        # Add end point
        end_point = QGraphicsEllipseItem(20, 55, 6, 6)
        end_point.setBrush(QBrush(QColor(255, 0, 0)))
        end_point.setPen(QPen(Qt.PenStyle.NoPen))
        self.addItem(end_point)
        
        end_text = QGraphicsTextItem("End Point")
        end_text.setPos(35, 50)
        self.addItem(end_text)
        
        # Add direction indicator
        if self.show_lines:
            direction_line = QGraphicsLineItem(20, 75, 50, 75)
            direction_line.setPen(QPen(QColor(100, 100, 255, 150)))
            self.addItem(direction_line)
            
            direction_text = QGraphicsTextItem("Movement Direction")
            direction_text.setPos(60, 70)
            self.addItem(direction_text)
            
    def set_show_numbers(self, show: bool) -> None:
        """
        Set whether to show point numbers.
        
        Args:
            show: Whether to show numbers
        """
        self.show_numbers = show
        self.update_visualization()
        
    def set_show_lines(self, show: bool) -> None:
        """
        Set whether to show connecting lines.
        
        Args:
            show: Whether to show lines
        """
        self.show_lines = show
        self.update_visualization()


class PatternVisualizerView(QGraphicsView):
    """
    Graphics view for the pattern visualizer.
    
    This view displays the pattern visualization scene and handles
    zooming and panning.
    """
    
    def __init__(self, scene, parent=None):
        """Initialize the pattern visualizer view."""
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumSize(600, 600)
        self.setMaximumSize(600, 600)
        
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming."""
        # Zoom factor
        factor = 1.1
        
        if event.angleDelta().y() < 0:
            # Zoom out
            self.scale(1.0 / factor, 1.0 / factor)
        else:
            # Zoom in
            self.scale(factor, factor)


class SearchPatternVisualizer(QDialog):
    """
    Dialog for visualizing search patterns.
    
    This dialog allows users to select a pattern type, configure its parameters,
    and see a visualization of the resulting pattern.
    """
    
    def __init__(self, parent=None):
        """Initialize the search pattern visualizer."""
        super().__init__(parent)
        self.setWindowTitle("Search Pattern Visualizer")
        self.setMinimumWidth(800)
        self.setMinimumHeight(650)
        
        self._create_ui()
        self._connect_signals()
        self._update_pattern()
        
    def _create_ui(self) -> None:
        """Create the dialog UI components."""
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Left side - controls
        controls_layout = QVBoxLayout()
        
        # Pattern selection
        pattern_group = QGroupBox("Pattern Type")
        pattern_layout = QVBoxLayout()
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["spiral", "grid", "circles", "quadtree"])
        pattern_layout.addWidget(self.pattern_combo)
        
        # Pattern description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-style: italic;")
        pattern_layout.addWidget(self.description_label)
        pattern_group.setLayout(pattern_layout)
        controls_layout.addWidget(pattern_group)
        
        # Parameter groups
        self.param_groups = {}
        
        # Spiral parameters
        spiral_group = QGroupBox("Spiral Parameters")
        spiral_layout = QFormLayout()
        
        self.spiral_center_x = QSpinBox()
        self.spiral_center_x.setRange(-1000, 1000)
        self.spiral_center_x.setValue(0)
        spiral_layout.addRow("Center X:", self.spiral_center_x)
        
        self.spiral_center_y = QSpinBox()
        self.spiral_center_y.setRange(-1000, 1000)
        self.spiral_center_y.setValue(0)
        spiral_layout.addRow("Center Y:", self.spiral_center_y)
        
        self.spiral_radius = QSpinBox()
        self.spiral_radius.setRange(50, 1000)
        self.spiral_radius.setValue(200)
        spiral_layout.addRow("Max Radius:", self.spiral_radius)
        
        self.spiral_step = QSpinBox()
        self.spiral_step.setRange(10, 100)
        self.spiral_step.setValue(20)
        spiral_layout.addRow("Step Size:", self.spiral_step)
        
        spiral_group.setLayout(spiral_layout)
        controls_layout.addWidget(spiral_group)
        self.param_groups["spiral"] = spiral_group
        
        # Grid parameters
        grid_group = QGroupBox("Grid Parameters")
        grid_layout = QFormLayout()
        
        self.grid_start_x = QSpinBox()
        self.grid_start_x.setRange(-1000, 1000)
        self.grid_start_x.setValue(-200)
        grid_layout.addRow("Start X:", self.grid_start_x)
        
        self.grid_start_y = QSpinBox()
        self.grid_start_y.setRange(-1000, 1000)
        self.grid_start_y.setValue(-200)
        grid_layout.addRow("Start Y:", self.grid_start_y)
        
        self.grid_width = QSpinBox()
        self.grid_width.setRange(50, 1000)
        self.grid_width.setValue(400)
        grid_layout.addRow("Width:", self.grid_width)
        
        self.grid_height = QSpinBox()
        self.grid_height.setRange(50, 1000)
        self.grid_height.setValue(400)
        grid_layout.addRow("Height:", self.grid_height)
        
        self.grid_step = QSpinBox()
        self.grid_step.setRange(10, 100)
        self.grid_step.setValue(40)
        grid_layout.addRow("Step Size:", self.grid_step)
        
        self.grid_snake = QCheckBox("Snake Pattern")
        self.grid_snake.setChecked(True)
        grid_layout.addRow("", self.grid_snake)
        
        grid_group.setLayout(grid_layout)
        controls_layout.addWidget(grid_group)
        self.param_groups["grid"] = grid_group
        
        # Circles parameters
        circles_group = QGroupBox("Circles Parameters")
        circles_layout = QFormLayout()
        
        self.circles_center_x = QSpinBox()
        self.circles_center_x.setRange(-1000, 1000)
        self.circles_center_x.setValue(0)
        circles_layout.addRow("Center X:", self.circles_center_x)
        
        self.circles_center_y = QSpinBox()
        self.circles_center_y.setRange(-1000, 1000)
        self.circles_center_y.setValue(0)
        circles_layout.addRow("Center Y:", self.circles_center_y)
        
        self.circles_radius = QSpinBox()
        self.circles_radius.setRange(50, 1000)
        self.circles_radius.setValue(200)
        circles_layout.addRow("Max Radius:", self.circles_radius)
        
        self.circles_step = QSpinBox()
        self.circles_step.setRange(10, 100)
        self.circles_step.setValue(40)
        circles_layout.addRow("Step Size:", self.circles_step)
        
        self.circles_points = QSpinBox()
        self.circles_points.setRange(4, 36)
        self.circles_points.setValue(8)
        circles_layout.addRow("Min Points Per Circle:", self.circles_points)
        
        circles_group.setLayout(circles_layout)
        controls_layout.addWidget(circles_group)
        self.param_groups["circles"] = circles_group
        
        # Quadtree parameters
        quadtree_group = QGroupBox("Quadtree Parameters")
        quadtree_layout = QFormLayout()
        
        self.quadtree_start_x = QSpinBox()
        self.quadtree_start_x.setRange(-1000, 1000)
        self.quadtree_start_x.setValue(-200)
        quadtree_layout.addRow("Start X:", self.quadtree_start_x)
        
        self.quadtree_start_y = QSpinBox()
        self.quadtree_start_y.setRange(-1000, 1000)
        self.quadtree_start_y.setValue(-200)
        quadtree_layout.addRow("Start Y:", self.quadtree_start_y)
        
        self.quadtree_width = QSpinBox()
        self.quadtree_width.setRange(50, 1000)
        self.quadtree_width.setValue(400)
        quadtree_layout.addRow("Width:", self.quadtree_width)
        
        self.quadtree_height = QSpinBox()
        self.quadtree_height.setRange(50, 1000)
        self.quadtree_height.setValue(400)
        quadtree_layout.addRow("Height:", self.quadtree_height)
        
        self.quadtree_min_size = QSpinBox()
        self.quadtree_min_size.setRange(10, 100)
        self.quadtree_min_size.setValue(40)
        quadtree_layout.addRow("Min Cell Size:", self.quadtree_min_size)
        
        quadtree_group.setLayout(quadtree_layout)
        controls_layout.addWidget(quadtree_group)
        self.param_groups["quadtree"] = quadtree_group
        
        # Visualization options
        vis_group = QGroupBox("Visualization Options")
        vis_layout = QVBoxLayout()
        
        self.show_numbers = QCheckBox("Show Point Numbers")
        self.show_numbers.setChecked(True)
        vis_layout.addWidget(self.show_numbers)
        
        self.show_lines = QCheckBox("Show Connecting Lines")
        self.show_lines.setChecked(True)
        vis_layout.addWidget(self.show_lines)
        
        # Point count display
        self.point_count = QLabel("Points: 0")
        vis_layout.addWidget(self.point_count)
        
        vis_group.setLayout(vis_layout)
        controls_layout.addWidget(vis_group)
        
        # Update button
        self.update_btn = QPushButton("Update Visualization")
        controls_layout.addWidget(self.update_btn)
        
        # Add spacer
        controls_layout.addStretch()
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        controls_layout.addWidget(self.close_btn)
        
        layout.addLayout(controls_layout)
        
        # Right side - visualization
        vis_layout = QVBoxLayout()
        
        # Create scene and view
        self.scene = PatternVisualizerScene()
        self.view = PatternVisualizerView(self.scene)
        vis_layout.addWidget(self.view)
        
        layout.addLayout(vis_layout)
        
        # Show only the relevant parameter group
        self._update_visible_params()
        
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self.pattern_combo.currentTextChanged.connect(self._update_visible_params)
        self.pattern_combo.currentTextChanged.connect(self._update_description)
        self.update_btn.clicked.connect(self._update_pattern)
        self.show_numbers.stateChanged.connect(self._update_visualization_options)
        self.show_lines.stateChanged.connect(self._update_visualization_options)
        
        # Connect all parameter controls to update the pattern
        for group_name, group in self.param_groups.items():
            for i in range(group.layout().rowCount()):
                widget = group.layout().itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
                if isinstance(widget, (QSpinBox, QCheckBox)):
                    if isinstance(widget, QSpinBox):
                        widget.valueChanged.connect(self._update_pattern)
                    else:
                        widget.stateChanged.connect(self._update_pattern)
        
    def _update_visible_params(self) -> None:
        """Show only the parameter group for the selected pattern."""
        current_pattern = self.pattern_combo.currentText()
        
        for pattern, group in self.param_groups.items():
            group.setVisible(pattern == current_pattern)
            
    def _update_description(self) -> None:
        """Update the pattern description text."""
        current_pattern = self.pattern_combo.currentText()
        
        descriptions = {
            "spiral": (
                "Spiral Pattern: Starts at the center and moves outward in a spiral. "
                "Efficient when targets are likely to be closer to the center."
            ),
            "grid": (
                "Grid Pattern: Systematically covers a rectangular area by moving in rows. "
                "The snake pattern alternates row direction for efficiency."
            ),
            "circles": (
                "Expanding Circles Pattern: Generates points in concentric circles around a center. "
                "Useful when targets might be at a specific distance from the center."
            ),
            "quadtree": (
                "Quadtree Pattern: Recursively divides the search space into quadrants. "
                "Efficient for quickly finding targets in a large area."
            )
        }
        
        self.description_label.setText(descriptions.get(current_pattern, ""))
        
    def _update_pattern(self) -> None:
        """Update the pattern visualization based on current parameters."""
        pattern_type = self.pattern_combo.currentText()
        points = []
        
        try:
            if pattern_type == "spiral":
                points = list(spiral_pattern(
                    center_x=self.spiral_center_x.value(),
                    center_y=self.spiral_center_y.value(),
                    max_radius=self.spiral_radius.value(),
                    step_size=self.spiral_step.value()
                ))
                
            elif pattern_type == "grid":
                points = list(grid_pattern(
                    start_x=self.grid_start_x.value(),
                    start_y=self.grid_start_y.value(),
                    width=self.grid_width.value(),
                    height=self.grid_height.value(),
                    step_size=self.grid_step.value(),
                    snake=self.grid_snake.isChecked()
                ))
                
            elif pattern_type == "circles":
                points = list(expanding_circles_pattern(
                    center_x=self.circles_center_x.value(),
                    center_y=self.circles_center_y.value(),
                    max_radius=self.circles_radius.value(),
                    step_size=self.circles_step.value(),
                    points_per_circle=self.circles_points.value()
                ))
                
            elif pattern_type == "quadtree":
                points = list(quadtree_pattern(
                    start_x=self.quadtree_start_x.value(),
                    start_y=self.quadtree_start_y.value(),
                    width=self.quadtree_width.value(),
                    height=self.quadtree_height.value(),
                    min_cell_size=self.quadtree_min_size.value()
                ))
                
            # Update the scene with the new points
            self.scene.set_points(points)
            
            # Update point count
            self.point_count.setText(f"Points: {len(points)}")
            
        except Exception as e:
            logger.error(f"Error updating pattern: {e}", exc_info=True)
            self.point_count.setText(f"Error: {str(e)}")
            
    def _update_visualization_options(self) -> None:
        """Update visualization options based on checkboxes."""
        self.scene.set_show_numbers(self.show_numbers.isChecked())
        self.scene.set_show_lines(self.show_lines.isChecked())
        
    @staticmethod
    def show_visualizer(parent=None) -> None:
        """
        Static method to create and show the visualizer dialog.
        
        Args:
            parent: Parent widget
        """
        dialog = SearchPatternVisualizer(parent)
        dialog.exec() 