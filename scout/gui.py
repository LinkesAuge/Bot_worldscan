from typing import Optional, Callable, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, 
    QLabel, QFrame, QHBoxLayout, QSlider, QColorDialog,
    QSpinBox, QDoubleSpinBox, QGroupBox, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QIcon, QImage, QPixmap, QPainter, QPen, QBrush, QPaintEvent, QMouseEvent
import logging
from scout.config_manager import ConfigManager
from scout.overlay import Overlay
from scout.pattern_matcher import PatternMatcher
from scout.world_scanner import WorldScanner, WorldPosition, ScanLogHandler, ScanWorker
import numpy as np
from time import sleep
import pyautogui

logger = logging.getLogger(__name__)

class OverlayController(QMainWindow):
    """
    Main GUI window for controlling the overlay.
    """
    
    def __init__(self, overlay: Overlay, overlay_settings: Dict[str, Any], pattern_settings: Dict[str, Any]) -> None:
        """
        Initialize the controller window.
        
        Args:
            overlay: Overlay instance to control
            overlay_settings: Initial overlay settings
            pattern_settings: Initial pattern matching settings
        """
        super().__init__()
        
        self.overlay = overlay
        self.config_manager = ConfigManager()
        self.toggle_callback: Optional[Callable[[], None]] = None
        self.quit_callback: Optional[Callable[[], None]] = None
        
        # Get pattern matcher reference
        if hasattr(self.overlay, 'pattern_matcher'):
            self.pattern_matcher = self.overlay.pattern_matcher
        else:
            logger.error("Overlay does not have pattern_matcher attribute")
            raise AttributeError("Overlay must have pattern_matcher attribute")
        
        # Store colors
        self.current_color = overlay_settings["rect_color"]
        self.font_color = overlay_settings["font_color"]
        self.cross_color = overlay_settings["cross_color"]
        
        # Create UI
        self.setWindowTitle("Total Battle Scout")
        self.setGeometry(100, 100, 400, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create control groups
        self.create_overlay_controls(layout, overlay_settings)
        self.create_pattern_matching_controls(layout, pattern_settings)
        self.create_color_controls(layout)
        self.create_scan_controls(layout)
        
        # Add quit button at the bottom
        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet("background-color: #aa0000; color: white; padding: 8px; font-weight: bold;")
        quit_btn.clicked.connect(self._handle_quit)
        layout.addWidget(quit_btn)
        
        # Create status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Connect settings handlers
        self.connect_settings_handlers()
        
        # Add debug image viewer
        self.debug_viewer = DebugImageViewer()
        
        # Initialize scan controls with current region
        scanner_settings = self.config_manager.get_scanner_settings()
        if scanner_settings:
            self.scan_status.setText(
                f"Minimap region: ({scanner_settings['minimap_left']}, {scanner_settings['minimap_top']})"
            )
        
        # Create FPS update timer
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps_display)
        self.fps_timer.start(500)  # Update every 500ms
        
        logger.debug("GUI initialized")
    
    def create_overlay_controls(self, parent_layout: QVBoxLayout, settings: Dict[str, Any]) -> None:
        """Create overlay control widgets."""
        overlay_group = QGroupBox("TB Scout Overlay Controls")
        layout = QVBoxLayout()
        
        # Toggle button - initialize state from settings
        is_active = settings.get("active", False)  # Get initial state from settings
        self.toggle_btn = QPushButton(f"Toggle TB Scout Overlay (F10): {'ON' if is_active else 'OFF'}")
        self.toggle_btn.clicked.connect(self._handle_toggle)
        self._update_toggle_button_color(is_active)  # Set initial color
        self.overlay.active = is_active  # Set initial state in overlay
        layout.addWidget(self.toggle_btn)
        
        # Thickness controls
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_input = QSpinBox()
        thickness_layout = self._create_slider_with_range(
            "Thickness:", self.thickness_slider, self.thickness_input,
            1, 20, settings["rect_thickness"]
        )
        layout.addLayout(thickness_layout)
        
        # Scale controls
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_input = QDoubleSpinBox()  # Use QDoubleSpinBox for decimal values
        scale_layout = QHBoxLayout()
        
        # Left side with label and range
        scale_label_layout = QVBoxLayout()
        scale_label = QLabel("Rectangle Scale:")
        scale_range = QLabel("Range: 0.5-5.0")
        scale_range.setStyleSheet("color: gray; font-size: 8pt;")
        scale_label_layout.addWidget(scale_label)
        scale_label_layout.addWidget(scale_range)
        
        # Set up scale controls (multiply by 10 for slider)
        self.scale_slider.setRange(5, 50)  # 0.5 to 5.0
        self.scale_slider.setValue(int(settings["rect_scale"] * 10))
        
        self.scale_input.setRange(0.5, 5.0)
        self.scale_input.setSingleStep(0.1)
        self.scale_input.setValue(settings["rect_scale"])
        
        scale_layout.addLayout(scale_label_layout)
        scale_layout.addWidget(self.scale_slider, stretch=1)
        scale_layout.addWidget(self.scale_input)
        layout.addLayout(scale_layout)
        
        # Font size controls
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_input = QSpinBox()
        font_layout = self._create_slider_with_range(
            "Font Size:", self.font_size_slider, self.font_size_input,
            1, 100, settings["font_size"]
        )
        layout.addLayout(font_layout)
        
        # Font thickness controls (renamed from confidence)
        self.text_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_thickness_input = QSpinBox()
        text_thickness_layout = self._create_slider_with_range(
            "Font Thickness:", self.text_thickness_slider, self.text_thickness_input,
            1, 20, settings["text_thickness"]
        )
        layout.addLayout(text_thickness_layout)
        
        # Cross scale controls
        self.cross_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.cross_scale_input = QDoubleSpinBox()  # Use QDoubleSpinBox for decimal values
        cross_scale_layout = QHBoxLayout()
        
        # Left side with label and range
        cross_scale_label_layout = QVBoxLayout()
        cross_scale_label = QLabel("Cross Scale:")
        cross_scale_range = QLabel("Range: 0.5-5.0")
        cross_scale_range.setStyleSheet("color: gray; font-size: 8pt;")
        cross_scale_label_layout.addWidget(cross_scale_label)
        cross_scale_label_layout.addWidget(cross_scale_range)
        
        # Set up cross scale controls (multiply by 10 for slider)
        self.cross_scale_slider.setRange(5, 50)  # 0.5 to 5.0
        self.cross_scale_slider.setValue(int(settings["cross_scale"] if "cross_scale" in settings else 1.0 * 10))
        
        self.cross_scale_input.setRange(0.5, 5.0)
        self.cross_scale_input.setSingleStep(0.1)
        self.cross_scale_input.setValue(settings["cross_scale"] if "cross_scale" in settings else 1.0)
        
        cross_scale_layout.addLayout(cross_scale_label_layout)
        cross_scale_layout.addWidget(self.cross_scale_slider, stretch=1)
        cross_scale_layout.addWidget(self.cross_scale_input)
        layout.addLayout(cross_scale_layout)
        
        # Cross thickness controls
        self.cross_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.cross_thickness_input = QSpinBox()
        cross_layout = self._create_slider_with_range(
            "Cross Thickness:", self.cross_thickness_slider, self.cross_thickness_input,
            1, 20, settings["cross_thickness"]
        )
        layout.addLayout(cross_layout)
        
        overlay_group.setLayout(layout)
        parent_layout.addWidget(overlay_group)
    
    def create_pattern_matching_controls(self, parent_layout: QVBoxLayout, settings: Dict[str, Any]) -> None:
        """Create pattern matching control widgets."""
        pattern_group = QGroupBox("Pattern Matching")
        layout = QVBoxLayout()
        
        # Pattern matching toggle
        is_active = settings["active"]
        self.pattern_btn = QPushButton("Pattern Matching: ON" if is_active else "Pattern Matching: OFF")
        self.pattern_btn.clicked.connect(self._toggle_pattern_matching)
        self._update_pattern_button_color(is_active)
        layout.addWidget(self.pattern_btn)
        
        # Confidence slider
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_input = QSpinBox()
        confidence_layout = self._create_slider_with_range(
            "Confidence:", self.confidence_slider, self.confidence_input,
            10, 100, int(settings["confidence"] * 100)
        )
        layout.addLayout(confidence_layout)
        
        # FPS controls with decimal values
        fps_layout = QVBoxLayout()
        
        # FPS slider with range (we'll multiply by 10 to handle decimals)
        self.fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.fps_input = QDoubleSpinBox()  # Change to QDoubleSpinBox for decimals
        
        # Set up FPS controls
        self.fps_slider.setRange(1, 20)  # Range 0.1 to 2.0 (multiplied by 10)
        self.fps_slider.setValue(int(settings["target_fps"] * 10))
        
        self.fps_input.setRange(0.1, 2.0)  # Actual decimal range
        self.fps_input.setSingleStep(0.1)  # Step by 0.1
        self.fps_input.setValue(settings["target_fps"])
        
        fps_slider_layout = QHBoxLayout()
        fps_label = QLabel("Target FPS:")
        range_label = QLabel("Range: 0.1-2.0")
        range_label.setStyleSheet("color: gray; font-size: 8pt;")
        
        label_layout = QVBoxLayout()
        label_layout.addWidget(fps_label)
        label_layout.addWidget(range_label)
        
        fps_slider_layout.addLayout(label_layout)
        fps_slider_layout.addWidget(self.fps_slider, stretch=1)
        fps_slider_layout.addWidget(self.fps_input)
        fps_layout.addLayout(fps_slider_layout)
        
        # Add FPS display
        self.fps_display = QLabel(f"Target: {settings['target_fps']} FPS")
        self.fps_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fps_layout.addWidget(self.fps_display)
        
        layout.addLayout(fps_layout)
        
        # Connect FPS controls
        def on_slider_change(value: int) -> None:
            self.fps_input.setValue(value / 10.0)
            self.save_settings()
        
        def on_spinbox_change(value: float) -> None:
            self.fps_slider.setValue(int(value * 10))
            self.save_settings()
        
        self.fps_slider.valueChanged.connect(on_slider_change)
        self.fps_input.valueChanged.connect(on_spinbox_change)
        
        # Reload templates button
        self.reload_btn = QPushButton("Reload Templates")
        self.reload_btn.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.reload_btn)
        
        # Debug mode toggle button - initialize from config
        debug_settings = self.config_manager.get_debug_settings()
        self.debug_btn = QPushButton(f"Debug Mode: {'ON' if debug_settings['enabled'] else 'OFF'}")
        self.debug_btn.clicked.connect(self._toggle_debug_mode)
        self._update_debug_button_color(debug_settings['enabled'])  # Initialize color from config
        layout.addWidget(self.debug_btn)
        
        # Sound toggle button
        self.sound_btn = QPushButton("Sound Alerts: ON" if settings["sound_enabled"] else "Sound Alerts: OFF")
        self.sound_btn.clicked.connect(self._toggle_sound)  # Connect click handler
        self._update_sound_button_color(settings["sound_enabled"])
        layout.addWidget(self.sound_btn)
        
        pattern_group.setLayout(layout)
        parent_layout.addWidget(pattern_group)
    
    def create_color_controls(self, parent_layout: QVBoxLayout) -> None:
        """Create color selection controls."""
        color_group = QGroupBox("Colors")
        layout = QVBoxLayout()
        
        # Rectangle color
        self.rect_color_btn = QPushButton("Set Rectangle Color")
        self.rect_color_btn.clicked.connect(self._choose_rect_color)
        self.rect_color_btn.setStyleSheet(f"background-color: {self.current_color.name()}; font-weight: bold;")
        layout.addWidget(self.rect_color_btn)
        
        # Font color
        self.font_color_btn = QPushButton("Set Font Color")
        self.font_color_btn.clicked.connect(self._choose_font_color)
        self.font_color_btn.setStyleSheet(f"background-color: {self.font_color.name()}; font-weight: bold;")
        layout.addWidget(self.font_color_btn)
        
        # Cross color
        self.cross_color_btn = QPushButton("Set Cross Color")
        self.cross_color_btn.clicked.connect(self._choose_cross_color)
        self.cross_color_btn.setStyleSheet(f"background-color: {self.cross_color.name()}; font-weight: bold;")
        layout.addWidget(self.cross_color_btn)
        
        color_group.setLayout(layout)
        parent_layout.addWidget(color_group)
    
    def create_scan_controls(self, layout: QVBoxLayout) -> None:
        """Create controls for world scanning."""
        group = QGroupBox("World Scanner")
        group_layout = QVBoxLayout()
        
        # Scan button
        self.scan_btn = QPushButton("Start World Scan")
        self.scan_btn.setCheckable(True)
        self.scan_btn.clicked.connect(self._toggle_scan)
        group_layout.addWidget(self.scan_btn)
        
        # Add region selection button
        self.select_region_btn = QPushButton("Select Minimap Region")
        self.select_region_btn.clicked.connect(self._start_region_selection)
        group_layout.addWidget(self.select_region_btn)
        
        # Status label
        self.scan_status = QLabel("Scanner: Inactive")
        group_layout.addWidget(self.scan_status)
        
        # Add input field configuration button
        self.input_field_btn = QPushButton("Set Coordinate Input Location")
        self.input_field_btn.clicked.connect(self._start_input_field_selection)
        group_layout.addWidget(self.input_field_btn)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
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
    
    def update_fps_display(self, target_fps: float, actual_fps: float) -> None:
        """Update FPS display label."""
        self.fps_display.setText(f"Target: {target_fps:.1f} FPS, Actual: {actual_fps:.1f} FPS")
    
    def _handle_quit(self) -> None:
        """Handle quit button click."""
        if self.quit_callback:
            self.quit_callback()
    
    def save_settings(self) -> None:
        """Save current settings to config."""
        try:
            self.config_manager.update_overlay_settings(
                active=self.overlay.active,
                rect_color=self.current_color,
                rect_thickness=self.thickness_slider.value(),
                rect_scale=self.scale_input.value(),
                font_color=self.font_color,
                font_size=self.font_size_slider.value(),
                text_thickness=self.text_thickness_slider.value(),
                cross_color=self.cross_color,
                cross_size=self.overlay.cross_size,
                cross_thickness=self.cross_thickness_slider.value(),
                cross_scale=self.cross_scale_input.value()
            )
            
            self.config_manager.update_pattern_matching_settings(
                active=self.pattern_btn.text().endswith("ON"),
                confidence=self.confidence_slider.value() / 100.0,
                target_fps=self.fps_input.value(),
                sound_enabled=self.sound_btn.text().endswith("ON")
            )
            
            logger.debug("Settings saved to config")
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}", exc_info=True)
    
    def connect_settings_handlers(self) -> None:
        """Connect all interactive elements to save settings."""
        # Connect sliders to input boxes and vice versa (except FPS which is handled separately)
        def on_thickness_change(value: int) -> None:
            self.thickness_input.setValue(value)
            self.overlay.rect_thickness = value
            self.save_settings()
            
        def on_font_size_change(value: int) -> None:
            self.font_size_input.setValue(value)
            self.overlay.font_size = value
            self.save_settings()
            
        def on_text_thickness_change(value: int) -> None:
            self.text_thickness_input.setValue(value)
            self.overlay.text_thickness = value
            self.save_settings()
            
        def on_cross_thickness_change(value: int) -> None:
            self.cross_thickness_input.setValue(value)
            self.overlay.cross_thickness = value
            self.save_settings()
            
        # Connect confidence controls
        def on_confidence_slider_change(value: int) -> None:
            self.confidence_input.setValue(value)
            # Convert from percentage (0-100) to decimal (0.0-1.0)
            confidence = value / 100.0
            self.pattern_matcher.confidence = confidence
            self.save_settings()
            logger.debug(f"Confidence updated to: {confidence:.2f}")
            
        def on_confidence_spinbox_change(value: int) -> None:
            self.confidence_slider.setValue(value)
            # Convert from percentage (0-100) to decimal (0.0-1.0)
            confidence = value / 100.0
            self.pattern_matcher.confidence = confidence
            self.save_settings()
            logger.debug(f"Confidence updated to: {confidence:.2f}")
            
        # Connect scale controls
        def on_rect_scale_slider_change(value: int) -> None:
            scale = value / 10.0
            self.scale_input.setValue(scale)
            self.overlay.rect_scale = scale
            self.save_settings()
        
        def on_rect_scale_spinbox_change(value: float) -> None:
            self.scale_slider.setValue(int(value * 10))
            self.overlay.rect_scale = value
            self.save_settings()
            
        def on_cross_scale_slider_change(value: int) -> None:
            scale = value / 10.0
            self.cross_scale_input.setValue(scale)
            self.overlay.cross_scale = scale
            self.save_settings()
            
        def on_cross_scale_spinbox_change(value: float) -> None:
            self.cross_scale_slider.setValue(int(value * 10))
            self.overlay.cross_scale = value
            self.save_settings()
        
        # Connect all sliders to their handlers
        self.thickness_slider.valueChanged.connect(on_thickness_change)
        self.font_size_slider.valueChanged.connect(on_font_size_change)
        self.text_thickness_slider.valueChanged.connect(on_text_thickness_change)
        self.cross_thickness_slider.valueChanged.connect(on_cross_thickness_change)
        self.confidence_slider.valueChanged.connect(on_confidence_slider_change)
        self.confidence_input.valueChanged.connect(on_confidence_spinbox_change)
        self.scale_slider.valueChanged.connect(on_rect_scale_slider_change)
        self.scale_input.valueChanged.connect(on_rect_scale_spinbox_change)
        self.cross_scale_slider.valueChanged.connect(on_cross_scale_spinbox_change)
        self.cross_scale_input.valueChanged.connect(on_cross_scale_spinbox_change)
        
        # Connect input boxes to their sliders
        self.thickness_input.valueChanged.connect(self.thickness_slider.setValue)
        self.font_size_input.valueChanged.connect(self.font_size_slider.setValue)
        self.text_thickness_input.valueChanged.connect(self.text_thickness_slider.setValue)
        self.cross_thickness_input.valueChanged.connect(self.cross_thickness_slider.setValue)
        
        # Connect reload templates button
        self.reload_btn.clicked.connect(self._reload_templates)
        
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

    def _create_slider_with_range(self, label: str, slider: QSlider, input_box: QSpinBox, 
                                min_val: int, max_val: int, current_val: int) -> QHBoxLayout:
        """
        Create a slider layout with range indicators.
        
        Args:
            label: Label text for the control
            slider: The slider widget
            input_box: The input spin box
            min_val: Minimum value
            max_val: Maximum value
            current_val: Current value
        
        Returns:
            QHBoxLayout: The complete layout
        """
        layout = QHBoxLayout()
        
        # Set up slider
        slider.setRange(min_val, max_val)
        slider.setValue(current_val)
        
        # Set up input box
        input_box.setRange(min_val, max_val)
        input_box.setValue(current_val)
        
        # Left side with label and range
        label_layout = QVBoxLayout()
        main_label = QLabel(label)
        range_label = QLabel(f"Range: {min_val}-{max_val}")
        range_label.setStyleSheet("color: gray; font-size: 8pt;")
        label_layout.addWidget(main_label)
        label_layout.addWidget(range_label)
        
        # Add components to main layout
        layout.addLayout(label_layout)
        layout.addWidget(slider, stretch=1)  # Give slider more space
        layout.addWidget(input_box)
        
        return layout 

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
            self.debug_viewer.hide()
    
    def _start_world_scan(self) -> None:
        """Start the world scanning process."""
        try:
            # Ensure pattern matching is active
            if not self.pattern_btn.text().endswith("ON"):
                logger.info("Activating pattern matching for scan")
                self.pattern_btn.setText("Pattern Matching: ON")
                self._update_pattern_button_color(True)
                # Update config and activate pattern matching
                self.config_manager.update_pattern_matching_settings(
                    active=True,
                    confidence=self.confidence_slider.value() / 100.0,
                    target_fps=self.fps_input.value(),
                    sound_enabled=self.sound_btn.text().endswith("ON")
                )
                # Actually start pattern matching in overlay
                self.overlay.start_pattern_matching()
            elif not self.overlay.pattern_matching_active:
                logger.info("Restarting pattern matching")
                self.overlay.start_pattern_matching()
            
            # Initialize scanner with current position
            start_pos = WorldPosition(x=0, y=0, k=1)
            self.scanner = WorldScanner(start_pos)
            self.log_handler = ScanLogHandler()
            
            # Show debug viewer
            self.debug_viewer.show()
            
            # Start in a separate thread
            self.scan_thread = QThread()
            self.scan_worker = ScanWorker(self.scanner, self.pattern_matcher)
            self.scan_worker.moveToThread(self.scan_thread)
            
            # Connect signals
            self.scan_thread.started.connect(self.scan_worker.run)
            self.scan_worker.position_found.connect(self._on_position_found)
            self.scan_worker.error.connect(self._on_scan_error)
            self.scan_worker.finished.connect(self.scan_thread.quit)
            self.scan_worker.debug_image.connect(self.debug_viewer.update_image)
            
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
                self.region_selector.close()
                self.region_selector.deleteLater()
            
            self.region_selector = RegionSelector()
            self.region_selector.region_selected.connect(self._on_region_selected)
            self.region_selector.selection_cancelled.connect(self._on_region_cancelled)
            
            # Don't hide main window, just show selector
            QTimer.singleShot(100, self.region_selector.show)
            QTimer.singleShot(100, self.region_selector.activateWindow)
            
            logger.debug("Region selector window displayed")
            
        except Exception as e:
            logger.error(f"Error starting region selection: {e}", exc_info=True)
    
    def _on_region_selected(self, region: dict) -> None:
        """Handle selected region."""
        logger.info(f"Selected region: {region}")
        
        try:
            # Convert region to scanner settings format
            settings = {
                'minimap_left': region['left'],
                'minimap_top': region['top'],
                'minimap_width': region['width'],
                'minimap_height': region['height']
            }
            
            # Save region to config
            self.config_manager.update_scanner_settings(settings)
            logger.info("Region saved to config")
            
            # Update status
            self.scan_status.setText(f"Minimap region set: ({region['left']}, {region['top']})")
            logger.debug("Status updated")
            
        except Exception as e:
            logger.error(f"Error saving region: {e}", exc_info=True)
            self.scan_status.setText("Error saving region!")

    def _on_region_cancelled(self) -> None:
        """Handle region selection cancellation."""
        logger.info("Region selection cancelled")
        
        # Restore previous region status if it exists
        scanner_settings = self.config_manager.get_scanner_settings()
        if scanner_settings:
            self.scan_status.setText(
                f"Minimap region: ({scanner_settings['minimap_left']}, {scanner_settings['minimap_top']})"
            )
        else:
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
        is_active = self.pattern_btn.text().endswith("ON")
        new_state = not is_active
        
        # Update confidence in pattern matcher before toggling
        if new_state:  # If turning ON
            self.pattern_matcher.confidence = self.confidence_slider.value() / 100.0
            logger.debug(f"Updated pattern matcher confidence to: {self.pattern_matcher.confidence:.2f}")
        
        self._update_pattern_button_color(new_state)  # Toggle state
        
        # Save the new state
        self.config_manager.update_pattern_matching_settings(
            active=new_state,
            confidence=self.confidence_slider.value() / 100.0,
            target_fps=self.fps_input.value(),
            sound_enabled=self.sound_btn.text().endswith("ON")
        )

    def _toggle_sound(self) -> None:
        """Toggle sound alerts on/off."""
        is_enabled = self.sound_btn.text().endswith("ON")
        new_state = not is_enabled
        
        # Update button state
        self.sound_btn.setText(f"Sound Alerts: {'ON' if new_state else 'OFF'}")
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

    def _update_fps_display(self) -> None:
        """Update the FPS display with current values."""
        if hasattr(self.pattern_matcher, 'fps'):
            actual_fps = self.pattern_matcher.fps
            target_fps = self.fps_input.value()
            self.fps_display.setText(f"Target: {target_fps:.1f} FPS, Actual: {actual_fps:.1f} FPS")
            
            # Color code the display based on performance
            if actual_fps >= target_fps * 0.9:  # Within 90% of target
                self.fps_display.setStyleSheet("color: green;")
            elif actual_fps >= target_fps * 0.7:  # Within 70% of target
                self.fps_display.setStyleSheet("color: orange;")
            else:  # Below 70% of target
                self.fps_display.setStyleSheet("color: red;")
        else:
            self.fps_display.setText("FPS: N/A")
            self.fps_display.setStyleSheet("")

    def _toggle_debug_mode(self) -> None:
        """Toggle debug mode on/off."""
        is_enabled = self.debug_btn.text().endswith("ON")
        new_state = not is_enabled
        
        # Update button state
        self.debug_btn.setText(f"Debug Mode: {'ON' if new_state else 'OFF'}")
        self._update_debug_button_color(new_state)
        
        # Update pattern matcher debug state
        if hasattr(self.pattern_matcher, 'set_debug_mode'):
            self.pattern_matcher.set_debug_mode(new_state)
        
        # Save debug settings to config
        self.config_manager.update_debug_settings(
            enabled=new_state,
            save_screenshots=True,  # Keep default values for now
            save_templates=True
        )
            
        logger.info(f"Debug mode {'enabled' if new_state else 'disabled'}")

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

