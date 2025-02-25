"""
Layout Helper Tests

This module contains tests for the layout helper utilities,
which help with creating UI layouts that work well with
internationalized applications.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QFormLayout, QGridLayout
from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import QFont

from scout.ui.utils.layout_helper import (
    get_current_language_code, get_expansion_factor,
    calculate_min_width_for_text, set_min_width_for_text,
    adjust_button_sizes, create_form_layout, create_responsive_grid_layout
)


class TestLayoutHelper(unittest.TestCase):
    """Tests for the layout helper utilities."""
    
    def setUp(self):
        """Set up the test environment."""
        self.app = QApplication.instance() or QApplication(sys.argv)
    
    def test_get_current_language_code(self):
        """Test getting the current language code."""
        # Patch QLocale.system() to return a specific locale
        with patch('PyQt6.QtCore.QLocale.system') as mock_system:
            mock_locale = MagicMock()
            mock_locale.name.return_value = "en_US"
            mock_system.return_value = mock_locale
            
            result = get_current_language_code()
            self.assertEqual(result, "en")
            
            # Test with a different locale
            mock_locale.name.return_value = "de_DE"
            result = get_current_language_code()
            self.assertEqual(result, "de")
    
    def test_get_expansion_factor(self):
        """Test getting the expansion factor for different languages."""
        # Patch get_current_language_code to return specific languages
        with patch('scout.ui.utils.layout_helper.get_current_language_code') as mock_get_code:
            # Test English
            mock_get_code.return_value = "en"
            result = get_expansion_factor()
            self.assertEqual(result, 1.0)
            
            # Test German
            mock_get_code.return_value = "de"
            result = get_expansion_factor()
            self.assertEqual(result, 1.3)
            
            # Test Japanese
            mock_get_code.return_value = "ja"
            result = get_expansion_factor()
            self.assertEqual(result, 0.6)
            
            # Test unknown language (should default to 1.0)
            mock_get_code.return_value = "xx"
            result = get_expansion_factor()
            self.assertEqual(result, 1.0)
    
    def test_calculate_min_width_for_text(self):
        """Test calculating the minimum width for text."""
        # Simple text
        short_text = "OK"
        min_width = calculate_min_width_for_text(short_text)
        self.assertGreater(min_width, len(short_text))  # Should be more than just the character count
        
        # Longer text should result in wider width
        long_text = "This is a much longer piece of text"
        long_width = calculate_min_width_for_text(long_text)
        self.assertGreater(long_width, min_width)
        
        # Test with a specific font
        font = QFont("Arial", 14)
        font_width = calculate_min_width_for_text(short_text, font)
        # Font size should affect the width, but hard to test precisely
    
    def test_set_min_width_for_text(self):
        """Test setting the minimum width for a widget based on text."""
        label = QLabel("Test Label")
        original_min_width = label.minimumWidth()
        
        # Setting min width should change the widget's minimum width
        set_min_width_for_text(label, "Test Label")
        new_min_width = label.minimumWidth()
        
        # New width should be greater than original (or equal if already sufficient)
        self.assertGreaterEqual(new_min_width, original_min_width)
        
        # Test with longer text
        set_min_width_for_text(label, "This is a much longer test label")
        long_min_width = label.minimumWidth()
        self.assertGreater(long_min_width, new_min_width)
    
    def test_adjust_button_sizes(self):
        """Test adjusting button sizes to be consistent."""
        # Create some buttons with different text lengths
        button1 = QPushButton("OK")
        button2 = QPushButton("Cancel")
        button3 = QPushButton("Apply and Close")
        
        # Get initial widths
        width1 = button1.minimumWidth()
        width2 = button2.minimumWidth()
        width3 = button3.minimumWidth()
        
        # Adjust button sizes
        buttons = [button1, button2, button3]
        adjust_button_sizes(buttons)
        
        # All buttons should now have the same minimum width
        self.assertEqual(button1.minimumWidth(), button2.minimumWidth())
        self.assertEqual(button2.minimumWidth(), button3.minimumWidth())
        
        # The width should be based on the longest text
        self.assertGreaterEqual(button1.minimumWidth(), max(width1, width2, width3))
    
    def test_create_form_layout(self):
        """Test creating a form layout with proper configuration."""
        layout = create_form_layout()
        
        # Verify the layout is properly configured
        self.assertEqual(layout.labelAlignment(), Qt.AlignmentFlag.AlignRight)
        self.assertEqual(layout.formAlignment(), Qt.AlignmentFlag.AlignLeft)
        self.assertEqual(layout.fieldGrowthPolicy(), QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    
    def test_create_responsive_grid_layout(self):
        """Test creating a responsive grid layout."""
        # Test with default columns (2)
        layout1 = create_responsive_grid_layout()
        self.assertEqual(layout1.columnStretch(0), 1)
        self.assertEqual(layout1.columnStretch(1), 1)
        
        # Test with custom columns
        columns = 4
        layout2 = create_responsive_grid_layout(columns)
        for i in range(columns):
            self.assertEqual(layout2.columnStretch(i), 1)


if __name__ == "__main__":
    unittest.main() 