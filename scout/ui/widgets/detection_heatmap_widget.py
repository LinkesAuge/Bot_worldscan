"""Detection Heatmap Widget

This module provides a widget for visualizing the frequency of detections across
different areas of the game window. It generates heatmaps showing where detections
occur most frequently to help identify patterns and important regions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from scout.core.detection.detection_service_interface import (
    DetectionServiceInterface,
)
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.ui.utils.language_manager import tr

# Set up logging
logger = logging.getLogger(__name__)

class DetectionHeatmapWidget(QWidget):
    """
    Widget for visualizing detection frequency as a heatmap.
    
    This widget shows where detections occur most frequently across the game window,
    providing insights into important regions and detection patterns.
    """
    
    def __init__(self, window_service: WindowServiceInterface,
                detection_service: DetectionServiceInterface):
        """
        Initialize the heatmap widget.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
        """
        super().__init__()
        
        self.window_service = window_service
        self.detection_service = detection_service
        
        # Initialize data storage
        self.detection_data = []
        self.screenshot = None
        self.heatmap_data = None
        
        # Create UI
        self._create_ui()
        self._connect_signals()
        
        logger.debug("DetectionHeatmapWidget initialized")
    
    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Add controls at the top
        control_layout = self._create_controls()
        main_layout.addLayout(control_layout)
        
        # Add a placeholder label instead of the matplotlib canvas
        self.heatmap_view = QLabel("Heatmap Visualization (Requires matplotlib library)")
        self.heatmap_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_view.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #cccccc; "
            "font-size: 14px; padding: 40px;"
        )
        self.heatmap_view.setMinimumSize(600, 400)
        main_layout.addWidget(self.heatmap_view)
        
        # Status bar
        self.status_label = QLabel(tr("No data loaded. Generate a heatmap to visualize detection patterns."))
        main_layout.addWidget(self.status_label)
    
    def _create_controls(self) -> QHBoxLayout:
        """
        Create control elements.
        
        Returns:
            Layout with control elements
        """
        control_layout = QHBoxLayout()
        
        # Settings group
        settings_group = QGroupBox(tr("Heatmap Settings"))
        settings_layout = QGridLayout(settings_group)
        
        # Strategy filter
        settings_layout.addWidget(QLabel(tr("Detection Type:")), 0, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(tr("All Types"), "all")
        self.strategy_combo.addItem(tr("Template Matching"), "template")
        self.strategy_combo.addItem(tr("OCR"), "ocr")
        self.strategy_combo.addItem(tr("YOLO"), "yolo")
        settings_layout.addWidget(self.strategy_combo, 0, 1)
        
        # Time range
        settings_layout.addWidget(QLabel(tr("Time Range:")), 1, 0)
        self.time_combo = QComboBox()
        self.time_combo.addItem(tr("All Time"), "all")
        self.time_combo.addItem(tr("Last Hour"), "hour")
        self.time_combo.addItem(tr("Last Day"), "day")
        self.time_combo.addItem(tr("Current Session"), "session")
        settings_layout.addWidget(self.time_combo, 1, 1)
        
        # Resolution
        settings_layout.addWidget(QLabel(tr("Resolution:")), 2, 0)
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(10, 200)
        self.resolution_spin.setValue(50)
        self.resolution_spin.setSuffix(" " + tr("cells"))
        settings_layout.addWidget(self.resolution_spin, 2, 1)
        
        # Confidence threshold
        settings_layout.addWidget(QLabel(tr("Min Confidence:")), 3, 0)
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(50)
        settings_layout.addWidget(self.confidence_slider, 3, 1)
        self.confidence_label = QLabel("50%")
        settings_layout.addWidget(self.confidence_label, 3, 2)
        
        # Opacity
        settings_layout.addWidget(QLabel(tr("Opacity:")), 4, 0)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(70)
        settings_layout.addWidget(self.opacity_slider, 4, 1)
        self.opacity_label = QLabel("70%")
        settings_layout.addWidget(self.opacity_label, 4, 2)
        
        # Background image
        self.show_background_check = QCheckBox(tr("Show Background"))
        self.show_background_check.setChecked(True)
        settings_layout.addWidget(self.show_background_check, 5, 0, 1, 2)
        
        control_layout.addWidget(settings_group)
        
        # Data source group
        source_group = QGroupBox(tr("Data Source"))
        source_layout = QVBoxLayout(source_group)
        
        # Radio buttons for data source
        self.source_radio_group = QButtonGroup(self)
        self.history_radio = QRadioButton(tr("Detection History"))
        self.session_radio = QRadioButton(tr("Current Session"))
        self.file_radio = QRadioButton(tr("Load from File"))
        self.dummy_radio = QRadioButton(tr("Demo Data"))
        
        self.history_radio.setChecked(True)
        
        self.source_radio_group.addButton(self.history_radio)
        self.source_radio_group.addButton(self.session_radio)
        self.source_radio_group.addButton(self.file_radio)
        self.source_radio_group.addButton(self.dummy_radio)
        
        source_layout.addWidget(self.history_radio)
        source_layout.addWidget(self.session_radio)
        source_layout.addWidget(self.file_radio)
        source_layout.addWidget(self.dummy_radio)
        
        # Load and generate buttons
        button_layout = QHBoxLayout()
        self.load_data_btn = QPushButton(tr("Load Data"))
        self.generate_btn = QPushButton(tr("Generate Heatmap"))
        self.export_btn = QPushButton(tr("Export..."))
        
        button_layout.addWidget(self.load_data_btn)
        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.export_btn)
        
        source_layout.addLayout(button_layout)
        control_layout.addWidget(source_group)
        
        return control_layout
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.history_radio.toggled.connect(lambda: self._on_source_changed(self.history_radio))
        self.session_radio.toggled.connect(lambda: self._on_source_changed(self.session_radio))
        self.file_radio.toggled.connect(lambda: self._on_source_changed(self.file_radio))
        self.dummy_radio.toggled.connect(lambda: self._on_source_changed(self.dummy_radio))
        self.load_data_btn.clicked.connect(self._on_load_data_clicked)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
    
    def _on_confidence_changed(self, value: int):
        """
        Handle confidence slider value change.
        
        Args:
            value: New slider value
        """
        self.confidence_label.setText(f"{value}%")
    
    def _on_opacity_changed(self, value: int):
        """
        Handle opacity slider value change.
        
        Args:
            value: New slider value
        """
        self.opacity_label.setText(f"{value}%")
    
    def _on_source_changed(self, button):
        """
        Handle data source selection change.
        
        Args:
            button: The selected radio button
        """
        # Enable/disable load button based on source
        self.load_data_btn.setEnabled(button is not self.dummy_radio)
    
    def _on_load_data_clicked(self):
        """Handle load data button click."""
        if self.history_radio.isChecked():
            self._load_data_from_history()
            self.status_label.setText(tr("Loaded data from detection history."))
        elif self.session_radio.isChecked():
            self._load_data_from_history(current_session_only=True)
            self.status_label.setText(tr("Loaded data from current session."))
        elif self.file_radio.isChecked():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                tr("Load Detection Data"),
                "",
                tr("JSON Files (*.json);;All Files (*.*)")
            )
            if file_path:
                self._load_data_from_file(file_path)
                self.status_label.setText(tr(f"Loaded data from {file_path}"))
    
    def _load_data_from_history(self, current_session_only: bool = False):
        """
        Load detection data from history.
        
        Args:
            current_session_only: Only load data from current session
        """
        # This would be implemented to load real data
        # For testing, just use dummy data
        self._load_dummy_data()
    
    def _load_data_from_file(self, file_path: str):
        """
        Load detection data from a file.
        
        Args:
            file_path: Path to detection data file
        """
        # This would be implemented to load data from a JSON file
        # For testing, just use dummy data
        self._load_dummy_data()
    
    def _load_dummy_data(self):
        """Load dummy detection data for testing."""
        # Create some dummy detection data
        self.detection_data = []
        
        # Example data structure:
        # {
        #     'timestamp': datetime.now(),
        #     'strategy': 'template',
        #     'results': [
        #         {
        #             'template': 'resource_gold.png',
        #             'confidence': 0.95,
        #             'position': (100, 150),
        #             'size': (50, 50)
        #         }
        #     ]
        # }
        
        # Generate some random detections
        num_entries = 20
        strategies = ['template', 'ocr', 'yolo']
        templates = ['resource_gold.png', 'resource_wood.png', 'building_townhall.png']
        
        for i in range(num_entries):
            timestamp = datetime.now() - timedelta(minutes=i * 10)
            strategy = strategies[i % len(strategies)]
            
            results = []
            num_results = np.random.randint(1, 10)
            
            for j in range(num_results):
                template = templates[np.random.randint(0, len(templates))]
                confidence = np.random.uniform(0.7, 0.99)
                position = (
                    np.random.randint(0, 1000),
                    np.random.randint(0, 800)
                )
                size = (
                    np.random.randint(30, 100),
                    np.random.randint(30, 100)
                )
                
                results.append({
                    'template': template,
                    'confidence': confidence,
                    'position': position,
                    'size': size
                })
            
            self.detection_data.append({
                'timestamp': timestamp,
                'strategy': strategy,
                'results': results
            })
        
        logger.debug(f"Loaded {len(self.detection_data)} dummy detection entries with {sum(len(entry['results']) for entry in self.detection_data)} total detections")
        
        # Create a dummy screenshot
        width, height = 1000, 800
        self.screenshot = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some simple visual elements to the screenshot
        # Border
        cv2.rectangle(self.screenshot, (0, 0), (width-1, height-1), (100, 100, 100), 2)
        
        # Some UI elements
        cv2.rectangle(self.screenshot, (0, 0), (width, 50), (50, 50, 50), -1)
        cv2.rectangle(self.screenshot, (0, 50), (200, height), (70, 70, 70), -1)
        
        # Some game elements
        cv2.rectangle(self.screenshot, (300, 200), (400, 250), (0, 0, 200), -1)  # Blue building
        cv2.rectangle(self.screenshot, (600, 300), (650, 350), (0, 200, 0), -1)  # Green resource
        cv2.rectangle(self.screenshot, (800, 500), (900, 550), (0, 200, 200), -1)  # Cyan something
        
        # Text areas
        cv2.rectangle(self.screenshot, (400, 400), (600, 430), (50, 50, 50), -1)
        
        self.status_label.setText(tr(f"Loaded dummy data with {len(self.detection_data)} detection entries."))
    
    def _on_generate_clicked(self):
        """Handle generate heatmap button click."""
        # Load dummy data if needed
        if self.dummy_radio.isChecked() or not self.detection_data:
            self._load_dummy_data()
        
        # Display a message that we need matplotlib
        self.heatmap_view.setText(
            tr("Heatmap generation requires the matplotlib library.")
            + "\n\n" +
            tr("Install it with: pip install matplotlib")
        )
        
        self.status_label.setText(tr("Heatmap would be generated here with matplotlib."))
        
        logger.debug("Generate heatmap clicked - requires matplotlib for actual visualization")
    
    def _on_export_clicked(self):
        """Handle export button click."""
        # Display a message that we need matplotlib
        QFileDialog.getSaveFileName(
            self,
            tr("Export Heatmap"),
            "",
            tr("PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*.*)")
        )
        
        self.status_label.setText(tr("Export functionality requires matplotlib."))
        logger.debug("Export heatmap clicked - requires matplotlib for actual functionality")
    
    def add_detection_event(self, timestamp: datetime, results: List[Dict], 
                            strategy: str, screenshot: Optional[np.ndarray] = None):
        """
        Add a new detection event to the history.
        
        Args:
            timestamp: When the detection occurred
            results: Detection results
            strategy: Detection strategy used
            screenshot: Optional screenshot for context
        """
        self.detection_data.append({
            'timestamp': timestamp,
            'strategy': strategy,
            'results': results
        })
        
        if screenshot is not None:
            self.screenshot = screenshot.copy()
        
        logger.debug(f"Added detection event with {len(results)} results using {strategy} strategy")
    
    def clear_data(self):
        """Clear all detection data."""
        self.detection_data = []
        self.screenshot = None
        self.heatmap_data = None
        
        # Reset the view
        self.heatmap_view.setText(tr("Heatmap Visualization (Requires matplotlib library)"))
        self.status_label.setText(tr("No data loaded. Generate a heatmap to visualize detection patterns."))
        
        logger.debug("Cleared all detection data")
