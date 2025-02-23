"""
Automation Tab

This module provides the main automation tab in the GUI.
It contains:
- Position list and management
- Sequence builder and editor
- Import/export functionality
- Execution controls
"""

from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QMessageBox, QFileDialog,
    QGroupBox, QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
import json
from pathlib import Path
from scout.automation.core import AutomationPosition, AutomationSequence
from scout.automation.actions import ActionType, AutomationAction, ActionParamsCommon
from scout.automation.gui.position_marker import PositionMarker
from scout.automation.gui.action_params import create_params_widget, BaseParamsWidget
from scout.automation.executor import SequenceExecutor, ExecutionContext

logger = logging.getLogger(__name__)

class PositionList(QWidget):
    """
    Widget for managing marked positions.
    
    Features:
    - List of all marked positions
    - Add/remove positions
    - Edit position properties
    - Position selection for actions
    """
    
    position_selected = pyqtSignal(str)  # Emits position name
    
    def __init__(self):
        """Initialize the position list widget."""
        super().__init__()
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create position list
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_position_selected)
        layout.addWidget(QLabel("Marked Positions:"))
        layout.addWidget(self.list_widget)
        
        # Create controls
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Mark New Position")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Position")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # Add position details
        details_group = QGroupBox("Position Details")
        details_layout = QVBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Position Name")
        self.name_edit.textChanged.connect(self._on_details_changed)
        details_layout.addWidget(self.name_edit)
        
        coord_layout = QHBoxLayout()
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.valueChanged.connect(self._on_details_changed)
        coord_layout.addWidget(QLabel("X:"))
        coord_layout.addWidget(self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.valueChanged.connect(self._on_details_changed)
        coord_layout.addWidget(QLabel("Y:"))
        coord_layout.addWidget(self.y_spin)
        
        details_layout.addLayout(coord_layout)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        self.description_edit.textChanged.connect(self._on_details_changed)
        details_layout.addWidget(self.description_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Initialize state
        self.positions: Dict[str, AutomationPosition] = {}
        self._updating_details = False
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update the position list with new positions."""
        self.positions = positions
        self.list_widget.clear()
        for name in positions:
            self.list_widget.addItem(name)
            
    def _on_position_selected(self, item: QListWidgetItem) -> None:
        """Handle position selection."""
        name = item.text()
        self.remove_button.setEnabled(True)
        self.position_selected.emit(name)
        
        # Update details
        if name in self.positions:
            pos = self.positions[name]
            self._updating_details = True
            self.name_edit.setText(name)
            self.x_spin.setValue(pos.x)
            self.y_spin.setValue(pos.y)
            self.description_edit.setText(pos.description or "")
            self._updating_details = False
            
    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        # Signal that we want to start marking a position
        # The actual implementation will be in the parent widget
        self.add_button.setEnabled(False)
        
    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        current = self.list_widget.currentItem()
        if current:
            name = current.text()
            if name in self.positions:
                del self.positions[name]
                self.update_positions(self.positions)
                self.remove_button.setEnabled(False)
                
    def _on_details_changed(self) -> None:
        """Handle changes to position details."""
        if self._updating_details:
            return
            
        current = self.list_widget.currentItem()
        if not current:
            return
            
        old_name = current.text()
        new_name = self.name_edit.text()
        
        if old_name in self.positions:
            pos = self.positions[old_name]
            pos.x = self.x_spin.value()
            pos.y = self.y_spin.value()
            pos.description = self.description_edit.text()
            
            if new_name != old_name:
                # Rename position
                self.positions[new_name] = pos
                del self.positions[old_name]
                self.update_positions(self.positions)

class ActionListItem(QListWidgetItem):
    """List item representing an action in a sequence."""
    
    def __init__(self, action: AutomationAction):
        """Initialize the action list item."""
        super().__init__()
        self.action = action
        self.update_text()
        
    def update_text(self) -> None:
        """Update the item's display text."""
        params = self.action.params
        text = f"{self.action.action_type.name}"
        if params.position_name:
            text += f" @ {params.position_name}"
        if params.description:
            text += f" - {params.description}"
        self.setText(text)

class SequenceBuilder(QWidget):
    """
    Widget for building and editing action sequences.
    
    Features:
    - List of actions in sequence
    - Add/remove actions
    - Configure action parameters
    - Import/export sequences
    """
    
    sequence_changed = pyqtSignal()  # Emitted when sequence is modified
    sequence_execution = pyqtSignal(object, bool, float)  # sequence, simulation, delay
    execution_paused = pyqtSignal()
    execution_step = pyqtSignal()
    execution_stopped = pyqtSignal()
    
    def __init__(self):
        """Initialize the sequence builder widget."""
        super().__init__()
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add sequence name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sequence Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_sequence_changed)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Create sequence list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_action_selected)
        layout.addWidget(QLabel("Action Sequence:"))
        layout.addWidget(self.list_widget)
        
        # Create action controls
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Action")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Action")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(self._on_move_up_clicked)
        self.move_up_button.setEnabled(False)
        button_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(self._on_move_down_clicked)
        self.move_down_button.setEnabled(False)
        button_layout.addWidget(self.move_down_button)
        
        layout.addLayout(button_layout)
        
        # Add action configuration
        config_group = QGroupBox("Action Configuration")
        config_layout = QVBoxLayout()
        
        # Action type selection
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        for action_type in ActionType:
            self.type_combo.addItem(action_type.name)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        type_layout.addWidget(QLabel("Type:"))
        type_layout.addWidget(self.type_combo)
        config_layout.addLayout(type_layout)
        
        # Position selection
        self.position_combo = QComboBox()
        self.position_combo.currentTextChanged.connect(self._on_position_changed)
        config_layout.addWidget(QLabel("Position:"))
        config_layout.addWidget(self.position_combo)
        
        # Parameters (will be populated based on action type)
        self.params_widget: Optional[BaseParamsWidget] = None
        self.params_container = QWidget()
        self.params_layout = QVBoxLayout()
        self.params_container.setLayout(self.params_layout)
        config_layout.addWidget(self.params_container)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Add execution controls
        exec_group = QGroupBox("Execution Controls")
        exec_layout = QVBoxLayout()
        
        # Simulation mode
        sim_layout = QHBoxLayout()
        sim_layout.addWidget(QLabel("Simulation Mode:"))
        self.simulation_check = QCheckBox()
        sim_layout.addWidget(self.simulation_check)
        exec_layout.addLayout(sim_layout)
        
        # Step delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Step Delay (s):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 10.0)
        self.delay_spin.setValue(0.5)
        delay_layout.addWidget(self.delay_spin)
        exec_layout.addLayout(delay_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._on_run_clicked)
        control_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setEnabled(False)
        control_layout.addWidget(self.pause_button)
        
        self.step_button = QPushButton("Step")
        self.step_button.clicked.connect(self._on_step_clicked)
        self.step_button.setEnabled(False)
        control_layout.addWidget(self.step_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        exec_layout.addLayout(control_layout)
        
        # Progress label
        self.progress_label = QLabel()
        exec_layout.addWidget(self.progress_label)
        
        exec_group.setLayout(exec_layout)
        layout.addWidget(exec_group)
        
        # Add import/export buttons
        io_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Import Sequence")
        self.import_button.clicked.connect(self._on_import_clicked)
        io_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("Export Sequence")
        self.export_button.clicked.connect(self._on_export_clicked)
        io_layout.addWidget(self.export_button)
        
        layout.addLayout(io_layout)
        
        # Initialize state
        self.sequence: Optional[AutomationSequence] = None
        self.positions: Dict[str, AutomationPosition] = {}
        self._updating_widgets = False
        
        # Create initial sequence
        self._new_sequence()
        
        # Create initial params widget for the default action type
        self._update_params_widget(ActionType[self.type_combo.currentText()])
        
    def _new_sequence(self) -> None:
        """Create a new empty sequence."""
        self.sequence = AutomationSequence(
            name="New Sequence",
            actions=[],
            description=None
        )
        self.name_edit.setText(self.sequence.name)
        self.list_widget.clear()
        self._update_buttons()
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update available positions."""
        self.positions = positions
        self.position_combo.clear()
        self.position_combo.addItem("")  # Empty option
        self.position_combo.addItems(positions.keys())
        
    def _on_sequence_changed(self) -> None:
        """Handle sequence changes."""
        if self._updating_widgets:
            return
            
        if self.sequence:
            self.sequence.name = self.name_edit.text()
            self.sequence_changed.emit()
            
    def _on_action_selected(self, current: ActionListItem, previous: ActionListItem) -> None:
        """Handle action selection."""
        self._updating_widgets = True
        
        if current:
            action = current.action
            self.type_combo.setCurrentText(action.action_type.name)
            self._update_params_widget(action.action_type)
            
            if hasattr(action.params, 'position_name'):
                self.position_combo.setCurrentText(action.params.position_name or "")
            else:
                self.position_combo.setCurrentText("")
                
            if self.params_widget:
                self.params_widget.set_params(action.params)
        
        self._update_buttons()
        self._updating_widgets = False
        
    def _on_add_clicked(self) -> None:
        """Handle add action button click."""
        action_type = ActionType[self.type_combo.currentText()]
        params = self.params_widget.get_params() if self.params_widget else None
        
        if not params:
            return
            
        action = AutomationAction(action_type, params)
        item = ActionListItem(action)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        
        if self.sequence:
            self.sequence.actions.append(action.to_dict())
            self.sequence_changed.emit()
            
    def _on_remove_clicked(self) -> None:
        """Handle remove action button click."""
        current = self.list_widget.currentItem()
        if current:
            row = self.list_widget.row(current)
            self.list_widget.takeItem(row)
            
            if self.sequence:
                del self.sequence.actions[row]
                self.sequence_changed.emit()
                
        self._update_buttons()
        
    def _on_move_up_clicked(self) -> None:
        """Handle move up button click."""
        current = self.list_widget.currentItem()
        if not current:
            return
            
        row = self.list_widget.row(current)
        if row <= 0:
            return
            
        # Move in list widget
        self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, current)
        self.list_widget.setCurrentItem(current)
        
        # Move in sequence
        if self.sequence:
            action = self.sequence.actions.pop(row)
            self.sequence.actions.insert(row - 1, action)
            self.sequence_changed.emit()
            
    def _on_move_down_clicked(self) -> None:
        """Handle move down button click."""
        current = self.list_widget.currentItem()
        if not current:
            return
            
        row = self.list_widget.row(current)
        if row >= self.list_widget.count() - 1:
            return
            
        # Move in list widget
        self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, current)
        self.list_widget.setCurrentItem(current)
        
        # Move in sequence
        if self.sequence:
            action = self.sequence.actions.pop(row)
            self.sequence.actions.insert(row + 1, action)
            self.sequence_changed.emit()
            
    def _on_type_changed(self, action_type: str) -> None:
        """Handle action type change."""
        if self._updating_widgets:
            return
            
        self._update_params_widget(ActionType[action_type])
        self._update_current_action()
        
    def _on_position_changed(self, position_name: str) -> None:
        """Handle position selection change."""
        if self._updating_widgets:
            return
            
        self._update_current_action()
        
    def _update_params_widget(self, action_type: ActionType) -> None:
        """Update the parameter widget for the current action type."""
        # Clear existing widget
        if self.params_widget:
            self.params_widget.deleteLater()
            
        # Create new widget
        self.params_widget = create_params_widget(action_type)
        self.params_widget.params_changed.connect(self._update_current_action)
        self.params_layout.addWidget(self.params_widget)
        
        # Update position combo enabled state
        needs_position = action_type in {
            ActionType.CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.DRAG,
            ActionType.TYPE_TEXT
        }
        self.position_combo.setEnabled(needs_position)
        
    def _update_current_action(self) -> None:
        """Update the current action with new parameters."""
        if self._updating_widgets:
            return
            
        current = self.list_widget.currentItem()
        if not current or not self.params_widget:
            return
            
        # Update action
        action_type = ActionType[self.type_combo.currentText()]
        params = self.params_widget.get_params()
        
        if self.position_combo.isEnabled():
            params.position_name = self.position_combo.currentText() or None
            
        current.action = AutomationAction(action_type, params)
        current.update_text()
        
        # Update sequence
        if self.sequence:
            row = self.list_widget.row(current)
            self.sequence.actions[row] = current.action.to_dict()
            self.sequence_changed.emit()
            
    def _update_buttons(self) -> None:
        """Update button enabled states."""
        has_current = self.list_widget.currentItem() is not None
        has_items = self.list_widget.count() > 0
        current_row = self.list_widget.currentRow()
        
        self.remove_button.setEnabled(has_current)
        self.move_up_button.setEnabled(has_current and current_row > 0)
        self.move_down_button.setEnabled(has_current and current_row < self.list_widget.count() - 1)
        self.export_button.setEnabled(has_items)
        
    def _on_import_clicked(self) -> None:
        """Handle import button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Sequence", str(Path.home()), "JSON Files (*.json)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                sequence = AutomationSequence.from_dict(data)
                
            # Update UI
            self._updating_widgets = True
            self.sequence = sequence
            self.name_edit.setText(sequence.name)
            
            # Clear and rebuild list
            self.list_widget.clear()
            for action_data in sequence.actions:
                action = AutomationAction.from_dict(action_data)
                item = ActionListItem(action)
                self.list_widget.addItem(item)
                
            self._updating_widgets = False
            self.sequence_changed.emit()
            
        except Exception as e:
            logger.error(f"Failed to import sequence: {e}")
            QMessageBox.critical(self, "Import Error", str(e))
            
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        if not self.sequence or not self.sequence.actions:
            QMessageBox.warning(self, "Export Error", "No sequence to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Sequence", str(Path.home()), "JSON Files (*.json)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                json.dump(self.sequence.to_dict(), f, indent=4)
                
        except Exception as e:
            logger.error(f"Failed to export sequence: {e}")
            QMessageBox.critical(self, "Export Error", str(e))

    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        if not self.sequence or not self.sequence.actions:
            QMessageBox.warning(self, "Run Error", "No sequence to run")
            return
            
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.step_button.setEnabled(False)
        
        self.sequence_execution.emit(
            self.sequence,
            self.simulation_check.isChecked(),
            self.delay_spin.value()
        )
        
    def _on_pause_clicked(self) -> None:
        """Handle pause button click."""
        self.pause_button.setEnabled(False)
        self.step_button.setEnabled(True)
        self.execution_paused.emit()
        
    def _on_step_clicked(self) -> None:
        """Handle step button click."""
        self.execution_step.emit()
        
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.execution_stopped.emit()
        
    def _update_progress(self, step: int) -> None:
        """Update progress display."""
        if not self.sequence:
            return
            
        total = len(self.sequence.actions)
        self.progress_label.setText(f"Step {step + 1} of {total}")
        
    def _on_sequence_completed(self) -> None:
        """Handle sequence completion."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.progress_label.setText("Sequence completed")
        
    def _on_execution_error(self, message: str) -> None:
        """Handle execution error."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.progress_label.setText("Error: " + message)
        QMessageBox.critical(self, "Execution Error", message)

class AutomationTab(QWidget):
    """
    Main automation tab widget.
    
    This tab provides:
    - Split view with positions and sequences
    - Position marking interface
    - Sequence building and execution
    - Import/export functionality
    """
    
    def __init__(self, window_manager, pattern_matcher, text_ocr, game_actions):
        """Initialize the automation tab."""
        super().__init__()
        
        # Store components
        self.window_manager = window_manager
        self.pattern_matcher = pattern_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        
        # Create layout
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Create position marker
        self.position_marker = PositionMarker(window_manager)
        self.position_marker.position_marked.connect(self._on_position_marked)
        
        # Create left side (positions)
        self.position_list = PositionList()
        layout.addWidget(self.position_list, stretch=1)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Create right side (sequences)
        self.sequence_builder = SequenceBuilder()
        layout.addWidget(self.sequence_builder, stretch=2)
        
        # Create debug window
        from scout.automation.gui.debug_window import AutomationDebugWindow
        self.debug_window = AutomationDebugWindow()
        
        # Add debug button
        debug_button = QPushButton("Show Debug Window")
        debug_button.clicked.connect(self._on_debug_clicked)
        layout.addWidget(debug_button)
        
        # Create sequence executor
        self.executor = None  # Will be created when needed
        
        # Connect signals
        self.position_list.position_selected.connect(self._on_position_selected)
        self.sequence_builder.sequence_execution.connect(self._on_sequence_execution)
        self.sequence_builder.execution_paused.connect(self._on_execution_paused)
        self.sequence_builder.execution_step.connect(self._on_execution_step)
        self.sequence_builder.execution_stopped.connect(self._on_execution_stopped)
        
    def _on_debug_clicked(self) -> None:
        """Show or hide the debug window."""
        if self.debug_window.isVisible():
            self.debug_window.hide()
        else:
            self.debug_window.show()
            
    def _on_position_marked(self, point) -> None:
        """Handle new position being marked."""
        # Create new position and add to list
        name = f"Position_{len(self.position_list.positions) + 1}"
        position = AutomationPosition(name, point.x(), point.y())
        self.position_list.positions[name] = position
        self.position_list.update_positions(self.position_list.positions)
        self.sequence_builder.update_positions(self.position_list.positions)
        self.position_marker.stop_marking()
        self.position_list.add_button.setEnabled(True)
        
        # Update debug window
        self.debug_window.update_positions(self.position_list.positions)
        
    def _on_position_selected(self, name: str) -> None:
        """Handle position selection."""
        # Update sequence builder with selected position
        pass
        
    def _on_sequence_execution(self, sequence: AutomationSequence, simulation: bool, delay: float) -> None:
        """Handle sequence execution request."""
        # Create executor if needed
        if not self.executor:
            context = ExecutionContext(
                positions=self.position_list.positions,
                window_manager=self.window_manager,
                pattern_matcher=self.pattern_matcher,
                text_ocr=self.text_ocr,
                game_actions=self.game_actions,
                debug_tab=self.debug_window.execution_tab,
                simulation_mode=simulation,
                step_delay=delay
            )
            self.executor = SequenceExecutor(context)
            
            # Connect signals
            self.executor.step_completed.connect(self.sequence_builder._update_progress)
            self.executor.sequence_completed.connect(self.sequence_builder._on_sequence_completed)
            self.executor.execution_error.connect(self.sequence_builder._on_execution_error)
            
            # Connect debug signals
            self.executor.step_completed.connect(self._update_debug_state)
            
        # Update executor settings
        self.executor.context.simulation_mode = simulation
        self.executor.context.step_delay = delay
        
        # Clear debug window
        self.debug_window.clear_log()
        
        # Start execution
        self.executor.execute_sequence(sequence)
        
    def _on_execution_paused(self) -> None:
        """Handle execution pause request."""
        if self.executor:
            self.executor.pause_execution()
            self.debug_window.set_execution_paused(True)
            
    def _on_execution_step(self) -> None:
        """Handle execution step request."""
        if self.executor:
            self.executor.step_execution()
            
    def _on_execution_stopped(self) -> None:
        """Handle execution stop request."""
        if self.executor:
            self.executor.stop_execution()
            self.debug_window.set_execution_paused(False)
            
    def _update_debug_state(self, step: int) -> None:
        """Update debug window with current execution state."""
        if not self.executor or not self.executor.current_sequence:
            return
            
        # Take screenshot
        screenshot = self.window_manager.capture_screenshot()
        if screenshot is not None:
            self.debug_window.update_preview(screenshot)
            
        # Update status
        total_steps = len(self.executor.current_sequence.actions)
        self.debug_window.update_status(f"Step {step + 1} of {total_steps}")
        
        # Get current action
        action_data = self.executor.current_sequence.actions[step]
        action = AutomationAction.from_dict(action_data)
        
        # Update pattern matches if waiting for pattern
        if action.action_type == ActionType.WAIT_FOR_PATTERN:
            if screenshot is not None:
                matches = self.pattern_matcher.find_all_patterns(screenshot)
                self.debug_window.update_pattern_matches(matches)
                
        # Update OCR text if waiting for text
        elif action.action_type == ActionType.WAIT_FOR_OCR:
            if screenshot is not None:
                text = self.text_ocr.extract_text(screenshot)
                regions = self.text_ocr.get_text_regions(screenshot)
                self.debug_window.update_ocr_text(text, regions)
                
        # Update mouse position for mouse actions
        elif action.action_type in {
            ActionType.CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.DRAG,
            ActionType.TYPE_TEXT
        }:
            if hasattr(action.params, 'position_name'):
                position = self.position_list.positions.get(action.params.position_name)
                if position:
                    self.debug_window.update_mouse_position(position.x, position.y) 