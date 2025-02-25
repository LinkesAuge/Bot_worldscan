"""
Settings Tab

This module provides a tab interface for configuring application settings.
It allows users to customize detection parameters, automation behavior,
appearance settings, and other application preferences.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QTabWidget, QSlider, QColorDialog, QDialog,
    QDialogButtonBox, QFormLayout
)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings

# Set up logging
logger = logging.getLogger(__name__)

class SettingsModel:
    """
    Model for managing application settings.
    
    This class provides methods for loading, saving, and validating settings
    for the Scout application.
    """
    
    # Default settings
    DEFAULT_SETTINGS = {
        "detection": {
            "template_matching": {
                "method": "cv2.TM_CCOEFF_NORMED",
                "confidence_threshold": 0.8,
                "max_results": 5,
                "use_grayscale": True,
                "use_edge_detection": False
            },
            "ocr": {
                "engine": "tesseract",
                "language": "eng",
                "confidence_threshold": 0.6,
                "allow_whitespace": True,
                "preprocessing": "threshold"
            },
            "yolo": {
                "model": "yolov8n.pt",
                "confidence_threshold": 0.5,
                "overlap_threshold": 0.45,
                "use_gpu": True
            }
        },
        "automation": {
            "click_delay": 100,
            "typing_speed": "normal",
            "default_wait_time": 500,
            "error_handling": "pause",
            "max_retries": 3
        },
        "window": {
            "capture_method": "win32",
            "region_padding": 5,
            "capture_interval": 200,
            "highlight_color": "#00FF00",
            "auto_focus": True
        },
        "ui": {
            "theme": "system",
            "font_size": 10,
            "show_tooltips": True,
            "confirm_actions": True,
            "show_debug_info": False
        },
        "paths": {
            "templates_dir": "./scout/resources/templates",
            "state_dir": "./scout/resources/states",
            "logs_dir": "./scout/resources/logs",
            "sequences_dir": "./scout/resources/sequences"
        }
    }
    
    def __init__(self):
        """Initialize the settings model."""
        # Initialize settings
        self.settings = self.DEFAULT_SETTINGS.copy()
        
        # Settings file path
        self.settings_file = Path("./scout/settings.json")
        
        # Initialize QSettings for persistent storage
        self.qsettings = QSettings("ScoutTeam", "Scout")
        
        # Load settings
        self.load_settings()
        
        logger.info("Settings model initialized")
    
    def load_settings(self) -> bool:
        """
        Load settings from file or QSettings.
        
        Returns:
            bool: True if settings were loaded successfully, False otherwise
        """
        # Try to load from file first
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                
                # Merge with default settings to handle missing values
                self._merge_settings(loaded_settings)
                
                logger.info(f"Settings loaded from {self.settings_file}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load settings from file: {str(e)}")
        
        # If file loading failed, try QSettings
        try:
            if self.qsettings.contains("settings"):
                settings_json = self.qsettings.value("settings")
                loaded_settings = json.loads(settings_json)
                
                # Merge with default settings to handle missing values
                self._merge_settings(loaded_settings)
                
                logger.info("Settings loaded from QSettings")
                return True
                
        except Exception as e:
            logger.error(f"Failed to load settings from QSettings: {str(e)}")
        
        # If both methods failed, use default settings
        logger.warning("Using default settings")
        return False
    
    def save_settings(self) -> bool:
        """
        Save settings to file and QSettings.
        
        Returns:
            bool: True if settings were saved successfully, False otherwise
        """
        # Ensure settings directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info(f"Settings saved to {self.settings_file}")
            
        except Exception as e:
            logger.error(f"Failed to save settings to file: {str(e)}")
            return False
        
        # Save to QSettings
        try:
            settings_json = json.dumps(self.settings)
            self.qsettings.setValue("settings", settings_json)
            
            logger.info("Settings saved to QSettings")
            
        except Exception as e:
            logger.error(f"Failed to save settings to QSettings: {str(e)}")
            return False
        
        return True
    
    def get_setting(self, category: str, subcategory: str, key: str) -> Any:
        """
        Get a specific setting value.
        
        Args:
            category: Main category (e.g., "detection")
            subcategory: Subcategory (e.g., "template_matching")
            key: Setting key (e.g., "confidence_threshold")
            
        Returns:
            Setting value or None if not found
        """
        try:
            return self.settings[category][subcategory][key]
        except KeyError:
            logger.warning(f"Setting not found: {category}.{subcategory}.{key}")
            return None
    
    def set_setting(self, category: str, subcategory: str, key: str, value: Any) -> bool:
        """
        Set a specific setting value.
        
        Args:
            category: Main category (e.g., "detection")
            subcategory: Subcategory (e.g., "template_matching")
            key: Setting key (e.g., "confidence_threshold")
            value: New value for the setting
            
        Returns:
            bool: True if setting was updated successfully, False otherwise
        """
        try:
            # Ensure categories exist
            if category not in self.settings:
                self.settings[category] = {}
            
            if subcategory not in self.settings[category]:
                self.settings[category][subcategory] = {}
            
            # Update setting
            self.settings[category][subcategory][key] = value
            
            logger.debug(f"Setting updated: {category}.{subcategory}.{key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update setting: {str(e)}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        logger.info("Settings reset to defaults")
    
    def _merge_settings(self, loaded_settings: Dict) -> None:
        """
        Merge loaded settings with default settings to handle missing values.
        
        Args:
            loaded_settings: Settings loaded from file or QSettings
        """
        # Iterate through default settings structure
        for category, category_data in self.DEFAULT_SETTINGS.items():
            if category not in loaded_settings:
                loaded_settings[category] = category_data
                continue
            
            for subcategory, subcategory_data in category_data.items():
                if subcategory not in loaded_settings[category]:
                    loaded_settings[category][subcategory] = subcategory_data
                    continue
                
                for key, default_value in subcategory_data.items():
                    if key not in loaded_settings[category][subcategory]:
                        loaded_settings[category][subcategory][key] = default_value
        
        # Update settings with merged data
        self.settings = loaded_settings


class SettingsTab(QWidget):
    """
    Tab for configuring application settings.
    
    This tab provides an interface for customizing detection parameters,
    automation behavior, appearance settings, and other application preferences.
    """
    
    # Signal emitted when settings are changed
    settings_changed = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize the settings tab."""
        super().__init__()
        
        # Create settings model
        self.settings_model = SettingsModel()
        
        # Create UI components
        self._create_ui()
        
        # Load settings into UI
        self._load_settings_to_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Settings tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs for setting categories
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create individual setting tabs
        self._create_detection_tab()
        self._create_automation_tab()
        self._create_window_tab()
        self._create_ui_tab()
        self._create_paths_tab()
        
        # Create buttons
        buttons_layout = QHBoxLayout()
        
        # Save button
        self.save_btn = QPushButton("Save Settings")
        buttons_layout.addWidget(self.save_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset to Defaults")
        buttons_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(buttons_layout)
    
    def _create_detection_tab(self) -> None:
        """Create the detection settings tab."""
        detection_tab = QWidget()
        self.tabs.addTab(detection_tab, "Detection")
        
        # Create layout
        layout = QVBoxLayout(detection_tab)
        
        # Create tabs for detection methods
        detection_tabs = QTabWidget()
        layout.addWidget(detection_tabs)
        
        # Template matching settings
        template_tab = QWidget()
        template_layout = QFormLayout(template_tab)
        
        # Method
        self.template_method = QComboBox()
        self.template_method.addItems([
            "cv2.TM_CCOEFF_NORMED",
            "cv2.TM_CCORR_NORMED",
            "cv2.TM_SQDIFF_NORMED"
        ])
        template_layout.addRow("Matching Method:", self.template_method)
        
        # Confidence threshold
        self.template_confidence = QSlider(Qt.Orientation.Horizontal)
        self.template_confidence.setRange(0, 100)
        self.template_confidence.setValue(80)  # Default 0.8
        self.template_confidence_label = QLabel("0.80")
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(self.template_confidence)
        confidence_layout.addWidget(self.template_confidence_label)
        template_layout.addRow("Confidence Threshold:", confidence_layout)
        
        # Max results
        self.template_max_results = QSpinBox()
        self.template_max_results.setRange(1, 100)
        self.template_max_results.setValue(5)
        template_layout.addRow("Maximum Results:", self.template_max_results)
        
        # Use grayscale
        self.template_grayscale = QCheckBox()
        self.template_grayscale.setChecked(True)
        template_layout.addRow("Use Grayscale:", self.template_grayscale)
        
        # Use edge detection
        self.template_edge = QCheckBox()
        self.template_edge.setChecked(False)
        template_layout.addRow("Use Edge Detection:", self.template_edge)
        
        detection_tabs.addTab(template_tab, "Template Matching")
        
        # OCR settings
        ocr_tab = QWidget()
        ocr_layout = QFormLayout(ocr_tab)
        
        # Engine
        self.ocr_engine = QComboBox()
        self.ocr_engine.addItems(["tesseract", "easyocr"])
        ocr_layout.addRow("OCR Engine:", self.ocr_engine)
        
        # Language
        self.ocr_language = QComboBox()
        self.ocr_language.addItems(["eng", "deu", "fra", "spa", "ita"])
        ocr_layout.addRow("Language:", self.ocr_language)
        
        # Confidence threshold
        self.ocr_confidence = QSlider(Qt.Orientation.Horizontal)
        self.ocr_confidence.setRange(0, 100)
        self.ocr_confidence.setValue(60)  # Default 0.6
        self.ocr_confidence_label = QLabel("0.60")
        ocr_confidence_layout = QHBoxLayout()
        ocr_confidence_layout.addWidget(self.ocr_confidence)
        ocr_confidence_layout.addWidget(self.ocr_confidence_label)
        ocr_layout.addRow("Confidence Threshold:", ocr_confidence_layout)
        
        # Allow whitespace
        self.ocr_whitespace = QCheckBox()
        self.ocr_whitespace.setChecked(True)
        ocr_layout.addRow("Allow Whitespace:", self.ocr_whitespace)
        
        # Preprocessing
        self.ocr_preprocessing = QComboBox()
        self.ocr_preprocessing.addItems(["none", "threshold", "blur", "sharpen"])
        ocr_layout.addRow("Preprocessing:", self.ocr_preprocessing)
        
        detection_tabs.addTab(ocr_tab, "OCR")
        
        # YOLO settings
        yolo_tab = QWidget()
        yolo_layout = QFormLayout(yolo_tab)
        
        # Model
        self.yolo_model = QComboBox()
        self.yolo_model.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt"])
        yolo_layout.addRow("YOLO Model:", self.yolo_model)
        
        # Confidence threshold
        self.yolo_confidence = QSlider(Qt.Orientation.Horizontal)
        self.yolo_confidence.setRange(0, 100)
        self.yolo_confidence.setValue(50)  # Default 0.5
        self.yolo_confidence_label = QLabel("0.50")
        yolo_confidence_layout = QHBoxLayout()
        yolo_confidence_layout.addWidget(self.yolo_confidence)
        yolo_confidence_layout.addWidget(self.yolo_confidence_label)
        yolo_layout.addRow("Confidence Threshold:", yolo_confidence_layout)
        
        # Overlap threshold
        self.yolo_overlap = QSlider(Qt.Orientation.Horizontal)
        self.yolo_overlap.setRange(0, 100)
        self.yolo_overlap.setValue(45)  # Default 0.45
        self.yolo_overlap_label = QLabel("0.45")
        yolo_overlap_layout = QHBoxLayout()
        yolo_overlap_layout.addWidget(self.yolo_overlap)
        yolo_overlap_layout.addWidget(self.yolo_overlap_label)
        yolo_layout.addRow("Overlap Threshold:", yolo_overlap_layout)
        
        # Use GPU
        self.yolo_gpu = QCheckBox()
        self.yolo_gpu.setChecked(True)
        yolo_layout.addRow("Use GPU:", self.yolo_gpu)
        
        detection_tabs.addTab(yolo_tab, "YOLO")
    
    def _create_automation_tab(self) -> None:
        """Create the automation settings tab."""
        automation_tab = QWidget()
        self.tabs.addTab(automation_tab, "Automation")
        
        # Create layout
        layout = QFormLayout(automation_tab)
        
        # Click delay
        self.click_delay = QSpinBox()
        self.click_delay.setRange(0, 1000)
        self.click_delay.setValue(100)
        self.click_delay.setSuffix(" ms")
        layout.addRow("Click Delay:", self.click_delay)
        
        # Typing speed
        self.typing_speed = QComboBox()
        self.typing_speed.addItems(["fast", "normal", "slow"])
        layout.addRow("Typing Speed:", self.typing_speed)
        
        # Default wait time
        self.default_wait = QSpinBox()
        self.default_wait.setRange(0, 10000)
        self.default_wait.setValue(500)
        self.default_wait.setSuffix(" ms")
        layout.addRow("Default Wait Time:", self.default_wait)
        
        # Error handling
        self.error_handling = QComboBox()
        self.error_handling.addItems(["stop", "pause", "retry", "ignore"])
        layout.addRow("Error Handling:", self.error_handling)
        
        # Max retries
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        self.max_retries.setValue(3)
        layout.addRow("Maximum Retries:", self.max_retries)
    
    def _create_window_tab(self) -> None:
        """Create the window settings tab."""
        window_tab = QWidget()
        self.tabs.addTab(window_tab, "Window")
        
        # Create layout
        layout = QFormLayout(window_tab)
        
        # Capture method
        self.capture_method = QComboBox()
        self.capture_method.addItems(["win32", "dxcam", "mss", "PIL"])
        layout.addRow("Capture Method:", self.capture_method)
        
        # Region padding
        self.region_padding = QSpinBox()
        self.region_padding.setRange(0, 50)
        self.region_padding.setValue(5)
        self.region_padding.setSuffix(" px")
        layout.addRow("Region Padding:", self.region_padding)
        
        # Capture interval
        self.capture_interval = QSpinBox()
        self.capture_interval.setRange(10, 1000)
        self.capture_interval.setValue(200)
        self.capture_interval.setSuffix(" ms")
        layout.addRow("Capture Interval:", self.capture_interval)
        
        # Highlight color
        self.highlight_color_btn = QPushButton("Choose Color")
        self.highlight_color_btn.setAutoFillBackground(True)
        self.highlight_color = "#00FF00"  # Default green
        self._update_color_button(self.highlight_color)
        layout.addRow("Highlight Color:", self.highlight_color_btn)
        
        # Auto focus
        self.auto_focus = QCheckBox()
        self.auto_focus.setChecked(True)
        layout.addRow("Auto-focus Window:", self.auto_focus)
    
    def _create_ui_tab(self) -> None:
        """Create the UI settings tab."""
        ui_tab = QWidget()
        self.tabs.addTab(ui_tab, "UI")
        
        # Create layout
        layout = QFormLayout(ui_tab)
        
        # Theme
        self.theme = QComboBox()
        self.theme.addItems(["system", "light", "dark"])
        layout.addRow("Theme:", self.theme)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 16)
        self.font_size.setValue(10)
        self.font_size.setSuffix(" pt")
        layout.addRow("Font Size:", self.font_size)
        
        # Show tooltips
        self.show_tooltips = QCheckBox()
        self.show_tooltips.setChecked(True)
        layout.addRow("Show Tooltips:", self.show_tooltips)
        
        # Confirm actions
        self.confirm_actions = QCheckBox()
        self.confirm_actions.setChecked(True)
        layout.addRow("Confirm Actions:", self.confirm_actions)
        
        # Show debug info
        self.show_debug = QCheckBox()
        self.show_debug.setChecked(False)
        layout.addRow("Show Debug Info:", self.show_debug)
    
    def _create_paths_tab(self) -> None:
        """Create the paths settings tab."""
        paths_tab = QWidget()
        self.tabs.addTab(paths_tab, "Paths")
        
        # Create layout
        layout = QFormLayout(paths_tab)
        
        # Templates directory
        templates_layout = QHBoxLayout()
        self.templates_dir = QLineEdit("./scout/resources/templates")
        templates_layout.addWidget(self.templates_dir)
        
        templates_btn = QPushButton("Browse")
        templates_btn.clicked.connect(lambda: self._browse_directory(self.templates_dir))
        templates_layout.addWidget(templates_btn)
        
        layout.addRow("Templates Directory:", templates_layout)
        
        # States directory
        states_layout = QHBoxLayout()
        self.states_dir = QLineEdit("./scout/resources/states")
        states_layout.addWidget(self.states_dir)
        
        states_btn = QPushButton("Browse")
        states_btn.clicked.connect(lambda: self._browse_directory(self.states_dir))
        states_layout.addWidget(states_btn)
        
        layout.addRow("States Directory:", states_layout)
        
        # Logs directory
        logs_layout = QHBoxLayout()
        self.logs_dir = QLineEdit("./scout/resources/logs")
        logs_layout.addWidget(self.logs_dir)
        
        logs_btn = QPushButton("Browse")
        logs_btn.clicked.connect(lambda: self._browse_directory(self.logs_dir))
        logs_layout.addWidget(logs_btn)
        
        layout.addRow("Logs Directory:", logs_layout)
        
        # Sequences directory
        sequences_layout = QHBoxLayout()
        self.sequences_dir = QLineEdit("./scout/resources/sequences")
        sequences_layout.addWidget(self.sequences_dir)
        
        sequences_btn = QPushButton("Browse")
        sequences_btn.clicked.connect(lambda: self._browse_directory(self.sequences_dir))
        sequences_layout.addWidget(sequences_btn)
        
        layout.addRow("Sequences Directory:", sequences_layout)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Connect buttons
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        
        # Connect sliders to labels
        self.template_confidence.valueChanged.connect(
            lambda value: self.template_confidence_label.setText(f"{value/100:.2f}"))
        
        self.ocr_confidence.valueChanged.connect(
            lambda value: self.ocr_confidence_label.setText(f"{value/100:.2f}"))
        
        self.yolo_confidence.valueChanged.connect(
            lambda value: self.yolo_confidence_label.setText(f"{value/100:.2f}"))
        
        self.yolo_overlap.valueChanged.connect(
            lambda value: self.yolo_overlap_label.setText(f"{value/100:.2f}"))
        
        # Connect color button
        self.highlight_color_btn.clicked.connect(self._on_color_button_clicked)
    
    def _load_settings_to_ui(self) -> None:
        """Load settings from model into UI widgets."""
        # Detection - Template Matching
        template_method = self.settings_model.get_setting("detection", "template_matching", "method")
        index = self.template_method.findText(template_method)
        if index >= 0:
            self.template_method.setCurrentIndex(index)
        
        confidence = self.settings_model.get_setting("detection", "template_matching", "confidence_threshold")
        self.template_confidence.setValue(int(confidence * 100))
        self.template_confidence_label.setText(f"{confidence:.2f}")
        
        max_results = self.settings_model.get_setting("detection", "template_matching", "max_results")
        self.template_max_results.setValue(max_results)
        
        grayscale = self.settings_model.get_setting("detection", "template_matching", "use_grayscale")
        self.template_grayscale.setChecked(grayscale)
        
        edge = self.settings_model.get_setting("detection", "template_matching", "use_edge_detection")
        self.template_edge.setChecked(edge)
        
        # Detection - OCR
        engine = self.settings_model.get_setting("detection", "ocr", "engine")
        index = self.ocr_engine.findText(engine)
        if index >= 0:
            self.ocr_engine.setCurrentIndex(index)
        
        language = self.settings_model.get_setting("detection", "ocr", "language")
        index = self.ocr_language.findText(language)
        if index >= 0:
            self.ocr_language.setCurrentIndex(index)
        
        confidence = self.settings_model.get_setting("detection", "ocr", "confidence_threshold")
        self.ocr_confidence.setValue(int(confidence * 100))
        self.ocr_confidence_label.setText(f"{confidence:.2f}")
        
        whitespace = self.settings_model.get_setting("detection", "ocr", "allow_whitespace")
        self.ocr_whitespace.setChecked(whitespace)
        
        preprocessing = self.settings_model.get_setting("detection", "ocr", "preprocessing")
        index = self.ocr_preprocessing.findText(preprocessing)
        if index >= 0:
            self.ocr_preprocessing.setCurrentIndex(index)
        
        # Detection - YOLO
        model = self.settings_model.get_setting("detection", "yolo", "model")
        index = self.yolo_model.findText(model)
        if index >= 0:
            self.yolo_model.setCurrentIndex(index)
        
        confidence = self.settings_model.get_setting("detection", "yolo", "confidence_threshold")
        self.yolo_confidence.setValue(int(confidence * 100))
        self.yolo_confidence_label.setText(f"{confidence:.2f}")
        
        overlap = self.settings_model.get_setting("detection", "yolo", "overlap_threshold")
        self.yolo_overlap.setValue(int(overlap * 100))
        self.yolo_overlap_label.setText(f"{overlap:.2f}")
        
        gpu = self.settings_model.get_setting("detection", "yolo", "use_gpu")
        self.yolo_gpu.setChecked(gpu)
        
        # Automation
        click_delay = self.settings_model.get_setting("automation", "click_delay")
        self.click_delay.setValue(click_delay)
        
        typing_speed = self.settings_model.get_setting("automation", "typing_speed")
        index = self.typing_speed.findText(typing_speed)
        if index >= 0:
            self.typing_speed.setCurrentIndex(index)
        
        default_wait = self.settings_model.get_setting("automation", "default_wait_time")
        self.default_wait.setValue(default_wait)
        
        error_handling = self.settings_model.get_setting("automation", "error_handling")
        index = self.error_handling.findText(error_handling)
        if index >= 0:
            self.error_handling.setCurrentIndex(index)
        
        max_retries = self.settings_model.get_setting("automation", "max_retries")
        self.max_retries.setValue(max_retries)
        
        # Window
        capture_method = self.settings_model.get_setting("window", "capture_method")
        index = self.capture_method.findText(capture_method)
        if index >= 0:
            self.capture_method.setCurrentIndex(index)
        
        region_padding = self.settings_model.get_setting("window", "region_padding")
        self.region_padding.setValue(region_padding)
        
        capture_interval = self.settings_model.get_setting("window", "capture_interval")
        self.capture_interval.setValue(capture_interval)
        
        highlight_color = self.settings_model.get_setting("window", "highlight_color")
        self.highlight_color = highlight_color
        self._update_color_button(highlight_color)
        
        auto_focus = self.settings_model.get_setting("window", "auto_focus")
        self.auto_focus.setChecked(auto_focus)
        
        # UI
        theme = self.settings_model.get_setting("ui", "theme")
        index = self.theme.findText(theme)
        if index >= 0:
            self.theme.setCurrentIndex(index)
        
        font_size = self.settings_model.get_setting("ui", "font_size")
        self.font_size.setValue(font_size)
        
        show_tooltips = self.settings_model.get_setting("ui", "show_tooltips")
        self.show_tooltips.setChecked(show_tooltips)
        
        confirm_actions = self.settings_model.get_setting("ui", "confirm_actions")
        self.confirm_actions.setChecked(confirm_actions)
        
        show_debug = self.settings_model.get_setting("ui", "show_debug_info")
        self.show_debug.setChecked(show_debug)
        
        # Paths
        templates_dir = self.settings_model.get_setting("paths", "templates_dir")
        self.templates_dir.setText(templates_dir)
        
        state_dir = self.settings_model.get_setting("paths", "state_dir")
        self.states_dir.setText(state_dir)
        
        logs_dir = self.settings_model.get_setting("paths", "logs_dir")
        self.logs_dir.setText(logs_dir)
        
        sequences_dir = self.settings_model.get_setting("paths", "sequences_dir")
        self.sequences_dir.setText(sequences_dir)
    
    def _collect_settings_from_ui(self) -> None:
        """Collect settings from UI widgets into the model."""
        # Detection - Template Matching
        self.settings_model.set_setting(
            "detection", "template_matching", "method", 
            self.template_method.currentText()
        )
        
        self.settings_model.set_setting(
            "detection", "template_matching", "confidence_threshold", 
            self.template_confidence.value() / 100.0
        )
        
        self.settings_model.set_setting(
            "detection", "template_matching", "max_results", 
            self.template_max_results.value()
        )
        
        self.settings_model.set_setting(
            "detection", "template_matching", "use_grayscale", 
            self.template_grayscale.isChecked()
        )
        
        self.settings_model.set_setting(
            "detection", "template_matching", "use_edge_detection", 
            self.template_edge.isChecked()
        )
        
        # Detection - OCR
        self.settings_model.set_setting(
            "detection", "ocr", "engine", 
            self.ocr_engine.currentText()
        )
        
        self.settings_model.set_setting(
            "detection", "ocr", "language", 
            self.ocr_language.currentText()
        )
        
        self.settings_model.set_setting(
            "detection", "ocr", "confidence_threshold", 
            self.ocr_confidence.value() / 100.0
        )
        
        self.settings_model.set_setting(
            "detection", "ocr", "allow_whitespace", 
            self.ocr_whitespace.isChecked()
        )
        
        self.settings_model.set_setting(
            "detection", "ocr", "preprocessing", 
            self.ocr_preprocessing.currentText()
        )
        
        # Detection - YOLO
        self.settings_model.set_setting(
            "detection", "yolo", "model", 
            self.yolo_model.currentText()
        )
        
        self.settings_model.set_setting(
            "detection", "yolo", "confidence_threshold", 
            self.yolo_confidence.value() / 100.0
        )
        
        self.settings_model.set_setting(
            "detection", "yolo", "overlap_threshold", 
            self.yolo_overlap.value() / 100.0
        )
        
        self.settings_model.set_setting(
            "detection", "yolo", "use_gpu", 
            self.yolo_gpu.isChecked()
        )
        
        # Automation
        self.settings_model.set_setting(
            "automation", "click_delay", 
            self.click_delay.value()
        )
        
        self.settings_model.set_setting(
            "automation", "typing_speed", 
            self.typing_speed.currentText()
        )
        
        self.settings_model.set_setting(
            "automation", "default_wait_time", 
            self.default_wait.value()
        )
        
        self.settings_model.set_setting(
            "automation", "error_handling", 
            self.error_handling.currentText()
        )
        
        self.settings_model.set_setting(
            "automation", "max_retries", 
            self.max_retries.value()
        )
        
        # Window
        self.settings_model.set_setting(
            "window", "capture_method", 
            self.capture_method.currentText()
        )
        
        self.settings_model.set_setting(
            "window", "region_padding", 
            self.region_padding.value()
        )
        
        self.settings_model.set_setting(
            "window", "capture_interval", 
            self.capture_interval.value()
        )
        
        self.settings_model.set_setting(
            "window", "highlight_color", 
            self.highlight_color
        )
        
        self.settings_model.set_setting(
            "window", "auto_focus", 
            self.auto_focus.isChecked()
        )
        
        # UI
        self.settings_model.set_setting(
            "ui", "theme", 
            self.theme.currentText()
        )
        
        self.settings_model.set_setting(
            "ui", "font_size", 
            self.font_size.value()
        )
        
        self.settings_model.set_setting(
            "ui", "show_tooltips", 
            self.show_tooltips.isChecked()
        )
        
        self.settings_model.set_setting(
            "ui", "confirm_actions", 
            self.confirm_actions.isChecked()
        )
        
        self.settings_model.set_setting(
            "ui", "show_debug_info", 
            self.show_debug.isChecked()
        )
        
        # Paths
        self.settings_model.set_setting(
            "paths", "templates_dir", 
            self.templates_dir.text()
        )
        
        self.settings_model.set_setting(
            "paths", "state_dir", 
            self.states_dir.text()
        )
        
        self.settings_model.set_setting(
            "paths", "logs_dir", 
            self.logs_dir.text()
        )
        
        self.settings_model.set_setting(
            "paths", "sequences_dir", 
            self.sequences_dir.text()
        )
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        # Collect settings from UI
        self._collect_settings_from_ui()
        
        # Save settings
        if self.settings_model.save_settings():
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved successfully."
            )
            
            # Emit settings changed signal
            self.settings_changed.emit(self.settings_model.settings)
        else:
            QMessageBox.warning(
                self,
                "Save Failed",
                "Failed to save settings. See logs for details."
            )
    
    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        # Confirm reset
        result = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
        
        # Reset settings
        self.settings_model.reset_to_defaults()
        
        # Update UI
        self._load_settings_to_ui()
        
        QMessageBox.information(
            self,
            "Settings Reset",
            "Settings have been reset to default values."
        )
    
    def _on_color_button_clicked(self) -> None:
        """Handle color button click."""
        # Show color dialog
        color = QColorDialog.getColor(
            QColor(self.highlight_color),
            self,
            "Choose Highlight Color"
        )
        
        if color.isValid():
            # Update color
            self.highlight_color = color.name()
            self._update_color_button(self.highlight_color)
    
    def _update_color_button(self, color_str: str) -> None:
        """
        Update color button appearance.
        
        Args:
            color_str: Color string in hex format (#RRGGBB)
        """
        # Set button background color
        style = f"background-color: {color_str};"
        
        # Determine text color (white for dark backgrounds, black for light)
        color = QColor(color_str)
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        
        if luminance < 0.5:
            style += "color: white;"
        else:
            style += "color: black;"
        
        self.highlight_color_btn.setStyleSheet(style)
        self.highlight_color_btn.setText(color_str)
    
    def _browse_directory(self, line_edit: QLineEdit) -> None:
        """
        Open directory browser dialog.
        
        Args:
            line_edit: Line edit to update with selected directory
        """
        # Get current directory
        current_dir = line_edit.text()
        
        # Open directory dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            line_edit.setText(directory)
    
    def get_settings(self) -> Dict:
        """
        Get current settings.
        
        Returns:
            dict: Settings dictionary
        """
        return self.settings_model.settings 