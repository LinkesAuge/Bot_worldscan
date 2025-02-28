"""
Action Parameter Widgets

This module provides specialized widgets for configuring different types of action parameters.
Each action type has its own parameter widget that shows relevant configuration options.
"""

from typing import Dict, Any, Optional, List, Union
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from pathlib import Path
from scout.automation.actions import (
    ActionType, ClickParams, DragParams,
    TypeParams, WaitParams, TemplateSearchParams, OCRWaitParams
)
from scout.automation.core import AutomationPosition
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

ParamType = Union[ClickParams, DragParams, TypeParams, WaitParams, TemplateSearchParams, OCRWaitParams]

class BaseParamsWidget(QWidget):
    """Base class for all parameter widgets."""
    
    params_changed = pyqtSignal()  # Emitted when parameters are changed
    
    def __init__(self):
        """Initialize the base parameter widget."""
        super().__init__()
        self._creating_widgets = False
        
        # Create base layout
        self.base_layout = QVBoxLayout()
        self.setLayout(self.base_layout)
        
        # Add repeat count field
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat Count:"))
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 999)
        self.repeat_spin.setValue(1)
        self.repeat_spin.valueChanged.connect(self.params_changed.emit)
        repeat_layout.addWidget(self.repeat_spin)
        self.base_layout.addLayout(repeat_layout)
        
        # Add increment per loop fields
        increment_layout = QHBoxLayout()
        self.use_increment_check = QCheckBox("Use Increment Per Loop")
        self.use_increment_check.setChecked(False)
        self.use_increment_check.stateChanged.connect(self._on_use_increment_changed)
        self.use_increment_check.stateChanged.connect(self.params_changed.emit)
        increment_layout.addWidget(self.use_increment_check)
        
        increment_layout.addWidget(QLabel("Increment Value:"))
        self.increment_spin = QSpinBox()
        self.increment_spin.setRange(1, 100)
        self.increment_spin.setValue(1)
        self.increment_spin.setEnabled(False)  # Initially disabled
        self.increment_spin.valueChanged.connect(self.params_changed.emit)
        increment_layout.addWidget(self.increment_spin)
        
        self.base_layout.addLayout(increment_layout)
        
    def _on_use_increment_changed(self, state):
        """Enable/disable increment spin box based on checkbox state."""
        self.increment_spin.setEnabled(state == Qt.CheckState.Checked)
        
    def get_params(self) -> ParamType:
        """Get the current parameter values."""
        raise NotImplementedError()
        
    def set_params(self, params: ParamType) -> None:
        """Set the parameter values."""
        raise NotImplementedError()
        
    def _get_common_params(self) -> Dict[str, Any]:
        """Get common parameter values."""
        return {
            'repeat': self.repeat_spin.value(),
            'use_increment': self.use_increment_check.isChecked(),
            'increment': self.increment_spin.value()
        }
        
    def _set_common_params(self, params: ParamType) -> None:
        """Set common parameter values."""
        self.repeat_spin.setValue(getattr(params, 'repeat', 1))
        self.use_increment_check.setChecked(getattr(params, 'use_increment', False))
        self.increment_spin.setValue(getattr(params, 'increment', 1))
        self.increment_spin.setEnabled(getattr(params, 'use_increment', False))

class ClickParamsWidget(BaseParamsWidget):
    """Widget for configuring click action parameters."""
    
    def __init__(self):
        """Initialize the click parameters widget."""
        super().__init__()
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        self.base_layout.addLayout(timeout_layout)
        
    def get_params(self) -> ClickParams:
        """Get the current click parameters."""
        return ClickParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            **self._get_common_params()  # Include common params
        )
        
    def set_params(self, params: ClickParams) -> None:
        """Set the click parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self._set_common_params(params)  # Set common params
        self._creating_widgets = False

class DragParamsWidget(BaseParamsWidget):
    """Widget for configuring drag action parameters."""
    
    def __init__(self):
        """Initialize the drag parameters widget."""
        super().__init__()
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # End position selection
        end_pos_layout = QHBoxLayout()
        end_pos_layout.addWidget(QLabel("End Position:"))
        self.end_position_combo = QComboBox()
        self.end_position_combo.currentTextChanged.connect(self.params_changed.emit)
        end_pos_layout.addWidget(self.end_position_combo)
        self.base_layout.addLayout(end_pos_layout)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 999)
        self.duration_spin.setValue(0.5)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        self.base_layout.addLayout(duration_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        self.base_layout.addLayout(timeout_layout)
        
    def get_params(self) -> DragParams:
        """Get the current drag parameters."""
        return DragParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            duration=self.duration_spin.value(),
            end_position_name=self.end_position_combo.currentText(),
            **self._get_common_params()
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
        self._set_common_params(params)
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
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # Text field
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        self.base_layout.addLayout(text_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        self.base_layout.addLayout(timeout_layout)
        
    def get_params(self) -> TypeParams:
        """Get the current type parameters."""
        return TypeParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            text=self.text_edit.text(),
            **self._get_common_params()
        )
        
    def set_params(self, params: TypeParams) -> None:
        """Set the type parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.text_edit.setText(params.text)
        self._set_common_params(params)
        self._creating_widgets = False

