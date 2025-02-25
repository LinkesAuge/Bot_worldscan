#!/usr/bin/env python3
"""
Test Translator Application

This script tests the functionality of the translator application,
ensuring it can load and display UI components, switch languages, and
properly visualize layout issues.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QSize, Qt, QLocale, QTranslator, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QPixmap

# Ensure the scout package is in the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from scout.translations.translator_app import (
    TranslatorApp, ComponentPreviewWidget, main
)
from scout.translations.config import LANGUAGE_EXPANSION_FACTORS


class TestComponentPreviewWidget(unittest.TestCase):
    """Test the component preview widget's functionality."""
    
    def setUp(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.widget = ComponentPreviewWidget()
    
    def tearDown(self):
        self.widget.deleteLater()
    
    def test_initialization(self):
        """Test the widget initializes with the correct default state."""
        self.assertFalse(self.widget.show_borders)
        self.assertFalse(self.widget.highlight_issues)
        self.assertEqual(self.widget.expansion_factor, 1.0)
        self.assertIsNone(self.widget.component)
        self.assertIsNotNone(self.widget.default_label)
    
    def test_set_component(self):
        """Test setting a component to preview."""
        test_component = QWidget()
        self.widget.set_component(test_component)
        
        self.assertEqual(self.widget.component, test_component)
        self.assertIsNone(self.widget.default_label)
        
        # Test replacing with a new component
        new_component = QWidget()
        self.widget.set_component(new_component)
        self.assertEqual(self.widget.component, new_component)
    
    def test_set_show_borders(self):
        """Test toggling the border display."""
        self.assertFalse(self.widget.show_borders)
        
        self.widget.set_show_borders(True)
        self.assertTrue(self.widget.show_borders)
        
        self.widget.set_show_borders(False)
        self.assertFalse(self.widget.show_borders)
    
    def test_set_highlight_issues(self):
        """Test toggling the issue highlighting."""
        self.assertFalse(self.widget.highlight_issues)
        
        self.widget.set_highlight_issues(True)
        self.assertTrue(self.widget.highlight_issues)
        
        self.widget.set_highlight_issues(False)
        self.assertFalse(self.widget.highlight_issues)
    
    def test_set_expansion_factor(self):
        """Test setting the expansion factor."""
        self.assertEqual(self.widget.expansion_factor, 1.0)
        
        self.widget.set_expansion_factor(1.3)
        self.assertEqual(self.widget.expansion_factor, 1.3)


class TestTranslatorApp(unittest.TestCase):
    """Test the TranslatorApp's functionality."""
    
    def setUp(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Mock translators
        self.mock_translators = {
            'en': MagicMock(),
            'de': MagicMock()
        }
        
        # Patch the QTranslator.load method to always return True
        self.load_patch = patch('PyQt6.QtCore.QTranslator.load', return_value=True)
        self.mock_load = self.load_patch.start()
        
        # Patch the Path.exists method to simulate .qm files
        self.exists_patch = patch('pathlib.Path.exists', return_value=True)
        self.mock_exists = self.exists_patch.start()
        
        # Create the translator app
        self.translator_app = TranslatorApp()
    
    def tearDown(self):
        self.translator_app.deleteLater()
        self.load_patch.stop()
        self.exists_patch.stop()
    
    def test_initialization(self):
        """Test the application initializes correctly."""
        self.assertEqual(self.translator_app.current_language, 'en')
        self.assertIsNotNone(self.translator_app.language_combo)
        self.assertIsNotNone(self.translator_app.tree_widget)
        self.assertIsNotNone(self.translator_app.preview_widget)
    
    def test_tree_widget_population(self):
        """Test that the tree widget is populated with components."""
        # Check that the tree has the expected top-level items
        root = self.translator_app.tree_widget.invisibleRootItem()
        self.assertTrue(root.childCount() > 0)
        
        # Check categories exist (Main Window, Detection, Automation, etc.)
        categories = set()
        for i in range(root.childCount()):
            categories.add(root.child(i).text(0))
        
        expected_categories = {
            "Main Window", "Detection", "Automation", 
            "Game State", "Settings"
        }
        
        for category in expected_categories:
            self.assertIn(category, categories)
    
    def test_component_creation(self):
        """Test that components can be created for preview."""
        for component_id in [
            "menu_bar", "tool_bar", "detection_settings", 
            "game_state_overview", "general_settings", "about_dialog"
        ]:
            component = self.translator_app.create_component(component_id)
            self.assertIsNotNone(component, f"Failed to create component: {component_id}")
            self.assertIsInstance(component, QWidget)
    
    @patch('PyQt6.QtWidgets.QApplication.installTranslator')
    @patch('PyQt6.QtWidgets.QApplication.removeTranslator')
    def test_change_language(self, mock_remove, mock_install):
        """Test changing the application language."""
        # Store initial language
        initial_language = self.translator_app.current_language
        
        # Set up language combo box
        language_index = -1
        for i in range(self.translator_app.language_combo.count()):
            if self.translator_app.language_combo.itemData(i) == 'de':
                language_index = i
                break
        
        self.assertNotEqual(language_index, -1, "German language not found in combo box")
        
        # Change language to German
        self.translator_app.language_combo.setCurrentIndex(language_index)
        
        # Verify language changed
        self.assertEqual(self.translator_app.current_language, 'de')
        self.assertNotEqual(self.translator_app.current_language, initial_language)
        
        # Verify translator handling
        mock_remove.assert_called()
        if 'de' in self.translator_app.translators:
            mock_install.assert_called_with(self.translator_app.translators['de'])
    
    def test_save_screenshot(self):
        """Test saving a screenshot."""
        # Mock a component for preview
        component = self.translator_app.create_component("about_dialog")
        self.translator_app.preview_widget.set_component(component)
        
        # Mock QFileDialog.getSaveFileName
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', 
                  return_value=(os.path.join(tempfile.gettempdir(), "test_screenshot.png"), "PNG Files (*.png)")):
            
            # Mock QWidget.grab to return a pixmap
            with patch('PyQt6.QtWidgets.QWidget.grab', return_value=QPixmap(10, 10)):
                
                # Mock QPixmap.save to return True
                with patch('PyQt6.QtGui.QPixmap.save', return_value=True):
                    
                    # Call the save_screenshot method
                    self.translator_app.save_screenshot()
                    
                    # Verify status update
                    self.assertTrue("Screenshot saved" in self.translator_app.status_bar.currentMessage())


@patch('scout.translations.translator_app.QApplication')
@patch('scout.translations.translator_app.TranslatorApp')
def test_main_function(mock_translator_app, mock_qapp):
    """Test the main function."""
    # Set up mocks
    mock_app_instance = MagicMock()
    mock_qapp.instance.return_value = None
    mock_qapp.return_value = mock_app_instance
    
    mock_window = MagicMock()
    mock_translator_app.return_value = mock_window
    
    # Call main function
    main()
    
    # Verify application was created and run
    mock_qapp.assert_called_once_with(sys.argv)
    mock_translator_app.assert_called_once()
    mock_window.show.assert_called_once()
    mock_app_instance.exec.assert_called_once()


if __name__ == "__main__":
    unittest.main() 