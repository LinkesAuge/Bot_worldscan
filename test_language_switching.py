#!/usr/bin/env python3
"""
Language Switching Test

This script launches the Scout application with different language settings to test the
internationalization functionality. It provides a simple command-line interface to
switch between supported languages and verify translation and layout adaptability.
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure scout package is in Python path
script_dir = Path(__file__).absolute().parent
if script_dir not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
    from PyQt6.QtCore import Qt, QTimer
    from scout.ui.utils.language_manager import get_language_manager, Language
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you have installed all required dependencies.")
    sys.exit(1)

class LanguageSwitchingTester(QWidget):
    """Simple widget to control language switching for testing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Language Testing Tool")
        self.setGeometry(100, 100, 300, 200)
        
        # Get language manager
        self.language_manager = get_language_manager()
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add current language label
        self.current_lang_label = QLabel("Current Language: English")
        layout.addWidget(self.current_lang_label)
        
        # Add language buttons
        self.en_button = QPushButton("Switch to English")
        self.en_button.clicked.connect(lambda: self.switch_language(Language.ENGLISH))
        layout.addWidget(self.en_button)
        
        self.de_button = QPushButton("Switch to German")
        self.de_button.clicked.connect(lambda: self.switch_language(Language.GERMAN))
        layout.addWidget(self.de_button)
        
        self.sys_button = QPushButton("Switch to System Default")
        self.sys_button.clicked.connect(lambda: self.switch_language(Language.SYSTEM))
        layout.addWidget(self.sys_button)
        
        # Add quit button
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        layout.addWidget(self.quit_button)
        
        # Set initial state
        current_lang = self.language_manager.get_current_language()
        self.update_current_language_label(current_lang)
    
    def switch_language(self, language: Language):
        """Switch the application language."""
        success = self.language_manager.set_language(language)
        if success:
            self.update_current_language_label(language)
            print(f"Language switched to: {language.name}")
        else:
            print(f"Failed to switch language to: {language.name}")
    
    def update_current_language_label(self, language: Language):
        """Update the current language label."""
        lang_name = "System Default"
        if language == Language.ENGLISH:
            lang_name = "English"
        elif language == Language.GERMAN:
            lang_name = "German"
        
        self.current_lang_label.setText(f"Current Language: {lang_name}")


def launch_app_with_language(language: str = None):
    """Launch the main application with the specified language."""
    try:
        # Import main application only when needed
        from main import run_application
        
        # Set language environment variable if specified
        if language:
            os.environ["LANGUAGE"] = language
            print(f"Setting language to: {language}")
        
        # Launch the application
        run_application()
        
    except ImportError as e:
        print(f"Error importing main application: {e}")
        print("Make sure you are running this script from the project root directory.")
        sys.exit(1)


def run_language_tester():
    """Run the standalone language testing tool."""
    app = QApplication(sys.argv)
    tester = LanguageSwitchingTester()
    tester.show()
    sys.exit(app.exec())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test language switching in Scout application")
    parser.add_argument("--language", "-l", type=str, choices=["en", "de", "system"], 
                        help="Initial language to use (en, de, system)")
    parser.add_argument("--tester", "-t", action="store_true", 
                        help="Launch the language testing tool instead of the main application")
    
    args = parser.parse_args()
    
    if args.tester:
        run_language_tester()
    else:
        launch_app_with_language(args.language)


if __name__ == "__main__":
    main() 