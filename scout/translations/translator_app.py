#!/usr/bin/env python3
"""
Translator Application

A standalone application for testing translations and visualizing layout issues
across the Scout application. This tool helps developers identify and fix layout
issues that might arise when switching between different languages.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import datetime

from PyQt6.QtCore import QSize, Qt, QLocale, QTranslator, QEvent
from PyQt6.QtGui import QAction, QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
    QScrollArea, QCheckBox, QFrame, QGroupBox, QStatusBar, QTabWidget,
    QFormLayout, QLineEdit, QSpinBox, QTextEdit, QMenu, QMenuBar, QToolBar,
    QFileDialog
)

from scout.translations.config import (
    LANGUAGE_EXPANSION_FACTORS,
    DEFAULT_SPACING,
    DEFAULT_PADDING
)

from scout.ui.utils.layout_helper import (
    get_current_language_code, get_expansion_factor, 
    set_min_width_for_text, adjust_button_sizes,
    create_form_layout, create_responsive_grid_layout
)


class ComponentPreviewWidget(QWidget):
    """
    Widget that shows a preview of a UI component with optional border highlighting
    for layout visualization.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_borders = False
        self.highlight_issues = False
        self.component = None
        self.expansion_factor = 1.0
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 10, 10, 10)
        
        # Default message
        self.default_label = QLabel("Select a component from the tree to preview")
        self.default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.default_label)
    
    def set_component(self, component: QWidget) -> None:
        """Set the component to preview."""
        # Remove current component
        if self.component:
            self.layout().removeWidget(self.component)
            self.component.setParent(None)
        
        # Clear default label
        if self.default_label:
            self.layout().removeWidget(self.default_label)
            self.default_label.setParent(None)
            self.default_label = None
        
        # Add new component
        self.component = component
        if component:
            self.layout().addWidget(component)
    
    def set_show_borders(self, show: bool) -> None:
        """Set whether to show widget borders."""
        self.show_borders = show
        self.update()
    
    def set_highlight_issues(self, highlight: bool) -> None:
        """Set whether to highlight potential layout issues."""
        self.highlight_issues = highlight
        self.update()
    
    def set_expansion_factor(self, factor: float) -> None:
        """Set the current language expansion factor for highlighting."""
        self.expansion_factor = factor
        self.update()
    
    def paintEvent(self, event) -> None:
        """Custom paint event to draw borders and highlights."""
        super().paintEvent(event)
        
        if not self.component:
            return
        
        if self.show_borders or self.highlight_issues:
            painter = QPainter(self)
            
            def draw_borders(widget, level=0):
                rect = widget.geometry()
                
                # Draw border
                if self.show_borders:
                    painter.setPen(QPen(QColor(0, 0, 255, 100), 1))
                    painter.drawRect(rect)
                
                # Highlight potential issues
                if self.highlight_issues and hasattr(widget, 'minimumWidth'):
                    min_width = widget.minimumWidth()
                    if min_width > 0:
                        # If the widget has text and a fixed/minimum width, check if it might be too small
                        text = ""
                        if hasattr(widget, 'text'):
                            text = widget.text()
                        
                        if text and self.expansion_factor > 1.0:
                            # Highlight fixed-width widgets with text that might be too narrow
                            if hasattr(widget, 'maximumWidth') and widget.maximumWidth() < 10000:
                                if widget.maximumWidth() - min_width < 20:  # Fixed or nearly fixed width
                                    painter.setPen(QPen(QColor(255, 0, 0, 100), 2))
                                    painter.drawRect(rect)
                            
                            # Highlight potential overflow areas
                            needed_width = len(text) * 8 * self.expansion_factor  # Rough estimate
                            if needed_width > min_width and hasattr(widget, 'text'):
                                painter.setPen(QPen(QColor(255, 165, 0, 100), 2))
                                painter.drawRect(rect)
                
                # Recursively process child widgets
                if hasattr(widget, 'children'):
                    for child in widget.children():
                        if isinstance(child, QWidget) and child.isVisible():
                            draw_borders(child, level + 1)
            
            if self.component:
                draw_borders(self.component)


