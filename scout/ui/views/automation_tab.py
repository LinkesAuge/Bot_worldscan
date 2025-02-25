"""
Automation Tab

This module provides a tab interface for configuring and executing automation sequences.
It allows users to create, load, edit, and execute sequences of actions to automate
interaction with the target application.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox
)
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer

from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.ui.widgets.detection_result_widget import DetectionResultWidget

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
        self.title_label = QLabel("Edit Action")
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
        common_group = QGroupBox("Common Parameters")
        common_layout = QGridLayout(common_group)
        
        # Action type label & combo
        common_layout.addWidget(QLabel("Action Type:"), 0, 0)
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems([
            "Click", "Right Click", "Double Click",
            "Type Text", "Press Key", "Wait",
            "Wait for Template", "Wait for OCR Text",
            "Conditional", "Loop", "End Loop"
        ])
        common_layout.addWidget(self.action_type_combo, 0, 1)
        
        # Action name label & field
        common_layout.addWidget(QLabel("Action Name:"), 1, 0)
        self.action_name_field = QLineEdit()
        common_layout.addWidget(self.action_name_field, 1, 1)
        
        # Add common group to layout
        self.params_layout.addWidget(common_group)
        
        # Create specific parameters container
        self.specific_params_widget = QWidget()
        self.specific_params_layout = QVBoxLayout(self.specific_params_widget)
        self.params_layout.addWidget(self.specific_params_widget)
        
        # Placeholder for action-specific parameters
        self.placeholder_label = QLabel("Select an action type to configure parameters")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.specific_params_layout.addWidget(self.placeholder_label)
        
        # Create buttons
        buttons_layout = QHBoxLayout()
        
        # Apply button
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.setEnabled(False)
        buttons_layout.addWidget(self.apply_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
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
        group = QGroupBox("Click Parameters")
        layout = QGridLayout(group)
        
        # X position
        layout.addWidget(QLabel("X Position:"), 0, 0)
        self.x_position = QSpinBox()
        self.x_position.setRange(0, 9999)
        self.x_position.setValue(action.get('x', 0))
        self.x_position.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.x_position, 0, 1)
        
        # Y position
        layout.addWidget(QLabel("Y Position:"), 1, 0)
        self.y_position = QSpinBox()
        self.y_position.setRange(0, 9999)
        self.y_position.setValue(action.get('y', 0))
        self.y_position.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.y_position, 1, 1)
        
        # Use relative position
        layout.addWidget(QLabel("Relative to Target:"), 2, 0)
        self.relative_checkbox = QCheckBox()
        self.relative_checkbox.setChecked(action.get('relative', False))
        self.relative_checkbox.stateChanged.connect(self._on_fields_changed)
        layout.addWidget(self.relative_checkbox, 2, 1)
        
        # Add optional delay
        layout.addWidget(QLabel("Delay After (ms):"), 3, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 10000)
        self.delay_spinbox.setValue(action.get('delay_after', 0))
        self.delay_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.delay_spinbox, 3, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _create_type_text_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for type text actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox("Type Text Parameters")
        layout = QGridLayout(group)
        
        # Text to type
        layout.addWidget(QLabel("Text:"), 0, 0)
        self.text_field = QLineEdit()
        self.text_field.setText(action.get('text', ''))
        self.text_field.textChanged.connect(self._on_fields_changed)
        layout.addWidget(self.text_field, 0, 1)
        
        # Typing speed
        layout.addWidget(QLabel("Typing Speed:"), 1, 0)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Fast", "Normal", "Slow"])
        speed = action.get('speed', 'normal')
        index = self.speed_combo.findText(speed.capitalize())
        if index >= 0:
            self.speed_combo.setCurrentIndex(index)
        self.speed_combo.currentIndexChanged.connect(self._on_fields_changed)
        layout.addWidget(self.speed_combo, 1, 1)
        
        # Add optional delay
        layout.addWidget(QLabel("Delay After (ms):"), 2, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 10000)
        self.delay_spinbox.setValue(action.get('delay_after', 0))
        self.delay_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.delay_spinbox, 2, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _create_press_key_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for press key actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox("Press Key Parameters")
        layout = QGridLayout(group)
        
        # Key to press
        layout.addWidget(QLabel("Key:"), 0, 0)
        self.key_combo = QComboBox()
        self.key_combo.addItems([
            "Enter", "Escape", "Tab", "Space", "Backspace", "Delete",
            "Home", "End", "Page Up", "Page Down",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Arrow Up", "Arrow Down", "Arrow Left", "Arrow Right"
        ])
        key = action.get('key', 'Enter')
        index = self.key_combo.findText(key)
        if index >= 0:
            self.key_combo.setCurrentIndex(index)
        self.key_combo.currentIndexChanged.connect(self._on_fields_changed)
        layout.addWidget(self.key_combo, 0, 1)
        
        # Modifiers
        layout.addWidget(QLabel("Ctrl:"), 1, 0)
        self.ctrl_checkbox = QCheckBox()
        self.ctrl_checkbox.setChecked(action.get('ctrl', False))
        self.ctrl_checkbox.stateChanged.connect(self._on_fields_changed)
        layout.addWidget(self.ctrl_checkbox, 1, 1)
        
        layout.addWidget(QLabel("Alt:"), 2, 0)
        self.alt_checkbox = QCheckBox()
        self.alt_checkbox.setChecked(action.get('alt', False))
        self.alt_checkbox.stateChanged.connect(self._on_fields_changed)
        layout.addWidget(self.alt_checkbox, 2, 1)
        
        layout.addWidget(QLabel("Shift:"), 3, 0)
        self.shift_checkbox = QCheckBox()
        self.shift_checkbox.setChecked(action.get('shift', False))
        self.shift_checkbox.stateChanged.connect(self._on_fields_changed)
        layout.addWidget(self.shift_checkbox, 3, 1)
        
        # Add optional delay
        layout.addWidget(QLabel("Delay After (ms):"), 4, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 10000)
        self.delay_spinbox.setValue(action.get('delay_after', 0))
        self.delay_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.delay_spinbox, 4, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _create_wait_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for wait actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox("Wait Parameters")
        layout = QGridLayout(group)
        
        # Duration
        layout.addWidget(QLabel("Duration (ms):"), 0, 0)
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(0, 60000)
        self.duration_spinbox.setValue(action.get('duration', 1000))
        self.duration_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.duration_spinbox, 0, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _create_wait_for_params(self, action: Dict[str, Any], action_type: str) -> None:
        """
        Create parameters UI for wait for template/OCR actions.
        
        Args:
            action: Action data dictionary
            action_type: Action type string
        """
        # Create group box
        title = "Wait for Template" if action_type == "wait_for_template" else "Wait for OCR Text"
        group = QGroupBox(title)
        layout = QGridLayout(group)
        
        if action_type == "wait_for_template":
            # Template name
            layout.addWidget(QLabel("Template:"), 0, 0)
            self.template_field = QLineEdit()
            self.template_field.setText(action.get('template', ''))
            self.template_field.textChanged.connect(self._on_fields_changed)
            layout.addWidget(self.template_field, 0, 1)
        else:
            # OCR text
            layout.addWidget(QLabel("Text:"), 0, 0)
            self.text_field = QLineEdit()
            self.text_field.setText(action.get('text', ''))
            self.text_field.textChanged.connect(self._on_fields_changed)
            layout.addWidget(self.text_field, 0, 1)
        
        # Confidence threshold
        layout.addWidget(QLabel("Confidence:"), 1, 0)
        self.confidence_spinbox = QSpinBox()
        self.confidence_spinbox.setRange(1, 100)
        self.confidence_spinbox.setValue(int(action.get('confidence', 0.7) * 100))
        self.confidence_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.confidence_spinbox, 1, 1)
        
        # Timeout
        layout.addWidget(QLabel("Timeout (ms):"), 2, 0)
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(0, 60000)
        self.timeout_spinbox.setValue(action.get('timeout', 5000))
        self.timeout_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.timeout_spinbox, 2, 1)
        
        # Check interval
        layout.addWidget(QLabel("Check Interval (ms):"), 3, 0)
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(100, 5000)
        self.interval_spinbox.setValue(action.get('interval', 500))
        self.interval_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.interval_spinbox, 3, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
    def _create_conditional_params(self, action: Dict[str, Any]) -> None:
        """
        Create parameters UI for conditional actions.
        
        Args:
            action: Action data dictionary
        """
        # Create group box
        group = QGroupBox("Conditional Parameters")
        layout = QGridLayout(group)
        
        # Condition type
        layout.addWidget(QLabel("Condition Type:"), 0, 0)
        self.condition_combo = QComboBox()
        self.condition_combo.addItems([
            "Template Found", "OCR Text Found", "Not Found"
        ])
        condition = action.get('condition', 'template_found')
        if condition == 'template_found':
            index = 0
        elif condition == 'ocr_text_found':
            index = 1
        else:
            index = 2
        self.condition_combo.setCurrentIndex(index)
        self.condition_combo.currentIndexChanged.connect(self._on_fields_changed)
        layout.addWidget(self.condition_combo, 0, 1)
        
        # Target (template or text)
        layout.addWidget(QLabel("Target:"), 1, 0)
        self.target_field = QLineEdit()
        self.target_field.setText(action.get('target', ''))
        self.target_field.textChanged.connect(self._on_fields_changed)
        layout.addWidget(self.target_field, 1, 1)
        
        # Confidence threshold
        layout.addWidget(QLabel("Confidence:"), 2, 0)
        self.confidence_spinbox = QSpinBox()
        self.confidence_spinbox.setRange(1, 100)
        self.confidence_spinbox.setValue(int(action.get('confidence', 0.7) * 100))
        self.confidence_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.confidence_spinbox, 2, 1)
        
        # Then action index
        layout.addWidget(QLabel("Then Jump To:"), 3, 0)
        self.then_spinbox = QSpinBox()
        self.then_spinbox.setRange(0, 100)
        self.then_spinbox.setValue(action.get('then_index', 0))
        self.then_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.then_spinbox, 3, 1)
        
        # Else action index
        layout.addWidget(QLabel("Else Jump To:"), 4, 0)
        self.else_spinbox = QSpinBox()
        self.else_spinbox.setRange(0, 100)
        self.else_spinbox.setValue(action.get('else_index', 0))
        self.else_spinbox.valueChanged.connect(self._on_fields_changed)
        layout.addWidget(self.else_spinbox, 4, 1)
        
        # Add group to layout
        self.specific_params_layout.addWidget(group)
    
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
            action['relative'] = self.relative_checkbox.isChecked()
            action['delay_after'] = self.delay_spinbox.value()
            
        elif action_type == 'type_text':
            action['text'] = self.text_field.text()
            action['speed'] = self.speed_combo.currentText().lower()
            action['delay_after'] = self.delay_spinbox.value()
            
        elif action_type == 'press_key':
            action['key'] = self.key_combo.currentText()
            action['ctrl'] = self.ctrl_checkbox.isChecked()
            action['alt'] = self.alt_checkbox.isChecked()
            action['shift'] = self.shift_checkbox.isChecked()
            action['delay_after'] = self.delay_spinbox.value()
            
        elif action_type == 'wait':
            action['duration'] = self.duration_spinbox.value()
            
        elif action_type == 'wait_for_template':
            action['template'] = self.template_field.text()
            action['confidence'] = self.confidence_spinbox.value() / 100.0
            action['timeout'] = self.timeout_spinbox.value()
            action['interval'] = self.interval_spinbox.value()
            
        elif action_type == 'wait_for_ocr_text':
            action['text'] = self.text_field.text()
            action['confidence'] = self.confidence_spinbox.value() / 100.0
            action['timeout'] = self.timeout_spinbox.value()
            action['interval'] = self.interval_spinbox.value()
            
        elif action_type == 'conditional':
            index = self.condition_combo.currentIndex()
            if index == 0:
                action['condition'] = 'template_found'
            elif index == 1:
                action['condition'] = 'ocr_text_found'
            else:
                action['condition'] = 'not_found'
            
            action['target'] = self.target_field.text()
            action['confidence'] = self.confidence_spinbox.value() / 100.0
            action['then_index'] = self.then_spinbox.value()
            action['else_index'] = self.else_spinbox.value()
            
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


class AutomationTab(QWidget):
    """
    Tab for configuring and executing automation sequences.
    
    This tab provides an interface for creating, editing, and executing
    sequences of automation actions such as clicks, key presses, text input,
    and conditional logic.
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
            automation_service: Service for automation operations
            detection_service: Service for detection operations
            window_service: Service for window management
        """
        super().__init__()
        
        # Store services
        self.automation_service = automation_service
        self.detection_service = detection_service
        self.window_service = window_service
        
        # Initialize state
        self._current_sequence = []
        self._current_sequence_path = None
        self._is_running = False
        self._current_action_index = -1
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Load default actions
        self._create_default_sequence()
        
        logger.info("Automation tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        
        # Toolbar actions
        # TODO: Replace with actual icons
        self.new_action = QAction("New", self)
        self.open_action = QAction("Open", self)
        self.save_action = QAction("Save", self)
        self.run_action = QAction("Run", self)
        self.stop_action = QAction("Stop", self)
        
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_action)
        toolbar.addAction(self.stop_action)
        
        main_layout.addWidget(toolbar)
        
        # Create splitter for sequence editor and action editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Sequence list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Sequence list
        left_layout.addWidget(QLabel("Automation Sequence"))
        
        self.sequence_list = QListWidget()
        left_layout.addWidget(self.sequence_list)
        
        # Sequence actions
        sequence_actions = QHBoxLayout()
        
        self.add_btn = QPushButton("Add")
        sequence_actions.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setEnabled(False)
        sequence_actions.addWidget(self.edit_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setEnabled(False)
        sequence_actions.addWidget(self.remove_btn)
        
        left_layout.addLayout(sequence_actions)
        
        # Move actions
        move_actions = QHBoxLayout()
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.setEnabled(False)
        move_actions.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.setEnabled(False)
        move_actions.addWidget(self.move_down_btn)
        
        left_layout.addLayout(move_actions)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel - Action editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Action editor
        self.action_editor = AutomationActionEditor()
        right_layout.addWidget(self.action_editor)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (40% list, 60% editor)
        splitter.setSizes([400, 600])
        
        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Toolbar actions
        self.new_action.triggered.connect(self._on_new_clicked)
        self.open_action.triggered.connect(self._on_open_clicked)
        self.save_action.triggered.connect(self._on_save_clicked)
        self.run_action.triggered.connect(self._on_run_clicked)
        self.stop_action.triggered.connect(self._on_stop_clicked)
        
        # Sequence actions
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.move_up_btn.clicked.connect(self._on_move_up_clicked)
        self.move_down_btn.clicked.connect(self._on_move_down_clicked)
        
        # Sequence list selection
        self.sequence_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Action editor
        self.action_editor.action_updated.connect(self._on_action_updated)
    
    def _create_default_sequence(self) -> None:
        """Create a default empty sequence."""
        self._current_sequence = []
        self._current_sequence_path = None
        self._update_sequence_list()
        self.status_label.setText("New sequence created")
    
    def _update_sequence_list(self) -> None:
        """Update the sequence list with current actions."""
        # Clear list
        self.sequence_list.clear()
        
        # Add each action
        for i, action in enumerate(self._current_sequence):
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
            if i == self._current_action_index and self._is_running:
                item.setForeground(Qt.GlobalColor.red)
                item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            
            # Add to list
            self.sequence_list.addItem(item)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in sequence list."""
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
        # Update button states
        self.edit_btn.setEnabled(len(selected_items) > 0)
        self.remove_btn.setEnabled(len(selected_items) > 0)
        self.move_up_btn.setEnabled(len(selected_items) > 0 and
                                    selected_items[0].data(Qt.ItemDataRole.UserRole) > 0)
        self.move_down_btn.setEnabled(len(selected_items) > 0 and
                                     selected_items[0].data(Qt.ItemDataRole.UserRole) <
                                     len(self._current_sequence) - 1)
        
        # Update action editor
        if selected_items:
            index = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if 0 <= index < len(self._current_sequence):
                self.action_editor.set_action(self._current_sequence[index])
            else:
                self.action_editor.set_action(None)
        else:
            self.action_editor.set_action(None)
    
    def _on_new_clicked(self) -> None:
        """Handle new button click."""
        # Check if sequence is modified
        if self._current_sequence:
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
        if self._current_sequence:
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
            self._current_sequence = sequence
            self._current_sequence_path = file_path
            self._update_sequence_list()
            
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
        if not self._current_sequence:
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
                json.dump(self._current_sequence, f, indent=2)
            
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
        if not self._current_sequence:
            # Nothing to run
            QMessageBox.information(
                self,
                "Run Sequence",
                "No actions to run. Please add actions to the sequence."
            )
            return
        
        # Update button states
        self.run_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        
        # Set running state
        self._is_running = True
        self._current_action_index = -1
        
        # Start execution
        self._execute_next_action()
    
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        # Update button states
        self.run_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        
        # Set running state
        self._is_running = False
        self._current_action_index = -1
        
        # Update sequence list
        self._update_sequence_list()
        
        # Update status
        self.status_label.setText("Sequence execution stopped")
        
        logger.info("Sequence execution stopped")
    
    def _execute_next_action(self) -> None:
        """Execute the next action in the sequence."""
        if not self._is_running:
            return
        
        # Increment action index
        self._current_action_index += 1
        
        # Check if we reached the end
        if self._current_action_index >= len(self._current_sequence):
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
        
        # Update sequence list to highlight current action
        self._update_sequence_list()
        
        # Get current action
        action = self._current_sequence[self._current_action_index]
        
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
            'name': f'Action {len(self._current_sequence) + 1}',
            'x': 0,
            'y': 0,
            'relative': False,
            'delay_after': 0
        }
        
        # Add to sequence
        self._current_sequence.append(action)
        
        # Update list
        self._update_sequence_list()
        
        # Select new action
        self.sequence_list.setCurrentRow(len(self._current_sequence) - 1)
    
    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Select action in editor
        if 0 <= index < len(self._current_sequence):
            self.action_editor.set_action(self._current_sequence[index])
    
    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
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
        if 0 <= index < len(self._current_sequence):
            del self._current_sequence[index]
            
            # Update list
            self._update_sequence_list()
            
            # Clear selection if list is empty
            if not self._current_sequence:
                self.action_editor.set_action(None)
    
    def _on_move_up_clicked(self) -> None:
        """Handle move up button click."""
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Check if movable
        if index <= 0 or index >= len(self._current_sequence):
            return
        
        # Swap actions
        self._current_sequence[index], self._current_sequence[index - 1] = \
            self._current_sequence[index - 1], self._current_sequence[index]
        
        # Update list
        self._update_sequence_list()
        
        # Select moved action
        self.sequence_list.setCurrentRow(index - 1)
    
    def _on_move_down_clicked(self) -> None:
        """Handle move down button click."""
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Check if movable
        if index < 0 or index >= len(self._current_sequence) - 1:
            return
        
        # Swap actions
        self._current_sequence[index], self._current_sequence[index + 1] = \
            self._current_sequence[index + 1], self._current_sequence[index]
        
        # Update list
        self._update_sequence_list()
        
        # Select moved action
        self.sequence_list.setCurrentRow(index + 1)
    
    def _on_action_updated(self, action: Dict[str, Any]) -> None:
        """
        Handle action update from editor.
        
        Args:
            action: Updated action data
        """
        # Get selected items
        selected_items = self.sequence_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get action index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Update action in sequence
        if 0 <= index < len(self._current_sequence):
            self._current_sequence[index] = action
            
            # Update list
            self._update_sequence_list()
            
            # Keep selection
            self.sequence_list.setCurrentRow(index) 