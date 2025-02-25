"""
Temporary SettingsTab module that provides just enough for the application to run.
"""

import logging
from PyQt6.QtWidgets import QWidget, QLabel

# Set up logging
logger = logging.getLogger(__name__)

class ServiceLocator:
    @classmethod
    def get(cls, interface_class):
        return None

class SettingsTab(QWidget):
    """Minimal implementation of SettingsTab."""
    
    def __init__(self, service_locator: ServiceLocator):
        """Initialize settings tab."""
        super().__init__()
        self.status_label = QLabel("")
        self._modified = False
    
    def _mark_settings_changed(self) -> None:
        """Mark settings as modified."""
        self._modified = True
        
        # Update status label if it exists
        if hasattr(self, 'status_label') and self.status_label is not None:
            self.status_label.setText("Settings have been modified (not saved)")
    
    def _auto_save_settings(self) -> None:
        """Auto-save settings if they have been modified."""
        # Simply clear the modified flag - no actual saving in this dummy version
        self._modified = False
        
        # Clear the status label
        if hasattr(self, 'status_label') and self.status_label is not None:
            self.status_label.setText("") 