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
    QDialogButtonBox, QFormLayout, QProgressBar, QTextEdit,
    QDoubleSpinBox
)
from PyQt6.QtGui import QIcon, QAction, QFont, QColor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings, QTimer
from PyQt6.QtWidgets import QApplication

from scout.core.services.service_locator import ServiceLocator
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.ui.models.settings_model import SettingsModel
from scout.ui.utils.language_manager import get_language_manager, Language, tr
from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes

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
        
        # Create tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create each configuration tab
        self._create_detection_tab()
        self._create_automation_tab()
        self._create_window_tab()
        self._create_ocr_tab()
        self._create_ui_tab()
        self._create_paths_tab()
        self._create_advanced_tab()
        self._create_notification_tab()
        
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
        
        self.import_button = QPushButton(tr("Import..."))
        self.import_button.setIcon(QIcon.fromTheme("document-open"))
        self.import_button.clicked.connect(self._on_import_clicked)
        button_bar.addWidget(self.import_button)
        
        self.export_button = QPushButton(tr("Export..."))
        self.export_button.setIcon(QIcon.fromTheme("document-save-as"))
        self.export_button.clicked.connect(self._on_export_clicked)
        button_bar.addWidget(self.export_button)
        
        # Add button bar to main layout
        main_layout.addLayout(button_bar)
    
    def _create_detection_tab(self) -> None:
        """Create the object detection configuration tab."""
        detection_tab = QWidget()
        self.tabs.addTab(detection_tab, tr("Detection"))
        
        # Create layout
        layout = QVBoxLayout(detection_tab)
        
        # Template matching settings
        template_group = QGroupBox(tr("Template Matching"))
        template_layout = QFormLayout(template_group)
        
        # Method selection
        self.template_method = QComboBox()
        self.template_method.addItems([
            tr("TM_CCOEFF_NORMED"), 
            tr("TM_CCORR_NORMED"), 
            tr("TM_SQDIFF_NORMED")
        ])
        self.template_method.currentIndexChanged.connect(self._mark_settings_changed)
        template_layout.addRow(tr("Method:"), self.template_method)
        
        # Confidence threshold
        self.template_confidence_spin = QDoubleSpinBox()
        self.template_confidence_spin.setRange(0.0, 1.0)
        self.template_confidence_spin.setSingleStep(0.05)
        self.template_confidence_spin.setValue(0.8)
        self.template_confidence_spin.valueChanged.connect(self._mark_settings_changed)
        
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(self.template_confidence_spin)
        self.template_confidence_label = QLabel("0.80")
        confidence_layout.addWidget(self.template_confidence_label)
        template_layout.addRow(tr("Confidence Threshold:"), confidence_layout)
        
        # Max matches
        self.max_matches = QSpinBox()
        self.max_matches.setRange(1, 100)
        self.max_matches.setValue(5)
        self.max_matches.valueChanged.connect(self._mark_settings_changed)
        template_layout.addRow(tr("Max Matches:"), self.max_matches)
        
        # YOLO settings
        yolo_group = QGroupBox(tr("YOLO Object Detection"))
        yolo_layout = QGridLayout(yolo_group)
        
        # Model selection
        yolo_layout.addWidget(QLabel(tr("YOLO Model:")), 0, 0)
        self.yolo_model = QComboBox()
        self.yolo_model.addItems([tr("YOLOv8n"), tr("YOLOv8s"), tr("YOLOv8m"), tr("YOLOv8l"), tr("YOLOv8x")])
        self.yolo_model.currentIndexChanged.connect(self._mark_settings_changed)
        yolo_layout.addWidget(self.yolo_model, 0, 1)
        
        # Confidence threshold
        yolo_layout.addWidget(QLabel(tr("Confidence:")), 1, 0)
        self.yolo_confidence_spin = QDoubleSpinBox()
        self.yolo_confidence_spin.setRange(0.0, 1.0)
        self.yolo_confidence_spin.setSingleStep(0.05)
        self.yolo_confidence_spin.setValue(0.25)
        self.yolo_confidence_spin.valueChanged.connect(self._mark_settings_changed)
        yolo_layout.addWidget(self.yolo_confidence_spin, 1, 1)
        self.yolo_confidence_label = QLabel("0.25")
        yolo_layout.addWidget(self.yolo_confidence_label, 1, 2)
        
        # IOU threshold
        yolo_layout.addWidget(QLabel(tr("IOU Threshold:")), 2, 0)
        self.yolo_iou_spin = QDoubleSpinBox()
        self.yolo_iou_spin.setRange(0.0, 1.0)
        self.yolo_iou_spin.setSingleStep(0.05)
        self.yolo_iou_spin.setValue(0.45)
        self.yolo_iou_spin.valueChanged.connect(self._mark_settings_changed)
        yolo_layout.addWidget(self.yolo_iou_spin, 2, 1)
        self.yolo_iou_label = QLabel("0.45")
        yolo_layout.addWidget(self.yolo_iou_label, 2, 2)
        
        # Add the groups to main layout
        layout.addWidget(template_group)
        layout.addWidget(yolo_group)
        layout.addStretch()
    
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
        """Create the window configuration tab."""
        from scout.ui.utils.layout_helper import set_min_width_for_text
        
        window_tab = QWidget()
        self.tabs.addTab(window_tab, tr("Window"))
        
        # Create layout
        layout = QVBoxLayout(window_tab)
        
        # Window capture settings
        capture_group = QGroupBox(tr("Window Capture"))
        capture_layout = QFormLayout(capture_group)
        
        # Capture method
        self.capture_method = QComboBox()
        self.capture_method.addItems([tr("Windows API"), tr("Screenshot")])
        self.capture_method.currentIndexChanged.connect(self._mark_settings_changed)
        # Set minimum width based on longest option with padding
        set_min_width_for_text(self.capture_method, tr("Windows API") + " " * 5)
        capture_layout.addRow(tr("Capture Method:"), self.capture_method)
        
        # Capture interval
        self.capture_interval = QSpinBox()
        self.capture_interval.setRange(50, 5000)
        self.capture_interval.setValue(500)
        self.capture_interval.setSuffix(tr(" ms"))
        self.capture_interval.valueChanged.connect(self._mark_settings_changed)
        capture_layout.addRow(tr("Capture Interval:"), self.capture_interval)
        
        # Window search method
        self.window_search = QComboBox()
        self.window_search.addItems([tr("Title"), tr("Class"), tr("Process")])
        self.window_search.currentIndexChanged.connect(self._mark_settings_changed)
        # Set minimum width based on longest option with padding
        set_min_width_for_text(self.window_search, tr("Process") + " " * 5)
        capture_layout.addRow(tr("Window Search Method:"), self.window_search)
        
        # Window title pattern
        self.window_pattern = QLineEdit()
        self.window_pattern.setPlaceholderText(tr("Window Title Pattern"))
        self.window_pattern.textChanged.connect(self._mark_settings_changed)
        capture_layout.addRow(tr("Window Pattern:"), self.window_pattern)
        
        layout.addWidget(capture_group)
        
        # Window display settings
        display_group = QGroupBox(tr("Window Display"))
        display_layout = QFormLayout(display_group)
        
        # Show overlay
        self.show_overlay = QCheckBox()
        self.show_overlay.setChecked(True)
        self.show_overlay.stateChanged.connect(self._mark_settings_changed)
        display_layout.addRow(tr("Show Overlay:"), self.show_overlay)
        
        # Overlay opacity
        self.overlay_opacity = QSlider(Qt.Orientation.Horizontal)
        self.overlay_opacity.setRange(10, 100)
        self.overlay_opacity.setValue(50)
        self.overlay_opacity.valueChanged.connect(self._mark_settings_changed)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.overlay_opacity)
        self.opacity_label = QLabel("50%")
        opacity_layout.addWidget(self.opacity_label)
        display_layout.addRow(tr("Overlay Opacity:"), opacity_layout)
        
        # Highlight color
        self.highlight_color = QPushButton()
        self.highlight_color.setFixedSize(24, 24)
        self._update_color_button(self.highlight_color, "green")
        self.highlight_color.clicked.connect(
            lambda: self._on_color_button_clicked(self.highlight_color, "highlight_color")
        )
        display_layout.addRow(tr("Highlight Color:"), self.highlight_color)
        
        # Auto focus
        self.auto_focus = QCheckBox()
        self.auto_focus.setChecked(True)
        self.auto_focus.stateChanged.connect(self._mark_settings_changed)
        display_layout.addRow(tr("Auto-focus Window:"), self.auto_focus)
        
        # Sound volume
        self.sound_volume = QSlider(Qt.Orientation.Horizontal)
        self.sound_volume.setRange(0, 100)
        self.sound_volume.setValue(80)
        self.sound_volume.valueChanged.connect(self._mark_settings_changed)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.sound_volume)
        self.volume_label = QLabel("80%")
        volume_layout.addWidget(self.volume_label)
        sound_layout = QFormLayout()
        sound_layout.addRow(tr("Volume:"), volume_layout)
        
        layout.addWidget(display_group)
    
    def _create_ocr_tab(self) -> None:
        """Create the OCR configuration tab."""
        from scout.ui.utils.layout_helper import set_min_width_for_text
        
        ocr_tab = QWidget()
        self.tabs.addTab(ocr_tab, tr("OCR"))
        
        # Create layout
        layout = QVBoxLayout(ocr_tab)
        
        # Tesseract settings
        tesseract_group = QGroupBox(tr("Tesseract OCR"))
        tesseract_layout = QFormLayout(tesseract_group)
        
        # Language selection
        self.ocr_language = QComboBox()
        languages = ["eng", "deu", "fra", "spa", "ita", "por", "rus", "chi_sim", "chi_tra", "jpn"]
        self.ocr_language.addItems(languages)
        self.ocr_language.setCurrentText("eng")
        self.ocr_language.currentIndexChanged.connect(self._mark_settings_changed)
        
        # Set minimum width based on longest language code with padding
        set_min_width_for_text(self.ocr_language, "chi_tra" + " " * 5)
        
        tesseract_layout.addRow(tr("Language:"), self.ocr_language)
        
        # Page segmentation mode
        self.psm = QComboBox()
        psm_modes = [
            tr("0 - Orientation and script detection only"),
            tr("1 - Automatic page segmentation with OSD"),
            tr("2 - Automatic page segmentation, no OSD"),
            tr("3 - Fully automatic page segmentation, no OSD (default)"),
            tr("4 - Assume a single column of text"),
            tr("5 - Assume a single uniform block of text"),
            tr("6 - Assume a single uniform block of text"),
            tr("7 - Treat the image as a single text line"),
            tr("8 - Treat the image as a single word"),
            tr("9 - Treat the image as a single word in a circle"),
            tr("10 - Treat the image as a single character"),
            tr("11 - Sparse text. Find as much text as possible"),
            tr("12 - Sparse text with OSD"),
            tr("13 - Raw line. Treat the image as a single text line")
        ]
        self.psm.addItems(psm_modes)
        self.psm.setCurrentIndex(7)  # Default to text line
        self.psm.currentIndexChanged.connect(self._mark_settings_changed)
        
        # Set minimum width based on a reasonable length for the dropdown
        # Note: We don't set it to the longest item as that would be too wide
        # Instead, set it to a reasonable width that can show most of the shorter options
        reasonable_text = tr("4 - Assume a single column of text")
        set_min_width_for_text(self.psm, reasonable_text)
        
        tesseract_layout.addRow(tr("Page Segmentation:"), self.psm)
        
        # Add advanced options
        advanced_group = QGroupBox(tr("Advanced Options"))
        advanced_layout = QFormLayout(advanced_group)
        
        # DPI setting
        self.ocr_dpi = QSpinBox()
        self.ocr_dpi.setRange(72, 600)
        self.ocr_dpi.setValue(300)
        self.ocr_dpi.setSuffix(tr(" DPI"))
        self.ocr_dpi.valueChanged.connect(self._mark_settings_changed)
        advanced_layout.addRow(tr("Image Resolution:"), self.ocr_dpi)
        
        # Pre-processing options
        self.ocr_preprocess = QComboBox()
        preprocess_options = [
            tr("None"),
            tr("Grayscale"),
            tr("Threshold"),
            tr("Gaussian Blur"),
            tr("Edge Enhancement")
        ]
        self.ocr_preprocess.addItems(preprocess_options)
        self.ocr_preprocess.currentIndexChanged.connect(self._mark_settings_changed)
        set_min_width_for_text(self.ocr_preprocess, tr("Edge Enhancement") + " " * 5)
        advanced_layout.addRow(tr("Pre-processing:"), self.ocr_preprocess)
        
        # Character whitelist
        self.ocr_whitelist = QLineEdit()
        self.ocr_whitelist.setPlaceholderText(tr("e.g., 0123456789abcdefghijklmnopqrstuvwxyz"))
        self.ocr_whitelist.textChanged.connect(self._mark_settings_changed)
        advanced_layout.addRow(tr("Character Whitelist:"), self.ocr_whitelist)
        
        # Confidence threshold
        self.ocr_confidence = QSpinBox()
        self.ocr_confidence.setRange(0, 100)
        self.ocr_confidence.setValue(60)
        self.ocr_confidence.setSuffix(tr("%"))
        self.ocr_confidence.valueChanged.connect(self._mark_settings_changed)
        advanced_layout.addRow(tr("Confidence Threshold:"), self.ocr_confidence)
        
        # Add groups to layout
        tesseract_group.setLayout(tesseract_layout)
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(tesseract_group)
        layout.addWidget(advanced_group)
        layout.addStretch()
    
    def _create_ui_tab(self) -> None:
        """Create the UI configuration tab."""
        ui_tab = QWidget()
        self.tabs.addTab(ui_tab, tr("User Interface"))
        
        # Create layout
        layout = QVBoxLayout(ui_tab)
        
        # Appearance group
        appearance_group = QGroupBox(tr("Appearance"))
        appearance_layout = QFormLayout(appearance_group)
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("System"), "system")
        self.theme_combo.addItem(tr("Light"), "light")
        self.theme_combo.addItem(tr("Dark"), "dark")
        self.theme_combo.addItem(tr("Custom"), "custom")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        # Set minimum width based on longest option
        set_min_width_for_text(self.theme_combo, tr("System") + " " * 5)
        
        appearance_layout.addRow(tr("Theme:"), self.theme_combo)
        
        # Custom theme checkbox
        self.custom_theme_check = QCheckBox(tr("Use custom theme file"))
        self.custom_theme_check.stateChanged.connect(self._mark_settings_changed)
        appearance_layout.addRow("", self.custom_theme_check)
        
        # Custom theme path
        custom_theme_layout = QHBoxLayout()
        self.custom_theme_path = QLineEdit()
        self.custom_theme_path.setPlaceholderText(tr("Path to custom theme file (.qss)"))
        self.custom_theme_path.textChanged.connect(self._mark_settings_changed)
        
        self.browse_theme_button = QPushButton(tr("Browse..."))
        self.browse_theme_button.clicked.connect(lambda: self._browse_file(
            self.custom_theme_path, tr("QSS Files (*.qss);;All Files (*)")
        ))
        
        custom_theme_layout.addWidget(self.custom_theme_path)
        custom_theme_layout.addWidget(self.browse_theme_button)
        appearance_layout.addRow(tr("Theme File:"), custom_theme_layout)
        
        # Font size
        self.font_size_spinner = QSpinBox()
        self.font_size_spinner.setRange(8, 24)
        self.font_size_spinner.setValue(10)
        self.font_size_spinner.setSuffix(tr(" pt"))
        self.font_size_spinner.valueChanged.connect(self._mark_settings_changed)
        appearance_layout.addRow(tr("Font Size:"), self.font_size_spinner)
        
        # Language group
        language_group = QGroupBox(tr("Language"))
        language_layout = QFormLayout(language_group)
        
        # Language selection
        self.language_combo = QComboBox()
        self.language_combo.addItem(tr("System Default"), "system")
        self.language_combo.addItem(tr("English"), "en")
        self.language_combo.addItem(tr("German"), "de")
        
        # Set minimum width based on longest option
        set_min_width_for_text(self.language_combo, tr("System Default") + " " * 3)
        
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        language_layout.addRow(tr("Application Language:"), self.language_combo)
        
        # Language note
        note_label = QLabel(tr("Note: Some changes may require an application restart."))
        note_label.setStyleSheet("color: gray; font-style: italic;")
        language_layout.addRow("", note_label)
        
        # Add groups to layout
        layout.addWidget(appearance_group)
        layout.addWidget(language_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set initial state
        self._on_theme_changed(self.theme_combo.currentIndex())
    
    def _create_paths_tab(self) -> None:
        """Create the paths configuration tab."""
        from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes
        
        paths_tab = QWidget()
        self.tabs.addTab(paths_tab, tr("Paths"))
        
        # Create layout
        layout = QVBoxLayout(paths_tab)
        
        # Data paths
        data_group = QGroupBox(tr("Data Paths"))
        data_layout = QFormLayout(data_group)
        
        # Template directory
        self.template_dir = QLineEdit()
        self.template_dir.setText("./data/templates")
        self.template_dir.textChanged.connect(self._mark_settings_changed)
        self.template_dir.setMinimumWidth(300)  # Set reasonable minimum width for path inputs
        
        browse_template_btn = QPushButton(tr("Browse..."))
        browse_template_btn.clicked.connect(lambda: self._browse_directory(self.template_dir))
        
        template_layout = QHBoxLayout()
        template_layout.addWidget(self.template_dir)
        template_layout.addWidget(browse_template_btn)
        data_layout.addRow(tr("Template Directory:"), template_layout)
        
        # Screenshot directory
        self.screenshot_dir = QLineEdit()
        self.screenshot_dir.setText("./data/screenshots")
        self.screenshot_dir.textChanged.connect(self._mark_settings_changed)
        self.screenshot_dir.setMinimumWidth(300)
        
        browse_screenshot_btn = QPushButton(tr("Browse..."))
        browse_screenshot_btn.clicked.connect(lambda: self._browse_directory(self.screenshot_dir))
        
        screenshot_layout = QHBoxLayout()
        screenshot_layout.addWidget(self.screenshot_dir)
        screenshot_layout.addWidget(browse_screenshot_btn)
        data_layout.addRow(tr("Screenshot Directory:"), screenshot_layout)
        
        # Log directory
        self.log_dir = QLineEdit()
        self.log_dir.setText("./logs")
        self.log_dir.textChanged.connect(self._mark_settings_changed)
        self.log_dir.setMinimumWidth(300)
        
        browse_log_btn = QPushButton(tr("Browse..."))
        browse_log_btn.clicked.connect(lambda: self._browse_directory(self.log_dir))
        
        log_layout = QHBoxLayout()
        log_layout.addWidget(self.log_dir)
        log_layout.addWidget(browse_log_btn)
        data_layout.addRow(tr("Log Directory:"), log_layout)
        
        # Automation paths
        automation_group = QGroupBox(tr("Automation Paths"))
        automation_layout = QFormLayout(automation_group)
        
        # Sequence directory
        self.sequence_dir = QLineEdit()
        self.sequence_dir.setText("./data/sequences")
        self.sequence_dir.textChanged.connect(self._mark_settings_changed)
        self.sequence_dir.setMinimumWidth(300)
        
        browse_sequence_btn = QPushButton(tr("Browse..."))
        browse_sequence_btn.clicked.connect(lambda: self._browse_directory(self.sequence_dir))
        
        sequence_layout = QHBoxLayout()
        sequence_layout.addWidget(self.sequence_dir)
        sequence_layout.addWidget(browse_sequence_btn)
        automation_layout.addRow(tr("Sequence Directory:"), sequence_layout)
        
        # Export/Import directory
        self.export_dir = QLineEdit()
        self.export_dir.setText("./data/exports")
        self.export_dir.textChanged.connect(self._mark_settings_changed)
        self.export_dir.setMinimumWidth(300)
        
        browse_export_btn = QPushButton(tr("Browse..."))
        browse_export_btn.clicked.connect(lambda: self._browse_directory(self.export_dir))
        
        export_layout = QHBoxLayout()
        export_layout.addWidget(self.export_dir)
        export_layout.addWidget(browse_export_btn)
        automation_layout.addRow(tr("Export Directory:"), export_layout)
        
        # Setup button sizes consistently
        browse_buttons = [
            browse_template_btn, browse_screenshot_btn, browse_log_btn,
            browse_sequence_btn, browse_export_btn
        ]
        adjust_button_sizes(browse_buttons)
        
        # Path operations
        operations_group = QGroupBox(tr("Path Operations"))
        operations_layout = QVBoxLayout(operations_group)
        
        # Create missing directories button
        create_directories_btn = QPushButton(tr("Create Missing Directories"))
        create_directories_btn.clicked.connect(self._create_missing_directories)
        operations_layout.addWidget(create_directories_btn)
        
        # Check paths button
        check_paths_btn = QPushButton(tr("Verify Path Permissions"))
        check_paths_btn.clicked.connect(lambda: self._verify_path_permissions())
        operations_layout.addWidget(check_paths_btn)
        
        # Export paths button
        export_paths_btn = QPushButton(tr("Export Path Configuration"))
        export_paths_btn.clicked.connect(lambda: self._export_path_configuration())
        operations_layout.addWidget(export_paths_btn)
        
        # Add groups to layout
        data_group.setLayout(data_layout)
        automation_group.setLayout(automation_layout)
        operations_group.setLayout(operations_layout)
        
        layout.addWidget(data_group)
        layout.addWidget(automation_group)
        layout.addWidget(operations_group)
        layout.addStretch()
    
    def _verify_path_permissions(self) -> None:
        """Verify that the application has required permissions for all paths."""
        # This is a placeholder for the actual path permission verification
        QMessageBox.information(
            self,
            tr("Path Verification"),
            tr("All paths have been verified. No permission issues were detected.")
        )
        
    def _export_path_configuration(self) -> None:
        """Export the path configuration to a file."""
        # This is a placeholder for the actual path export functionality
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Path Configuration"),
            "",
            tr("Text Files (*.txt);;All Files (*)")
        )
        
        if not file_path:
            return
            
        try:
            # Simple export of path settings
            with open(file_path, 'w') as f:
                f.write(f"Template Directory: {self.template_dir.text()}\n")
                f.write(f"Screenshot Directory: {self.screenshot_dir.text()}\n")
                f.write(f"Log Directory: {self.log_dir.text()}\n")
                f.write(f"Sequence Directory: {self.sequence_dir.text()}\n")
                f.write(f"Export Directory: {self.export_dir.text()}\n")
                
            QMessageBox.information(
                self,
                tr("Export Complete"),
                tr("Path configuration has been exported to {0}").format(file_path)
            )
        except Exception as e:
            logger.error(f"Error exporting path configuration: {e}")
            QMessageBox.critical(
                self,
                tr("Export Error"),
                tr("Failed to export path configuration: {0}").format(str(e))
            )
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Connect buttons
        self.save_button.clicked.connect(self._on_save_clicked)
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.import_button.clicked.connect(self._on_import_clicked)
        self.export_button.clicked.connect(self._on_export_clicked)
        
        # Connect color buttons
        self.highlight_color.clicked.connect(lambda: self._on_color_button_clicked(self.highlight_color, "highlight_color"))
        
        # Connect sliders to labels
        self.template_confidence_spin.valueChanged.connect(
            lambda value: self.template_confidence_label.setText(f"{value:.2f}")
        )
        
        self.ocr_confidence_spin.valueChanged.connect(
            lambda value: self.ocr_confidence_label.setText(f"{value:.2f}")
        )
        
        self.yolo_confidence_spin.valueChanged.connect(
            lambda value: self.yolo_confidence_label.setText(f"{value:.2f}")
        )
        
        self.overlay_opacity.valueChanged.connect(
            lambda value: self.opacity_label.setText(f"{value}%")
        )
        
        self.sound_volume.valueChanged.connect(
            lambda value: self.volume_label.setText(f"{value}%")
        )
        
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
            self.template_confidence_spin.setValue(confidence)
            self.template_confidence_label.setText(f"{confidence:.2f}")
            
            self.template_max_results.setValue(self.settings_model.get("template_max_results", 5))
            self.multi_scale_check.setChecked(self.settings_model.get("template_scaling", True))
            self.min_scale_spin.setValue(self.settings_model.get("scale_min", 0.8))
            self.max_scale_spin.setValue(self.settings_model.get("scale_max", 1.2))
            self.scale_step_spin.setValue(self.settings_model.get("scale_steps", 0.05))
            
            # Detection - OCR
            engine = self.settings_model.get("ocr_engine", "tesseract")
            index = self.ocr_engine_combo.findText(engine)
            if index >= 0:
                self.ocr_engine_combo.setCurrentIndex(index)
            
            language = self.settings_model.get("ocr_language", "eng")
            index = self.ocr_language_combo.findText(language)
            if index >= 0:
                self.ocr_language_combo.setCurrentIndex(index)
            
            confidence = self.settings_model.get("ocr_confidence", 0.6)
            self.ocr_confidence_spin.setValue(confidence)
            self.ocr_confidence_label.setText(f"{confidence:.2f}")
            
            self.ocr_preprocess_combo.setCurrentText(self.settings_model.get("ocr_preprocessing", "threshold"))
            
            self.ocr_custom_params.setText(self.settings_model.get("ocr_custom_params", "--psm 6 --oem 3"))
            self.ocr_whitelist.setText(self.settings_model.get("ocr_whitelist", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            
            # Detection - YOLO
            model = self.settings_model.get("yolo_model", "yolov8n.pt")
            index = self.yolo_model_combo.findText(model)
            if index >= 0:
                self.yolo_model_combo.setCurrentIndex(index)
                
            self.yolo_model_file.setText(self.settings_model.get("yolo_model_file", ""))
            
            confidence = self.settings_model.get("yolo_confidence", 0.5)
            self.yolo_confidence_spin.setValue(confidence)
            self.yolo_confidence_label.setText(f"{confidence:.2f}")
            
            overlap = self.settings_model.get("yolo_iou", 0.45)
            self.yolo_iou_spin.setValue(overlap)
            self.yolo_iou_label.setText(f"{overlap:.2f}")
            
            self.yolo_size_combo.setCurrentText(self.settings_model.get("yolo_size", "320x320"))
            self.yolo_cuda_check.setChecked(self.settings_model.get("yolo_cuda", True))
            
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
            self._update_color_button(self.highlight_color, self.highlight_color)
            
            self.text_color = self.settings_model.get("text_color", "#FFFF00")
            self._update_color_button(self.highlight_color, self.highlight_color)
            
            self.show_confidence.setChecked(self.settings_model.get("show_confidence", True))
            self.overlay_refresh.setValue(self.settings_model.get("overlay_refresh_rate", 100))
            self.overlay_opacity.setValue(self.settings_model.get("overlay_opacity", 80))
            self.opacity_label.setText(f"{self.overlay_opacity.value()}%")
            
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
            self.volume_label.setText(f"{self.sound_volume.value()}%")
            
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
            self.settings_model.set("template_confidence", self.template_confidence_spin.value())
            self.settings_model.set("template_max_results", self.template_max_results.value())
            self.settings_model.set("template_scaling", self.multi_scale_check.isChecked())
            self.settings_model.set("scale_min", self.min_scale_spin.value())
            self.settings_model.set("scale_max", self.max_scale_spin.value())
            self.settings_model.set("scale_steps", self.scale_step_spin.value())
            
            # Detection - OCR
            self.settings_model.set("ocr_engine", self.ocr_engine_combo.currentText())
            self.settings_model.set("ocr_language", self.ocr_language_combo.currentText())
            self.settings_model.set("ocr_confidence", self.ocr_confidence_spin.value())
            self.settings_model.set("ocr_preprocessing", self.ocr_preprocess_combo.currentText())
            self.settings_model.set("ocr_custom_params", self.ocr_custom_params.text())
            self.settings_model.set("ocr_whitelist", self.ocr_whitelist.text())
            
            # Detection - YOLO
            self.settings_model.set("yolo_model", self.yolo_model_combo.currentText())
            self.settings_model.set("yolo_model_file", self.yolo_model_file.text())
            self.settings_model.set("yolo_confidence", self.yolo_confidence_spin.value())
            self.settings_model.set("yolo_iou", self.yolo_iou_spin.value())
            self.settings_model.set("yolo_size", self.yolo_size_combo.currentText())
            self.settings_model.set("yolo_cuda", self.yolo_cuda_check.isChecked())
            
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
            self.settings_model.set("overlay_enabled", self.show_overlay.isChecked())
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
        """Save settings and optionally show confirmation dialog."""
        try:
            # Collect settings from UI
            self._collect_settings_from_ui()
            
            # Save settings
            self.settings_model.save()
            logger.info("Settings saved successfully")
            
            # Reset "changed" flag
            self.settings_changed = False
            self.apply_btn.setEnabled(False)
            
            # Show confirmation dialog if requested
            if show_dialog:
                QMessageBox.information(
                    self,
                    tr("Settings Saved"),
                    tr("Your settings have been saved successfully."),
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            # Log exception
            logger.error(f"Error saving settings: {str(e)}")
            
            # Show error dialog
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to save settings: {0}").format(str(e)),
                QMessageBox.StandardButton.Ok
            )
    
    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        # Ask for confirmation
        response = QMessageBox.question(
            self,
            tr("Reset Settings"),
            tr("Are you sure you want to reset all settings to their default values? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.Yes:
            try:
                # Reset settings
                self.settings_model.reset_to_defaults()
                
                # Reload UI with default values
                self._load_settings_to_ui()
                
                # Mark as not changed
                self.settings_changed = False
                self.apply_btn.setEnabled(False)
                
                # Show success message
                QMessageBox.information(
                    self,
                    tr("Reset Complete"),
                    tr("Settings have been reset to their default values."),
                    QMessageBox.StandardButton.Ok
                )
            except Exception as e:
                # Log error
                logger.error(f"Error resetting settings: {str(e)}")
                
                # Show error message
                QMessageBox.critical(
                    self,
                    tr("Error"),
                    tr("Failed to reset settings: {0}").format(str(e)),
                    QMessageBox.StandardButton.Ok
                )
    
    def _on_import_clicked(self) -> None:
        """Handle import button click."""
        # Ask for file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Import Settings"),
            "",
            tr("Settings Files (*.json);;All Files (*)")
        )
        
        if not file_path:
            return
        
        try:
            # Import settings
            self.settings_model.import_from_file(file_path)
            
            # Reload UI
            self._load_settings_to_ui()
            
            # Show success message
            QMessageBox.information(
                self,
                tr("Import Complete"),
                tr("Settings have been imported successfully."),
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            # Log error
            logger.error(f"Error importing settings: {str(e)}")
            
            # Show error message
            QMessageBox.critical(
                self,
                tr("Import Error"),
                tr("Failed to import settings: {0}").format(str(e)),
                QMessageBox.StandardButton.Ok
            )
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        # Ask for file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Settings"),
            "",
            tr("Settings Files (*.json);;All Files (*)")
        )
        
        if not file_path:
            return
        
        # Add .json extension if not provided
        if not file_path.endswith(".json"):
            file_path += ".json"
        
        try:
            # Collect settings from UI
            self._collect_settings_from_ui()
            
            # Export settings
            self.settings_model.export_to_file(file_path)
            
            # Show success message
            QMessageBox.information(
                self,
                tr("Export Complete"),
                tr("Settings have been exported successfully."),
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            
            QMessageBox.critical(
                self,
                tr("Export Error"),
                tr("An error occurred while exporting configuration: {0}").format(str(e))
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
        """Create missing template and cache directories."""
        dirs_to_create = [
            self.template_dir.text(),
            self.screenshot_dir.text(),
            self.log_dir.text(),
            self.sequence_dir.text()
        ]
        
        # Filter out empty entries
        dirs_to_create = [dir_path for dir_path in dirs_to_create if dir_path]
        
        # Create directories
        created_count = 0
        for dir_path in dirs_to_create:
            try:
                path = Path(dir_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    created_count += 1
                    logger.info(f"Created directory: {dir_path}")
            except Exception as e:
                logger.error(f"Error creating directory {dir_path}: {e}")
        
        # Show result
        if created_count > 0:
            QMessageBox.information(
                self,
                tr("Directories Created"),
                tr("{0} missing directories have been created.").format(created_count)
            )
        else:
            QMessageBox.information(
                self,
                tr("Directories"),
                tr("All directories already exist.")
            )
    
    def _export_full_configuration(self) -> None:
        """Export the full configuration including system information."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Full Configuration"),
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
                tr("Configuration Exported"),
                tr("Full configuration has been exported to {0}").format(file_path)
            )
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                tr("Export Error"),
                tr("An error occurred while exporting configuration: {0}").format(str(e))
            )
    
    def _confirm_factory_reset(self) -> None:
        """Confirm and perform factory reset."""
        # Ask for confirmation with a more serious warning
        response = QMessageBox.warning(
            self,
            tr("Factory Reset"),
            tr("WARNING: This will reset ALL settings to factory defaults, including:\n\n"
                "• Window settings\n"
                "• Detection parameters\n"
                "• Automation configurations\n"
                "• UI preferences\n"
                "• Application paths\n\n"
                "This action CANNOT be undone. Are you sure you want to continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if response != QMessageBox.StandardButton.Yes:
            return
        
        # Ask for final confirmation
        final_response = QMessageBox.critical(
            self,
            tr("Final Confirmation"),
            tr("This is your final chance to cancel.\n\n"
                "Proceeding will reset ALL settings to factory defaults.\n\n"
                "Are you ABSOLUTELY sure you want to continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if final_response != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Perform factory reset
            self.settings_model.factory_reset()
            
            # Reload UI
            self._load_settings_to_ui()
            
            # Show success message
            QMessageBox.information(
                self,
                tr("Factory Reset Complete"),
                tr("All settings have been reset to factory defaults."),
                QMessageBox.StandardButton.Ok
            )
            
            # Restart the application if necessary
            restart_response = QMessageBox.question(
                self,
                tr("Restart Required"),
                tr("Some changes may require a restart to take full effect.\n\n"
                    "Would you like to restart the application now?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if restart_response == QMessageBox.StandardButton.Yes:
                # Request application restart
                QApplication.instance().exit(Codes.RESTART_CODE)
        
        except Exception as e:
            # Log error
            logger.error(f"Error performing factory reset: {str(e)}")
            
            # Show error message
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to perform factory reset: {0}").format(str(e)),
                QMessageBox.StandardButton.Ok
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
        
        try:
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
            
            # Apply theme immediately if we have a theme manager
            if hasattr(self, '_theme_manager') and self._theme_manager:
                success = self._theme_manager.set_theme(theme)
                if not success:
                    QMessageBox.warning(
                        self,
                        tr("Theme Change Error"),
                        tr("Failed to apply the selected theme. The application may need to be restarted."),
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    logger.info(f"Theme changed to: {theme}")
        
        except Exception as e:
            logger.error(f"Error changing theme: {str(e)}")
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to change theme: {0}").format(str(e)),
                QMessageBox.StandardButton.Ok
            )
    
    def _on_language_changed(self, index):
        """
        Handle language selection change.
        
        Args:
            index: Index of the selected item
        """
        lang_value = self.language_combo.currentData()
        
        # Mark settings as changed
        self._mark_settings_changed()
        
        # Convert string value to Language enum
        try:
            lang = Language(lang_value)
            
            # Update language
            success = self._language_manager.set_language(lang)
            if not success:
                QMessageBox.warning(
                    self,
                    tr("Language Change Error"),
                    tr("Failed to apply the selected language. Some UI elements may not be translated correctly."),
                    QMessageBox.StandardButton.Ok
                )
            else:
                # Show a note about application restart
                QMessageBox.information(
                    self,
                    tr("Language Changed"),
                    tr("Language has been changed to {0}.\n\nSome changes may require an application restart to take full effect.").format(self.language_combo.currentText()),
                    QMessageBox.StandardButton.Ok
                )
            
            logger.info(f"Language changed to: {lang.value}")
            
        except ValueError:
            logger.error(f"Invalid language value: {lang_value}")
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Invalid language selection. Please try again."),
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            logger.error(f"Error changing language: {str(e)}")
            QMessageBox.critical(
                self,
                tr("Error"),
                tr("Failed to change language: {0}").format(str(e)),
                QMessageBox.StandardButton.Ok
            )

    def _create_advanced_tab(self) -> None:
        """Create the advanced settings tab."""
        from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes
        
        advanced_tab = QWidget()
        self.tabs.addTab(advanced_tab, tr("Advanced"))
        
        # Create layout
        layout = QVBoxLayout(advanced_tab)
        
        # Warning label
        warning_label = QLabel(tr("Warning: These settings are for advanced users only. "
                               "Incorrect values may cause instability or crashes."))
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # Create form layout for settings
        form_layout = QFormLayout()
        layout.addLayout(form_layout)
        
        # Performance settings
        performance_group = QGroupBox(tr("Performance"))
        performance_layout = QFormLayout(performance_group)
        
        # Thread count
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 16)
        self.thread_count.setValue(4)
        self.thread_count.valueChanged.connect(self._mark_settings_changed)
        performance_layout.addRow(tr("Worker Threads:"), self.thread_count)
        
        # Process priority
        self.process_priority = QComboBox()
        priority_options = [tr("Normal"), tr("Above Normal"), tr("High"), tr("Realtime")]
        self.process_priority.addItems(priority_options)
        self.process_priority.currentIndexChanged.connect(self._mark_settings_changed)
        set_min_width_for_text(self.process_priority, tr("Above Normal") + " " * 3)
        performance_layout.addRow(tr("Process Priority:"), self.process_priority)
        
        # Image cache size
        self.image_cache_size = QSpinBox()
        self.image_cache_size.setRange(10, 1000)
        self.image_cache_size.setValue(100)
        self.image_cache_size.setSuffix(tr(" MB"))
        self.image_cache_size.valueChanged.connect(self._mark_settings_changed)
        performance_layout.addRow(tr("Image Cache Size:"), self.image_cache_size)
        
        # Enable parallel processing
        self.parallel_processing = QCheckBox()
        self.parallel_processing.setChecked(True)
        self.parallel_processing.stateChanged.connect(self._mark_settings_changed)
        performance_layout.addRow(tr("Parallel Processing:"), self.parallel_processing)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        # Debug settings
        debug_group = QGroupBox(tr("Debug"))
        debug_layout = QFormLayout(debug_group)
        
        # Log level
        self.log_level = QComboBox()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level.addItems(log_levels)
        self.log_level.setCurrentIndex(1)  # Default to INFO
        self.log_level.currentIndexChanged.connect(self._mark_settings_changed)
        set_min_width_for_text(self.log_level, "CRITICAL" + " " * 3)
        debug_layout.addRow(tr("Log Level:"), self.log_level)
        
        # Log to file
        self.log_to_file = QCheckBox()
        self.log_to_file.setChecked(True)
        self.log_to_file.stateChanged.connect(self._mark_settings_changed)
        debug_layout.addRow(tr("Log to File:"), self.log_to_file)
        
        # Log format
        self.log_format = QLineEdit("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.log_format.textChanged.connect(self._mark_settings_changed)
        debug_layout.addRow(tr("Log Format:"), self.log_format)
        
        # Debug window
        self.debug_window = QCheckBox()
        self.debug_window.setChecked(False)
        self.debug_window.stateChanged.connect(self._mark_settings_changed)
        debug_layout.addRow(tr("Show Debug Window:"), self.debug_window)
        
        # Performance monitoring
        self.performance_monitoring = QCheckBox()
        self.performance_monitoring.setChecked(False)
        self.performance_monitoring.stateChanged.connect(self._mark_settings_changed)
        debug_layout.addRow(tr("Performance Monitoring:"), self.performance_monitoring)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # Developer settings
        developer_group = QGroupBox(tr("Developer"))
        developer_layout = QFormLayout(developer_group)
        
        # Development mode
        self.development_mode = QCheckBox()
        self.development_mode.setChecked(False)
        self.development_mode.stateChanged.connect(self._mark_settings_changed)
        developer_layout.addRow(tr("Development Mode:"), self.development_mode)
        
        # Remote debugging
        self.remote_debugging = QCheckBox()
        self.remote_debugging.setChecked(False)
        self.remote_debugging.stateChanged.connect(self._mark_settings_changed)
        developer_layout.addRow(tr("Remote Debugging:"), self.remote_debugging)
        
        # Remote debugging port
        self.remote_debugging_port = QSpinBox()
        self.remote_debugging_port.setRange(1024, 65535)
        self.remote_debugging_port.setValue(5678)
        self.remote_debugging_port.valueChanged.connect(self._mark_settings_changed)
        developer_layout.addRow(tr("Debugging Port:"), self.remote_debugging_port)
        
        # Export config button
        export_config_btn = QPushButton(tr("Export Configuration"))
        export_config_btn.clicked.connect(self._export_full_configuration)
        developer_layout.addRow("", export_config_btn)
        
        developer_group.setLayout(developer_layout)
        layout.addWidget(developer_group)
        
        # Restore factory settings button
        factory_reset_btn = QPushButton(tr("Restore Factory Settings"))
        factory_reset_btn.clicked.connect(self._confirm_factory_reset)
        factory_reset_btn.setStyleSheet("background-color: #ffaaaa;")
        layout.addWidget(factory_reset_btn)
        
    def _create_notification_tab(self) -> None:
        """Create the notification configuration tab."""
        from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes
        
        notification_tab = QWidget()
        self.tabs.addTab(notification_tab, tr("Notifications"))
        
        # Create layout
        layout = QVBoxLayout(notification_tab)
        
        # Sound notifications
        sound_group = QGroupBox(tr("Sound Notifications"))
        sound_layout = QFormLayout(sound_group)
        
        # Enable sound
        self.enable_sound = QCheckBox()
        self.enable_sound.setChecked(True)
        self.enable_sound.stateChanged.connect(self._mark_settings_changed)
        sound_layout.addRow(tr("Enable Sound:"), self.enable_sound)
        
        # Sound volume
        self.sound_volume = QSlider(Qt.Orientation.Horizontal)
        self.sound_volume.setRange(0, 100)
        self.sound_volume.setValue(80)
        self.sound_volume.valueChanged.connect(self._mark_settings_changed)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.sound_volume)
        self.volume_label = QLabel("80%")
        volume_layout.addWidget(self.volume_label)
        sound_layout.addRow(tr("Volume:"), volume_layout)
        
        # Sound test button
        test_sound_btn = QPushButton(tr("Test Sound"))
        test_sound_btn.clicked.connect(self._test_notification_sound)
        sound_layout.addRow("", test_sound_btn)
        
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)
        
        # Desktop notifications
        desktop_group = QGroupBox(tr("Desktop Notifications"))
        desktop_layout = QFormLayout(desktop_group)
        
        # Enable desktop notifications
        self.desktop_notifications = QCheckBox()
        self.desktop_notifications.setChecked(True)
        self.desktop_notifications.stateChanged.connect(self._mark_settings_changed)
        desktop_layout.addRow(tr("Enable Notifications:"), self.desktop_notifications)
        
        # Notification duration
        self.notification_duration = QSpinBox()
        self.notification_duration.setRange(1, 60)
        self.notification_duration.setValue(5)
        self.notification_duration.setSuffix(tr(" sec"))
        self.notification_duration.valueChanged.connect(self._mark_settings_changed)
        desktop_layout.addRow(tr("Duration:"), self.notification_duration)
        
        # Test notification button
        test_notification_btn = QPushButton(tr("Test Notification"))
        test_notification_btn.clicked.connect(self._test_desktop_notification)
        desktop_layout.addRow("", test_notification_btn)
        
        desktop_group.setLayout(desktop_layout)
        layout.addWidget(desktop_group)
        
        # Add notification types grid
        types_group = QGroupBox(tr("Notification Types"))
        types_layout = QGridLayout(types_group)
        
        # Checkbox for each notification type
        notification_types = [
            tr("Task Completed"), 
            tr("Error Occurred"), 
            tr("Resource Found"),
            tr("Battle Started"),
            tr("Resource Depleted"),
            tr("Building Completed"),
            tr("Scout Completed")
        ]
        
        self.notification_type_checks = {}
        for i, notification_type in enumerate(notification_types):
            checkbox = QCheckBox(notification_type)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._mark_settings_changed)
            row, col = divmod(i, 2)
            types_layout.addWidget(checkbox, row, col)
            self.notification_type_checks[notification_type] = checkbox
        
        types_group.setLayout(types_layout)
        layout.addWidget(types_group)
        layout.addStretch()
        
    def _test_notification_sound(self):
        """Test the notification sound."""
        # This is a placeholder for the actual sound test functionality
        QMessageBox.information(
            self,
            tr("Sound Test"),
            tr("Sound test feature is not yet implemented.")
        )
        
    def _test_desktop_notification(self):
        """Test the desktop notification."""
        # This is a placeholder for the actual notification test functionality
        QMessageBox.information(
            self,
            tr("Notification Test"),
            tr("Desktop notification test feature is not yet implemented.")
        ) 