"""
Automation Position List

This module provides the PositionList widget for managing positions in automation sequences.
It allows users to define, select, and manage positions for automation actions.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QMenu, QInputDialog, QMessageBox, QFileDialog, QHeaderView
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal

from scout.ui.utils.language_manager import tr

# Set up logging
logger = logging.getLogger(__name__)


class PositionList(QWidget):
    """
    Widget for managing predefined positions for automation actions.
    
    This widget provides functionality to:
    - Define named positions (X, Y coordinates)
    - Save positions for reuse in automation sequences
    - Import/export position lists
    - Select positions for use in actions
    
    Signals:
        position_selected(dict): Emitted when a position is selected, with position data
        position_added(dict): Emitted when a position is added, with position data
        position_removed(str): Emitted when a position is removed, with position name
    """
    
    # Signals
    position_selected = pyqtSignal(dict)  # Selected position data
    position_added = pyqtSignal(dict)     # Added position data
    position_removed = pyqtSignal(str)    # Removed position name
    
    def __init__(self, parent=None):
        """
        Initialize the position list.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize state
        self._positions = {}  # name -> {"x": x, "y": y}
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(tr("Saved Positions"))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Position table
        self.position_table = QTableWidget(0, 3)  # Rows, Columns
        self.position_table.setHorizontalHeaderLabels([tr("Name"), tr("X"), tr("Y")])
        self.position_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.position_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.position_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.position_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set table to resize to contents
        self.position_table.horizontalHeader().setStretchLastSection(True)
        self.position_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.position_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton(tr("Add"))
        self.remove_button = QPushButton(tr("Remove"))
        self.capture_button = QPushButton(tr("Capture"))
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.capture_button)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Table signals
        self.position_table.itemDoubleClicked.connect(self._on_position_double_clicked)
        self.position_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.position_table.customContextMenuRequested.connect(self._on_context_menu)
        
        # Button signals
        self.add_button.clicked.connect(self._on_add_clicked)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.capture_button.clicked.connect(self._on_capture_clicked)
    
    def add_position(self, name: str, x: int, y: int):
        """
        Add a position to the list.
        
        Args:
            name: Position name
            x: X coordinate
            y: Y coordinate
        """
        # Store position
        self._positions[name] = {"x": x, "y": y}
        
        # Add to table
        row = self.position_table.rowCount()
        self.position_table.insertRow(row)
        
        # Set data
        self.position_table.setItem(row, 0, QTableWidgetItem(name))
        self.position_table.setItem(row, 1, QTableWidgetItem(str(x)))
        self.position_table.setItem(row, 2, QTableWidgetItem(str(y)))
        
        # Emit signal
        self.position_added.emit({"name": name, "x": x, "y": y})
    
    def remove_position(self, name: str):
        """
        Remove a position from the list.
        
        Args:
            name: Position name
        """
        # Remove from positions dictionary
        if name in self._positions:
            del self._positions[name]
            
            # Find and remove from table
            for row in range(self.position_table.rowCount()):
                if self.position_table.item(row, 0).text() == name:
                    self.position_table.removeRow(row)
                    break
            
            # Emit signal
            self.position_removed.emit(name)
    
    def get_position(self, name: str) -> Optional[Dict[str, int]]:
        """
        Get a position by name.
        
        Args:
            name: Position name
            
        Returns:
            Position data or None if not found
        """
        return self._positions.get(name)
    
    def get_all_positions(self) -> Dict[str, Dict[str, int]]:
        """
        Get all positions.
        
        Returns:
            Dictionary of all positions
        """
        return self._positions.copy()
    
    def clear_positions(self):
        """Clear all positions."""
        self._positions.clear()
        self.position_table.setRowCount(0)
    
    def _on_add_clicked(self):
        """Handle add button click."""
        # Show dialog to get position name and coordinates
        name, ok = QInputDialog.getText(self, tr("Add Position"), tr("Position Name:"))
        if not ok or not name:
            return
        
        # Check for duplicate name
        if name in self._positions:
            QMessageBox.warning(self, tr("Duplicate Name"), 
                               tr("A position with this name already exists."))
            return
        
        # Get X coordinate
        x, ok = QInputDialog.getInt(self, tr("Add Position"), 
                                   tr("X Coordinate:"), 0, 0, 9999, 1)
        if not ok:
            return
        
        # Get Y coordinate
        y, ok = QInputDialog.getInt(self, tr("Add Position"), 
                                   tr("Y Coordinate:"), 0, 0, 9999, 1)
        if not ok:
            return
        
        # Add position
        self.add_position(name, x, y)
    
    def _on_remove_clicked(self):
        """Handle remove button click."""
        # Get selected row
        selected_rows = self.position_table.selectedItems()
        if not selected_rows:
            return
        
        # Get position name from first column
        row = selected_rows[0].row()
        name = self.position_table.item(row, 0).text()
        
        # Confirm deletion
        reply = QMessageBox.question(self, tr("Remove Position"), 
                                     tr(f"Are you sure you want to remove the position '{name}'?"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_position(name)
    
    def _on_capture_clicked(self):
        """Handle capture button click."""
        # This would normally capture the current cursor position
        # For now, just show a message
        QMessageBox.information(self, tr("Capture Position"), 
                               tr("Position capture not implemented in this version."))
    
    def _on_position_double_clicked(self, item: QTableWidgetItem):
        """
        Handle position double click.
        
        Args:
            item: Clicked item
        """
        # Get position data
        row = item.row()
        name = self.position_table.item(row, 0).text()
        position = self._positions.get(name)
        
        if position:
            # Emit position selected signal
            self.position_selected.emit({"name": name, **position})
    
    def _on_context_menu(self, pos):
        """
        Show context menu for positions.
        
        Args:
            pos: Menu position
        """
        # Get item at position
        item = self.position_table.itemAt(pos)
        if not item:
            return
        
        # Create menu
        menu = QMenu(self)
        
        # Add actions
        select_action = menu.addAction(tr("Select"))
        edit_action = menu.addAction(tr("Edit"))
        remove_action = menu.addAction(tr("Remove"))
        
        # Show menu and get selected action
        action = menu.exec(self.position_table.mapToGlobal(pos))
        
        if not action:
            return
        
        # Get position data
        row = item.row()
        name = self.position_table.item(row, 0).text()
        
        # Handle actions
        if action == select_action:
            position = self._positions.get(name)
            if position:
                self.position_selected.emit({"name": name, **position})
                
        elif action == edit_action:
            self._edit_position(name)
            
        elif action == remove_action:
            # Confirm deletion
            reply = QMessageBox.question(self, tr("Remove Position"), 
                                        tr(f"Are you sure you want to remove the position '{name}'?"),
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.remove_position(name)
    
    def _edit_position(self, name: str):
        """
        Edit an existing position.
        
        Args:
            name: Position name
        """
        position = self._positions.get(name)
        if not position:
            return
        
        # Get new coordinates
        x, ok = QInputDialog.getInt(self, tr("Edit Position"), 
                                   tr("X Coordinate:"), position["x"], 0, 9999, 1)
        if not ok:
            return
        
        y, ok = QInputDialog.getInt(self, tr("Edit Position"), 
                                   tr("Y Coordinate:"), position["y"], 0, 9999, 1)
        if not ok:
            return
        
        # Update position
        self._positions[name] = {"x": x, "y": y}
        
        # Update table
        for row in range(self.position_table.rowCount()):
            if self.position_table.item(row, 0).text() == name:
                self.position_table.item(row, 1).setText(str(x))
                self.position_table.item(row, 2).setText(str(y))
                break
        
        # Emit signal
        self.position_added.emit({"name": name, "x": x, "y": y}) 