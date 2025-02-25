"""
Update Settings Tests

This module contains tests for the update settings functionality.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Ensure the scout package is in the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from scout.core.updater.settings import (
    UpdateSettings, get_update_settings, DEFAULT_SETTINGS
)


class TestUpdateSettings(unittest.TestCase):
    """Tests for the UpdateSettings class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock QSettings to avoid affecting real settings during testing
        self.qsettings_patch = patch('scout.core.updater.settings.QSettings')
        self.mock_qsettings = self.qsettings_patch.start()
        
        # Create a mock settings instance
        self.mock_settings_instance = MagicMock()
        self.mock_qsettings.return_value = self.mock_settings_instance
        
        # Set up the mock's value method to return default values
        self.mock_settings_instance.value.side_effect = lambda key, default: default
        
        # Create a test settings instance
        self.settings = UpdateSettings()
        
        # Reset the singleton for each test
        from scout.core.updater.settings import _update_settings
        _update_settings = None
    
    def tearDown(self):
        """Clean up after tests."""
        self.qsettings_patch.stop()
    
    def test_initialization(self):
        """Test that UpdateSettings initializes correctly."""
        # Verify QSettings was created with correct parameters
        self.mock_qsettings.assert_called_with("ScoutTeam", "Scout")
        
        # Verify settings were loaded
        self.assertIsNotNone(self.settings._settings_data)
    
    def test_load_settings_defaults(self):
        """Test loading settings with defaults."""
        # Mock settings instance to return default values
        self.mock_settings_instance.value.side_effect = lambda key, default: default
        
        # Load settings
        settings_data = self.settings.load_settings()
        
        # Verify all default settings are loaded
        for key, default_value in DEFAULT_SETTINGS.items():
            self.assertEqual(settings_data[key], default_value)
    
    def test_load_settings_custom_values(self):
        """Test loading settings with custom values."""
        # Mock custom values for specific settings
        def mock_value(key, default):
            if key == "updates/check_updates_on_startup":
                return False
            elif key == "updates/auto_download_updates":
                return True
            elif key == "updates/check_frequency_days":
                return 14
            else:
                return default
        
        self.mock_settings_instance.value.side_effect = mock_value
        
        # Load settings
        settings_data = self.settings.load_settings()
        
        # Verify custom values were loaded
        self.assertFalse(settings_data["check_updates_on_startup"])
        self.assertTrue(settings_data["auto_download_updates"])
        self.assertEqual(settings_data["check_frequency_days"], 14)
        
        # Verify other settings have default values
        self.assertEqual(settings_data["notify_on_update"], DEFAULT_SETTINGS["notify_on_update"])
        self.assertEqual(settings_data["update_channel"], DEFAULT_SETTINGS["update_channel"])
    
    def test_load_settings_boolean_conversion(self):
        """Test that string booleans are properly converted."""
        # Mock string boolean values
        def mock_value(key, default):
            if key == "updates/check_updates_on_startup":
                return "true"  # String "true"
            elif key == "updates/auto_download_updates":
                return "false"  # String "false"
            elif key == "updates/notify_on_update":
                return "1"  # String "1"
            else:
                return default
        
        self.mock_settings_instance.value.side_effect = mock_value
        
        # Load settings
        settings_data = self.settings.load_settings()
        
        # Verify boolean conversion
        self.assertTrue(settings_data["check_updates_on_startup"])
        self.assertFalse(settings_data["auto_download_updates"])
        self.assertTrue(settings_data["notify_on_update"])
        self.assertTrue(isinstance(settings_data["check_updates_on_startup"], bool))
        self.assertTrue(isinstance(settings_data["auto_download_updates"], bool))
        self.assertTrue(isinstance(settings_data["notify_on_update"], bool))
    
    def test_save_settings(self):
        """Test saving settings."""
        # Set up test data
        self.settings._settings_data = {
            "check_updates_on_startup": False,
            "auto_download_updates": True,
            "notify_on_update": False,
            "check_frequency_days": 30,
            "update_channel": "beta"
        }
        
        # Save settings
        self.settings.save_settings()
        
        # Verify settings were saved
        expected_calls = [
            ('updates/check_updates_on_startup', False),
            ('updates/auto_download_updates', True),
            ('updates/notify_on_update', False),
            ('updates/check_frequency_days', 30),
            ('updates/update_channel', 'beta')
        ]
        
        for args in expected_calls:
            self.mock_settings_instance.setValue.assert_any_call(*args)
        
        # Verify sync was called
        self.mock_settings_instance.sync.assert_called_once()
    
    def test_save_settings_error(self):
        """Test handling errors during saving settings."""
        # Set up test data
        self.settings._settings_data = {
            "check_updates_on_startup": False
        }
        
        # Make setValue throw an exception
        self.mock_settings_instance.setValue.side_effect = Exception("Test error")
        
        # Save settings (should not raise exception)
        self.settings.save_settings()
    
    def test_get_setting(self):
        """Test getting a specific setting."""
        # Set up test data
        self.settings._settings_data = {
            "check_updates_on_startup": False,
            "auto_download_updates": True
        }
        
        # Get settings
        value1 = self.settings.get_setting("check_updates_on_startup")
        value2 = self.settings.get_setting("auto_download_updates")
        
        # Verify values
        self.assertFalse(value1)
        self.assertTrue(value2)
    
    def test_get_setting_default(self):
        """Test getting a setting with default value."""
        # Set up test data (missing some keys)
        self.settings._settings_data = {
            "check_updates_on_startup": False
        }
        
        # Get non-existent setting with default
        value = self.settings.get_setting("non_existent_key", default="default_value")
        
        # Verify default value was returned
        self.assertEqual(value, "default_value")
    
    def test_set_setting(self):
        """Test setting a specific setting."""
        # Set up initial data
        self.settings._settings_data = {
            "check_updates_on_startup": True
        }
        
        # Set setting
        self.settings.set_setting("check_updates_on_startup", False)
        self.settings.set_setting("new_setting", "new_value")
        
        # Verify values
        self.assertFalse(self.settings._settings_data["check_updates_on_startup"])
        self.assertEqual(self.settings._settings_data["new_setting"], "new_value")
    
    def test_should_check_updates_on_startup(self):
        """Test checking if updates should be checked on startup."""
        # Test with default value (True)
        self.settings._settings_data = {
            "check_updates_on_startup": True
        }
        self.assertTrue(self.settings.should_check_updates_on_startup())
        
        # Test with custom value (False)
        self.settings._settings_data = {
            "check_updates_on_startup": False
        }
        self.assertFalse(self.settings.should_check_updates_on_startup())
        
        # Test with missing value (should use default)
        self.settings._settings_data = {}
        self.assertTrue(self.settings.should_check_updates_on_startup())
    
    def test_should_auto_download_updates(self):
        """Test checking if updates should be auto-downloaded."""
        # Test with default value (False)
        self.settings._settings_data = {
            "auto_download_updates": False
        }
        self.assertFalse(self.settings.should_auto_download_updates())
        
        # Test with custom value (True)
        self.settings._settings_data = {
            "auto_download_updates": True
        }
        self.assertTrue(self.settings.should_auto_download_updates())
        
        # Test with missing value (should use default)
        self.settings._settings_data = {}
        self.assertFalse(self.settings.should_auto_download_updates())
    
    def test_should_notify_on_update(self):
        """Test checking if notifications should be shown for updates."""
        # Test with default value (True)
        self.settings._settings_data = {
            "notify_on_update": True
        }
        self.assertTrue(self.settings.should_notify_on_update())
        
        # Test with custom value (False)
        self.settings._settings_data = {
            "notify_on_update": False
        }
        self.assertFalse(self.settings.should_notify_on_update())
        
        # Test with missing value (should use default)
        self.settings._settings_data = {}
        self.assertTrue(self.settings.should_notify_on_update())
    
    def test_update_last_check_time(self):
        """Test updating the last check time."""
        # Set up initial data
        self.settings._settings_data = {}
        
        # Mock save_settings to avoid actual save
        self.settings.save_settings = MagicMock()
        
        # Update last check time
        test_time = "2023-01-01T12:00:00"
        self.settings.update_last_check_time(test_time)
        
        # Verify value was set
        self.assertEqual(self.settings._settings_data["last_check_time"], test_time)
        
        # Verify save_settings was called
        self.settings.save_settings.assert_called_once()
    
    def test_get_update_settings_singleton(self):
        """Test that get_update_settings returns a singleton instance."""
        # Get settings instances
        settings1 = get_update_settings()
        settings2 = get_update_settings()
        
        # Verify both instances are the same object
        self.assertIs(settings1, settings2)
        
        # Verify it's an UpdateSettings instance
        self.assertIsInstance(settings1, UpdateSettings)


if __name__ == "__main__":
    unittest.main() 