class WaitParamsWidget(BaseParamsWidget):
    """Widget for configuring wait action parameters."""
    
    def __init__(self):
        """Initialize the wait parameters widget."""
        super().__init__()
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 999)
        self.duration_spin.setValue(1.0)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        self.base_layout.addLayout(duration_layout)
        
    def get_params(self) -> WaitParams:
        """Get the current wait parameters."""
        return WaitParams(
            description=self.description_edit.text() or None,
            duration=self.duration_spin.value(),
            **self._get_common_params()
        )
        
    def set_params(self, params: WaitParams) -> None:
        """Set the wait parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.duration_spin.setValue(params.duration)
        self._set_common_params(params)
        self._creating_widgets = False

class TemplateSearchParamsWidget(BaseParamsWidget):
    """Widget for configuring template search parameters."""
    
    def __init__(self):
        """Initialize the template search parameters widget."""
        super().__init__()
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # Template list
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.template_list.itemSelectionChanged.connect(self.params_changed.emit)
        self.base_layout.addWidget(QLabel("Templates:"))
        self.base_layout.addWidget(self.template_list)
        
        # Use all templates checkbox
        self.use_all_templates = QCheckBox("Use All Templates")
        self.use_all_templates.setChecked(True)
        self.use_all_templates.stateChanged.connect(self._on_use_all_changed)
        self.base_layout.addWidget(self.use_all_templates)
        
        # Overlay enabled checkbox
        self.overlay_enabled = QCheckBox("Show Overlay")
        self.overlay_enabled.setChecked(True)
        self.overlay_enabled.stateChanged.connect(self.params_changed.emit)
        self.base_layout.addWidget(self.overlay_enabled)
        
        # Sound enabled checkbox
        self.sound_enabled = QCheckBox("Enable Sound")
        self.sound_enabled.setChecked(True)
        self.sound_enabled.stateChanged.connect(self.params_changed.emit)
        self.base_layout.addWidget(self.sound_enabled)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 999)
        self.duration_spin.setValue(30.0)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        self.base_layout.addLayout(duration_layout)
        
        # Update frequency field
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Updates/sec:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(0.1, 60)
        self.freq_spin.setValue(1.0)
        self.freq_spin.valueChanged.connect(self.params_changed.emit)
        freq_layout.addWidget(self.freq_spin)
        self.base_layout.addLayout(freq_layout)
        
        # Confidence threshold field
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 1.0)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.valueChanged.connect(self.params_changed.emit)
        conf_layout.addWidget(self.confidence_spin)
        self.base_layout.addLayout(conf_layout)
        
        # Load available templates
        self._load_templates()
        
    def _load_templates(self) -> None:
        """Load available templates from templates directory."""
        try:
            templates_dir = Path('scout/templates')
            if templates_dir.exists():
                for template_file in templates_dir.glob('*.png'):
                    item = QListWidgetItem(template_file.stem)
                    self.template_list.addItem(item)
            
            # Update template list enabled state
            self._on_use_all_changed()
            
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            
    def _on_use_all_changed(self) -> None:
        """Handle use all templates toggle."""
        use_all = self.use_all_templates.isChecked()
        self.template_list.setEnabled(not use_all)
        if use_all:
            # Deselect all items
            self.template_list.clearSelection()
            
    def _load_settings(self) -> None:
        """Load saved template search settings."""
        try:
            config = ConfigManager()
            settings = config.get_template_search_settings()
            
            if settings:
                self.overlay_enabled.setChecked(settings.get("overlay_enabled", True))
                self.sound_enabled.setChecked(settings.get("sound_enabled", True))
                self.duration_spin.setValue(settings.get("duration", 30.0))
                self.freq_spin.setValue(settings.get("update_frequency", 1.0))
                self.confidence_spin.setValue(settings.get("min_confidence", 0.8))
                
                # Load template selection
                use_all = settings.get("use_all_templates", True)
                self.use_all_templates.setChecked(use_all)
                if not use_all:
                    selected_templates = settings.get("templates", [])
                    for i in range(self.template_list.count()):
                        item = self.template_list.item(i)
                        if item.text() in selected_templates:
                            item.setSelected(True)
                            
        except Exception as e:
            logger.error(f"Failed to load template search settings: {e}")
            
    def _save_settings(self) -> None:
        """Save template search settings."""
        try:
            config = ConfigManager()
            settings = {
                "overlay_enabled": self.overlay_enabled.isChecked(),
                "sound_enabled": self.sound_enabled.isChecked(),
                "duration": self.duration_spin.value(),
                "update_frequency": self.freq_spin.value(),
                "min_confidence": self.confidence_spin.value(),
                "use_all_templates": self.use_all_templates.isChecked(),
                "templates": [item.text() for item in self.template_list.selectedItems()]
            }
            
            config.update_template_search_settings(settings)
            
        except Exception as e:
            logger.error(f"Failed to save template search settings: {e}")
            
    def get_params(self) -> TemplateSearchParams:
        """Get the current template search parameters."""
        # Save settings before returning
        self._save_settings()
        
        # Get selected templates - ensure we have a list even if 'use all' is checked
        if self.use_all_templates.isChecked():
            templates = [self.template_list.item(i).text() 
                       for i in range(self.template_list.count())]
        else:
            templates = [item.text() for item in self.template_list.selectedItems()]
            if not templates:  # If no templates selected, use all
                templates = [self.template_list.item(i).text() 
                           for i in range(self.template_list.count())]
                
        return TemplateSearchParams(
            templates=templates,
            use_all_templates=self.use_all_templates.isChecked(),
            overlay_enabled=self.overlay_enabled.isChecked(),
            sound_enabled=self.sound_enabled.isChecked(),
            duration=self.duration_spin.value(),
            update_frequency=self.freq_spin.value(),
            min_confidence=self.confidence_spin.value(),
            description=self.description_edit.text() or None,
            **self._get_common_params()
        )
        
    def set_params(self, params: TemplateSearchParams) -> None:
        """Set the template search parameters."""
        self._creating_widgets = True
        
        self.use_all_templates.setChecked(params.use_all_templates)
        self.overlay_enabled.setChecked(params.overlay_enabled)
        self.sound_enabled.setChecked(params.sound_enabled)
        self.duration_spin.setValue(params.duration)
        self.freq_spin.setValue(params.update_frequency)
        self.confidence_spin.setValue(params.min_confidence)
        self.description_edit.setText(params.description or "")
        
        # Set selected templates
        self.template_list.clearSelection()
        if not params.use_all_templates:
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.text() in params.templates:
                    item.setSelected(True)
        
        self._set_common_params(params)
        self._creating_widgets = False

class OCRWaitParamsWidget(BaseParamsWidget):
    """Widget for configuring OCR wait action parameters."""
    
    def __init__(self):
        """Initialize the OCR wait parameters widget."""
        super().__init__()
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        self.base_layout.addLayout(desc_layout)
        
        # Expected text field
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Expected Text:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        self.base_layout.addLayout(text_layout)
        
        # Partial match checkbox
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("Partial Match:"))
        self.partial_check = QCheckBox()
        self.partial_check.stateChanged.connect(self.params_changed.emit)
        match_layout.addWidget(self.partial_check)
        self.base_layout.addLayout(match_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        self.base_layout.addLayout(timeout_layout)
        
    def get_params(self) -> OCRWaitParams:
        """Get the current OCR wait parameters."""
        return OCRWaitParams(
            description=self.description_edit.text() or None,
            timeout=self.timeout_spin.value(),
            expected_text=self.text_edit.text(),
            partial_match=self.partial_check.isChecked(),
            **self._get_common_params()
        )
        
    def set_params(self, params: OCRWaitParams) -> None:
        """Set the OCR wait parameters."""
        self._creating_widgets = True
        self.description_edit.setText(params.description or "")
        self.timeout_spin.setValue(params.timeout)
        self.text_edit.setText(params.expected_text)
        self.partial_check.setChecked(params.partial_match)
        self._set_common_params(params)
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
        ActionType.TEMPLATE_SEARCH: TemplateSearchParamsWidget,
        ActionType.WAIT_FOR_OCR: OCRWaitParamsWidget
    }
    
    widget_class = widget_map.get(action_type)
    if not widget_class:
        raise ValueError(f"No parameter widget for action type: {action_type}")
        
    return widget_class() 