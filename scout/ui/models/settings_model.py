"""
Settings Model

This module provides the settings model for the Scout application.
It manages loading, saving, and accessing application settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union, List

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
    
    # Default settings - these are used when no settings file exists or when a setting is missing
    DEFAULT_SETTINGS = {
        # General settings
        'window_title': 'Total Battle',
        'auto_find_window': True,
        'overlay_enabled': True,
        'overlay_refresh_rate': 100,  # ms
        'overlay_opacity': 80,  # percentage
        
        # Detection settings
        'use_caching': True,
        'cache_timeout': 5000,  # ms
        'cache_size': 100,  # items
        'result_sorting': 'confidence',
        'grouping_radius': 5,  # px
        'max_results': 20,
        
        # Template matching settings
        'template_method': 'cv2.TM_CCOEFF_NORMED',
        'template_confidence': 0.7,
        'template_max_results': 5,
        'template_grayscale': True,
        'template_edge': False,
        'template_scaling': False,
        'scale_min': 0.8,
        'scale_max': 1.2,
        'scale_steps': 3,
        
        # OCR settings
        'ocr_engine': 'tesseract',
        'ocr_language': 'eng',
        'ocr_confidence': 0.6,
        'ocr_whitespace': True,
        'ocr_preprocessing': 'threshold',
        'ocr_custom_params': '--psm 6 --oem 3',
        'ocr_whitelist': '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        
        # YOLO settings
        'yolo_model': 'yolov8n.pt',
        'yolo_model_file': '',
        'yolo_confidence': 0.5,
        'yolo_overlap': 0.45,
        'yolo_classes': '',
        'yolo_gpu': True,
        
        # Display settings
        'highlight_color': '#00FF00',  # Green
        'text_color': '#FFFF00',  # Yellow
        'show_confidence': True,
        
        # Automation settings
        'click_delay': 100,  # ms
        'double_click_delay': 50,  # ms
        'typing_speed': 'normal',
        'default_wait_time': 500,  # ms
        'mouse_speed': 5,
        'randomize_movements': True,
        'error_handling': 'pause',
        'max_retries': 3,
        'retry_delay': 1000,  # ms
        'jitter_min': 5,  # px
        'jitter_max': 15,  # px
        'detection_interval': 500,  # ms
        'autostart_sequence': False,
        'loop_sequence': False,
        'default_sequence': '',
        
        # Window settings
        'capture_method': 'win32',
        'region_padding': 5,
        'capture_interval': 200,  # ms
        'auto_focus': True,
        
        # UI settings
        'theme': 'system',
        'theme_file': '',
        'font_size': 10,
        'font_family': 'System Default',
        'show_tooltips': True,
        'confirm_actions': True,
        'show_debug_info': False,
        'sidebar_position': 'left',
        'tab_position': 'top',
        'recent_files_count': 10,
        
        # Notification settings
        'enable_sound': True,
        'sound_volume': 80,  # percentage
        'desktop_notifications': True,
        'status_updates': True,
        
        # Paths
        'templates_dir': os.path.join('scout', 'resources', 'templates'),
        'models_dir': os.path.join('scout', 'resources', 'models'),
        'state_dir': os.path.join('scout', 'resources', 'states'),
        'logs_dir': os.path.join('scout', 'resources', 'logs'),
        'sequences_dir': os.path.join('scout', 'resources', 'sequences'),
        'screenshots_dir': os.path.join('scout', 'resources', 'screenshots'),
        
        # Advanced settings
        'thread_count': 4,
        'process_priority': 'normal',
        'image_cache_size': 100,  # MB
        'parallel_processing': True,
        'log_level': 'INFO',
        'log_to_file': True,
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'debug_window': False,
        'performance_monitoring': False,
        'development_mode': False,
        'remote_debugging': False,
        'remote_debugging_port': 5678
    }
    
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
        self.settings = self.DEFAULT_SETTINGS.copy()
        
        # Flag to track settings changes
        self._settings_changed = False
        
        # Load settings from file
        self.load()
        
        logger.info("Settings model initialized")
    
    def load(self) -> bool:
        """
        Load settings from file.
        
        If the file doesn't exist or is invalid, default settings are used.
        
        Returns:
            bool: True if settings were loaded successfully, False otherwise
        """
        try:
            # Check if the settings file exists
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    
                # Update settings with loaded values
                self._update_with_loaded_settings(loaded_settings)
                logger.info(f"Loaded settings from {self.settings_file}")
                return True
            else:
                logger.info("Settings file not found, using defaults")
                
                # Create directories if they don't exist
                settings_dir = os.path.dirname(self.settings_file)
                if not os.path.exists(settings_dir):
                    os.makedirs(settings_dir, exist_ok=True)
                    logger.info(f"Created settings directory: {settings_dir}")
                
                # Save default settings
                self.save()
                return False
                    
        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
            logger.info("Using default settings")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load settings from a specific file.
        
        Args:
            file_path: Path to the settings file
            
        Returns:
            bool: True if settings were loaded successfully, False otherwise
        """
        try:
            # Check if the file exists
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    loaded_settings = json.load(f)
                
                # Create a new settings dictionary with defaults
                new_settings = self.DEFAULT_SETTINGS.copy()
                
                # Update with loaded settings
                self._update_with_loaded_settings(loaded_settings)
                
                logger.info(f"Loaded settings from {file_path}")
                
                # Mark as changed
                self._settings_changed = True
                
                return True
            else:
                logger.error(f"Settings file not found: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading settings from {file_path}: {e}", exc_info=True)
            return False
    
    def _update_with_loaded_settings(self, loaded_settings: Dict[str, Any]) -> None:
        """
        Update settings with loaded values, maintaining proper types.
        
        Args:
            loaded_settings: Settings loaded from file
        """
        for key, default_value in self.DEFAULT_SETTINGS.items():
            if key in loaded_settings:
                # Get the loaded value
                loaded_value = loaded_settings[key]
                
                # Ensure the loaded value has the same type as the default value
                try:
                    if isinstance(default_value, bool) and not isinstance(loaded_value, bool):
                        # Special handling for booleans - convert strings to bool
                        if isinstance(loaded_value, str):
                            loaded_value = loaded_value.lower() in ('true', 'yes', '1', 'y')
                        else:
                            loaded_value = bool(loaded_value)
                    elif isinstance(default_value, int) and not isinstance(loaded_value, int):
                        loaded_value = int(loaded_value)
                    elif isinstance(default_value, float) and not isinstance(loaded_value, float):
                        loaded_value = float(loaded_value)
                    
                    # Update the setting
                    self.settings[key] = loaded_value
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for setting {key}: {loaded_value}. Using default. Error: {e}")
    
    def save(self) -> bool:
        """
        Save settings to file.
        
        Creates the settings directory if it doesn't exist.
        
        Returns:
            bool: True if settings were saved successfully, False otherwise
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
            
            # Reset the changed flag
            self._settings_changed = False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            return False
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save settings to a specific file.
        
        Args:
            file_path: Path to save settings to
            
        Returns:
            bool: True if settings were saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save settings to file
            with open(file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
                
            logger.info(f"Saved settings to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings to {file_path}: {e}", exc_info=True)
            return False
    
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
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
            
        Returns:
            bool: True if the setting was set successfully, False otherwise
        """
        # Check if the key exists in default settings
        if key not in self.DEFAULT_SETTINGS:
            logger.warning(f"Unknown setting: {key}")
            return False
        
        # Validate setting value
        if self._validate_setting(key, value):
            # Check if the value has changed
            if key not in self.settings or self.settings[key] != value:
                self.settings[key] = value
                self._settings_changed = True
                logger.debug(f"Setting {key} updated to {value}")
            return True
        else:
            logger.warning(f"Invalid value for setting {key}: {value}")
            return False
    
    def _validate_setting(self, key: str, value: Any) -> bool:
        """
        Validate a setting value.
        
        Args:
            key: Setting key
            value: Setting value to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Get the default value to determine the expected type
        default_value = self.DEFAULT_SETTINGS.get(key)
        
        if default_value is None:
            # Unknown setting
            return False
        
        # Check if the value is of the expected type or can be converted
        try:
            if isinstance(default_value, bool):
                # Special handling for booleans
                if isinstance(value, bool):
                    return True
                if isinstance(value, str):
                    return value.lower() in ('true', 'false', 'yes', 'no', '1', '0', 'y', 'n')
                return isinstance(value, (int, float))
                
            if isinstance(default_value, int):
                # Allow numeric types for integers
                if isinstance(value, (int, float)):
                    return True
                if isinstance(value, str):
                    return value.isdigit() or (value.startswith('-') and value[1:].isdigit())
                return False
                
            if isinstance(default_value, float):
                # Allow numeric types for floats
                if isinstance(value, (int, float)):
                    return True
                if isinstance(value, str):
                    try:
                        float(value)
                        return True
                    except ValueError:
                        return False
                return False
                
            if isinstance(default_value, str):
                # String validation for specific settings
                if key in ('highlight_color', 'text_color'):
                    # Color in hex format (#RRGGBB or #RRGGBBAA)
                    if not isinstance(value, str):
                        return False
                    return value.startswith('#') and len(value) in (7, 9) and all(c in '0123456789ABCDEFabcdef' for c in value[1:])
                
                # Allow any string or convertible value
                return True
                
            if isinstance(default_value, list):
                # Allow list or convertible value
                return isinstance(value, (list, tuple)) or (isinstance(value, str) and ',' in value)
                
            # Default validation: require same type
            return isinstance(value, type(default_value))
            
        except Exception as e:
            logger.error(f"Error validating setting {key}: {e}", exc_info=True)
            return False
    
    def has_changed(self) -> bool:
        """
        Check if settings have changed since last save.
        
        Returns:
            bool: True if settings have changed, False otherwise
        """
        return self._settings_changed
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            dict: All settings
        """
        return self.settings.copy()
    
    def reset_to_default(self, key: Optional[str] = None) -> None:
        """
        Reset settings to default values.
        
        Args:
            key: Specific setting to reset (None for all)
        """
        if key is None:
            # Reset all settings
            self.settings = self.DEFAULT_SETTINGS.copy()
            self._settings_changed = True
            logger.info("Reset all settings to defaults")
        elif key in self.DEFAULT_SETTINGS:
            # Reset specific setting
            default_value = self.DEFAULT_SETTINGS[key]
            if self.settings.get(key) != default_value:
                self.settings[key] = default_value
                self._settings_changed = True
                logger.info(f"Reset setting {key} to default: {default_value}")
        else:
            logger.warning(f"Unknown setting: {key}")
    
    def reset_category(self, category: str) -> None:
        """
        Reset all settings in a category to their default values.
        
        Args:
            category: Category prefix (e.g., 'template_' for all template-related settings)
        """
        reset_count = 0
        
        # Find all settings with the given prefix
        for key, default_value in self.DEFAULT_SETTINGS.items():
            if key.startswith(category):
                if self.settings.get(key) != default_value:
                    self.settings[key] = default_value
                    reset_count += 1
        
        if reset_count > 0:
            self._settings_changed = True
            logger.info(f"Reset {reset_count} settings in category '{category}' to defaults")
        else:
            logger.info(f"No settings changed when resetting category '{category}'")
    
    def update(self, settings: Dict[str, Any]) -> int:
        """
        Update multiple settings at once.
        
        Args:
            settings: Dictionary with settings to update
            
        Returns:
            int: Number of settings updated
        """
        updated_count = 0
        
        # Validate and update each setting
        for key, value in settings.items():
            if self.set(key, value):
                updated_count += 1
                
        logger.debug(f"Updated {updated_count} settings")
        return updated_count
    
    def is_valid_key(self, key: str) -> bool:
        """
        Check if a key is a valid setting.
        
        Args:
            key: Setting key to check
            
        Returns:
            bool: True if the key is a valid setting, False otherwise
        """
        return key in self.DEFAULT_SETTINGS
    
    def get_default(self, key: str) -> Any:
        """
        Get the default value for a setting.
        
        Args:
            key: Setting key
            
        Returns:
            Default value for the setting or None if not found
        """
        return self.DEFAULT_SETTINGS.get(key)
    
    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """
        Import settings from a dictionary.
        
        Args:
            data: Dictionary with settings to import
            
        Returns:
            int: Number of settings imported
        """
        return self.update(data) 