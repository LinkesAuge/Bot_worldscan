#!/usr/bin/env python3
"""
Visual Language Test

This script provides a visual testing tool for verifying translations and layout
adaptability across different languages in the Scout application.
"""

import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ensure the scout package is in the Python path
script_dir = Path(__file__).absolute().parent
if script_dir not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QLabel, QPushButton, QComboBox, QTabWidget, QFormLayout, 
        QLineEdit, QGroupBox, QCheckBox, QSpinBox, QSlider, 
        QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
        QSplitter, QScrollArea, QSizePolicy, QDialog, QDialogButtonBox
    )
    from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QTranslator, QLocale, QCoreApplication
    from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap
    
    # If the language_manager isn't working well, we'll use our direct implementation
    # We'll still try to import the tr function for displaying translated text
    try:
        from scout.ui.utils.language_manager import tr
    except ImportError:
        # Fallback tr function
        def tr(source_text, context=None, n=-1):
            app = QCoreApplication.instance()
            if app:
                if context:
                    return app.translate(context, source_text, None, n)
                else:
                    return app.translate("", source_text, None, n)
            return source_text
    
    from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you have installed all required dependencies.")
    sys.exit(1)

# Define language enum
class Language:
    SYSTEM = "system"
    ENGLISH = "en"
    GERMAN = "de"

