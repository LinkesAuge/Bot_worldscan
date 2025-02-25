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
        move_buttons_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton(tr("Move Down"))
        self.move_down_button.clicked.connect(self._on_move_down_clicked)
        self.move_down_button.setEnabled(False)
        move_buttons_layout.addWidget(self.move_down_button)
        
        actions_layout.addLayout(move_buttons_layout)
        
        # Loop checkbox
        loop_layout = QHBoxLayout()
        self.loop_check = QCheckBox(tr("Loop sequence"))
        loop_layout.addWidget(self.loop_check)
        actions_layout.addLayout(loop_layout)
        
        # Add actions group to left panel
        left_layout.addWidget(actions_group)
        
        # Add position list
        self.position_list = PositionList()
        left_layout.addWidget(self.position_list)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Create right panel for action editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create action editor
        self.action_editor = AutomationActionEditor()
        right_layout.addWidget(self.action_editor)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Create execution controls
        controls_layout = QHBoxLayout()
        
        self.run_button = QPushButton(tr("Run"))
        self.run_button.clicked.connect(self._on_run_clicked)
        controls_layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton(tr("Stop"))
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(controls_layout)

        # Connect signals 
        self.action_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.action_editor.action_updated.connect(self._on_action_updated)
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
        """Handle sequence selection change."""
        selected_sequence = self.sequence_combo.currentText()
        if selected_sequence != self._current_sequence["name"]:
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
    
    def _load_sequence(self, sequence_name: str) -> None:
        """
        Load a sequence by name.
        
        Args:
            sequence_name: Name of the sequence to load
        """
        # If sequence is already loaded, do nothing
        if sequence_name == self._current_sequence["name"]:
            return
            
        # For now, we just create a new empty sequence with the given name
        # In a real application, you'd load it from storage
        self._current_sequence = {"name": sequence_name, "actions": []}
        
        # Update UI
        self._update_action_list()
        
        # Update selected sequence in the combo box
        index = self.sequence_combo.findText(sequence_name)
        if index >= 0:
            self.sequence_combo.setCurrentIndex(index)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Sequence combo
        self.sequence_combo.currentIndexChanged.connect(self._on_sequence_changed)
        
        # File operations
        self.new_button.clicked.connect(self._on_new_clicked)
        self.open_button.clicked.connect(self._on_open_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)
        
        # Action list
        self.action_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Action operations
        self.add_button.clicked.connect(self._on_add_clicked)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.move_up_button.clicked.connect(self._on_move_up_clicked)
        self.move_down_button.clicked.connect(self._on_move_down_clicked)
        
        # Run controls
        self.run_button.clicked.connect(self._on_run_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        
        logger.debug("Connected automation tab signals") 

    def _update_sequence_list(self) -> None:
        """Update the sequence list with available sequences."""
        # Clear existing items
        self.sequence_combo.clear()
        
        # Add available sequences
        self.sequence_combo.addItem(self._current_sequence["name"])
        
        # TODO: Load sequences from disk/storage
        
        # Select current sequence
        self.sequence_combo.setCurrentText(self._current_sequence["name"])
        
        # Update action list
        self._update_action_list() 