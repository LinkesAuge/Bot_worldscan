"""
Settings Tab Module

This module provides the settings tab for the Scout application.
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QHBoxLayout, QGroupBox, QFormLayout,
                             QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox,
                             QLineEdit, QFileDialog, QMessageBox, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui import QIcon

from scout.ui.utils.language_manager import tr, get_language_manager, Language
from scout.ui.service_locator_ui import ServiceLocator
from scout.ui.models.settings_model import SettingsModel
from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes
from scout.core.interfaces.service_interfaces import (
    WindowServiceInterface, DetectionServiceInterface, 
    AutomationServiceInterface
)

# Set up logging
logger = logging.getLogger(__name__)

class SettingsTab(QWidget):
    """
    Tab for configuring application settings.
    
    This tab provides an interface for customizing detection parameters,
    automation behavior, appearance settings, and other application preferences.
    """
    
    # Signal emitted when settings are changed
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, service_locator: ServiceLocator):
        """
        Initialize the settings tab.
        
        Args:
            service_locator: Service locator for accessing services
        """
        super().__init__()
        
        # Store service locator
        self.service_locator = service_locator
        
        # Get services
        self.window_service = service_locator.get(WindowServiceInterface)
        self.detection_service = service_locator.get(DetectionServiceInterface)
        self.automation_service = service_locator.get(AutomationServiceInterface)
        
        # Create settings model
        self.settings_model = SettingsModel()
        
        # Flag to prevent signals when bulk updating the UI
        self._updating_ui = False
        
        # Initialize state
        self._settings = QSettings("ScoutTeam", "Scout")
        self._modified = False
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Load settings to UI
        self._load_settings_to_ui()
        
        # Start periodic auto-save timer 
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self._auto_save_settings)
        self.save_timer.start(30000)  # Auto-save every 30 seconds if changes were made
        
        logger.info("Settings tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create General Settings tab
        self._create_general_settings_tab()
        
        # Create Detection Settings tab
        self._create_detection_settings_tab()
        
        # Create Automation Settings tab
        self._create_automation_settings_tab()
        
        # Create Appearance Settings tab
        self._create_appearance_settings_tab()
        
        # Create button bar
        button_bar = QHBoxLayout()
        
        # Add spacer to push buttons right
        button_bar.addStretch()
        
        # Create buttons
        self.save_button = QPushButton(tr("Save Settings"))
        self.save_button.setIcon(QIcon.fromTheme("document-save"))
        self.save_button.clicked.connect(lambda: self._on_save_clicked(True))
        button_bar.addWidget(self.save_button)
        
        self.reset_button = QPushButton(tr("Reset to Defaults"))
        self.reset_button.setIcon(QIcon.fromTheme("edit-undo"))
        self.reset_button.clicked.connect(self._on_reset_clicked)
        button_bar.addWidget(self.reset_button)
        
        # Create status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #FF6600;")  # Orange color for visibility
        
        # Add status label and button bar to main layout
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(button_bar)
        
        # Adjust button sizes for different languages
        adjust_button_sizes([self.save_button, self.reset_button])
    
    def _create_general_settings_tab(self) -> None:
        """Create the general settings tab."""
        general_tab = QWidget()
        layout = QVBoxLayout(general_tab)
        
        # Add general settings groups
        language_group = QGroupBox(tr("Language"))
        language_layout = QFormLayout(language_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItem(tr("System Default"), "system")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Deutsch", "de")
        self.language_combo.currentIndexChanged.connect(self._mark_settings_changed)
        
        language_layout.addRow(tr("Interface Language:"), self.language_combo)
        layout.addWidget(language_group)
        
        # Add paths group
        paths_group = QGroupBox(tr("File Paths"))
        paths_layout = QFormLayout(paths_group)
        
        self.templates_path = QLineEdit()
        self.templates_path.textChanged.connect(self._mark_settings_changed)
        
        browse_templates = QPushButton(tr("Browse"))
        browse_templates.clicked.connect(lambda: self._browse_directory(self.templates_path))
        
        templates_layout = QHBoxLayout()
        templates_layout.addWidget(self.templates_path)
        templates_layout.addWidget(browse_templates)
        
        paths_layout.addRow(tr("Templates Directory:"), templates_layout)
        layout.addWidget(paths_group)
        
        # Add spacer
        layout.addStretch()
        
        # Add to tabs
        self.tabs.addTab(general_tab, tr("General"))
    
    def _create_detection_settings_tab(self) -> None:
        """Create the detection settings tab."""
        detection_tab = QWidget()
        layout = QVBoxLayout(detection_tab)
        
        # Template matching group
        template_group = QGroupBox(tr("Template Matching"))
        template_layout = QFormLayout(template_group)
        
        self.confidence_threshold = QDoubleSpinBox()
        self.confidence_threshold.setRange(0.1, 1.0)
        self.confidence_threshold.setSingleStep(0.05)
        self.confidence_threshold.setValue(0.7)
        self.confidence_threshold.valueChanged.connect(self._mark_settings_changed)
        
        template_layout.addRow(tr("Confidence Threshold:"), self.confidence_threshold)
        
        self.max_results = QSpinBox()
        self.max_results.setRange(1, 100)
        self.max_results.setValue(10)
        self.max_results.valueChanged.connect(self._mark_settings_changed)
        
        template_layout.addRow(tr("Maximum Results:"), self.max_results)
        
        layout.addWidget(template_group)
        
        # OCR group
        ocr_group = QGroupBox(tr("OCR Settings"))
        ocr_layout = QFormLayout(ocr_group)
        
        self.ocr_language = QComboBox()
        self.ocr_language.addItem("English", "eng")
        self.ocr_language.addItem("German", "deu")
        self.ocr_language.currentIndexChanged.connect(self._mark_settings_changed)
        
        ocr_layout.addRow(tr("OCR Language:"), self.ocr_language)
        
        layout.addWidget(ocr_group)
        
        # Add spacer
        layout.addStretch()
        
        # Add to tabs
        self.tabs.addTab(detection_tab, tr("Detection"))
    
    def _create_automation_settings_tab(self) -> None:
        """Create the automation settings tab."""
        automation_tab = QWidget()
        layout = QVBoxLayout(automation_tab)
        
        # General automation group
        general_group = QGroupBox(tr("General"))
        general_layout = QFormLayout(general_group)
        
        self.action_delay = QSpinBox()
        self.action_delay.setRange(0, 5000)
        self.action_delay.setSingleStep(50)
        self.action_delay.setSuffix(" ms")
        self.action_delay.setValue(200)
        self.action_delay.valueChanged.connect(self._mark_settings_changed)
        
        general_layout.addRow(tr("Action Delay:"), self.action_delay)
        
        self.enable_sounds = QCheckBox(tr("Enable Sound Effects"))
        self.enable_sounds.setChecked(True)
        self.enable_sounds.toggled.connect(self._mark_settings_changed)
        
        general_layout.addRow("", self.enable_sounds)
        
        layout.addWidget(general_group)
        
        # Safety group
        safety_group = QGroupBox(tr("Safety"))
        safety_layout = QFormLayout(safety_group)
        
        self.confirm_actions = QCheckBox(tr("Confirm Destructive Actions"))
        self.confirm_actions.setChecked(True)
        self.confirm_actions.toggled.connect(self._mark_settings_changed)
        
        safety_layout.addRow("", self.confirm_actions)
        
        self.emergency_stop_key = QComboBox()
        self.emergency_stop_key.addItem("Escape", "Escape")
        self.emergency_stop_key.addItem("F12", "F12")
        self.emergency_stop_key.addItem("Ctrl+Q", "Ctrl+Q")
        self.emergency_stop_key.currentIndexChanged.connect(self._mark_settings_changed)
        
        safety_layout.addRow(tr("Emergency Stop Key:"), self.emergency_stop_key)
        
        layout.addWidget(safety_group)
        
        # Add spacer
        layout.addStretch()
        
        # Add to tabs
        self.tabs.addTab(automation_tab, tr("Automation"))
    
    def _create_appearance_settings_tab(self) -> None:
        """Create the appearance settings tab."""
        appearance_tab = QWidget()
        layout = QVBoxLayout(appearance_tab)
        
        # Theme group
        theme_group = QGroupBox(tr("Theme"))
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("System"), "system")
        self.theme_combo.addItem(tr("Light"), "light")
        self.theme_combo.addItem(tr("Dark"), "dark")
        self.theme_combo.currentIndexChanged.connect(self._mark_settings_changed)
        
        theme_layout.addRow(tr("Application Theme:"), self.theme_combo)
        
        layout.addWidget(theme_group)
        
        # Overlay group
        overlay_group = QGroupBox(tr("Detection Overlay"))
        overlay_layout = QFormLayout(overlay_group)
        
        self.show_overlay = QCheckBox(tr("Show Overlay"))
        self.show_overlay.setChecked(True)
        self.show_overlay.toggled.connect(self._mark_settings_changed)
        
        overlay_layout.addRow("", self.show_overlay)
        
        self.show_confidence = QCheckBox(tr("Show Confidence Values"))
        self.show_confidence.setChecked(True)
        self.show_confidence.toggled.connect(self._mark_settings_changed)
        
        overlay_layout.addRow("", self.show_confidence)
        
        layout.addWidget(overlay_group)
        
        # Add spacer
        layout.addStretch()
        
        # Add to tabs
        self.tabs.addTab(appearance_tab, tr("Appearance"))
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        try:
            # Connect UI change signals
            self.language_combo.currentIndexChanged.connect(self._mark_settings_changed)
            self.templates_path.textChanged.connect(self._mark_settings_changed)
            self.confidence_threshold.valueChanged.connect(self._mark_settings_changed)
            self.max_results.valueChanged.connect(self._mark_settings_changed)
            self.ocr_language.currentIndexChanged.connect(self._mark_settings_changed)
            self.action_delay.valueChanged.connect(self._mark_settings_changed)
            self.enable_sounds.toggled.connect(self._mark_settings_changed)
            self.confirm_actions.toggled.connect(self._mark_settings_changed)
            self.emergency_stop_key.currentIndexChanged.connect(self._mark_settings_changed)
            self.theme_combo.currentIndexChanged.connect(self._mark_settings_changed)
            self.show_overlay.toggled.connect(self._mark_settings_changed)
            self.show_confidence.toggled.connect(self._mark_settings_changed)
            
            logger.debug("Settings tab signals connected")
        except Exception as e:
            logger.error(f"Error connecting settings tab signals: {e}")
    
    def _load_settings_to_ui(self) -> None:
        """Load settings to UI components."""
        try:
            self._updating_ui = True
            
            # Load language settings
            language = self.settings_model.get_setting("general", "language", "system")
            index = self.language_combo.findData(language)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
            
            # Load path settings
            templates_path = self.settings_model.get_setting("general", "templates_path", "")
            self.templates_path.setText(templates_path)
            
            # Load detection settings
            confidence = self.settings_model.get_setting("detection", "confidence_threshold", 0.7)
            self.confidence_threshold.setValue(confidence)
            
            max_results = self.settings_model.get_setting("detection", "max_results", 10)
            self.max_results.setValue(max_results)
            
            ocr_lang = self.settings_model.get_setting("detection", "ocr_language", "eng")
            index = self.ocr_language.findData(ocr_lang)
            if index >= 0:
                self.ocr_language.setCurrentIndex(index)
            
            # Load automation settings
            action_delay = self.settings_model.get_setting("automation", "action_delay", 200)
            self.action_delay.setValue(action_delay)
            
            enable_sounds = self.settings_model.get_setting("automation", "enable_sounds", True)
            self.enable_sounds.setChecked(enable_sounds)
            
            confirm_actions = self.settings_model.get_setting("automation", "confirm_actions", True)
            self.confirm_actions.setChecked(confirm_actions)
            
            emergency_key = self.settings_model.get_setting("automation", "emergency_stop_key", "Escape")
            index = self.emergency_stop_key.findData(emergency_key)
            if index >= 0:
                self.emergency_stop_key.setCurrentIndex(index)
            
            # Load appearance settings
            theme = self.settings_model.get_setting("appearance", "theme", "system")
            index = self.theme_combo.findData(theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
            
            show_overlay = self.settings_model.get_setting("appearance", "show_overlay", True)
            self.show_overlay.setChecked(show_overlay)
            
            show_confidence = self.settings_model.get_setting("appearance", "show_confidence", True)
            self.show_confidence.setChecked(show_confidence)
            
            logger.debug("Settings loaded to UI")
        except Exception as e:
            logger.error(f"Error loading settings to UI: {e}")
        finally:
            self._updating_ui = False
            self._modified = False
            
            # Update status
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText("")
            
            # Update save button
            if hasattr(self, 'save_button') and self.save_button is not None:
                self.save_button.setEnabled(False)
    
    def _browse_directory(self, line_edit: QLineEdit) -> None:
        """
        Open file dialog to browse for a directory.
        
        Args:
            line_edit: Line edit to update with selected directory
        """
        current_path = line_edit.text()
        if not current_path:
            current_path = str(Path.home())
            
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Select Directory"),
            current_path,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            line_edit.setText(directory)
    
    def _mark_settings_changed(self) -> None:
        """Mark settings as modified."""
        if self._updating_ui:
            return
        
        self._modified = True
        
        # Update save button if it exists
        if hasattr(self, 'save_button') and self.save_button is not None:
            self.save_button.setEnabled(True)
        
        # Update status label if it exists
        if hasattr(self, 'status_label') and self.status_label is not None:
            self.status_label.setText(tr("Settings have been modified (not saved)"))
    
    def _auto_save_settings(self) -> None:
        """Auto-save settings if they have been modified."""
        # Check if settings have been modified
        try:
            # Check modified flag first
            if self._modified:
                logger.debug("Auto-saving modified settings")
                self._on_save_clicked(show_dialog=False)
            # As a fallback, check the status label text
            elif hasattr(self, 'status_label') and self.status_label is not None and self.status_label.text() == tr("Settings have been modified (not saved)"):
                logger.debug("Auto-saving settings based on status label")
                self._on_save_clicked(show_dialog=False)
        except Exception as e:
            # Log exception but don't crash
            logger.error(f"Error in auto-save settings: {str(e)}")
    
    def _on_save_clicked(self, show_dialog: bool = True) -> None:
        """
        Save settings and optionally show confirmation dialog.
        
        Args:
            show_dialog: Whether to show a confirmation dialog
        """
        try:
            # Collect settings from UI
            self._collect_settings_from_ui()
            
            # Save settings
            self.settings_model.save_settings()
            
            # Reset modified flag
            self._modified = False
            
            # Clear status label
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText("")
            
            # Disable save button
            if hasattr(self, 'save_button') and self.save_button is not None:
                self.save_button.setEnabled(False)
            
            # Emit settings changed signal
            self.settings_changed.emit(self.settings_model.get_all_settings())
            
            # Show confirmation dialog if requested
            if show_dialog:
                QMessageBox.information(
                    self,
                    tr("Settings Saved"),
                    tr("Your settings have been saved successfully."),
                    QMessageBox.StandardButton.Ok
                )
                
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            if show_dialog:
                QMessageBox.critical(
                    self,
                    tr("Error"),
                    tr("Failed to save settings: {0}").format(str(e)),
                    QMessageBox.StandardButton.Ok
                )
    
    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        try:
            # Ask for confirmation
            result = QMessageBox.question(
                self,
                tr("Reset Settings"),
                tr("Are you sure you want to reset all settings to their default values?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                # Reset settings in model
                self.settings_model.reset_to_defaults()
                
                # Reload UI from model
                self._load_settings_to_ui()
                
                # Notify about change
                self.settings_changed.emit(self.settings_model.get_all_settings())
                
                logger.info("Settings reset to defaults")
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
    
    def _collect_settings_from_ui(self) -> None:
        """Collect settings from UI components."""
        try:
            # General settings
            language = self.language_combo.currentData()
            self.settings_model.set_setting("general", "language", language)
            
            templates_path = self.templates_path.text()
            self.settings_model.set_setting("general", "templates_path", templates_path)
            
            # Detection settings
            confidence = self.confidence_threshold.value()
            self.settings_model.set_setting("detection", "confidence_threshold", confidence)
            
            max_results = self.max_results.value()
            self.settings_model.set_setting("detection", "max_results", max_results)
            
            ocr_lang = self.ocr_language.currentData()
            self.settings_model.set_setting("detection", "ocr_language", ocr_lang)
            
            # Automation settings
            action_delay = self.action_delay.value()
            self.settings_model.set_setting("automation", "action_delay", action_delay)
            
            enable_sounds = self.enable_sounds.isChecked()
            self.settings_model.set_setting("automation", "enable_sounds", enable_sounds)
            
            confirm_actions = self.confirm_actions.isChecked()
            self.settings_model.set_setting("automation", "confirm_actions", confirm_actions)
            
            emergency_key = self.emergency_stop_key.currentData()
            self.settings_model.set_setting("automation", "emergency_stop_key", emergency_key)
            
            # Appearance settings
            theme = self.theme_combo.currentData()
            self.settings_model.set_setting("appearance", "theme", theme)
            
            show_overlay = self.show_overlay.isChecked()
            self.settings_model.set_setting("appearance", "show_overlay", show_overlay)
            
            show_confidence = self.show_confidence.isChecked()
            self.settings_model.set_setting("appearance", "show_confidence", show_confidence)
            
            logger.debug("Settings collected from UI")
        except Exception as e:
            logger.error(f"Error collecting settings from UI: {e}")
            raise
