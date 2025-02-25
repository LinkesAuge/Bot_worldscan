"""
Settings Tab

This module provides a tab interface for configuring application settings,
including language, appearance, paths, and other application preferences.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QTabWidget, QSlider, QColorDialog, QDialog,
    QDialogButtonBox, QFormLayout, QProgressBar, QTextEdit
)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings, QTimer

from scout.core.services.service_locator import ServiceLocator
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.ui.models.settings_model import SettingsModel
from scout.ui.utils.language_manager import get_language_manager, Language, tr

# Set up logging
logger = logging.getLogger(__name__)

class SettingsTab(QWidget):
    """
    Tab for configuring application settings.
    
    This tab provides an interface for customizing detection parameters,
    automation behavior, appearance settings, and other application preferences.
    
    It's organized into several sections:
    1. Detection Configuration - For configuring detection strategies
    2. Automation Configuration - For configuring automation behavior
    3. Window Configuration - For configuring window capture and display
    4. UI Configuration - For configuring general UI settings (including language)
    5. Application Configuration - For configuring general application settings
    6. Advanced Configuration - For advanced and developer options
    """
    
    # Signal emitted when settings are changed
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, service_locator: ServiceLocator):
        """
        Initialize the settings tab.
        
        Args:
            service_locator: Service locator for accessing application services
        """
        super().__init__()
        
        # Store services
        self.service_locator = service_locator
        self.detection_service = service_locator.get_service(DetectionServiceInterface)
        self.window_service = service_locator.get_service(WindowServiceInterface)
        self.automation_service = service_locator.get_service(AutomationServiceInterface)
        
        # Create settings model
        self.settings_model = SettingsModel()
        
        # Flag to prevent signals when bulk updating the UI
        self._updating_ui = False
        
        # Initialize state
        self._settings = QSettings("ScoutTeam", "Scout")
        self._modified = False
        self._language_manager = get_language_manager()
        
        # Create UI components
        self._create_ui()
        
        # Load settings into UI
        self._load_settings_to_ui()
        
        # Connect signals
        self._connect_signals()
        
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
        main_layout.setSpacing(10)
        
        # Create tabs for setting categories
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs)
        
        # Create individual setting tabs
        self._create_detection_tab()
        self._create_automation_tab()
        self._create_window_tab()
        self._create_ui_tab()
        self._create_paths_tab()
        self._create_advanced_tab()
        
        # Create status label to show save status
        self.status_label = QLabel("All settings up to date")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Create buttons
        buttons_layout = QHBoxLayout()
        
        # Import button
        self.import_btn = QPushButton("Import Settings")
        self.import_btn.setIcon(QIcon.fromTheme("document-open"))
        self.import_btn.setToolTip("Import settings from a JSON file")
        buttons_layout.addWidget(self.import_btn)
        
        # Export button
        self.export_btn = QPushButton("Export Settings")
        self.export_btn.setIcon(QIcon.fromTheme("document-save-as"))
        self.export_btn.setToolTip("Export settings to a JSON file")
        buttons_layout.addWidget(self.export_btn)
        
        # Spacer
        buttons_layout.addStretch()
        
        # Save button
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setIcon(QIcon.fromTheme("document-save"))
        buttons_layout.addWidget(self.save_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setIcon(QIcon.fromTheme("edit-clear"))
        buttons_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(buttons_layout)
    
    def _create_detection_tab(self) -> None:
        """Create the detection settings tab."""
        detection_tab = QWidget()
        self.tabs.addTab(detection_tab, "Detection")
        
        # Create layout
        layout = QVBoxLayout(detection_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tabs for detection methods
        detection_tabs = QTabWidget()
        layout.addWidget(detection_tabs)
        
        # General detection settings
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        # Cache settings
        cache_group = QGroupBox("Detection Cache")
        cache_layout = QFormLayout(cache_group)
        
        # Use cache
        self.use_cache = QCheckBox()
        self.use_cache.setChecked(True)
        cache_layout.addRow("Enable Caching:", self.use_cache)
        
        # Cache timeout
        self.cache_timeout = QSpinBox()
        self.cache_timeout.setRange(100, 10000)
        self.cache_timeout.setValue(5000)
        self.cache_timeout.setSuffix(" ms")
        cache_layout.addRow("Cache Timeout:", self.cache_timeout)
        
        # Cache size
        self.cache_size = QSpinBox()
        self.cache_size.setRange(10, 1000)
        self.cache_size.setValue(100)
        self.cache_size.setSuffix(" items")
        cache_layout.addRow("Max Cache Size:", self.cache_size)
        
        cache_group.setLayout(cache_layout)
        general_layout.addRow(cache_group)
        
        # Detection result settings
        result_group = QGroupBox("Detection Results")
        result_layout = QFormLayout(result_group)
        
        # Result sorting
        self.result_sorting = QComboBox()
        self.result_sorting.addItems(["confidence", "position", "size", "type"])
        result_layout.addRow("Sort Results By:", self.result_sorting)
        
        # Result grouping radius
        self.grouping_radius = QSpinBox()
        self.grouping_radius.setRange(0, 100)
        self.grouping_radius.setValue(5)
        self.grouping_radius.setSuffix(" px")
        result_layout.addRow("Grouping Radius:", self.grouping_radius)
        
        # Max results per detection
        self.max_results = QSpinBox()
        self.max_results.setRange(1, 100)
        self.max_results.setValue(20)
        result_layout.addRow("Max Results:", self.max_results)
        
        result_group.setLayout(result_layout)
        general_layout.addRow(result_group)
        
        detection_tabs.addTab(general_tab, "General")
        
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
        
        # Template scaling
        self.template_scaling = QCheckBox()
        self.template_scaling.setChecked(False)
        template_layout.addRow("Scale Templates:", self.template_scaling)
        
        # Scale range
        scale_layout = QHBoxLayout()
        self.scale_min = QDoubleSpinBox()
        self.scale_min.setRange(0.5, 1.0)
        self.scale_min.setValue(0.8)
        self.scale_min.setSingleStep(0.05)
        scale_layout.addWidget(self.scale_min)
        
        scale_layout.addWidget(QLabel("to"))
        
        self.scale_max = QDoubleSpinBox()
        self.scale_max.setRange(1.0, 2.0)
        self.scale_max.setValue(1.2)
        self.scale_max.setSingleStep(0.05)
        scale_layout.addWidget(self.scale_max)
        
        template_layout.addRow("Scale Range:", scale_layout)
        
        # Scale steps
        self.scale_steps = QSpinBox()
        self.scale_steps.setRange(1, 10)
        self.scale_steps.setValue(3)
        template_layout.addRow("Scale Steps:", self.scale_steps)
        
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
        
        # Custom parameters
        self.ocr_custom_params = QLineEdit()
        self.ocr_custom_params.setPlaceholderText("--psm 6 --oem 3")
        ocr_layout.addRow("Custom Parameters:", self.ocr_custom_params)
        
        # Character whitelist
        self.ocr_whitelist = QLineEdit()
        self.ocr_whitelist.setPlaceholderText("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        ocr_layout.addRow("Character Whitelist:", self.ocr_whitelist)
        
        detection_tabs.addTab(ocr_tab, "OCR")
        
        # YOLO settings
        yolo_tab = QWidget()
        yolo_layout = QFormLayout(yolo_tab)
        
        # Model
        self.yolo_model = QComboBox()
        self.yolo_model.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt"])
        yolo_layout.addRow("YOLO Model:", self.yolo_model)
        
        # Model file
        model_file_layout = QHBoxLayout()
        self.yolo_model_file = QLineEdit()
        model_file_layout.addWidget(self.yolo_model_file)
        
        browse_model_btn = QPushButton("Browse")
        browse_model_btn.clicked.connect(lambda: self._browse_file(self.yolo_model_file, "YOLO Models (*.pt *.onnx)"))
        model_file_layout.addWidget(browse_model_btn)
        
        yolo_layout.addRow("Model File:", model_file_layout)
        
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
        
        # Classes
        self.yolo_classes = QLineEdit()
        self.yolo_classes.setPlaceholderText("0,1,2,3")
        yolo_layout.addRow("Classes (comma separated):", self.yolo_classes)
        
        # Use GPU
        self.yolo_gpu = QCheckBox()
        self.yolo_gpu.setChecked(True)
        yolo_layout.addRow("Use GPU:", self.yolo_gpu)
        
        # Add help text at bottom
        yolo_help = QLabel("Note: YOLO models must be in PyTorch or ONNX format and located in the models directory.")
        yolo_help.setWordWrap(True)
        yolo_help.setStyleSheet("color: gray; font-style: italic;")
        yolo_layout.addRow(yolo_help)
        
        detection_tabs.addTab(yolo_tab, "YOLO")
    
    def _create_automation_tab(self) -> None:
        """Create the automation settings tab."""
        automation_tab = QWidget()
        self.tabs.addTab(automation_tab, "Automation")
        
        # Create main layout
        main_layout = QVBoxLayout(automation_tab)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll_area)
        
        # Create content widget
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        
        # Basic automation settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        # Click delay
        self.click_delay = QSpinBox()
        self.click_delay.setRange(0, 1000)
        self.click_delay.setValue(100)
        self.click_delay.setSuffix(" ms")
        basic_layout.addRow("Click Delay:", self.click_delay)
        
        # Double click delay
        self.double_click_delay = QSpinBox()
        self.double_click_delay.setRange(0, 500)
        self.double_click_delay.setValue(50)
        self.double_click_delay.setSuffix(" ms")
        basic_layout.addRow("Double Click Delay:", self.double_click_delay)
        
        # Typing speed
        self.typing_speed = QComboBox()
        self.typing_speed.addItems(["fast", "normal", "slow"])
        basic_layout.addRow("Typing Speed:", self.typing_speed)
        
        # Default wait time
        self.default_wait = QSpinBox()
        self.default_wait.setRange(0, 10000)
        self.default_wait.setValue(500)
        self.default_wait.setSuffix(" ms")
        basic_layout.addRow("Default Wait Time:", self.default_wait)
        
        # Mouse movement speed
        self.mouse_speed = QSlider(Qt.Orientation.Horizontal)
        self.mouse_speed.setRange(1, 10)
        self.mouse_speed.setValue(5)
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Slow"))
        speed_layout.addWidget(self.mouse_speed)
        speed_layout.addWidget(QLabel("Fast"))
        basic_layout.addRow("Mouse Speed:", speed_layout)
        
        # Randomize movements
        self.randomize_movements = QCheckBox()
        self.randomize_movements.setChecked(True)
        basic_layout.addRow("Randomize Movements:", self.randomize_movements)
        
        basic_group.setLayout(basic_layout)
        content_layout.addWidget(basic_group)
        
        # Advanced automation settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()
        
        # Error handling
        self.error_handling = QComboBox()
        self.error_handling.addItems(["stop", "pause", "retry", "ignore"])
        advanced_layout.addRow("Error Handling:", self.error_handling)
        
        # Max retries
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        self.max_retries.setValue(3)
        advanced_layout.addRow("Maximum Retries:", self.max_retries)
        
        # Retry delay
        self.retry_delay = QSpinBox()
        self.retry_delay.setRange(0, 10000)
        self.retry_delay.setValue(1000)
        self.retry_delay.setSuffix(" ms")
        advanced_layout.addRow("Retry Delay:", self.retry_delay)
        
        # Jitter range
        jitter_layout = QHBoxLayout()
        
        self.jitter_min = QSpinBox()
        self.jitter_min.setRange(0, 50)
        self.jitter_min.setValue(5)
        self.jitter_min.setSuffix(" px")
        jitter_layout.addWidget(self.jitter_min)
        
        jitter_layout.addWidget(QLabel("to"))
        
        self.jitter_max = QSpinBox()
        self.jitter_max.setRange(0, 100)
        self.jitter_max.setValue(15)
        self.jitter_max.setSuffix(" px")
        jitter_layout.addWidget(self.jitter_max)
        
        advanced_layout.addRow("Jitter Range:", jitter_layout)
        
        # Detection polling interval
        self.detection_interval = QSpinBox()
        self.detection_interval.setRange(100, 10000)
        self.detection_interval.setValue(500)
        self.detection_interval.setSuffix(" ms")
        advanced_layout.addRow("Detection Interval:", self.detection_interval)
        
        advanced_group.setLayout(advanced_layout)
        content_layout.addWidget(advanced_group)
        
        # Sequence settings
        sequence_group = QGroupBox("Sequence Settings")
        sequence_layout = QFormLayout()
        
        # Sequence directory
        sequence_dir_layout = QHBoxLayout()
        self.sequence_dir = QLineEdit("./scout/resources/sequences")
        sequence_dir_layout.addWidget(self.sequence_dir)
        
        sequence_browse_btn = QPushButton("Browse")
        sequence_browse_btn.clicked.connect(lambda: self._browse_directory(self.sequence_dir))
        sequence_dir_layout.addWidget(sequence_browse_btn)
        
        sequence_layout.addRow("Sequences Directory:", sequence_dir_layout)
        
        # Default sequence
        self.default_sequence = QComboBox()
        self.default_sequence.setEditable(True)
        self._update_sequence_list()
        sequence_layout.addRow("Default Sequence:", self.default_sequence)
        
        # Autostart sequence
        self.autostart_sequence = QCheckBox()
        self.autostart_sequence.setChecked(False)
        sequence_layout.addRow("Autostart Sequence:", self.autostart_sequence)
        
        # Loop sequences
        self.loop_sequence = QCheckBox()
        self.loop_sequence.setChecked(False)
        sequence_layout.addRow("Loop Sequences:", self.loop_sequence)
        
        sequence_group.setLayout(sequence_layout)
        content_layout.addWidget(sequence_group)
    
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
        
        # Window title
        self.window_title = QLineEdit("Total Battle")
        layout.addRow("Window Title:", self.window_title)
        
        # Auto-find window
        self.auto_find = QCheckBox()
        self.auto_find.setChecked(True)
        layout.addRow("Auto-find Window:", self.auto_find)
        
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
        
        # Overlay settings
        overlay_group = QGroupBox("Overlay Settings")
        overlay_layout = QFormLayout()
        
        # Enable overlay
        self.overlay_enabled = QCheckBox()
        self.overlay_enabled.setChecked(True)
        overlay_layout.addRow("Enable Overlay:", self.overlay_enabled)
        
        # Highlight color
        self.highlight_color_btn = QPushButton("Choose Color")
        self.highlight_color_btn.setAutoFillBackground(True)
        self.highlight_color = "#00FF00"  # Default green
        self._update_color_button(self.highlight_color_btn, self.highlight_color)
        overlay_layout.addRow("Highlight Color:", self.highlight_color_btn)
        
        # Text color
        self.text_color_btn = QPushButton("Choose Color")
        self.text_color_btn.setAutoFillBackground(True)
        self.text_color = "#FFFF00"  # Default yellow
        self._update_color_button(self.text_color_btn, self.text_color)
        overlay_layout.addRow("Text Color:", self.text_color_btn)
        
        # Show confidence
        self.show_confidence = QCheckBox()
        self.show_confidence.setChecked(True)
        overlay_layout.addRow("Show Confidence:", self.show_confidence)
        
        # Overlay refresh rate
        self.overlay_refresh = QSpinBox()
        self.overlay_refresh.setRange(10, 1000)
        self.overlay_refresh.setValue(100)
        self.overlay_refresh.setSuffix(" ms")
        overlay_layout.addRow("Refresh Rate:", self.overlay_refresh)
        
        # Overlay opacity
        self.overlay_opacity = QSlider(Qt.Orientation.Horizontal)
        self.overlay_opacity.setRange(10, 100)
        self.overlay_opacity.setValue(80)
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.overlay_opacity)
        opacity_layout.addWidget(QLabel("80%"))
        overlay_layout.addRow("Opacity:", opacity_layout)
        
        overlay_group.setLayout(overlay_layout)
        layout.addRow(overlay_group)
        
        # Auto focus
        self.auto_focus = QCheckBox()
        self.auto_focus.setChecked(True)
        layout.addRow("Auto-focus Window:", self.auto_focus)
    
    def _create_ui_tab(self) -> None:
        """Create the UI configuration tab."""
        ui_tab = QWidget()
        self.tabs.addTab(ui_tab, "UI")
        
        # Create layout
        layout = QFormLayout(ui_tab)
        
        # Theme
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        # Theme selection
        theme_layout.addWidget(QLabel("Application Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System", "system")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Custom", "custom")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        # Custom theme file
        custom_theme_layout = QHBoxLayout()
        self.custom_theme_check = QCheckBox("Use Custom Theme File:")
        self.custom_theme_check.stateChanged.connect(self._mark_settings_changed)
        custom_theme_layout.addWidget(self.custom_theme_check)
        
        self.custom_theme_path = QLineEdit()
        self.custom_theme_path.setEnabled(False)
        self.custom_theme_path.textChanged.connect(self._mark_settings_changed)
        custom_theme_layout.addWidget(self.custom_theme_path)
        
        self.browse_theme_button = QPushButton("...")
        self.browse_theme_button.setEnabled(False)
        self.browse_theme_button.clicked.connect(lambda: self._browse_file(self.custom_theme_path, "QSS Files (*.qss)"))
        custom_theme_layout.addWidget(self.browse_theme_button)
        
        theme_layout.addLayout(custom_theme_layout)
        
        layout.addWidget(theme_group)
        
        # Language section
        language_group = QGroupBox("Language")
        language_layout = QVBoxLayout(language_group)
        
        # Language selection
        language_layout.addWidget(QLabel("Application Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("System Default", Language.SYSTEM.value)
        self.language_combo.addItem("English", Language.ENGLISH.value)
        self.language_combo.addItem("Deutsch", Language.GERMAN.value)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        language_layout.addWidget(self.language_combo)
        
        # Add note about restart
        language_note = QLabel("Note: Some changes may require an application restart.")
        language_note.setStyleSheet("font-style: italic; color: gray;")
        language_layout.addWidget(language_note)
        
        layout.addWidget(language_group)
        
        # Font section
        font_group = QGroupBox("Fonts")
        font_layout = QVBoxLayout(font_group)
        
        # Font size
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Interface Font Size:"))
        self.font_size_spinner = QSpinBox()
        self.font_size_spinner.setRange(8, 24)
        self.font_size_spinner.setSingleStep(1)
        self.font_size_spinner.setValue(10)
        self.font_size_spinner.valueChanged.connect(self._mark_settings_changed)
        font_size_layout.addWidget(self.font_size_spinner)
        font_layout.addLayout(font_size_layout)
        
        layout.addWidget(font_group)
    
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
        
        # Models directory
        models_layout = QHBoxLayout()
        self.models_dir = QLineEdit("./scout/resources/models")
        models_layout.addWidget(self.models_dir)
        
        models_btn = QPushButton("Browse")
        models_btn.clicked.connect(lambda: self._browse_directory(self.models_dir))
        models_layout.addWidget(models_btn)
        
        layout.addRow("Models Directory:", models_layout)
        
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
        
        # Screenshots directory
        screenshots_layout = QHBoxLayout()
        self.screenshots_dir = QLineEdit("./scout/resources/screenshots")
        screenshots_layout.addWidget(self.screenshots_dir)
        
        screenshots_btn = QPushButton("Browse")
        screenshots_btn.clicked.connect(lambda: self._browse_directory(self.screenshots_dir))
        screenshots_layout.addWidget(screenshots_btn)
        
        layout.addRow("Screenshots Directory:", screenshots_layout)
        
        # Create directories button
        create_dirs_btn = QPushButton("Create Missing Directories")
        create_dirs_btn.clicked.connect(self._create_missing_directories)
        layout.addRow("", create_dirs_btn)
    
    def _create_advanced_tab(self) -> None:
        """Create the advanced settings tab."""
        advanced_tab = QWidget()
        self.tabs.addTab(advanced_tab, "Advanced")
        
        # Create layout
        layout = QVBoxLayout(advanced_tab)
        
        # Warning label
        warning_label = QLabel("Warning: These settings are for advanced users only. "
                               "Incorrect values may cause instability or crashes.")
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # Create form layout for settings
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Performance settings
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout()
        
        # Thread count
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 16)
        self.thread_count.setValue(4)
        performance_layout.addRow("Worker Threads:", self.thread_count)
        
        # Process priority
        self.process_priority = QComboBox()
        self.process_priority.addItems(["normal", "above_normal", "high", "realtime"])
        performance_layout.addRow("Process Priority:", self.process_priority)
        
        # Image cache size
        self.image_cache_size = QSpinBox()
        self.image_cache_size.setRange(10, 1000)
        self.image_cache_size.setValue(100)
        self.image_cache_size.setSuffix(" MB")
        performance_layout.addRow("Image Cache Size:", self.image_cache_size)
        
        # Enable parallel processing
        self.parallel_processing = QCheckBox()
        self.parallel_processing.setChecked(True)
        performance_layout.addRow("Parallel Processing:", self.parallel_processing)
        
        performance_group.setLayout(performance_layout)
        form_layout.addRow(performance_group)
        
        # Debug settings
        debug_group = QGroupBox("Debug")
        debug_layout = QFormLayout()
        
        # Log level
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level.setCurrentIndex(1)  # Default to INFO
        debug_layout.addRow("Log Level:", self.log_level)
        
        # Log to file
        self.log_to_file = QCheckBox()
        self.log_to_file.setChecked(True)
        debug_layout.addRow("Log to File:", self.log_to_file)
        
        # Log format
        self.log_format = QLineEdit("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        debug_layout.addRow("Log Format:", self.log_format)
        
        # Debug window
        self.debug_window = QCheckBox()
        self.debug_window.setChecked(False)
        debug_layout.addRow("Show Debug Window:", self.debug_window)
        
        # Performance monitoring
        self.performance_monitoring = QCheckBox()
        self.performance_monitoring.setChecked(False)
        debug_layout.addRow("Performance Monitoring:", self.performance_monitoring)
        
        debug_group.setLayout(debug_layout)
        form_layout.addRow(debug_group)
        
        # Developer settings
        developer_group = QGroupBox("Developer")
        developer_layout = QFormLayout()
        
        # Development mode
        self.development_mode = QCheckBox()
        self.development_mode.setChecked(False)
        developer_layout.addRow("Development Mode:", self.development_mode)
        
        # Remote debugging
        self.remote_debugging = QCheckBox()
        self.remote_debugging.setChecked(False)
        developer_layout.addRow("Remote Debugging:", self.remote_debugging)
        
        # Remote debugging port
        self.remote_debugging_port = QSpinBox()
        self.remote_debugging_port.setRange(1024, 65535)
        self.remote_debugging_port.setValue(5678)
        developer_layout.addRow("Debugging Port:", self.remote_debugging_port)
        
        # Export config button
        export_config_btn = QPushButton("Export Configuration")
        export_config_btn.clicked.connect(self._export_full_configuration)
        developer_layout.addRow("", export_config_btn)
        
        developer_group.setLayout(developer_layout)
        form_layout.addRow(developer_group)
        
        # Restore factory settings button
        factory_reset_btn = QPushButton("Restore Factory Settings")
        factory_reset_btn.clicked.connect(self._confirm_factory_reset)
        factory_reset_btn.setStyleSheet("background-color: #ffaaaa;")
        layout.addWidget(factory_reset_btn)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Connect buttons
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        self.import_btn.clicked.connect(self._on_import_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
        
        # Connect color buttons
        self.highlight_color_btn.clicked.connect(lambda: self._on_color_button_clicked(self.highlight_color_btn, "highlight_color"))
        self.text_color_btn.clicked.connect(lambda: self._on_color_button_clicked(self.text_color_btn, "text_color"))
        
        # Connect sliders to labels
        self.template_confidence.valueChanged.connect(
            lambda value: self.template_confidence_label.setText(f"{value/100:.2f}"))
        
        self.ocr_confidence.valueChanged.connect(
            lambda value: self.ocr_confidence_label.setText(f"{value/100:.2f}"))
        
        self.yolo_confidence.valueChanged.connect(
            lambda value: self.yolo_confidence_label.setText(f"{value/100:.2f}"))
        
        self.yolo_overlap.valueChanged.connect(
            lambda value: self.yolo_overlap_label.setText(f"{value/100:.2f}"))
            
        self.overlay_opacity.valueChanged.connect(
            lambda value: self.overlay_opacity.parent().layout().itemAt(1).widget().setText(f"{value}%"))
            
        self.sound_volume.valueChanged.connect(
            lambda value: self.sound_volume.parent().layout().itemAt(1).widget().setText(f"{value}%"))
        
        # Connect sequence directory to update sequence list
        self.sequence_dir.textChanged.connect(self._update_sequence_list)
        
        # Connect theme selection to enable/disable custom theme file
        self.theme_combo.currentTextChanged.connect(self._update_theme_file_state)
        
        # Connect settings changes to auto-save
        for widget in self.findChildren((QComboBox, QLineEdit, QSpinBox, QCheckBox, QSlider)):
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._mark_settings_changed)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._mark_settings_changed)
            elif isinstance(widget, QSpinBox) or isinstance(widget, QSlider):
                widget.valueChanged.connect(self._mark_settings_changed)
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(self._mark_settings_changed)
    
    def _load_settings_to_ui(self) -> None:
        """Load settings from model into UI widgets."""
        try:
            # Set updating flag to prevent signal triggers
            self._updating_ui = True
            
            # Detection - General
            self.use_cache.setChecked(self.settings_model.get("use_caching", True))
            self.cache_timeout.setValue(self.settings_model.get("cache_timeout", 5000))
            self.cache_size.setValue(self.settings_model.get("cache_size", 100))
            
            result_sorting = self.settings_model.get("result_sorting", "confidence")
            index = self.result_sorting.findText(result_sorting)
            if index >= 0:
                self.result_sorting.setCurrentIndex(index)
                
            self.grouping_radius.setValue(self.settings_model.get("grouping_radius", 5))
            self.max_results.setValue(self.settings_model.get("max_results", 20))
            
            # Detection - Template Matching
            template_method = self.settings_model.get("template_method", "cv2.TM_CCOEFF_NORMED")
            index = self.template_method.findText(template_method)
            if index >= 0:
                self.template_method.setCurrentIndex(index)
            
            confidence = self.settings_model.get("template_confidence", 0.8)
            self.template_confidence.setValue(int(confidence * 100))
            self.template_confidence_label.setText(f"{confidence:.2f}")
            
            self.template_max_results.setValue(self.settings_model.get("template_max_results", 5))
            self.template_grayscale.setChecked(self.settings_model.get("template_grayscale", True))
            self.template_edge.setChecked(self.settings_model.get("template_edge", False))
            self.template_scaling.setChecked(self.settings_model.get("template_scaling", False))
            self.scale_min.setValue(self.settings_model.get("scale_min", 0.8))
            self.scale_max.setValue(self.settings_model.get("scale_max", 1.2))
            self.scale_steps.setValue(self.settings_model.get("scale_steps", 3))
            
            # Detection - OCR
            engine = self.settings_model.get("ocr_engine", "tesseract")
            index = self.ocr_engine.findText(engine)
            if index >= 0:
                self.ocr_engine.setCurrentIndex(index)
            
            language = self.settings_model.get("ocr_language", "eng")
            index = self.ocr_language.findText(language)
            if index >= 0:
                self.ocr_language.setCurrentIndex(index)
            
            confidence = self.settings_model.get("ocr_confidence", 0.6)
            self.ocr_confidence.setValue(int(confidence * 100))
            self.ocr_confidence_label.setText(f"{confidence:.2f}")
            
            self.ocr_whitespace.setChecked(self.settings_model.get("ocr_whitespace", True))
            
            preprocessing = self.settings_model.get("ocr_preprocessing", "threshold")
            index = self.ocr_preprocessing.findText(preprocessing)
            if index >= 0:
                self.ocr_preprocessing.setCurrentIndex(index)
                
            self.ocr_custom_params.setText(self.settings_model.get("ocr_custom_params", "--psm 6 --oem 3"))
            self.ocr_whitelist.setText(self.settings_model.get("ocr_whitelist", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            
            # Detection - YOLO
            model = self.settings_model.get("yolo_model", "yolov8n.pt")
            index = self.yolo_model.findText(model)
            if index >= 0:
                self.yolo_model.setCurrentIndex(index)
                
            self.yolo_model_file.setText(self.settings_model.get("yolo_model_file", ""))
            
            confidence = self.settings_model.get("yolo_confidence", 0.5)
            self.yolo_confidence.setValue(int(confidence * 100))
            self.yolo_confidence_label.setText(f"{confidence:.2f}")
            
            overlap = self.settings_model.get("yolo_overlap", 0.45)
            self.yolo_overlap.setValue(int(overlap * 100))
            self.yolo_overlap_label.setText(f"{overlap:.2f}")
            
            self.yolo_classes.setText(self.settings_model.get("yolo_classes", ""))
            self.yolo_gpu.setChecked(self.settings_model.get("yolo_gpu", True))
            
            # Automation
            self.click_delay.setValue(self.settings_model.get("click_delay", 100))
            self.double_click_delay.setValue(self.settings_model.get("double_click_delay", 50))
            
            typing_speed = self.settings_model.get("typing_speed", "normal")
            index = self.typing_speed.findText(typing_speed)
            if index >= 0:
                self.typing_speed.setCurrentIndex(index)
            
            self.default_wait.setValue(self.settings_model.get("default_wait_time", 500))
            self.mouse_speed.setValue(self.settings_model.get("mouse_speed", 5))
            self.randomize_movements.setChecked(self.settings_model.get("randomize_movements", True))
            
            error_handling = self.settings_model.get("error_handling", "pause")
            index = self.error_handling.findText(error_handling)
            if index >= 0:
                self.error_handling.setCurrentIndex(index)
            
            self.max_retries.setValue(self.settings_model.get("max_retries", 3))
            self.retry_delay.setValue(self.settings_model.get("retry_delay", 1000))
            self.jitter_min.setValue(self.settings_model.get("jitter_min", 5))
            self.jitter_max.setValue(self.settings_model.get("jitter_max", 15))
            self.detection_interval.setValue(self.settings_model.get("detection_interval", 500))
            
            self.sequence_dir.setText(self.settings_model.get("sequences_dir", "./scout/resources/sequences"))
            
            default_sequence = self.settings_model.get("default_sequence", "")
            if default_sequence:
                index = self.default_sequence.findText(default_sequence)
                if index >= 0:
                    self.default_sequence.setCurrentIndex(index)
                else:
                    self.default_sequence.setCurrentText(default_sequence)
                    
            self.autostart_sequence.setChecked(self.settings_model.get("autostart_sequence", False))
            self.loop_sequence.setChecked(self.settings_model.get("loop_sequence", False))
            
            # Window
            capture_method = self.settings_model.get("capture_method", "win32")
            index = self.capture_method.findText(capture_method)
            if index >= 0:
                self.capture_method.setCurrentIndex(index)
                
            self.window_title.setText(self.settings_model.get("window_title", "Total Battle"))
            self.auto_find.setChecked(self.settings_model.get("auto_find_window", True))
            self.region_padding.setValue(self.settings_model.get("region_padding", 5))
            self.capture_interval.setValue(self.settings_model.get("capture_interval", 200))
            
            self.overlay_enabled.setChecked(self.settings_model.get("overlay_enabled", True))
            
            self.highlight_color = self.settings_model.get("highlight_color", "#00FF00")
            self._update_color_button(self.highlight_color_btn, self.highlight_color)
            
            self.text_color = self.settings_model.get("text_color", "#FFFF00")
            self._update_color_button(self.text_color_btn, self.text_color)
            
            self.show_confidence.setChecked(self.settings_model.get("show_confidence", True))
            self.overlay_refresh.setValue(self.settings_model.get("overlay_refresh_rate", 100))
            self.overlay_opacity.setValue(self.settings_model.get("overlay_opacity", 80))
            self.overlay_opacity.parent().layout().itemAt(1).widget().setText(f"{self.overlay_opacity.value()}%")
            
            self.auto_focus.setChecked(self.settings_model.get("auto_focus", True))
            
            # UI
            theme = self.settings_model.get("theme", "system")
            index = self.theme_combo.findData(theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
                
            self.custom_theme_path.setText(self.settings_model.get("theme_file", ""))
            self._update_theme_file_state()
            
            self.font_size_spinner.setValue(self.settings_model.get("font_size", 10))
            
            font_family = self.settings_model.get("font_family", "System Default")
            index = self.font_family.findText(font_family)
            if index >= 0:
                self.font_family.setCurrentIndex(index)
                
            self.show_tooltips.setChecked(self.settings_model.get("show_tooltips", True))
            self.confirm_actions.setChecked(self.settings_model.get("confirm_actions", True))
            self.show_debug.setChecked(self.settings_model.get("show_debug_info", False))
            
            sidebar_position = self.settings_model.get("sidebar_position", "left")
            index = self.sidebar_position.findText(sidebar_position)
            if index >= 0:
                self.sidebar_position.setCurrentIndex(index)
                
            tab_position = self.settings_model.get("tab_position", "top")
            index = self.tab_position.findText(tab_position)
            if index >= 0:
                self.tab_position.setCurrentIndex(index)
                
            self.recent_files_count.setValue(self.settings_model.get("recent_files_count", 10))
            
            self.enable_sound.setChecked(self.settings_model.get("enable_sound", True))
            self.sound_volume.setValue(self.settings_model.get("sound_volume", 80))
            self.sound_volume.parent().layout().itemAt(1).widget().setText(f"{self.sound_volume.value()}%")
            
            self.desktop_notifications.setChecked(self.settings_model.get("desktop_notifications", True))
            self.status_updates.setChecked(self.settings_model.get("status_updates", True))
            
            # Paths
            self.templates_dir.setText(self.settings_model.get("templates_dir", "./scout/resources/templates"))
            self.models_dir.setText(self.settings_model.get("models_dir", "./scout/resources/models"))
            self.states_dir.setText(self.settings_model.get("state_dir", "./scout/resources/states"))
            self.logs_dir.setText(self.settings_model.get("logs_dir", "./scout/resources/logs"))
            self.sequences_dir.setText(self.settings_model.get("sequences_dir", "./scout/resources/sequences"))
            self.screenshots_dir.setText(self.settings_model.get("screenshots_dir", "./scout/resources/screenshots"))
            
            # Advanced
            self.thread_count.setValue(self.settings_model.get("thread_count", 4))
            
            priority = self.settings_model.get("process_priority", "normal")
            index = self.process_priority.findText(priority)
            if index >= 0:
                self.process_priority.setCurrentIndex(index)
                
            self.image_cache_size.setValue(self.settings_model.get("image_cache_size", 100))
            self.parallel_processing.setChecked(self.settings_model.get("parallel_processing", True))
            
            log_level = self.settings_model.get("log_level", "INFO")
            index = self.log_level.findText(log_level)
            if index >= 0:
                self.log_level.setCurrentIndex(index)
                
            self.log_to_file.setChecked(self.settings_model.get("log_to_file", True))
            self.log_format.setText(self.settings_model.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self.debug_window.setChecked(self.settings_model.get("debug_window", False))
            self.performance_monitoring.setChecked(self.settings_model.get("performance_monitoring", False))
            
            self.development_mode.setChecked(self.settings_model.get("development_mode", False))
            self.remote_debugging.setChecked(self.settings_model.get("remote_debugging", False))
            self.remote_debugging_port.setValue(self.settings_model.get("remote_debugging_port", 5678))
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
        finally:
            self._updating_ui = False
    
    def _collect_settings_from_ui(self) -> None:
        """Collect settings from UI widgets into the model."""
        try:
            # Detection - General
            self.settings_model.set("use_caching", self.use_cache.isChecked())
            self.settings_model.set("cache_timeout", self.cache_timeout.value())
            self.settings_model.set("cache_size", self.cache_size.value())
            self.settings_model.set("result_sorting", self.result_sorting.currentText())
            self.settings_model.set("grouping_radius", self.grouping_radius.value())
            self.settings_model.set("max_results", self.max_results.value())
            
            # Detection - Template Matching
            self.settings_model.set("template_method", self.template_method.currentText())
            self.settings_model.set("template_confidence", self.template_confidence.value() / 100.0)
            self.settings_model.set("template_max_results", self.template_max_results.value())
            self.settings_model.set("template_grayscale", self.template_grayscale.isChecked())
            self.settings_model.set("template_edge", self.template_edge.isChecked())
            self.settings_model.set("template_scaling", self.template_scaling.isChecked())
            self.settings_model.set("scale_min", self.scale_min.value())
            self.settings_model.set("scale_max", self.scale_max.value())
            self.settings_model.set("scale_steps", self.scale_steps.value())
            
            # Detection - OCR
            self.settings_model.set("ocr_engine", self.ocr_engine.currentText())
            self.settings_model.set("ocr_language", self.ocr_language.currentText())
            self.settings_model.set("ocr_confidence", self.ocr_confidence.value() / 100.0)
            self.settings_model.set("ocr_whitespace", self.ocr_whitespace.isChecked())
            self.settings_model.set("ocr_preprocessing", self.ocr_preprocessing.currentText())
            self.settings_model.set("ocr_custom_params", self.ocr_custom_params.text())
            self.settings_model.set("ocr_whitelist", self.ocr_whitelist.text())
            
            # Detection - YOLO
            self.settings_model.set("yolo_model", self.yolo_model.currentText())
            self.settings_model.set("yolo_model_file", self.yolo_model_file.text())
            self.settings_model.set("yolo_confidence", self.yolo_confidence.value() / 100.0)
            self.settings_model.set("yolo_overlap", self.yolo_overlap.value() / 100.0)
            self.settings_model.set("yolo_classes", self.yolo_classes.text())
            self.settings_model.set("yolo_gpu", self.yolo_gpu.isChecked())
            
            # Automation
            self.settings_model.set("click_delay", self.click_delay.value())
            self.settings_model.set("double_click_delay", self.double_click_delay.value())
            self.settings_model.set("typing_speed", self.typing_speed.currentText())
            self.settings_model.set("default_wait_time", self.default_wait.value())
            self.settings_model.set("mouse_speed", self.mouse_speed.value())
            self.settings_model.set("randomize_movements", self.randomize_movements.isChecked())
            self.settings_model.set("error_handling", self.error_handling.currentText())
            self.settings_model.set("max_retries", self.max_retries.value())
            self.settings_model.set("retry_delay", self.retry_delay.value())
            self.settings_model.set("jitter_min", self.jitter_min.value())
            self.settings_model.set("jitter_max", self.jitter_max.value())
            self.settings_model.set("detection_interval", self.detection_interval.value())
            self.settings_model.set("sequences_dir", self.sequence_dir.text())
            self.settings_model.set("default_sequence", self.default_sequence.currentText())
            self.settings_model.set("autostart_sequence", self.autostart_sequence.isChecked())
            self.settings_model.set("loop_sequence", self.loop_sequence.isChecked())
            
            # Window
            self.settings_model.set("capture_method", self.capture_method.currentText())
            self.settings_model.set("window_title", self.window_title.text())
            self.settings_model.set("auto_find_window", self.auto_find.isChecked())
            self.settings_model.set("region_padding", self.region_padding.value())
            self.settings_model.set("capture_interval", self.capture_interval.value())
            self.settings_model.set("overlay_enabled", self.overlay_enabled.isChecked())
            self.settings_model.set("highlight_color", self.highlight_color)
            self.settings_model.set("text_color", self.text_color)
            self.settings_model.set("show_confidence", self.show_confidence.isChecked())
            self.settings_model.set("overlay_refresh_rate", self.overlay_refresh.value())
            self.settings_model.set("overlay_opacity", self.overlay_opacity.value())
            self.settings_model.set("auto_focus", self.auto_focus.isChecked())
            
            # UI
            self.settings_model.set("theme", self.theme_combo.currentData())
            self.settings_model.set("theme_file", self.custom_theme_path.text())
            self.settings_model.set("font_size", self.font_size_spinner.value())
            self.settings_model.set("font_family", self.font_family.currentText())
            self.settings_model.set("show_tooltips", self.show_tooltips.isChecked())
            self.settings_model.set("confirm_actions", self.confirm_actions.isChecked())
            self.settings_model.set("show_debug_info", self.show_debug.isChecked())
            self.settings_model.set("sidebar_position", self.sidebar_position.currentText())
            self.settings_model.set("tab_position", self.tab_position.currentText())
            self.settings_model.set("recent_files_count", self.recent_files_count.value())
            self.settings_model.set("enable_sound", self.enable_sound.isChecked())
            self.settings_model.set("sound_volume", self.sound_volume.value())
            self.settings_model.set("desktop_notifications", self.desktop_notifications.isChecked())
            self.settings_model.set("status_updates", self.status_updates.isChecked())
            
            # Paths
            self.settings_model.set("templates_dir", self.templates_dir.text())
            self.settings_model.set("models_dir", self.models_dir.text())
            self.settings_model.set("state_dir", self.states_dir.text())
            self.settings_model.set("logs_dir", self.logs_dir.text())
            self.settings_model.set("sequences_dir", self.sequences_dir.text())
            self.settings_model.set("screenshots_dir", self.screenshots_dir.text())
            
            # Advanced
            self.settings_model.set("thread_count", self.thread_count.value())
            self.settings_model.set("process_priority", self.process_priority.currentText())
            self.settings_model.set("image_cache_size", self.image_cache_size.value())
            self.settings_model.set("parallel_processing", self.parallel_processing.isChecked())
            self.settings_model.set("log_level", self.log_level.currentText())
            self.settings_model.set("log_to_file", self.log_to_file.isChecked())
            self.settings_model.set("log_format", self.log_format.text())
            self.settings_model.set("debug_window", self.debug_window.isChecked())
            self.settings_model.set("performance_monitoring", self.performance_monitoring.isChecked())
            self.settings_model.set("development_mode", self.development_mode.isChecked())
            self.settings_model.set("remote_debugging", self.remote_debugging.isChecked())
            self.settings_model.set("remote_debugging_port", self.remote_debugging_port.value())
            
        except Exception as e:
            logger.error(f"Error collecting settings: {e}", exc_info=True)
    
    def _mark_settings_changed(self) -> None:
        """Mark settings as changed in the UI."""
        if self._updating_ui:
            return
            
        self.status_label.setText("Settings have been modified (not saved)")
        self.status_label.setStyleSheet("color: blue;")
    
    def _auto_save_settings(self) -> None:
        """Auto-save settings if they have been changed."""
        if self.status_label.text() == "Settings have been modified (not saved)":
            self._on_save_clicked(show_dialog=False)
    
    def _on_save_clicked(self, show_dialog: bool = True) -> None:
        """
        Handle save button click.
        
        Args:
            show_dialog: Whether to show a success dialog
        """
        # Collect settings from UI
        self._collect_settings_from_ui()
        
        # Save settings
        if self.settings_model.save():
            self.status_label.setText("All settings up to date")
            self.status_label.setStyleSheet("")
            
            if show_dialog:
                QMessageBox.information(
                    self,
                    "Settings Saved",
                    "Settings have been saved successfully."
                )
            
            # Emit settings changed signal
            self.settings_changed.emit(self.settings_model.get_all())
        else:
            self.status_label.setText("Error saving settings")
            self.status_label.setStyleSheet("color: red;")
            
            if show_dialog:
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
        self.settings_model.reset_to_default()
        
        # Update UI
        self._load_settings_to_ui()
        
        # Update status
        self.status_label.setText("Settings reset to defaults")
        self.status_label.setStyleSheet("color: green;")
        
        QMessageBox.information(
            self,
            "Settings Reset",
            "Settings have been reset to default values."
        )
        
        # Emit settings changed signal
        self.settings_changed.emit(self.settings_model.get_all())
    
    def _on_import_clicked(self) -> None:
        """Handle import button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            str(Path.home()),
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Load settings from file
            result = self.settings_model.load_from_file(file_path)
            
            if result:
                # Update UI
                self._load_settings_to_ui()
                
                # Update status
                self.status_label.setText(f"Settings imported from {file_path}")
                self.status_label.setStyleSheet("color: green;")
                
                QMessageBox.information(
                    self,
                    "Settings Imported",
                    f"Settings have been imported from {file_path}"
                )
                
                # Emit settings changed signal
                self.settings_changed.emit(self.settings_model.get_all())
            else:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    "Failed to import settings. See logs for details."
                )
        except Exception as e:
            logger.error(f"Error importing settings: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred while importing settings: {str(e)}"
            )
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            str(Path.home()),
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Collect settings from UI
            self._collect_settings_from_ui()
            
            # Save settings to file
            result = self.settings_model.save_to_file(file_path)
            
            if result:
                QMessageBox.information(
                    self,
                    "Settings Exported",
                    f"Settings have been exported to {file_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to export settings. See logs for details."
                )
        except Exception as e:
            logger.error(f"Error exporting settings: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred while exporting settings: {str(e)}"
            )
    
    def _on_color_button_clicked(self, button: QPushButton, setting_name: str) -> None:
        """
        Handle color button click.
        
        Args:
            button: Button that was clicked
            setting_name: Name of the setting to update
        """
        # Get current color
        current_color = QColor(getattr(self, setting_name))
        
        # Show color dialog
        color = QColorDialog.getColor(
            current_color,
            self,
            f"Choose {setting_name.replace('_', ' ').title()}"
        )
        
        if color.isValid():
            # Update color
            color_hex = color.name()
            setattr(self, setting_name, color_hex)
            self._update_color_button(button, color_hex)
            
            # Mark settings as changed
            self._mark_settings_changed()
    
    def _update_color_button(self, button: QPushButton, color_str: str) -> None:
        """
        Update color button appearance.
        
        Args:
            button: Button to update
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
        
        button.setStyleSheet(style)
        button.setText(color_str)
    
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
    
    def _browse_file(self, line_edit: QLineEdit, filter_str: str) -> None:
        """
        Open file browser dialog.
        
        Args:
            line_edit: Line edit to update with selected file
            filter_str: Filter string for file dialog
        """
        # Get current directory
        current_file = line_edit.text()
        current_dir = os.path.dirname(current_file) if current_file else ""
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            current_dir,
            filter_str
        )
        
        if file_path:
            line_edit.setText(file_path)
    
    def _update_sequence_list(self) -> None:
        """Update the sequence list based on the selected directory."""
        try:
            # Get sequence directory
            sequence_dir = self.sequence_dir.text()
            
            # Clear current list
            self.default_sequence.clear()
            
            # Add empty option
            self.default_sequence.addItem("")
            
            # Check if directory exists
            if not os.path.exists(sequence_dir):
                return
                
            # List JSON files in directory
            for file_name in os.listdir(sequence_dir):
                if file_name.endswith(".json"):
                    sequence_name = os.path.splitext(file_name)[0]
                    self.default_sequence.addItem(sequence_name)
                    
        except Exception as e:
            logger.error(f"Error updating sequence list: {e}", exc_info=True)
    
    def _update_theme_file_state(self) -> None:
        """Update the theme file input state based on theme selection."""
        is_custom = self.theme_combo.currentText() == "custom"
        self.custom_theme_check.setEnabled(is_custom)
        self.custom_theme_path.setEnabled(is_custom)
        self.browse_theme_button.setEnabled(is_custom)
    
    def _create_missing_directories(self) -> None:
        """Create missing directories from path settings."""
        directories = [
            self.templates_dir.text(),
            self.models_dir.text(),
            self.states_dir.text(),
            self.logs_dir.text(),
            self.sequences_dir.text(),
            self.screenshots_dir.text()
        ]
        
        created_count = 0
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    created_count += 1
                    logger.info(f"Created directory: {directory}")
                except Exception as e:
                    logger.error(f"Error creating directory {directory}: {e}")
        
        if created_count > 0:
            QMessageBox.information(
                self,
                "Directories Created",
                f"Created {created_count} missing directories."
            )
        else:
            QMessageBox.information(
                self,
                "Directories",
                "All directories already exist."
            )
    
    def _export_full_configuration(self) -> None:
        """Export the full configuration including system information."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Full Configuration",
            str(Path.home()),
            "Text Files (*.txt)"
        )
        
        if not file_path:
            return
            
        try:
            # Collect settings from UI
            self._collect_settings_from_ui()
            
            # Get all settings
            settings = self.settings_model.get_all()
            
            # Create report
            with open(file_path, 'w') as f:
                # Write header
                f.write("Scout Application Configuration Report\n")
                f.write("=" * 50 + "\n\n")
                
                # Write system information
                f.write("System Information:\n")
                f.write("-" * 50 + "\n")
                
                import platform
                import sys
                import datetime
                
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Python Version: {sys.version}\n")
                f.write(f"Platform: {platform.platform()}\n")
                f.write(f"Machine: {platform.machine()}\n")
                f.write(f"Processor: {platform.processor()}\n")
                
                # Try to get more detailed information if available
                try:
                    import psutil
                    f.write(f"CPU Cores: {psutil.cpu_count(logical=False)} (Physical), {psutil.cpu_count()} (Logical)\n")
                    f.write(f"Total Memory: {psutil.virtual_memory().total / (1024 ** 3):.2f} GB\n")
                except ImportError:
                    pass
                
                f.write("\n")
                
                # Write application settings
                f.write("Application Settings:\n")
                f.write("-" * 50 + "\n")
                
                # Format settings as readable text
                for key, value in settings.items():
                    if isinstance(value, dict):
                        f.write(f"\n{key}:\n")
                        for sub_key, sub_value in value.items():
                            f.write(f"  {sub_key}: {sub_value}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            
            QMessageBox.information(
                self,
                "Configuration Exported",
                f"Full configuration has been exported to {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred while exporting configuration: {str(e)}"
            )
    
    def _confirm_factory_reset(self) -> None:
        """Confirm and perform factory reset of all settings."""
        # Confirm reset with a more serious warning
        result = QMessageBox.warning(
            self,
            "Factory Reset",
            "Warning: This will reset ALL settings to factory defaults and cannot be undone. "
            "Are you absolutely sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Double-confirm with a text challenge
        confirmation_text, ok = QInputDialog.getText(
            self,
            "Confirm Factory Reset",
            "Type 'RESET' to confirm factory reset:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or confirmation_text != "RESET":
            return
            
        try:
            # Delete the settings file
            settings_file = self.settings_model.settings_file
            if os.path.exists(settings_file):
                os.remove(settings_file)
                
            # Clear QSettings
            qsettings = QSettings("ScoutTeam", "Scout")
            qsettings.clear()
            
            # Reset settings model
            self.settings_model = SettingsModel()
            
            # Update UI
            self._load_settings_to_ui()
            
            # Update status
            self.status_label.setText("Factory reset completed")
            self.status_label.setStyleSheet("color: green;")
            
            QMessageBox.information(
                self,
                "Factory Reset Complete",
                "All settings have been reset to factory defaults. "
                "You may need to restart the application for all changes to take effect."
            )
            
            # Emit settings changed signal
            self.settings_changed.emit(self.settings_model.get_all())
            
        except Exception as e:
            logger.error(f"Error performing factory reset: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Factory Reset Error",
                f"An error occurred during factory reset: {str(e)}"
            )
    
    def get_settings(self) -> Dict:
        """
        Get current settings.
        
        Returns:
            dict: Settings dictionary
        """
        # Collect latest settings from UI
        self._collect_settings_from_ui()
        return self.settings_model.get_all()

    def _on_theme_changed(self, index):
        """
        Handle theme selection change.
        
        Args:
            index: Index of the selected item
        """
        self._mark_settings_changed()
        
        # Enable/disable custom theme controls
        theme = self.theme_combo.currentData()
        is_custom = (theme == "custom")
        self.custom_theme_check.setEnabled(is_custom)
        if is_custom:
            self.custom_theme_path.setEnabled(self.custom_theme_check.isChecked())
            self.browse_theme_button.setEnabled(self.custom_theme_check.isChecked())
        else:
            self.custom_theme_path.setEnabled(False)
            self.browse_theme_button.setEnabled(False)
    
    def _on_language_changed(self, index):
        """
        Handle language selection change.
        
        Args:
            index: Index of the selected item
        """
        lang_value = self.language_combo.currentData()
        
        # Convert string value to Language enum
        try:
            lang = Language(lang_value)
            
            # Update language
            success = self._language_manager.set_language(lang)
            if not success:
                QMessageBox.warning(
                    self,
                    tr("Language Error"),
                    tr("Failed to apply the selected language. Some UI elements may not be translated correctly.")
                )
            
            logger.info(f"Language changed to: {lang.value}")
            
        except ValueError:
            logger.error(f"Invalid language value: {lang_value}")
    
    def _save_settings(self):
        """Save settings to QSettings."""
        # Save UI settings
        self._settings.setValue("ui/theme", self.theme_combo.currentData())
        self._settings.setValue("ui/use_custom_theme", self.custom_theme_check.isChecked())
        self._settings.setValue("ui/custom_theme_path", self.custom_theme_path.text())
        self._settings.setValue("ui/font_size", self.font_size_spinner.value())
        
        # Don't need to save language here as it's handled by the LanguageManager
        
        self._modified = False
        logger.info("Settings saved")
    
    def _mark_settings_changed(self):
        """Mark settings as changed."""
        self._modified = True
    
    def _on_theme_changed(self, index):
        """
        Handle theme selection change.
        
        Args:
            index: Index of the selected item
        """
        self._mark_settings_changed()
        
        # Enable/disable custom theme controls
        theme = self.theme_combo.currentData()
        is_custom = (theme == "custom")
        self.custom_theme_check.setEnabled(is_custom)
        if is_custom:
            self.custom_theme_path.setEnabled(self.custom_theme_check.isChecked())
            self.browse_theme_button.setEnabled(self.custom_theme_check.isChecked())
        else:
            self.custom_theme_path.setEnabled(False)
            self.browse_theme_button.setEnabled(False)
    
    def _on_language_changed(self, index):
        """
        Handle language selection change.
        
        Args:
            index: Index of the selected item
        """
        lang_value = self.language_combo.currentData()
        
        # Convert string value to Language enum
        try:
            lang = Language(lang_value)
            
            # Update language
            success = self._language_manager.set_language(lang)
            if not success:
                QMessageBox.warning(
                    self,
                    tr("Language Error"),
                    tr("Failed to apply the selected language. Some UI elements may not be translated correctly.")
                )
            
            logger.info(f"Language changed to: {lang.value}")
            
        except ValueError:
            logger.error(f"Invalid language value: {lang_value}") 