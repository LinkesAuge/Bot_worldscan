"""
Keyboard Shortcuts Utility

This module provides a centralized management system for keyboard shortcuts
throughout the Scout application. It ensures consistent shortcut assignment
and provides utilities for creating, registering, and documenting shortcuts.
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Union, Tuple

from PyQt6.QtCore import Qt, QObject, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtWidgets import QWidget

# Set up logging
logger = logging.getLogger(__name__)

class ShortcutContext(Enum):
    """Enumeration of shortcut contexts for organization."""
    APPLICATION = auto()    # Application-wide shortcuts
    DETECTION = auto()      # Detection-related shortcuts
    AUTOMATION = auto()     # Automation-related shortcuts
    GAME = auto()           # Game-related shortcuts
    NAVIGATION = auto()     # Navigation shortcuts
    DEBUGGING = auto()      # Debugging shortcuts


class ShortcutManager:
    """
    Centralized manager for keyboard shortcuts in the Scout application.
    
    This class provides functionality for:
    - Registering shortcuts with consistent naming
    - Preventing shortcut conflicts
    - Providing documentation for available shortcuts
    - Supporting different shortcut contexts
    - Allowing shortcut customization
    """
    
    # Default shortcut configuration
    DEFAULT_SHORTCUTS = {
        # Application shortcuts
        "application.quit": QKeySequence("Ctrl+Q"),
        "application.settings": QKeySequence("Ctrl+,"),
        "application.theme_toggle": QKeySequence("Ctrl+T"),
        "application.fullscreen": QKeySequence("F11"),
        "application.help": QKeySequence("F1"),
        
        # Navigation shortcuts
        "navigation.tab_detection": QKeySequence("Ctrl+1"),
        "navigation.tab_automation": QKeySequence("Ctrl+2"),
        "navigation.tab_game": QKeySequence("Ctrl+3"),
        "navigation.tab_debugging": QKeySequence("Ctrl+4"),
        "navigation.next_tab": QKeySequence("Ctrl+Tab"),
        "navigation.previous_tab": QKeySequence("Ctrl+Shift+Tab"),
        
        # Detection shortcuts
        "detection.run": QKeySequence("F5"),
        "detection.stop": QKeySequence("Shift+F5"),
        "detection.capture": QKeySequence("F12"),
        "detection.new_template": QKeySequence("Ctrl+N"),
        "detection.edit_template": QKeySequence("Ctrl+E"),
        "detection.delete_template": QKeySequence("Delete"),
        
        # Automation shortcuts
        "automation.run": QKeySequence("F6"),
        "automation.stop": QKeySequence("Shift+F6"),
        "automation.new_action": QKeySequence("Ctrl+Shift+N"),
        "automation.edit_action": QKeySequence("Ctrl+Shift+E"),
        "automation.delete_action": QKeySequence("Shift+Delete"),
        
        # Game shortcuts
        "game.refresh_state": QKeySequence("F9"),
        "game.toggle_resource_graph": QKeySequence("Ctrl+G"),
        "game.toggle_map": QKeySequence("Ctrl+M"),
        
        # Debugging shortcuts
        "debugging.console": QKeySequence("Ctrl+`"),
        "debugging.toggle_logs": QKeySequence("Ctrl+L"),
        "debugging.clear_logs": QKeySequence("Ctrl+Shift+L"),
    }
    
    # Shortcut descriptions for documentation
    SHORTCUT_DESCRIPTIONS = {
        # Application shortcuts
        "application.quit": "Exit the application",
        "application.settings": "Open settings dialog",
        "application.theme_toggle": "Toggle between light and dark theme",
        "application.fullscreen": "Toggle fullscreen mode",
        "application.help": "Show help documentation",
        
        # Navigation shortcuts
        "navigation.tab_detection": "Switch to Detection tab",
        "navigation.tab_automation": "Switch to Automation tab",
        "navigation.tab_game": "Switch to Game tab",
        "navigation.tab_debugging": "Switch to Debugging tab",
        "navigation.next_tab": "Go to next tab",
        "navigation.previous_tab": "Go to previous tab",
        
        # Detection shortcuts
        "detection.run": "Run detection",
        "detection.stop": "Stop detection",
        "detection.capture": "Capture screenshot",
        "detection.new_template": "Create new template",
        "detection.edit_template": "Edit selected template",
        "detection.delete_template": "Delete selected template",
        
        # Automation shortcuts
        "automation.run": "Run automation sequence",
        "automation.stop": "Stop automation",
        "automation.new_action": "Create new automation action",
        "automation.edit_action": "Edit selected action",
        "automation.delete_action": "Delete selected action",
        
        # Game shortcuts
        "game.refresh_state": "Refresh game state",
        "game.toggle_resource_graph": "Toggle resource graph view",
        "game.toggle_map": "Toggle map view",
        
        # Debugging shortcuts
        "debugging.console": "Show/hide debug console",
        "debugging.toggle_logs": "Show/hide log panel",
        "debugging.clear_logs": "Clear log contents",
    }
    
    def __init__(self):
        """Initialize the shortcut manager."""
        # Map of shortcut IDs to key sequences
        self._shortcuts: Dict[str, QKeySequence] = self.DEFAULT_SHORTCUTS.copy()
        
        # Map of shortcut IDs to registered QShortcut or QAction objects
        self._registered_shortcuts: Dict[str, List[Union[QShortcut, QAction]]] = {}
        
        # Load custom shortcuts if available
        self._load_custom_shortcuts()
    
    def _load_custom_shortcuts(self) -> None:
        """Load custom shortcuts from settings."""
        # TODO: Implement loading from QSettings
        pass
    
    def _save_custom_shortcuts(self) -> None:
        """Save custom shortcuts to settings."""
        # TODO: Implement saving to QSettings
        pass
    
    def register_shortcut(self, 
                         shortcut_id: str, 
                         parent: QWidget, 
                         callback: Callable, 
                         context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut) -> Optional[QShortcut]:
        """
        Register a keyboard shortcut with the specified ID.
        
        Args:
            shortcut_id: Unique identifier for the shortcut (e.g. "detection.run")
            parent: Parent widget for the shortcut
            callback: Function to call when shortcut is triggered
            context: Shortcut context (window or application)
            
        Returns:
            Created QShortcut object, or None if the shortcut ID is invalid
        """
        # Check if shortcut ID exists
        key_sequence = self._shortcuts.get(shortcut_id)
        if not key_sequence:
            logger.warning(f"Attempted to register unknown shortcut ID: {shortcut_id}")
            return None
        
        # Create shortcut
        shortcut = QShortcut(key_sequence, parent)
        shortcut.setContext(context)
        shortcut.activated.connect(callback)
        
        # Register shortcut
        if shortcut_id not in self._registered_shortcuts:
            self._registered_shortcuts[shortcut_id] = []
        
        self._registered_shortcuts[shortcut_id].append(shortcut)
        
        logger.debug(f"Registered shortcut: {shortcut_id} ({key_sequence.toString()})")
        
        return shortcut
    
    def register_action_shortcut(self, 
                                shortcut_id: str, 
                                action: QAction) -> bool:
        """
        Register a shortcut with a QAction.
        
        Args:
            shortcut_id: Unique identifier for the shortcut
            action: QAction to assign the shortcut to
            
        Returns:
            True if the shortcut was registered, False otherwise
        """
        # Check if shortcut ID exists
        key_sequence = self._shortcuts.get(shortcut_id)
        if not key_sequence:
            logger.warning(f"Attempted to register unknown shortcut ID: {shortcut_id}")
            return False
        
        # Set shortcut on action
        action.setShortcut(key_sequence)
        
        # Register action
        if shortcut_id not in self._registered_shortcuts:
            self._registered_shortcuts[shortcut_id] = []
        
        self._registered_shortcuts[shortcut_id].append(action)
        
        logger.debug(f"Registered action shortcut: {shortcut_id} ({key_sequence.toString()})")
        
        return True
    
    def get_shortcut_sequence(self, shortcut_id: str) -> Optional[QKeySequence]:
        """
        Get the key sequence for a shortcut ID.
        
        Args:
            shortcut_id: Shortcut identifier
            
        Returns:
            Key sequence for the shortcut, or None if not found
        """
        return self._shortcuts.get(shortcut_id)
    
    def get_shortcut_string(self, shortcut_id: str) -> str:
        """
        Get the string representation of a shortcut key sequence.
        
        Args:
            shortcut_id: Shortcut identifier
            
        Returns:
            String representation of the shortcut, or empty string if not found
        """
        key_sequence = self._shortcuts.get(shortcut_id)
        return key_sequence.toString() if key_sequence else ""
    
    def get_shortcut_description(self, shortcut_id: str) -> str:
        """
        Get the description for a shortcut ID.
        
        Args:
            shortcut_id: Shortcut identifier
            
        Returns:
            Description of the shortcut, or empty string if not found
        """
        return self.SHORTCUT_DESCRIPTIONS.get(shortcut_id, "")
    
    def update_shortcut(self, shortcut_id: str, key_sequence: QKeySequence) -> bool:
        """
        Update the key sequence for a shortcut.
        
        Args:
            shortcut_id: Shortcut identifier
            key_sequence: New key sequence
            
        Returns:
            True if the shortcut was updated, False otherwise
        """
        # Check if shortcut ID exists
        if shortcut_id not in self._shortcuts:
            logger.warning(f"Attempted to update unknown shortcut ID: {shortcut_id}")
            return False
        
        # Update shortcut
        self._shortcuts[shortcut_id] = key_sequence
        
        # Update registered shortcuts
        if shortcut_id in self._registered_shortcuts:
            for obj in self._registered_shortcuts[shortcut_id]:
                if isinstance(obj, QShortcut):
                    obj.setKey(key_sequence)
                elif isinstance(obj, QAction):
                    obj.setShortcut(key_sequence)
        
        # Save custom shortcuts
        self._save_custom_shortcuts()
        
        logger.debug(f"Updated shortcut: {shortcut_id} to {key_sequence.toString()}")
        
        return True
    
    def reset_shortcuts(self) -> None:
        """Reset all shortcuts to default values."""
        # Update shortcuts
        self._shortcuts = self.DEFAULT_SHORTCUTS.copy()
        
        # Update registered shortcuts
        for shortcut_id, objs in self._registered_shortcuts.items():
            key_sequence = self._shortcuts.get(shortcut_id)
            if key_sequence:
                for obj in objs:
                    if isinstance(obj, QShortcut):
                        obj.setKey(key_sequence)
                    elif isinstance(obj, QAction):
                        obj.setShortcut(key_sequence)
        
        # Save custom shortcuts
        self._save_custom_shortcuts()
        
        logger.info("Reset all shortcuts to default values")
    
    def get_shortcuts_by_context(self, context: ShortcutContext) -> Dict[str, Tuple[QKeySequence, str]]:
        """
        Get all shortcuts for a specific context.
        
        Args:
            context: Shortcut context to filter by
            
        Returns:
            Dictionary mapping shortcut IDs to (key sequence, description) tuples
        """
        prefix = context.name.lower() + "."
        result = {}
        
        for shortcut_id, key_sequence in self._shortcuts.items():
            if shortcut_id.startswith(prefix):
                description = self.SHORTCUT_DESCRIPTIONS.get(shortcut_id, "")
                result[shortcut_id] = (key_sequence, description)
                
        return result
    
    def get_all_shortcuts(self) -> Dict[str, Tuple[QKeySequence, str]]:
        """
        Get all shortcuts with their descriptions.
        
        Returns:
            Dictionary mapping shortcut IDs to (key sequence, description) tuples
        """
        result = {}
        
        for shortcut_id, key_sequence in self._shortcuts.items():
            description = self.SHORTCUT_DESCRIPTIONS.get(shortcut_id, "")
            result[shortcut_id] = (key_sequence, description)
                
        return result


# Singleton instance
_shortcut_manager = None

def get_shortcut_manager() -> ShortcutManager:
    """
    Get the singleton shortcut manager instance.
    
    Returns:
        Shortcut manager instance
    """
    global _shortcut_manager
    if _shortcut_manager is None:
        _shortcut_manager = ShortcutManager()
    return _shortcut_manager 