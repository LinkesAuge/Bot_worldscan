"""
Platform-Specific UI Tests

This module tests the platform-specific behaviors of the UI components,
ensuring that they adapt correctly to different operating systems.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QStyle
from PyQt6.QtCore import Qt

from scout.tests.cross_platform.platform_utils import (
    PlatformType,
    get_current_platform,
    PlatformContext
)


class TestUIPlatformSpecific(unittest.TestCase):
    """Test platform-specific behaviors of UI components."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test class with a QApplication instance."""
        # Create QApplication if it doesn't exist
        cls.app = QApplication.instance() or QApplication(sys.argv)
    
    def test_default_styles(self):
        """Test that platform-appropriate default styles are applied."""
        # Creating a window should apply appropriate platform styles
        window = QMainWindow()
        
        # Perform basic style checks that should work on all platforms
        # These are very basic and just verify that style properties exist
        self.assertIsNotNone(window.style())
        self.assertTrue(hasattr(window.style(), 'standardPalette'))
    
    def test_file_dialogs_default_locations(self):
        """Test that file dialogs use platform-appropriate default locations."""
        # This is more of a smoke test since we can't easily test actual dialog behavior
        # without UI interaction, but we can verify the code doesn't crash
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName') as mock_dialog:
            # Mock the dialog return value
            mock_dialog.return_value = ("", "")
            
            # Import here to avoid circular imports
            from scout.ui.utils.file_utils import get_open_filename
            
            # Call the function (should use platform-appropriate paths)
            get_open_filename("Open File", "", "All Files (*.*)")
            
            # Verify the function was called
            mock_dialog.assert_called_once()
    
    def test_standard_paths(self):
        """Test platform-specific standard paths."""
        from PyQt6.QtCore import QStandardPaths
        
        # Get documents location (should be platform-specific)
        docs_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        self.assertIsNotNone(docs_location)
        self.assertTrue(len(docs_location) > 0)
        
        # Get app data location (should be platform-specific)
        app_data_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.assertIsNotNone(app_data_location)
        self.assertTrue(len(app_data_location) > 0)
    
    def test_platform_specific_shortcuts(self):
        """Test platform-specific keyboard shortcuts."""
        # Import here to avoid circular imports
        from scout.ui.utils.shortcuts import get_platform_specific_key_sequence
        
        # Test platform-specific shortcuts for common actions
        # Save action - Typically Ctrl+S on Windows/Linux, Command+S on macOS
        save_shortcut = get_platform_specific_key_sequence(
            win_shortcut="Ctrl+S",
            mac_shortcut="Cmd+S",
            linux_shortcut="Ctrl+S"
        )
        self.assertIsNotNone(save_shortcut)
        
        # Copy action - Typically Ctrl+C on Windows/Linux, Command+C on macOS
        copy_shortcut = get_platform_specific_key_sequence(
            win_shortcut="Ctrl+C",
            mac_shortcut="Cmd+C",
            linux_shortcut="Ctrl+C"
        )
        self.assertIsNotNone(copy_shortcut)
    
    def test_platform_specific_icons(self):
        """Test platform-specific icons."""
        # Create a main window
        window = QMainWindow()
        
        # Get standard icons that might have platform-specific appearances
        standard_icons = [
            QStyle.StandardPixmap.SP_DialogOkButton,
            QStyle.StandardPixmap.SP_DialogCancelButton,
            QStyle.StandardPixmap.SP_DialogHelpButton,
            QStyle.StandardPixmap.SP_DialogOpenButton,
            QStyle.StandardPixmap.SP_DialogSaveButton,
            QStyle.StandardPixmap.SP_DialogCloseButton,
            QStyle.StandardPixmap.SP_DirHomeIcon,
        ]
        
        # Verify we can get all the standard icons without errors
        for icon_enum in standard_icons:
            icon = window.style().standardIcon(icon_enum)
            self.assertIsNotNone(icon)
            self.assertFalse(icon.isNull())


class TestFilePathHandlingPlatformSpecific(unittest.TestCase):
    """Test platform-specific file path handling."""
    
    def test_path_normalization(self):
        """Test that paths are normalized correctly for each platform."""
        test_paths = [
            # Mixed slashes
            "path/to\\file.txt",
            # Double slashes
            "path//to/file.txt",
            # Trailing slash
            "path/to/dir/",
            # Dots
            "path/./to/../to/file.txt",
        ]
        
        for test_path in test_paths:
            # Normalize the path
            normalized = Path(test_path).resolve().as_posix()
            
            # The normalized path should not contain backslashes
            self.assertNotIn('\\', normalized)
            
            # The normalized path should not contain double slashes
            self.assertNotIn('//', normalized)
    
    def test_path_joining(self):
        """Test that path joining works correctly on each platform."""
        # Components to join
        components = ["path", "to", "file.txt"]
        
        # Join using os.path.join (platform-specific)
        os_joined = os.path.join(*components)
        
        # Join using pathlib (normalized)
        pathlib_joined = str(Path(*components))
        
        # Paths should be valid on the current platform
        self.assertTrue(os.path.isabs(os.path.abspath(os_joined)))
        self.assertTrue(os.path.isabs(os.path.abspath(pathlib_joined)))


if __name__ == "__main__":
    unittest.main() 