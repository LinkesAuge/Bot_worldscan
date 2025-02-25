#!/usr/bin/env python3
"""
UI Components Translation Test

This script systematically tests UI components for proper translation and layout adaptability
when switching between languages. It creates various UI components, applies translations,
and checks for any layout issues or untranslated strings.
"""

import sys
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, QCheckBox, 
    QRadioButton, QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout, QGridLayout,
    QMessageBox, QDialog, QFileDialog, QScrollArea, QFrame, QSplitter,
    QStatusBar, QMenuBar, QMenu, QToolBar
)
from PyQt6.QtCore import Qt, QSize, QTranslator, QEvent, QLocale
from PyQt6.QtGui import QIcon, QPixmap, QFont, QAction

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define a simple translation dictionary for testing
TRANSLATIONS = {
    "en": {
        "UI Components Test": "UI Components Test",
        "Basic Components": "Basic Components",
        "Form Elements": "Form Elements",
        "Dialogs": "Dialogs",
        "Complex Layouts": "Complex Layouts",
        "Game State": "Game State",
        "Run Test": "Run Test",
        "OK": "OK",
        "Cancel": "Cancel",
        "Apply": "Apply",
        "Yes": "Yes",
        "No": "No",
        "Warning": "Warning",
        "Error": "Error",
        "Information": "Information",
        "Success": "Success",
        "Reset": "Reset",
        "Save": "Save",
        "Load": "Load",
        "Settings": "Settings",
        "Language": "Language",
        "English": "English",
        "German": "German",
        "System Default": "System Default",
        "Username:": "Username:",
        "Password:": "Password:",
        "Email:": "Email:",
        "Address:": "Address:",
        "Phone:": "Phone:",
        "This is a test label with potentially long text that must be properly wrapped and displayed.": 
            "This is a test label with potentially long text that must be properly wrapped and displayed.",
        "Are you sure you want to perform this action?":
            "Are you sure you want to perform this action?",
        "This is a test message box content.":
            "This is a test message box content.",
        "Resources:": "Resources:",
        "Gold:": "Gold:",
        "Wood:": "Wood:",
        "Stone:": "Stone:",
        "Food:": "Food:",
        "Iron:": "Iron:",
    },
    "de": {
        "UI Components Test": "UI-Komponententest",
        "Basic Components": "Grundlegende Komponenten",
        "Form Elements": "Formularelemente",
        "Dialogs": "Dialoge",
        "Complex Layouts": "Komplexe Layouts",
        "Game State": "Spielstatus",
        "Run Test": "Test ausführen",
        "OK": "OK",
        "Cancel": "Abbrechen",
        "Apply": "Anwenden",
        "Yes": "Ja",
        "No": "Nein",
        "Warning": "Warnung",
        "Error": "Fehler",
        "Information": "Information",
        "Success": "Erfolg",
        "Reset": "Zurücksetzen",
        "Save": "Speichern",
        "Load": "Laden",
        "Settings": "Einstellungen",
        "Language": "Sprache",
        "English": "Englisch",
        "German": "Deutsch",
        "System Default": "Systemstandard",
        "Username:": "Benutzername:",
        "Password:": "Passwort:",
        "Email:": "E-Mail:",
        "Address:": "Adresse:",
        "Phone:": "Telefon:",
        "This is a test label with potentially long text that must be properly wrapped and displayed.": 
            "Dies ist ein Testlabel mit potenziell langem Text, der ordnungsgemäß umgebrochen und angezeigt werden muss.",
        "Are you sure you want to perform this action?":
            "Sind Sie sicher, dass Sie diese Aktion ausführen möchten?",
        "This is a test message box content.":
            "Dies ist ein Testinhalt für eine Nachrichtenbox.",
        "Resources:": "Ressourcen:",
        "Gold:": "Gold:",
        "Wood:": "Holz:",
        "Stone:": "Stein:",
        "Food:": "Nahrung:",
        "Iron:": "Eisen:",
    }
}

