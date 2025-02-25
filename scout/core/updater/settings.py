"""
Update Settings

This module manages settings and preferences for the update system.
"""

import logging
from typing import Dict, Any
from PyQt6.QtCore import QSettings

# Set up logging
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    "check_updates_on_startup": True,  # Check for updates when application starts
    "auto_download_updates": False,    # Automatically download available updates
    "notify_on_update": True,          # Show notification when update is available
    "last_check_time": None,           # Last time updates were checked (ISO format)
    "check_frequency_days": 1,         # How often to check for updates (in days)
    "update_channel": "stable",        # Update channel (stable, beta, etc.)
}


class UpdateSettings:
    """
    Manages update settings and preferences.
    
    This class handles loading, saving, and accessing settings related to the 
    update system, such as automatic update checking and download preferences.
    """
    
    def __init__(self):
        """Initialize update settings."""
        self.settings = QSettings("ScoutTeam", "Scout")
        self._settings_data = {}
        self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load update settings from QSettings.
        
        Returns:
            Dictionary of settings
        """
        self._settings_data = {}
        
        # Start with defaults
        for key, default_value in DEFAULT_SETTINGS.items():
            stored_value = self.settings.value(f"updates/{key}", default_value)
            
            # Handle boolean values (QSettings can return them as strings)
            if isinstance(default_value, bool) and not isinstance(stored_value, bool):
                if isinstance(stored_value, str):
                    stored_value = stored_value.lower() in ("true", "1", "yes")
            
            self._settings_data[key] = stored_value
        
        logger.debug(f"Loaded update settings: {self._settings_data}")
        return self._settings_data
    
    def save_settings(self) -> None:
        """Save update settings to QSettings."""
        try:
            for key, value in self._settings_data.items():
                self.settings.setValue(f"updates/{key}", value)
            
            self.settings.sync()
            logger.debug("Update settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving update settings: {e}")
    
    def get_setting(self, key: str, default=None) -> Any:
        """
        Get a specific setting value.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value
        """
        return self._settings_data.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a specific setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self._settings_data[key] = value
    
    def should_check_updates_on_startup(self) -> bool:
        """
        Check if updates should be checked on startup.
        
        Returns:
            True if updates should be checked, False otherwise
        """
        return self.get_setting("check_updates_on_startup", DEFAULT_SETTINGS["check_updates_on_startup"])
    
    def should_auto_download_updates(self) -> bool:
        """
        Check if updates should be downloaded automatically.
        
        Returns:
            True if updates should be auto-downloaded, False otherwise
        """
        return self.get_setting("auto_download_updates", DEFAULT_SETTINGS["auto_download_updates"])
    
    def should_notify_on_update(self) -> bool:
        """
        Check if notifications should be shown for available updates.
        
        Returns:
            True if notifications should be shown, False otherwise
        """
        return self.get_setting("notify_on_update", DEFAULT_SETTINGS["notify_on_update"])
    
    def update_last_check_time(self, time_str: str) -> None:
        """
        Update the last update check time.
        
        Args:
            time_str: ISO formatted time string
        """
        self.set_setting("last_check_time", time_str)
        self.save_settings()


# Singleton instance
_update_settings = None

def get_update_settings() -> UpdateSettings:
    """
    Get the singleton update settings instance.
    
    Returns:
        UpdateSettings instance
    """
    global _update_settings
    if _update_settings is None:
        _update_settings = UpdateSettings()
    return _update_settings 