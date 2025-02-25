#!/usr/bin/env python3
"""
Test Translation Checker

This script tests the functionality of the translation checker tool,
ensuring it can properly identify translation issues in the codebase.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import xml.etree.ElementTree as ET

# Ensure the scout package is in the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from scout.translations.check_translations import TranslationChecker


class TestTranslationChecker(unittest.TestCase):
    """Test the TranslationChecker's functionality."""
    
    def setUp(self):
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Create the checker with the test directory
        self.checker = TranslationChecker(self.test_dir)
        
        # Create test files
        self.create_test_files()
    
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def create_test_files(self):
        """Create test files for checking."""
        # Python file with hardcoded strings
        py_content = """
        def some_function():
            # This file has hardcoded strings
            label = QLabel("Hardcoded String")
            button = QPushButton("Click Me")
            button.setFixedWidth(100)  # Layout issue
            window.setWindowTitle("My Window")
            
            # This string is translated
            translated = tr("Translated String")
            
            # This is a long text string
            long_text = tr("This is a very long text string that might cause layout issues when translated to other languages")
        """
        py_file = self.test_dir / "test.py"
        py_file.write_text(py_content)
        
        # UI file
        ui_content = """
        <ui version="4.0">
         <class>MainWindow</class>
         <widget class="QMainWindow" name="MainWindow">
          <property name="geometry">
           <rect>
            <x>0</x>
            <y>0</y>
            <width>800</width>
            <height>600</height>
           </rect>
          </property>
          <property name="windowTitle">
           <string>Main Window</string>
          </property>
          <widget class="QWidget" name="centralwidget">
           <layout class="QVBoxLayout" name="verticalLayout">
            <item>
             <widget class="QLabel" name="label">
              <property name="text">
               <string>Hardcoded UI String</string>
              </property>
             </widget>
            </item>
            <item>
             <widget class="QPushButton" name="pushButton">
              <property name="text">
               <string>UI Button</string>
              </property>
             </widget>
            </item>
           </layout>
          </widget>
         </widget>
        </ui>
        """
        ui_file = self.test_dir / "test.ui"
        ui_file.write_text(ui_content)
        
        # Translation file with correct <name> tags
        ts_content = """
        <!DOCTYPE TS>
        <TS version="2.1" language="en_US">
        <context>
            <name>MainWindow</name>
            <message>
                <source>Translated String</source>
                <translation>Translated String</translation>
            </message>
        </context>
        </TS>
        """
        ts_file = self.test_dir / "test_en.ts"
        ts_file.write_text(ts_content)
    
    def test_find_files(self):
        """Test finding relevant files."""
        self.checker.find_files()
        
        self.assertEqual(len(self.checker.py_files), 1)
        self.assertEqual(len(self.checker.ui_files), 1)
        self.assertEqual(len(self.checker.ts_files), 1)
        
        self.assertEqual(self.checker.py_files[0].name, "test.py")
        self.assertEqual(self.checker.ui_files[0].name, "test.ui")
        self.assertEqual(self.checker.ts_files[0].name, "test_en.ts")
    
    def test_parse_ts_files(self):
        """Test parsing translation files."""
        self.checker.find_files()
        self.checker.parse_ts_files()
        
        self.assertIn("MainWindow", self.checker.ts_contexts)
        self.assertIn("Translated String", self.checker.ts_contexts["MainWindow"])
    
    def test_check_py_files(self):
        """Test checking Python files for issues."""
        self.checker.find_files()
        self.checker.check_py_files()
        
        # There should be hardcoded strings
        self.assertEqual(len(self.checker.hardcoded_strings), 1)
        py_file = self.checker.py_files[0]
        hardcoded_strings = self.checker.hardcoded_strings[py_file]
        
        # Check hardcoded strings were found
        hardcoded_text = [text for _, text in hardcoded_strings]
        self.assertIn("Hardcoded String", hardcoded_text)
        self.assertIn("Click Me", hardcoded_text)
        self.assertIn("My Window", hardcoded_text)
        
        # Check layout issues
        self.assertEqual(len(self.checker.layout_issues), 1)
        layout_issues = self.checker.layout_issues[py_file]
        self.assertTrue(any("setFixedWidth" in issue[1] for issue in layout_issues))
        
        # Check long text issues
        self.assertEqual(len(self.checker.long_text_issues), 1)
        long_text_issues = self.checker.long_text_issues[py_file]
        self.assertTrue(any(len(text) > 30 for _, text in long_text_issues))
    
    def test_check_ui_files(self):
        """Test checking UI files for issues."""
        self.checker.find_files()
        self.checker.check_ui_files()
        
        # There should be hardcoded strings
        self.assertEqual(len(self.checker.hardcoded_strings), 1)
        ui_file = self.checker.ui_files[0]
        hardcoded_strings = self.checker.hardcoded_strings[ui_file]
        
        # Check hardcoded strings were found
        hardcoded_text = [text for _, text in hardcoded_strings]
        self.assertIn("Hardcoded UI String", hardcoded_text)
        self.assertIn("UI Button", hardcoded_text)
        self.assertIn("Main Window", hardcoded_text)
        
        # Check layout issues
        self.assertEqual(len(self.checker.layout_issues), 1)
        layout_issues = self.checker.layout_issues[ui_file]
        self.assertTrue(any("width" in issue[1] for issue in layout_issues))
    
    def test_check_missing_translations(self):
        """Test checking for missing translations."""
        # Capture logging output
        with patch('logging.warning') as mock_warning:
            self.checker.find_files()
            self.checker.parse_ts_files()
            self.checker.check_py_files()
            self.checker.check_missing_translations()
            
            # Verify that warning about missing translations was called
            mock_warning.assert_called()
            
            # Get all the warning calls
            warning_calls = [call[0][0] for call in mock_warning.call_args_list]
            # Check for missing translation warning for a specific string
            missing_translation_warning = any(
                "strings marked for translation but missing" in warning 
                for warning in warning_calls
            )
            self.assertTrue(missing_translation_warning)
    
    @patch('builtins.print')
    def test_generate_report(self, mock_print):
        """Test report generation."""
        self.checker.find_files()
        self.checker.parse_ts_files()
        self.checker.check_py_files()
        self.checker.check_ui_files()
        self.checker.check_missing_translations()
        self.checker.generate_report()
        
        # Verify print was called multiple times for the report
        self.assertTrue(mock_print.call_count > 10)
        
        # Check that various sections were included in the report
        report_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # Verify report sections
        self.assertTrue(any("HARDCODED STRINGS" in call for call in report_calls))
        self.assertTrue(any("LAYOUT ISSUES" in call for call in report_calls))
        self.assertTrue(any("LONG TEXT" in call for call in report_calls))
        self.assertTrue(any("SUMMARY" in call for call in report_calls))
        self.assertTrue(any("RECOMMENDATIONS" in call for call in report_calls))
    
    def test_run(self):
        """Test the full run process."""
        with patch.object(self.checker, 'find_files') as mock_find:
            with patch.object(self.checker, 'parse_ts_files') as mock_parse:
                with patch.object(self.checker, 'check_py_files') as mock_check_py:
                    with patch.object(self.checker, 'check_ui_files') as mock_check_ui:
                        with patch.object(self.checker, 'check_missing_translations') as mock_check_missing:
                            with patch.object(self.checker, 'generate_report') as mock_report:
                                
                                # Run the checker
                                self.checker.run()
                                
                                # Verify all methods were called
                                mock_find.assert_called_once()
                                mock_parse.assert_called_once()
                                mock_check_py.assert_called_once()
                                mock_check_ui.assert_called_once()
                                mock_check_missing.assert_called_once()
                                mock_report.assert_called_once()


if __name__ == "__main__":
    unittest.main() 