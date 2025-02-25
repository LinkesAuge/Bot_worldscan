"""
Keyboard Shortcuts Dialog

This module provides a dialog for displaying and configuring keyboard shortcuts.
"""

import logging
from typing import Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import Qt

from scout.ui.utils.shortcuts import get_shortcut_manager, ShortcutContext

# Set up logging
logger = logging.getLogger(__name__)


class KeyboardShortcutsDialog(QDialog):
    """
    Dialog for displaying and configuring keyboard shortcuts.
    
    This dialog shows all available keyboard shortcuts organized by context,
    and allows the user to view and customize them.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the keyboard shortcuts dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Get shortcut manager
        self.shortcut_manager = get_shortcut_manager()
        
        # Set up dialog
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(600, 400)
        self.resize(700, 500)
        
        # Create layout
        self._create_layout()
    
    def _create_layout(self):
        """Create dialog layout."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create tab widget for organizing shortcuts by context
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Add tab for each context
        contexts = [
            (ShortcutContext.APPLICATION, "Application"),
            (ShortcutContext.NAVIGATION, "Navigation"),
            (ShortcutContext.DETECTION, "Detection"),
            (ShortcutContext.AUTOMATION, "Automation"),
            (ShortcutContext.GAME, "Game"),
            (ShortcutContext.DEBUGGING, "Debugging")
        ]
        
        for context, title in contexts:
            # Create tab for context
            tab = self._create_context_tab(context)
            tabs.addTab(tab, title)
        
        # Add button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Reset button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _create_context_tab(self, context: ShortcutContext) -> QWidget:
        """
        Create a tab for a specific shortcut context.
        
        Args:
            context: Shortcut context
            
        Returns:
            Tab widget
        """
        # Create tab widget
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel(f"{context.name.title()} Shortcuts")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Description
        description = QLabel("These shortcuts are available in the application. "
                            "Click on a shortcut to edit it.")
        layout.addWidget(description)
        
        # Get shortcuts for context
        shortcuts = self.shortcut_manager.get_shortcuts_by_context(context)
        
        # Create table
        table = QTableWidget(len(shortcuts), 2)
        table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(table)
        
        # Add shortcuts to table
        row = 0
        for shortcut_id, (key_sequence, description) in shortcuts.items():
            # Create action item
            action_item = QTableWidgetItem(description)
            action_item.setData(Qt.ItemDataRole.UserRole, shortcut_id)
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, action_item)
            
            # Create shortcut item
            shortcut_item = QTableWidgetItem(key_sequence.toString())
            shortcut_item.setFlags(shortcut_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, shortcut_item)
            
            row += 1
        
        # Connect double-click signal
        table.itemDoubleClicked.connect(self._on_shortcut_edit)
        
        return tab
    
    def _on_shortcut_edit(self, item):
        """
        Handle shortcut edit request.
        
        Args:
            item: Table item that was double-clicked
        """
        # We only handle double-clicks on shortcut cells
        if item.column() != 1:
            return
        
        # Get shortcut ID from action item
        action_item = item.tableWidget().item(item.row(), 0)
        shortcut_id = action_item.data(Qt.ItemDataRole.UserRole)
        
        # TODO: Implement shortcut editing dialog
        logger.debug(f"Edit shortcut: {shortcut_id}")
    
    def _on_reset(self):
        """Handle reset to defaults action."""
        # Reset shortcuts
        self.shortcut_manager.reset_shortcuts()
        
        # Recreate layout to show updated shortcuts
        # Remove old layout first
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Create new layout
        self._create_layout() 