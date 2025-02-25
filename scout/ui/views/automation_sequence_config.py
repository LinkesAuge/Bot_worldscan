"""
Automation Sequence Configuration

This module provides a UI component for configuring automation sequences.
It allows users to create, edit, and manage complex automation sequences through an
intuitive interface that supports various action types and configurations.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QTabWidget, QSlider, QDialog, QTableWidget,
    QHeaderView, QDialogButtonBox, QFormLayout, QTableWidgetItem,
    QAbstractItemView, QTreeWidget, QTreeWidgetItem, QDoubleSpinBox
)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor, QPixmap, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QEvent

from scout.core.automation.automation_service_interface import AutomationServiceInterface

# Set up logging
logger = logging.getLogger(__name__)

class AutomationSequenceConfig(QWidget):
    """
    UI component for configuring automation sequences.
    
    This widget provides an interface for creating and editing automation sequences
    with support for various action types, conditional logic, and sequence management.
    
    Features:
    - Creating and editing sequences
    - Adding, removing, and reordering actions
    - Configuring action parameters
    - Testing sequences
    - Importing and exporting sequences
    - Managing dependencies between actions
    
    The configuration component integrates with the AutomationService to execute
    and validate sequences.
    """
    
    # Signals
    sequence_created = pyqtSignal(str)  # Path to new sequence
    sequence_updated = pyqtSignal(str)  # Path to updated sequence
    sequence_deleted = pyqtSignal(str)  # Path to deleted sequence
    
    def __init__(self, automation_service: AutomationServiceInterface):
        """
        Initialize the automation sequence configuration widget.
        
        Args:
            automation_service: Service for executing and validating automation sequences
        """
        super().__init__()
        
        # Store dependencies
        self.automation_service = automation_service
        
        # Initialize state
        self.current_sequence: Dict[str, Any] = {
            'name': '',
            'description': '',
            'actions': []
        }
        self.current_sequence_path: Optional[str] = None
        self.sequences_dir = os.path.join('scout', 'resources', 'sequences')
        self.is_modified = False
        self.current_action_index = -1
        
        # Action types and their parameters
        self.action_types = {
            'click': {
                'name': 'Mouse Click',
                'description': 'Click at a specific location',
                'params': {
                    'x': {'type': 'int', 'default': 0, 'description': 'X coordinate'},
                    'y': {'type': 'int', 'default': 0, 'description': 'Y coordinate'},
                    'button': {'type': 'choice', 'default': 'left', 'options': ['left', 'right', 'middle'], 'description': 'Mouse button to click'},
                    'count': {'type': 'int', 'default': 1, 'description': 'Number of clicks'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'move': {
                'name': 'Mouse Move',
                'description': 'Move the mouse to a specific location',
                'params': {
                    'x': {'type': 'int', 'default': 0, 'description': 'X coordinate'},
                    'y': {'type': 'int', 'default': 0, 'description': 'Y coordinate'},
                    'duration': {'type': 'int', 'default': 200, 'description': 'Movement duration (ms)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'drag': {
                'name': 'Mouse Drag',
                'description': 'Drag from one location to another',
                'params': {
                    'start_x': {'type': 'int', 'default': 0, 'description': 'Start X coordinate'},
                    'start_y': {'type': 'int', 'default': 0, 'description': 'Start Y coordinate'},
                    'end_x': {'type': 'int', 'default': 100, 'description': 'End X coordinate'},
                    'end_y': {'type': 'int', 'default': 100, 'description': 'End Y coordinate'},
                    'duration': {'type': 'int', 'default': 500, 'description': 'Drag duration (ms)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'keypress': {
                'name': 'Key Press',
                'description': 'Press a keyboard key',
                'params': {
                    'key': {'type': 'string', 'default': '', 'description': 'Key to press (e.g., "a", "enter", "ctrl+c")'},
                    'duration': {'type': 'int', 'default': 100, 'description': 'Press duration (ms)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'text': {
                'name': 'Type Text',
                'description': 'Type a sequence of text',
                'params': {
                    'text': {'type': 'string', 'default': '', 'description': 'Text to type'},
                    'interval': {'type': 'int', 'default': 10, 'description': 'Interval between keystrokes (ms)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'wait': {
                'name': 'Wait',
                'description': 'Wait for a specified time',
                'params': {
                    'duration': {'type': 'int', 'default': 1000, 'description': 'Wait duration (ms)'}
                }
            },
            'detect': {
                'name': 'Detect',
                'description': 'Wait for an element to be detected',
                'params': {
                    'strategy': {'type': 'choice', 'default': 'template', 'options': ['template', 'ocr', 'yolo'], 'description': 'Detection strategy'},
                    'template': {'type': 'string', 'default': '', 'description': 'Template name (for template strategy)'},
                    'text': {'type': 'string', 'default': '', 'description': 'Text to detect (for OCR strategy)'},
                    'class_name': {'type': 'string', 'default': '', 'description': 'Class name (for YOLO strategy)'},
                    'timeout': {'type': 'int', 'default': 5000, 'description': 'Detection timeout (ms)'},
                    'confidence': {'type': 'float', 'default': 0.7, 'description': 'Minimum confidence threshold (0-1)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'condition': {
                'name': 'Condition',
                'description': 'Conditional branching based on detection',
                'params': {
                    'strategy': {'type': 'choice', 'default': 'template', 'options': ['template', 'ocr', 'yolo'], 'description': 'Detection strategy'},
                    'template': {'type': 'string', 'default': '', 'description': 'Template name (for template strategy)'},
                    'text': {'type': 'string', 'default': '', 'description': 'Text to detect (for OCR strategy)'},
                    'class_name': {'type': 'string', 'default': '', 'description': 'Class name (for YOLO strategy)'},
                    'confidence': {'type': 'float', 'default': 0.7, 'description': 'Minimum confidence threshold (0-1)'},
                    'true_action': {'type': 'int', 'default': -1, 'description': 'Action index to execute if condition is true (-1 for next)'},
                    'false_action': {'type': 'int', 'default': -1, 'description': 'Action index to execute if condition is false (-1 for next)'},
                    'timeout': {'type': 'int', 'default': 1000, 'description': 'Condition evaluation timeout (ms)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'loop': {
                'name': 'Loop',
                'description': 'Loop a sequence of actions',
                'params': {
                    'count': {'type': 'int', 'default': 5, 'description': 'Number of iterations (0 for infinite)'},
                    'start_action': {'type': 'int', 'default': -1, 'description': 'Starting action index (-1 for current)'},
                    'end_action': {'type': 'int', 'default': -1, 'description': 'Ending action index (-1 for current)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after each iteration (ms)'}
                }
            },
            'screenshot': {
                'name': 'Screenshot',
                'description': 'Take a screenshot',
                'params': {
                    'filename': {'type': 'string', 'default': '', 'description': 'Screenshot filename (empty for automatic naming)'},
                    'region_x': {'type': 'int', 'default': -1, 'description': 'Region start X (-1 for full screen)'},
                    'region_y': {'type': 'int', 'default': -1, 'description': 'Region start Y (-1 for full screen)'},
                    'region_width': {'type': 'int', 'default': -1, 'description': 'Region width (-1 for full screen)'},
                    'region_height': {'type': 'int', 'default': -1, 'description': 'Region height (-1 for full screen)'},
                    'delay': {'type': 'int', 'default': 100, 'description': 'Delay after action (ms)'}
                }
            },
            'comment': {
                'name': 'Comment',
                'description': 'Add a comment (no action)',
                'params': {
                    'text': {'type': 'string', 'default': '', 'description': 'Comment text'}
                }
            }
        }
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Set up initial state
        self._create_new_sequence()
        
        # Ensure sequences directory exists
        os.makedirs(self.sequences_dir, exist_ok=True)
        
        logger.info("Automation sequence configuration widget initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter to divide sequence list and editor
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Create sequence list panel (left side)
        sequence_panel = QWidget()
        sequence_layout = QVBoxLayout(sequence_panel)
        
        # Create sequence list label
        list_label = QLabel("Automation Sequences:")
        list_label.setStyleSheet("font-weight: bold;")
        sequence_layout.addWidget(list_label)
        
        # Create sequence list
        self.sequence_list = QListWidget()
        self.sequence_list.setMinimumWidth(200)
        self.sequence_list.setAlternatingRowColors(True)
        self.sequence_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        sequence_layout.addWidget(self.sequence_list)
        
        # Create sequence list buttons
        list_buttons_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.setToolTip("Create a new sequence")
        self.new_btn.setIcon(QIcon.fromTheme("document-new"))
        list_buttons_layout.addWidget(self.new_btn)
        
        self.open_btn = QPushButton("Open")
        self.open_btn.setToolTip("Open an existing sequence")
        self.open_btn.setIcon(QIcon.fromTheme("document-open"))
        list_buttons_layout.addWidget(self.open_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setToolTip("Remove the selected sequence")
        self.remove_btn.setIcon(QIcon.fromTheme("edit-delete"))
        list_buttons_layout.addWidget(self.remove_btn)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setToolTip("Duplicate the selected sequence")
        self.duplicate_btn.setIcon(QIcon.fromTheme("edit-copy"))
        list_buttons_layout.addWidget(self.duplicate_btn)
        
        sequence_layout.addLayout(list_buttons_layout)
        
        # Add sequence panel to splitter
        self.splitter.addWidget(sequence_panel)
        
        # Create editor panel (right side)
        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        
        # Create editor header with sequence details
        header_group = QGroupBox("Sequence Details")
        header_layout = QFormLayout()
        
        # Sequence name
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("Name of the sequence (must be unique)")
        header_layout.addRow("Name:", self.name_edit)
        
        # Sequence description
        self.description_edit = QLineEdit()
        self.description_edit.setToolTip("Brief description of the sequence's purpose")
        header_layout.addRow("Description:", self.description_edit)
        
        header_group.setLayout(header_layout)
        editor_layout.addWidget(header_group)
        
        # Create actions list
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        # Actions list
        self.actions_list = QListWidget()
        self.actions_list.setAlternatingRowColors(True)
        self.actions_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.actions_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.actions_list.setMinimumHeight(200)
        actions_layout.addWidget(self.actions_list)
        
        # Action buttons
        action_buttons_layout = QHBoxLayout()
        
        self.add_action_btn = QPushButton("Add")
        self.add_action_btn.setToolTip("Add a new action")
        self.add_action_btn.setIcon(QIcon.fromTheme("list-add"))
        action_buttons_layout.addWidget(self.add_action_btn)
        
        self.edit_action_btn = QPushButton("Edit")
        self.edit_action_btn.setToolTip("Edit the selected action")
        self.edit_action_btn.setIcon(QIcon.fromTheme("document-edit"))
        action_buttons_layout.addWidget(self.edit_action_btn)
        
        self.remove_action_btn = QPushButton("Remove")
        self.remove_action_btn.setToolTip("Remove the selected action")
        self.remove_action_btn.setIcon(QIcon.fromTheme("list-remove"))
        action_buttons_layout.addWidget(self.remove_action_btn)
        
        self.move_up_btn = QPushButton("Up")
        self.move_up_btn.setToolTip("Move the selected action up")
        self.move_up_btn.setIcon(QIcon.fromTheme("go-up"))
        action_buttons_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("Down")
        self.move_down_btn.setToolTip("Move the selected action down")
        self.move_down_btn.setIcon(QIcon.fromTheme("go-down"))
        action_buttons_layout.addWidget(self.move_down_btn)
        
        actions_layout.addLayout(action_buttons_layout)
        
        actions_group.setLayout(actions_layout)
        editor_layout.addWidget(actions_group)
        
        # Create action editor
        editor_group = QGroupBox("Action Editor")
        editor_inner_layout = QVBoxLayout()
        
        # Action type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Action Type:"))
        
        self.action_type_combo = QComboBox()
        
        # Add action types
        for action_type, details in self.action_types.items():
            self.action_type_combo.addItem(details['name'], action_type)
            
        type_layout.addWidget(self.action_type_combo)
        editor_inner_layout.addLayout(type_layout)
        
        # Action description
        self.action_description = QLabel()
        self.action_description.setStyleSheet("font-style: italic;")
        self.action_description.setWordWrap(True)
        editor_inner_layout.addWidget(self.action_description)
        
        # Action parameters
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        
        self.params_scroll.setWidget(self.params_widget)
        editor_inner_layout.addWidget(self.params_scroll)
        
        # Apply button
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setToolTip("Apply changes to the selected action")
        self.apply_btn.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        editor_inner_layout.addWidget(self.apply_btn)
        
        editor_group.setLayout(editor_inner_layout)
        editor_layout.addWidget(editor_group)
        
        # Create control buttons at the bottom
        controls_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save the current sequence")
        self.save_btn.setIcon(QIcon.fromTheme("document-save"))
        controls_layout.addWidget(self.save_btn)
        
        self.test_btn = QPushButton("Test")
        self.test_btn.setToolTip("Test the current sequence")
        self.test_btn.setIcon(QIcon.fromTheme("system-run"))
        controls_layout.addWidget(self.test_btn)
        
        self.import_btn = QPushButton("Import")
        self.import_btn.setToolTip("Import a sequence from a file")
        self.import_btn.setIcon(QIcon.fromTheme("document-import"))
        controls_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.setToolTip("Export the current sequence to a file")
        self.export_btn.setIcon(QIcon.fromTheme("document-export"))
        controls_layout.addWidget(self.export_btn)
        
        editor_layout.addLayout(controls_layout)
        
        # Add editor panel to splitter
        self.splitter.addWidget(editor_panel)
        
        # Set initial splitter sizes
        self.splitter.setSizes([1, 3])
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Sequence list buttons
        self.new_btn.clicked.connect(self._on_new_clicked)
        self.open_btn.clicked.connect(self._on_open_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.duplicate_btn.clicked.connect(self._on_duplicate_clicked)
        
        # Sequence list selection
        self.sequence_list.itemSelectionChanged.connect(self._on_sequence_selected)
        
        # Sequence details
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.description_edit.textChanged.connect(self._on_description_changed)
        
        # Actions list
        self.actions_list.itemSelectionChanged.connect(self._on_action_selected)
        self.actions_list.model().rowsMoved.connect(self._on_actions_reordered)
        
        # Action buttons
        self.add_action_btn.clicked.connect(self._on_add_action_clicked)
        self.edit_action_btn.clicked.connect(self._on_edit_action_clicked)
        self.remove_action_btn.clicked.connect(self._on_remove_action_clicked)
        self.move_up_btn.clicked.connect(self._on_move_up_clicked)
        self.move_down_btn.clicked.connect(self._on_move_down_clicked)
        
        # Action editor
        self.action_type_combo.currentIndexChanged.connect(self._on_action_type_changed)
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        
        # Control buttons
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.test_btn.clicked.connect(self._on_test_clicked)
        self.import_btn.clicked.connect(self._on_import_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
        
        # Initial action type update
        self._on_action_type_changed(self.action_type_combo.currentIndex())
    
    def _create_new_sequence(self) -> None:
        """Create a new empty sequence."""
        # Check for unsaved changes
        if self.is_modified:
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The current sequence has unsaved changes. Do you want to save it first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if result == QMessageBox.StandardButton.Cancel:
                return
                
            if result == QMessageBox.StandardButton.Yes:
                if not self._save_sequence():
                    return  # Cancel if save failed
        
        # Reset sequence
        self.current_sequence = {
            'name': 'New Sequence',
            'description': '',
            'actions': []
        }
        self.current_sequence_path = None
        self.is_modified = False
        
        # Update UI
        self.name_edit.setText(self.current_sequence['name'])
        self.description_edit.setText(self.current_sequence['description'])
        self.actions_list.clear()
        
        # Select appropriate item in sequence list
        self._select_current_sequence_in_list()
        
        logger.info("Created new sequence")
    
    def _load_sequence(self, path: str) -> bool:
        """
        Load a sequence from a file.
        
        Args:
            path: Path to the sequence file
            
        Returns:
            bool: True if sequence was loaded successfully, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(path):
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Sequence file does not exist: {path}"
                )
                return False
                
            # Load sequence
            with open(path, 'r') as f:
                data = json.load(f)
                
            # Validate sequence
            if 'name' not in data or 'actions' not in data:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Invalid sequence format: missing required fields"
                )
                return False
                
            # Update current sequence
            self.current_sequence = data
            self.current_sequence_path = path
            self.is_modified = False
            
            # Update UI
            self.name_edit.setText(self.current_sequence.get('name', ''))
            self.description_edit.setText(self.current_sequence.get('description', ''))
            
            # Update actions list
            self._update_actions_list()
            
            # Select appropriate item in sequence list
            self._select_current_sequence_in_list()
            
            logger.info(f"Loaded sequence from {path}")
            return True
            
        except json.JSONDecodeError:
            QMessageBox.critical(
                self,
                "Error",
                f"Invalid JSON format in sequence file: {path}"
            )
            return False
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load sequence: {str(e)}"
            )
            logger.error(f"Error loading sequence from {path}: {e}", exc_info=True)
            return False
    
    def _save_sequence(self) -> bool:
        """
        Save the current sequence to a file.
        
        Returns:
            bool: True if sequence was saved successfully, False otherwise
        """
        try:
            # Validate sequence
            if not self.current_sequence.get('name'):
                QMessageBox.critical(
                    self,
                    "Error",
                    "Sequence name cannot be empty"
                )
                return False
                
            # Determine save path
            if self.current_sequence_path is None:
                # Generate filename from sequence name
                filename = self._sanitize_filename(self.current_sequence['name']) + '.json'
                self.current_sequence_path = os.path.join(self.sequences_dir, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.current_sequence_path), exist_ok=True)
            
            # Save sequence
            with open(self.current_sequence_path, 'w') as f:
                json.dump(self.current_sequence, f, indent=4)
                
            self.is_modified = False
            
            # Update sequence list
            self._refresh_sequence_list()
            
            # Select appropriate item in sequence list
            self._select_current_sequence_in_list()
            
            # Emit signal
            self.sequence_updated.emit(self.current_sequence_path)
            
            logger.info(f"Saved sequence to {self.current_sequence_path}")
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save sequence: {str(e)}"
            )
            logger.error(f"Error saving sequence: {e}", exc_info=True)
            return False
    
    def _refresh_sequence_list(self) -> None:
        """Refresh the list of available sequences."""
        # Save current selection
        selected_path = None
        if self.sequence_list.currentItem() is not None:
            selected_path = self.sequence_list.currentItem().data(Qt.ItemDataRole.UserRole)
            
        # Clear list
        self.sequence_list.clear()
        
        try:
            # Get all JSON files in sequences directory
            if os.path.exists(self.sequences_dir):
                filenames = sorted([f for f in os.listdir(self.sequences_dir) if f.endswith('.json')])
                
                for filename in filenames:
                    path = os.path.join(self.sequences_dir, filename)
                    
                    # Load sequence name
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                            name = data.get('name', os.path.splitext(filename)[0])
                    except:
                        name = os.path.splitext(filename)[0]
                        
                    # Create list item
                    item = QListWidgetItem(name)
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    self.sequence_list.addItem(item)
                    
                    # Re-select previously selected item
                    if selected_path == path:
                        self.sequence_list.setCurrentItem(item)
        except Exception as e:
            logger.error(f"Error refreshing sequence list: {e}", exc_info=True)
    
    def _update_actions_list(self) -> None:
        """Update the actions list with the current sequence actions."""
        self.actions_list.clear()
        
        for i, action in enumerate(self.current_sequence.get('actions', [])):
            # Get action type and name
            action_type = action.get('type', 'unknown')
            action_type_info = self.action_types.get(action_type, {'name': 'Unknown'})
            
            # Create list item
            item_text = f"{i+1}. {action_type_info['name']}"
            
            # Add action-specific information
            if action_type == 'click':
                item_text += f" ({action.get('x', 0)}, {action.get('y', 0)})"
            elif action_type == 'move':
                item_text += f" ({action.get('x', 0)}, {action.get('y', 0)})"
            elif action_type == 'drag':
                item_text += f" ({action.get('start_x', 0)}, {action.get('start_y', 0)}) → ({action.get('end_x', 0)}, {action.get('end_y', 0)})"
            elif action_type == 'keypress':
                item_text += f" {action.get('key', '')}"
            elif action_type == 'text':
                text = action.get('text', '')
                if len(text) > 20:
                    text = text[:17] + "..."
                item_text += f" '{text}'"
            elif action_type == 'wait':
                item_text += f" {action.get('duration', 0)}ms"
            elif action_type == 'detect':
                strategy = action.get('strategy', 'template')
                if strategy == 'template':
                    item_text += f" (Template: {action.get('template', '')})"
                elif strategy == 'ocr':
                    item_text += f" (OCR: {action.get('text', '')})"
                elif strategy == 'yolo':
                    item_text += f" (YOLO: {action.get('class_name', '')})"
            elif action_type == 'comment':
                text = action.get('text', '')
                if len(text) > 30:
                    text = text[:27] + "..."
                item_text += f" ({text})"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store action index
            self.actions_list.addItem(item)
    
    def _select_current_sequence_in_list(self) -> None:
        """Select the current sequence in the sequence list."""
        if self.current_sequence_path is None:
            return
            
        # Find and select the item
        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_sequence_path:
                self.sequence_list.setCurrentItem(item)
                return
    
    def _update_action_editor(self, action: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the action editor with the current action parameters.
        
        Args:
            action: Action to edit (None for new action)
        """
        # Clear existing parameter widgets
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if action is None:
            # New action, use default parameters
            action_type = self.action_type_combo.currentData()
            self.param_widgets = {}
            
            # Create parameter widgets
            if action_type in self.action_types:
                action_params = self.action_types[action_type]['params']
                
                for param_name, param_info in action_params.items():
                    # Create widget based on parameter type
                    widget = self._create_param_widget(param_name, param_info)
                    
                    if widget:
                        self.param_widgets[param_name] = widget
                        self.params_layout.addRow(f"{param_info['description']}:", widget)
        else:
            # Existing action, use action parameters
            action_type = action.get('type', 'unknown')
            
            if action_type in self.action_types:
                # Set action type in combo box
                index = self.action_type_combo.findData(action_type)
                if index >= 0:
                    self.action_type_combo.setCurrentIndex(index)
                
                action_params = self.action_types[action_type]['params']
                self.param_widgets = {}
                
                # Create parameter widgets with action values
                for param_name, param_info in action_params.items():
                    # Get current value (or default if not present)
                    value = action.get(param_name, param_info['default'])
                    
                    # Create widget based on parameter type
                    widget = self._create_param_widget(param_name, param_info, value)
                    
                    if widget:
                        self.param_widgets[param_name] = widget
                        self.params_layout.addRow(f"{param_info['description']}:", widget)
    
    def _create_param_widget(self, param_name: str, param_info: Dict[str, Any], value: Any = None) -> Optional[QWidget]:
        """
        Create a widget for a parameter based on its type.
        
        Args:
            param_name: Parameter name
            param_info: Parameter information
            value: Current value (None for default)
            
        Returns:
            Created widget or None if type is not supported
        """
        param_type = param_info.get('type', 'string')
        default_value = param_info.get('default')
        
        # Use provided value or default
        if value is None:
            value = default_value
            
        if param_type == 'string':
            widget = QLineEdit()
            widget.setText(str(value))
            return widget
            
        elif param_type == 'int':
            widget = QSpinBox()
            widget.setRange(-100000, 100000)  # Wide range
            widget.setValue(int(value))
            return widget
            
        elif param_type == 'float':
            widget = QDoubleSpinBox()
            widget.setRange(-100000, 100000)  # Wide range
            widget.setDecimals(2)
            widget.setSingleStep(0.1)
            widget.setValue(float(value))
            return widget
            
        elif param_type == 'bool':
            widget = QCheckBox()
            widget.setChecked(bool(value))
            return widget
            
        elif param_type == 'choice':
            widget = QComboBox()
            options = param_info.get('options', [])
            widget.addItems(options)
            
            current_index = options.index(value) if value in options else 0
            widget.setCurrentIndex(current_index)
            return widget
            
        return None
    
    def _get_param_value(self, widget: QWidget, param_type: str) -> Any:
        """
        Get the value from a parameter widget.
        
        Args:
            widget: Widget to get value from
            param_type: Parameter type
            
        Returns:
            Parameter value
        """
        if param_type == 'string':
            return widget.text()
            
        elif param_type == 'int':
            return widget.value()
            
        elif param_type == 'float':
            return widget.value()
            
        elif param_type == 'bool':
            return widget.isChecked()
            
        elif param_type == 'choice':
            return widget.currentText()
            
        return None
    
    def _collect_action_params(self) -> Dict[str, Any]:
        """
        Collect action parameters from the UI.
        
        Returns:
            Dictionary with action parameters
        """
        action_type = self.action_type_combo.currentData()
        params = {'type': action_type}
        
        if action_type in self.action_types:
            action_params = self.action_types[action_type]['params']
            
            for param_name, param_info in action_params.items():
                if param_name in self.param_widgets:
                    param_type = param_info.get('type', 'string')
                    value = self._get_param_value(self.param_widgets[param_name], param_type)
                    params[param_name] = value
        
        return params
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename.
        
        Args:
            name: String to sanitize
            
        Returns:
            Sanitized string
        """
        # Replace spaces with underscores and remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        return ''.join(c if c not in invalid_chars else '_' for c in name.replace(' ', '_'))
    
    def _validate_sequence(self) -> Tuple[bool, str]:
        """
        Validate the current sequence.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check name
        if not self.current_sequence.get('name', ''):
            return False, "Sequence name cannot be empty"
            
        # Check actions
        if not self.current_sequence.get('actions', []):
            return False, "Sequence must have at least one action"
            
        # Check for valid action parameters
        for i, action in enumerate(self.current_sequence.get('actions', [])):
            action_type = action.get('type')
            
            if action_type not in self.action_types:
                return False, f"Action {i+1} has an invalid type: {action_type}"
                
            # Check required parameters
            action_params = self.action_types[action_type]['params']
            for param_name, param_info in action_params.items():
                if param_name not in action and param_info.get('required', False):
                    return False, f"Action {i+1} is missing required parameter: {param_name}"
        
        return True, ""
    
    def _on_new_clicked(self) -> None:
        """Handle New button click."""
        self._create_new_sequence()
    
    def _on_open_clicked(self) -> None:
        """Handle Open button click."""
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Sequence",
            self.sequences_dir,
            "JSON Files (*.json)"
        )
        
        if file_path:
            # Check for unsaved changes
            if self.is_modified:
                result = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "The current sequence has unsaved changes. Do you want to save it first?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes
                )
                
                if result == QMessageBox.StandardButton.Cancel:
                    return
                    
                if result == QMessageBox.StandardButton.Yes:
                    if not self._save_sequence():
                        return  # Cancel if save failed
            
            # Load selected sequence
            self._load_sequence(file_path)
    
    def _on_remove_clicked(self) -> None:
        """Handle Remove button click."""
        # Get selected sequence
        selected_item = self.sequence_list.currentItem()
        if not selected_item:
            return
            
        path = selected_item.data(Qt.ItemDataRole.UserRole)
        name = selected_item.text()
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the sequence '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        try:
            # Delete the file
            if os.path.exists(path):
                os.remove(path)
                
            # Update list
            self._refresh_sequence_list()
            
            # Create new sequence if the current one was deleted
            if self.current_sequence_path == path:
                self._create_new_sequence()
                
            # Emit signal
            self.sequence_deleted.emit(path)
            
            logger.info(f"Removed sequence: {path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete sequence: {str(e)}"
            )
            logger.error(f"Error deleting sequence {path}: {e}", exc_info=True)
    
    def _on_duplicate_clicked(self) -> None:
        """Handle Duplicate button click."""
        # Get selected sequence
        selected_item = self.sequence_list.currentItem()
        if not selected_item:
            return
            
        path = selected_item.data(Qt.ItemDataRole.UserRole)
        
        try:
            # Load sequence
            with open(path, 'r') as f:
                data = json.load(f)
                
            # Create a copy
            name, _ = QInputDialog.getText(
                self,
                "Duplicate Sequence",
                "Enter name for the duplicate sequence:",
                QLineEdit.EchoMode.Normal,
                data.get('name', '') + " (Copy)"
            )
            
            if not name:
                return
                
            data['name'] = name
            
            # Generate filename
            filename = self._sanitize_filename(name) + '.json'
            new_path = os.path.join(self.sequences_dir, filename)
            
            # Save duplicate
            with open(new_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            # Update list
            self._refresh_sequence_list()
            
            # Load the duplicate
            self._load_sequence(new_path)
            
            # Emit signal
            self.sequence_created.emit(new_path)
            
            logger.info(f"Duplicated sequence {path} to {new_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to duplicate sequence: {str(e)}"
            )
            logger.error(f"Error duplicating sequence {path}: {e}", exc_info=True)
    
    def _on_sequence_selected(self) -> None:
        """Handle sequence selection change."""
        # Get selected sequence
        selected_item = self.sequence_list.currentItem()
        if not selected_item:
            return
            
        path = selected_item.data(Qt.ItemDataRole.UserRole)
        
        # Check if we're already editing this sequence
        if path == self.current_sequence_path:
            return
            
        # Check for unsaved changes
        if self.is_modified:
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The current sequence has unsaved changes. Do you want to save it first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if result == QMessageBox.StandardButton.Cancel:
                # Revert selection
                self._select_current_sequence_in_list()
                return
                
            if result == QMessageBox.StandardButton.Yes:
                if not self._save_sequence():
                    # Revert selection
                    self._select_current_sequence_in_list()
                    return
        
        # Load selected sequence
        if not self._load_sequence(path):
            # Revert selection
            self._select_current_sequence_in_list()
    
    def _on_name_changed(self, text: str) -> None:
        """
        Handle sequence name change.
        
        Args:
            text: New name
        """
        if self.current_sequence.get('name') != text:
            self.current_sequence['name'] = text
            self.is_modified = True
    
    def _on_description_changed(self, text: str) -> None:
        """
        Handle sequence description change.
        
        Args:
            text: New description
        """
        if self.current_sequence.get('description') != text:
            self.current_sequence['description'] = text
            self.is_modified = True
    
    def _on_action_selected(self) -> None:
        """Handle action selection change."""
        # Get selected action
        selected_item = self.actions_list.currentItem()
        if not selected_item:
            self.current_action_index = -1
            self._update_action_editor()
            return
            
        self.current_action_index = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if 0 <= self.current_action_index < len(self.current_sequence.get('actions', [])):
            action = self.current_sequence['actions'][self.current_action_index]
            self._update_action_editor(action)
    
    def _on_actions_reordered(self) -> None:
        """Handle actions being reordered via drag and drop."""
        # Create a new actions list based on the current order
        new_actions = []
        
        for i in range(self.actions_list.count()):
            item = self.actions_list.item(i)
            index = item.data(Qt.ItemDataRole.UserRole)
            
            if 0 <= index < len(self.current_sequence.get('actions', [])):
                new_actions.append(self.current_sequence['actions'][index])
        
        # Update sequence
        self.current_sequence['actions'] = new_actions
        self.is_modified = True
        
        # Update UI
        self._update_actions_list()
    
    def _on_add_action_clicked(self) -> None:
        """Handle Add Action button click."""
        # Get selected action type
        action_type = self.action_type_combo.currentData()
        
        # Create new action with default parameters
        action = {'type': action_type}
        
        if action_type in self.action_types:
            action_params = self.action_types[action_type]['params']
            
            for param_name, param_info in action_params.items():
                action[param_name] = param_info['default']
        
        # Add action to sequence
        if 'actions' not in self.current_sequence:
            self.current_sequence['actions'] = []
            
        self.current_sequence['actions'].append(action)
        self.is_modified = True
        
        # Update UI
        self._update_actions_list()
        
        # Select the new action
        self.actions_list.setCurrentRow(self.actions_list.count() - 1)
    
    def _on_edit_action_clicked(self) -> None:
        """Handle Edit Action button click."""
        # Get selected action
        selected_item = self.actions_list.currentItem()
        if not selected_item:
            return
            
        self.current_action_index = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if 0 <= self.current_action_index < len(self.current_sequence.get('actions', [])):
            action = self.current_sequence['actions'][self.current_action_index]
            self._update_action_editor(action)
    
    def _on_remove_action_clicked(self) -> None:
        """Handle Remove Action button click."""
        # Get selected action
        selected_item = self.actions_list.currentItem()
        if not selected_item:
            return
            
        index = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if 0 <= index < len(self.current_sequence.get('actions', [])):
            # Remove action
            del self.current_sequence['actions'][index]
            self.is_modified = True
            
            # Update UI
            self._update_actions_list()
            
            # Select an appropriate item
            if self.actions_list.count() > 0:
                self.actions_list.setCurrentRow(min(index, self.actions_list.count() - 1))
    
    def _on_move_up_clicked(self) -> None:
        """Handle Move Up button click."""
        # Get selected action
        selected_item = self.actions_list.currentItem()
        if not selected_item:
            return
            
        index = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if 0 < index < len(self.current_sequence.get('actions', [])):
            # Swap with previous action
            self.current_sequence['actions'][index], self.current_sequence['actions'][index-1] = \
                self.current_sequence['actions'][index-1], self.current_sequence['actions'][index]
            self.is_modified = True
            
            # Update UI
            self._update_actions_list()
            
            # Select the moved item
            self.actions_list.setCurrentRow(index - 1)
    
    def _on_move_down_clicked(self) -> None:
        """Handle Move Down button click."""
        # Get selected action
        selected_item = self.actions_list.currentItem()
        if not selected_item:
            return
            
        index = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if 0 <= index < len(self.current_sequence.get('actions', [])) - 1:
            # Swap with next action
            self.current_sequence['actions'][index], self.current_sequence['actions'][index+1] = \
                self.current_sequence['actions'][index+1], self.current_sequence['actions'][index]
            self.is_modified = True
            
            # Update UI
            self._update_actions_list()
            
            # Select the moved item
            self.actions_list.setCurrentRow(index + 1)
    
    def _on_action_type_changed(self, index: int) -> None:
        """
        Handle action type change.
        
        Args:
            index: Index of the selected action type
        """
        action_type = self.action_type_combo.itemData(index)
        
        if action_type in self.action_types:
            # Update description
            self.action_description.setText(self.action_types[action_type]['description'])
            
            # Update parameters if no action is selected
            if self.current_action_index == -1:
                self._update_action_editor()
    
    def _on_apply_clicked(self) -> None:
        """Handle Apply Changes button click."""
        if self.current_action_index == -1:
            return
            
        if 0 <= self.current_action_index < len(self.current_sequence.get('actions', [])):
            # Collect parameters
            action = self._collect_action_params()
            
            # Update action
            self.current_sequence['actions'][self.current_action_index] = action
            self.is_modified = True
            
            # Update UI
            self._update_actions_list()
            
            # Maintain selection
            self.actions_list.setCurrentRow(self.current_action_index)
    
    def _on_save_clicked(self) -> None:
        """Handle Save button click."""
        self._save_sequence()
    
    def _on_test_clicked(self) -> None:
        """Handle Test button click."""
        # Validate sequence
        valid, error = self._validate_sequence()
        if not valid:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"The sequence is not valid: {error}"
            )
            return
            
        # Save sequence if modified
        if self.is_modified:
            result = QMessageBox.question(
                self,
                "Save Before Testing",
                "The sequence must be saved before testing. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
                
            if not self._save_sequence():
                return
        
        # Test the sequence
        try:
            # Load the sequence into the automation service
            success = self.automation_service.load_sequence(self.current_sequence_path)
            
            if not success:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to load sequence into automation service"
                )
                return
                
            # Confirm execution
            result = QMessageBox.question(
                self,
                "Test Sequence",
                f"Ready to test sequence '{self.current_sequence['name']}'. "
                "Make sure the target application is ready. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
                
            # Execute the sequence
            self.automation_service.execute_sequence(simulation_mode=False)
            
            logger.info(f"Executed sequence: {self.current_sequence_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to test sequence: {str(e)}"
            )
            logger.error(f"Error testing sequence: {e}", exc_info=True)
    
    def _on_import_clicked(self) -> None:
        """Handle Import button click."""
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sequence",
            str(Path.home()),
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        # Check for unsaved changes
        if self.is_modified:
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The current sequence has unsaved changes. Do you want to save it first?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if result == QMessageBox.StandardButton.Cancel:
                return
                
            if result == QMessageBox.StandardButton.Yes:
                if not self._save_sequence():
                    return
        
        try:
            # Load sequence from file
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Validate sequence
            if 'name' not in data or 'actions' not in data:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Invalid sequence format: missing required fields"
                )
                return
                
            # Ask for name if importing to sequences directory
            copy_to_sequences = QMessageBox.question(
                self,
                "Import Sequence",
                "Do you want to copy this sequence to the sequences directory?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            ) == QMessageBox.StandardButton.Yes
            
            if copy_to_sequences:
                # Ask for name
                new_name, ok = QInputDialog.getText(
                    self,
                    "Sequence Name",
                    "Enter a name for the imported sequence:",
                    QLineEdit.EchoMode.Normal,
                    data.get('name', '')
                )
                
                if not ok or not new_name:
                    return
                    
                # Set new name
                data['name'] = new_name
                
                # Generate filename
                filename = self._sanitize_filename(new_name) + '.json'
                import_path = os.path.join(self.sequences_dir, filename)
                
                # Save to sequences directory
                with open(import_path, 'w') as f:
                    json.dump(data, f, indent=4)
                    
                # Refresh sequence list
                self._refresh_sequence_list()
                
                # Load the imported sequence
                self._load_sequence(import_path)
                
                # Emit signal
                self.sequence_created.emit(import_path)
                
                logger.info(f"Imported sequence to {import_path}")
                
            else:
                # Just load the sequence without saving
                self.current_sequence = data
                self.current_sequence_path = None
                self.is_modified = True
                
                # Update UI
                self.name_edit.setText(self.current_sequence.get('name', ''))
                self.description_edit.setText(self.current_sequence.get('description', ''))
                self._update_actions_list()
                
                logger.info(f"Loaded sequence from {file_path} (not saved)")
                
        except json.JSONDecodeError:
            QMessageBox.critical(
                self,
                "Error",
                f"Invalid JSON format in sequence file: {file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to import sequence: {str(e)}"
            )
            logger.error(f"Error importing sequence from {file_path}: {e}", exc_info=True)
    
    def _on_export_clicked(self) -> None:
        """Handle Export button click."""
        # Validate sequence
        valid, error = self._validate_sequence()
        if not valid:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"The sequence is not valid: {error}"
            )
            return
            
        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sequence",
            str(Path.home()),
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Save sequence to file
            with open(file_path, 'w') as f:
                json.dump(self.current_sequence, f, indent=4)
                
            logger.info(f"Exported sequence to {file_path}")
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Sequence exported to {file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to export sequence: {str(e)}"
            )
            logger.error(f"Error exporting sequence to {file_path}: {e}", exc_info=True)
    
    def set_sequences_directory(self, directory: str) -> None:
        """
        Set the directory for sequences.
        
        Args:
            directory: Directory path
        """
        self.sequences_dir = directory
        
        # Create directory if it doesn't exist
        os.makedirs(self.sequences_dir, exist_ok=True)
        
        # Refresh sequence list
        self._refresh_sequence_list()
        
        logger.info(f"Set sequences directory to {directory}")
    
    def load_sequence_by_name(self, name: str) -> bool:
        """
        Load a sequence by name.
        
        Args:
            name: Sequence name
            
        Returns:
            bool: True if sequence was loaded successfully, False otherwise
        """
        # Find the sequence file
        if os.path.exists(self.sequences_dir):
            filenames = [f for f in os.listdir(self.sequences_dir) if f.endswith('.json')]
            
            for filename in filenames:
                path = os.path.join(self.sequences_dir, filename)
                
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        sequence_name = data.get('name', '')
                        
                    if sequence_name == name:
                        return self._load_sequence(path)
                        
                except:
                    continue
        
        logger.warning(f"Sequence not found: {name}")
        return False 