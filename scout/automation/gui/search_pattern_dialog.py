"""
Search Pattern Dialog

This module provides a dialog for configuring and creating search patterns
that can be used in automation sequences.
"""

from typing import Dict, Any, Optional
import logging
import math
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QDialogButtonBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from scout.automation.core import AutomationManager
from scout.automation.search_automation import SearchPatternAutomation
from scout.automation.actions import ActionType
from scout.automation.gui.search_pattern_visualizer import SearchPatternVisualizer

logger = logging.getLogger(__name__)


class SearchPatternDialog(QDialog):
    """
    Dialog for configuring and creating search patterns.
    
    This dialog allows users to select a search pattern type, configure its
    parameters, and create an automation sequence that follows the pattern.
    """
    
    def __init__(self, automation_manager: AutomationManager, parent=None):
        """
        Initialize the search pattern dialog.
        
        Args:
            automation_manager: The automation manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.automation_manager = automation_manager
        self.search_automation = SearchPatternAutomation(automation_manager)
        
        self.setWindowTitle("Create Search Pattern")
        self.setMinimumWidth(500)
        
        self._create_ui()
        self._connect_signals()
        self._update_description()
        
    def _create_ui(self) -> None:
        """Create the dialog UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Sequence name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sequence Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText("Search Pattern")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Pattern selection
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern Type:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["spiral", "grid", "circles", "quadtree"])
        pattern_layout.addWidget(self.pattern_combo)
        layout.addLayout(pattern_layout)
        
        # Pattern description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-style: italic;")
        layout.addWidget(self.description_label)
        
        # Visualize button
        self.visualize_button = QPushButton("Visualize Pattern")
        self.visualize_button.clicked.connect(self._visualize_pattern)
        layout.addWidget(self.visualize_button)
        
        # Action type
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("Action Type:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["CLICK", "TEMPLATE_SEARCH"])
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)
        
        # Parameter groups
        self.param_groups = {}
        
        # Spiral parameters
        spiral_group = QGroupBox("Spiral Parameters")
        spiral_layout = QFormLayout()
        
        self.spiral_center_combo = QComboBox()
        self.spiral_center_combo.addItem("Screen Center")
        for pos_name in sorted(self.automation_manager.positions.keys()):
            self.spiral_center_combo.addItem(pos_name)
        spiral_layout.addRow("Center Position:", self.spiral_center_combo)
        
        self.spiral_radius_spin = QSpinBox()
        self.spiral_radius_spin.setRange(50, 2000)
        self.spiral_radius_spin.setValue(500)
        spiral_layout.addRow("Max Radius:", self.spiral_radius_spin)
        
        self.spiral_step_spin = QSpinBox()
        self.spiral_step_spin.setRange(10, 200)
        self.spiral_step_spin.setValue(50)
        spiral_layout.addRow("Step Size:", self.spiral_step_spin)
        
        spiral_group.setLayout(spiral_layout)
        layout.addWidget(spiral_group)
        self.param_groups["spiral"] = spiral_group
        
        # Grid parameters
        grid_group = QGroupBox("Grid Parameters")
        grid_layout = QFormLayout()
        
        self.grid_start_combo = QComboBox()
        self.grid_start_combo.addItem("Top Left")
        for pos_name in sorted(self.automation_manager.positions.keys()):
            self.grid_start_combo.addItem(pos_name)
        grid_layout.addRow("Start Position:", self.grid_start_combo)
        
        self.grid_width_spin = QSpinBox()
        self.grid_width_spin.setRange(100, 3840)
        self.grid_width_spin.setValue(1920)
        grid_layout.addRow("Width:", self.grid_width_spin)
        
        self.grid_height_spin = QSpinBox()
        self.grid_height_spin.setRange(100, 2160)
        self.grid_height_spin.setValue(1080)
        grid_layout.addRow("Height:", self.grid_height_spin)
        
        self.grid_step_spin = QSpinBox()
        self.grid_step_spin.setRange(10, 200)
        self.grid_step_spin.setValue(50)
        grid_layout.addRow("Step Size:", self.grid_step_spin)
        
        self.grid_snake_check = QCheckBox("Use Snake Pattern")
        self.grid_snake_check.setChecked(True)
        grid_layout.addRow("", self.grid_snake_check)
        
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        self.param_groups["grid"] = grid_group
        
        # Circles parameters
        circles_group = QGroupBox("Circles Parameters")
        circles_layout = QFormLayout()
        
        self.circles_center_combo = QComboBox()
        self.circles_center_combo.addItem("Screen Center")
        for pos_name in sorted(self.automation_manager.positions.keys()):
            self.circles_center_combo.addItem(pos_name)
        circles_layout.addRow("Center Position:", self.circles_center_combo)
        
        self.circles_radius_spin = QSpinBox()
        self.circles_radius_spin.setRange(50, 2000)
        self.circles_radius_spin.setValue(500)
        circles_layout.addRow("Max Radius:", self.circles_radius_spin)
        
        self.circles_step_spin = QSpinBox()
        self.circles_step_spin.setRange(10, 200)
        self.circles_step_spin.setValue(50)
        circles_layout.addRow("Step Size:", self.circles_step_spin)
        
        self.circles_points_spin = QSpinBox()
        self.circles_points_spin.setRange(4, 36)
        self.circles_points_spin.setValue(8)
        circles_layout.addRow("Min Points Per Circle:", self.circles_points_spin)
        
        circles_group.setLayout(circles_layout)
        layout.addWidget(circles_group)
        self.param_groups["circles"] = circles_group
        
        # Quadtree parameters
        quadtree_group = QGroupBox("Quadtree Parameters")
        quadtree_layout = QFormLayout()
        
        self.quadtree_start_combo = QComboBox()
        self.quadtree_start_combo.addItem("Top Left")
        for pos_name in sorted(self.automation_manager.positions.keys()):
            self.quadtree_start_combo.addItem(pos_name)
        quadtree_layout.addRow("Start Position:", self.quadtree_start_combo)
        
        self.quadtree_width_spin = QSpinBox()
        self.quadtree_width_spin.setRange(100, 3840)
        self.quadtree_width_spin.setValue(1920)
        quadtree_layout.addRow("Width:", self.quadtree_width_spin)
        
        self.quadtree_height_spin = QSpinBox()
        self.quadtree_height_spin.setRange(100, 2160)
        self.quadtree_height_spin.setValue(1080)
        quadtree_layout.addRow("Height:", self.quadtree_height_spin)
        
        self.quadtree_min_size_spin = QSpinBox()
        self.quadtree_min_size_spin.setRange(10, 200)
        self.quadtree_min_size_spin.setValue(50)
        quadtree_layout.addRow("Min Cell Size:", self.quadtree_min_size_spin)
        
        quadtree_group.setLayout(quadtree_layout)
        layout.addWidget(quadtree_group)
        self.param_groups["quadtree"] = quadtree_group
        
        # Preview button
        self.preview_button = QPushButton("Preview Pattern")
        self.preview_button.clicked.connect(self._preview_pattern)
        layout.addWidget(self.preview_button)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Show only the relevant parameter group
        self._update_visible_params()
        
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self.pattern_combo.currentTextChanged.connect(self._update_visible_params)
        self.pattern_combo.currentTextChanged.connect(self._update_description)
        self.preview_button.clicked.connect(self._preview_pattern)
        self.visualize_button.clicked.connect(self._visualize_pattern)
        
    def _update_visible_params(self) -> None:
        """Show only the parameter group for the selected pattern."""
        current_pattern = self.pattern_combo.currentText()
        
        for pattern, group in self.param_groups.items():
            group.setVisible(pattern == current_pattern)
            
    def _update_description(self) -> None:
        """Update the pattern description text."""
        current_pattern = self.pattern_combo.currentText()
        description = self.search_automation.get_pattern_description(current_pattern)
        self.description_label.setText(description)
        
    def _preview_pattern(self) -> None:
        """Generate and visualize the current pattern."""
        try:
            pattern_name = self.pattern_combo.currentText()
            params = self._get_pattern_params()
            
            # Create visualization
            output_path = "search_pattern_preview.json"
            self.search_automation.visualize_pattern(
                pattern_name,
                output_path=output_path,
                **params
            )
            
            QMessageBox.information(
                self,
                "Pattern Preview",
                f"Pattern visualization saved to {output_path}.\n\n"
                f"The pattern will generate approximately {self._estimate_point_count(pattern_name, params)} points."
            )
            
        except Exception as e:
            logger.error(f"Error previewing pattern: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Preview Error",
                f"Failed to preview pattern: {str(e)}"
            )
            
    def _visualize_pattern(self) -> None:
        """Open the pattern visualizer dialog."""
        try:
            SearchPatternVisualizer.show_visualizer(self)
        except Exception as e:
            logger.error(f"Error opening pattern visualizer: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Visualization Error",
                f"Failed to open pattern visualizer: {str(e)}"
            )
            
    def _estimate_point_count(self, pattern_name: str, params: Dict[str, Any]) -> int:
        """
        Estimate the number of points that will be generated by the pattern.
        
        Args:
            pattern_name: Name of the pattern
            params: Pattern parameters
            
        Returns:
            Estimated number of points
        """
        if pattern_name == "spiral":
            max_radius = params.get("max_radius", 500)
            step_size = params.get("step_size", 50)
            # Approximate formula for spiral points
            return 1 + 4 * (max_radius // step_size) * (max_radius // step_size + 1)
            
        elif pattern_name == "grid":
            width = params.get("width", 1920)
            height = params.get("height", 1080)
            step_size = params.get("step_size", 50)
            return ((width // step_size) + 1) * ((height // step_size) + 1)
            
        elif pattern_name == "circles":
            max_radius = params.get("max_radius", 500)
            step_size = params.get("step_size", 50)
            points_per_circle = params.get("points_per_circle", 8)
            # Approximate formula for circles points
            circles_count = max_radius // step_size
            return 1 + sum(max(points_per_circle, int(2 * 3.14159 * r)) for r in range(step_size, max_radius + 1, step_size))
            
        elif pattern_name == "quadtree":
            width = params.get("width", 1920)
            height = params.get("height", 1080)
            min_cell_size = params.get("min_cell_size", 50)
            # Approximate formula for quadtree points
            depth = max(
                int(math.log2(width / min_cell_size)),
                int(math.log2(height / min_cell_size))
            )
            return (4**(depth + 1) - 1) // 3  # Sum of geometric series
            
        return 0
        
    def _get_pattern_params(self) -> Dict[str, Any]:
        """
        Get the parameters for the current pattern.
        
        Returns:
            Dictionary of pattern parameters
        """
        pattern_name = self.pattern_combo.currentText()
        
        if pattern_name == "spiral":
            center_pos = self.spiral_center_combo.currentText()
            if center_pos == "Screen Center":
                return {
                    "center_x": 1920,
                    "center_y": 1080,
                    "max_radius": self.spiral_radius_spin.value(),
                    "step_size": self.spiral_step_spin.value()
                }
            else:
                return {
                    "center_position": center_pos,
                    "max_radius": self.spiral_radius_spin.value(),
                    "step_size": self.spiral_step_spin.value()
                }
                
        elif pattern_name == "grid":
            start_pos = self.grid_start_combo.currentText()
            if start_pos == "Top Left":
                return {
                    "start_x": 0,
                    "start_y": 0,
                    "width": self.grid_width_spin.value(),
                    "height": self.grid_height_spin.value(),
                    "step_size": self.grid_step_spin.value(),
                    "snake": self.grid_snake_check.isChecked()
                }
            else:
                return {
                    "start_position": start_pos,
                    "width": self.grid_width_spin.value(),
                    "height": self.grid_height_spin.value(),
                    "step_size": self.grid_step_spin.value(),
                    "snake": self.grid_snake_check.isChecked()
                }
                
        elif pattern_name == "circles":
            center_pos = self.circles_center_combo.currentText()
            if center_pos == "Screen Center":
                return {
                    "center_x": 1920,
                    "center_y": 1080,
                    "max_radius": self.circles_radius_spin.value(),
                    "step_size": self.circles_step_spin.value(),
                    "points_per_circle": self.circles_points_spin.value()
                }
            else:
                return {
                    "center_position": center_pos,
                    "max_radius": self.circles_radius_spin.value(),
                    "step_size": self.circles_step_spin.value(),
                    "points_per_circle": self.circles_points_spin.value()
                }
                
        elif pattern_name == "quadtree":
            start_pos = self.quadtree_start_combo.currentText()
            if start_pos == "Top Left":
                return {
                    "start_x": 0,
                    "start_y": 0,
                    "width": self.quadtree_width_spin.value(),
                    "height": self.quadtree_height_spin.value(),
                    "min_cell_size": self.quadtree_min_size_spin.value()
                }
            else:
                return {
                    "start_position": start_pos,
                    "width": self.quadtree_width_spin.value(),
                    "height": self.quadtree_height_spin.value(),
                    "min_cell_size": self.quadtree_min_size_spin.value()
                }
                
        return {}
        
    def accept(self) -> None:
        """Handle dialog acceptance."""
        try:
            # Get sequence name
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(
                    self,
                    "Invalid Name",
                    "Please enter a name for the search sequence."
                )
                return
                
            # Get pattern parameters
            pattern_name = self.pattern_combo.currentText()
            params = self._get_pattern_params()
            
            # Get action type
            action_type_str = self.action_combo.currentText()
            action_type = getattr(ActionType, action_type_str)
            
            # Create and save the sequence
            sequence = self.search_automation.create_and_save_search_sequence(
                name,
                pattern_name,
                action_type,
                **params
            )
            
            QMessageBox.information(
                self,
                "Sequence Created",
                f"Search sequence '{name}' created with {len(sequence.actions)} points."
            )
            
            super().accept()
            
        except Exception as e:
            logger.error(f"Error creating search sequence: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Creation Error",
                f"Failed to create search sequence: {str(e)}"
            )
            
    @staticmethod
    def create_search_pattern(automation_manager: AutomationManager, parent=None) -> bool:
        """
        Static method to create and show the dialog.
        
        Args:
            automation_manager: The automation manager instance
            parent: Parent widget
            
        Returns:
            True if a sequence was created, False otherwise
        """
        dialog = SearchPatternDialog(automation_manager, parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted 