"""
Game State Tab

This module provides a tab interface for monitoring and managing game state.
It allows users to view, edit, and track state variables during game operation,
as well as define state transitions and triggers.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget
)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer

from scout.core.game.game_state_service_interface import GameStateServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.game.game_service_interface import GameServiceInterface
from scout.ui.widgets.game_state_visualization_widget import GameStateVisualizationWidget
from scout.ui.utils.language_manager import tr

# Set up logging
logger = logging.getLogger(__name__)

class StateVariableEditor(QWidget):
    """
    Widget for editing game state variables.
    
    This widget provides an interface for adding, editing, and removing
    state variables that track the current state of the game.
    """
    
    # Signals
    state_updated = pyqtSignal(dict)  # Updated state data
    
    def __init__(self, game_state_service: GameStateServiceInterface):
        """
        Initialize the state variable editor.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        # Store services
        self.game_state_service = game_state_service
        
        # Initialize state
        self._current_state = {}
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # Add variable button
        self.add_btn = QPushButton(tr("Add Variable"))
        toolbar_layout.addWidget(self.add_btn)
        
        # Remove variable button
        self.remove_btn = QPushButton(tr("Remove Variable"))
        self.remove_btn.setEnabled(False)
        toolbar_layout.addWidget(self.remove_btn)
        
        # Save state button
        self.save_btn = QPushButton(tr("Save State"))
        toolbar_layout.addWidget(self.save_btn)
        
        # Load state button
        self.load_btn = QPushButton(tr("Load State"))
        toolbar_layout.addWidget(self.load_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create state variables table
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(3)
        self.variables_table.setHorizontalHeaderLabels(["Variable", "Value", "Type"])
        
        # Configure table
        self.variables_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.variables_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Double-click to edit
        self.variables_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        
        main_layout.addWidget(self.variables_table)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Toolbar buttons
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.load_btn.clicked.connect(self._on_load_clicked)
        
        # Table selection
        self.variables_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Table item changed
        self.variables_table.itemChanged.connect(self._on_item_changed)
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Set the current state.
        
        Args:
            state: State dictionary
        """
        # Store current state
        self._current_state = state.copy() if state else {}
        
        # Update variables table
        self._update_variables_table()
    
    def _update_variables_table(self) -> None:
        """Update the variables table with current state."""
        # Temporarily disconnect signals to prevent recursive calls
        self.variables_table.itemChanged.disconnect(self._on_item_changed)
        
        # Clear table
        self.variables_table.clearContents()
        self.variables_table.setRowCount(len(self._current_state))
        
        # Add each variable
        for i, (key, value) in enumerate(self._current_state.items()):
            # Variable name
            name_item = QTableWidgetItem(key)
            self.variables_table.setItem(i, 0, name_item)
            
            # Variable value
            value_str = str(value)
            value_item = QTableWidgetItem(value_str)
            self.variables_table.setItem(i, 1, value_item)
            
            # Variable type
            type_name = type(value).__name__
            type_item = QTableWidgetItem(type_name)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make read-only
            self.variables_table.setItem(i, 2, type_item)
        
        # Re-connect signals
        self.variables_table.itemChanged.connect(self._on_item_changed)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in variables table."""
        # Enable/disable remove button
        self.remove_btn.setEnabled(len(self.variables_table.selectedItems()) > 0)
    
    def _on_add_clicked(self) -> None:
        """Handle add variable button click."""
        # Show dialog to enter variable name
        name, ok = QInputDialog.getText(
            self,
            tr("Add Variable"),
            tr("Enter variable name:")
        )
        
        if not ok or not name:
            return
        
        # Check if variable already exists
        if name in self._current_state:
            QMessageBox.warning(
                self,
                tr("Duplicate Variable"),
                tr("Variable '{name}' already exists. Please use a different name.")
            )
            return
        
        # Show dialog to select variable type
        type_dialog = QDialog(self)
        type_dialog.setWindowTitle(tr("Select Variable Type"))
        type_layout = QVBoxLayout(type_dialog)
        
        type_combo = QComboBox()
        type_combo.addItems(["String", "Integer", "Float", "Boolean", "List", "Dictionary"])
        type_layout.addWidget(type_combo)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton(tr("OK"))
        ok_btn.clicked.connect(type_dialog.accept)
        buttons.addWidget(ok_btn)
        
        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.clicked.connect(type_dialog.reject)
        buttons.addWidget(cancel_btn)
        
        type_layout.addLayout(buttons)
        
        if type_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Get selected type
        var_type = type_combo.currentText()
        
        # Create default value based on type
        if var_type == "String":
            value = ""
        elif var_type == "Integer":
            value = 0
        elif var_type == "Float":
            value = 0.0
        elif var_type == "Boolean":
            value = False
        elif var_type == "List":
            value = []
        elif var_type == "Dictionary":
            value = {}
        else:
            value = None
        
        # Add to state
        self._current_state[name] = value
        
        # Update table
        self._update_variables_table()
        
        # Emit state updated signal
        self.state_updated.emit(self._current_state)
    
    def _on_remove_clicked(self) -> None:
        """Handle remove variable button click."""
        # Get selected row
        selected = self.variables_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        name_item = self.variables_table.item(row, 0)
        if not name_item:
            return
        
        name = name_item.text()
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            tr("Remove Variable"),
            tr("Are you sure you want to remove variable '{name}'?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Remove from state
        if name in self._current_state:
            del self._current_state[name]
        
        # Update table
        self._update_variables_table()
        
        # Emit state updated signal
        self.state_updated.emit(self._current_state)
    
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """
        Handle item change in variables table.
        
        Args:
            item: Changed table item
        """
        # Ignore changes in the type column
        if item.column() == 2:
            return
        
        # Get row and variable name
        row = item.row()
        name_item = self.variables_table.item(row, 0)
        if not name_item:
            return
        
        # Get old name and new name
        old_name = list(self._current_state.keys())[row] if row < len(self._current_state) else ""
        new_name = name_item.text()
        
        # Handle name change
        if item.column() == 0 and old_name != new_name:
            # Check if new name already exists
            if new_name in self._current_state and new_name != old_name:
                QMessageBox.warning(
                    self,
                    tr("Duplicate Variable"),
                    tr("Variable '{new_name}' already exists. Please use a different name.")
                )
                
                # Revert to old name
                name_item.setText(old_name)
                return
            
            # Rename key in state dictionary
            value = self._current_state.pop(old_name, None)
            self._current_state[new_name] = value
            
        # Handle value change
        elif item.column() == 1:
            value_item = self.variables_table.item(row, 1)
            if not value_item:
                return
            
            # Get current value and type
            current_value = self._current_state.get(new_name)
            current_type = type(current_value)
            
            # Try to convert new value to current type
            try:
                if current_type == bool:
                    # Special handling for booleans
                    value_text = value_item.text().lower()
                    if value_text in ['true', 'yes', '1', 'y', 't']:
                        new_value = True
                    elif value_text in ['false', 'no', '0', 'n', 'f']:
                        new_value = False
                    else:
                        raise ValueError(tr("Invalid boolean value"))
                elif current_type in [list, dict]:
                    # Parse JSON for complex types
                    new_value = json.loads(value_item.text())
                    if not isinstance(new_value, current_type):
                        raise TypeError(tr("Expected {current_type.__name__}, got {type(new_value).__name__}"))
                else:
                    # Convert simple types
                    new_value = current_type(value_item.text())
                
                # Update state
                self._current_state[new_name] = new_value
                
            except Exception as e:
                # Show error message
                QMessageBox.warning(
                    self,
                    tr("Invalid Value"),
                    tr("Failed to convert value to {current_type.__name__}: {str(e)}")
                )
                
                # Revert to old value
                value_item.setText(str(current_value))
                return
        
        # Emit state updated signal
        self.state_updated.emit(self._current_state)
    
    def _on_save_clicked(self) -> None:
        """Handle save state button click."""
        # Get state directory
        state_dir = Path("./scout/resources/states")
        if not state_dir.exists():
            state_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"state_{timestamp}.json"
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save State"),
            str(state_dir / default_filename),
            "State Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Save state
        try:
            with open(file_path, 'w') as f:
                json.dump(self._current_state, f, indent=2)
            
            QMessageBox.information(
                self,
                tr("State Saved"),
                tr("Game state successfully saved to {file_path}")
            )
            
            logger.info(f"Game state saved to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to save state: {str(e)}")
            )
            
            logger.error(f"Failed to save state: {str(e)}")
    
    def _on_load_clicked(self) -> None:
        """Handle load state button click."""
        # Check if current state has changes
        if self._current_state:
            result = QMessageBox.question(
                self,
                tr("Load State"),
                tr("Loading a state will replace current variables. Continue?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
        
        # Get state directory
        state_dir = Path("./scout/resources/states")
        if not state_dir.exists():
            state_dir.mkdir(parents=True, exist_ok=True)
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Load State"),
            "Load State",
            str(state_dir),
            "State Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Load state
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Set new state
            self.set_state(state)
            
            # Emit state updated signal
            self.state_updated.emit(self._current_state)
            
            QMessageBox.information(
                self,
                "State Loaded",
                f"Game state successfully loaded from {file_path}"
            )
            
            logger.info(f"Game state loaded from {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load state: {str(e)}"
            )
            
            logger.error(f"Failed to load state: {str(e)}")


class StateTransitionEditor(QWidget):
    """
    Widget for editing game state transitions.
    
    This widget provides an interface for defining transitions between game states
    based on detection results or time intervals.
    """
    
    def __init__(self, game_state_service: GameStateServiceInterface,
                detection_service: DetectionServiceInterface):
        """
        Initialize the state transition editor.
        
        Args:
            game_state_service: Service for managing game state
            detection_service: Service for detection operations
        """
        super().__init__()
        
        # Store services
        self.game_state_service = game_state_service
        self.detection_service = detection_service
        
        # Initialize state
        self._transitions = []
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # Add transition button
        self.add_btn = QPushButton("Add Transition")
        toolbar_layout.addWidget(self.add_btn)
        
        # Edit transition button
        self.edit_btn = QPushButton("Edit Transition")
        self.edit_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_btn)
        
        # Remove transition button
        self.remove_btn = QPushButton("Remove Transition")
        self.remove_btn.setEnabled(False)
        toolbar_layout.addWidget(self.remove_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create transitions list
        self.transitions_list = QListWidget()
        main_layout.addWidget(self.transitions_list)
        
        # Create details section
        details_group = QGroupBox("Transition Details")
        details_layout = QGridLayout(details_group)
        
        # From state
        details_layout.addWidget(QLabel("From State:"), 0, 0)
        self.from_state_label = QLabel("N/A")
        details_layout.addWidget(self.from_state_label, 0, 1)
        
        # To state
        details_layout.addWidget(QLabel("To State:"), 1, 0)
        self.to_state_label = QLabel("N/A")
        details_layout.addWidget(self.to_state_label, 1, 1)
        
        # Trigger type
        details_layout.addWidget(QLabel("Trigger Type:"), 2, 0)
        self.trigger_type_label = QLabel("N/A")
        details_layout.addWidget(self.trigger_type_label, 2, 1)
        
        # Condition
        details_layout.addWidget(QLabel("Condition:"), 3, 0)
        self.condition_label = QLabel("N/A")
        details_layout.addWidget(self.condition_label, 3, 1)
        
        # Variables to update
        details_layout.addWidget(QLabel("Variables Updated:"), 4, 0)
        self.variables_label = QLabel("N/A")
        details_layout.addWidget(self.variables_label, 4, 1)
        
        main_layout.addWidget(details_group)
        
        # Enable/disable transition button
        self.enable_btn = QPushButton("Enable Transition")
        self.enable_btn.setEnabled(False)
        main_layout.addWidget(self.enable_btn)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Toolbar buttons
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.enable_btn.clicked.connect(self._on_enable_clicked)
        
        # Transitions list selection
        self.transitions_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in transitions list."""
        # Get selected items
        selected_items = self.transitions_list.selectedItems()
        
        # Enable/disable buttons
        self.edit_btn.setEnabled(len(selected_items) > 0)
        self.remove_btn.setEnabled(len(selected_items) > 0)
        self.enable_btn.setEnabled(len(selected_items) > 0)
        
        # Update details section
        if selected_items:
            # Get transition index
            index = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if 0 <= index < len(self._transitions):
                transition = self._transitions[index]
                
                # Update labels
                self.from_state_label.setText(transition.get('from_state', 'Any'))
                self.to_state_label.setText(transition.get('to_state', 'N/A'))
                self.trigger_type_label.setText(transition.get('trigger_type', 'N/A'))
                
                # Format condition based on trigger type
                trigger_type = transition.get('trigger_type', '')
                condition = ''
                
                if trigger_type == 'template_detected':
                    template = transition.get('template', '')
                    confidence = transition.get('confidence', 0.7)
                    condition = f"Template '{template}' detected with confidence >= {confidence}"
                
                elif trigger_type == 'ocr_text_detected':
                    text = transition.get('text', '')
                    confidence = transition.get('confidence', 0.7)
                    condition = f"OCR Text '{text}' detected with confidence >= {confidence}"
                
                elif trigger_type == 'variable_condition':
                    variable = transition.get('variable', '')
                    operator = transition.get('operator', '==')
                    value = transition.get('value', '')
                    condition = f"{variable} {operator} {value}"
                
                elif trigger_type == 'time_interval':
                    interval = transition.get('interval', 0)
                    condition = f"Every {interval} ms"
                
                self.condition_label.setText(condition)
                
                # Format variables to update
                variables = transition.get('variables_update', {})
                if variables:
                    variables_text = "; ".join([f"{k}={v}" for k, v in variables.items()])
                else:
                    variables_text = "None"
                
                self.variables_label.setText(variables_text)
                
                # Update enable button text
                enabled = transition.get('enabled', True)
                self.enable_btn.setText("Disable Transition" if enabled else "Enable Transition")
                
            else:
                self._clear_details()
        else:
            self._clear_details()
    
    def _clear_details(self) -> None:
        """Clear the details section."""
        self.from_state_label.setText("N/A")
        self.to_state_label.setText("N/A")
        self.trigger_type_label.setText("N/A")
        self.condition_label.setText("N/A")
        self.variables_label.setText("N/A")
        self.enable_btn.setText("Enable Transition")
    
    def _on_add_clicked(self) -> None:
        """Handle add transition button click."""
        # Show transition editor dialog
        # This would be a complex dialog with multiple fields
        # For now, just create a simple transition
        
        # Create default transition
        transition = {
            'id': f"transition_{len(self._transitions) + 1}",
            'name': f"Transition {len(self._transitions) + 1}",
            'from_state': "Any",
            'to_state': "Default",
            'trigger_type': "template_detected",
            'template': "example_template",
            'confidence': 0.7,
            'variables_update': {},
            'enabled': True
        }
        
        # Add to transitions list
        self._transitions.append(transition)
        
        # Update list
        self._update_transitions_list()
        
        # Select new transition
        self.transitions_list.setCurrentRow(len(self._transitions) - 1)
    
    def _on_edit_clicked(self) -> None:
        """Handle edit transition button click."""
        # TODO: Implement transition editor dialog
        QMessageBox.information(
            self,
            "Not Implemented",
            "Transition editor dialog not yet implemented."
        )
    
    def _on_remove_clicked(self) -> None:
        """Handle remove transition button click."""
        # Get selected items
        selected_items = self.transitions_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get transition index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Remove Transition",
            f"Are you sure you want to remove transition {index + 1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Remove transition
        if 0 <= index < len(self._transitions):
            del self._transitions[index]
            
            # Update list
            self._update_transitions_list()
            
            # Clear selection if list is empty
            if not self._transitions:
                self._clear_details()
    
    def _on_enable_clicked(self) -> None:
        """Handle enable/disable transition button click."""
        # Get selected items
        selected_items = self.transitions_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get transition index
        index = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Toggle enabled state
        if 0 <= index < len(self._transitions):
            transition = self._transitions[index]
            transition['enabled'] = not transition.get('enabled', True)
            
            # Update list
            self._update_transitions_list()
            
            # Update enable button text
            enabled = transition.get('enabled', True)
            self.enable_btn.setText("Disable Transition" if enabled else "Enable Transition")
    
    def _update_transitions_list(self) -> None:
        """Update the transitions list with current transitions."""
        # Clear list
        self.transitions_list.clear()
        
        # Add each transition
        for i, transition in enumerate(self._transitions):
            # Create item text
            name = transition.get('name', f"Transition {i + 1}")
            from_state = transition.get('from_state', 'Any')
            to_state = transition.get('to_state', 'Default')
            enabled = transition.get('enabled', True)
            
            item_text = f"{name} ({from_state} → {to_state})"
            
            # Create item
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store transition index
            
            # Set color based on enabled state
            if not enabled:
                item.setForeground(QColor(150, 150, 150))  # Grey for disabled
            
            # Add to list
            self.transitions_list.addItem(item)


class StateHistoryView(QWidget):
    """
    Widget for viewing game state history.
    
    This widget provides a visual representation of state changes over time,
    including transitions and variable updates.
    """
    
    def __init__(self, game_state_service: GameStateServiceInterface):
        """
        Initialize the state history view.
        
        Args:
            game_state_service: Service for managing game state
        """
        super().__init__()
        
        # Store services
        self.game_state_service = game_state_service
        
        # Initialize state
        self._history = []
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # Clear history button
        self.clear_btn = QPushButton("Clear History")
        toolbar_layout.addWidget(self.clear_btn)
        
        # Export history button
        self.export_btn = QPushButton("Export History")
        toolbar_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create history table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Time", "Event Type", "State", "Details"])
        
        # Configure table
        self.history_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch)
        
        main_layout.addWidget(self.history_table)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Toolbar buttons
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
    
    def add_event(self, event_type: str, state: str, details: str) -> None:
        """
        Add an event to the history.
        
        Args:
            event_type: Type of event (e.g., "Transition", "Variable Update")
            state: Current state name
            details: Additional details about the event
        """
        # Create timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Add to history
        self._history.append({
            'time': timestamp,
            'event_type': event_type,
            'state': state,
            'details': details
        })
        
        # Update table
        self._update_history_table()
    
    def _update_history_table(self) -> None:
        """Update the history table with current history."""
        # Set row count
        self.history_table.setRowCount(len(self._history))
        
        # Add each event
        for i, event in enumerate(self._history):
            # Time
            time_item = QTableWidgetItem(event.get('time', ''))
            self.history_table.setItem(i, 0, time_item)
            
            # Event type
            type_item = QTableWidgetItem(event.get('event_type', ''))
            self.history_table.setItem(i, 1, type_item)
            
            # State
            state_item = QTableWidgetItem(event.get('state', ''))
            self.history_table.setItem(i, 2, state_item)
            
            # Details
            details_item = QTableWidgetItem(event.get('details', ''))
            self.history_table.setItem(i, 3, details_item)
        
        # Scroll to bottom
        self.history_table.scrollToBottom()
    
    def _on_clear_clicked(self) -> None:
        """Handle clear history button click."""
        # Confirm clearance
        result = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear the history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Clear history
        self._history = []
        
        # Update table
        self._update_history_table()
    
    def _on_export_clicked(self) -> None:
        """Handle export history button click."""
        if not self._history:
            QMessageBox.information(
                self,
                "Export History",
                "No history to export."
            )
            return
        
        # Get logs directory
        logs_dir = Path("./scout/resources/logs")
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"state_history_{timestamp}.json"
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History",
            str(logs_dir / default_filename),
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Determine export format from file extension
        if file_path.endswith('.json'):
            self._export_as_json(file_path)
        elif file_path.endswith('.csv'):
            self._export_as_csv(file_path)
        else:
            # Default to JSON
            self._export_as_json(file_path)
    
    def _export_as_json(self, file_path: str) -> None:
        """
        Export history as JSON.
        
        Args:
            file_path: Path to save the file
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self._history, f, indent=2)
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"History exported to {file_path}"
            )
            
            logger.info(f"State history exported to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export history: {str(e)}"
            )
            
            logger.error(f"Failed to export state history: {str(e)}")
    
    def _export_as_csv(self, file_path: str) -> None:
        """
        Export history as CSV.
        
        Args:
            file_path: Path to save the file
        """
        try:
            with open(file_path, 'w', newline='') as f:
                # Write header
                f.write("Time,Event Type,State,Details\n")
                
                # Write each row
                for event in self._history:
                    time = event.get('time', '')
                    event_type = event.get('event_type', '')
                    state = event.get('state', '')
                    details = event.get('details', '').replace('"', '""')  # Escape quotes
                    
                    f.write(f'"{time}","{event_type}","{state}","{details}"\n')
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"History exported to {file_path}"
            )
            
            logger.info(f"State history exported to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export history: {str(e)}"
            )
            
            logger.error(f"Failed to export state history: {str(e)}")


