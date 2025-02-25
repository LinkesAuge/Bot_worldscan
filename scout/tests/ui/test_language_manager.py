"""
Language Manager Test

This module contains tests for the language management functionality,
ensuring that language switching works correctly and that translations
are properly applied across the application.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QCoreApplication, QSettings, QTranslator
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from scout.ui.utils.language_manager import Language, LanguageManager, get_language_manager, tr


class TestLanguageManager(unittest.TestCase):
    """Tests for the LanguageManager class."""

    def setUp(self):
        """Set up test environment."""
        # Create QApplication instance for testing
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Clear any existing settings
        settings = QSettings("ScoutTeam", "Scout")
        settings.clear()
        
        # Create a test widget with translatable strings
        self.test_widget = QWidget()
        self.test_label = QLabel("Settings", self.test_widget)
        self.test_button = QPushButton("Save", self.test_widget)

    def tearDown(self):
        """Clean up after tests."""
        self.test_widget.deleteLater()
        
        # Clear settings
        settings = QSettings("ScoutTeam", "Scout")
        settings.clear()

    def test_instance_creation(self):
        """Test that we can create a LanguageManager instance."""
        manager = LanguageManager()
        self.assertIsNotNone(manager)
        
    def test_singleton(self):
        """Test that get_language_manager returns a singleton instance."""
        manager1 = get_language_manager()
        manager2 = get_language_manager()
        self.assertIs(manager1, manager2)
        
    def test_default_language(self):
        """Test that the default language is Language.SYSTEM."""
        manager = LanguageManager()
        self.assertEqual(manager.get_current_language(), Language.SYSTEM)
        
    def test_set_language(self):
        """Test setting the language."""
        manager = LanguageManager()
        
        # Set to English
        result = manager.set_language(Language.ENGLISH)
        self.assertTrue(result)
        self.assertEqual(manager.get_current_language(), Language.ENGLISH)
        
        # Set to German
        result = manager.set_language(Language.GERMAN)
        self.assertTrue(result)
        self.assertEqual(manager.get_current_language(), Language.GERMAN)
        
        # Set back to System
        result = manager.set_language(Language.SYSTEM)
        self.assertTrue(result)
        self.assertEqual(manager.get_current_language(), Language.SYSTEM)
        
    def test_language_persistence(self):
        """Test that language settings persist between instances."""
        # First instance sets language
        manager1 = LanguageManager()
        manager1.set_language(Language.GERMAN)
        
        # Second instance should have the same language
        manager2 = LanguageManager()
        self.assertEqual(manager2.get_current_language(), Language.GERMAN)
        
    def test_translation_function(self):
        """Test the tr function."""
        # Simple translation test
        result = tr("Test")
        self.assertIsInstance(result, str)
        
        # With context
        result = tr("Test", "Context")
        self.assertIsInstance(result, str)
        
        # With plural form
        result = tr("Test", n=2)
        self.assertIsInstance(result, str)

    @patch('scout.ui.utils.language_manager.QTranslator.load')
    def test_language_switching_effect(self, mock_load):
        """Test that switching language has an effect on the UI."""
        # Mock successful loading of translation file
        mock_load.return_value = True
        
        # Create a new manager for this test to avoid conflicts
        with patch('scout.ui.utils.language_manager._language_manager', None):
            manager = get_language_manager()
            
            # Set language to German
            result = manager.set_language(Language.GERMAN)
            self.assertTrue(result)
            self.assertEqual(manager.get_current_language(), Language.GERMAN)
            
            # Verify that set_language was called with the right parameters
            mock_load.assert_called()
            
            # Set back to English for cleanup
            manager.set_language(Language.ENGLISH)


class TestIntegrationLanguageUI(unittest.TestCase):
    """Integration tests for language UI components."""
    
    def setUp(self):
        """Set up test environment."""
        # Create QApplication instance for testing
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Clear any existing settings
        settings = QSettings("ScoutTeam", "Scout")
        settings.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        # Clear settings
        settings = QSettings("ScoutTeam", "Scout")
        settings.clear()
    
    @patch('scout.ui.utils.language_manager.QTranslator.load')
    def test_language_switching_with_ui(self, mock_load):
        """Test switching between languages with actual UI elements."""
        # Mock successful loading of translation file
        mock_load.return_value = True
        
        # Create a fresh manager for this test
        with patch('scout.ui.utils.language_manager._language_manager', None):
            manager = get_language_manager()
            
            # Create a test widget with translatable texts
            from PyQt6.QtWidgets import QVBoxLayout
            test_widget = QWidget()
            layout = QVBoxLayout(test_widget)
            
            # Add some UI elements with translatable strings
            settings_label = QLabel(tr("Settings", "SettingsTab"))
            language_label = QLabel(tr("Language", "SettingsTab"))
            save_button = QPushButton(tr("Save", "MainWindow"))
            
            layout.addWidget(settings_label)
            layout.addWidget(language_label)
            layout.addWidget(save_button)
            
            # Switch to German and verify that the UI elements use translated strings
            result = manager.set_language(Language.GERMAN)
            self.assertTrue(result)
            self.assertEqual(manager.get_current_language(), Language.GERMAN)
            
            # We would need to verify the actual translated text here,
            # but since we mocked the translator loading, we can only
            # verify that the process was attempted
            mock_load.assert_called()
            
            # Switch back to English for cleanup
            manager.set_language(Language.ENGLISH)


if __name__ == "__main__":
    unittest.main() 