class TranslatorApp(QMainWindow):
    """
    Main application window for the translator testing tool.
    
    This application allows testing UI components with different languages
    and identifying potential layout issues.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize translators
        self.translators = {}
        self.current_language = get_current_language_code()
        self.load_translators()
        
        # Set up the UI
        self.setup_ui()
    
    def load_translators(self) -> None:
        """Load available translation files."""
        logging.info("Loading translators...")
        
        # Get the translations directory
        script_dir = Path(__file__).parent
        translations_dir = script_dir
        
        # Look for .qm files
        for lang_code in LANGUAGE_EXPANSION_FACTORS.keys():
            qm_path = translations_dir / f"scout_{lang_code}.qm"
            if qm_path.exists():
                translator = QTranslator()
                if translator.load(str(qm_path)):
                    self.translators[lang_code] = translator
                    logging.info(f"Loaded translator for {lang_code}")
                else:
                    logging.warning(f"Failed to load translator for {lang_code}")
        
        logging.info(f"Loaded {len(self.translators)} translators")
    
    def setup_ui(self) -> None:
        """Set up the main UI components."""
        self.setWindowTitle("Scout Translator Tool")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(toolbar_layout)
        
        # Language selector
        lang_label = QLabel("Language:")
        toolbar_layout.addWidget(lang_label)
        
        self.language_combo = QComboBox()
        for lang_code, factor in LANGUAGE_EXPANSION_FACTORS.items():
            if lang_code in self.translators or lang_code == 'en':
                lang_name = QLocale(lang_code).nativeLanguageName()
                self.language_combo.addItem(f"{lang_name} ({lang_code})", lang_code)
        
        # Set current language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == self.current_language:
                self.language_combo.setCurrentIndex(i)
                break
        
        self.language_combo.currentIndexChanged.connect(self.change_language)
        toolbar_layout.addWidget(self.language_combo)
        toolbar_layout.addSpacing(20)
        
        # View options
        self.show_borders_checkbox = QCheckBox("Show Component Borders")
        self.show_borders_checkbox.setChecked(False)
        self.show_borders_checkbox.toggled.connect(self.toggle_borders)
        toolbar_layout.addWidget(self.show_borders_checkbox)
        
        self.highlight_issues_checkbox = QCheckBox("Highlight Potential Issues")
        self.highlight_issues_checkbox.setChecked(True)
        self.highlight_issues_checkbox.toggled.connect(self.toggle_highlight)
        toolbar_layout.addWidget(self.highlight_issues_checkbox)
        
        toolbar_layout.addStretch(1)
        
        # Screenshot button
        self.screenshot_button = QPushButton("Save Screenshot")
        self.screenshot_button.clicked.connect(self.save_screenshot)
        toolbar_layout.addWidget(self.screenshot_button)
        
        # Main splitter (tree view and preview area)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Component tree
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("UI Components")
        self.tree_widget.setMinimumWidth(250)
        self.tree_widget.itemClicked.connect(self.on_component_selected)
        splitter.addWidget(self.tree_widget)
        
        # Preview area
        preview_container = QScrollArea()
        preview_container.setWidgetResizable(True)
        self.preview_widget = ComponentPreviewWidget()
        preview_container.setWidget(self.preview_widget)
        splitter.addWidget(preview_container)
        
        # Set splitter proportions
        splitter.setSizes([250, 750])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
        # Populate the component tree
        self.populate_component_tree()
    
    def populate_component_tree(self) -> None:
        """Populate the tree widget with available UI components for testing."""
        # Top-level categories
        main_window = QTreeWidgetItem(self.tree_widget, ["Main Window"])
        detection = QTreeWidgetItem(self.tree_widget, ["Detection"])
        automation = QTreeWidgetItem(self.tree_widget, ["Automation"])
        game_state = QTreeWidgetItem(self.tree_widget, ["Game State"])
        settings = QTreeWidgetItem(self.tree_widget, ["Settings"])
        
        # Add specific components under each category
        
        # Main Window components
        QTreeWidgetItem(main_window, ["Menu Bar"]).setData(0, Qt.ItemDataRole.UserRole, "menu_bar")
        QTreeWidgetItem(main_window, ["Tool Bar"]).setData(0, Qt.ItemDataRole.UserRole, "tool_bar")
        QTreeWidgetItem(main_window, ["Status Bar"]).setData(0, Qt.ItemDataRole.UserRole, "status_bar")
        
        # Detection components
        QTreeWidgetItem(detection, ["Detection Settings"]).setData(0, Qt.ItemDataRole.UserRole, "detection_settings")
        QTreeWidgetItem(detection, ["Detection Results"]).setData(0, Qt.ItemDataRole.UserRole, "detection_results")
        
        # Automation components
        QTreeWidgetItem(automation, ["Automation Settings"]).setData(0, Qt.ItemDataRole.UserRole, "automation_settings")
        QTreeWidgetItem(automation, ["Script Editor"]).setData(0, Qt.ItemDataRole.UserRole, "script_editor")
        
        # Game State components
        QTreeWidgetItem(game_state, ["Game State Overview"]).setData(0, Qt.ItemDataRole.UserRole, "game_state_overview")
        QTreeWidgetItem(game_state, ["Game State Details"]).setData(0, Qt.ItemDataRole.UserRole, "game_state_details")
        
        # Settings components
        QTreeWidgetItem(settings, ["General Settings"]).setData(0, Qt.ItemDataRole.UserRole, "general_settings")
        QTreeWidgetItem(settings, ["Advanced Settings"]).setData(0, Qt.ItemDataRole.UserRole, "advanced_settings")
        QTreeWidgetItem(settings, ["About Dialog"]).setData(0, Qt.ItemDataRole.UserRole, "about_dialog")
        
        # Expand all items
        self.tree_widget.expandAll()
    
    def on_component_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle component selection from the tree."""
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not component_id:
            return
        
        # Create the selected component
        component = self.create_component(component_id)
        if component:
            self.preview_widget.set_component(component)
            self.status_bar.showMessage(f"Showing component: {item.text(0)}")
    
    def create_component(self, component_id: str) -> Optional[QWidget]:
        """Create a UI component for preview based on its ID."""
        # Get expansion factor for the current language
        expansion_factor = get_expansion_factor()
        self.preview_widget.set_expansion_factor(expansion_factor)
        
        # Create the component based on its ID
        if component_id == "menu_bar":
            return self.create_menu_bar()
        elif component_id == "tool_bar":
            return self.create_tool_bar()
        elif component_id == "status_bar":
            return self.create_status_bar()
        elif component_id == "detection_settings":
            return self.create_detection_settings()
        elif component_id == "detection_results":
            return self.create_detection_results()
        elif component_id == "automation_settings":
            return self.create_automation_settings()
        elif component_id == "script_editor":
            return self.create_script_editor()
        elif component_id == "game_state_overview":
            return self.create_game_state_overview()
        elif component_id == "game_state_details":
            return self.create_game_state_details()
        elif component_id == "general_settings":
            return self.create_general_settings()
        elif component_id == "advanced_settings":
            return self.create_advanced_settings()
        elif component_id == "about_dialog":
            return self.create_about_dialog()
        
        return None
    
    def create_menu_bar(self) -> QWidget:
        """Create a sample menu bar for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        menu_bar = QMenuBar()
        
        file_menu = menu_bar.addMenu(self.tr("File"))
        file_menu.addAction(self.tr("New"))
        file_menu.addAction(self.tr("Open..."))
        file_menu.addAction(self.tr("Save"))
        file_menu.addAction(self.tr("Save As..."))
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Exit"))
        
        edit_menu = menu_bar.addMenu(self.tr("Edit"))
        edit_menu.addAction(self.tr("Undo"))
        edit_menu.addAction(self.tr("Redo"))
        edit_menu.addSeparator()
        edit_menu.addAction(self.tr("Cut"))
        edit_menu.addAction(self.tr("Copy"))
        edit_menu.addAction(self.tr("Paste"))
        
        view_menu = menu_bar.addMenu(self.tr("View"))
        view_menu.addAction(self.tr("Zoom In"))
        view_menu.addAction(self.tr("Zoom Out"))
        view_menu.addAction(self.tr("Reset Zoom"))
        
        tools_menu = menu_bar.addMenu(self.tr("Tools"))
        tools_menu.addAction(self.tr("Detection Settings"))
        tools_menu.addAction(self.tr("Automation Settings"))
        tools_menu.addAction(self.tr("Game State Visualization"))
        
        help_menu = menu_bar.addMenu(self.tr("Help"))
        help_menu.addAction(self.tr("Documentation"))
        help_menu.addAction(self.tr("Check for Updates"))
        help_menu.addSeparator()
        help_menu.addAction(self.tr("About"))
        
        layout.addWidget(menu_bar)
        layout.addStretch(1)
        
        return container
    
    def create_tool_bar(self) -> QWidget:
        """Create a sample toolbar for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        
        toolbar.addAction(self.tr("New"))
        toolbar.addAction(self.tr("Open"))
        toolbar.addAction(self.tr("Save"))
        toolbar.addSeparator()
        toolbar.addAction(self.tr("Cut"))
        toolbar.addAction(self.tr("Copy"))
        toolbar.addAction(self.tr("Paste"))
        toolbar.addSeparator()
        toolbar.addAction(self.tr("Run"))
        toolbar.addAction(self.tr("Stop"))
        
        layout.addWidget(toolbar)
        layout.addStretch(1)
        
        return container
    
    def create_status_bar(self) -> QWidget:
        """Create a sample status bar for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        status = QStatusBar()
        status.showMessage(self.tr("Ready"))
        
        layout.addWidget(status)
        layout.addStretch(1)
        
        return container
    
    def create_detection_settings(self) -> QWidget:
        """Create a sample detection settings panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("Detection Settings"))
        group_layout = QVBoxLayout(group)
        
        form_widget = QWidget()
        labels = [
            QLabel(self.tr("Detection Method:")),
            QLabel(self.tr("Confidence Threshold:")),
            QLabel(self.tr("Filter Results:")),
            QLabel(self.tr("Processing Mode:")),
        ]
        
        fields = [
            QComboBox(),
            QSpinBox(),
            QComboBox(),
            QComboBox(),
        ]
        
        # Set up the combo boxes with options
        fields[0].addItems([
            self.tr("Template Matching"),
            self.tr("Feature Detection"),
            self.tr("Deep Learning"),
            self.tr("Hybrid Approach")
        ])
        
        fields[2].addItems([
            self.tr("Show All Results"),
            self.tr("Only High Confidence"),
            self.tr("Custom Filter")
        ])
        
        fields[3].addItems([
            self.tr("Performance"),
            self.tr("Balanced"),
            self.tr("Quality")
        ])
        
        # Set up spinbox
        fields[1].setRange(0, 100)
        fields[1].setValue(70)
        fields[1].setSuffix("%")
        
        # Create form layout with labels and fields
        form_layout = create_form_layout(list(zip(labels, fields)))
        form_widget.setLayout(form_layout)
        group_layout.addWidget(form_widget)
        
        # Advanced options
        advanced_box = QGroupBox(self.tr("Advanced Options"))
        advanced_layout = QVBoxLayout(advanced_box)
        
        checkboxes = [
            QCheckBox(self.tr("Enable region of interest selection")),
            QCheckBox(self.tr("Use pre-processing filters")),
            QCheckBox(self.tr("Enable multi-scale detection")),
            QCheckBox(self.tr("Save detection results to file"))
        ]
        
        for checkbox in checkboxes:
            advanced_layout.addWidget(checkbox)
        
        group_layout.addWidget(advanced_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton(self.tr("Apply"))
        reset_button = QPushButton(self.tr("Reset"))
        help_button = QPushButton(self.tr("Help"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([apply_button, reset_button, help_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(help_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_detection_results(self) -> QWidget:
        """Create a sample detection results panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("Detection Results"))
        group_layout = QVBoxLayout(group)
        
        # Add a label with detection statistics
        stats_label = QLabel(self.tr("Found 8 objects (6 with high confidence, 2 with medium confidence)"))
        stats_label.setWordWrap(True)
        group_layout.addWidget(stats_label)
        
        # Create a table-like display of results
        results_frame = QFrame()
        results_frame.setFrameShape(QFrame.Shape.StyledPanel)
        results_frame.setFrameShadow(QFrame.Shadow.Sunken)
        results_layout = QVBoxLayout(results_frame)
        
        # Header row
        header_layout = QHBoxLayout()
        headers = [
            self.tr("Object"),
            self.tr("Confidence"),
            self.tr("Position"),
            self.tr("Size"),
            self.tr("Actions")
        ]
        
        for header in headers:
            label = QLabel(header)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(label)
        
        results_layout.addLayout(header_layout)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        results_layout.addWidget(separator)
        
        # Sample results rows
        result_data = [
            (self.tr("Enemy"), "98%", "X: 450, Y: 320", "W: 40, H: 60", self.tr("Select")),
            (self.tr("Health Pack"), "95%", "X: 200, Y: 150", "W: 25, H: 25", self.tr("Select")),
            (self.tr("Weapon"), "92%", "X: 600, Y: 400", "W: 35, H: 15", self.tr("Select")),
            (self.tr("Obstacle"), "88%", "X: 300, Y: 250", "W: 100, H: 50", self.tr("Select")),
            (self.tr("Player"), "85%", "X: 400, Y: 300", "W: 45, H: 70", self.tr("Select")),
            (self.tr("Door"), "78%", "X: 720, Y: 180", "W: 60, H: 100", self.tr("Select")),
            (self.tr("Unknown"), "65%", "X: 150, Y: 500", "W: 30, H: 30", self.tr("Select")),
            (self.tr("Unknown"), "51%", "X: 550, Y: 450", "W: 20, H: 20", self.tr("Select"))
        ]
        
        for data in result_data:
            row_layout = QHBoxLayout()
            
            for i, text in enumerate(data):
                if i < 4:  # Regular labels
                    label = QLabel(text)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    row_layout.addWidget(label)
                else:  # Action button
                    button = QPushButton(text)
                    row_layout.addWidget(button)
            
            results_layout.addLayout(row_layout)
        
        group_layout.addWidget(results_frame)
        
        # Export and clear buttons
        button_layout = QHBoxLayout()
        export_button = QPushButton(self.tr("Export Results"))
        clear_button = QPushButton(self.tr("Clear Results"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([export_button, clear_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(export_button)
        button_layout.addWidget(clear_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_automation_settings(self) -> QWidget:
        """Create a sample automation settings panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("Automation Settings"))
        group_layout = QVBoxLayout(group)
        
        tabs = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        general_form = QWidget()
        general_labels = [
            QLabel(self.tr("Automation Mode:")),
            QLabel(self.tr("Click Delay (ms):")),
            QLabel(self.tr("Mouse Movement:")),
            QLabel(self.tr("Default Script:")),
        ]
        
        general_fields = [
            QComboBox(),
            QSpinBox(),
            QComboBox(),
            QLineEdit(),
        ]
        
        # Set up the combo boxes with options
        general_fields[0].addItems([
            self.tr("Interactive"),
            self.tr("Semi-Automatic"),
            self.tr("Fully Automatic")
        ])
        
        general_fields[2].addItems([
            self.tr("Direct (Instant)"),
            self.tr("Linear Path"),
            self.tr("Human-like")
        ])
        
        # Set up spinbox
        general_fields[1].setRange(0, 1000)
        general_fields[1].setValue(100)
        
        # Set up line edit
        general_fields[3].setText("default_script.py")
        
        # Create form layout with labels and fields
        general_form_layout = create_form_layout(list(zip(general_labels, general_fields)))
        general_form.setLayout(general_form_layout)
        general_layout.addWidget(general_form)
        
        # Advanced options
        advanced_box = QGroupBox(self.tr("Safety Options"))
        advanced_layout = QVBoxLayout(advanced_box)
        
        checkboxes = [
            QCheckBox(self.tr("Emergency stop hotkey (Esc)")),
            QCheckBox(self.tr("Limited runtime (max 2 hours)")),
            QCheckBox(self.tr("Avoid system-critical areas")),
            QCheckBox(self.tr("Log all actions"))
        ]
        
        for checkbox in checkboxes:
            checkbox.setChecked(True)
            advanced_layout.addWidget(checkbox)
        
        general_layout.addWidget(advanced_box)
        
        # Triggers tab
        triggers_tab = QWidget()
        triggers_layout = QVBoxLayout(triggers_tab)
        
        triggers_label = QLabel(self.tr("Define triggers that will start or stop automation:"))
        triggers_layout.addWidget(triggers_label)
        
        triggers_form = QWidget()
        triggers_labels = [
            QLabel(self.tr("On Image Detected:")),
            QLabel(self.tr("On Text Detected:")),
            QLabel(self.tr("On Color Change:")),
            QLabel(self.tr("On Time Elapsed:")),
        ]
        
        triggers_fields = [
            QComboBox(),
            QComboBox(),
            QComboBox(),
            QComboBox(),
        ]
        
        # Set up the combo boxes with options
        triggers_fields[0].addItems([
            self.tr("No Action"),
            self.tr("Start Script"),
            self.tr("Stop Script"),
            self.tr("Pause Script")
        ])
        
        triggers_fields[1].addItems([
            self.tr("No Action"),
            self.tr("Start Script"),
            self.tr("Stop Script"),
            self.tr("Pause Script")
        ])
        
        triggers_fields[2].addItems([
            self.tr("No Action"),
            self.tr("Start Script"),
            self.tr("Stop Script"),
            self.tr("Pause Script")
        ])
        
        triggers_fields[3].addItems([
            self.tr("No Action"),
            self.tr("Start Script"),
            self.tr("Stop Script"),
            self.tr("Pause Script")
        ])
        
        # Create form layout with labels and fields
        triggers_form_layout = create_form_layout(list(zip(triggers_labels, triggers_fields)))
        triggers_form.setLayout(triggers_form_layout)
        triggers_layout.addWidget(triggers_form)
        
        # Add custom trigger button
        add_trigger_button = QPushButton(self.tr("Add Custom Trigger"))
        triggers_layout.addWidget(add_trigger_button)
        triggers_layout.addStretch(1)
        
        # Add tabs
        tabs.addTab(general_tab, self.tr("General"))
        tabs.addTab(triggers_tab, self.tr("Triggers"))
        
        group_layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.tr("Save Settings"))
        load_button = QPushButton(self.tr("Load Settings"))
        reset_button = QPushButton(self.tr("Reset to Defaults"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([save_button, load_button, reset_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(save_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(reset_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_script_editor(self) -> QWidget:
        """Create a sample script editor for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("Script Editor"))
        group_layout = QVBoxLayout(group)
        
        # File name row
        file_layout = QHBoxLayout()
        file_label = QLabel(self.tr("File:"))
        file_edit = QLineEdit("my_script.py")
        file_button = QPushButton(self.tr("Browse..."))
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(file_edit, 1)
        file_layout.addWidget(file_button)
        
        group_layout.addLayout(file_layout)
        
        # Editor
        editor = QTextEdit()
        editor.setPlainText("# Scout Automation Script\n\n"
                           "def main():\n"
                           "    # Find the game window\n"
                           "    window = find_window('Game Window')\n"
                           "    if not window:\n"
                           "        print('Game window not found!')\n"
                           "        return\n\n"
                           "    # Perform automated actions\n"
                           "    click_at(100, 200)  # Click at coordinates\n"
                           "    wait(500)  # Wait 500ms\n"
                           "    type_text('Hello world')\n\n"
                           "    # Detect objects\n"
                           "    objects = detect_objects()\n"
                           "    for obj in objects:\n"
                           "        print(f'Found {obj.name} at {obj.position}')\n\n"
                           "if __name__ == '__main__':\n"
                           "    main()\n")
        
        group_layout.addWidget(editor, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        run_button = QPushButton(self.tr("Run Script"))
        save_button = QPushButton(self.tr("Save"))
        check_button = QPushButton(self.tr("Check Syntax"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([run_button, save_button, check_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(check_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(run_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_game_state_overview(self) -> QWidget:
        """Create a sample game state overview panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("Game State Overview"))
        group_layout = QVBoxLayout(group)
        
        # Status indicators
        status_layout = QHBoxLayout()
        
        status_boxes = [
            (self.tr("Game Status"), self.tr("Running")),
            (self.tr("Player Health"), self.tr("78/100")),
            (self.tr("Position"), self.tr("X: 450, Y: 320")),
            (self.tr("Current Area"), self.tr("Forest of Despair"))
        ]
        
        for title, value in status_boxes:
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(value_label)
            status_layout.addWidget(box)
        
        group_layout.addLayout(status_layout)
        
        # Inventory section
        inventory_group = QGroupBox(self.tr("Inventory"))
        inventory_layout = QGridLayout(inventory_group)
        
        inventory_items = [
            self.tr("Health Potion (3)"),
            self.tr("Mana Potion (2)"),
            self.tr("Iron Sword"),
            self.tr("Leather Armor"),
            self.tr("Magic Wand"),
            self.tr("Gold Coins (250)")
        ]
        
        # Create a responsive grid layout for inventory items
        inventory_widgets = []
        for item in inventory_items:
            label = QLabel(item)
            inventory_widgets.append(label)
        
        responsive_layout = create_responsive_grid_layout(inventory_widgets, 3, True)
        inventory_group.setLayout(responsive_layout)
        group_layout.addWidget(inventory_group)
        
        # Quest information
        quest_group = QGroupBox(self.tr("Active Quests"))
        quest_layout = QVBoxLayout(quest_group)
        
        quests = [
            (self.tr("Main Quest: Defeat the Dragon"), self.tr("Progress: 2/5 objectives completed")),
            (self.tr("Side Quest: Find the Lost Artifact"), self.tr("Progress: 1/3 objectives completed")),
            (self.tr("Daily Quest: Collect 10 Herbs"), self.tr("Progress: 7/10 collected"))
        ]
        
        for title, progress in quests:
            quest_box = QFrame()
            quest_box.setFrameShape(QFrame.Shape.StyledPanel)
            quest_box_layout = QVBoxLayout(quest_box)
            
            title_label = QLabel(title)
            progress_label = QLabel(progress)
            
            quest_box_layout.addWidget(title_label)
            quest_box_layout.addWidget(progress_label)
            
            quest_layout.addWidget(quest_box)
        
        group_layout.addWidget(quest_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        refresh_button = QPushButton(self.tr("Refresh"))
        details_button = QPushButton(self.tr("View Details"))
        export_button = QPushButton(self.tr("Export State"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([refresh_button, details_button, export_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(details_button)
        button_layout.addWidget(export_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_game_state_details(self) -> QWidget:
        """Create a sample game state details panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        tabs = QTabWidget()
        
        # Player tab
        player_tab = QWidget()
        player_layout = QVBoxLayout(player_tab)
        
        # Player attributes
        attributes_group = QGroupBox(self.tr("Player Attributes"))
        attributes_layout = QFormLayout(attributes_group)
        
        attribute_pairs = [
            (self.tr("Level:"), QLabel("12")),
            (self.tr("Experience:"), QLabel("4,564 / 5,000")),
            (self.tr("Health:"), QLabel("78 / 100")),
            (self.tr("Mana:"), QLabel("45 / 80")),
            (self.tr("Strength:"), QLabel("18")),
            (self.tr("Dexterity:"), QLabel("14")),
            (self.tr("Intelligence:"), QLabel("16")),
            (self.tr("Charisma:"), QLabel("12")),
        ]
        
        for label_text, value_widget in attribute_pairs:
            attributes_layout.addRow(QLabel(label_text), value_widget)
        
        player_layout.addWidget(attributes_group)
        
        # Player skills
        skills_group = QGroupBox(self.tr("Skills"))
        skills_layout = QGridLayout(skills_group)
        
        skills = [
            (self.tr("Swordsmanship"), "Lv. 4"),
            (self.tr("Archery"), "Lv. 2"),
            (self.tr("Magic"), "Lv. 3"),
            (self.tr("Alchemy"), "Lv. 1"),
            (self.tr("Crafting"), "Lv. 5"),
            (self.tr("Persuasion"), "Lv. 2")
        ]
        
        for i, (skill, level) in enumerate(skills):
            row = i // 2
            col = i % 2 * 2
            
            skills_layout.addWidget(QLabel(skill), row, col)
            skills_layout.addWidget(QLabel(level), row, col + 1)
        
        player_layout.addWidget(skills_group)
        player_layout.addStretch(1)
        
        # World tab
        world_tab = QWidget()
        world_layout = QVBoxLayout(world_tab)
        
        # Current location
        location_group = QGroupBox(self.tr("Current Location"))
        location_layout = QVBoxLayout(location_group)
        
        location_info = QLabel(self.tr("You are in the Forest of Despair, a dark and mysterious woodland "
                                     "located in the eastern region of Eldoria. This area is known for "
                                     "its dangerous creatures and valuable resources."))
        location_info.setWordWrap(True)
        
        location_layout.addWidget(location_info)
        world_layout.addWidget(location_group)
        
        # Nearby points of interest
        poi_group = QGroupBox(self.tr("Points of Interest"))
        poi_layout = QVBoxLayout(poi_group)
        
        pois = [
            (self.tr("Ancient Ruins"), self.tr("Distance: 250m NW")),
            (self.tr("Abandoned Mine"), self.tr("Distance: 500m E")),
            (self.tr("Village of Greenfield"), self.tr("Distance: 1.2km S")),
            (self.tr("Mystic Lake"), self.tr("Distance: 800m NE"))
        ]
        
        for name, distance in pois:
            poi_widget = QFrame()
            poi_widget.setFrameShape(QFrame.Shape.StyledPanel)
            poi_layout_inner = QHBoxLayout(poi_widget)
            
            poi_layout_inner.addWidget(QLabel(name), 1)
            poi_layout_inner.addWidget(QLabel(distance))
            
            poi_layout.addWidget(poi_widget)
        
        world_layout.addWidget(poi_group)
        world_layout.addStretch(1)
        
        # Quests tab
        quests_tab = QWidget()
        quests_layout = QVBoxLayout(quests_tab)
        
        # Active quests
        active_quests_group = QGroupBox(self.tr("Active Quests"))
        active_quests_layout = QVBoxLayout(active_quests_group)
        
        quests = [
            {
                "title": self.tr("Defeat the Dragon"),
                "type": self.tr("Main Quest"),
                "description": self.tr("The ancient dragon has awakened and threatens the kingdom. You must gather allies, find the legendary sword, and defeat the beast."),
                "objectives": [
                    (self.tr("Find the knight's guild"), True),
                    (self.tr("Recruit at least 3 allies"), True),
                    (self.tr("Locate the legendary sword"), False),
                    (self.tr("Enter the dragon's lair"), False),
                    (self.tr("Defeat the dragon"), False)
                ]
            },
            {
                "title": self.tr("Find the Lost Artifact"),
                "type": self.tr("Side Quest"),
                "description": self.tr("An ancient artifact of great power has been lost in the Forest of Despair. The scholars need it for their research."),
                "objectives": [
                    (self.tr("Search the old shrine"), True),
                    (self.tr("Decipher the ancient map"), False),
                    (self.tr("Retrieve the artifact"), False)
                ]
            },
            {
                "title": self.tr("Collect 10 Herbs"),
                "type": self.tr("Daily Quest"),
                "description": self.tr("The village healer needs medicinal herbs that grow in the forest. Collect 10 of them to help the sick villagers."),
                "objectives": [
                    (self.tr("Collect red herbs (7/10)"), False)
                ]
            }
        ]
        
        for quest in quests:
            quest_widget = QGroupBox(f"{quest['title']} ({quest['type']})")
            quest_layout = QVBoxLayout(quest_widget)
            
            desc = QLabel(quest["description"])
            desc.setWordWrap(True)
            quest_layout.addWidget(desc)
            
            objectives_label = QLabel(self.tr("Objectives:"))
            quest_layout.addWidget(objectives_label)
            
            for objective, completed in quest["objectives"]:
                obj_layout = QHBoxLayout()
                status = "✓" if completed else "□"
                obj_layout.addWidget(QLabel(f"{status} {objective}"))
                quest_layout.addLayout(obj_layout)
            
            active_quests_layout.addWidget(quest_widget)
        
        quests_layout.addWidget(active_quests_group)
        quests_layout.addStretch(1)
        
        # Add tabs
        tabs.addTab(player_tab, self.tr("Player"))
        tabs.addTab(world_tab, self.tr("World"))
        tabs.addTab(quests_tab, self.tr("Quests"))
        
        layout.addWidget(tabs)
        return container
    
    def create_general_settings(self) -> QWidget:
        """Create a sample general settings panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        group = QGroupBox(self.tr("General Settings"))
        group_layout = QVBoxLayout(group)
        
        # General settings
        form_widget = QWidget()
        labels = [
            QLabel(self.tr("Language:")),
            QLabel(self.tr("Theme:")),
            QLabel(self.tr("Window Size:")),
            QLabel(self.tr("Auto Save Interval:")),
        ]
        
        fields = [
            QComboBox(),
            QComboBox(),
            QComboBox(),
            QSpinBox(),
        ]
        
        # Set up the combo boxes with options
        fields[0].addItems([
            self.tr("English"),
            self.tr("German"),
            self.tr("French"),
            self.tr("Spanish"),
            self.tr("Japanese"),
            self.tr("Chinese")
        ])
        
        fields[1].addItems([
            self.tr("Light"),
            self.tr("Dark"),
            self.tr("System Default"),
            self.tr("Custom")
        ])
        
        fields[2].addItems([
            self.tr("Small (800x600)"),
            self.tr("Medium (1024x768)"),
            self.tr("Large (1280x800)"),
            self.tr("Full Screen")
        ])
        
        # Set up spinbox
        fields[3].setRange(1, 60)
        fields[3].setValue(5)
        fields[3].setSuffix(self.tr(" minutes"))
        
        # Create form layout with labels and fields
        form_layout = create_form_layout(list(zip(labels, fields)))
        form_widget.setLayout(form_layout)
        group_layout.addWidget(form_widget)
        
        # Notification settings
        notification_group = QGroupBox(self.tr("Notifications"))
        notification_layout = QVBoxLayout(notification_group)
        
        checkboxes = [
            QCheckBox(self.tr("Show desktop notifications")),
            QCheckBox(self.tr("Play sound on detection")),
            QCheckBox(self.tr("Show status in system tray")),
            QCheckBox(self.tr("Notify on script completion"))
        ]
        
        for checkbox in checkboxes:
            checkbox.setChecked(True)
            notification_layout.addWidget(checkbox)
        
        group_layout.addWidget(notification_group)
        
        # Data settings
        data_group = QGroupBox(self.tr("Data Management"))
        data_layout = QVBoxLayout(data_group)
        
        data_options = [
            QCheckBox(self.tr("Save detection history")),
            QCheckBox(self.tr("Save screenshots automatically")),
            QCheckBox(self.tr("Collect anonymous usage statistics")),
            QCheckBox(self.tr("Clear cache on exit"))
        ]
        
        for option in data_options:
            data_layout.addWidget(option)
        
        data_options[0].setChecked(True)
        data_options[1].setChecked(True)
        
        group_layout.addWidget(data_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton(self.tr("Save Settings"))
        reset_button = QPushButton(self.tr("Reset to Defaults"))
        export_button = QPushButton(self.tr("Export Settings"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([save_button, reset_button, export_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(save_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(export_button)
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
        return container
    
    def create_advanced_settings(self) -> QWidget:
        """Create a sample advanced settings panel for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        warning_label = QLabel(self.tr("Warning: These settings should only be modified by advanced users. "
                                      "Incorrect settings may cause the application to malfunction."))
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning_label)
        
        tabs = QTabWidget()
        
        # Performance tab
        performance_tab = QWidget()
        performance_layout = QVBoxLayout(performance_tab)
        
        performance_form = QWidget()
        performance_labels = [
            QLabel(self.tr("Processing Threads:")),
            QLabel(self.tr("Memory Usage Limit:")),
            QLabel(self.tr("Detection Frequency:")),
            QLabel(self.tr("Image Processing Quality:")),
        ]
        
        performance_fields = [
            QSpinBox(),
            QComboBox(),
            QSpinBox(),
            QComboBox(),
        ]
        
        # Set up controls
        performance_fields[0].setRange(1, 16)
        performance_fields[0].setValue(4)
        
        performance_fields[1].addItems([
            self.tr("512 MB"),
            self.tr("1 GB"),
            self.tr("2 GB"),
            self.tr("4 GB"),
            self.tr("Unlimited")
        ])
        
        performance_fields[2].setRange(1, 120)
        performance_fields[2].setValue(30)
        performance_fields[2].setSuffix(self.tr(" fps"))
        
        performance_fields[3].addItems([
            self.tr("Low (Fastest)"),
            self.tr("Medium"),
            self.tr("High"),
            self.tr("Ultra (Slowest)")
        ])
        
        # Create form layout
        performance_form_layout = create_form_layout(list(zip(performance_labels, performance_fields)))
        performance_form.setLayout(performance_form_layout)
        performance_layout.addWidget(performance_form)
        
        # Add some performance-related checkboxes
        performance_checks = [
            QCheckBox(self.tr("Use GPU acceleration if available")),
            QCheckBox(self.tr("Enable multi-threading")),
            QCheckBox(self.tr("Disable animations for better performance")),
            QCheckBox(self.tr("Prefer performance over accuracy"))
        ]
        
        for check in performance_checks:
            performance_layout.addWidget(check)
        
        performance_checks[0].setChecked(True)
        performance_checks[1].setChecked(True)
        
        performance_layout.addStretch(1)
        
        # Debug tab
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)
        
        debug_form = QWidget()
        debug_labels = [
            QLabel(self.tr("Log Level:")),
            QLabel(self.tr("Log File Size:")),
            QLabel(self.tr("Debug Mode:")),
            QLabel(self.tr("Debug Port:")),
        ]
        
        debug_fields = [
            QComboBox(),
            QComboBox(),
            QComboBox(),
            QSpinBox(),
        ]
        
        # Set up controls
        debug_fields[0].addItems([
            self.tr("Error"),
            self.tr("Warning"),
            self.tr("Info"),
            self.tr("Debug"),
            self.tr("Verbose")
        ])
        
        debug_fields[1].addItems([
            self.tr("1 MB"),
            self.tr("5 MB"),
            self.tr("10 MB"),
            self.tr("50 MB"),
            self.tr("Unlimited")
        ])
        
        debug_fields[2].addItems([
            self.tr("Disabled"),
            self.tr("Basic"),
            self.tr("Advanced"),
            self.tr("Developer")
        ])
        
        debug_fields[3].setRange(1024, 65535)
        debug_fields[3].setValue(8080)
        
        # Create form layout
        debug_form_layout = create_form_layout(list(zip(debug_labels, debug_fields)))
        debug_form.setLayout(debug_form_layout)
        debug_layout.addWidget(debug_form)
        
        # Debug actions
        debug_actions_group = QGroupBox(self.tr("Debug Actions"))
        debug_actions_layout = QVBoxLayout(debug_actions_group)
        
        debug_buttons = [
            QPushButton(self.tr("Generate Debug Report")),
            QPushButton(self.tr("Clear Application Cache")),
            QPushButton(self.tr("Reset All Settings")),
            QPushButton(self.tr("Check for Memory Leaks"))
        ]
        
        for button in debug_buttons:
            debug_actions_layout.addWidget(button)
        
        debug_layout.addWidget(debug_actions_group)
        debug_layout.addStretch(1)
        
        # Add tabs
        tabs.addTab(performance_tab, self.tr("Performance"))
        tabs.addTab(debug_tab, self.tr("Debug"))
        
        layout.addWidget(tabs, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton(self.tr("Apply"))
        cancel_button = QPushButton(self.tr("Cancel"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([apply_button, cancel_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        return container
    
    def create_about_dialog(self) -> QWidget:
        """Create a sample about dialog for testing."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        title_label = QLabel("Scout")
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        version_label = QLabel(self.tr("Version 1.0.0"))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        description = QLabel(self.tr("A powerful tool for screen analysis, "
                                   "object detection, and game state visualization. "
                                   "Scout helps you automate tasks and analyze game information."))
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        layout.addSpacing(20)
        
        copyright_label = QLabel(self.tr("© 2023 Scout Team. All rights reserved."))
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)
        
        layout.addSpacing(10)
        
        links_label = QLabel('<a href="https://www.scout-app.com">www.scout-app.com</a> | '
                           '<a href="https://github.com/scout-team/scout">GitHub</a> | '
                           '<a href="mailto:info@scout-app.com">Contact</a>')
        links_label.setOpenExternalLinks(True)
        links_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(links_label)
        
        layout.addStretch(1)
        
        # Credits
        credits_group = QGroupBox(self.tr("Credits"))
        credits_layout = QVBoxLayout(credits_group)
        
        credits_text = QLabel(self.tr("Developed by: Scout Team\n"
                                     "UI Design: Jane Doe\n"
                                     "Detection Engine: John Smith\n"
                                     "Testing: The Amazing QA Team"))
        credits_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_layout.addWidget(credits_text)
        
        layout.addWidget(credits_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton(self.tr("OK"))
        more_info_button = QPushButton(self.tr("More Information"))
        
        # Use layout helper to make buttons consistent
        adjust_button_sizes([ok_button, more_info_button])
        
        button_layout.addStretch(1)
        button_layout.addWidget(more_info_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        
        return container
    
    def change_language(self, index: int) -> None:
        """Change the application language."""
        lang_code = self.language_combo.itemData(index)
        if not lang_code or lang_code == self.current_language:
            return
        
        logging.info(f"Changing language to {lang_code}")
        self.current_language = lang_code
        
        # Apply translator
        app = QApplication.instance()
        
        # Remove current translators
        for translator in self.translators.values():
            app.removeTranslator(translator)
        
        # Install new translator
        if lang_code in self.translators:
            app.installTranslator(self.translators[lang_code])
        
        # Update UI
        self.retranslate_ui()
        self.update_status_bar()
        
        # Update the preview if there's a component displayed
        if self.preview_widget.component:
            # Get the selected component
            item = self.tree_widget.currentItem()
            if item:
                component_id = item.data(0, Qt.ItemDataRole.UserRole)
                if component_id:
                    # Recreate the component with the new language
                    component = self.create_component(component_id)
                    if component:
                        self.preview_widget.set_component(component)
    
    def retranslate_ui(self) -> None:
        """Update the UI text after a language change."""
        self.setWindowTitle(self.tr("Scout Translator Tool"))
        
        # Update checkboxes
        self.show_borders_checkbox.setText(self.tr("Show Component Borders"))
        self.highlight_issues_checkbox.setText(self.tr("Highlight Potential Issues"))
        self.screenshot_button.setText(self.tr("Save Screenshot"))
        
        # Update tree widget
        self.tree_widget.setHeaderLabel(self.tr("UI Components"))
        
        # Recreate the tree items
        self.tree_widget.clear()
        self.populate_component_tree()
        
        # Update status bar
        self.update_status_bar()
    
    def toggle_borders(self, show: bool) -> None:
        """Toggle showing widget borders in the preview."""
        self.preview_widget.set_show_borders(show)
    
    def toggle_highlight(self, highlight: bool) -> None:
        """Toggle highlighting potential layout issues in the preview."""
        self.preview_widget.set_highlight_issues(highlight)
    
    def update_status_bar(self) -> None:
        """Update the status bar with current language information."""
        expansion_factor = get_expansion_factor()
        lang_name = QLocale(self.current_language).nativeLanguageName()
        
        status_text = self.tr("Current Language: {0} ({1}) - Expansion Factor: {2:.2f}").format(
            lang_name, self.current_language, expansion_factor
        )
        
        self.status_bar.showMessage(status_text)
    
    def save_screenshot(self) -> None:
        """Save a screenshot of the current preview."""
        if not self.preview_widget.component:
            self.status_bar.showMessage(self.tr("No component to capture"))
            return
        
        # Get a suggested filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"scout_ui_{self.current_language}_{timestamp}.png"
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Screenshot"),
            default_filename,
            self.tr("PNG Files (*.png);;All Files (*)")
        )
        
        if not file_path:
            return
        
        # Capture the component
        pixmap = self.preview_widget.grab()
        if pixmap.save(file_path, "PNG"):
            self.status_bar.showMessage(self.tr("Screenshot saved to {0}").format(file_path))
        else:
            self.status_bar.showMessage(self.tr("Failed to save screenshot"))


def main():
    """Main entry point for the translator application."""
    app = QApplication(sys.argv)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Create and show the main window
    window = TranslatorApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 