# Simple translation dictionary for demonstration
DEMO_TRANSLATIONS = {
    "en": {
        # Tab titles
        "Basic Components": "Basic Components",
        "Form Elements": "Form Elements",
        "Dialogs": "Dialogs",
        "Complex Layouts": "Complex Layouts",
        "Game State": "Game State",
        
        # Labels and buttons
        "Select Language:": "Select Language:",
        "Test All Components": "Test All Components",
        "Test Results": "Test Results",
        "Current Language: English": "Current Language: English",
        "Current Language: German": "Current Language: German",
        "Current Language: System Default": "Current Language: System Default",
        
        # Basic components tab
        "Test Label": "Test Label",
        "Test Button": "Test Button",
        "Test Combobox": "Test Combobox",
        "Test Checkbox": "Test Checkbox",
        "This is a test label with potentially long text that needs to be properly wrapped and displayed": 
            "This is a test label with potentially long text that needs to be properly wrapped and displayed",
        "Save Configuration": "Save Configuration",
        "Highlight Layout Issues": "Highlight Layout Issues",
        "Show Component Bounds": "Show Component Bounds",
        
        # Form tab
        "Test Form": "Test Form",
        "Test Table": "Test Table",
        "Test Grid": "Test Grid",
        "First Name:": "First Name:",
        "Last Name:": "Last Name:",
        "Email:": "Email:",
        "Password:": "Password:",
        "Confirm Password:": "Confirm Password:",
        "I agree to the terms": "I agree to the terms",
        
        # Dialog tab
        "Test Message Box": "Test Message Box",
        "Test Export Dialog": "Test Export Dialog",
        "Test File Dialog": "Test File Dialog",
        
        # Complex layouts tab
        "Test Settings Panel": "Test Settings Panel",
        "Test Detection Controls": "Test Detection Controls",
        "Test Automation Controls": "Test Automation Controls",
        
        # Game state tab
        "Test Resource Panel": "Test Resource Panel",
        "Test Map Controls": "Test Map Controls",
        "Test Army Panel": "Test Army Panel",
        
        # Common UI elements
        "Cancel": "Cancel",
        "Apply": "Apply",
        "OK": "OK",
        "Yes": "Yes", 
        "No": "No",
        "&Yes": "&Yes",
        "&No": "&No",
        "Save": "Save",
        "Open": "Open",
        "Delete": "Delete",
        "Settings": "Settings",
        "Language": "Language",
        "Help": "Help",
        "About": "About",
        "Quit": "Quit",
        "Application": "Application",
        "Detection": "Detection",
        "Automation": "Automation",
        "Resources": "Resources",
        "Map": "Map",
        "Army": "Army",
        "Buildings": "Buildings",
        "Action": "Action",
        "Description": "Description",
        "Keyboard Shortcuts": "Keyboard Shortcuts",
        
        # UI labels
        "Settings Panel": "Settings Panel",
        "Detection Controls": "Detection Controls",
        "Automation Controls": "Automation Controls",
        "Resource Panel": "Resource Panel", 
        "Map Controls": "Map Controls",
        "Army Panel": "Army Panel",
        
        # Additional form fields
        "Username:": "Username:",
        "Email Address:": "Email Address:",
        "Phone Number:": "Phone Number:",
        "Remember Login:": "Remember Login:",
        "Account Type:": "Account Type:",
        "Administrator": "Administrator",
        "User": "User",
        "Guest": "Guest",
        "Name:": "Name:",
        "Address:": "Address:",
        "City:": "City:",
        "State/Province:": "State/Province:",
        "Postal Code:": "Postal Code:",
        "Name": "Name",
        "Type": "Type",
        
        # Resource labels
        "Gold:": "Gold:",
        "Food:": "Food:",
        "Wood:": "Wood:",
        "Stone:": "Stone:",
        "Iron:": "Iron:",
        
        # Detection settings
        "Detection Settings": "Detection Settings",
        "Confidence Threshold:": "Confidence Threshold:",
        "Maximum Matches:": "Maximum Matches:",
        "Detection Strategy:": "Detection Strategy:",
        "Use GPU Acceleration:": "Use GPU Acceleration:",
        "Template Matching": "Template Matching",
        "Feature Matching": "Feature Matching",
        "OCR": "OCR",
        "YOLO": "YOLO",
        
        # Dialog items
        "Confirmation": "Confirmation",
        "Are you sure you want to perform this action?": "Are you sure you want to perform this action?",
        "Settings Export": "Settings Export",
        "Select export options:": "Select export options:",
        "Include system information": "Include system information",
        "Include user preferences": "Include user preferences",
        "Include detection settings": "Include detection settings",
        "Include automation sequences": "Include automation sequences",
        "Open Configuration File": "Open Configuration File",
        "Configuration Files": "Configuration Files",
        "All Files": "All Files",
        
        # Language settings
        "System Default": "System Default",
        "English": "English",
        "German": "German",
        "French": "French",
        "Spanish": "Spanish",
        "Italian": "Italian",
        
        # Advanced options
        "Enable advanced options for detection and processing": "Enable advanced options for detection and processing",
        
        # Detection controls
        "Run Detection": "Run Detection",
        "Stop": "Stop",
        "Select Template:": "Select Template:",
        "Button": "Button",
        "Dialog": "Dialog", 
        "Window": "Window",
        "Resource Icon": "Resource Icon",
        
        # Sequence controls
        "Sequence:": "Sequence:",
        "Resource Collection": "Resource Collection",
        "Building Upgrade": "Building Upgrade",
        "Troop Training": "Troop Training",
        "Map Exploration": "Map Exploration",
        "New": "New",
        "Run": "Run",
        "Loop:": "Loop:",
        "Iterations:": "Iterations:",
        
        # Map controls
        "Zoom In": "Zoom In",
        "Zoom Out": "Zoom Out",
        "Reset View": "Reset View",
        "Filter:": "Filter:",
        "All": "All",
        "Enemies": "Enemies",
        "Allies": "Allies",
        "Points of Interest": "Points of Interest",
        
        # Army units
        "Army Units": "Army Units",
        "Infantry:": "Infantry:",
        "Cavalry:": "Cavalry:",
        "Archers:": "Archers:",
        "Siege Engines:": "Siege Engines:",
        "Special Units:": "Special Units:",
        
        # Table data
        "Coffee": "Coffee",
        "Tea": "Tea",
        "Water": "Water",
        "Orange Juice": "Orange Juice",
        "Apple": "Apple",
        "Fruit": "Fruit",
        "Beverage": "Beverage",
        "Hot drink made from roasted coffee beans": "Hot drink made from roasted coffee beans",
        "Hot drink made by infusing tea leaves in water": "Hot drink made by infusing tea leaves in water",
        "Clear, colorless, odorless liquid": "Clear, colorless, odorless liquid",
        "Juice from oranges": "Juice from oranges",
        "Round fruit from an apple tree": "Round fruit from an apple tree",
    },
    "de": {
        # Tab titles
        "Basic Components": "Grundlegende Komponenten",
        "Form Elements": "Formularelemente",
        "Dialogs": "Dialoge",
        "Complex Layouts": "Komplexe Layouts",
        "Game State": "Spielstatus",
        
        # Labels and buttons
        "Select Language:": "Sprache auswählen:",
        "Test All Components": "Alle Komponenten testen",
        "Test Results": "Testergebnisse",
        "Current Language: English": "Aktuelle Sprache: Englisch",
        "Current Language: German": "Aktuelle Sprache: Deutsch",
        "Current Language: System Default": "Aktuelle Sprache: Systemstandard",
        
        # Basic components tab
        "Test Label": "Label testen",
        "Test Button": "Button testen",
        "Test Combobox": "Auswahlfeld testen",
        "Test Checkbox": "Kontrollkästchen testen",
        "This is a test label with potentially long text that needs to be properly wrapped and displayed": 
            "Dies ist ein Testlabel mit potenziell langem Text, der ordnungsgemäß umgebrochen und angezeigt werden muss",
        "Save Configuration": "Konfiguration speichern",
        "Highlight Layout Issues": "Layout-Probleme hervorheben",
        "Show Component Bounds": "Komponentengrenzen anzeigen",
        
        # Form tab
        "Test Form": "Formular testen",
        "Test Table": "Tabelle testen",
        "Test Grid": "Gitter testen",
        "First Name:": "Vorname:",
        "Last Name:": "Nachname:",
        "Email:": "E-Mail:",
        "Password:": "Passwort:",
        "Confirm Password:": "Passwort bestätigen:",
        "I agree to the terms": "Ich stimme den Bedingungen zu",
        
        # Dialog tab
        "Test Message Box": "Meldungsfeld testen",
        "Test Export Dialog": "Exportdialog testen",
        "Test File Dialog": "Dateiauswahldialog testen",
        
        # Complex layouts tab
        "Test Settings Panel": "Einstellungspanel testen",
        "Test Detection Controls": "Erkennungssteuerung testen",
        "Test Automation Controls": "Automatisierungssteuerung testen",
        
        # Game state tab
        "Test Resource Panel": "Ressourcenpanel testen",
        "Test Map Controls": "Kartensteuerung testen",
        "Test Army Panel": "Armeepanel testen",
        
        # Common UI elements
        "Cancel": "Abbrechen",
        "Apply": "Anwenden",
        "OK": "OK",
        "Yes": "Ja",
        "No": "Nein",
        "&Yes": "&Ja",
        "&No": "&Nein",
        "Save": "Speichern",
        "Open": "Öffnen",
        "Delete": "Löschen",
        "Settings": "Einstellungen",
        "Language": "Sprache",
        "Help": "Hilfe",
        "About": "Über",
        "Quit": "Beenden",
        "Application": "Anwendung",
        "Detection": "Erkennung",
        "Automation": "Automatisierung",
        "Resources": "Ressourcen",
        "Map": "Karte",
        "Army": "Armee",
        "Buildings": "Gebäude",
        "Action": "Aktion",
        "Description": "Beschreibung",
        "Keyboard Shortcuts": "Tastaturkürzel",
        
        # UI labels
        "Settings Panel": "Einstellungsbereich",
        "Detection Controls": "Erkennungssteuerung",
        "Automation Controls": "Automatisierungssteuerung",
        "Resource Panel": "Ressourcenbereich",
        "Map Controls": "Kartensteuerung",
        "Army Panel": "Armeebereich",
        
        # Additional form fields
        "Username:": "Benutzername:",
        "Email Address:": "E-Mail-Adresse:",
        "Phone Number:": "Telefonnummer:",
        "Remember Login:": "Anmeldedaten speichern:",
        "Account Type:": "Kontotyp:",
        "Administrator": "Administrator",
        "User": "Benutzer",
        "Guest": "Gast",
        "Name:": "Name:",
        "Address:": "Adresse:",
        "City:": "Stadt:",
        "State/Province:": "Bundesland/Provinz:",
        "Postal Code:": "Postleitzahl:",
        "Name": "Name",
        "Type": "Typ",
        
        # Resource labels
        "Gold:": "Gold:",
        "Food:": "Nahrung:",
        "Wood:": "Holz:",
        "Stone:": "Stein:",
        "Iron:": "Eisen:",
        
        # Detection settings
        "Detection Settings": "Erkennungseinstellungen",
        "Confidence Threshold:": "Vertrauensschwelle:",
        "Maximum Matches:": "Maximale Übereinstimmungen:",
        "Detection Strategy:": "Erkennungsstrategie:",
        "Use GPU Acceleration:": "GPU-Beschleunigung verwenden:",
        "Template Matching": "Vorlagenabgleich",
        "Feature Matching": "Merkmalsabgleich",
        "OCR": "OCR",
        "YOLO": "YOLO",
        
        # Dialog items
        "Confirmation": "Bestätigung",
        "Are you sure you want to perform this action?": "Sind Sie sicher, dass Sie diese Aktion ausführen möchten?",
        "Settings Export": "Einstellungen exportieren",
        "Select export options:": "Exportoptionen auswählen:",
        "Include system information": "Systeminformationen einbeziehen",
        "Include user preferences": "Benutzereinstellungen einbeziehen",
        "Include detection settings": "Erkennungseinstellungen einbeziehen",
        "Include automation sequences": "Automatisierungssequenzen einbeziehen",
        "Open Configuration File": "Konfigurationsdatei öffnen",
        "Configuration Files": "Konfigurationsdateien",
        "All Files": "Alle Dateien",
        
        # Language settings
        "System Default": "Systemstandard",
        "English": "Englisch",
        "German": "Deutsch",
        "French": "Französisch",
        "Spanish": "Spanisch",
        "Italian": "Italienisch",
        
        # Advanced options
        "Enable advanced options for detection and processing": "Erweiterte Optionen für Erkennung und Verarbeitung aktivieren",
        
        # Detection controls
        "Run Detection": "Erkennung ausführen",
        "Stop": "Stoppen",
        "Select Template:": "Vorlage auswählen:",
        "Button": "Schaltfläche",
        "Dialog": "Dialog", 
        "Window": "Fenster",
        "Resource Icon": "Ressourcensymbol",
        
        # Sequence controls
        "Sequence:": "Sequenz:",
        "Resource Collection": "Ressourcensammlung",
        "Building Upgrade": "Gebäudeausbau",
        "Troop Training": "Truppenausbildung",
        "Map Exploration": "Kartenexploration",
        "New": "Neu",
        "Run": "Ausführen",
        "Loop:": "Schleife:",
        "Iterations:": "Wiederholungen:",
        
        # Map controls
        "Zoom In": "Vergrößern",
        "Zoom Out": "Verkleinern",
        "Reset View": "Ansicht zurücksetzen",
        "Filter:": "Filter:",
        "All": "Alle",
        "Enemies": "Feinde",
        "Allies": "Verbündete",
        "Points of Interest": "Sehenswürdigkeiten",
        
        # Army units
        "Army Units": "Armeeeinheiten",
        "Infantry:": "Infanterie:",
        "Cavalry:": "Kavallerie:",
        "Archers:": "Bogenschützen:",
        "Siege Engines:": "Belagerungsmaschinen:",
        "Special Units:": "Spezialeinheiten:",
        
        # Table data
        "Coffee": "Kaffee",
        "Tea": "Tee",
        "Water": "Wasser",
        "Orange Juice": "Orangensaft",
        "Apple": "Apfel",
        "Fruit": "Frucht",
        "Beverage": "Getränk",
        "Hot drink made from roasted coffee beans": "Heißgetränk aus gerösteten Kaffeebohnen",
        "Hot drink made by infusing tea leaves in water": "Heißgetränk aus in Wasser aufgegossenen Teeblättern",
        "Clear, colorless, odorless liquid": "Klare, farblose, geruchlose Flüssigkeit",
        "Juice from oranges": "Saft aus Orangen",
        "Round fruit from an apple tree": "Runde Frucht vom Apfelbaum",
    }
}

