"""
Detection Tab

This module provides the Detection Tab view for the Scout application.
It allows users to configure and run detection operations using different strategies,
view detection results, and manage templates.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QGroupBox, 
    QTabWidget, QScrollArea, QFrame, QSplitter, QFileDialog,
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QImage

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.ui.widgets.template_list_widget import TemplateListWidget
from scout.ui.widgets.detection_result_widget import DetectionResultWidget

# Set up logging
logger = logging.getLogger(__name__)

class DetectionTab(QWidget):
    """
    Detection Tab for configuring and running detection operations.
    
    This tab provides:
    - Template management interface
    - Detection strategy configuration
    - Result visualization
    - Controls for running detection operations
    """
    
    # Signals
    detection_requested = pyqtSignal(str, dict)  # Strategy name, params
    
    def __init__(self, window_service: WindowServiceInterface, 
                 detection_service: DetectionServiceInterface):
        """
        Initialize the detection tab.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
        """
        super().__init__()
        
        self.window_service = window_service
        self.detection_service = detection_service
        
        # Initialize state
        self._current_strategy = "template"
        self._template_dir = Path("scout/resources/templates")
        self._detection_results = []
        
        # Create UI layout
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Load templates
        self._load_templates()
        
        logger.info("Detection tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side - Configuration
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # Detection strategy selection
        strategy_group = QGroupBox("Detection Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Template Matching", "template")
        self.strategy_combo.addItem("OCR Text Recognition", "ocr")
        self.strategy_combo.addItem("YOLO Object Detection", "yolo")
        strategy_layout.addWidget(self.strategy_combo)
        
        config_layout.addWidget(strategy_group)
        
        # Create stacked widget for strategy-specific settings
        self.strategy_tabs = QTabWidget()
        
        # Template matching settings
        self.template_tab = QWidget()
        template_layout = QVBoxLayout(self.template_tab)
        
        # Template list
        self.template_list = TemplateListWidget(str(self._template_dir))
        template_layout.addWidget(self.template_list)
        
        # Template confidence setting
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence:"))
        
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(70)  # Default 0.7
        confidence_layout.addWidget(self.confidence_slider, stretch=1)
        
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 1.0)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setValue(0.7)
        confidence_layout.addWidget(self.confidence_spin)
        
        template_layout.addLayout(confidence_layout)
        
        # Maximum results
        max_results_layout = QHBoxLayout()
        max_results_layout.addWidget(QLabel("Max Results:"))
        
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(1, 100)
        self.max_results_spin.setValue(10)
        max_results_layout.addWidget(self.max_results_spin)
        
        template_layout.addLayout(max_results_layout)
        
        # Add template tab
        self.strategy_tabs.addTab(self.template_tab, "Template Matching")
        
        # OCR settings
        self.ocr_tab = QWidget()
        ocr_layout = QVBoxLayout(self.ocr_tab)
        
        # Text pattern
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Text Pattern:"))
        
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("Leave empty to detect all text")
        pattern_layout.addWidget(self.pattern_edit)
        
        ocr_layout.addLayout(pattern_layout)
        
        # OCR confidence
        ocr_confidence_layout = QHBoxLayout()
        ocr_confidence_layout.addWidget(QLabel("Confidence:"))
        
        self.ocr_confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_confidence_slider.setRange(1, 100)
        self.ocr_confidence_slider.setValue(60)  # Default 0.6
        ocr_confidence_layout.addWidget(self.ocr_confidence_slider, stretch=1)
        
        self.ocr_confidence_spin = QDoubleSpinBox()
        self.ocr_confidence_spin.setRange(0.01, 1.0)
        self.ocr_confidence_spin.setSingleStep(0.01)
        self.ocr_confidence_spin.setValue(0.6)
        ocr_confidence_layout.addWidget(self.ocr_confidence_spin)
        
        ocr_layout.addLayout(ocr_confidence_layout)
        
        # Preprocessing options
        preprocess_layout = QVBoxLayout()
        preprocess_layout.addWidget(QLabel("Preprocessing:"))
        
        self.preprocess_none = QCheckBox("None")
        self.preprocess_none.setChecked(True)
        preprocess_layout.addWidget(self.preprocess_none)
        
        self.preprocess_threshold = QCheckBox("Threshold")
        preprocess_layout.addWidget(self.preprocess_threshold)
        
        self.preprocess_grayscale = QCheckBox("Grayscale")
        preprocess_layout.addWidget(self.preprocess_grayscale)
        
        self.preprocess_blur = QCheckBox("Blur")
        preprocess_layout.addWidget(self.preprocess_blur)
        
        ocr_layout.addLayout(preprocess_layout)
        
        # Add OCR tab
        self.strategy_tabs.addTab(self.ocr_tab, "OCR")
        
        # YOLO settings
        self.yolo_tab = QWidget()
        yolo_layout = QVBoxLayout(self.yolo_tab)
        
        # Class selection
        yolo_layout.addWidget(QLabel("Object Classes:"))
        
        self.class_list = QListWidget()
        # Populate with default classes when YOLO is initialized
        yolo_layout.addWidget(self.class_list)
        
        # YOLO confidence
        yolo_confidence_layout = QHBoxLayout()
        yolo_confidence_layout.addWidget(QLabel("Confidence:"))
        
        self.yolo_confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.yolo_confidence_slider.setRange(1, 100)
        self.yolo_confidence_slider.setValue(50)  # Default 0.5
        yolo_confidence_layout.addWidget(self.yolo_confidence_slider, stretch=1)
        
        self.yolo_confidence_spin = QDoubleSpinBox()
        self.yolo_confidence_spin.setRange(0.01, 1.0)
        self.yolo_confidence_spin.setSingleStep(0.01)
        self.yolo_confidence_spin.setValue(0.5)
        yolo_confidence_layout.addWidget(self.yolo_confidence_spin)
        
        yolo_layout.addLayout(yolo_confidence_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        
        self.model_combo = QComboBox()
        self.model_combo.addItem("YOLOv8n", "yolov8n")
        self.model_combo.addItem("YOLOv8s", "yolov8s")
        self.model_combo.addItem("YOLOv8m", "yolov8m")
        model_layout.addWidget(self.model_combo)
        
        yolo_layout.addLayout(model_layout)
        
        # Add YOLO tab
        self.strategy_tabs.addTab(self.yolo_tab, "YOLO")
        
        # Add strategy tabs to config layout
        config_layout.addWidget(self.strategy_tabs)
        
        # Add region selection
        region_group = QGroupBox("Detection Region")
        region_layout = QVBoxLayout(region_group)
        
        self.full_screen_check = QCheckBox("Full Game Window")
        self.full_screen_check.setChecked(True)
        region_layout.addWidget(self.full_screen_check)
        
        region_buttons_layout = QHBoxLayout()
        
        self.select_region_btn = QPushButton("Select Region")
        self.select_region_btn.setEnabled(False)
        region_buttons_layout.addWidget(self.select_region_btn)
        
        self.clear_region_btn = QPushButton("Clear Region")
        self.clear_region_btn.setEnabled(False)
        region_buttons_layout.addWidget(self.clear_region_btn)
        
        region_layout.addLayout(region_buttons_layout)
        
        # Region info label
        self.region_info_label = QLabel("Region: Full Window")
        region_layout.addWidget(self.region_info_label)
        
        config_layout.addWidget(region_group)
        
        # Run detection button
        self.run_button = QPushButton("Run Detection")
        self.run_button.setStyleSheet("font-weight: bold; padding: 8px;")
        config_layout.addWidget(self.run_button)
        
        # Add configuration widget to splitter
        splitter.addWidget(config_widget)
        
        # Right side - Results
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Results header
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Detection Results"))
        
        self.results_count_label = QLabel("0 results")
        results_header.addWidget(self.results_count_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        results_layout.addLayout(results_header)
        
        # Results display
        self.results_widget = DetectionResultWidget(self.window_service)
        results_layout.addWidget(self.results_widget)
        
        # Add results widget to splitter
        splitter.addWidget(results_widget)
        
        # Set initial splitter sizes (40% left, 60% right)
        splitter.setSizes([400, 600])
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Strategy selection
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        
        # Template confidence sync
        self.confidence_slider.valueChanged.connect(
            lambda val: self.confidence_spin.setValue(val / 100.0)
        )
        self.confidence_spin.valueChanged.connect(
            lambda val: self.confidence_slider.setValue(int(val * 100))
        )
        
        # OCR confidence sync
        self.ocr_confidence_slider.valueChanged.connect(
            lambda val: self.ocr_confidence_spin.setValue(val / 100.0)
        )
        self.ocr_confidence_spin.valueChanged.connect(
            lambda val: self.ocr_confidence_slider.setValue(int(val * 100))
        )
        
        # YOLO confidence sync
        self.yolo_confidence_slider.valueChanged.connect(
            lambda val: self.yolo_confidence_spin.setValue(val / 100.0)
        )
        self.yolo_confidence_spin.valueChanged.connect(
            lambda val: self.yolo_confidence_slider.setValue(int(val * 100))
        )
        
        # Region selection
        self.full_screen_check.toggled.connect(self._on_full_screen_toggled)
        self.select_region_btn.clicked.connect(self._on_select_region_clicked)
        self.clear_region_btn.clicked.connect(self._on_clear_region_clicked)
        
        # Preprocess options mutual exclusivity
        self.preprocess_none.toggled.connect(self._on_preprocess_none_toggled)
        
        # Run detection
        self.run_button.clicked.connect(self.run_detection)
    
    def _on_strategy_changed(self, index: int) -> None:
        """
        Handle detection strategy change.
        
        Args:
            index: Index of the selected strategy
        """
        strategy = self.strategy_combo.currentData()
        self._current_strategy = strategy
        
        # Update strategy-specific UI elements if needed
        self.strategy_tabs.setCurrentIndex(index)
    
    def _on_full_screen_toggled(self, checked: bool) -> None:
        """
        Handle full screen toggle.
        
        Args:
            checked: Whether full screen is enabled
        """
        self.select_region_btn.setEnabled(not checked)
        self.clear_region_btn.setEnabled(not checked and hasattr(self, '_region'))
        
        if checked:
            self.region_info_label.setText("Region: Full Window")
            if hasattr(self, '_region'):
                delattr(self, '_region')
    
    def _on_select_region_clicked(self) -> None:
        """Handle select region button click."""
        # First check if we can find the game window
        if not self.window_service.find_window():
            QMessageBox.warning(self, "Error", "Could not find game window")
            return
        
        # TODO: Implement region selection using the overlay or a selector tool
        # For now, just set a hardcoded region
        self._region = {'x': 100, 'y': 100, 'width': 400, 'height': 400}
        self.region_info_label.setText(
            f"Region: ({self._region['x']}, {self._region['y']}, "
            f"{self._region['width']}x{self._region['height']})"
        )
        
        self.clear_region_btn.setEnabled(True)
    
    def _on_clear_region_clicked(self) -> None:
        """Handle clear region button click."""
        if hasattr(self, '_region'):
            delattr(self, '_region')
        
        self.region_info_label.setText("Region: Full Window")
        self.clear_region_btn.setEnabled(False)
    
    def _on_preprocess_none_toggled(self, checked: bool) -> None:
        """
        Handle preprocess none option toggle.
        
        Args:
            checked: Whether "None" preprocessing is checked
        """
        # Disable other options if "None" is checked
        self.preprocess_threshold.setEnabled(not checked)
        self.preprocess_grayscale.setEnabled(not checked)
        self.preprocess_blur.setEnabled(not checked)
        
        if checked:
            self.preprocess_threshold.setChecked(False)
            self.preprocess_grayscale.setChecked(False)
            self.preprocess_blur.setChecked(False)
    
    def _load_templates(self) -> None:
        """Load templates from the templates directory."""
        try:
            # Ensure template directory exists
            self._template_dir.mkdir(parents=True, exist_ok=True)
            
            # Load templates into list
            self.template_list.load_templates()
            
            # Log template count
            template_count = self.template_list.count()
            logger.info(f"Loaded {template_count} templates from {self._template_dir}")
            
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def run_detection(self) -> None:
        """Run detection with the current settings."""
        # First check if we can find the game window
        if not self.window_service.find_window():
            QMessageBox.warning(self, "Error", "Could not find game window")
            return
        
        # Get detection parameters based on current strategy
        params = self._get_detection_params()
        
        logger.info(f"Running detection with strategy: {self._current_strategy}, params: {params}")
        
        # Run detection
        results = []
        try:
            if self._current_strategy == "template":
                # Get selected templates
                templates = self.template_list.get_selected_templates()
                if not templates:
                    QMessageBox.warning(self, "Error", "No templates selected")
                    return
                
                params['template_names'] = templates
                results = self.detection_service.detect_template(**params)
                
            elif self._current_strategy == "ocr":
                results = self.detection_service.detect_text(**params)
                
            elif self._current_strategy == "yolo":
                # Get selected classes
                selected_items = self.class_list.selectedItems()
                class_names = [item.text() for item in selected_items]
                
                if not class_names:
                    QMessageBox.warning(self, "Error", "No object classes selected")
                    return
                
                params['class_names'] = class_names
                results = self.detection_service.detect_objects(**params)
        
        except Exception as e:
            logger.error(f"Error running detection: {e}")
            QMessageBox.critical(self, "Error", f"Detection failed: {e}")
            return
        
        # Store and display results
        self._detection_results = results
        self.results_count_label.setText(f"{len(results)} results")
        self.results_widget.display_results(results, self._current_strategy)
        
        # Emit signal
        self.detection_requested.emit(self._current_strategy, params)
    
    def _get_detection_params(self) -> Dict[str, Any]:
        """
        Get detection parameters based on current settings.
        
        Returns:
            Dictionary of detection parameters
        """
        params = {}
        
        # Add region parameter if custom region is set
        if not self.full_screen_check.isChecked() and hasattr(self, '_region'):
            params['region'] = self._region
        
        # Strategy-specific parameters
        if self._current_strategy == "template":
            params['confidence_threshold'] = self.confidence_spin.value()
            params['max_results'] = self.max_results_spin.value()
            
        elif self._current_strategy == "ocr":
            # Get pattern if specified
            pattern = self.pattern_edit.text()
            if pattern:
                params['pattern'] = pattern
                
            params['confidence_threshold'] = self.ocr_confidence_spin.value()
            
            # Preprocessing options
            if not self.preprocess_none.isChecked():
                preprocess = []
                if self.preprocess_threshold.isChecked():
                    preprocess.append('threshold')
                if self.preprocess_grayscale.isChecked():
                    preprocess.append('grayscale')
                if self.preprocess_blur.isChecked():
                    preprocess.append('blur')
                    
                if preprocess:
                    params['preprocess'] = preprocess
                    
        elif self._current_strategy == "yolo":
            params['confidence_threshold'] = self.yolo_confidence_spin.value()
            params['model_name'] = self.model_combo.currentData()
        
        return params 