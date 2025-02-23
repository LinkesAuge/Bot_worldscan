from typing import Optional, Callable, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QLabel, QFrame, QHBoxLayout, QSlider, QColorDialog,
    QSpinBox, QDoubleSpinBox, QGroupBox, QApplication, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QFileDialog, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, QPoint
from PyQt6.QtGui import QPalette, QColor, QIcon, QImage, QPixmap, QPainter, QPen, QBrush, QPaintEvent, QMouseEvent
import logging
from scout.config_manager import ConfigManager
from scout.overlay import Overlay
from scout.pattern_matcher import PatternMatcher
from scout.world_scanner import WorldScanner, WorldPosition, ScanLogHandler, ScanWorker
from scout.debug_window import DebugWindow
import numpy as np
from time import sleep
import pyautogui
from scout.selector_tool import SelectorTool
import cv2
import mss
from pathlib import Path
from scout.text_ocr import TextOCR
from scout.window_manager import WindowManager
from scout.automation.gui.automation_tab import AutomationTab
from scout.actions import GameActions

logger = logging.getLogger(__name__)

class OverlayController(QMainWindow):
    """
    Main GUI window for controlling the overlay.
    """
    
    def __init__(self, overlay: Overlay, overlay_settings: Dict[str, Any], pattern_settings: Dict[str, Any], 
                 game_actions: GameActions, text_ocr: TextOCR, debug_window: DebugWindow) -> None:
        """
        Initialize the controller window.
        
        Args:
            overlay: Overlay instance to control
            overlay_settings: Initial overlay settings
            pattern_settings: Initial pattern matching settings
            game_actions: GameActions instance for automation
            text_ocr: TextOCR instance for text recognition
            debug_window: DebugWindow instance for debugging
        """
        super().__init__()
        
        # Initialize debug mode to off
        config = ConfigManager()
        debug_settings = {
            "enabled": False,
            "save_screenshots": False,
            "save_templates": False
        }
        config.update_debug_settings(debug_settings)
        
        # Create window manager first
        self.window_manager = WindowManager("Total Battle")
        
        # Store debug window
        self.debug_window = debug_window
        self.debug_window.window_closed.connect(self._on_debug_window_closed)
        
        # Create pattern matcher with window manager and debug window
        self.pattern_matcher = PatternMatcher(
            window_manager=self.window_manager,
            confidence=pattern_settings["confidence"],
            target_frequency=pattern_settings["target_frequency"],
            sound_enabled=pattern_settings["sound_enabled"],
            debug_window=self.debug_window
        )
        
        # Create overlay with window manager and pattern matcher
        self.overlay = Overlay(self.window_manager, pattern_settings, overlay_settings)
        
        # Store game actions and text OCR
        self.game_actions = game_actions
        self.text_ocr = text_ocr
        
        self.config_manager = ConfigManager()
        self.toggle_callback: Optional[Callable[[], None]] = None
        self.quit_callback: Optional[Callable[[], None]] = None
        
        # Store colors
        self.current_color = overlay_settings["rect_color"]
        self.font_color = overlay_settings["font_color"]
        self.cross_color = overlay_settings["cross_color"]
        
        # Create UI
        self.setWindowTitle("Total Battle Scout")
        self.setGeometry(100, 100, 800, 800)  # Made window larger to accommodate tabs
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create overlay tab
        overlay_tab = QWidget()
        overlay_layout = QVBoxLayout(overlay_tab)
        
        # Move existing controls to overlay tab
        self.create_overlay_controls(overlay_layout, overlay_settings)
        self.create_pattern_matching_controls(overlay_layout, pattern_settings)
        self.create_scan_controls(overlay_layout)
        
        # Add quit button at the bottom of overlay tab
        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet("background-color: #aa0000; color: white; padding: 8px; font-weight: bold;")
        quit_btn.clicked.connect(self._handle_quit)
        overlay_layout.addWidget(quit_btn)
        
        # Add overlay tab
        self.tab_widget.addTab(overlay_tab, "Overlay")
        
        # Create automation tab
        self.automation_tab = AutomationTab(
            window_manager=self.window_manager,
            pattern_matcher=self.pattern_matcher,
            text_ocr=self.text_ocr,
            game_actions=self.game_actions
        )
        self.tab_widget.addTab(self.automation_tab, "Automation")
        
        # Create status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Now that all controls are created, connect their handlers
        self.connect_settings_handlers()
        
        # Initialize scan controls with current region
        scanner_settings = self.config_manager.get_scanner_settings()
        if scanner_settings:
            self.scan_status.setText(
                f"Minimap region: ({scanner_settings['minimap_left']}, {scanner_settings['minimap_top']})"
            )
        
        # Load OCR settings
        ocr_settings = self.config_manager.get_ocr_settings()
        if ocr_settings['region']['width'] > 0:
            self.text_ocr.set_region(ocr_settings['region'])
            self.text_ocr.set_frequency(ocr_settings['frequency'])
            self.ocr_status.setText(
                f"OCR region: ({ocr_settings['region']['left']}, {ocr_settings['region']['top']})"
            )
        
        # Connect OCR frequency controls
        def on_ocr_slider_change(value: int) -> None:
            freq = value / 10.0
            logger.debug(f"OCR frequency slider changed: {value} -> {freq} updates/sec")
            self.ocr_freq_input.setValue(freq)
            self.text_ocr.set_frequency(freq)
            self.ocr_freq_display.setText(f"Target: {freq:.1f} updates/sec")
            
            # Save to config
            ocr_settings = self.config_manager.get_ocr_settings()
            ocr_settings['frequency'] = freq
            self.config_manager.update_ocr_settings(ocr_settings)
        
        def on_ocr_spinbox_change(value: float) -> None:
            logger.debug(f"OCR frequency spinbox changed to: {value} updates/sec")
            self.ocr_freq_slider.setValue(int(value * 10))
            self.text_ocr.set_frequency(value)
            self.ocr_freq_display.setText(f"Target: {value:.1f} updates/sec")
            
            # Save to config
            ocr_settings = self.config_manager.get_ocr_settings()
            ocr_settings['frequency'] = value
            self.config_manager.update_ocr_settings(ocr_settings)
        
        self.ocr_freq_slider.valueChanged.connect(on_ocr_slider_change)
        self.ocr_freq_input.valueChanged.connect(on_ocr_spinbox_change)
        
        logger.debug("GUI initialized")
        
        # Create pattern update timer - moved to end after all UI elements are initialized
        self.pattern_update_timer = QTimer()
        self.pattern_update_timer.timeout.connect(self.update_pattern_frequency_display)
        self.pattern_update_timer.start(500)  # Update every 500ms
    
    def create_overlay_controls(self, parent_layout: QVBoxLayout, settings: Dict[str, Any]) -> None:
        """
        Create overlay control widgets.
        
        Args:
            parent_layout: Parent layout to add controls to
            settings: Dictionary containing overlay settings
        """
        overlay_group = QGroupBox("TB Scout Overlay Controls")
        layout = QVBoxLayout()
        
        # Toggle button - initialize state from settings
        is_active = settings.get("active", False)
        self.toggle_btn = QPushButton(f"Toggle TB Scout Overlay (F10): {'ON' if is_active else 'OFF'}")
        self.toggle_btn.clicked.connect(self._handle_toggle)
        self._update_toggle_button_color(is_active)
        self.overlay.active = is_active
        layout.addWidget(self.toggle_btn)
        
        # Color controls
        color_group = QGroupBox("Colors")
        color_layout = QVBoxLayout()
        
        # Rectangle color
        self.rect_color_btn = QPushButton("Set Rectangle Color")
        self.rect_color_btn.clicked.connect(self._choose_rect_color)
        self.rect_color_btn.setStyleSheet(f"background-color: {self.current_color.name()}; font-weight: bold;")
        color_layout.addWidget(self.rect_color_btn)
        
        # Font color
        self.font_color_btn = QPushButton("Set Font Color")
        self.font_color_btn.clicked.connect(self._choose_font_color)
        self.font_color_btn.setStyleSheet(f"background-color: {self.font_color.name()}; font-weight: bold;")
        color_layout.addWidget(self.font_color_btn)
        
        # Cross color
        self.cross_color_btn = QPushButton("Set Cross Color")
        self.cross_color_btn.clicked.connect(self._choose_cross_color)
        self.cross_color_btn.setStyleSheet(f"background-color: {self.cross_color.name()}; font-weight: bold;")
        color_layout.addWidget(self.cross_color_btn)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Rectangle Thickness controls
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_input = QSpinBox()
        thickness_layout = self._create_slider_with_range(
            "Rectangle Thickness:", self.thickness_slider, self.thickness_input,
            1, 20, settings.get("rect_thickness", 2)
        )
        # Connect thickness controls bidirectionally
        self.thickness_slider.valueChanged.connect(self.thickness_input.setValue)
        self.thickness_input.valueChanged.connect(self.thickness_slider.setValue)
        layout.addLayout(thickness_layout)
        
        # Rectangle Scale controls
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_input = QDoubleSpinBox()
        scale_layout = QHBoxLayout()
        
        # Left side with label and range
        scale_label_layout = QVBoxLayout()
        scale_label = QLabel("Rectangle Scale:")
        scale_range = QLabel("Range: 0.5-5.0")
        scale_range.setStyleSheet("color: gray; font-size: 8pt;")
        scale_label_layout.addWidget(scale_label)
        scale_label_layout.addWidget(scale_range)
        
        # Set up rectangle scale controls (multiply by 10 for slider)
        rect_scale = settings.get("rect_scale", 1.0)
        self.scale_slider.setRange(5, 50)  # 0.5 to 5.0
        self.scale_slider.setValue(int(rect_scale * 10))
        
        self.scale_input.setRange(0.5, 5.0)
        self.scale_input.setSingleStep(0.1)
        self.scale_input.setValue(rect_scale)
        
        scale_layout.addLayout(scale_label_layout)
        scale_layout.addWidget(self.scale_slider, stretch=1)
        scale_layout.addWidget(self.scale_input)
        layout.addLayout(scale_layout)
        
        # Cross Scale controls
        self.cross_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.cross_scale_input = QDoubleSpinBox()
        cross_scale_layout = QHBoxLayout()
        
        # Left side with label and range
        cross_scale_label_layout = QVBoxLayout()
        cross_scale_label = QLabel("Cross Scale:")
        cross_scale_range = QLabel("Range: 0.5-5.0")
        cross_scale_range.setStyleSheet("color: gray; font-size: 8pt;")
        cross_scale_label_layout.addWidget(cross_scale_label)
        cross_scale_label_layout.addWidget(cross_scale_range)
        
        # Set up cross scale controls (multiply by 10 for slider)
        cross_scale = settings.get("cross_scale", 1.0)
        self.cross_scale_slider.setRange(5, 50)  # 0.5 to 5.0
        self.cross_scale_slider.setValue(int(cross_scale * 10))
        
        self.cross_scale_input.setRange(0.5, 5.0)
        self.cross_scale_input.setSingleStep(0.1)
        self.cross_scale_input.setValue(cross_scale)
        
        cross_scale_layout.addLayout(cross_scale_label_layout)
        cross_scale_layout.addWidget(self.cross_scale_slider, stretch=1)
        cross_scale_layout.addWidget(self.cross_scale_input)
        layout.addLayout(cross_scale_layout)
        
        # Font size controls
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_input = QSpinBox()
        font_size_layout = self._create_slider_with_range(
            "Font Size:", self.font_size_slider, self.font_size_input,
            8, 72, settings.get("font_size", 12)
        )
        # Connect font size controls bidirectionally
        self.font_size_slider.valueChanged.connect(self.font_size_input.setValue)
        self.font_size_input.valueChanged.connect(self.font_size_slider.setValue)
        layout.addLayout(font_size_layout)
        
        # Text thickness controls
        self.text_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_thickness_input = QSpinBox()
        text_thickness_layout = self._create_slider_with_range(
            "Text Thickness:", self.text_thickness_slider, self.text_thickness_input,
            1, 10, settings.get("text_thickness", 1)
        )
        # Connect text thickness controls bidirectionally
        self.text_thickness_slider.valueChanged.connect(self.text_thickness_input.setValue)
        self.text_thickness_input.valueChanged.connect(self.text_thickness_slider.setValue)
        layout.addLayout(text_thickness_layout)
        
        # Cross thickness controls
        self.cross_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.cross_thickness_input = QSpinBox()
        cross_thickness_layout = self._create_slider_with_range(
            "Cross Thickness:", self.cross_thickness_slider, self.cross_thickness_input,
            1, 10, settings.get("cross_thickness", 1)
        )
        # Connect cross thickness controls bidirectionally
        self.cross_thickness_slider.valueChanged.connect(self.cross_thickness_input.setValue)
        self.cross_thickness_input.valueChanged.connect(self.cross_thickness_slider.setValue)
        layout.addLayout(cross_thickness_layout)
        
        overlay_group.setLayout(layout)
        parent_layout.addWidget(overlay_group)
    
    def create_pattern_matching_controls(self, parent_layout: QVBoxLayout, settings: Dict[str, Any]) -> None:
        """
        Create pattern matching control widgets.
        
        Args:
            parent_layout: Parent layout to add controls to
            settings: Dictionary containing pattern matching settings
        """
        pattern_group = QGroupBox("Pattern Matching Controls")
        layout = QVBoxLayout()
        
        # Pattern matching toggle button
        is_active = settings.get("active", False)
        self.pattern_btn = QPushButton(f"Pattern Matching: {'ON' if is_active else 'OFF'}")
        self.pattern_btn.clicked.connect(self._toggle_pattern_matching)
        self._update_pattern_button_color(is_active)
        layout.addWidget(self.pattern_btn)
        
        # Sound toggle button
        sound_enabled = settings.get("sound_enabled", False)
        self.sound_btn = QPushButton(f"Sound Alert: {'ON' if sound_enabled else 'OFF'}")
        self.sound_btn.clicked.connect(self._toggle_sound)
        self._update_sound_button_color(sound_enabled)
        layout.addWidget(self.sound_btn)
        
        # Confidence controls
        confidence_layout = QHBoxLayout()
        confidence_label = QLabel("Confidence:")
        confidence_layout.addWidget(confidence_label)
        
        # Add range label
        range_label = QLabel("(10-100%)")
        range_label.setStyleSheet("color: gray;")
        confidence_layout.addWidget(range_label)
        
        # Slider for confidence
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setMinimum(10)  # 0.1
        self.confidence_slider.setMaximum(100)  # 1.0
        self.confidence_slider.setValue(int(settings.get("confidence", 0.8) * 100))
        confidence_layout.addWidget(self.confidence_slider)
        
        # Spinbox for confidence
        self.confidence_input = QDoubleSpinBox()
        self.confidence_input.setMinimum(0.1)
        self.confidence_input.setMaximum(1.0)
        self.confidence_input.setSingleStep(0.05)
        self.confidence_input.setDecimals(2)
        self.confidence_input.setValue(settings.get("confidence", 0.8))
        confidence_layout.addWidget(self.confidence_input)
        
        layout.addLayout(confidence_layout)
        
        # Frequency controls
        freq_layout = QVBoxLayout()  # Changed to vertical layout
        
        # Create horizontal layout for slider and spinbox
        freq_controls = QHBoxLayout()
        freq_label = QLabel("Updates/sec:")
        freq_controls.addWidget(freq_label)
        
        # Add range label
        range_label = QLabel("(0.1-10)")
        range_label.setStyleSheet("color: gray;")
        freq_controls.addWidget(range_label)
        
        # Slider for frequency (0.1 to 10 updates/sec)
        self.freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.freq_slider.setMinimum(1)  # 0.1
        self.freq_slider.setMaximum(100)  # 10.0
        self.freq_slider.setValue(int(settings.get("target_frequency", 1.0) * 10))
        freq_controls.addWidget(self.freq_slider)
        
        # Spinbox for frequency
        self.freq_input = QDoubleSpinBox()
        self.freq_input.setMinimum(0.1)
        self.freq_input.setMaximum(10.0)
        self.freq_input.setSingleStep(0.1)
        self.freq_input.setDecimals(1)
        self.freq_input.setValue(settings.get("target_frequency", 1.0))
        freq_controls.addWidget(self.freq_input)
        
        # Add controls to main frequency layout
        freq_layout.addLayout(freq_controls)
        
        # Add frequency display label below controls
        self.freq_display = QLabel("Updates/sec: N/A")
        self.freq_display.setStyleSheet("font-weight: bold;")
        self.freq_display.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
        freq_layout.addWidget(self.freq_display)
        
        layout.addLayout(freq_layout)
        
        # Connect frequency controls
        def on_slider_change(value: int) -> None:
            freq = value / 10.0
            logger.debug(f"Frequency slider changed: {value} -> {freq} updates/sec")
            self.freq_input.setValue(freq)
            if hasattr(self.pattern_matcher, 'target_frequency'):
                self.pattern_matcher.target_frequency = freq
                logger.debug(f"Updated pattern matcher target_frequency to: {freq}")
                # Update overlay timer interval
                if hasattr(self.overlay, 'update_timer_interval'):
                    self.overlay.update_timer_interval()
                    logger.debug("Updated overlay timer interval")
            self.save_settings()

        def on_spinbox_change(value: float) -> None:
            logger.debug(f"Frequency spinbox changed to: {value} updates/sec")
            self.freq_slider.setValue(int(value * 10))
            if hasattr(self.pattern_matcher, 'target_frequency'):
                self.pattern_matcher.target_frequency = value
                logger.debug(f"Updated pattern matcher target_frequency to: {value}")
                # Update overlay timer interval
                if hasattr(self.overlay, 'update_timer_interval'):
                    self.overlay.update_timer_interval()
                    logger.debug("Updated overlay timer interval")
            self.save_settings()
        
        self.freq_slider.valueChanged.connect(on_slider_change)
        self.freq_input.valueChanged.connect(on_spinbox_change)
        
        # Reload templates button
        self.reload_btn = QPushButton("Reload Templates")
        self.reload_btn.setStyleSheet("font-weight: bold;")
        self.reload_btn.clicked.connect(self._reload_templates)  # Connect to handler
        layout.addWidget(self.reload_btn)
        
        # Debug mode toggle button - initialize from config
        debug_settings = self.config_manager.get_debug_settings()
        is_debug_enabled = debug_settings.get('enabled', False)
        self.debug_btn = QPushButton(f"Debug Mode: {'ON' if is_debug_enabled else 'OFF'}")
        self.debug_btn.clicked.connect(self._toggle_debug_mode)
        self._update_debug_button_color(is_debug_enabled)
        
        # Show/hide debug window based on initial state
        if is_debug_enabled:
            self.debug_window.show()
        else:
            self.debug_window.hide()
            
        layout.addWidget(self.debug_btn)
        
        pattern_group.setLayout(layout)
        parent_layout.addWidget(pattern_group)
    
    def create_scan_controls(self, layout: QVBoxLayout) -> None:
        """
        Create controls for world scanning and OCR functionality.
        
        This method sets up:
        1. World scanning controls (toggle button, status)
        2. OCR controls (toggle button, frequency slider, region selection)
        
        Args:
            layout: Parent layout to add controls to
        """
        # Get OCR settings from config manager
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        
        # Create group box for world scanning
        scan_group = QGroupBox("World Scanning")
        scan_layout = QVBoxLayout()
        
        # Create scan toggle button
        self.scan_btn = QPushButton("Start World Scan")
        self.scan_btn.setCheckable(True)
        self.scan_btn.clicked.connect(self._toggle_scan)
        scan_layout.addWidget(self.scan_btn)
        
        # Create scan status label
        self.scan_status = QLabel("World Scan: Inactive")
        scan_layout.addWidget(self.scan_status)
        
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)
        
        # Create group box for OCR
        ocr_group = QGroupBox("Text OCR")
        ocr_layout = QVBoxLayout()
        
        # Create OCR toggle button
        self.ocr_btn = QPushButton("Start Text OCR")
        self.ocr_btn.setCheckable(True)
        self.ocr_btn.clicked.connect(self._toggle_ocr)
        ocr_layout.addWidget(self.ocr_btn)
        
        # Create OCR frequency controls
        freq_layout = QVBoxLayout()  # Changed to vertical layout
        
        # Create horizontal layout for slider and spinbox
        freq_controls = QHBoxLayout()
        freq_label = QLabel("OCR Frequency:")
        freq_controls.addWidget(freq_label)
        
        # Add range label
        range_label = QLabel("(0.1 - 2.0 updates/sec)")
        range_label.setStyleSheet("QLabel { color: gray; }")
        freq_controls.addWidget(range_label)
        
        # Slider for frequency
        self.ocr_freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_freq_slider.setMinimum(1)  # 0.1 updates/sec
        self.ocr_freq_slider.setMaximum(20)  # 2.0 updates/sec
        self.ocr_freq_slider.setValue(int(ocr_settings['frequency'] * 10))
        self.ocr_freq_slider.valueChanged.connect(self.on_ocr_slider_change)
        freq_controls.addWidget(self.ocr_freq_slider)
        
        # Create spinbox for precise input
        self.ocr_freq_input = QDoubleSpinBox()
        self.ocr_freq_input.setMinimum(0.1)
        self.ocr_freq_input.setMaximum(2.0)
        self.ocr_freq_input.setSingleStep(0.1)
        self.ocr_freq_input.setValue(ocr_settings['frequency'])
        self.ocr_freq_input.valueChanged.connect(self.on_ocr_spinbox_change)
        freq_controls.addWidget(self.ocr_freq_input)
        
        ocr_layout.addLayout(freq_layout)
        
        # Create OCR region selection button
        self.select_ocr_region_btn = QPushButton("Select OCR Region")
        self.select_ocr_region_btn.clicked.connect(self._start_ocr_region_selection)
        ocr_layout.addWidget(self.select_ocr_region_btn)
        
        # Create OCR status label with coordinates
        self.ocr_status = QLabel("Text OCR: Inactive")
        self.ocr_coords_label = QLabel("Coordinates: None")
        self.ocr_coords_label.setStyleSheet("font-family: monospace;")  # For better alignment
        ocr_layout.addWidget(self.ocr_status)
        ocr_layout.addWidget(self.ocr_coords_label)
        
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)
    
    def _choose_rect_color(self) -> None:
        """Open color picker for rectangle color."""
        color = QColorDialog.getColor(self.current_color)
        if color.isValid():
            self.current_color = color
            self.rect_color_btn.setStyleSheet(f"background-color: {color.name()}; font-weight: bold;")
            # Convert QColor to BGR for OpenCV
            self.overlay.rect_color = (color.blue(), color.green(), color.red())
            self.save_settings()
    
    def _choose_font_color(self) -> None:
        """Open color picker for font color."""
        color = QColorDialog.getColor(self.font_color)
        if color.isValid():
            self.font_color = color
            self.font_color_btn.setStyleSheet(f"background-color: {color.name()}; font-weight: bold;")
            # Convert QColor to BGR for OpenCV
            self.overlay.font_color = (color.blue(), color.green(), color.red())
            self.save_settings()
    
    def _choose_cross_color(self) -> None:
        """Open color picker for cross color."""
        color = QColorDialog.getColor(self.cross_color)
        if color.isValid():
            self.cross_color = color
            self.cross_color_btn.setStyleSheet(f"background-color: {color.name()}; font-weight: bold;")
            # Convert QColor to BGR for OpenCV
            self.overlay.cross_color = (color.blue(), color.green(), color.red())
            self.save_settings()
    
    def _handle_toggle(self) -> None:
        """Handle overlay toggle button click."""
        if self.toggle_callback:
            self.toggle_callback()
            # Get the current state from the overlay after toggle
            is_active = self.overlay.active
            # Update button color and text based on current state
            self._update_toggle_button_color(is_active)
            self.toggle_btn.setText(f"Toggle TB Scout Overlay (F10): {'ON' if is_active else 'OFF'}")
            # Update status bar
            self.status_bar.showMessage(f"Overlay: {'ON' if is_active else 'OFF'}")
            # Save settings including overlay state
            self.save_settings()
    
    def set_toggle_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for overlay toggle."""
        self.toggle_callback = callback
    
    def set_quit_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for application quit."""
        self.quit_callback = callback
    
    def update_status(self, overlay_active: bool) -> None:
        """Update status bar with overlay state."""
        state = "ON" if overlay_active else "OFF"
        self.status_bar.showMessage(f"Overlay: {state}")
        self._update_toggle_button_color(overlay_active)  # Update button color
        self.toggle_btn.setText(f"Toggle TB Scout Overlay (F10): {state}")  # Update button text
    
    def update_pattern_frequency_display(self) -> None:
        """Update the frequency display with current pattern matching values.
        
        This method updates the display showing the target and actual frequency of pattern matching updates.
        It also color-codes the display based on how well the actual frequency matches the target:
        - Green: >= 90% of target
        - Orange: >= 70% of target
        - Red: < 70% of target
        """
        if hasattr(self.pattern_matcher, 'update_frequency'):
            actual_freq = self.pattern_matcher.update_frequency
            target_freq = self.freq_input.value()
            
            logger.debug(f"Updating pattern frequency display - Target: {target_freq:.1f}, Actual: {actual_freq:.1f}")
            
            # Update display with frequency values
            self.freq_display.setText(f"Target: {target_freq:.1f} updates/sec, Actual: {actual_freq:.1f} updates/sec")
            
            # Color code the display based on performance
            if actual_freq >= target_freq * 0.9:  # Within 90% of target
                self.freq_display.setStyleSheet("color: green;")
                logger.debug("Performance good (>90%) - display green")
            elif actual_freq >= target_freq * 0.7:  # Within 70% of target
                self.freq_display.setStyleSheet("color: orange;")
                logger.debug("Performance moderate (70-90%) - display orange")
            else:  # Below 70% of target
                self.freq_display.setStyleSheet("color: red;")
                logger.debug("Performance poor (<70%) - display red")
        else:
            logger.warning("Pattern matcher has no update_frequency attribute")
            self.freq_display.setText("Updates/sec: N/A")
            self.freq_display.setStyleSheet("")
    
    def _handle_quit(self) -> None:
        """Handle quit button click."""
        if self.quit_callback:
            self.quit_callback()
    
    def save_settings(self) -> None:
        """
        Save current settings to config.
        
        This method saves all current GUI values to the configuration file, including:
        - Overlay settings (colors, sizes, scales, etc.)
        - Pattern matching settings (confidence, frequency, etc.)
        - OCR settings (frequency, region, etc.)
        """
        try:
            # Create overlay settings dictionary
            overlay_settings = {
                "active": self.overlay.active,
                "rect_color": self.current_color,
                "rect_thickness": self.thickness_slider.value(),
                "rect_scale": self.scale_input.value(),
                "font_color": self.font_color,
                "font_size": self.font_size_slider.value(),
                "text_thickness": self.text_thickness_slider.value(),
                "cross_color": self.cross_color,
                "cross_size": self.overlay.cross_size,
                "cross_thickness": self.cross_thickness_slider.value(),
                "cross_scale": self.cross_scale_input.value()
            }
            
            # Create pattern matching settings dictionary
            pattern_settings = {
                "active": self.pattern_btn.text().endswith("ON"),
                "confidence": self.confidence_input.value(),
                "target_frequency": self.freq_input.value(),
                "sound_enabled": self.sound_btn.text().endswith("ON")
            }
            
            # Create OCR settings dictionary
            ocr_settings = self.config_manager.get_ocr_settings()  # Get existing settings first
            ocr_settings.update({
                "active": self.ocr_btn.isChecked(),
                "frequency": self.ocr_freq_input.value()
            })
            
            # Save all settings
            self.config_manager.update_overlay_settings(overlay_settings)
            self.config_manager.update_pattern_matching_settings(pattern_settings)
            self.config_manager.update_ocr_settings(ocr_settings)
            
            logger.debug("All settings saved to config")
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}", exc_info=True)
    
    def connect_settings_handlers(self) -> None:
        """Connect all settings handlers to their respective UI elements."""
        try:
            # Handler for confidence slider
            def on_confidence_slider_change(value: int) -> None:
                """
                Handle changes to the confidence slider.
                
                Args:
                    value: Integer value from slider (0-100)
                """
                # Convert slider value (0-100) to confidence (0.0-1.0)
                confidence = value / 100.0
                # Update spinbox with the float value
                self.confidence_input.setValue(confidence)
                # Update pattern matcher
                if hasattr(self.overlay, 'pattern_matcher'):
                    self.overlay.pattern_matcher.confidence = confidence
                    self.save_settings()
                    logger.debug(f"Confidence updated to {confidence:.2f}")

            # Handler for confidence spinbox
            def on_confidence_spinbox_change(value: float) -> None:
                """
                Handle changes to the confidence spinbox.
                
                Args:
                    value: Float value from spinbox (0.0-1.0)
                """
                # Convert confidence (0.0-1.0) to slider value (0-100)
                slider_value = int(value * 100)
                # Update slider with the integer value
                self.confidence_slider.setValue(slider_value)
                # Update pattern matcher
                if hasattr(self.overlay, 'pattern_matcher'):
                    self.overlay.pattern_matcher.confidence = value
                    self.save_settings()
                    logger.debug(f"Confidence updated to {value:.2f}")

            # Connect confidence handlers if elements exist
            if hasattr(self, 'confidence_slider') and hasattr(self, 'confidence_input'):
                self.confidence_slider.valueChanged.connect(on_confidence_slider_change)
                self.confidence_input.valueChanged.connect(on_confidence_spinbox_change)
                logger.debug("Connected confidence handlers")

            # Define handler functions
            def on_thickness_change(value: int) -> None:
                """Handle rectangle thickness change."""
                self.overlay.rect_thickness = value
                self.save_settings()

            def on_font_size_change(value: int) -> None:
                """Handle font size change."""
                self.overlay.font_size = value
                self.save_settings()

            def on_text_thickness_change(value: int) -> None:
                """Handle text thickness change."""
                self.overlay.text_thickness = value
                self.save_settings()

            def on_cross_thickness_change(value: int) -> None:
                """Handle cross thickness change."""
                self.overlay.cross_thickness = value
                self.save_settings()

            def on_rect_scale_slider_change(value: int) -> None:
                """Handle rectangle scale slider change."""
                scale = value / 10.0
                self.scale_input.setValue(scale)
                self.overlay.rect_scale = scale
                self.save_settings()

            def on_rect_scale_spinbox_change(value: float) -> None:
                """Handle rectangle scale spinbox change."""
                self.scale_slider.setValue(int(value * 10))
                self.overlay.rect_scale = value
                self.save_settings()

            def on_cross_scale_slider_change(value: int) -> None:
                """Handle cross scale slider change."""
                scale = value / 10.0
                self.cross_scale_input.setValue(scale)
                self.overlay.cross_scale = scale
                self.save_settings()

            def on_cross_scale_spinbox_change(value: float) -> None:
                """Handle cross scale spinbox change."""
                self.cross_scale_slider.setValue(int(value * 10))
                self.overlay.cross_scale = value
                self.save_settings()

            # Connect handlers only if the UI elements exist
            if hasattr(self, 'thickness_slider'):
                self.thickness_slider.valueChanged.connect(on_thickness_change)
            if hasattr(self, 'font_size_slider'):
                self.font_size_slider.valueChanged.connect(on_font_size_change)
            if hasattr(self, 'text_thickness_slider'):
                self.text_thickness_slider.valueChanged.connect(on_text_thickness_change)
            if hasattr(self, 'cross_thickness_slider'):
                self.cross_thickness_slider.valueChanged.connect(on_cross_thickness_change)
            if hasattr(self, 'scale_slider'):
                self.scale_slider.valueChanged.connect(on_rect_scale_slider_change)
            if hasattr(self, 'scale_input'):
                self.scale_input.valueChanged.connect(on_rect_scale_spinbox_change)
            if hasattr(self, 'cross_scale_slider'):
                self.cross_scale_slider.valueChanged.connect(on_cross_scale_slider_change)
            if hasattr(self, 'cross_scale_input'):
                self.cross_scale_input.valueChanged.connect(on_cross_scale_spinbox_change)

        except Exception as e:
            logger.error(f"Error connecting settings handlers: {e}", exc_info=True)
    
    def _reload_templates(self) -> None:
        """Reload pattern matching templates."""
        if hasattr(self.pattern_matcher, 'reload_templates'):
            self.pattern_matcher.reload_templates()
            logger.info("Templates reloaded")
            
    def _update_toggle_button_color(self, is_active: bool) -> None:
        """Update toggle button color based on state."""
        if is_active:
            self.toggle_btn.setStyleSheet(
                "background-color: #228B22; color: white; padding: 8px; font-weight: bold;"  # Forest Green
            )
        else:
            self.toggle_btn.setStyleSheet(
                "background-color: #8B0000; color: white; padding: 8px; font-weight: bold;"  # Dark red
            )

    def _update_pattern_button_color(self, is_active: bool) -> None:
        """Update pattern matching button color based on state."""
        if is_active:
            self.pattern_btn.setStyleSheet(
                "background-color: #228B22; color: white; padding: 8px; font-weight: bold;"
            )
            self.pattern_btn.setText("Pattern Matching: ON")
            self.overlay.start_pattern_matching()
            logger.info("Pattern matching activated")
        else:
            self.pattern_btn.setStyleSheet(
                "background-color: #8B0000; color: white; padding: 8px; font-weight: bold;"
            )
            self.pattern_btn.setText("Pattern Matching: OFF")
            self.overlay.stop_pattern_matching()
            logger.info("Pattern matching deactivated")

    def _update_sound_button_color(self, is_active: bool) -> None:
        """Update sound button color based on state."""
        if is_active:
            self.sound_btn.setStyleSheet(
                "background-color: #228B22; color: white; padding: 8px; font-weight: bold;"  # Forest Green
            )
        else:
            self.sound_btn.setStyleSheet(
                "background-color: #8B0000; color: white; padding: 8px; font-weight: bold;"  # Dark red
            )

    def _toggle_scan(self) -> None:
        """Toggle world scanning."""
        if self.scan_btn.isChecked():
            self.start_scan()
        else:
            self.stop_scan()
            
    def start_scan(self) -> None:
        """Start world scanning."""
        self.scan_btn.setText("Stop Scanning")
        self.scan_status.setText("Scanner: Active")
        self._start_world_scan()
        
    def stop_scan(self) -> None:
        """Stop world scanning."""
        self.scan_btn.setText("Start World Scan")
        self.scan_status.setText("Scanner: Inactive")
        
        if hasattr(self, 'scan_worker'):
            self.scan_worker.stop()
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.log_handler.cleanup()
            self.debug_window.hide()
    
    def _start_world_scan(self) -> None:
        """Start the world scanning process."""
        try:
            # Create and configure scanner
            scanner_settings = self.config_manager.get_scanner_settings()
            if not scanner_settings:
                logger.error("No scanner settings found")
                return
                
            self.world_scanner = WorldScanner(
                minimap_left=scanner_settings['minimap_left'],
                minimap_top=scanner_settings['minimap_top'],
                minimap_width=scanner_settings['minimap_width'],
                minimap_height=scanner_settings['minimap_height'],
                dpi_scale=scanner_settings['dpi_scale']
            )
            
            # Create worker and thread
            self.scan_worker = ScanWorker(self.world_scanner, self.pattern_matcher)
            self.scan_thread = QThread()
            
            # Move worker to thread
            self.scan_worker.moveToThread(self.scan_thread)
            
            # Connect signals
            self.scan_thread.started.connect(self.scan_worker.run)
            self.scan_worker.finished.connect(self.scan_thread.quit)
            self.scan_worker.finished.connect(self.scan_worker.deleteLater)
            self.scan_thread.finished.connect(self.scan_thread.deleteLater)
            
            self.scan_worker.position_found.connect(self._on_position_found)
            self.scan_worker.error.connect(self._on_scan_error)
            
            # Connect debug image signal to debug window
            self.scan_worker.debug_image.connect(
                lambda img, coord_type, value: self.debug_window.update_image(
                    f"Coordinate {coord_type}",
                    img,
                    metadata={"value": value},
                    save=True
                )
            )
            
            # Start scanning
            self.scan_thread.start()
            logger.info("World scan started with pattern matching active")
            
        except Exception as e:
            logger.error(f"Error starting scan: {e}", exc_info=True)
            self.stop_scan()
            
    def _on_position_found(self, position: WorldPosition) -> None:
        """Handle when a matching position is found."""
        self.scan_status.setText(f"Match found at X={position.x}, Y={position.y}, K={position.k}")
        self.stop_scan()
        
    def _on_scan_error(self, error_msg: str) -> None:
        """Handle scan errors."""
        self.scan_status.setText(f"Error: {error_msg}")
        self.stop_scan()

    def _start_region_selection(self) -> None:
        """Start the region selection process."""
        logger.info("Starting minimap region selection")
        
        try:
            if hasattr(self, 'region_selector'):
                logger.debug("Cleaning up previous region selector")
                self.region_selector.close()
                self.region_selector.deleteLater()
            
            logger.debug("Creating new SelectorTool instance")
            self.region_selector = SelectorTool(
                window_manager=self.window_manager,
                instruction_text="Click and drag to select minimap region"
            )
            self.region_selector.region_selected.connect(self._on_region_selected)
            self.region_selector.selection_cancelled.connect(self._on_region_cancelled)
            
            # Don't hide main window, just show selector
            logger.debug("Scheduling selector display")
            QTimer.singleShot(100, lambda: self._show_selector())
            
            logger.debug("Region selector initialization complete")
            
        except Exception as e:
            logger.error(f"Error starting region selection: {e}", exc_info=True)
            
    def _show_selector(self) -> None:
        """Helper method to show and activate the selector."""
        try:
            logger.debug("Showing selector tool")
            self.region_selector.show()
            logger.debug("Activating selector window")
            self.region_selector.activateWindow()
            logger.debug("Selector display complete")
        except Exception as e:
            logger.error(f"Error showing selector: {e}", exc_info=True)
    
    def _on_region_selected(self, region: dict) -> None:
        """
        Handle the selected region from the selector tool.
        
        This method processes the selected region coordinates and captures the raw screenshot
        without any color space conversion or processing.
        
        Args:
            region: Dictionary containing the selected region coordinates (left, top, width, height)
                   and DPI scaling information
        """
        logger.info(f"Selected region: {region}")
        
        try:
            # Log all screens and their geometries
            screens = QApplication.screens()
            logger.info(f"Found {len(screens)} screens")
            
            for i, screen in enumerate(screens):
                geom = screen.geometry()
                dpi = screen.devicePixelRatio()
                logger.info(f"Screen {i}: Geometry={geom}, DPI={dpi}")
            
            # The coordinates in region are already physical pixels adjusted for DPI scaling
            # Save physical coordinates to config for MSS
            config = ConfigManager()
            config.update_scanner_settings({
                'minimap_left': region['left'],
                'minimap_top': region['top'],
                'minimap_width': region['width'],
                'minimap_height': region['height'],
                'dpi_scale': region['dpi_scale'],
                'logical_coords': region['logical_coords']
            })
            
            # Capture and display debug image using physical coordinates
            with mss.mss() as sct:
                # MSS uses physical coordinates, so use them directly
                monitor = {
                    "left": region['left'],
                    "top": region['top'],
                    "width": region['width'],
                    "height": region['height'],
                    "mon": 0  # Use the virtual screen
                }
                
                logger.info(f"Capturing with monitor settings: {monitor}")
                screenshot = np.array(sct.grab(monitor))
                
                # Display raw debug image in window
                self.debug_window.update_image(
                    "Selected Region",
                    screenshot,
                    metadata={
                        "physical_coords": f"({region['left']}, {region['top']}) {region['width']}x{region['height']}",
                        "logical_coords": f"({region['logical_coords']['left']}, {region['logical_coords']['top']}) "
                                        f"{region['logical_coords']['width']}x{region['logical_coords']['height']}",
                        "dpi_scale": region['dpi_scale']
                    },
                    save=True
                )
                
                # Update status with logical coordinates for display
                logical = region['logical_coords']
                self.scan_status.setText(
                    f"Minimap region: ({logical['left']}, {logical['top']}) "
                    f"[Physical: ({region['left']}, {region['top']})]"
                )
                
        except Exception as e:
            logger.error(f"Error saving region: {e}", exc_info=True)

    def _on_region_cancelled(self) -> None:
        """Handle region selection cancellation."""
        logger.info("Region selection cancelled")
        
        try:
            # Restore previous region status if it exists
            scanner_settings = self.config_manager.get_scanner_settings()
            if scanner_settings:
                status_text = f"Minimap region: ({scanner_settings['minimap_left']}, {scanner_settings['minimap_top']})"
                logger.debug(f"Restoring previous region status: {status_text}")
                self.scan_status.setText(status_text)
            else:
                logger.debug("No previous region settings found")
                self.scan_status.setText("Scanner: Inactive")
        except Exception as e:
            logger.error(f"Error handling region cancellation: {e}", exc_info=True)
            self.scan_status.setText("Scanner: Inactive")

    def _start_input_field_selection(self) -> None:
        """Start the input field location selection."""
        logger.info("Starting input field selection")
        
        msg = QMessageBox()
        msg.setWindowTitle("Input Field Selection")
        msg.setText("Click OK, then click on the coordinate input field in the game.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Ok:
            # Hide window during selection
            self.hide()
            sleep(0.5)
            
            try:
                # Wait for mouse click
                x, y = self._get_click_position()
                logger.info(f"Input field position selected: ({x}, {y})")
                
                # Save to config
                self.config_manager.update_scanner_settings({
                    'input_field_x': x,
                    'input_field_y': y
                })
                
                # Update status
                self.scan_status.setText(f"Input field set: ({x}, {y})")
                
            except Exception as e:
                logger.error(f"Error setting input field: {e}", exc_info=True)
                self.scan_status.setText("Error setting input field!")
            
            finally:
                self.show()
                
    def _get_click_position(self) -> Tuple[int, int]:
        """Wait for and return the next mouse click position."""
        while True:
            if pyautogui.mouseDown():
                x, y = pyautogui.position()
                sleep(0.1)  # Wait to avoid multiple detections
                return x, y
            sleep(0.1)

    def _toggle_pattern_matching(self) -> None:
        """Toggle pattern matching on/off."""
        try:
            # Get current settings
            settings = self.config_manager.get_pattern_matching_settings()
            
            # Toggle active state
            settings["active"] = not settings["active"]
            
            # Update settings in config
            self.config_manager.update_pattern_matching_settings(settings)
            
            # Update pattern matcher
            if settings["active"]:
                self.overlay.start_pattern_matching()
                self._update_pattern_button_color(True)
                logger.info("Pattern matching activated")
            else:
                self.overlay.stop_pattern_matching()
                self._update_pattern_button_color(False)
                logger.info("Pattern matching deactivated")
                
        except Exception as e:
            logger.error(f"Error toggling pattern matching: {e}", exc_info=True)
            self._update_pattern_button_color(False)

    def _toggle_sound(self) -> None:
        """Toggle sound alerts on/off."""
        is_enabled = self.sound_btn.text().endswith("ON")
        new_state = not is_enabled
        
        # Update button state
        self.sound_btn.setText(f"Sound Alert: {'ON' if new_state else 'OFF'}")
        self._update_sound_button_color(new_state)
        
        # Update pattern matcher sound state
        if hasattr(self.pattern_matcher, 'sound_enabled'):
            self.pattern_matcher.sound_enabled = new_state
        
        # Save the new state
        self.save_settings()
        
        # Play test sound if enabled
        if new_state and hasattr(self.pattern_matcher, 'sound_manager'):
            self.pattern_matcher.sound_manager.play_if_ready()
            
        logger.info(f"Sound alerts {'enabled' if new_state else 'disabled'}")

    def _toggle_debug_mode(self) -> None:
        """
        Toggle debug mode on/off.
        
        When enabled:
        1. Shows debug window
        2. Enables debug logging
        3. Saves debug screenshots
        
        When disabled:
        1. Hides debug window
        2. Disables debug logging
        3. Stops saving debug screenshots
        """
        # Get current debug state
        config = ConfigManager()
        debug_settings = config.get_debug_settings()
        
        # Toggle state
        is_enabled = not debug_settings["enabled"]
        
        # Update pattern matcher debug mode
        self.pattern_matcher.set_debug_mode(is_enabled)
        
        # Update debug settings
        debug_settings = {
            "enabled": is_enabled,
            "save_screenshots": is_enabled,
            "save_templates": is_enabled
        }
        config.update_debug_settings(debug_settings)
        
        # Update button text and color
        self.debug_btn.setText(f"Debug Mode: {'ON' if is_enabled else 'OFF'}")
        self._update_debug_button_color(is_enabled)
        
        # Show/hide debug window based on state
        if is_enabled:
            self.debug_window.show()
            logger.info("Debug mode enabled - debug window shown")
        else:
            self.debug_window.hide()
        
        logger.info(f"Debug mode {'enabled' if is_enabled else 'disabled'}")

    def _update_debug_button_color(self, is_active: bool) -> None:
        """Update debug mode button color based on state."""
        if is_active:
            self.debug_btn.setStyleSheet(
                "background-color: #228B22; color: white; padding: 8px; font-weight: bold;"  # Forest Green
            )
        else:
            self.debug_btn.setStyleSheet(
                "background-color: #8B0000; color: white; padding: 8px; font-weight: bold;"  # Dark red
            )

    def update_frequency_display(self, target_freq: float, actual_freq: float) -> None:
        """Update the frequency display label."""
        self.freq_display.setText(f"Target: {target_freq:.1f} updates/sec, Actual: {actual_freq:.1f} updates/sec")
        
        # Color code the display based on performance
        if actual_freq >= target_freq * 0.9:  # Within 90% of target
            self.freq_display.setStyleSheet("color: green;")
        elif actual_freq >= target_freq * 0.7:  # Within 70% of target
            self.freq_display.setStyleSheet("color: orange;")
        else:  # Below 70% of target
            self.freq_display.setStyleSheet("color: red;")

    def _create_slider_with_range(self, label_text: str, slider: 'QSlider', 
                                spinbox: 'QSpinBox', min_val: int, max_val: int, 
                                default_val: int) -> 'QHBoxLayout':
        """
        Create a horizontal layout with a label, range indicator, slider and spinbox.
        
        Args:
            label_text: Text for the label
            slider: QSlider instance to configure
            spinbox: QSpinBox instance to configure
            min_val: Minimum value for the range
            max_val: Maximum value for the range
            default_val: Default/initial value
            
        Returns:
            QHBoxLayout: Layout containing all the configured widgets
        """
        layout = QHBoxLayout()
        
        # Create label layout with range
        label_layout = QVBoxLayout()
        label = QLabel(label_text)
        range_label = QLabel(f"Range: {min_val}-{max_val}")
        range_label.setStyleSheet("color: gray; font-size: 8pt;")
        label_layout.addWidget(label)
        label_layout.addWidget(range_label)
        
        # Configure slider
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        # Configure spinbox
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        
        # Add widgets to layout
        layout.addLayout(label_layout)
        layout.addWidget(slider, stretch=1)
        layout.addWidget(spinbox)
        
        return layout 

    def _on_debug_window_closed(self) -> None:
        """
        Handle debug window close event.
        
        When the debug window is closed:
        1. Disables debug mode
        2. Updates button state
        3. Saves disabled state to config
        4. Stops debug logging and screenshot saving
        """
        logger.debug("Debug window closed - disabling debug mode")
        
        # Update button state
        self.debug_btn.setText("Debug Mode: OFF")
        self._update_debug_button_color(False)
        
        # Update pattern matcher debug mode
        if hasattr(self.pattern_matcher, 'set_debug_mode'):
            self.pattern_matcher.set_debug_mode(False)
        
        # Update config
        debug_settings = {
            "enabled": False,
            "save_screenshots": False,
            "save_templates": False
        }
        self.config_manager.update_debug_settings(debug_settings)
        
        logger.info("Debug mode disabled due to window close")

    def _toggle_ocr(self) -> None:
        """Toggle Text OCR on/off."""
        is_active = self.ocr_btn.isChecked()
        self.ocr_btn.setText(f"Text OCR: {'ON' if is_active else 'OFF'}")
        
        if is_active:
            self.ocr_btn.setStyleSheet(
                "background-color: #228B22; color: white; padding: 8px; font-weight: bold;"
            )
            self._start_ocr()
        else:
            self.ocr_btn.setStyleSheet(
                "background-color: #8B0000; color: white; padding: 8px; font-weight: bold;"
            )
            self._stop_ocr()
    
    def _start_ocr(self) -> None:
        """Start Text OCR processing."""
        logger.info("Starting Text OCR")
        self.ocr_status.setText("Text OCR: Active")
        
        # Connect coordinates signal
        self.text_ocr.coordinates_updated.connect(self._update_coordinates_display)
        
        # Update config
        ocr_settings = self.config_manager.get_ocr_settings()
        ocr_settings['active'] = True
        self.config_manager.update_ocr_settings(ocr_settings)
        
        # Start OCR processing
        self.text_ocr.start()
    
    def _stop_ocr(self) -> None:
        """Stop Text OCR processing."""
        logger.info("Stopping Text OCR")
        self.ocr_status.setText("Text OCR: Inactive")
        
        # Disconnect coordinates signal
        self.text_ocr.coordinates_updated.disconnect(self._update_coordinates_display)
        
        # Update config
        ocr_settings = self.config_manager.get_ocr_settings()
        ocr_settings['active'] = False
        self.config_manager.update_ocr_settings(ocr_settings)
        
        # Stop OCR processing
        self.text_ocr.stop()
    
    def _update_coordinates_display(self, coords: 'GameCoordinates') -> None:
        """Update the coordinate display in the GUI."""
        self.ocr_coords_label.setText(str(coords))

    def _start_ocr_region_selection(self) -> None:
        """Start the Text OCR region selection process."""
        logger.info("Starting Text OCR region selection")
        
        try:
            if hasattr(self, 'region_selector'):
                logger.debug("Cleaning up previous region selector")
                self.region_selector.close()
                self.region_selector.deleteLater()
            
            logger.debug("Creating new SelectorTool instance")
            self.region_selector = SelectorTool(
                window_manager=self.window_manager,
                instruction_text="Click and drag to select Text OCR region"
            )
            self.region_selector.region_selected.connect(self._on_ocr_region_selected)
            self.region_selector.selection_cancelled.connect(self._on_ocr_region_cancelled)
            
            # Don't hide main window, just show selector
            logger.debug("Scheduling selector display")
            QTimer.singleShot(100, lambda: self._show_selector())
            
        except Exception as e:
            logger.error(f"Error starting region selection: {e}")
            
    def _show_selector(self) -> None:
        """Helper method to show and activate the selector."""
        try:
            logger.debug("Showing selector tool")
            self.region_selector.show()
            logger.debug("Activating selector window")
            self.region_selector.activateWindow()
            logger.debug("Selector display complete")
        except Exception as e:
            logger.error(f"Error showing selector: {e}", exc_info=True)
    
    def _on_ocr_region_selected(self, region: dict) -> None:
        """Handle selected Text OCR region."""
        logger.info(f"Selected OCR region: {region}")
        
        try:
            # Update OCR settings
            ocr_settings = self.config_manager.get_ocr_settings()
            ocr_settings['region'] = {
                'left': region['left'],
                'top': region['top'],
                'width': region['width'],
                'height': region['height'],
                'dpi_scale': region['dpi_scale']
            }
            self.config_manager.update_ocr_settings(ocr_settings)
            
            # Update TextOCR instance
            self.text_ocr.set_region(ocr_settings['region'])
            
            # Update status with logical coordinates
            logical = region['logical_coords']
            self.ocr_status.setText(
                f"OCR region: ({logical['left']}, {logical['top']}) "
                f"[Physical: ({region['left']}, {region['top']})]"
            )
            
        except Exception as e:
            logger.error(f"Error saving OCR region: {e}", exc_info=True)
            
    def _on_ocr_region_cancelled(self) -> None:
        """Handle OCR region selection cancellation."""
        logger.info("OCR region selection cancelled")
        
        try:
            # Restore previous region status if it exists
            ocr_settings = self.config_manager.get_ocr_settings()
            if ocr_settings['region']['width'] > 0:
                status_text = f"OCR region: ({ocr_settings['region']['left']}, {ocr_settings['region']['top']})"
                logger.debug(f"Restoring previous OCR region status: {status_text}")
                self.ocr_status.setText(status_text)
            else:
                logger.debug("No previous OCR region settings found")
                self.ocr_status.setText("Text OCR: Inactive")
        except Exception as e:
            logger.error(f"Error handling region cancellation: {e}", exc_info=True)
            self.ocr_status.setText("Text OCR: Inactive")

    def on_ocr_slider_change(self, value: int) -> None:
        """
        Handle changes to the OCR frequency slider.
        
        Args:
            value: The slider value (1-20, representing 0.1-2.0 updates/sec)
        """
        # Convert slider value to frequency
        freq = value / 10.0
        logger.debug(f"OCR frequency slider changed: {value} -> {freq} updates/sec")
        
        # Update spinbox
        self.ocr_freq_input.setValue(freq)
        
        # Update OCR frequency
        if hasattr(self, 'text_ocr'):
            self.text_ocr.set_frequency(freq)
            
        # Save to config
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        ocr_settings['frequency'] = freq
        config.update_ocr_settings(ocr_settings)
        
    def on_ocr_spinbox_change(self, value: float) -> None:
        """
        Handle changes to the OCR frequency spinbox.
        
        Args:
            value: The frequency value in updates per second (0.1-2.0)
        """
        logger.debug(f"OCR frequency spinbox changed to: {value} updates/sec")
        
        # Update slider
        self.ocr_freq_slider.setValue(int(value * 10))
        
        # Update OCR frequency
        if hasattr(self, 'text_ocr'):
            self.text_ocr.set_frequency(value)
            
        # Save to config
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        ocr_settings['frequency'] = value
        config.update_ocr_settings(ocr_settings)

    def closeEvent(self, event) -> None:
        """
        Handle application close event.
        
        This method ensures proper cleanup when the application is closed:
        1. Closes the debug window if it's open
        2. Disables debug mode and saves settings
        3. Stops any active processes
        4. Performs parent class cleanup
        """
        logger.info("Application closing - performing cleanup")
        
        try:
            # Close debug window if it exists
            if hasattr(self, 'debug_window'):
                logger.debug("Closing debug window")
                self.debug_window.close()
            
            # Disable debug mode and save settings
            debug_settings = {
                "enabled": False,
                "save_screenshots": False,
                "save_templates": False
            }
            self.config_manager.update_debug_settings(debug_settings)
            
            # Stop pattern matching if active
            if hasattr(self, 'pattern_matcher'):
                logger.debug("Stopping pattern matching")
                self.pattern_matcher.set_debug_mode(False)
            
            # Save all settings
            self.save_settings()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during application cleanup: {e}", exc_info=True)
            
        finally:
            # Call parent class closeEvent
            super().closeEvent(event) 