# Override tr function for demonstration
def demo_tr(source_text, context=None, n=-1):
    """Demo translation function that uses our dictionary."""
    app = QApplication.instance()
    current_language = getattr(app, 'demo_language', Language.ENGLISH)
    
    logger.debug(f"demo_tr called for: '{source_text}', current language: {current_language}")
    
    # If it's English or not in our dictionary, return the source text
    if current_language == Language.ENGLISH:
        return source_text
    
    # Try to find a translation
    if current_language in DEMO_TRANSLATIONS and source_text in DEMO_TRANSLATIONS[current_language]:
        translated = DEMO_TRANSLATIONS[current_language][source_text]
        logger.debug(f"Translation found: '{translated}'")
        return translated
    
    # Fallback to the original text
    logger.debug(f"No translation found for: '{source_text}'")
    return source_text

# Try to use the language_manager's tr function, but fall back to our demo one if needed
try:
    from scout.ui.utils.language_manager import tr
except ImportError:
    # Use our demo translation function
    tr = demo_tr

class DemoTranslator(QTranslator):
    """Custom translator that uses our dictionary-based translations."""
    
    def __init__(self, language_code):
        super().__init__()
        self.language_code = language_code
        logger.info(f"Created DemoTranslator for language: {language_code}")
    
    def translate(self, context, source_text, disambiguation=None, n=-1):
        """
        Override the translate method to use our dictionary.
        
        This is called by Qt when it needs to translate a string.
        """
        logger.debug(f"DemoTranslator.translate called for: '{source_text}' (context: {context}, language: {self.language_code})")
        
        # If language is English, return the original text
        if self.language_code == Language.ENGLISH:
            return source_text
        
        # Check if we have a translation for this text
        if self.language_code in DEMO_TRANSLATIONS and source_text in DEMO_TRANSLATIONS[self.language_code]:
            translated = DEMO_TRANSLATIONS[self.language_code][source_text]
            logger.debug(f"Translation found: '{translated}'")
            return translated
        
        # Log missing translations for debugging
        if self.language_code != Language.ENGLISH:
            logger.debug(f"No translation found for: '{source_text}'")
        
        # Return the original if no translation is found
        return source_text

