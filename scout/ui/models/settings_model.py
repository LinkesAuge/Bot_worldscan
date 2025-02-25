"""
Settings Model

This module provides the settings model for the Scout application.
It manages loading, saving, and accessing application settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

class SettingsModel:
    """
    Model for managing application settings.
    
    This class is responsible for:
    - Loading settings from file
    - Saving settings to file
    - Providing access to settings values
    - Validating settings
    - Applying defaults for missing settings
    
    It manages the persistence of user preferences and application configuration.
    """
    
    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize the settings model.
        
        Args:
            settings_file: Path to the settings file (None for default)
        """
        # Set settings file path
        self.settings_file = settings_file or os.path.join(
            os.path.expanduser('~'),
            '.scout',
            'settings.json'
        )
        
        # Initialize settings with defaults
        self.settings = self._get_default_settings()
        
        # Load settings from file
        self.load()
        
        logger.info("Settings model initialized")
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings values.
        
        Returns:
            Dictionary with default settings
        """
        return {
            # General settings
            'window_title': 'Total Battle',
            'auto_find_window': True,
            'overlay_enabled': True,
            'overlay_refresh_rate': 100,  # ms
            
            # Detection settings
            'template_confidence': 0.7,
            'ocr_confidence': 0.6,
            'yolo_confidence': 0.5,
            'use_caching': True,
            'cache_timeout': 5000,  # ms
            
            # Display settings
            'highlight_color': '#00FF00',  # Green
            'text_color': '#FFFF00',  # Yellow
            'show_confidence': True,
            
            # Automation settings
            'execution_delay': 500,  # ms
            'click_delay': 200,  # ms
            'double_click_delay': 100,  # ms
            'drag_duration': 500,  # ms
            'key_press_duration': 100,  # ms
            
            # Paths
            'templates_dir': os.path.join('scout', 'resources', 'templates'),
            'state_file': os.path.join('scout', 'resources', 'game_state.json'),
            'sequences_dir': os.path.join('scout', 'resources', 'sequences')
        }
    
    def load(self) -> None:
        """
        Load settings from file.
        
        If the file doesn't exist or is invalid, default settings are used.
        """
        try:
            # Check if the settings file exists
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    
                # Update settings with loaded values
                self.settings.update(loaded_settings)
                logger.info(f"Loaded settings from {self.settings_file}")
            else:
                logger.info("Settings file not found, using defaults")
                
                # Create directories if they don't exist
                settings_dir = os.path.dirname(self.settings_file)
                if not os.path.exists(settings_dir):
                    os.makedirs(settings_dir, exist_ok=True)
                    logger.info(f"Created settings directory: {settings_dir}")
                
                # Save default settings
                self.save()
                    
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            logger.info("Using default settings")
    
    def save(self) -> None:
        """
        Save settings to file.
        
        Creates the settings directory if it doesn't exist.
        """
        try:
            # Create settings directory if it doesn't exist
            settings_dir = os.path.dirname(self.settings_file)
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
                
            # Save settings to file
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
                
            logger.info(f"Saved settings to {self.settings_file}")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if the setting doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        # Validate setting value
        if self._validate_setting(key, value):
            self.settings[key] = value
            logger.debug(f"Setting {key} updated to {value}")
        else:
            logger.warning(f"Invalid value for setting {key}: {value}")
    
    def _validate_setting(self, key: str, value: Any) -> bool:
        """
        Validate a setting value.
        
        Args:
            key: Setting key
            value: Setting value to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Implement specific validation rules for each setting
        if key == 'template_confidence' or key == 'ocr_confidence' or key == 'yolo_confidence':
            # Confidence must be between 0 and 1
            return isinstance(value, (int, float)) and 0 <= value <= 1
            
        if key == 'overlay_refresh_rate' or key == 'cache_timeout' or key == 'execution_delay':
            # Time values must be positive integers
            return isinstance(value, int) and value > 0
            
        if key == 'highlight_color' or key == 'text_color':
            # Colors must be valid hex codes
            if not isinstance(value, str):
                return False
            return value.startswith('#') and len(value) in (7, 9)
            
        # Default validation: accept any value
        return True
    
    def reset_to_default(self, key: Optional[str] = None) -> None:
        """
        Reset settings to default values.
        
        Args:
            key: Specific setting to reset (None for all)
        """
        defaults = self._get_default_settings()
        
        if key is None:
            # Reset all settings
            self.settings = defaults.copy()
            logger.info("Reset all settings to defaults")
        elif key in defaults:
            # Reset specific setting
            self.settings[key] = defaults[key]
            logger.info(f"Reset setting {key} to default: {defaults[key]}")
        else:
            logger.warning(f"Unknown setting: {key}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            Dictionary with all settings
        """
        return self.settings.copy()
    
    def update(self, settings: Dict[str, Any]) -> None:
        """
        Update multiple settings at once.
        
        Args:
            settings: Dictionary with settings to update
        """
        # Validate and update each setting
        for key, value in settings.items():
            if self._validate_setting(key, value):
                self.settings[key] = value
            else:
                logger.warning(f"Invalid value for setting {key}: {value}")
                
        logger.debug(f"Updated {len(settings)} settings") 