class DebugImageViewer(QWidget):
    """Window for displaying debug images."""
    
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Debug Images")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        
        # Coordinate values
        self.coord_label = QLabel()
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coord_label)
        
        self.setLayout(layout)
        
    def update_image(self, image: np.ndarray, coord_type: str, value: int) -> None:
        """Update the displayed image and coordinate value."""
        height, width = image.shape[:2]
        bytes_per_line = width
        
        # Convert image to QImage
        q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        
        # Scale image for display
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(
            400, 200, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
        self.coord_label.setText(f"{coord_type} coordinate: {value}") 

class RegionSelector(QWidget):
    """Widget for selecting a screen region."""
    
    region_selected = pyqtSignal(dict)  # Emits region as dict (left, top, width, height)
    selection_cancelled = pyqtSignal()  # Add new signal for cancellation
    
    def __init__(self) -> None:
        super().__init__()
        logger.info("Initializing region selector")
        
        # Set window flags - remove Tool flag as it can interfere with dialog
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Initialize selection variables
        self.start_pos = None
        self.current_pos = None
        self.is_selecting = False
        
        # Make the widget fullscreen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # Add a label to show instructions
        self.instruction_label = QLabel("Click and drag to select minimap region", self)
        self.instruction_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                padding: 10px;
                border-radius: 5px;
            }
        """)
        self.instruction_label.adjustSize()
        self.instruction_label.move(20, 20)
        
        logger.debug(f"Region selector set to fullscreen: {screen}")
        
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the selection overlay."""
        painter = QPainter(self)
        
        # Draw semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))  # Almost transparent black
        
        if self.is_selecting and self.start_pos and self.current_pos:
            # Draw selection rectangle
            painter.setPen(QPen(QColor(0, 255, 0), 2))  # Green border
            color = QColor(0, 255, 0, 50)  # Green with 50/255 alpha
            painter.setBrush(QBrush(color))
            
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            painter.drawRect(x, y, width, height)
            
            # Draw size info
            size_text = f"{width}x{height}"
            painter.setPen(QPen(QColor(255, 255, 255)))  # White text
            painter.drawText(x + 5, y - 5, size_text)
            
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.is_selecting = True
            logger.debug(f"Started selection at position: ({self.start_pos.x()}, {self.start_pos.y()})")
            
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement to update selection."""
        if self.is_selecting:
            self.current_pos = event.pos()
            # Log every 10 pixels moved to avoid spam
            if self.current_pos.x() % 10 == 0 and self.current_pos.y() % 10 == 0:
                logger.debug(f"Selection updated to: ({self.current_pos.x()}, {self.current_pos.y()})")
            self.update()
            
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to finish selection."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            
            # If mouse was released without moving, use the start position
            if self.current_pos is None:
                self.current_pos = self.start_pos
                logger.debug("Using start position as no movement detected")
            
            try:
                # Calculate region
                x = min(self.start_pos.x(), self.current_pos.x())
                y = min(self.start_pos.y(), self.current_pos.y())
                width = abs(self.current_pos.x() - self.start_pos.x())
                height = abs(self.current_pos.y() - self.start_pos.y())
                
                # Ensure minimum size
                if width < 10 or height < 10:
                    logger.warning("Selection too small, ignoring")
                    # Reset and show selector again
                    self.start_pos = None
                    self.current_pos = None
                    self.is_selecting = False
                    QTimer.singleShot(100, self.show)
                    QTimer.singleShot(100, self.update)
                    return
                
                region = {
                    'left': x,
                    'top': y,
                    'width': width,
                    'height': height
                }
                
                logger.info(f"Selection completed: {region}")
                
                # Hide the selector window before showing dialog
                self.hide()
                
                # Show confirmation dialog
                msg = QMessageBox()
                msg.setWindowTitle("Confirm Selection")
                msg.setText(f"Use this region?\nPosition: ({x}, {y})\nSize: {width}x{height}")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
                
                result = msg.exec()
                if result == QMessageBox.StandardButton.Yes:
                    logger.info("Selection confirmed by user")
                    self.region_selected.emit(region)
                    self.close()
                else:
                    logger.info("Selection cancelled by user")
                    self.selection_cancelled.emit()  # Emit cancellation signal
                    self.close()
                    
            except Exception as e:
                logger.error(f"Error during selection: {e}", exc_info=True)
                self.selection_cancelled.emit()  # Emit cancellation signal on error
                self.close() 