class ComponentVisualizer(QWidget):
    """Widget for visualizing UI components with translation information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        
        # Default component
        self.component = None
        
        # Create layout
        self.layout = QVBoxLayout(self)
        
        # Display options
        options_layout = QHBoxLayout()
        
        self.highlight_issues = QCheckBox("Highlight Layout Issues")
        self.highlight_issues.setChecked(True)
        self.highlight_issues.stateChanged.connect(self.update)
        options_layout.addWidget(self.highlight_issues)
        
        self.show_bounds = QCheckBox("Show Component Bounds")
        self.show_bounds.setChecked(True)
        self.show_bounds.stateChanged.connect(self.update)
        options_layout.addWidget(self.show_bounds)
        
        self.layout.addLayout(options_layout)
        
        # Component container
        self.component_container = QWidget()
        self.component_container.setMinimumHeight(150)
        self.component_container.setAutoFillBackground(True)
        self.component_container.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        
        self.component_layout = QVBoxLayout(self.component_container)
        self.component_layout.setContentsMargins(10, 10, 10, 10)
        
        self.layout.addWidget(self.component_container)
        
        # Info text area
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.layout.addWidget(self.info_text)
    
    def set_component(self, component, title="Component Test", description=""):
        """Set the component to visualize."""
        # Clear previous component
        for i in reversed(range(self.component_layout.count())): 
            item = self.component_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # Add new component
        self.component = component
        self.component_layout.addWidget(component)
        
        # Update component info
        info = f"<h3>{title}</h3>"
        if description:
            info += f"<p>{description}</p>"
        
        # Add component size info
        size = component.size()
        info += f"<p>Size: {size.width()} x {size.height()} pixels</p>"
        
        self.info_text.setHtml(info)
        
        # Force update
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event to visualize component bounds and layout issues."""
        super().paintEvent(event)
        
        if not self.component:
            return
            
        if not self.show_bounds.isChecked() and not self.highlight_issues.isChecked():
            return
            
        painter = QPainter(self)
        
        # Get component geometry in our coordinates
        component_rect = self.component.geometry()
        component_rect = self.component_container.mapToParent(component_rect.topLeft())
        component_rect = QRect(
            component_rect.x(), 
            component_rect.y(), 
            self.component.width(), 
            self.component.height()
        )
        
        # Draw component bounds
        if self.show_bounds.isChecked():
            painter.setPen(QPen(QColor(0, 0, 255), 2, Qt.PenStyle.DashLine))
            painter.drawRect(component_rect)
        
        # Highlight layout issues
        if self.highlight_issues.isChecked():
            # Simple layout issue detection based on size
            if component_rect.width() > self.component_container.width() - 20:
                # Draw red line to indicate width issue
                painter.setPen(QPen(QColor(255, 0, 0), 3))
                painter.drawLine(
                    component_rect.left(), component_rect.bottom() + 5,
                    component_rect.right(), component_rect.bottom() + 5
                )
                
                # Add warning text
                painter.setFont(QFont("Arial", 10))
                painter.drawText(
                    component_rect.left(), component_rect.bottom() + 20,
                    "Width exceeds container bounds"
                )
            
            if component_rect.height() > self.component_container.height() - 20:
                # Draw red line to indicate height issue
                painter.setPen(QPen(QColor(255, 0, 0), 3))
                painter.drawLine(
                    component_rect.right() + 5, component_rect.top(),
                    component_rect.right() + 5, component_rect.bottom()
                )
                
                # Add warning text
                painter.setFont(QFont("Arial", 10))
                painter.drawText(
                    component_rect.right() + 10, component_rect.top() + 20,
                    "Height exceeds container bounds"
                )


