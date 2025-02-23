"""
Action Parameter Widgets

This module provides specialized widgets for configuring different types of action parameters.
Each action type has its own parameter widget that shows relevant configuration options.
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from scout.automation.actions import (
    ActionType, ActionParamsCommon, ClickParams, DragParams,
    TypeParams, WaitParams, PatternWaitParams, OCRWaitParams
)

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
        
        # End position field
        end_pos_layout = QHBoxLayout()
        end_pos_layout.addWidget(QLabel("End Position:"))
        self.end_position_edit = QLineEdit()
        self.end_position_edit.textChanged.connect(self.params_changed.emit)
        end_pos_layout.addWidget(self.end_position_edit)
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
            end_position_name=self.end_position_edit.text()
        )
        
    def set_params(self, params: DragParams) -> None:
        """Set the drag parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.duration_spin.setValue(params.duration)
        self.end_position_edit.setText(params.end_position_name)
        self._creating_widgets = False

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

class PatternWaitParamsWidget(BaseParamsWidget):
    """Widget for configuring pattern wait action parameters."""
    
    def __init__(self):
        """Initialize the pattern wait parameters widget."""
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
        
        # Pattern name field
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.textChanged.connect(self.params_changed.emit)
        pattern_layout.addWidget(self.pattern_edit)
        layout.addLayout(pattern_layout)
        
        # Confidence field
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.valueChanged.connect(self.params_changed.emit)
        confidence_layout.addWidget(self.confidence_spin)
        layout.addLayout(confidence_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
    def get_params(self) -> PatternWaitParams:
        """Get the current pattern wait parameters."""
        return PatternWaitParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            pattern_name=self.pattern_edit.text(),
            min_confidence=self.confidence_spin.value()
        )
        
    def set_params(self, params: PatternWaitParams) -> None:
        """Set the pattern wait parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.pattern_edit.setText(params.pattern_name)
        self.confidence_spin.setValue(params.min_confidence)
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
        ActionType.WAIT_FOR_PATTERN: PatternWaitParamsWidget,
        ActionType.WAIT_FOR_OCR: OCRWaitParamsWidget
    }
    
    widget_class = widget_map.get(action_type)
    if not widget_class:
        raise ValueError(f"No parameter widget for action type: {action_type}")
        
    return widget_class() 