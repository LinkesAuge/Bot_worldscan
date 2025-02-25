"""
Detection Tab

This module provides a tab interface for configuring and running detection operations.
It allows users to manage templates, configure detection settings, and view results.
"""

import logging
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QFrame, QSplitter, QComboBox,
    QToolBar, QScrollArea, QLineEdit, QSpinBox, QCheckBox,
    QMessageBox, QInputDialog, QMenu, QFileDialog, QGridLayout,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal

from pathlib import Path
from datetime import datetime

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.ui.widgets.template_list_widget import TemplateListWidget
from scout.ui.widgets.detection_result_widget import DetectionResultWidget
from scout.ui.widgets.detection_history_widget import DetectionHistoryWidget
from scout.ui.widgets.detection_heatmap_widget import DetectionHeatmapWidget
from scout.ui.utils.language_manager import tr

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
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs for different detection views
        self.view_tabs = QTabWidget()
        main_layout.addWidget(self.view_tabs)
        
        # Create real-time detection tab
        realtime_tab = QWidget()
        self.view_tabs.addTab(realtime_tab, tr("Real-time Detection"))
        
        # Create historical view tab
        history_tab = QWidget()
        self.view_tabs.addTab(history_tab, tr("Detection History"))
        
        # Create heatmap tab
        heatmap_tab = QWidget()
        self.view_tabs.addTab(heatmap_tab, tr("Detection Heatmap"))
        
        # Setup real-time detection tab
        self._setup_realtime_tab(realtime_tab)
        
        # Setup history tab
        self._setup_history_tab(history_tab)
        
        # Setup heatmap tab
        self._setup_heatmap_tab(heatmap_tab)
    
    def _setup_realtime_tab(self, tab_widget: QWidget) -> None:
        """
        Set up the real-time detection tab.
        
        Args:
            tab_widget: Tab widget to set up
        """
        # Create layout for real-time tab
        realtime_layout = QVBoxLayout(tab_widget)
        
        # Create toolbar
        toolbar = QToolBar()
        
        # Detection strategy selector
        toolbar.addWidget(QLabel(tr("Detection Strategy:")))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Template Matching", "OCR", "YOLO"])
        toolbar.addWidget(self.strategy_combo)
        
        # Add spacer
        toolbar.addSeparator()
        
        # Run detection button
        self.run_btn = QPushButton(tr("Run Detection"))
        self.run_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        toolbar.addWidget(self.run_btn)
        
        # Add toolbar to layout
        realtime_layout.addWidget(toolbar)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        realtime_layout.addWidget(main_splitter)
        
        # Left panel - configuration
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        
        # Create template list
        self.template_group = QGroupBox(tr("Templates"))
        template_layout = QVBoxLayout(self.template_group)
        
        self.template_list = TemplateListWidget(self._template_dir)
        template_layout.addWidget(self.template_list)
        
        config_layout.addWidget(self.template_group)
        
        # Create detection parameters group
        params_group = QGroupBox(tr("Detection Parameters"))
        params_layout = QGridLayout(params_group)
        
        # Confidence threshold
        params_layout.addWidget(QLabel(tr("Confidence Threshold:")), 0, 0)
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(1, 100)
        self.confidence_spin.setValue(70)
        self.confidence_spin.setSuffix("%")
        params_layout.addWidget(self.confidence_spin, 0, 1)
        
        # Max results
        params_layout.addWidget(QLabel(tr("Max Results:")), 1, 0)
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(1, 100)
        self.max_results_spin.setValue(10)
        params_layout.addWidget(self.max_results_spin, 1, 1)
        
        # Use region checkbox
        params_layout.addWidget(QLabel(tr("Use Detection Region:")), 2, 0)
        self.use_region_check = QCheckBox()
        params_layout.addWidget(self.use_region_check, 2, 1)
        
        # Region parameters
        params_layout.addWidget(QLabel(tr("X:")), 3, 0)
        self.region_x_spin = QSpinBox()
        self.region_x_spin.setRange(0, 3000)
        self.region_x_spin.setEnabled(False)
        params_layout.addWidget(self.region_x_spin, 3, 1)
        
        params_layout.addWidget(QLabel(tr("Y:")), 4, 0)
        self.region_y_spin = QSpinBox()
        self.region_y_spin.setRange(0, 3000)
        self.region_y_spin.setEnabled(False)
        params_layout.addWidget(self.region_y_spin, 4, 1)
        
        params_layout.addWidget(QLabel(tr("Width:")), 5, 0)
        self.region_width_spin = QSpinBox()
        self.region_width_spin.setRange(10, 3000)
        self.region_width_spin.setValue(500)
        self.region_width_spin.setEnabled(False)
        params_layout.addWidget(self.region_width_spin, 5, 1)
        
        params_layout.addWidget(QLabel(tr("Height:")), 6, 0)
        self.region_height_spin = QSpinBox()
        self.region_height_spin.setRange(10, 3000)
        self.region_height_spin.setValue(500)
        self.region_height_spin.setEnabled(False)
        params_layout.addWidget(self.region_height_spin, 6, 1)
        
        config_layout.addWidget(params_group)
        
        # Add spacer
        config_layout.addStretch()
        
        # Right panel - results
        self.result_widget = DetectionResultWidget(self.window_service)
        
        # Add panels to splitter
        main_splitter.addWidget(config_panel)
        main_splitter.addWidget(self.result_widget)
        
        # Set initial splitter sizes (30% left, 70% right)
        main_splitter.setSizes([300, 700])
    
    def _setup_history_tab(self, tab_widget: QWidget) -> None:
        """
        Set up the detection history tab.
        
        Args:
            tab_widget: Tab widget to set up
        """
        # Create layout
        layout = QVBoxLayout(tab_widget)
        
        # Create detection history widget
        self._history_widget = DetectionHistoryWidget(
            self.window_service, 
            self.detection_service
        )
        
        # Add to layout
        layout.addWidget(self._history_widget)
        
        # Load sample data for testing
        # TODO: Remove or make configurable in production
        self._history_widget.load_sample_data()
    
    def _setup_heatmap_tab(self, tab_widget: QWidget) -> None:
        """
        Set up the detection heatmap tab.
        
        Args:
            tab_widget: Tab widget to set up
        """
        # Create layout
        layout = QVBoxLayout(tab_widget)
        
        # Create detection heatmap widget
        self._heatmap_widget = DetectionHeatmapWidget(
            self.window_service, 
            self.detection_service
        )
        
        # Add to layout
        layout.addWidget(self._heatmap_widget)
        
        # Connect signals
        # When a detection occurs, add it to both the history and heatmap widgets
        # This is handled in the _on_detection_result method
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Strategy combo
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        
        # Run button
        self.run_btn.clicked.connect(self.run_detection)
        
        # Region checkbox
        self.use_region_check.toggled.connect(self._on_use_region_toggled)
        
        # View tabs
        self.view_tabs.currentChanged.connect(self._on_view_tab_changed)
    
    def _on_strategy_changed(self, index: int) -> None:
        """
        Handle strategy change.
        
        Args:
            index: Selected index
        """
        strategy_map = {
            0: "template",
            1: "ocr",
            2: "yolo"
        }
        
        self._current_strategy = strategy_map.get(index, "template")
        
        # Update UI based on selected strategy
        self.template_group.setVisible(self._current_strategy == "template")
    
    def _on_use_region_toggled(self, checked: bool) -> None:
        """
        Handle use region checkbox toggle.
        
        Args:
            checked: Whether the checkbox is checked
        """
        # Enable/disable region parameters
        self.region_x_spin.setEnabled(checked)
        self.region_y_spin.setEnabled(checked)
        self.region_width_spin.setEnabled(checked)
        self.region_height_spin.setEnabled(checked)
    
    def _on_view_tab_changed(self, index: int) -> None:
        """
        Handle view tab changed.
        
        Args:
            index: Selected tab index
        """
        # If switching to history tab, make sure it's updated
        if index == 1:  # History tab
            logger.debug("Switched to history tab")
            # Any updates needed for the history tab
    
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
                template_names = self.template_list.get_selected_templates()
                if not template_names:
                    QMessageBox.warning(self, "Error", "No templates selected")
                    return
                
                # Add template names to params
                params["template_names"] = template_names
                
                # Run template detection
                results = self.detection_service.run_template_detection(
                    template_names=template_names,
                    confidence_threshold=params.get("confidence_threshold", 0.7),
                    max_results=params.get("max_results", 10),
                    region=params.get("region")
                )
                
            elif self._current_strategy == "ocr":
                # Run OCR detection
                results = self.detection_service.run_ocr_detection(
                    pattern=params.get("pattern", ""),
                    confidence_threshold=params.get("confidence_threshold", 0.6),
                    region=params.get("region")
                )
                
            elif self._current_strategy == "yolo":
                # Run YOLO detection
                results = self.detection_service.run_yolo_detection(
                    classes=params.get("classes"),
                    confidence_threshold=params.get("confidence_threshold", 0.5),
                    region=params.get("region")
                )
            
            # Display results
            self.result_widget.display_results(results, self._current_strategy)
            
            # Store results
            self._detection_results = results
            
            # Add to history
            self._history_widget.add_detection_result(results, self._current_strategy)
            
            # Emit signal with strategy and results
            self.detection_requested.emit(self._current_strategy, params)
            
        except Exception as e:
            logger.error(f"Error running detection: {e}")
            QMessageBox.critical(self, "Error", f"Detection failed: {str(e)}")
    
    def _get_detection_params(self) -> Dict[str, Any]:
        """
        Get detection parameters based on current UI settings.
        
        Returns:
            Dictionary of detection parameters
        """
        # Common parameters
        params = {
            "confidence_threshold": self.confidence_spin.value() / 100.0,
            "max_results": self.max_results_spin.value()
        }
        
        # Add region if enabled
        if self.use_region_check.isChecked():
            params["region"] = {
                "x": self.region_x_spin.value(),
                "y": self.region_y_spin.value(),
                "width": self.region_width_spin.value(),
                "height": self.region_height_spin.value()
            }
        
        return params

    def _on_detection_result(self, strategy: str, results: List[Dict]) -> None:
        """
        Handle detection results.
        
        Args:
            strategy: Detection strategy used
            results: List of detection results
        """
        # Get current screenshot
        screenshot = self.window_service.capture_screenshot()
        
        # Add to history widget
        timestamp = datetime.now()
        self._history_widget.add_to_history(timestamp, results, strategy, screenshot)
        
        # Add to heatmap widget
        self._heatmap_widget.add_detection_event(timestamp, results, strategy, screenshot)
        
        # Update tab title with result count
        tab_text = f"Detection History ({len(results)} new)"
        self.view_tabs.setTabText(1, tab_text)
        
        # Log the results
        logger.info(f"Detection completed: {strategy} with {len(results)} results") 