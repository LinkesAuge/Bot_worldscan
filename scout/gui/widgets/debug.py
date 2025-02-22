from typing import Optional, Dict, Any
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSpinBox,
    QCheckBox,
    QTextEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from ...visualization import DebugVisualizer

logger = logging.getLogger(__name__)

class DebugWidget(QWidget):
    """
    Widget for debug visualization and logging.
    
    This widget provides:
    - Debug mode controls
    - Visualization options
    - Performance monitoring
    - Log viewing
    - Screenshot management
    """
    
    # Signals
    text_received = pyqtSignal(str)  # Emits text when received
    
    def __init__(
        self,
        debug_visualizer: DebugVisualizer,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize debug widget.
        
        Args:
            debug_visualizer: Debug visualizer instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.debug_visualizer = debug_visualizer
        
        # Initialize state
        self.is_active = False
        self.text_history = []
        self.max_history_size = 100
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.debug("Debug widget initialized")
        
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
            
            self.active_checkbox = QCheckBox("Debug Mode")
            activation_layout.addWidget(self.active_checkbox)
            
            self.interval_spinbox = QSpinBox()
            self.interval_spinbox.setRange(100, 10000)
            self.interval_spinbox.setValue(1000)
            self.interval_spinbox.setSuffix(" ms")
            activation_layout.addWidget(QLabel("Update Interval:"))
            activation_layout.addWidget(self.interval_spinbox)
            
            control_layout.addLayout(activation_layout)
            
            # Create visualization controls
            viz_layout = QHBoxLayout()
            
            self.show_coords = QCheckBox("Show Coordinates")
            self.show_coords.setChecked(True)
            viz_layout.addWidget(self.show_coords)
            
            self.show_regions = QCheckBox("Show Regions")
            self.show_regions.setChecked(True)
            viz_layout.addWidget(self.show_regions)
            
            self.show_matches = QCheckBox("Show Matches")
            self.show_matches.setChecked(True)
            viz_layout.addWidget(self.show_matches)
            
            control_layout.addLayout(viz_layout)
            
            main_layout.addWidget(control_group)
            
            # Create preview group
            preview_group = QGroupBox("Preview")
            preview_layout = QVBoxLayout(preview_group)
            
            # Create preview label
            self.preview_label = QLabel()
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Create scroll area for preview
            scroll_area = QScrollArea()
            scroll_area.setWidget(self.preview_label)
            scroll_area.setWidgetResizable(True)
            preview_layout.addWidget(scroll_area)
            
            main_layout.addWidget(preview_group)
            
            # Create text display group
            text_group = QGroupBox("Text History")
            text_layout = QVBoxLayout(text_group)
            
            # Create text display
            self.text_display = QTextEdit()
            self.text_display.setReadOnly(True)
            text_layout.addWidget(self.text_display)
            
            main_layout.addWidget(text_group)
            
            # Create metrics group
            metrics_group = QGroupBox("Metrics")
            metrics_layout = QVBoxLayout(metrics_group)
            
            # Create metrics text
            self.metrics_text = QTextEdit()
            self.metrics_text.setReadOnly(True)
            metrics_layout.addWidget(self.metrics_text)
            
            main_layout.addWidget(metrics_group)
            
            # Create screenshot controls
            screenshot_layout = QHBoxLayout()
            
            self.save_screenshot = QPushButton("Save Screenshot")
            screenshot_layout.addWidget(self.save_screenshot)
            
            self.clear_screenshots = QPushButton("Clear Screenshots")
            screenshot_layout.addWidget(self.clear_screenshots)
            
            main_layout.addLayout(screenshot_layout)
            
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
            
            # Visualization signals
            self.show_coords.stateChanged.connect(
                self._update_preview
            )
            self.show_regions.stateChanged.connect(
                self._update_preview
            )
            self.show_matches.stateChanged.connect(
                self._update_preview
            )
            
            # Screenshot signals
            self.save_screenshot.clicked.connect(
                self._save_screenshot
            )
            self.clear_screenshots.clicked.connect(
                self._clear_screenshots
            )
            
            # Debug visualizer signals
            self.debug_visualizer.preview_updated.connect(
                self._on_preview_updated
            )
            self.debug_visualizer.metrics_updated.connect(
                self._on_metrics_updated
            )
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _on_active_changed(self, state: int) -> None:
        """Handle debug mode activation."""
        try:
            active = bool(state)
            
            if active:
                # Start debug visualizer
                self.debug_visualizer.start()
                logger.debug("Debug visualization started")
                
            else:
                # Stop debug visualizer
                self.debug_visualizer.stop()
                logger.debug("Debug visualization stopped")
                
        except Exception as e:
            logger.error(f"Error handling activation: {e}")
            
    def _on_interval_changed(self, value: int) -> None:
        """Handle update interval change."""
        try:
            # Update debug visualizer
            self.debug_visualizer.update_timer.setInterval(value)
            logger.debug(f"Update interval changed to {value}ms")
            
        except Exception as e:
            logger.error(f"Error handling interval change: {e}")
            
    def _update_preview(self) -> None:
        """Update preview display."""
        try:
            # Get current preview
            preview = self.preview_label.pixmap()
            if not preview:
                return
                
            # Convert to image for drawing
            image = preview.toImage()
            
            # Apply visualization options
            if self.show_coords.isChecked():
                # Draw coordinate system
                pass
                
            if self.show_regions.isChecked():
                # Draw regions
                pass
                
            if self.show_matches.isChecked():
                # Draw pattern matches
                pass
                
            # Update preview
            self.preview_label.setPixmap(QPixmap.fromImage(image))
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            
    def _on_preview_updated(self, image: QImage) -> None:
        """Handle preview image update."""
        try:
            # Scale image to fit
            scaled = image.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Update preview
            self.preview_label.setPixmap(QPixmap.fromImage(scaled))
            
        except Exception as e:
            logger.error(f"Error handling preview update: {e}")
            
    def _on_metrics_updated(self, metrics: Dict[str, Any]) -> None:
        """Handle metrics update."""
        try:
            # Format metrics text
            lines = ["Debug Metrics:", ""]
            
            # Window metrics
            if "window" in metrics:
                lines.extend([
                    "WINDOW:",
                    f"  window_found: {metrics['window']['window_found']}",
                    f"  window_handle: {metrics['window']['window_handle']}",
                    ""
                ])
            
            # Capture metrics
            if "capture" in metrics:
                lines.extend([
                    "CAPTURE:",
                    f"  total_captures: {metrics['capture']['total_captures']}",
                    f"  failed_captures: {metrics['capture']['failed_captures']}",
                    ""
                ])
            
            # Pattern metrics
            if "pattern" in metrics:
                lines.extend([
                    "PATTERN:",
                    f"  templates: {metrics['pattern']['templates']}",
                    ""
                ])
            
            # OCR metrics
            if "ocr" in metrics and "metrics" in metrics["ocr"]:
                ocr_metrics = metrics["ocr"]["metrics"]
                lines.extend([
                    "OCR:",
                    f"  total_extractions: {ocr_metrics['total_extractions']}",
                    f"  failed_extractions: {ocr_metrics['failed_extractions']}",
                    ""
                ])
            
            # Update text
            self.metrics_text.setText("\n".join(lines))
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _save_screenshot(self) -> None:
        """Save current preview as screenshot."""
        try:
            # Get current preview
            preview = self.preview_label.pixmap()
            if not preview:
                return
                
            # Save screenshot
            preview.save("debug_screenshots/manual_capture.png")
            logger.debug("Screenshot saved")
            
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            
    def _clear_screenshots(self) -> None:
        """Clear debug screenshots."""
        try:
            # Clear screenshot directory
            import os
            import glob
            
            files = glob.glob("debug_screenshots/*.png")
            for f in files:
                os.remove(f)
                
            logger.debug("Screenshots cleared")
            
        except Exception as e:
            logger.error(f"Error clearing screenshots: {e}")
            
    def handle_text_event(self, region: str, text: str) -> None:
        """Handle text event from OCR or pattern matching.
        
        Args:
            region: Name of the region where text was found
            text: The text that was found
        """
        try:
            # Add to history
            self.text_history.append(text)
            
            # Trim history if needed
            if len(self.text_history) > self.max_history_size:
                self.text_history = self.text_history[-self.max_history_size:]
            
            # Update display
            self._update_text_display()
            
            # Emit signal
            self.text_received.emit(text)
            
        except Exception as e:
            logger.error(f"Error handling text event: {e}")
    
    def clear_history(self) -> None:
        """Clear text history."""
        try:
            self.text_history.clear()
            self._update_text_display()
            
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
    
    def _update_text_display(self) -> None:
        """Update text display with current history."""
        try:
            text = "\n".join(self.text_history)
            self.text_display.setText(text)
            
        except Exception as e:
            logger.error(f"Error updating text display: {e}")
    
    def activate(self) -> None:
        """Activate debug visualization."""
        try:
            self.is_active = True
            self.timer = QTimer()
            self.timer.timeout.connect(self._update_preview)
            self.timer.start(1000)
            
        except Exception as e:
            logger.error(f"Error activating debug widget: {e}")
    
    def deactivate(self) -> None:
        """Deactivate debug visualization."""
        try:
            self.is_active = False
            if hasattr(self, "timer"):
                self.timer.stop()
            
        except Exception as e:
            logger.error(f"Error deactivating debug widget: {e}") 