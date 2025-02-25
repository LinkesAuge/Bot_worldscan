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
from scout.ui.utils.language_manager import tr

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
        self.setWindowTitle(tr("Keyboard Shortcuts"))
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
            (ShortcutContext.APPLICATION, tr("Application")),
            (ShortcutContext.NAVIGATION, tr("Navigation")),
            (ShortcutContext.DETECTION, tr("Detection")),
            (ShortcutContext.AUTOMATION, tr("Automation")),
            (ShortcutContext.GAME, tr("Game")),
            (ShortcutContext.DEBUGGING, tr("Debugging"))
        ]
        
        for context, title in contexts:
            # Create tab for context
            tab = self._create_context_tab(context)
            tabs.addTab(tab, title)
        
        # Add button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Reset button
        reset_button = QPushButton(tr("Reset to Defaults"))
        reset_button.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_button)
        
        # Close button
        close_button = QPushButton(tr("Close"))
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
        
        # Create shortcuts table
        shortcuts_table = QTableWidget()
        shortcuts_table.setColumnCount(3)
        shortcuts_table.setHorizontalHeaderLabels([
            tr("Action"), tr("Shortcut"), tr("Description")
        ])
        
        # Adjust column sizes
        shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        shortcuts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Get shortcuts for context
        shortcuts = self.shortcut_manager.get_shortcuts_for_context(context)
        shortcuts_table.setRowCount(len(shortcuts))
        
        # Populate table
        for i, (shortcut_id, shortcut_info) in enumerate(shortcuts.items()):
            # Action name
            action_name = shortcut_info.get("name", shortcut_id)
            action_item = QTableWidgetItem(action_name)
            shortcuts_table.setItem(i, 0, action_item)
            
            # Shortcut key sequence
            key_sequence = shortcut_info.get("key_sequence", "")
            key_item = QTableWidgetItem(key_sequence)
            key_item.setData(Qt.ItemDataRole.UserRole, shortcut_id)  # Store ID for editing
            shortcuts_table.setItem(i, 1, key_item)
            
            # Description
            description = shortcut_info.get("description", "")
            desc_item = QTableWidgetItem(description)
            shortcuts_table.setItem(i, 2, desc_item)
        
        # Double-click to edit shortcut
        shortcuts_table.itemDoubleClicked.connect(self._on_shortcut_edit)
        
        # Add table to layout
        layout.addWidget(shortcuts_table)
        
        # Add note about editing
        note_label = QLabel(tr("Double-click on a shortcut to edit it."))
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)
        
        return tab
    
    def _on_shortcut_edit(self, item):
        """
        Handle shortcut editing.
        
        Args:
            item: Table item being edited
        """
        # Only handle shortcut column
        if item.column() != 1:
            return
        
        # Get shortcut ID from item
        shortcut_id = item.data(Qt.ItemDataRole.UserRole)
        if not shortcut_id:
            return
        
        # TODO: Implement shortcut editing dialog
        logger.info(f"Editing shortcut: {shortcut_id}")
    
    def _on_reset(self):
        """Handle reset button click."""
        # Reset all shortcuts
        self.shortcut_manager.reset_shortcuts()
        logger.info("Reset all shortcuts to defaults")
        
        # Refresh dialog
        self.close()
        self.__init__(self.parent())
        self.show() 