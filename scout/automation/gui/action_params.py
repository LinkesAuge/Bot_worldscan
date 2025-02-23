"""
Action Parameter Widgets

This module provides specialized widgets for configuring different types of action parameters.
Each action type has its own parameter widget that shows relevant configuration options.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from pathlib import Path
from scout.automation.actions import (
    ActionType, ActionParamsCommon, ClickParams, DragParams,
    TypeParams, WaitParams, OCRWaitParams
)
from scout.automation.core import AutomationPosition
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class BaseParamsWidget(QWidget):
    """Base class for all parameter widgets."""
    
    params_changed = pyqtSignal()  # Emitted when parameters are changed
    
    def __init__(self):
        """Initialize the base parameter widget."""
        super().__init__()
        self._creating_widgets = False
        
    def get_params(self) -> ActionParamsCommon:
        """Get the current parameter values."""
        raise NotImplementedError()
        
    def set_params(self, params: ActionParamsCommon) -> None:
        """Set the parameter values."""
        raise NotImplementedError()

class ClickParamsWidget(BaseParamsWidget):
    """Widget for configuring click action parameters."""
    
    def __init__(self):
        """Initialize the click parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
    def get_params(self) -> ClickParams:
        """Get the current click parameters."""
        return ClickParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value()
        )
        
    def set_params(self, params: ClickParams) -> None:
        """Set the click parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self._creating_widgets = False

class DragParamsWidget(BaseParamsWidget):
    """Widget for configuring drag action parameters."""
    
    def __init__(self):
        """Initialize the drag parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Add note about positions
        note_label = QLabel("Select start position from the main position dropdown above")
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)
        
        # End position field
        end_pos_layout = QVBoxLayout()  # Changed to vertical layout for better organization
        end_pos_layout.addWidget(QLabel("End Position:"))
        self.end_position_combo = QComboBox()
        self.end_position_combo.setMinimumWidth(200)  # Make the combo box wider
        self.end_position_combo.currentTextChanged.connect(self.params_changed.emit)
        end_pos_layout.addWidget(self.end_position_combo)
        layout.addLayout(end_pos_layout)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 10.0)
        self.duration_spin.setValue(0.5)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
    def get_params(self) -> DragParams:
        """Get the current drag parameters."""
        return DragParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            duration=self.duration_spin.value(),
            end_position_name=self.end_position_combo.currentText()
        )
        
    def set_params(self, params: DragParams) -> None:
        """Set the drag parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.duration_spin.setValue(params.duration)
        
        # Find and select the end position in the combo box
        index = self.end_position_combo.findText(params.end_position_name)
        if index >= 0:
            self.end_position_combo.setCurrentIndex(index)
        self._creating_widgets = False
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """
        Update the available positions in the end position combo box.
        
        Args:
            positions: Dictionary of position name to AutomationPosition
        """
        # Store current selection
        current_pos = self.end_position_combo.currentText()
        
        # Update combo box items
        self.end_position_combo.clear()
        self.end_position_combo.addItems(sorted(positions.keys()))
        
        # Restore previous selection if it still exists
        index = self.end_position_combo.findText(current_pos)
        if index >= 0:
            self.end_position_combo.setCurrentIndex(index)

class TypeParamsWidget(BaseParamsWidget):
    """Widget for configuring text input action parameters."""
    
    def __init__(self):
        """Initialize the type parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Text field
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
    def get_params(self) -> TypeParams:
        """Get the current type parameters."""
        return TypeParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            text=self.text_edit.text()
        )
        
    def set_params(self, params: TypeParams) -> None:
        """Set the type parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.text_edit.setText(params.text)
        self._creating_widgets = False

class WaitParamsWidget(BaseParamsWidget):
    """Widget for configuring wait action parameters."""
    
    def __init__(self):
        """Initialize the wait parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 999)
        self.duration_spin.setValue(1.0)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
    def get_params(self) -> WaitParams:
        """Get the current wait parameters."""
        return WaitParams(
            description=self.description_edit.text() or None,
            duration=self.duration_spin.value()
        )
        
    def set_params(self, params: WaitParams) -> None:
        """Set the wait parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.duration_spin.setValue(params.duration)
        self._creating_widgets = False

class OCRWaitParamsWidget(BaseParamsWidget):
    """Widget for configuring OCR wait action parameters."""
    
    def __init__(self):
        """Initialize the OCR wait parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Expected text field
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Expected Text:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)
        
        # Partial match checkbox
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("Partial Match:"))
        self.partial_check = QCheckBox()
        self.partial_check.stateChanged.connect(self.params_changed.emit)
        match_layout.addWidget(self.partial_check)
        layout.addLayout(match_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
    def get_params(self) -> OCRWaitParams:
        """Get the current OCR wait parameters."""
        return OCRWaitParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            expected_text=self.text_edit.text(),
            partial_match=self.partial_check.isChecked()
        )
        
    def set_params(self, params: OCRWaitParams) -> None:
        """Set the OCR wait parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.text_edit.setText(params.expected_text)
        self.partial_check.setChecked(params.partial_match)
        self._creating_widgets = False

def create_params_widget(action_type: ActionType) -> BaseParamsWidget:
    """
    Create a parameter widget for the given action type.
    
    Args:
        action_type: Type of action to create parameters for
        
    Returns:
        Parameter widget instance
    """
    widget_map = {
        ActionType.CLICK: ClickParamsWidget,
        ActionType.RIGHT_CLICK: ClickParamsWidget,
        ActionType.DOUBLE_CLICK: ClickParamsWidget,
        ActionType.DRAG: DragParamsWidget,
        ActionType.TYPE_TEXT: TypeParamsWidget,
        ActionType.WAIT: WaitParamsWidget,
        ActionType.WAIT_FOR_OCR: OCRWaitParamsWidget
    }
    
    widget_class = widget_map.get(action_type)
    if not widget_class:
        raise ValueError(f"No parameter widget for action type: {action_type}")
        
    return widget_class() 