class SimpleTranslator(QTranslator):
    """Simple translator for testing that uses a dictionary of translations."""
    
    def __init__(self, language: str):
        """
        Initialize translator with specified language.
        
        Args:
            language: Language code ("en" or "de")
        """
        super().__init__()
        self.language = language
        logger.info(f"Created SimpleTranslator for language: {language}")
    
    def translate(self, context: str, source_text: str, disambiguation: str = None, n: int = -1) -> str:
        """
        Translate a string.
        
        Args:
            context: Translation context
            source_text: Text to translate
            disambiguation: Disambiguation comment
            n: Number for plural form
            
        Returns:
            Translated text or empty string if no translation found
        """
        # Log translation request for debugging
        logger.debug(f"SimpleTranslator.translate called for: '{source_text}' (context: {context}, language: {self.language})")
        
        # Look up translation in dictionary
        if source_text in TRANSLATIONS.get(self.language, {}):
            translation = TRANSLATIONS[self.language][source_text]
            logger.debug(f"Translation found: '{translation}'")
            return translation
        
        # No translation found
        return ""

def tr(source_text: str, language: str = "en") -> str:
    """
    Translate a string using the simple translation dictionary.
    
    Args:
        source_text: Text to translate
        language: Target language
        
    Returns:
        Translated text or original text if no translation found
    """
    if language in TRANSLATIONS and source_text in TRANSLATIONS[language]:
        return TRANSLATIONS[language][source_text]
    return source_text

