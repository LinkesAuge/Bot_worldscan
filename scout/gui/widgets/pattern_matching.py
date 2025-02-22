from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QListWidget,
    QCheckBox,
    QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from ...capture import PatternMatcher
from ...core import CoordinateManager

logger = logging.getLogger(__name__)

class PatternMatchingWidget(QWidget):
    """
    Widget for pattern matching controls and visualization.
    
    This widget provides:
    - Pattern matching activation controls
    - Confidence threshold adjustment
    - Template management
    - Match result display
    - Performance metrics
    """
    
    # Signals
    template_added = pyqtSignal(str)  # template_name
    template_removed = pyqtSignal(str)  # template_name
    
    def __init__(
        self,
        pattern_matcher: PatternMatcher,
        coordinate_manager: CoordinateManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize pattern matching widget.
        
        Args:
            pattern_matcher: Pattern matcher instance
            coordinate_manager: Coordinate manager instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.pattern_matcher = pattern_matcher
        self.coordinate_manager = coordinate_manager
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Initialize state
        self.active = False
        self.update_interval = 1000
        
        logger.debug("Pattern matching widget initialized")
        
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
            
            # Create confidence controls
            confidence_layout = QHBoxLayout()
            
            self.confidence_spinbox = QDoubleSpinBox()
            self.confidence_spinbox.setRange(0.1, 1.0)
            self.confidence_spinbox.setValue(0.8)
            self.confidence_spinbox.setSingleStep(0.1)
            confidence_layout.addWidget(QLabel("Confidence Threshold:"))
            confidence_layout.addWidget(self.confidence_spinbox)
            
            control_layout.addLayout(confidence_layout)
            
            main_layout.addWidget(control_group)
            
            # Create template group
            template_group = QGroupBox("Templates")
            template_layout = QVBoxLayout(template_group)
            
            # Create template list
            self.template_list = QListWidget()
            template_layout.addWidget(self.template_list)
            
            # Create template buttons
            button_layout = QHBoxLayout()
            
            self.add_button = QPushButton("Add Template")
            button_layout.addWidget(self.add_button)
            
            self.remove_button = QPushButton("Remove Template")
            button_layout.addWidget(self.remove_button)
            
            self.reload_button = QPushButton("Reload Templates")
            button_layout.addWidget(self.reload_button)
            
            template_layout.addLayout(button_layout)
            
            main_layout.addWidget(template_group)
            
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
            
            # Confidence signals
            self.confidence_spinbox.valueChanged.connect(
                self._on_confidence_changed
            )
            
            # Template signals
            self.add_button.clicked.connect(self._add_template)
            self.remove_button.clicked.connect(self._remove_template)
            self.reload_button.clicked.connect(self._reload_templates)
            
            # Pattern matcher signals
            self.pattern_matcher.match_found.connect(
                self._on_match_found
            )
            self.pattern_matcher.match_failed.connect(
                self._on_match_failed
            )
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _on_active_changed(self, state: int) -> None:
        """Handle activation state change."""
        try:
            self.active = bool(state)
            
            if self.active:
                # Create and start update timer
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self._update_matches)
                self.update_timer.start(self.update_interval)
                logger.debug("Pattern matching activated")
                
            else:
                # Stop update timer
                if hasattr(self, "update_timer"):
                    self.update_timer.stop()
                logger.debug("Pattern matching deactivated")
                
        except Exception as e:
            logger.error(f"Error handling activation: {e}")
            
    def _on_interval_changed(self, value: int) -> None:
        """Handle update interval change."""
        try:
            self.update_interval = value
            
            # Update timer if active
            if self.active and hasattr(self, "update_timer"):
                self.update_timer.setInterval(value)
                
            logger.debug(f"Update interval changed to {value}ms")
            
        except Exception as e:
            logger.error(f"Error handling interval change: {e}")
            
    def _on_confidence_changed(self, value: float) -> None:
        """Handle confidence threshold change."""
        try:
            self.pattern_matcher.confidence_threshold = value
            logger.debug(f"Confidence threshold changed to {value}")
            
        except Exception as e:
            logger.error(f"Error handling confidence change: {e}")
            
    def _add_template(self) -> None:
        """Add new template."""
        try:
            # Open file dialog
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Template Images",
                str(self.pattern_matcher.template_dir),
                "Images (*.png)"
            )
            
            if files:
                # Copy files to template directory
                for file_path in files:
                    path = Path(file_path)
                    dest = self.pattern_matcher.template_dir / path.name
                    
                    if dest.exists():
                        continue
                        
                    dest.write_bytes(path.read_bytes())
                    
                # Reload templates
                self._reload_templates()
                
        except Exception as e:
            logger.error(f"Error adding template: {e}")
            
    def _remove_template(self) -> None:
        """Remove selected template."""
        try:
            # Get selected template
            item = self.template_list.currentItem()
            if not item:
                return
                
            template_name = item.text()
            
            # Remove template file
            template_path = (
                self.pattern_matcher.template_dir /
                f"{template_name}.png"
            )
            if template_path.exists():
                template_path.unlink()
                
            # Reload templates
            self._reload_templates()
            
            # Emit signal
            self.template_removed.emit(template_name)
            
            logger.debug(f"Removed template: {template_name}")
            
        except Exception as e:
            logger.error(f"Error removing template: {e}")
            
    def _reload_templates(self) -> None:
        """Reload template list."""
        try:
            # Clear template list
            self.template_list.clear()
            
            # Reload templates
            self.pattern_matcher.reload_templates()
            
            # Update template list
            for name in self.pattern_matcher.templates:
                self.template_list.addItem(name)
                
            logger.debug("Templates reloaded")
            
        except Exception as e:
            logger.error(f"Error reloading templates: {e}")
            
    def _update_matches(self) -> None:
        """Update pattern matches."""
        try:
            # Clear results
            self.results_list.clear()
            
            # Get matches
            matches = self.pattern_matcher.find_matches()
            
            # Update results list
            for match in matches:
                item_text = (
                    f"{match.template_name}: "
                    f"conf={match.confidence:.2f}, "
                    f"pos=({match.position.x()}, {match.position.y()})"
                )
                self.results_list.addItem(item_text)
                
            # Update metrics
            self._update_metrics()
            
        except Exception as e:
            logger.error(f"Error updating matches: {e}")
            
    def _update_metrics(self) -> None:
        """Update performance metrics."""
        try:
            # Get template info
            template_info = self.pattern_matcher.get_template_info()
            
            # Format metrics text
            metrics_text = (
                f"Templates: {len(template_info)}\n"
                f"Active: {self.active}\n"
                f"Interval: {self.update_interval}ms\n"
                f"Confidence: {self.pattern_matcher.confidence_threshold:.2f}"
            )
            
            self.metrics_label.setText(metrics_text)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _on_match_found(
        self,
        template: str,
        confidence: float,
        position: Any
    ) -> None:
        """Handle match found event."""
        try:
            logger.debug(
                f"Match found: {template} "
                f"(conf={confidence:.2f}, pos={position})"
            )
            
        except Exception as e:
            logger.error(f"Error handling match: {e}")
            
    def _on_match_failed(self, template: str, error: str) -> None:
        """Handle match failed event."""
        try:
            logger.error(f"Match failed for {template}: {error}")
            
        except Exception as e:
            logger.error(f"Error handling match failure: {e}") 