class GameTab(QWidget):
    """
    Tab for monitoring and managing game state.
    
    This tab provides an interface for:
    - Viewing and editing game state variables
    - Defining state transitions based on detection results
    - Viewing state history and logs
    """
    
    def __init__(
        self,
        game_state_service: GameStateServiceInterface,
        detection_service: DetectionServiceInterface
    ):
        """
        Initialize the game state tab.
        
        Args:
            game_state_service: Service for managing game state
            detection_service: Service for detection operations
        """
        super().__init__()
        
        # Store services
        self.game_state_service = game_state_service
        self.detection_service = detection_service
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Initialize with current state
        self._load_current_state()
        
        # Start update timer
        self._start_update_timer()
        
        logger.info("Game state tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Variables tab
        variables_tab = QWidget()
        variables_layout = QVBoxLayout(variables_tab)
        
        self.variable_editor = StateVariableEditor(self.game_state_service)
        variables_layout.addWidget(self.variable_editor)
        
        tabs.addTab(variables_tab, "Variables")
        
        # Transitions tab
        transitions_tab = QWidget()
        transitions_layout = QVBoxLayout(transitions_tab)
        
        self.transition_editor = StateTransitionEditor(
            self.game_state_service, self.detection_service)
        transitions_layout.addWidget(self.transition_editor)
        
        tabs.addTab(transitions_tab, "Transitions")
        
        # History tab
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        
        self.history_view = StateHistoryView(self.game_state_service)
        history_layout.addWidget(self.history_view)
        
        tabs.addTab(history_tab, "History")
        
        # Current state section
        state_group = QGroupBox("Current Game State")
        state_layout = QGridLayout(state_group)
        
        # State name
        state_layout.addWidget(QLabel("Current State:"), 0, 0)
        self.current_state_label = QLabel("Unknown")
        self.current_state_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        state_layout.addWidget(self.current_state_label, 0, 1)
        
        # State duration
        state_layout.addWidget(QLabel("Duration:"), 1, 0)
        self.duration_label = QLabel("0s")
        state_layout.addWidget(self.duration_label, 1, 1)
        
        # Variable count
        state_layout.addWidget(QLabel("Variables:"), 2, 0)
        self.variable_count_label = QLabel("0")
        state_layout.addWidget(self.variable_count_label, 2, 1)
        
        main_layout.addWidget(state_group)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Variable editor
        self.variable_editor.state_updated.connect(self._on_state_updated)
    
    def _load_current_state(self) -> None:
        """Load the current game state."""
        # TODO: Implement using actual game state service
        # For now, just use sample data
        
        state = {
            'current_state': 'Main Menu',
            'state_start_time': datetime.now(),
            'gold': 1000,
            'health': 100,
            'level': 1,
            'inventory': ['Sword', 'Potion'],
            'quest_progress': {
                'main_quest': 0.25,
                'side_quest_1': 0.5
            }
        }
        
        # Update variable editor
        self.variable_editor.set_state(state)
        
        # Update current state display
        self._update_current_state_display(state)
        
        # Add to history
        self.history_view.add_event(
            "Initial State",
            state.get('current_state', 'Unknown'),
            "Game state initialized"
        )
    
    def _update_current_state_display(self, state: Dict[str, Any]) -> None:
        """
        Update the current state display.
        
        Args:
            state: State dictionary
        """
        # Update state name
        current_state = state.get('current_state', 'Unknown')
        self.current_state_label.setText(current_state)
        
        # Calculate duration
        state_start_time = state.get('state_start_time', datetime.now())
        if isinstance(state_start_time, str):
            try:
                state_start_time = datetime.fromisoformat(state_start_time)
            except ValueError:
                state_start_time = datetime.now()
        
        duration = datetime.now() - state_start_time
        duration_seconds = duration.total_seconds()
        
        if duration_seconds < 60:
            duration_text = f"{duration_seconds:.1f}s"
        elif duration_seconds < 3600:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_text = f"{minutes}m {seconds}s"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            duration_text = f"{hours}h {minutes}m"
        
        self.duration_label.setText(duration_text)
        
        # Update variable count
        variable_count = len(state)
        self.variable_count_label.setText(str(variable_count))
    
    def _start_update_timer(self) -> None:
        """Start the update timer for regular state updates."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update_timer)
        self.update_timer.start(1000)  # Update every second
    
    def _on_update_timer(self) -> None:
        """Handle update timer tick."""
        # In a real implementation, we would get the latest state from the service
        # For now, just update the duration
        state = self.variable_editor._current_state
        self._update_current_state_display(state)
    
    def _on_state_updated(self, state: Dict[str, Any]) -> None:
        """
        Handle state updates from the variable editor.
        
        Args:
            state: Updated state dictionary
        """
        # Update current state display
        self._update_current_state_display(state)
        
        # Add to history
        self.history_view.add_event(
            "Variable Update",
            state.get('current_state', 'Unknown'),
            "Game state variables updated"
        )
        
        # In a real implementation, we would also update the game state service
        # TODO: Update game state service
    
    def closeEvent(self, event) -> None:
        """
        Handle tab closing.
        
        Args:
            event: Close event
        """
        # Stop the update timer
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        # Let the parent handle the event
        super().closeEvent(event) 