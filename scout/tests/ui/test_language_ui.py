"""
Language Switching Test UI

This module provides a visual test application to verify language
switching functionality and layout adjustments in the Scout application.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QCheckBox, QTabWidget, QGridLayout
)
from PyQt6.QtCore import Qt

from scout.translations.language_manager import LanguageManager
from scout.ui.utils.layout_helper import (
    set_min_width_for_text, adjust_button_sizes, 
    create_form_layout, create_responsive_grid_layout
)


class LanguageTestWindow(QMainWindow):
    """A test window for verifying language switching and layout adjustments."""
    
    def __init__(self):
        """Initialize the test window."""
        super().__init__()
        
        # Set up language manager
        self.language_manager = LanguageManager()
        self.language_manager.load_translations()
        
        # Set window properties
        self.setWindowTitle(self.tr("Language Switching Test"))
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Add language selector
        language_layout = QHBoxLayout()
        language_label = QLabel(self.tr("Select Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        main_layout.addLayout(language_layout)
        
        # Create tab widget for different UI examples
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Add tabs for different UI examples
        tab_widget.addTab(self.create_form_tab(), self.tr("Form Elements"))
        tab_widget.addTab(self.create_button_tab(), self.tr("Buttons"))
        tab_widget.addTab(self.create_grid_tab(), self.tr("Grid Layout"))
        tab_widget.addTab(self.create_mixed_tab(), self.tr("Mixed UI"))
        
        # Status bar with language info
        self.statusBar().showMessage(self.tr("Current Language: English"))
    
    def create_form_tab(self):
        """Create a tab with form elements."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Form group box
        form_group = QGroupBox(self.tr("Personal Information"))
        form_layout = create_form_layout()
        
        # Add form fields
        name_label = QLabel(self.tr("Full Name:"))
        name_field = QLineEdit()
        form_layout.addRow(name_label, name_field)
        
        email_label = QLabel(self.tr("Email Address:"))
        email_field = QLineEdit()
        form_layout.addRow(email_label, email_field)
        
        phone_label = QLabel(self.tr("Phone Number:"))
        phone_field = QLineEdit()
        form_layout.addRow(phone_label, phone_field)
        
        address_label = QLabel(self.tr("Mailing Address:"))
        address_field = QTextEdit()
        form_layout.addRow(address_label, address_field)
        
        subscribe_check = QCheckBox(self.tr("Subscribe to newsletter"))
        form_layout.addRow("", subscribe_check)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Add some buttons at the bottom
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.tr("Save Information"))
        clear_button = QPushButton(self.tr("Clear Form"))
        cancel_button = QPushButton(self.tr("Cancel"))
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(cancel_button)
        
        # Adjust button sizes for consistency
        adjust_button_sizes([save_button, clear_button, cancel_button])
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_button_tab(self):
        """Create a tab with various button examples."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Standard buttons group
        standard_group = QGroupBox(self.tr("Standard Buttons"))
        standard_layout = QHBoxLayout(standard_group)
        
        ok_button = QPushButton(self.tr("OK"))
        cancel_button = QPushButton(self.tr("Cancel"))
        apply_button = QPushButton(self.tr("Apply"))
        
        standard_layout.addWidget(ok_button)
        standard_layout.addWidget(cancel_button)
        standard_layout.addWidget(apply_button)
        standard_layout.addStretch()
        
        # Adjust button sizes
        adjust_button_sizes([ok_button, cancel_button, apply_button])
        
        layout.addWidget(standard_group)
        
        # Action buttons group
        action_group = QGroupBox(self.tr("Action Buttons"))
        action_layout = QHBoxLayout(action_group)
        
        save_button = QPushButton(self.tr("Save Project"))
        export_button = QPushButton(self.tr("Export Results"))
        settings_button = QPushButton(self.tr("Open Settings"))
        
        action_layout.addWidget(save_button)
        action_layout.addWidget(export_button)
        action_layout.addWidget(settings_button)
        action_layout.addStretch()
        
        # Adjust button sizes
        adjust_button_sizes([save_button, export_button, settings_button])
        
        layout.addWidget(action_group)
        
        # Long text buttons group
        long_group = QGroupBox(self.tr("Buttons with Long Text"))
        long_layout = QVBoxLayout(long_group)
        
        long_button1 = QPushButton(self.tr("Generate Comprehensive Analysis Report"))
        long_button2 = QPushButton(self.tr("Export All Data to External Database"))
        long_button3 = QPushButton(self.tr("Configure Advanced Detection Parameters"))
        
        long_layout.addWidget(long_button1)
        long_layout.addWidget(long_button2)
        long_layout.addWidget(long_button3)
        
        # Each button gets its width set individually based on text
        set_min_width_for_text(long_button1, long_button1.text())
        set_min_width_for_text(long_button2, long_button2.text())
        set_min_width_for_text(long_button3, long_button3.text())
        
        layout.addWidget(long_group)
        
        layout.addStretch()
        return widget
    
    def create_grid_tab(self):
        """Create a tab with grid layout examples."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Grid layout example
        grid_group = QGroupBox(self.tr("Game State Grid"))
        grid_layout = create_responsive_grid_layout(3)  # 3 columns
        
        # Add items to grid
        labels = [
            self.tr("Player Position"), self.tr("Enemy Count"), self.tr("Health"),
            self.tr("Ammunition"), self.tr("Score"), self.tr("Time Left"),
            self.tr("Level Name"), self.tr("Difficulty"), self.tr("Status")
        ]
        
        for i, label_text in enumerate(labels):
            row = i // 3
            col = i % 3
            label = QLabel(f"{label_text}:")
            value = QLabel(f"Value {i+1}")
            
            # Make sure labels have consistent width
            set_min_width_for_text(label, label_text)
            
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.addWidget(label)
            container_layout.addWidget(value)
            container_layout.addStretch()
            
            grid_layout.addWidget(container, row, col)
        
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        
        # Another grid example with form elements
        form_grid_group = QGroupBox(self.tr("Settings Grid"))
        form_grid_layout = create_responsive_grid_layout(2)  # 2 columns
        
        # Settings in a grid
        settings = [
            (self.tr("Enable Autosave"), QCheckBox()),
            (self.tr("Autosave Interval (minutes)"), QLineEdit("5")),
            (self.tr("Show Notifications"), QCheckBox()),
            (self.tr("Log Level"), QComboBox())
        ]
        
        for i, (label_text, widget) in enumerate(settings):
            row = i // 2
            col = i % 2
            label = QLabel(f"{label_text}:")
            
            # Make sure labels have consistent width
            set_min_width_for_text(label, label_text)
            
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.addWidget(label)
            container_layout.addWidget(widget)
            container_layout.addStretch()
            
            form_grid_layout.addWidget(container, row, col)
        
        form_grid_group.setLayout(form_grid_layout)
        layout.addWidget(form_grid_group)
        
        layout.addStretch()
        return widget
    
    def create_mixed_tab(self):
        """Create a tab with mixed UI elements."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Information section
        info_label = QLabel(self.tr(
            "This tab demonstrates a mixture of UI elements that might be found in a typical application screen. "
            "Pay attention to how layouts adapt when switching between languages."
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Project section
        project_group = QGroupBox(self.tr("Project Overview"))
        project_layout = QFormLayout(project_group)
        project_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        project_name = QLineEdit("Scout Demo Project")
        project_desc = QTextEdit()
        project_desc.setPlaceholderText(self.tr("Enter project description here..."))
        project_desc.setMaximumHeight(80)
        
        project_layout.addRow(self.tr("Project Name:"), project_name)
        project_layout.addRow(self.tr("Description:"), project_desc)
        
        layout.addWidget(project_group)
        
        # Statistics section
        stats_group = QGroupBox(self.tr("Detection Statistics"))
        stats_layout = create_responsive_grid_layout(3)
        
        stat_items = [
            (self.tr("Total Scans"), "1,245"),
            (self.tr("Objects Detected"), "3,782"),
            (self.tr("Average Confidence"), "87.3%"),
            (self.tr("False Positives"), "42"),
            (self.tr("Processing Time"), "3.2s"),
            (self.tr("Memory Usage"), "1.2 GB")
        ]
        
        for i, (label_text, value) in enumerate(stat_items):
            row = i // 3
            col = i % 3
            
            label = QLabel(f"{label_text}:")
            value_label = QLabel(f"<b>{value}</b>")
            
            # Make sure labels have consistent width
            set_min_width_for_text(label, label_text)
            
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.addWidget(label)
            container_layout.addWidget(value_label)
            container_layout.addStretch()
            
            stats_layout.addWidget(container, row, col)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        run_button = QPushButton(self.tr("Run New Scan"))
        export_button = QPushButton(self.tr("Export Results"))
        settings_button = QPushButton(self.tr("Settings"))
        help_button = QPushButton(self.tr("Help"))
        
        button_layout.addWidget(run_button)
        button_layout.addWidget(export_button)
        button_layout.addStretch()
        button_layout.addWidget(settings_button)
        button_layout.addWidget(help_button)
        
        # Adjust button sizes
        adjust_button_sizes([run_button, export_button, settings_button, help_button])
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return widget
    
    def change_language(self, index):
        """Change the application language."""
        language_code = self.language_combo.itemData(index)
        self.language_manager.switch_language(language_code)
        
        # Update status bar
        language_name = "English" if language_code == "en" else "Deutsch"
        self.statusBar().showMessage(self.tr(f"Current Language: {language_name}"))
        
        # Force window to redraw and recompute sizes
        self.adjustSize()


def run_language_test():
    """Run the language test application."""
    app = QApplication(sys.argv)
    window = LanguageTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_language_test()