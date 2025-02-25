#!/usr/bin/env python3
"""
Language Persistence Test

This script tests whether language settings persist between application sessions.
It uses QSettings to check and manipulate the application's language settings directly.
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtCore import QSettings, QCoreApplication
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LanguagePersistenceTester(QWidget):
    """Tool to verify language persistence between application sessions."""
    
    def __init__(self):
        """Initialize the tester."""
        super().__init__()
        
        # Create QApplication instance for accessing QSettings
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("Scout")
        self.app.setOrganizationName("ScoutTeam")
        
        # Set up UI
        self.setWindowTitle("Language Persistence Tester")
        self.setGeometry(100, 100, 400, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add current settings label
        self.current_settings_label = QLabel("Current language setting: Unknown")
        layout.addWidget(self.current_settings_label)
        
        # Add language selector
        layout.addWidget(QLabel("Select language to save:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("System", "system")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("German", "de")
        layout.addWidget(self.language_combo)
        
        # Add buttons
        save_button = QPushButton("Save Language Setting")
        save_button.clicked.connect(self.save_language_setting)
        layout.addWidget(save_button)
        
        read_button = QPushButton("Read Current Setting")
        read_button.clicked.connect(self.read_language_setting)
        layout.addWidget(read_button)
        
        reset_button = QPushButton("Reset to System Default")
        reset_button.clicked.connect(self.reset_to_default)
        layout.addWidget(reset_button)
        
        # Initialize by reading current setting
        self.read_language_setting()
    
    def save_language_setting(self):
        """Save the selected language setting."""
        try:
            settings = QSettings()
            language = self.language_combo.currentData()
            
            # Save the setting
            settings.setValue("language/current", language)
            settings.sync()
            
            logger.info(f"Saved language setting: {language}")
            self.current_settings_label.setText(f"Current language setting: {language}")
        except Exception as e:
            logger.error(f"Error saving language setting: {e}")
            self.current_settings_label.setText(f"Error: {str(e)}")
    
    def read_language_setting(self):
        """Read the current language setting."""
        try:
            settings = QSettings()
            language = settings.value("language/current", "system")
            
            logger.info(f"Read language setting: {language}")
            self.current_settings_label.setText(f"Current language setting: {language}")
            
            # Update combo box to match current setting
            index = self.language_combo.findData(language)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
            
        except Exception as e:
            logger.error(f"Error reading language setting: {e}")
            self.current_settings_label.setText(f"Error: {str(e)}")
    
    def reset_to_default(self):
        """Reset language to system default."""
        try:
            settings = QSettings()
            settings.setValue("language/current", "system")
            settings.sync()
            
            logger.info("Reset language to system default")
            self.current_settings_label.setText("Current language setting: system")
            
            # Update combo box
            index = self.language_combo.findData("system")
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
                
        except Exception as e:
            logger.error(f"Error resetting language: {e}")
            self.current_settings_label.setText(f"Error: {str(e)}")
            

def main():
    """Main entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Scout")
    app.setOrganizationName("ScoutTeam")
    
    tester = LanguagePersistenceTester()
    tester.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 