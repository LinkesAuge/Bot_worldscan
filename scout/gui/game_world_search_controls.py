"""
Game World Search Controls

This module provides the search controls widget for the game world search tab.
It handles template selection and search pattern configuration.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QListWidget, QListWidgetItem, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from scout.template_matcher import TemplateMatcher
from scout.game_world_coordinator import GameWorldCoordinator

logger = logging.getLogger(__name__)

class SearchControlsWidget(QWidget):
    """
    Widget for configuring and controlling template searches.
    
    This widget provides:
    - Template selection
    - Search pattern configuration
    - Search control buttons
    """
    
    # Signals
    search_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    
    def __init__(
        self,
        template_matcher: TemplateMatcher,
        game_coordinator: GameWorldCoordinator
    ):
        """
        Initialize the search controls widget.
        
        Args:
            template_matcher: The template matcher instance
            game_coordinator: The game world coordinator instance
        """
        super().__init__()
        
        self.template_matcher = template_matcher
        self.game_coordinator = game_coordinator
        
        self._create_ui()
        self._load_templates()
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create template selection group
        template_group = QGroupBox("Templates")
        template_layout = QVBoxLayout()
        
        # Template list
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        template_layout.addWidget(self.template_list)
        
        # Populate template list
        self._populate_template_list()
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Create pattern selection group
        pattern_group = QGroupBox("Search Pattern")
        pattern_layout = QFormLayout()
        
        # Pattern type
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["spiral", "grid", "circles", "quadtree"])
        self.pattern_combo.currentTextChanged.connect(self._update_visible_params)
        pattern_layout.addRow("Pattern:", self.pattern_combo)
        
        # Pattern parameters
        self._create_pattern_params(pattern_layout)
        
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Create search control buttons
        control_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("Start Search")
        self.search_btn.clicked.connect(self.search_requested.emit)
        control_layout.addWidget(self.search_btn)
        
        self.stop_btn = QPushButton("Stop Search")
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        layout.addLayout(control_layout)
        
        # Show only relevant pattern parameters
        self._update_visible_params()
        
    def _create_pattern_params(self, layout: QFormLayout):
        """
        Create widgets for pattern parameters.
        
        Args:
            layout: Form layout to add widgets to
        """
        # Spiral pattern parameters
        self.spiral_params = {}
        
        self.spiral_params['center_x'] = QSpinBox()
        self.spiral_params['center_x'].setRange(-10000, 10000)
        self.spiral_params['center_x'].setValue(0)
        layout.addRow("Center X:", self.spiral_params['center_x'])
        
        self.spiral_params['center_y'] = QSpinBox()
        self.spiral_params['center_y'].setRange(-10000, 10000)
        self.spiral_params['center_y'].setValue(0)
        layout.addRow("Center Y:", self.spiral_params['center_y'])
        
        self.spiral_params['max_radius'] = QSpinBox()
        self.spiral_params['max_radius'].setRange(100, 10000)
        self.spiral_params['max_radius'].setValue(1000)
        layout.addRow("Max Radius:", self.spiral_params['max_radius'])
        
        self.spiral_params['step_size'] = QSpinBox()
        self.spiral_params['step_size'].setRange(10, 1000)
        self.spiral_params['step_size'].setValue(100)
        layout.addRow("Step Size:", self.spiral_params['step_size'])
        
        # Grid pattern parameters
        self.grid_params = {}
        
        self.grid_params['start_x'] = QSpinBox()
        self.grid_params['start_x'].setRange(-10000, 10000)
        self.grid_params['start_x'].setValue(-500)
        layout.addRow("Start X:", self.grid_params['start_x'])
        
        self.grid_params['start_y'] = QSpinBox()
        self.grid_params['start_y'].setRange(-10000, 10000)
        self.grid_params['start_y'].setValue(-500)
        layout.addRow("Start Y:", self.grid_params['start_y'])
        
        self.grid_params['width'] = QSpinBox()
        self.grid_params['width'].setRange(100, 10000)
        self.grid_params['width'].setValue(1000)
        layout.addRow("Width:", self.grid_params['width'])
        
        self.grid_params['height'] = QSpinBox()
        self.grid_params['height'].setRange(100, 10000)
        self.grid_params['height'].setValue(1000)
        layout.addRow("Height:", self.grid_params['height'])
        
        self.grid_params['step_size'] = QSpinBox()
        self.grid_params['step_size'].setRange(10, 1000)
        self.grid_params['step_size'].setValue(100)
        layout.addRow("Step Size:", self.grid_params['step_size'])
        
        self.grid_params['snake'] = QCheckBox()
        self.grid_params['snake'].setChecked(True)
        layout.addRow("Snake Pattern:", self.grid_params['snake'])
        
        # Circles pattern parameters
        self.circles_params = {}
        
        self.circles_params['center_x'] = QSpinBox()
        self.circles_params['center_x'].setRange(-10000, 10000)
        self.circles_params['center_x'].setValue(0)
        layout.addRow("Center X:", self.circles_params['center_x'])
        
        self.circles_params['center_y'] = QSpinBox()
        self.circles_params['center_y'].setRange(-10000, 10000)
        self.circles_params['center_y'].setValue(0)
        layout.addRow("Center Y:", self.circles_params['center_y'])
        
        self.circles_params['max_radius'] = QSpinBox()
        self.circles_params['max_radius'].setRange(100, 10000)
        self.circles_params['max_radius'].setValue(1000)
        layout.addRow("Max Radius:", self.circles_params['max_radius'])
        
        self.circles_params['step_size'] = QSpinBox()
        self.circles_params['step_size'].setRange(10, 1000)
        self.circles_params['step_size'].setValue(100)
        layout.addRow("Step Size:", self.circles_params['step_size'])
        
        self.circles_params['points_per_circle'] = QSpinBox()
        self.circles_params['points_per_circle'].setRange(4, 36)
        self.circles_params['points_per_circle'].setValue(8)
        layout.addRow("Points Per Circle:", self.circles_params['points_per_circle'])
        
        # Quadtree pattern parameters
        self.quadtree_params = {}
        
        self.quadtree_params['start_x'] = QSpinBox()
        self.quadtree_params['start_x'].setRange(-10000, 10000)
        self.quadtree_params['start_x'].setValue(-500)
        layout.addRow("Start X:", self.quadtree_params['start_x'])
        
        self.quadtree_params['start_y'] = QSpinBox()
        self.quadtree_params['start_y'].setRange(-10000, 10000)
        self.quadtree_params['start_y'].setValue(-500)
        layout.addRow("Start Y:", self.quadtree_params['start_y'])
        
        self.quadtree_params['width'] = QSpinBox()
        self.quadtree_params['width'].setRange(100, 10000)
        self.quadtree_params['width'].setValue(1000)
        layout.addRow("Width:", self.quadtree_params['width'])
        
        self.quadtree_params['height'] = QSpinBox()
        self.quadtree_params['height'].setRange(100, 10000)
        self.quadtree_params['height'].setValue(1000)
        layout.addRow("Height:", self.quadtree_params['height'])
        
        self.quadtree_params['min_cell_size'] = QSpinBox()
        self.quadtree_params['min_cell_size'].setRange(10, 1000)
        self.quadtree_params['min_cell_size'].setValue(100)
        layout.addRow("Min Cell Size:", self.quadtree_params['min_cell_size'])
        
    def _load_templates(self):
        """Load available templates from the template matcher."""
        try:
            # Clear existing items
            self.template_list.clear()
            
            # Add templates from template matcher
            if hasattr(self.template_matcher, 'templates'):
                for template_name in sorted(self.template_matcher.templates.keys()):
                    item = QListWidgetItem(template_name)
                    self.template_list.addItem(item)
                    
                logger.info(f"Loaded {len(self.template_matcher.templates)} templates")
                
        except Exception as e:
            logger.error(f"Error loading templates: {e}", exc_info=True)
            
    def _populate_template_list(self):
        """Populate the template list with available templates."""
        self._load_templates()
        
    def _update_visible_params(self):
        """Show only the parameters for the selected pattern."""
        pattern = self.pattern_combo.currentText()
        
        # Hide all parameters
        for param_dict in [self.spiral_params, self.grid_params, 
                          self.circles_params, self.quadtree_params]:
            for widget in param_dict.values():
                widget.hide()
                
        # Show parameters for selected pattern
        if pattern == "spiral":
            for widget in self.spiral_params.values():
                widget.show()
        elif pattern == "grid":
            for widget in self.grid_params.values():
                widget.show()
        elif pattern == "circles":
            for widget in self.circles_params.values():
                widget.show()
        elif pattern == "quadtree":
            for widget in self.quadtree_params.values():
                widget.show()
                
    def get_selected_templates(self) -> List[str]:
        """
        Get the list of selected template names.
        
        Returns:
            List of selected template names
        """
        return [item.text() for item in self.template_list.selectedItems()]
        
    def get_search_pattern(self) -> str:
        """
        Get the selected search pattern.
        
        Returns:
            Name of the selected pattern
        """
        return self.pattern_combo.currentText()
        
    def get_pattern_params(self) -> Dict[str, Any]:
        """
        Get the parameters for the selected pattern.
        
        Returns:
            Dictionary of pattern parameters
        """
        pattern = self.pattern_combo.currentText()
        
        if pattern == "spiral":
            return {
                'center_x': self.spiral_params['center_x'].value(),
                'center_y': self.spiral_params['center_y'].value(),
                'max_radius': self.spiral_params['max_radius'].value(),
                'step_size': self.spiral_params['step_size'].value()
            }
        elif pattern == "grid":
            return {
                'start_x': self.grid_params['start_x'].value(),
                'start_y': self.grid_params['start_y'].value(),
                'width': self.grid_params['width'].value(),
                'height': self.grid_params['height'].value(),
                'step_size': self.grid_params['step_size'].value(),
                'snake': self.grid_params['snake'].isChecked()
            }
        elif pattern == "circles":
            return {
                'center_x': self.circles_params['center_x'].value(),
                'center_y': self.circles_params['center_y'].value(),
                'max_radius': self.circles_params['max_radius'].value(),
                'step_size': self.circles_params['step_size'].value(),
                'points_per_circle': self.circles_params['points_per_circle'].value()
            }
        elif pattern == "quadtree":
            return {
                'start_x': self.quadtree_params['start_x'].value(),
                'start_y': self.quadtree_params['start_y'].value(),
                'width': self.quadtree_params['width'].value(),
                'height': self.quadtree_params['height'].value(),
                'min_cell_size': self.quadtree_params['min_cell_size'].value()
            }
            
        return {}
        
    def set_searching(self, is_searching: bool):
        """
        Update UI for search state.
        
        Args:
            is_searching: Whether a search is in progress
        """
        self.search_btn.setEnabled(not is_searching)
        self.stop_btn.setEnabled(is_searching)
        self.template_list.setEnabled(not is_searching)
        self.pattern_combo.setEnabled(not is_searching)
        
        # Disable pattern parameters
        for param_dict in [self.spiral_params, self.grid_params, 
                          self.circles_params, self.quadtree_params]:
            for widget in param_dict.values():
                widget.setEnabled(not is_searching) 