class VisualLanguageTest(QMainWindow):
    """Main window for the visual language testing tool."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scout Visual Language Test")
        self.setGeometry(100, 100, 1000, 800)
        
        # Set up our demo translators
        self.translators = {
            Language.ENGLISH: DemoTranslator(Language.ENGLISH),
            Language.GERMAN: DemoTranslator(Language.GERMAN),
        }
        self.current_language = Language.ENGLISH
        
        # For demo translations
        app = QApplication.instance()
        app.demo_language = self.current_language
        
        # Install the English translator by default
        app.installTranslator(self.translators[Language.ENGLISH])
        
        # No need to load translators from files anymore
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Select Language:"))
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("German", "de")
        self.lang_combo.addItem("System Default", "system")
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.lang_combo)
        
        # Current language info
        self.lang_info = QLabel("Current Language: English")
        lang_layout.addWidget(self.lang_info)
        
        lang_layout.addStretch()
        
        # Test all button
        test_all_button = QPushButton("Test All Components")
        test_all_button.clicked.connect(self.run_all_tests)
        lang_layout.addWidget(test_all_button)
        
        main_layout.addLayout(lang_layout)
        
        # Create tab widget for testing different component types
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Add tabs for different component types
        self.setup_basic_components_tab()
        self.setup_form_components_tab()
        self.setup_dialogs_tab()
        self.setup_complex_layouts_tab()
        self.setup_game_state_tab()
        
        # Results panel
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        main_layout.addWidget(results_group)
        
        # Set initial language
        self.update_language_info()
        
        # Set initial results text
        self.results_text.setHtml(
            "<h2>Language Test Results</h2>"
            "<p>Switch between languages to test translation and layout adaptability.</p>"
            "<p>Use the visualizer to check for layout issues with different components.</p>"
        )
    
    def setup_basic_components_tab(self):
        """Set up the basic components test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Component visualizer
        visualizer = ComponentVisualizer()
        layout.addWidget(visualizer)
        
        # Components to test
        components_layout = QHBoxLayout()
        
        # Basic label button
        test_label_btn = QPushButton("Test Label")
        test_label_btn.clicked.connect(lambda: self.test_label_component(visualizer))
        components_layout.addWidget(test_label_btn)
        
        # Button with text
        test_button_btn = QPushButton("Test Button")
        test_button_btn.clicked.connect(lambda: self.test_button_component(visualizer))
        components_layout.addWidget(test_button_btn)
        
        # Combo box
        test_combo_btn = QPushButton("Test ComboBox")
        test_combo_btn.clicked.connect(lambda: self.test_combo_component(visualizer))
        components_layout.addWidget(test_combo_btn)
        
        # Checkbox
        test_checkbox_btn = QPushButton("Test Checkbox")
        test_checkbox_btn.clicked.connect(lambda: self.test_checkbox_component(visualizer))
        components_layout.addWidget(test_checkbox_btn)
        
        layout.addLayout(components_layout)
        
        self.tabs.addTab(tab, "Basic Components")
    
    def setup_form_components_tab(self):
        """Set up the form components test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Component visualizer
        visualizer = ComponentVisualizer()
        layout.addWidget(visualizer)
        
        # Components to test
        components_layout = QHBoxLayout()
        
        # Form layout
        test_form_btn = QPushButton("Test Form Layout")
        test_form_btn.clicked.connect(lambda: self.test_form_layout(visualizer))
        components_layout.addWidget(test_form_btn)
        
        # Grid layout
        test_grid_btn = QPushButton("Test Grid Layout")
        test_grid_btn.clicked.connect(lambda: self.test_grid_layout(visualizer))
        components_layout.addWidget(test_grid_btn)
        
        # Table
        test_table_btn = QPushButton("Test Table")
        test_table_btn.clicked.connect(lambda: self.test_table_component(visualizer))
        components_layout.addWidget(test_table_btn)
        
        layout.addLayout(components_layout)
        
        self.tabs.addTab(tab, "Form Components")
    
    def setup_dialogs_tab(self):
        """Set up the dialogs test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Instructions
        label = QLabel("Dialogs will appear as separate windows:")
        layout.addWidget(label)
        
        # Dialog buttons
        dialog_layout = QHBoxLayout()
        
        # Message box
        test_msgbox_btn = QPushButton("Test Message Box")
        test_msgbox_btn.clicked.connect(self.test_message_box)
        dialog_layout.addWidget(test_msgbox_btn)
        
        # Custom dialog
        test_dialog_btn = QPushButton("Test Custom Dialog")
        test_dialog_btn.clicked.connect(self.test_custom_dialog)
        dialog_layout.addWidget(test_dialog_btn)
        
        # File dialog
        test_file_dialog_btn = QPushButton("Test File Dialog")
        test_file_dialog_btn.clicked.connect(self.test_file_dialog)
        dialog_layout.addWidget(test_file_dialog_btn)
        
        layout.addLayout(dialog_layout)
        
        # Preview area
        preview_group = QGroupBox("Dialog Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.dialog_preview = QTextEdit()
        self.dialog_preview.setReadOnly(True)
        self.dialog_preview.setHtml(
            "<h3>Dialog Information</h3>"
            "<p>Click the buttons above to test different dialog types.</p>"
            "<p>Dialog information will appear here after testing.</p>"
        )
        
        preview_layout.addWidget(self.dialog_preview)
        layout.addWidget(preview_group)
        
        self.tabs.addTab(tab, "Dialog Tests")
    
    def setup_complex_layouts_tab(self):
        """Set up the complex layouts test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Component visualizer
        visualizer = ComponentVisualizer()
        layout.addWidget(visualizer)
        
        # Components to test
        components_layout = QHBoxLayout()
        
        # Settings panel
        test_settings_btn = QPushButton("Test Settings Panel")
        test_settings_btn.clicked.connect(lambda: self.test_settings_panel(visualizer))
        components_layout.addWidget(test_settings_btn)
        
        # Detection controls
        test_detection_btn = QPushButton("Test Detection Controls")
        test_detection_btn.clicked.connect(lambda: self.test_detection_controls(visualizer))
        components_layout.addWidget(test_detection_btn)
        
        # Automation sequence
        test_automation_btn = QPushButton("Test Automation Controls")
        test_automation_btn.clicked.connect(lambda: self.test_automation_controls(visualizer))
        components_layout.addWidget(test_automation_btn)
        
        layout.addLayout(components_layout)
        
        self.tabs.addTab(tab, "Complex Layouts")
    
    def setup_game_state_tab(self):
        """Set up the game state test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Component visualizer
        visualizer = ComponentVisualizer()
        layout.addWidget(visualizer)
        
        # Components to test
        components_layout = QHBoxLayout()
        
        # Resource panel
        test_resources_btn = QPushButton("Test Resource Panel")
        test_resources_btn.clicked.connect(lambda: self.test_resource_panel(visualizer))
        components_layout.addWidget(test_resources_btn)
        
        # Map controls
        test_map_btn = QPushButton("Test Map Controls")
        test_map_btn.clicked.connect(lambda: self.test_map_controls(visualizer))
        components_layout.addWidget(test_map_btn)
        
        # Army panel
        test_army_btn = QPushButton("Test Army Panel")
        test_army_btn.clicked.connect(lambda: self.test_army_panel(visualizer))
        components_layout.addWidget(test_army_btn)
        
        layout.addLayout(components_layout)
        
        self.tabs.addTab(tab, "Game State")
    
    def load_translators(self):
        """
        This method is now optional since we're using our custom DemoTranslator.
        
        It's kept for debugging purposes and future extensibility.
        """
        logger.info("Using demo translators that don't rely on QM files")
    
    def on_language_changed(self, index):
        """Handle language change."""
        language_code = self.lang_combo.itemData(index)
        logger.info(f"Switching language to: {language_code}")
        
        app = QApplication.instance()
        
        # Set the language on the app instance - important to set the enum value not string
        if language_code == Language.GERMAN:
            app.demo_language = Language.GERMAN
            logger.info("Set app.demo_language to Language.GERMAN")
        elif language_code == Language.ENGLISH:
            app.demo_language = Language.ENGLISH
            logger.info("Set app.demo_language to Language.ENGLISH")
        else:
            # For system, use the system locale
            system_locale = QLocale.system()
            if system_locale.language() == QLocale.Language.German:
                app.demo_language = Language.GERMAN
                logger.info("Set app.demo_language to Language.GERMAN (system)")
            else:
                app.demo_language = Language.ENGLISH
                logger.info("Set app.demo_language to Language.ENGLISH (system)")
        
        # Remove all translators
        for translator in self.translators.values():
            app.removeTranslator(translator)
        
        # Install appropriate translator
        if language_code == Language.GERMAN:
            logger.info("Installing German translator")
            app.installTranslator(self.translators[Language.GERMAN])
            self.current_language = Language.GERMAN
        elif language_code == Language.ENGLISH:
            logger.info("Using English (base language)")
            app.installTranslator(self.translators[Language.ENGLISH])
            self.current_language = Language.ENGLISH
        else:
            # System language - use system locale to determine
            if system_locale.language() == QLocale.Language.German:
                logger.info("System language is German, installing German translator")
                app.installTranslator(self.translators[Language.GERMAN])
                self.current_language = Language.GERMAN
            else:
                logger.info("System language defaulting to English")
                app.installTranslator(self.translators[Language.ENGLISH])
                self.current_language = Language.ENGLISH
        
        # Force UI update after language change
        self.update_language_info()
        
        # Force recreation of components to ensure they use the new language
        current_tab = self.tabs.currentWidget()
        if current_tab:
            # Find and click the first button to recreate the component
            first_button = current_tab.findChild(QPushButton)
            if first_button:
                logger.info(f"Clicking button to recreate component: {first_button.text()}")
                first_button.click()
        
        # Refresh tab labels
        self.retranslate_ui()
        
        # Log the change
        self.log_result(f"Changed language to: {self.lang_combo.currentText()}")
    
    def update_language_info(self):
        """Update the current language information display."""
        lang_name = "System Default"
        if self.current_language == Language.ENGLISH:
            lang_name = "English"
        elif self.current_language == Language.GERMAN:
            lang_name = "German"
        
        self.lang_info.setText(f"Current Language: {lang_name}")
    
    def run_all_tests(self):
        """Run all component tests."""
        # Switch to each tab and run the test
        for i in range(self.tabs.count()):
            self.tabs.setCurrentIndex(i)
            QApplication.processEvents()  # Allow UI to update
            
            # Find the first test button and click it
            tab_widget = self.tabs.widget(i)
            first_button = tab_widget.findChild(QPushButton)
            if first_button:
                first_button.click()
                QApplication.processEvents()  # Allow UI to update
            
            # Wait a moment before continuing
            QTimer.singleShot(500, lambda: None)
        
        self.log_result("All tests completed")
    
    def log_result(self, message, is_error=False):
        """Log a test result."""
        color = "red" if is_error else "black"
        self.results_text.append(f"<p style='color: {color};'>{message}</p>")
    
    # Test component generators
    def test_label_component(self, visualizer):
        """Test a label component."""
        # Force using the current language
        current_language = self.current_language
        logger.info(f"Creating label with language: {current_language}")
        
        # Get the text and explicitly translate it
        source_text = "This is a test label with potentially long text that needs to be properly wrapped and displayed"
        if current_language == Language.GERMAN and source_text in DEMO_TRANSLATIONS[Language.GERMAN]:
            display_text = DEMO_TRANSLATIONS[Language.GERMAN][source_text]
            logger.info(f"Using direct German translation: {display_text}")
        else:
            display_text = tr(source_text)
            logger.info(f"Using tr() function: {display_text}")
        
        # Create the label with the translated text
        label = QLabel(display_text)
        label.setWordWrap(True)
        
        visualizer.set_component(
            label, 
            "QLabel Test",
            f"Testing with language: {current_language}. Text should be in {'German' if current_language == Language.GERMAN else 'English'}."
        )
        self.log_result(f"Tested QLabel component with language: {current_language}")
    
    def test_button_component(self, visualizer):
        """Test a button component."""
        # Force using the current language
        current_language = self.current_language
        logger.info(f"Creating button with language: {current_language}")
        
        # Get the text and explicitly translate it
        source_text = "Save Configuration"
        if current_language == Language.GERMAN and source_text in DEMO_TRANSLATIONS[Language.GERMAN]:
            display_text = DEMO_TRANSLATIONS[Language.GERMAN][source_text]
            logger.info(f"Using direct German translation: {display_text}")
        else:
            display_text = tr(source_text)
            logger.info(f"Using tr() function: {display_text}")
        
        # Create the button with the translated text
        button = QPushButton(display_text)
        set_min_width_for_text(button, display_text + " " * 5)
        
        visualizer.set_component(
            button,
            "QPushButton Test",
            f"Testing with language: {current_language}. Text should be in {'German' if current_language == Language.GERMAN else 'English'}."
        )
        self.log_result(f"Tested QPushButton component with language: {current_language}")
    
    def test_combo_component(self, visualizer):
        """Test a combo box component."""
        combo = QComboBox()
        combo.addItem(tr("System Default"))
        combo.addItem(tr("English"))
        combo.addItem(tr("German"))
        combo.addItem(tr("French"))
        combo.addItem(tr("Spanish"))
        combo.addItem(tr("Italian"))
        
        # Set minimum width based on longest option
        set_min_width_for_text(combo, tr("System Default") + " " * 5)
        
        visualizer.set_component(
            combo,
            "QComboBox Test",
            "Testing a combo box with options that may have different lengths in different languages."
        )
        self.log_result("Tested QComboBox component")
    
    def test_checkbox_component(self, visualizer):
        """Test a checkbox component."""
        checkbox = QCheckBox(tr("Enable advanced options for detection and processing"))
        visualizer.set_component(
            checkbox,
            "QCheckBox Test",
            "Testing a checkbox with text that may be longer in German than in English."
        )
        self.log_result("Tested QCheckBox component")
    
    def test_form_layout(self, visualizer):
        """Test a form layout."""
        widget = QWidget()
        form_layout = QFormLayout(widget)
        
        # Add some form fields
        form_layout.addRow(tr("Username:"), QLineEdit())
        form_layout.addRow(tr("Password:"), QLineEdit())
        form_layout.addRow(tr("Email Address:"), QLineEdit())
        form_layout.addRow(tr("Phone Number:"), QLineEdit())
        
        # Add a checkbox
        form_layout.addRow(tr("Remember Login:"), QCheckBox())
        
        # Add a combo box
        combo = QComboBox()
        combo.addItems([
            tr("Administrator"), tr("User"), tr("Guest")
        ])
        form_layout.addRow(tr("Account Type:"), combo)
        
        visualizer.set_component(
            widget,
            "QFormLayout Test",
            "Testing a form layout with labels that may have different lengths in different languages."
        )
        self.log_result("Tested QFormLayout component")
    
    def test_grid_layout(self, visualizer):
        """Test a grid layout."""
        widget = QWidget()
        from PyQt6.QtWidgets import QGridLayout
        grid_layout = QGridLayout(widget)
        
        # Add some grid items
        grid_layout.addWidget(QLabel(tr("Name:")), 0, 0)
        grid_layout.addWidget(QLineEdit(), 0, 1)
        
        grid_layout.addWidget(QLabel(tr("Address:")), 1, 0)
        grid_layout.addWidget(QLineEdit(), 1, 1)
        
        grid_layout.addWidget(QLabel(tr("City:")), 2, 0)
        grid_layout.addWidget(QLineEdit(), 2, 1)
        
        grid_layout.addWidget(QLabel(tr("State/Province:")), 3, 0)
        grid_layout.addWidget(QLineEdit(), 3, 1)
        
        grid_layout.addWidget(QLabel(tr("Postal Code:")), 4, 0)
        grid_layout.addWidget(QLineEdit(), 4, 1)
        
        visualizer.set_component(
            widget,
            "QGridLayout Test",
            "Testing a grid layout with labels that may have different lengths in different languages."
        )
        self.log_result("Tested QGridLayout component")
    
    def test_table_component(self, visualizer):
        """Test a table component."""
        table = QTableWidget(5, 3)
        
        # Set headers
        table.setHorizontalHeaderLabels([
            tr("Name"), 
            tr("Type"), 
            tr("Description")
        ])
        
        # Add some data
        items = [
            (tr("Coffee"), tr("Beverage"), tr("Hot drink made from roasted coffee beans")),
            (tr("Tea"), tr("Beverage"), tr("Hot drink made by infusing tea leaves in water")),
            (tr("Water"), tr("Beverage"), tr("Clear, colorless, odorless liquid")),
            (tr("Orange Juice"), tr("Beverage"), tr("Juice from oranges")),
            (tr("Apple"), tr("Fruit"), tr("Round fruit from an apple tree"))
        ]
        
        for row, (name, type_, desc) in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(type_))
            table.setItem(row, 2, QTableWidgetItem(desc))
        
        # Resize columns to content
        table.resizeColumnsToContents()
        
        visualizer.set_component(
            table,
            "QTableWidget Test",
            "Testing a table with headers and content that may have different lengths in different languages."
        )
        self.log_result("Tested QTableWidget component")
    
    def test_settings_panel(self, visualizer):
        """Test a settings panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create a group box
        group = QGroupBox(tr("Detection Settings"))
        group_layout = QFormLayout(group)
        
        # Add some settings
        confidence = QSlider(Qt.Orientation.Horizontal)
        confidence.setRange(0, 100)
        confidence.setValue(70)
        group_layout.addRow(tr("Confidence Threshold:"), confidence)
        
        # Max matches
        max_matches = QSpinBox()
        max_matches.setRange(1, 100)
        max_matches.setValue(5)
        group_layout.addRow(tr("Maximum Matches:"), max_matches)
        
        # Strategy combo
        strategy = QComboBox()
        strategy.addItems([
            tr("Template Matching"), 
            tr("Feature Matching"), 
            tr("OCR"),
            tr("YOLO")
        ])
        # Set minimum width
        set_min_width_for_text(strategy, tr("Template Matching") + " " * 5)
        group_layout.addRow(tr("Detection Strategy:"), strategy)
        
        # Use GPU
        use_gpu = QCheckBox()
        use_gpu.setChecked(True)
        group_layout.addRow(tr("Use GPU Acceleration:"), use_gpu)
        
        layout.addWidget(group)
        
        visualizer.set_component(
            widget,
            "Settings Panel Test",
            "Testing a settings panel with various controls and labels that may have different lengths in different languages."
        )
        self.log_result("Tested Settings Panel component")
    
    def test_detection_controls(self, visualizer):
        """Test detection controls."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Add detection buttons
        run_btn = QPushButton(tr("Run Detection"))
        layout.addWidget(run_btn)
        
        stop_btn = QPushButton(tr("Stop"))
        layout.addWidget(stop_btn)
        
        # Add a spacer
        layout.addStretch()
        
        # Add template selection
        layout.addWidget(QLabel(tr("Select Template:")))
        
        template = QComboBox()
        template.addItems([
            tr("Button"), 
            tr("Dialog"),
            tr("Window"),
            tr("Resource Icon")
        ])
        layout.addWidget(template)
        
        # Adjust button sizes
        adjust_button_sizes([run_btn, stop_btn])
        
        visualizer.set_component(
            widget,
            "Detection Controls Test",
            "Testing detection controls with buttons and dropdown that may have different lengths in different languages."
        )
        self.log_result("Tested Detection Controls component")
    
    def test_automation_controls(self, visualizer):
        """Test automation controls."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Top row with sequence selection
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(tr("Sequence:")))
        
        sequence = QComboBox()
        sequence.addItems([
            tr("Resource Collection"),
            tr("Building Upgrade"),
            tr("Troop Training"),
            tr("Map Exploration")
        ])
        set_min_width_for_text(sequence, tr("Building Upgrade") + " " * 5)
        top_row.addWidget(sequence)
        
        # Add buttons
        new_btn = QPushButton(tr("New"))
        top_row.addWidget(new_btn)
        
        open_btn = QPushButton(tr("Open"))
        top_row.addWidget(open_btn)
        
        save_btn = QPushButton(tr("Save"))
        top_row.addWidget(save_btn)
        
        layout.addLayout(top_row)
        
        # Bottom row with execution controls
        bottom_row = QHBoxLayout()
        
        run_btn = QPushButton(tr("Run"))
        bottom_row.addWidget(run_btn)
        
        stop_btn = QPushButton(tr("Stop"))
        bottom_row.addWidget(stop_btn)
        
        # Add options
        bottom_row.addWidget(QLabel(tr("Loop:")))
        
        loop = QCheckBox()
        bottom_row.addWidget(loop)
        
        bottom_row.addWidget(QLabel(tr("Iterations:")))
        
        iterations = QSpinBox()
        iterations.setRange(1, 100)
        iterations.setValue(1)
        bottom_row.addWidget(iterations)
        
        layout.addLayout(bottom_row)
        
        # Adjust button sizes
        adjust_button_sizes([new_btn, open_btn, save_btn, run_btn, stop_btn])
        
        visualizer.set_component(
            widget,
            "Automation Controls Test",
            "Testing automation controls with various buttons and options that may have different lengths in different languages."
        )
        self.log_result("Tested Automation Controls component")
    
    def test_resource_panel(self, visualizer):
        """Test resource panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create a group box
        group = QGroupBox(tr("Resources"))
        group_layout = QFormLayout(group)
        
        # Add resource values
        group_layout.addRow(tr("Gold:"), QLabel("1,234,567"))
        group_layout.addRow(tr("Food:"), QLabel("987,654"))
        group_layout.addRow(tr("Wood:"), QLabel("567,890"))
        group_layout.addRow(tr("Stone:"), QLabel("345,678"))
        group_layout.addRow(tr("Iron:"), QLabel("123,456"))
        
        layout.addWidget(group)
        
        visualizer.set_component(
            widget,
            "Resource Panel Test",
            "Testing a resource panel with labels that may have different lengths in different languages."
        )
        self.log_result("Tested Resource Panel component")
    
    def test_map_controls(self, visualizer):
        """Test map controls."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Add map control buttons
        zoom_in_btn = QPushButton(tr("Zoom In"))
        layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton(tr("Zoom Out"))
        layout.addWidget(zoom_out_btn)
        
        reset_btn = QPushButton(tr("Reset View"))
        layout.addWidget(reset_btn)
        
        # Add spacer
        layout.addStretch()
        
        # Add filter options
        layout.addWidget(QLabel(tr("Filter:")))
        
        filter_combo = QComboBox()
        filter_combo.addItems([
            tr("All"),
            tr("Resources"),
            tr("Enemies"),
            tr("Allies"),
            tr("Points of Interest")
        ])
        layout.addWidget(filter_combo)
        
        # Adjust button sizes
        adjust_button_sizes([zoom_in_btn, zoom_out_btn, reset_btn])
        
        visualizer.set_component(
            widget,
            "Map Controls Test",
            "Testing map controls with buttons and dropdown that may have different lengths in different languages."
        )
        self.log_result("Tested Map Controls component")
    
    def test_army_panel(self, visualizer):
        """Test army panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create a group box
        group = QGroupBox(tr("Army Units"))
        group_layout = QFormLayout(group)
        
        # Add unit counts
        group_layout.addRow(tr("Infantry:"), QLabel("1,234"))
        group_layout.addRow(tr("Cavalry:"), QLabel("567"))
        group_layout.addRow(tr("Archers:"), QLabel("890"))
        group_layout.addRow(tr("Siege Engines:"), QLabel("123"))
        group_layout.addRow(tr("Special Units:"), QLabel("45"))
        
        layout.addWidget(group)
        
        visualizer.set_component(
            widget,
            "Army Panel Test",
            "Testing an army panel with labels that may have different lengths in different languages."
        )
        self.log_result("Tested Army Panel component")
    
    # Dialog tests
    def test_message_box(self):
        """Test a message box dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        result = QMessageBox.question(
            self,
            tr("Confirmation"),
            tr("Are you sure you want to perform this action?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        response = "Yes" if result == QMessageBox.StandardButton.Yes else "No"
        
        # Update dialog preview
        self.dialog_preview.setHtml(
            f"<h3>Message Box Test</h3>"
            f"<p>Title: {tr('Confirmation')}</p>"
            f"<p>Message: {tr('Are you sure you want to perform this action?')}</p>"
            f"<p>User Response: {response}</p>"
        )
        
        self.log_result(f"Tested Message Box dialog, user clicked: {response}")
    
    def test_custom_dialog(self):
        """Test a custom dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Settings Export"))
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Add some content
        layout.addWidget(QLabel(tr("Select export options:")))
        
        # Add some options
        layout.addWidget(QCheckBox(tr("Include system information")))
        layout.addWidget(QCheckBox(tr("Include user preferences")))
        layout.addWidget(QCheckBox(tr("Include detection settings")))
        layout.addWidget(QCheckBox(tr("Include automation sequences")))
        
        # Add button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        result = dialog.exec()
        
        response = "OK" if result == QDialog.DialogCode.Accepted else "Cancel"
        
        # Update dialog preview
        self.dialog_preview.setHtml(
            f"<h3>Custom Dialog Test</h3>"
            f"<p>Title: {tr('Settings Export')}</p>"
            f"<p>Options:</p>"
            f"<ul>"
            f"<li>{tr('Include system information')}</li>"
            f"<li>{tr('Include user preferences')}</li>"
            f"<li>{tr('Include detection settings')}</li>"
            f"<li>{tr('Include automation sequences')}</li>"
            f"</ul>"
            f"<p>User Response: {response}</p>"
        )
        
        self.log_result(f"Tested Custom Dialog, user clicked: {response}")
    
    def test_file_dialog(self):
        """Test a file dialog."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Don't actually open the dialog to avoid blocking the test
        # Instead, just show what would be in the dialog
        
        # Update dialog preview
        self.dialog_preview.setHtml(
            f"<h3>File Dialog Test</h3>"
            f"<p>Title: {tr('Open Configuration File')}</p>"
            f"<p>File Types: {tr('Configuration Files')} (*.json);;{tr('All Files')} (*)</p>"
            f"<p>Note: Dialog not shown to avoid blocking test</p>"
        )
        
        self.log_result("Tested File Dialog (simulated)")
    
    def retranslate_ui(self):
        """Update UI elements after language change."""
        # Update tab titles
        tab_titles = [
            tr("Basic Components"),
            tr("Form Elements"),
            tr("Dialogs"),
            tr("Complex Layouts"),
            tr("Game State")
        ]
        
        for i, title in enumerate(tab_titles):
            if i < self.tabs.count():
                self.tabs.setTabText(i, title)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = VisualLanguageTest()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 