class ComponentTester(QWidget):
    """Tests a specific UI component for translation and layout issues."""
    
    def __init__(self, component_name: str, parent=None):
        """
        Initialize component tester.
        
        Args:
            component_name: Name of component being tested
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_name = component_name
        self.layout = QVBoxLayout(self)
        
        # Add component name label
        self.title_label = QLabel(f"<h3>{component_name}</h3>")
        self.layout.addWidget(self.title_label)
        
        # Add component container
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.layout.addWidget(self.container)
        
        # Add test result label
        self.result_label = QLabel("Not tested yet")
        self.layout.addWidget(self.result_label)
        
        # Set minimum size
        self.setMinimumSize(400, 300)
    
    def setup_component(self, language: str) -> None:
        """
        Set up the component for testing in the specified language.
        
        Args:
            language: Language to use for the component
        """
        # Clear container
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Override in subclasses
        pass
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """
        Test the component for translation and layout issues.
        
        Args:
            language: Language to test with
            
        Returns:
            (success, message) tuple
        """
        # Set up component in current language
        self.setup_component(language)
        
        # Use the title label to indicate current language
        self.title_label.setText(f"<h3>{self.component_name} ({language})</h3>")
        
        # Override in subclasses to perform specific tests
        return True, "Test passed"
    
    def set_result(self, success: bool, message: str) -> None:
        """
        Set the test result.
        
        Args:
            success: Whether the test passed
            message: Result message
        """
        if success:
            self.result_label.setText(f"✅ {message}")
            self.result_label.setStyleSheet("color: green;")
        else:
            self.result_label.setText(f"❌ {message}")
            self.result_label.setStyleSheet("color: red;")


class LabelTester(ComponentTester):
    """Tests label components for translation and layout issues."""
    
    def __init__(self, parent=None):
        super().__init__("Label Test", parent)
    
    def setup_component(self, language: str) -> None:
        """Set up labels with various text styles."""
        super().setup_component(language)
        
        # Standard label
        standard_label = QLabel(tr("This is a test label with potentially long text that must be properly wrapped and displayed.", language))
        standard_label.setWordWrap(True)
        self.container_layout.addWidget(standard_label)
        
        # Bold label
        bold_label = QLabel(f"<b>{tr('Settings', language)}</b>")
        self.container_layout.addWidget(bold_label)
        
        # Labels with different font sizes
        small_label = QLabel(tr("OK", language))
        small_label.setStyleSheet("font-size: 8pt;")
        self.container_layout.addWidget(small_label)
        
        large_label = QLabel(tr("Warning", language))
        large_label.setStyleSheet("font-size: 14pt; color: red;")
        self.container_layout.addWidget(large_label)
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """Test labels for proper translation and layout."""
        super().test_component(language)
        
        # Check if labels are set up correctly
        labels = self.findChildren(QLabel)
        if len(labels) < 5:  # Title label + 4 test labels
            return False, "Not all labels were created"
        
        # In a real test, we would check for overflow, truncation, etc.
        # Here we just log the information
        for label in labels:
            if label != self.title_label and label != self.result_label:
                text = label.text()
                logger.info(f"Label text: '{text}', width: {label.width()}, contains HTML: {'<' in text}")
        
        return True, f"Labels tested in {language}"


class ButtonTester(ComponentTester):
    """Tests button components for translation and layout issues."""
    
    def __init__(self, parent=None):
        super().__init__("Button Test", parent)
    
    def setup_component(self, language: str) -> None:
        """Set up buttons with various text lengths."""
        super().setup_component(language)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Standard buttons
        ok_button = QPushButton(tr("OK", language))
        cancel_button = QPushButton(tr("Cancel", language))
        apply_button = QPushButton(tr("Apply", language))
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)
        
        self.container_layout.addLayout(button_layout)
        
        # Button with longer text
        long_button = QPushButton(tr("This is a test label with potentially long text that must be properly wrapped and displayed.", language))
        self.container_layout.addWidget(long_button)
        
        # Store initial button widths for testing
        self.button_widths = {
            "ok": ok_button.width(),
            "cancel": cancel_button.width(),
            "apply": apply_button.width(),
            "long": long_button.width()
        }
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """Test buttons for proper translation and layout."""
        super().test_component(language)
        
        # Check if buttons are set up correctly
        buttons = self.findChildren(QPushButton)
        if len(buttons) < 4:
            return False, "Not all buttons were created"
        
        # In a real test, we would check for overflow, misalignment, etc.
        # Here we just log the information
        for button in buttons:
            text = button.text()
            logger.info(f"Button text: '{text}', width: {button.width()}")
        
        return True, f"Buttons tested in {language}"


class FormTester(ComponentTester):
    """Tests form elements for translation and layout issues."""
    
    def __init__(self, parent=None):
        super().__init__("Form Test", parent)
    
    def setup_component(self, language: str) -> None:
        """Set up a form with various input fields."""
        super().setup_component(language)
        
        # Create form layout
        form_layout = QFormLayout()
        
        # Add form fields
        username_label = QLabel(tr("Username:", language))
        username_field = QLineEdit()
        form_layout.addRow(username_label, username_field)
        
        password_label = QLabel(tr("Password:", language))
        password_field = QLineEdit()
        password_field.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(password_label, password_field)
        
        email_label = QLabel(tr("Email:", language))
        email_field = QLineEdit()
        form_layout.addRow(email_label, email_field)
        
        # Add dropdown
        language_label = QLabel(tr("Language", language))
        language_combo = QComboBox()
        language_combo.addItem(tr("English", language))
        language_combo.addItem(tr("German", language))
        language_combo.addItem(tr("System Default", language))
        form_layout.addRow(language_label, language_combo)
        
        # Add to container
        self.container_layout.addLayout(form_layout)
        
        # Add submit button
        submit_button = QPushButton(tr("Save", language))
        self.container_layout.addWidget(submit_button)
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """Test form elements for proper translation and layout."""
        super().test_component(language)
        
        # Check if form elements are set up correctly
        labels = self.findChildren(QLabel)
        line_edits = self.findChildren(QLineEdit)
        combos = self.findChildren(QComboBox)
        
        if len(labels) < 5 or len(line_edits) < 3 or len(combos) < 1:
            return False, "Not all form elements were created"
        
        # In a real test, we would check for alignment, proper label widths, etc.
        # Here we just log the information
        for label in labels:
            if label != self.title_label and label != self.result_label:
                logger.info(f"Form label: '{label.text()}', width: {label.width()}")
        
        return True, f"Form elements tested in {language}"


class DialogTester(ComponentTester):
    """Tests dialog components for translation and layout issues."""
    
    def __init__(self, parent=None):
        super().__init__("Dialog Test", parent)
    
    def setup_component(self, language: str) -> None:
        """Set up buttons to trigger different dialogs."""
        super().setup_component(language)
        
        # Create button layout
        button_layout = QVBoxLayout()
        
        # Info dialog button
        info_button = QPushButton(tr("Information", language))
        info_button.clicked.connect(lambda: self.show_info_dialog(language))
        button_layout.addWidget(info_button)
        
        # Warning dialog button
        warning_button = QPushButton(tr("Warning", language))
        warning_button.clicked.connect(lambda: self.show_warning_dialog(language))
        button_layout.addWidget(warning_button)
        
        # Error dialog button
        error_button = QPushButton(tr("Error", language))
        error_button.clicked.connect(lambda: self.show_error_dialog(language))
        button_layout.addWidget(error_button)
        
        # Question dialog button
        question_button = QPushButton(tr("Question", language))
        question_button.clicked.connect(lambda: self.show_question_dialog(language))
        button_layout.addWidget(question_button)
        
        # Add layout to container
        self.container_layout.addLayout(button_layout)
        
        # Save current language for dialogs
        self.current_language = language
    
    def show_info_dialog(self, language: str) -> None:
        """Show information dialog."""
        QMessageBox.information(
            self,
            tr("Information", language),
            tr("This is a test message box content.", language)
        )
    
    def show_warning_dialog(self, language: str) -> None:
        """Show warning dialog."""
        QMessageBox.warning(
            self,
            tr("Warning", language),
            tr("This is a test message box content.", language)
        )
    
    def show_error_dialog(self, language: str) -> None:
        """Show error dialog."""
        QMessageBox.critical(
            self,
            tr("Error", language),
            tr("This is a test message box content.", language)
        )
    
    def show_question_dialog(self, language: str) -> None:
        """Show question dialog."""
        QMessageBox.question(
            self,
            tr("Question", language),
            tr("Are you sure you want to perform this action?", language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """Test dialog components for proper translation and layout."""
        super().test_component(language)
        
        # Check if dialog buttons are set up correctly
        buttons = self.findChildren(QPushButton)
        if len(buttons) < 4:
            return False, "Not all dialog buttons were created"
        
        # In a real test, we would programmatically trigger and check the dialogs
        # Here we just log that manual testing is required
        logger.info(f"Dialog buttons created for {language}")
        
        return True, f"Dialog buttons created (click to test) in {language}"


class GameStateTester(ComponentTester):
    """Tests game state components for translation and layout issues."""
    
    def __init__(self, parent=None):
        super().__init__("Game State Test", parent)
    
    def setup_component(self, language: str) -> None:
        """Set up game state components."""
        super().setup_component(language)
        
        # Create resources group
        resources_group = QGroupBox(tr("Resources:", language))
        resources_layout = QGridLayout(resources_group)
        
        # Add resource labels and values
        resources = [
            ("Gold:", "1,000"),
            ("Wood:", "500"),
            ("Stone:", "250"),
            ("Food:", "750"),
            ("Iron:", "100"),
        ]
        
        for i, (resource, value) in enumerate(resources):
            label = QLabel(tr(resource, language))
            value_label = QLabel(value)
            resources_layout.addWidget(label, i, 0)
            resources_layout.addWidget(value_label, i, 1)
        
        self.container_layout.addWidget(resources_group)
    
    def test_component(self, language: str) -> Tuple[bool, str]:
        """Test game state components for proper translation and layout."""
        super().test_component(language)
        
        # Check if components are set up correctly
        group_boxes = self.findChildren(QGroupBox)
        labels = self.findChildren(QLabel)
        
        if len(group_boxes) < 1 or len(labels) < 10:
            return False, "Not all game state components were created"
        
        # In a real test, we would check for alignment, proper formatting, etc.
        # Here we just log the information
        for group_box in group_boxes:
            logger.info(f"Group box title: '{group_box.title()}', width: {group_box.width()}")
        
        return True, f"Game state components tested in {language}"


class UIComponentTester(QMainWindow):
    """Main window for testing UI components with language switching."""
    
    def __init__(self):
        """Initialize the UI components tester."""
        super().__init__()
        
        # Set up window
        self.setWindowTitle("UI Components Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create language selector
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Language:"))
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("German", "de")
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        
        main_layout.addLayout(language_layout)
        
        # Create tab widget for different component tests
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Add component testers
        self.label_tester = LabelTester()
        self.tabs.addTab(self.label_tester, "Label Test")
        
        self.button_tester = ButtonTester()
        self.tabs.addTab(self.button_tester, "Button Test")
        
        self.form_tester = FormTester()
        self.tabs.addTab(self.form_tester, "Form Test")
        
        self.dialog_tester = DialogTester()
        self.tabs.addTab(self.dialog_tester, "Dialog Test")
        
        self.game_state_tester = GameStateTester()
        self.tabs.addTab(self.game_state_tester, "Game State Test")
        
        # Add run test button
        run_button = QPushButton("Run All Tests")
        run_button.clicked.connect(self.run_all_tests)
        main_layout.addWidget(run_button)
        
        # Set up translators
        self.en_translator = SimpleTranslator("en")
        self.de_translator = SimpleTranslator("de")
        
        # Set initial language to English
        self.current_language = "en"
        self._apply_language("en")
    
    def on_language_changed(self, index: int) -> None:
        """
        Handle language change.
        
        Args:
            index: Selected language index
        """
        language = self.language_combo.itemData(index)
        logger.info(f"Switching language to: {language}")
        
        # Apply language change
        self._apply_language(language)
        
        # Update all component tests
        self.update_all_components()
    
    def _apply_language(self, language: str) -> None:
        """
        Apply a language to the application.
        
        Args:
            language: Language code to apply
        """
        # Store current language
        self.current_language = language
        
        # Get application instance
        app = QApplication.instance()
        
        # Remove existing translators
        app.removeTranslator(self.en_translator)
        app.removeTranslator(self.de_translator)
        
        # Install appropriate translator
        if language == "de":
            app.installTranslator(self.de_translator)
            logger.info("Installed German translator")
        else:
            app.installTranslator(self.en_translator)
            logger.info("Installed English translator")
        
        # Update window title
        self.setWindowTitle(tr("UI Components Test", language))
        
        # Update tab titles
        self.tabs.setTabText(0, tr("Basic Components", language))
        self.tabs.setTabText(1, tr("Form Elements", language))
        self.tabs.setTabText(2, tr("Dialogs", language))
        self.tabs.setTabText(3, tr("Complex Layouts", language))
        self.tabs.setTabText(4, tr("Game State", language))
    
    def update_all_components(self) -> None:
        """Update all component tests for the current language."""
        # Run each component test with current language
        self.label_tester.test_component(self.current_language)
        self.button_tester.test_component(self.current_language)
        self.form_tester.test_component(self.current_language)
        self.dialog_tester.test_component(self.current_language)
        self.game_state_tester.test_component(self.current_language)
    
    def run_all_tests(self) -> None:
        """Run all component tests in both languages."""
        logger.info("Running all tests")
        
        # Test English
        self.language_combo.setCurrentIndex(0)
        self.update_all_components()
        time.sleep(0.5)  # Allow UI to update
        
        # Test German
        self.language_combo.setCurrentIndex(1)
        self.update_all_components()
        
        logger.info("All tests completed")
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        logger.info("UI Components Test closing")
        super().closeEvent(event)


def main():
    """Main entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Scout")
    
    tester = UIComponentTester()
    tester.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 