"""
Automation Tab

This module provides a tab interface for configuring and executing automation sequences.
It allows users to create, load, edit, and execute sequences of actions to automate
interaction with the target application.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QDoubleSpinBox, QTabWidget, QRadioButton, QSizePolicy
)
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer

from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.ui.widgets.detection_result_widget import DetectionResultWidget
from scout.ui.widgets.control_panel_widget import ControlPanelWidget
from scout.ui.utils.language_manager import tr

# Import action editor and position list
from .automation_action_editor import AutomationActionEditor
from .automation_position_list import PositionList

# Set up logging
logger = logging.getLogger(__name__)

class AutomationActionEditor(QWidget):
    """
    Widget for editing automation action properties.
    
    This widget provides an interface for configuring the parameters of
    different automation actions like clicking, typing, waiting, etc.
    """
    
    # Signals
    action_updated = pyqtSignal(dict)  # Updated action data
    
    def __init__(self):
        """Initialize the automation action editor."""
        super().__init__()
        
        # Initialize state
        self._current_action = None
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create title label
        self.title_label = QLabel(tr("Edit Action"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(self.title_label)
        
        # Create scroll area for parameters
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        # Create scrollable content widget
        scroll_content = QWidget()
        self.params_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        
        # Create common parameters group
        common_group = QGroupBox(tr("Common Parameters"))
        common_layout = QGridLayout(common_group)
        
        # Action type label & combo
        common_layout.addWidget(QLabel(tr("Action Type:")), 0, 0)
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems([
            tr("Click"), tr("Right Click"), tr("Double Click"),
            tr("Type Text"), tr("Press Key"), tr("Wait"),
            tr("Wait for Template"), tr("Wait for OCR Text"),
            tr("Conditional"), tr("Loop"), tr("End Loop")
        ])
        common_layout.addWidget(self.action_type_combo, 0, 1)
        
        # Action name label & field
        common_layout.addWidget(QLabel(tr("Action Name:")), 1, 0)
        self.action_name_field = QLineEdit()
        common_layout.addWidget(self.action_name_field, 1, 1)
        
        # Add common group to layout
        self.params_layout.addWidget(common_group)
        
        # Create specific parameters container
        self.specific_params_widget = QWidget()
        self.specific_params_layout = QVBoxLayout(self.specific_params_widget)
        self.params_layout.addWidget(self.specific_params_widget)
        
        # Placeholder for action-specific parameters
        self.placeholder_label = QLabel(tr("Select an action type to configure parameters"))
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.specific_params_layout.addWidget(self.placeholder_label)
        
        # Create buttons
        buttons_layout = QHBoxLayout()
        
        # Apply button
        self.apply_button = QPushButton(tr("Apply Changes"))
        self.apply_button.setEnabled(False)
        buttons_layout.addWidget(self.apply_button)
        
        # Cancel button
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.setEnabled(False)
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(buttons_layout)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Action type combo
        self.action_type_combo.currentIndexChanged.connect(self._on_action_type_changed)
        
        # Action name field
        self.action_name_field.textChanged.connect(self._on_fields_changed)
        
        # Buttons
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
    
    def set_action(self, action: Dict[str, Any]) -> None:
        """
        Set the action to edit.
        
        Args:
            action: Action data dictionary
        """
        # Store current action
        self._current_action = action.copy() if action else None
        
        # Enable/disable buttons
        self.apply_button.setEnabled(action is not None)
        self.cancel_button.setEnabled(action is not None)
        
        if not action:
            # Clear fields
            self.action_type_combo.setCurrentIndex(0)
            self.action_name_field.setText("")
            self._clear_specific_params()
            return
        
        # Update fields with action data
        
        # Action type
        action_type = action.get('type', 'click')
        index = self.action_type_combo.findText(action_type.capitalize())
        if index >= 0:
            self.action_type_combo.setCurrentIndex(index)
        
        # Action name
        self.action_name_field.setText(action.get('name', ''))
        
        # Update specific parameters
        self._update_specific_params(action_type, action)
    
    def _on_action_type_changed(self, index: int) -> None:
        """
        Handle action type change.
        
        Args:
            index: Selected index
        """
        if self._current_action is None:
            return
        
        # Get selected action type
        action_type = self.action_type_combo.currentText().lower().replace(' ', '_')
        
        # Update specific parameters
        self._update_specific_params(action_type, self._current_action)
        
        # Update current action type
        self._current_action['type'] = action_type
        
        # Enable apply button
        self._on_fields_changed()
    
    def _update_specific_params(self, action_type: str, action: Dict[str, Any]) -> None:
        """
        Update specific parameters UI based on action type.
        
        Args:
            action_type: Action type string
            action: Action data dictionary
        """
        # Clear previous parameters
        self._clear_specific_params()
        
        # Create parameters based on action type
        if action_type in ['click', 'right_click', 'double_click']:
            self._create_click_params(action)
        elif action_type == 'type_text':
            self._create_type_text_params(action)
        elif action_type == 'press_key':
            self._create_press_key_params(action)
        elif action_type == 'wait':
            self._create_wait_params(action)
        elif action_type in ['wait_for_template', 'wait_for_ocr_text']:
            self._create_wait_for_params(action, action_type)
        elif action_type == 'conditional':
            self._create_conditional_params(action)
        elif action_type in ['loop', 'end_loop']:
            self._create_loop_params(action, action_type)
    
    def _clear_specific_params(self) -> None:
        """Clear specific parameters UI."""
        # Remove all widgets from layout
        while self.specific_params_layout.count():
            item = self.specific_params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _create_click_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for click actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox(tr("Click Parameters"))
        layout = QGridLayout(group)
        
        # X position
        layout.addWidget(QLabel(tr("X Position:")), 0, 0)
        self.x_position = QSpinBox()
        self.x_position.setRange(0, 9999)
        self.x_position.setValue(action.get('x', 0))
        layout.addWidget(self.x_position, 0, 1)
        
        # Y position
        layout.addWidget(QLabel(tr("Y Position:")), 1, 0)
        self.y_position = QSpinBox()
        self.y_position.setRange(0, 9999)
        self.y_position.setValue(action.get('y', 0))
        layout.addWidget(self.y_position, 1, 1)
        
        # Delay
        layout.addWidget(QLabel(tr("Delay (ms):")), 2, 0)
        self.delay = QSpinBox()
        self.delay.setRange(0, 60000)
        self.delay.setValue(action.get('delay', 500))
        layout.addWidget(self.delay, 2, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        self.x_position.valueChanged.connect(self._on_fields_changed)
        self.y_position.valueChanged.connect(self._on_fields_changed)
        self.delay.valueChanged.connect(self._on_fields_changed)
    
    def _create_type_text_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for type text actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox(tr("Text Input Parameters"))
        layout = QGridLayout(group)
        
        # Text
        layout.addWidget(QLabel(tr("Text:")), 0, 0)
        self.text = QLineEdit()
        self.text.setText(action.get('text', ''))
        layout.addWidget(self.text, 0, 1)
        
        # Delay
        layout.addWidget(QLabel(tr("Delay between keys (ms):")), 1, 0)
        self.delay = QSpinBox()
        self.delay.setRange(0, 1000)
        self.delay.setValue(action.get('delay', 50))
        layout.addWidget(self.delay, 1, 1)
        
        # Enter key
        layout.addWidget(QLabel(tr("Press Enter after text:")), 2, 0)
        self.press_enter = QCheckBox()
        self.press_enter.setChecked(action.get('press_enter', False))
        layout.addWidget(self.press_enter, 2, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        self.text.textChanged.connect(self._on_fields_changed)
        self.delay.valueChanged.connect(self._on_fields_changed)
        self.press_enter.stateChanged.connect(self._on_fields_changed)
    
    def _create_press_key_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for pressing key actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox(tr("Key Press Parameters"))
        layout = QGridLayout(group)
        
        # Key
        layout.addWidget(QLabel(tr("Key:")), 0, 0)
        self.key = QComboBox()
        
        # Add common keys
        key_groups = {
            tr("Special Keys"): ['enter', 'tab', 'space', 'backspace', 'escape', 'delete'],
            tr("Arrow Keys"): ['up', 'down', 'left', 'right'],
            tr("Function Keys"): [f'f{i}' for i in range(1, 13)],
            tr("Modifier Keys"): ['shift', 'ctrl', 'alt', 'win'],
            tr("Common Keys"): ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        }
        
        for group_name, keys in key_groups.items():
            self.key.addItem(group_name, None)  # Add group header
            for key in keys:
                self.key.addItem(key, key)  # Add actual key
        
        # Set current key if available
        key_value = action.get('key', 'enter')
        index = self.key.findData(key_value)
        if index >= 0:
            self.key.setCurrentIndex(index)
        
        layout.addWidget(self.key, 0, 1)
        
        # Modifiers
        modifiers_group = QGroupBox(tr("Modifiers"))
        modifiers_layout = QVBoxLayout(modifiers_group)
        
        self.shift_mod = QCheckBox(tr("Shift"))
        self.shift_mod.setChecked(action.get('shift', False))
        modifiers_layout.addWidget(self.shift_mod)
        
        self.ctrl_mod = QCheckBox(tr("Control"))
        self.ctrl_mod.setChecked(action.get('ctrl', False))
        modifiers_layout.addWidget(self.ctrl_mod)
        
        self.alt_mod = QCheckBox(tr("Alt"))
        self.alt_mod.setChecked(action.get('alt', False))
        modifiers_layout.addWidget(self.alt_mod)
        
        layout.addWidget(modifiers_group, 1, 0, 1, 2)
        
        # Repeat
        layout.addWidget(QLabel(tr("Repeat Count:")), 2, 0)
        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 100)
        self.repeat_count.setValue(action.get('repeat', 1))
        layout.addWidget(self.repeat_count, 2, 1)
        
        # Delay
        layout.addWidget(QLabel(tr("Delay between repeats (ms):")), 3, 0)
        self.delay = QSpinBox()
        self.delay.setRange(0, 10000)
        self.delay.setValue(action.get('delay', 100))
        layout.addWidget(self.delay, 3, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        self.key.currentIndexChanged.connect(self._on_fields_changed)
        self.shift_mod.stateChanged.connect(self._on_fields_changed)
        self.ctrl_mod.stateChanged.connect(self._on_fields_changed)
        self.alt_mod.stateChanged.connect(self._on_fields_changed)
        self.repeat_count.valueChanged.connect(self._on_fields_changed)
        self.delay.valueChanged.connect(self._on_fields_changed)
    
    def _create_wait_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for wait actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox(tr("Wait Parameters"))
        layout = QGridLayout(group)
        
        # Duration
        layout.addWidget(QLabel(tr("Duration (ms):")), 0, 0)
        self.duration = QSpinBox()
        self.duration.setRange(0, 3600000)  # Up to 1 hour
        self.duration.setValue(action.get('duration', 1000))
        layout.addWidget(self.duration, 0, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        self.duration.valueChanged.connect(self._on_fields_changed)
    
    def _create_wait_for_params(self, action: Dict[str, Any], action_type: str) -> None:
        """
        Create parameters UI for wait for template/text actions.
        
        Args:
            action: Action data dictionary
            action_type: 'wait_for_template' or 'wait_for_ocr_text'
        """
        if action_type == 'wait_for_template':
            # Create group box for template wait
            group = QGroupBox(tr("Wait for Template Parameters"))
            layout = QGridLayout(group)
            
            # Template name
            layout.addWidget(QLabel(tr("Template Name:")), 0, 0)
            self.template_name = QComboBox()
            
            # Load available templates
            template_dir = Path('resources/templates')
            if template_dir.exists():
                template_files = list(template_dir.glob('*.png'))
                template_names = [f.stem for f in template_files]
                if template_names:
                    self.template_name.addItems(template_names)
            
            # Set current template if available
            template = action.get('template', '')
            index = self.template_name.findText(template)
            if index >= 0:
                self.template_name.setCurrentIndex(index)
            
            layout.addWidget(self.template_name, 0, 1)
        else:
            # Create group box for OCR text wait
            group = QGroupBox(tr("Wait for OCR Text Parameters"))
            layout = QGridLayout(group)
            
            # Text to wait for
            layout.addWidget(QLabel(tr("Text:")), 0, 0)
            self.text = QLineEdit()
            self.text.setText(action.get('text', ''))
            layout.addWidget(self.text, 0, 1)
        
        # Common parameters
        # Timeout
        layout.addWidget(QLabel(tr("Timeout (ms):")), 1, 0)
        self.timeout = QSpinBox()
        self.timeout.setRange(0, 3600000)  # Up to 1 hour
        self.timeout.setValue(action.get('timeout', 10000))
        layout.addWidget(self.timeout, 1, 1)
        
        # Confidence threshold (for template matching)
        if action_type == 'wait_for_template':
            layout.addWidget(QLabel(tr("Confidence Threshold:")), 2, 0)
            self.confidence = QDoubleSpinBox()
            self.confidence.setRange(0.1, 1.0)
            self.confidence.setSingleStep(0.05)
            self.confidence.setValue(action.get('confidence', 0.7))
            layout.addWidget(self.confidence, 2, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        if action_type == 'wait_for_template':
            self.template_name.currentIndexChanged.connect(self._on_fields_changed)
            self.confidence.valueChanged.connect(self._on_fields_changed)
        else:
            self.text.textChanged.connect(self._on_fields_changed)
        
        self.timeout.valueChanged.connect(self._on_fields_changed)
    
    def _create_conditional_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for conditional actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox(tr("Conditional Parameters"))
        layout = QGridLayout(group)
        
        # Condition type
        layout.addWidget(QLabel(tr("Condition Type:")), 0, 0)
        self.condition_type = QComboBox()
        self.condition_type.addItems([
            tr("Template Found"),
            tr("OCR Text Found"),
            tr("Color at Point"),
            tr("Pixel Comparison")
        ])
        
        # Set current condition type if available
        condition_type = action.get('condition_type', 'template_found')
        index = 0
        
        if condition_type == 'template_found':
            index = 0
        elif condition_type == 'ocr_text_found':
            index = 1
        elif condition_type == 'color_at_point':
            index = 2
        elif condition_type == 'pixel_comparison':
            index = 3
        
        self.condition_type.setCurrentIndex(index)
        layout.addWidget(self.condition_type, 0, 1)
        
        # Create container for condition-specific params
        self.condition_params_widget = QWidget()
        self.condition_params_layout = QVBoxLayout(self.condition_params_widget)
        
        # Create condition-specific params based on type
        self._create_condition_specific_params(condition_type, action)
        
        layout.addWidget(self.condition_params_widget, 1, 0, 1, 2)
        
        # True action
        layout.addWidget(QLabel(tr("If True, Skip to:")), 2, 0)
        self.true_action = QSpinBox()
        self.true_action.setRange(0, 999)
        self.true_action.setValue(action.get('true_action', 0))
        layout.addWidget(self.true_action, 2, 1)
        
        # False action
        layout.addWidget(QLabel(tr("If False, Skip to:")), 3, 0)
        self.false_action = QSpinBox()
        self.false_action.setRange(0, 999)
        self.false_action.setValue(action.get('false_action', 0))
        layout.addWidget(self.false_action, 3, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
        
        # Connect signals
        self.condition_type.currentIndexChanged.connect(self._on_condition_type_changed)
        self.true_action.valueChanged.connect(self._on_fields_changed)
        self.false_action.valueChanged.connect(self._on_fields_changed)
    
    def _create_loop_params(self, action: Dict[str, Any], action_type: str) -> None:
        """
        Create parameters UI for loop/end loop actions.
        
        Args:
            action: Action data dictionary
            action_type: Action type string
        """
        # Create group box
        title = "Loop Parameters" if action_type == "loop" else "End Loop Parameters"
        group = QGroupBox(title)
        layout = QGridLayout(group)
        
        if action_type == "loop":
            # Loop type
            layout.addWidget(QLabel("Loop Type:"), 0, 0)
            self.loop_type_combo = QComboBox()
            self.loop_type_combo.addItems([
                "Infinite", "Count", "While Condition"
            ])
            loop_type = action.get('loop_type', 'count')
            if loop_type == 'infinite':
                index = 0
            elif loop_type == 'count':
                index = 1
            else:
                index = 2
            self.loop_type_combo.setCurrentIndex(index)
            self.loop_type_combo.currentIndexChanged.connect(self._on_fields_changed)
            layout.addWidget(self.loop_type_combo, 0, 1)
            
            # Repeat count
            layout.addWidget(QLabel("Repeat Count:"), 1, 0)
            self.count_spinbox = QSpinBox()
            self.count_spinbox.setRange(1, 1000)
            self.count_spinbox.setValue(action.get('count', 5))
            self.count_spinbox.valueChanged.connect(self._on_fields_changed)
            layout.addWidget(self.count_spinbox, 1, 1)
        else:
            # Loop target index
            layout.addWidget(QLabel("Jump To:"), 0, 0)
            self.target_spinbox = QSpinBox()
            self.target_spinbox.setRange(0, 100)
            self.target_spinbox.setValue(action.get('target_index', 0))
            self.target_spinbox.valueChanged.connect(self._on_fields_changed)
            layout.addWidget(self.target_spinbox, 0, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _on_fields_changed(self) -> None:
        """Handle field changes."""
        # Enable apply button
        self.apply_button.setEnabled(True)
    
    def _on_apply_clicked(self) -> None:
        """Handle apply button click."""
        if not self._current_action:
            return
        
        # Update action with field values
        action = self._current_action.copy()
        
        # Update common parameters
        action['type'] = self.action_type_combo.currentText().lower().replace(' ', '_')
        action['name'] = self.action_name_field.text()
        
        # Update specific parameters based on action type
        action_type = action['type']
        
        if action_type in ['click', 'right_click', 'double_click']:
            action['x'] = self.x_position.value()
            action['y'] = self.y_position.value()
            action['delay'] = self.delay.value()
            
        elif action_type == 'type_text':
            action['text'] = self.text.text()
            action['delay'] = self.delay.value()
            action['press_enter'] = self.press_enter.isChecked()
            
        elif action_type == 'press_key':
            action['key'] = self.key.currentText()
            action['shift'] = self.shift_mod.isChecked()
            action['ctrl'] = self.ctrl_mod.isChecked()
            action['alt'] = self.alt_mod.isChecked()
            action['repeat'] = self.repeat_count.value()
            action['delay'] = self.delay.value()
            
        elif action_type == 'wait':
            action['duration'] = self.duration.value()
            
        elif action_type == 'wait_for_template':
            action['template'] = self.template_name.currentText()
            action['confidence'] = self.confidence.value()
            action['timeout'] = self.timeout.value()
            
        elif action_type == 'wait_for_ocr_text':
            action['text'] = self.text.text()
            action['confidence'] = self.confidence.value()
            action['timeout'] = self.timeout.value()
            
        elif action_type == 'conditional':
            index = self.condition_type.currentIndex()
            if index == 0:
                action['condition_type'] = 'template_found'
            elif index == 1:
                action['condition_type'] = 'ocr_text_found'
            elif index == 2:
                action['condition_type'] = 'color_at_point'
            elif index == 3:
                action['condition_type'] = 'pixel_comparison'
            
            action['true_action'] = self.true_action.value()
            action['false_action'] = self.false_action.value()
            
        elif action_type == 'loop':
            index = self.loop_type_combo.currentIndex()
            if index == 0:
                action['loop_type'] = 'infinite'
            elif index == 1:
                action['loop_type'] = 'count'
            else:
                action['loop_type'] = 'while_condition'
            
            action['count'] = self.count_spinbox.value()
            
        elif action_type == 'end_loop':
            action['target_index'] = self.target_spinbox.value()
        
        # Emit action updated signal
        self.action_updated.emit(action)
        
        # Disable apply button
        self.apply_button.setEnabled(False)
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        # Restore original action
        if self._current_action:
            self.set_action(self._current_action)
            
            # Disable apply button
            self.apply_button.setEnabled(False)

    def _create_condition_specific_params(self, condition_type: str, action: Dict[str, Any]) -> None:
        """
        Create specific parameters UI for the selected condition type.
        
        Args:
            condition_type: Type of condition
            action: Action data dictionary
        """
        # Clear existing widgets
        self._clear_condition_params()
        
        if condition_type == 'template_found':
            # Template parameter
            template_layout = QHBoxLayout()
            template_layout.addWidget(QLabel(tr("Template:")))
            self.template_field = QLineEdit()
            self.template_field.setText(action.get('template', ''))
            self.template_field.textChanged.connect(self._on_fields_changed)
            template_layout.addWidget(self.template_field)
            self.condition_params_layout.addLayout(template_layout)
            
            # Confidence parameter
            confidence_layout = QHBoxLayout()
            confidence_layout.addWidget(QLabel(tr("Confidence:")))
            self.confidence_spinbox = QDoubleSpinBox()
            self.confidence_spinbox.setRange(0.1, 1.0)
            self.confidence_spinbox.setSingleStep(0.05)
            self.confidence_spinbox.setValue(action.get('confidence', 0.7))
            self.confidence_spinbox.valueChanged.connect(self._on_fields_changed)
            confidence_layout.addWidget(self.confidence_spinbox)
            self.condition_params_layout.addLayout(confidence_layout)
            
        elif condition_type == 'ocr_text_found':
            # Text parameter
            text_layout = QHBoxLayout()
            text_layout.addWidget(QLabel(tr("Text:")))
            self.text_field = QLineEdit()
            self.text_field.setText(action.get('text', ''))
            self.text_field.textChanged.connect(self._on_fields_changed)
            text_layout.addWidget(self.text_field)
            self.condition_params_layout.addLayout(text_layout)
            
            # Confidence parameter
            confidence_layout = QHBoxLayout()
            confidence_layout.addWidget(QLabel(tr("Confidence:")))
            self.confidence_spinbox = QDoubleSpinBox()
            self.confidence_spinbox.setRange(0.1, 1.0)
            self.confidence_spinbox.setSingleStep(0.05)
            self.confidence_spinbox.setValue(action.get('confidence', 0.7))
            self.confidence_spinbox.valueChanged.connect(self._on_fields_changed)
            confidence_layout.addWidget(self.confidence_spinbox)
            self.condition_params_layout.addLayout(confidence_layout)
            
        elif condition_type == 'color_at_point':
            # X,Y coordinates
            coord_layout = QHBoxLayout()
            coord_layout.addWidget(QLabel(tr("X:")))
            self.x_spinbox = QSpinBox()
            self.x_spinbox.setRange(0, 9999)
            self.x_spinbox.setValue(action.get('x', 0))
            self.x_spinbox.valueChanged.connect(self._on_fields_changed)
            coord_layout.addWidget(self.x_spinbox)
            
            coord_layout.addWidget(QLabel(tr("Y:")))
            self.y_spinbox = QSpinBox()
            self.y_spinbox.setRange(0, 9999)
            self.y_spinbox.setValue(action.get('y', 0))
            self.y_spinbox.valueChanged.connect(self._on_fields_changed)
            coord_layout.addWidget(self.y_spinbox)
            self.condition_params_layout.addLayout(coord_layout)
            
            # Color
            color_layout = QHBoxLayout()
            color_layout.addWidget(QLabel(tr("Color (R,G,B):")))
            
            self.r_spinbox = QSpinBox()
            self.r_spinbox.setRange(0, 255)
            self.r_spinbox.setValue(action.get('r', 0))
            self.r_spinbox.valueChanged.connect(self._on_fields_changed)
            color_layout.addWidget(self.r_spinbox)
            
            self.g_spinbox = QSpinBox()
            self.g_spinbox.setRange(0, 255)
            self.g_spinbox.setValue(action.get('g', 0))
            self.g_spinbox.valueChanged.connect(self._on_fields_changed)
            color_layout.addWidget(self.g_spinbox)
            
            self.b_spinbox = QSpinBox()
            self.b_spinbox.setRange(0, 255)
            self.b_spinbox.setValue(action.get('b', 0))
            self.b_spinbox.valueChanged.connect(self._on_fields_changed)
            color_layout.addWidget(self.b_spinbox)
            
            self.condition_params_layout.addLayout(color_layout)
            
            # Tolerance
            tolerance_layout = QHBoxLayout()
            tolerance_layout.addWidget(QLabel(tr("Tolerance:")))
            self.tolerance_spinbox = QSpinBox()
            self.tolerance_spinbox.setRange(0, 255)
            self.tolerance_spinbox.setValue(action.get('tolerance', 10))
            self.tolerance_spinbox.valueChanged.connect(self._on_fields_changed)
            tolerance_layout.addWidget(self.tolerance_spinbox)
            self.condition_params_layout.addLayout(tolerance_layout)
            
        elif condition_type == 'pixel_comparison':
            # First point
            point1_layout = QHBoxLayout()
            point1_layout.addWidget(QLabel(tr("Point 1 (X,Y):")))
            self.x1_spinbox = QSpinBox()
            self.x1_spinbox.setRange(0, 9999)
            self.x1_spinbox.setValue(action.get('x1', 0))
            self.x1_spinbox.valueChanged.connect(self._on_fields_changed)
            point1_layout.addWidget(self.x1_spinbox)
            
            point1_layout.addWidget(QLabel(tr("Y:")))
            self.y1_spinbox = QSpinBox()
            self.y1_spinbox.setRange(0, 9999)
            self.y1_spinbox.setValue(action.get('y1', 0))
            self.y1_spinbox.valueChanged.connect(self._on_fields_changed)
            point1_layout.addWidget(self.y1_spinbox)
            self.condition_params_layout.addLayout(point1_layout)
            
            # Second point
            point2_layout = QHBoxLayout()
            point2_layout.addWidget(QLabel(tr("Point 2 (X,Y):")))
            self.x2_spinbox = QSpinBox()
            self.x2_spinbox.setRange(0, 9999)
            self.x2_spinbox.setValue(action.get('x2', 0))
            self.x2_spinbox.valueChanged.connect(self._on_fields_changed)
            point2_layout.addWidget(self.x2_spinbox)
            
            point2_layout.addWidget(QLabel(tr("Y:")))
            self.y2_spinbox = QSpinBox()
            self.y2_spinbox.setRange(0, 9999)
            self.y2_spinbox.setValue(action.get('y2', 0))
            self.y2_spinbox.valueChanged.connect(self._on_fields_changed)
            point2_layout.addWidget(self.y2_spinbox)
            self.condition_params_layout.addLayout(point2_layout)
            
            # Tolerance
            tolerance_layout = QHBoxLayout()
            tolerance_layout.addWidget(QLabel(tr("Tolerance:")))
            self.tolerance_spinbox = QSpinBox()
            self.tolerance_spinbox.setRange(0, 255)
            self.tolerance_spinbox.setValue(action.get('tolerance', 10))
            self.tolerance_spinbox.valueChanged.connect(self._on_fields_changed)
            tolerance_layout.addWidget(self.tolerance_spinbox)
            self.condition_params_layout.addLayout(tolerance_layout)

    def _clear_condition_params(self) -> None:
        """Clear condition-specific parameters widgets."""
        while self.condition_params_layout.count():
            item = self.condition_params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Clear the layout
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def _on_condition_type_changed(self, index: int) -> None:
        """
        Handle condition type change.
        
        Args:
            index: Selected index
        """
        if self._current_action is None:
            return
        
        condition_types = ['template_found', 'ocr_text_found', 'color_at_point', 'pixel_comparison']
        condition_type = condition_types[index]
        
        # Update condition-specific parameters
        self._create_condition_specific_params(condition_type, self._current_action)
        
        # Update current action type
        self._current_action['condition_type'] = condition_type
        
        # Enable apply button
        self._on_fields_changed()


class AutomationTab(QWidget):
    """
    Automation Tab for creating and running automation sequences.
    
    This tab provides:
    - Management of automation sequences
    - Action editing and configuration
    - Execution controls
    - Simulation capabilities
    """
    
    def __init__(
        self,
        automation_service: AutomationServiceInterface,
        detection_service: DetectionServiceInterface,
        window_service: WindowServiceInterface
    ):
        """
        Initialize the automation tab.
        
        Args:
            automation_service: Service for automation execution
            detection_service: Service for detection operations
            window_service: Service for window operations
        """
        super().__init__()
        
        # Store services
        self.automation_service = automation_service
        self.detection_service = detection_service
        self.window_service = window_service
        
        # Initialize state
        self._current_sequence = {"name": tr("New Sequence"), "actions": []}
        self._modified = False
        self._running = False
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Create default sequence
        self._create_default_sequence()
        
        logger.info("Automation tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a splitter for sequence selection and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create left panel for sequence selection and actions
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Sequence group
        sequence_group = QGroupBox(tr("Sequence"))
        sequence_layout = QVBoxLayout(sequence_group)
        
        # Sequence selection and file operations
        sequence_header_layout = QHBoxLayout()
        sequence_header_layout.addWidget(QLabel(tr("Sequence:")))
        
        self.sequence_combo = QComboBox()
        self.sequence_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.sequence_combo.currentIndexChanged.connect(self._on_sequence_changed)
        sequence_header_layout.addWidget(self.sequence_combo)
        
        sequence_layout.addLayout(sequence_header_layout)
        
        # Sequence file operations
        file_layout = QHBoxLayout()
        
        self.new_button = QPushButton(tr("New"))
        self.new_button.clicked.connect(self._on_new_clicked)
        file_layout.addWidget(self.new_button)
        
        self.open_button = QPushButton(tr("Open"))
        self.open_button.clicked.connect(self._on_open_clicked)
        file_layout.addWidget(self.open_button)
        
        self.save_button = QPushButton(tr("Save"))
        self.save_button.clicked.connect(self._on_save_clicked)
        file_layout.addWidget(self.save_button)
        
        sequence_layout.addLayout(file_layout)
        
        # Add sequence group to left panel
        left_layout.addWidget(sequence_group)
        
        # Create actions group
        actions_group = QGroupBox(tr("Sequence Actions"))
        actions_layout = QVBoxLayout(actions_group)
        
        # Action list
        self.action_list = QListWidget()
        self.action_list.currentItemChanged.connect(self._on_selection_changed)
        actions_layout.addWidget(self.action_list)
        
        # Action management buttons
        action_buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton(tr("Add Action"))
        self.add_button.clicked.connect(self._on_add_clicked)
        action_buttons_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton(tr("Remove"))
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setEnabled(False)
        action_buttons_layout.addWidget(self.remove_button)
        
        actions_layout.addLayout(action_buttons_layout)
        
        # Movement buttons
        move_buttons_layout = QHBoxLayout()
        
        self.move_up_button = QPushButton(tr("Move Up"))
        self.move_up_button.clicked.connect(self._on_move_up_clicked)
        self.move_up_button.setEnabled(False)
        self.action_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Action editor
        self.action_editor.action_updated.connect(self._on_action_updated)
        
        # Loop checkbox
        self.loop_check.toggled.connect(self._on_loop_toggled)
        
        # Connect position list to action editor
        self.position_list.position_selected.connect(self.action_editor.set_position)
    
    def _create_default_sequence(self) -> None:
        """Create a default empty sequence."""
        self._current_sequence = {"name": tr("New Sequence"), "actions": []}
        self._update_action_list()
        self._update_sequence_list()
        self._modified = False
    
    def _update_action_list(self) -> None:
        """Update the action list with current actions."""
        # Clear list
        self.action_list.clear()
        
        # Add each action
        for i, action in enumerate(self._current_sequence["actions"]):
            # Create item text
            action_type = action.get('type', 'unknown')
            action_name = action.get('name', '')
            
            if action_name:
                item_text = f"{i + 1}. {action_name} ({action_type})"
            else:
                item_text = f"{i + 1}. {action_type}"
            
            # Create item
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store action index
            
            # Set background color based on action type
            if action_type in ['click', 'right_click', 'double_click']:
                item.setBackground(Qt.GlobalColor.lightGray)
            elif action_type in ['type_text', 'press_key']:
                item.setBackground(Qt.GlobalColor.cyan)
            elif action_type in ['wait', 'wait_for_template', 'wait_for_ocr_text']:
                item.setBackground(Qt.GlobalColor.yellow)
            elif action_type == 'conditional':
                item.setBackground(Qt.GlobalColor.magenta)
            elif action_type in ['loop', 'end_loop']:
                item.setBackground(Qt.GlobalColor.green)
            
            # Highlight current action during execution
            if i == self._current_action_index and self._running:
                item.setForeground(Qt.GlobalColor.red)
                item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            
            # Add to list
            self.action_list.addItem(item)
    
    def _on_sequence_changed(self) -> None:
        """Handle sequence change."""
        # Get selected sequence
        selected_sequence = self.sequence_combo.currentText()
        
        # Load sequence
        self._load_sequence(selected_sequence)
    
    def _on_new_clicked(self) -> None:
        """Handle new button click."""
        # Check if sequence is modified
        if self._current_sequence["actions"]:
            # Ask for confirmation
            result = QMessageBox.question(
                self,
                "New Sequence",
                "Create a new sequence? Any unsaved changes will be lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
        
        # Create new sequence
        self._create_default_sequence()
    
    def _on_open_clicked(self) -> None:
        """Handle open button click."""
        # Check if sequence is modified
        if self._current_sequence["actions"]:
            # Ask for confirmation
            result = QMessageBox.question(
                self,
                "Open Sequence",
                "Open a sequence? Any unsaved changes will be lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
        
        # Get sequence directory
        sequence_dir = Path("./scout/resources/sequences")
        if not sequence_dir.exists():
            sequence_dir.mkdir(parents=True, exist_ok=True)
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Sequence",
            str(sequence_dir),
            "Sequence Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Load sequence
        try:
            with open(file_path, 'r') as f:
                sequence = json.load(f)
            
            # Validate sequence
            if not isinstance(sequence, list):
                raise ValueError("Invalid sequence format")
            
            # Update sequence
            self._current_sequence["actions"] = sequence
            self._current_sequence_path = file_path
            self._update_action_list()
            
            # Update status
            self.status_label.setText(f"Loaded sequence from {file_path}")
            
            logger.info(f"Loaded sequence from {file_path}")
            
        except Exception as e:
            # Show error
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load sequence: {str(e)}"
            )
            
            logger.error(f"Failed to load sequence: {str(e)}")
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        if not self._current_sequence["actions"]:
            # Nothing to save
            return
        
        # Get sequence directory
        sequence_dir = Path("./scout/resources/sequences")
        if not sequence_dir.exists():
            sequence_dir.mkdir(parents=True, exist_ok=True)
        
        # If path is not set, ask for a new path
        if not self._current_sequence_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Sequence",
                str(sequence_dir),
                "Sequence Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            self._current_sequence_path = file_path
        
        # Save sequence
        try:
            with open(self._current_sequence_path, 'w') as f:
                json.dump(self._current_sequence["actions"], f, indent=2)
            
            # Update status
            self.status_label.setText(f"Saved sequence to {self._current_sequence_path}")
            
            logger.info(f"Saved sequence to {self._current_sequence_path}")
            
        except Exception as e:
            # Show error
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save sequence: {str(e)}"
            )
            
            logger.error(f"Failed to save sequence: {str(e)}")
    
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        if not self._current_sequence["actions"]:
            # Nothing to run
            QMessageBox.information(
                self,
                "Run Sequence",
                "No actions to run. Please add actions to the sequence."
            )
            return
        
        # Update button states
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Set running state
        self._running = True
        self._current_action_index = -1
        
        # Start execution
        self._execute_next_action()
    
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        # Update button states
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Set running state
        self._running = False
        self._current_action_index = -1
        
        # Update action list
        self._update_action_list()
        
        # Update status
        self.status_label.setText("Sequence execution stopped")
        
        logger.info("Sequence execution stopped")
    
    def _execute_next_action(self) -> None:
        """Execute the next action in the sequence."""
        if not self._running:
            return
        
        # Increment action index
        self._current_action_index += 1
        
        # Check if we reached the end
        if self._current_action_index >= len(self._current_sequence["actions"]):
            # Execution complete
            self._on_stop_clicked()
            
            # Update status
            self.status_label.setText("Sequence execution completed")
            
            # Show message
            QMessageBox.information(
                self,
                "Execution Complete",
                "Sequence execution completed successfully."
            )
            
            logger.info("Sequence execution completed")
            return
        
        # Update action list to highlight current action
        self._update_action_list()
        
        # Get current action
        action = self._current_sequence["actions"][self._current_action_index]
        
        # Update status
        action_name = action.get('name', action.get('type', 'unknown'))
        self.status_label.setText(f"Executing: {action_name}")
        
        logger.info(f"Executing action: {action_name}")
        
        # TODO: Implement actual execution using automation service
        # For now, just wait and move to next action
        QTimer.singleShot(1000, self._execute_next_action)
    
    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        # Create default action
        action = {
            'type': 'click',
            'name': f'Action {len(self._current_sequence["actions"]) + 1}',
            'x': 0,
            'y': 0,
            'relative': False,
            'delay_after': 0
        }
        
        # Add to sequence
        self._current_sequence["actions"].append(action)
        
        # Update list
        self._update_action_list()
        
        # Select new action
        self.action_list.setCurrentRow(len(self._current_sequence["actions"]) - 1)
    
    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        # Get selected items
        selected_items = self.action_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Ask for confirmation
        result = QMessageBox.question(
            self,
            "Remove Action",
            f"Remove action at position {index + 1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Remove action
        if 0 <= index < len(self._current_sequence["actions"]):
            del self._current_sequence["actions"][index]
            
            # Update list
            self._update_action_list()
            
            # Clear selection if list is empty
            if not self._current_sequence["actions"]:
                self.action_editor.set_action(None)
    
    def _on_move_up_clicked(self) -> None:
        """Handle move up button click."""
        # Get selected items
        selected_items = self.action_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Check if movable
        if index <= 0 or index >= len(self._current_sequence["actions"]):
            return
        
        # Swap actions
        self._current_sequence["actions"][index], self._current_sequence["actions"][index - 1] = \
            self._current_sequence["actions"][index - 1], self._current_sequence["actions"][index]
        
        # Update list
        self._update_action_list()
        
        # Select moved action
        self.action_list.setCurrentRow(index - 1)
    
    def _on_move_down_clicked(self) -> None:
        """Handle move down button click."""
        # Get selected items
        selected_items = self.action_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Check if movable
        if index < 0 or index >= len(self._current_sequence["actions"]) - 1:
            return
        
        # Swap actions
        self._current_sequence["actions"][index], self._current_sequence["actions"][index + 1] = \
            self._current_sequence["actions"][index + 1], self._current_sequence["actions"][index]
        
        # Update list
        self._update_action_list()
        
        # Select moved action
        self.action_list.setCurrentRow(index + 1)
    
    def _on_action_updated(self, action: Dict[str, Any]) -> None:
        """
        Handle action update from editor.
        
        Args:
            action: Updated action data
        """
        # Get selected items
        selected_items = self.action_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Update action in sequence
        if 0 <= index < len(self._current_sequence["actions"]):
            self._current_sequence["actions"][index] = action
            
            # Update list
            self._update_action_list()
            
            # Keep selection
            self.action_list.setCurrentRow(index)
    
    def _on_loop_toggled(self, checked: bool) -> None:
        """Handle loop checkbox toggled."""
        # Enable/disable iterations spinbox
        self.iterations_spin.setEnabled(checked)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in action list."""
        # Update button states
        self.remove_action_btn.setEnabled(len(self.action_list.selectedItems()) > 0)
        self.move_up_btn.setEnabled(len(self.action_list.selectedItems()) > 0 and
                                    self.action_list.selectedItems()[0].data(Qt.ItemDataRole.UserRole) > 0)
        self.move_down_btn.setEnabled(len(self.action_list.selectedItems()) > 0 and
                                     self.action_list.selectedItems()[0].data(Qt.ItemDataRole.UserRole) <
                                     len(self._current_sequence["actions"]) - 1)
        
        # Update action editor
        if self.action_list.selectedItems():
            index = self.action_list.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            if 0 <= index < len(self._current_sequence["actions"]):
                self.action_editor.set_action(self._current_sequence["actions"][index])
            else:
                self.action_editor.set_action(None)
        else:
            self.action_editor.set_action(None)
    
    def _on_sequence_changed(self) -> None:
        """Handle sequence change."""
        # Get selected sequence
        selected_sequence = self.sequence_combo.currentText()
        
        # Load sequence
        self._load_sequence(selected_sequence)
    
    def _load_sequence(self, sequence_name: str) -> None:
        """Load a sequence from the sequence directory."""
        # Construct full path to sequence file
        sequence_dir = Path("./scout/resources/sequences")
        sequence_path = sequence_dir / f"{sequence_name}.json"
        
        # Check if sequence file exists
        if not sequence_path.exists():
            self.sequence_list.setCurrentRow(index) 