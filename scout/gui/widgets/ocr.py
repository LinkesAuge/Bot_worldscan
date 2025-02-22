from typing import Optional, Dict, Any, List
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSpinBox,
    QComboBox,
    QListWidget,
    QCheckBox,
    QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect

from ...capture import OCRProcessor
from ...core import CoordinateManager, CoordinateSpace

logger = logging.getLogger(__name__)

class OCRWidget(QWidget):
    """
    Widget for OCR controls and results display.
    
    This widget provides:
    - OCR activation controls
    - Region selection and management
    - Processing frequency adjustment
    - Result display
    - Performance metrics
    """
    
    # Signals
    region_added = pyqtSignal(str, QRect)  # region_name, rect
    region_removed = pyqtSignal(str)  # region_name
    text_event = pyqtSignal(str)  # text found
    
    def __init__(
        self,
        ocr_processor: OCRProcessor,
        coordinate_manager: CoordinateManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize OCR widget.
        
        Args:
            ocr_processor: OCR processor instance
            coordinate_manager: Coordinate manager instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.ocr_processor = ocr_processor
        self.coordinate_manager = coordinate_manager
        
        # Initialize state
        self.active = False
        self.update_interval = 1000
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_regions)
        self.update_timer.setInterval(self.update_interval)
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.debug("OCR widget initialized")
        
    def _setup_ui(self) -> None:
        """Setup user interface."""
        try:
            # Create main layout
            main_layout = QVBoxLayout(self)
            
            # Create control group
            control_group = QGroupBox("Controls")
            control_layout = QVBoxLayout(control_group)
            
            # Create activation controls
            activation_layout = QHBoxLayout()
            
            self.active_checkbox = QCheckBox("Active")
            activation_layout.addWidget(self.active_checkbox)
            
            self.interval_spinbox = QSpinBox()
            self.interval_spinbox.setRange(100, 10000)
            self.interval_spinbox.setValue(1000)
            self.interval_spinbox.setSuffix(" ms")
            activation_layout.addWidget(QLabel("Update Interval:"))
            activation_layout.addWidget(self.interval_spinbox)
            
            control_layout.addLayout(activation_layout)
            
            # Create language controls
            language_layout = QHBoxLayout()
            
            self.language_combo = QComboBox()
            self._update_languages()
            language_layout.addWidget(QLabel("Language:"))
            language_layout.addWidget(self.language_combo)
            
            control_layout.addLayout(language_layout)
            
            main_layout.addWidget(control_group)
            
            # Create region group
            region_group = QGroupBox("Regions")
            region_layout = QVBoxLayout(region_group)
            
            # Create region controls
            region_controls = QHBoxLayout()
            
            self.region_name = QLineEdit()
            self.region_name.setPlaceholderText("Region Name")
            region_controls.addWidget(self.region_name)
            
            self.add_region = QPushButton("Add Region")
            region_controls.addWidget(self.add_region)
            
            self.remove_button = QPushButton("Remove Region")
            region_controls.addWidget(self.remove_button)
            
            region_layout.addLayout(region_controls)
            
            # Create region list
            self.region_list = QListWidget()
            region_layout.addWidget(self.region_list)
            
            main_layout.addWidget(region_group)
            
            # Create results group
            results_group = QGroupBox("Results")
            results_layout = QVBoxLayout(results_group)
            
            # Create results list
            self.results_list = QListWidget()
            results_layout.addWidget(self.results_list)
            
            main_layout.addWidget(results_group)
            
            # Create metrics group
            metrics_group = QGroupBox("Metrics")
            metrics_layout = QVBoxLayout(metrics_group)
            
            self.metrics_label = QLabel()
            metrics_layout.addWidget(self.metrics_label)
            
            main_layout.addWidget(metrics_group)
            
            logger.debug("UI setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            raise
            
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        try:
            # Activation signals
            self.active_checkbox.stateChanged.connect(
                self._on_active_changed
            )
            self.interval_spinbox.valueChanged.connect(
                self._on_interval_changed
            )
            
            # Language signals
            self.language_combo.currentTextChanged.connect(
                lambda text: self._on_language_changed(text)
            )
            
            # Region signals
            self.add_region.clicked.connect(self._add_region)
            self.remove_button.clicked.connect(self._remove_region)
            
            # OCR processor signals
            self.ocr_processor.text_found.connect(
                self._on_text_found
            )
            self.ocr_processor.text_failed.connect(
                self._on_text_failed
            )
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _on_active_changed(self, state: int) -> None:
        """Handle activation state change."""
        try:
            self.active = bool(state)
            
            if self.active:
                self.update_timer.start(self.update_interval)
                logger.debug("OCR processing activated")
            else:
                self.update_timer.stop()
                logger.debug("OCR processing deactivated")
                
        except Exception as e:
            logger.error(f"Error handling activation: {e}")
            
    def _on_interval_changed(self, value: int) -> None:
        """Handle update interval change."""
        try:
            self.update_interval = value
            self.update_timer.setInterval(value)
            logger.debug(f"Update interval changed to {value}ms")
            
        except Exception as e:
            logger.error(f"Error handling interval change: {e}")
            
    def _on_language_changed(self, language: str) -> None:
        """Handle OCR language change."""
        try:
            self.ocr_processor.config = {"lang": language}
            logger.debug(f"OCR language changed to {language}")
            
        except Exception as e:
            logger.error(f"Error handling language change: {e}")
            
    def _add_region(self) -> None:
        """Add new OCR region."""
        try:
            # Get region name
            name = self.region_name.text().strip()
            if not name:
                return
                
            # Create region in client space
            rect = QRect(0, 0, 100, 30)  # Default size
            
            # Add to coordinate manager
            self.coordinate_manager.add_region(
                f"ocr_{name}",
                rect,
                CoordinateSpace.CLIENT
            )
            
            # Update region list
            self.region_list.addItem(name)
            
            # Clear input
            self.region_name.clear()
            
            # Emit signal
            self.region_added.emit(name, rect)
            
            logger.debug(f"Added OCR region: {name}")
            
        except Exception as e:
            logger.error(f"Error adding region: {e}")
            
    def _remove_region(self) -> None:
        """Remove selected OCR region."""
        try:
            # Get selected region
            item = self.region_list.currentItem()
            if not item:
                return
                
            name = item.text()
            
            # Remove from coordinate manager
            self.coordinate_manager.remove_region(f"ocr_{name}")
            
            # Remove from list
            self.region_list.takeItem(
                self.region_list.row(item)
            )
            
            # Emit signal
            self.region_removed.emit(name)
            
            logger.debug(f"Removed OCR region: {name}")
            
        except Exception as e:
            logger.error(f"Error removing region: {e}")
            
    def _update_regions(self) -> None:
        """Update OCR regions."""
        try:
            # Clear results
            self.results_list.clear()
            
            # Process each region
            for i in range(self.region_list.count()):
                name = self.region_list.item(i).text()
                region_name = f"ocr_{name}"
                
                # Process region
                text = self.ocr_processor.process_region(region_name)
                
                if text:
                    # Add to results
                    item_text = f"{name}: {text}"
                    self.results_list.addItem(item_text)
                    
            # Update metrics
            self._update_metrics()
            
        except Exception as e:
            logger.error(f"Error updating regions: {e}")
            
    def _update_languages(self) -> None:
        """Update the language combo box with supported languages."""
        try:
            self.language_combo.clear()
            self.language_combo.addItems(
                self.ocr_processor.get_supported_languages()
            )
            logger.debug("Updated language list")
            
        except Exception as e:
            logger.error(f"Error updating languages: {e}")
            
    def _update_metrics(self, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Update performance metrics."""
        try:
            # Use provided metrics or get from OCR processor
            if metrics is None:
                metrics = self.ocr_processor.get_debug_info()["metrics"]
            
            # Format metrics text
            metrics_text = (
                f"Total Extractions: {metrics['total_extractions']}\n"
                f"Failed Extractions: {metrics['failed_extractions']}\n"
                f"Last Extraction Time: {metrics.get('last_extraction_time', 0.0)}s"
            )
            
            self.metrics_label.setText(metrics_text)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _on_text_found(self, region: str, text: str) -> None:
        """Handle text found event."""
        try:
            logger.debug(f"Text found in {region}: {text}")
            self._handle_text_event(region, text)
            
        except Exception as e:
            logger.error(f"Error handling text found: {e}")
            
    def _on_text_failed(self, region: str, error: str) -> None:
        """Handle text extraction failure."""
        try:
            logger.error(f"Text extraction failed for {region}: {error}")
            
        except Exception as e:
            logger.error(f"Error handling text failure: {e}")
            
    def _handle_text_event(self, region: str, text: str) -> None:
        """Handle text event from OCR processor."""
        try:
            # Add to results list
            self.results_list.addItem(f"{region}: {text}")
            
            # Emit text event
            self.text_event.emit(text)
            
            logger.debug(f"Text event handled: {region} - {text}")
            
        except Exception as e:
            logger.error(f"Error handling text event: {e}") 