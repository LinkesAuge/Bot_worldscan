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
    QFileDialog,
    QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
import sys
from PyQt6.QtCore import QSettings

from ...capture import PatternMatcher
from ...core import CoordinateManager
from ...config import ConfigManager

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
    template_removed = pyqtSignal(str)
    
    def __init__(
        self,
        pattern_matcher: PatternMatcher,
        coordinate_manager: CoordinateManager,
        config: ConfigManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize pattern matching widget.
        
        Args:
            pattern_matcher: Pattern matcher instance
            coordinate_manager: Coordinate manager instance
            config: Configuration manager instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.pattern_matcher = pattern_matcher
        self.coordinate_manager = coordinate_manager
        self.config = config
        
        # Initialize state
        self.active = False
        self.update_interval = 1000  # ms
        self.is_updating = False  # Flag to prevent overlapping updates
        
        # Setup UI
        self._setup_ui()
        
        # Load saved settings
        self._load_settings()
        
        # Connect signals
        self._connect_signals()
        
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
            self.confidence_spinbox.setSingleStep(0.05)
            self.confidence_spinbox.setDecimals(2)
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
            # Connect controls
            self.active_checkbox.stateChanged.connect(self._on_active_changed)
            self.interval_spinbox.valueChanged.connect(self._on_interval_changed)
            self.confidence_spinbox.valueChanged.connect(self._on_confidence_changed)
            
            # Connect buttons
            self.add_button.clicked.connect(self._add_template)
            self.remove_button.clicked.connect(self._remove_template)
            self.reload_button.clicked.connect(self._reload_templates)
            
            # Connect template list
            self.template_list.itemChanged.connect(self._on_template_state_changed)
            
            # Connect pattern matcher signals
            self.pattern_matcher.match_found.connect(self._on_match_found)
            self.pattern_matcher.match_failed.connect(self._on_match_failed)
            
            logger.debug("Pattern matching widget signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _load_settings(self) -> None:
        """Load saved settings."""
        try:
            # Get pattern config
            pattern_config = self.config.get_pattern_config()
            
            # Load confidence threshold
            self.confidence_spinbox.setValue(pattern_config.confidence_threshold)
            self.pattern_matcher.confidence_threshold = pattern_config.confidence_threshold
            
            # Load update interval
            self.interval_spinbox.setValue(self.update_interval)
            
            # Load active state
            self.active_checkbox.setChecked(False)  # Always start inactive
            
            # Ensure template directory exists
            self.pattern_matcher.template_dir.mkdir(parents=True, exist_ok=True)
            
            # Load templates
            self.pattern_matcher.reload_templates()
            
            # Update template list
            self.template_list.clear()
            for name in self.pattern_matcher.templates:
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.template_list.addItem(item)
            
            logger.debug(
                f"Settings loaded: confidence={pattern_config.confidence_threshold}, "
                f"interval={self.update_interval}"
            )
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            
    def _save_settings(self) -> None:
        """Save current settings."""
        try:
            # Update pattern config
            self.config.update_section("Pattern", {
                "confidence_threshold": self.confidence_spinbox.value(),
                "template_dir": str(self.pattern_matcher.template_dir),
                "save_matches": "true"
            })
            
            logger.debug(
                f"Settings saved: confidence={self.confidence_spinbox.value()}, "
                f"interval={self.interval_spinbox.value()}"
            )
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            
    def _on_active_changed(self, state: int) -> None:
        """Handle activation state change."""
        try:
            self.active = bool(state)
            
            if self.active:
                # Create and start update timer
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self._check_update)
                self.update_timer.start(self.update_interval)
                logger.debug("Pattern matching activated")
                
            else:
                # Stop update timer
                if hasattr(self, "update_timer"):
                    self.update_timer.stop()
                logger.debug("Pattern matching deactivated")
                
            # Save settings
            self._save_settings()
            
        except Exception as e:
            logger.error(f"Error handling activation: {e}")
            
    def _on_interval_changed(self, value: int) -> None:
        """Handle update interval change."""
        try:
            self.update_interval = value
            
            # Update timer if active
            if self.active and hasattr(self, "update_timer"):
                self.update_timer.setInterval(value)
                
            # Save settings
            self._save_settings()
            
            logger.debug(f"Update interval changed to {value}ms")
            
        except Exception as e:
            logger.error(f"Error handling interval change: {e}")
            
    def _on_confidence_changed(self, value: float) -> None:
        """Handle confidence threshold change."""
        try:
            # Update pattern matcher
            self.pattern_matcher.confidence_threshold = value
            
            # Save settings
            self._save_settings()
            
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
                # Create template directory if it doesn't exist
                self.pattern_matcher.template_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy files to template directory
                for file_path in files:
                    path = Path(file_path)
                    dest = self.pattern_matcher.template_dir / path.name
                    
                    if dest.exists():
                        continue
                        
                    dest.write_bytes(path.read_bytes())
                    
                # Reload templates
                self._reload_templates()
                
                # Save settings to persist template selection
                self._save_settings()
                
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
            
            # Save settings to update template list
            self._save_settings()
            
            # Emit signal
            self.template_removed.emit(template_name)
            
            logger.debug(f"Removed template: {template_name}")
            
        except Exception as e:
            logger.error(f"Error removing template: {e}")
            
    def _reload_templates(self) -> None:
        """Reload templates and restore selection."""
        try:
            # Clear current list
            self.template_list.clear()
            
            # Get template info
            templates = self.pattern_matcher.get_template_info()
            
            # Get previously selected templates
            selected = self.config.get_pattern_config().active_templates
            selected = [t.strip() for t in selected if t.strip()]
            
            # Add templates to list
            for name in sorted(templates.keys()):
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if name in selected else Qt.CheckState.Unchecked
                )
                self.template_list.addItem(item)
                
            logger.debug(f"Reloaded {len(templates)} templates, {len(selected)} selected")
            
        except Exception as e:
            logger.error(f"Error reloading templates: {e}")

    def _save_template_selection(self) -> None:
        """Save currently selected templates to config."""
        try:
            selected = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected.append(item.text())
            
            # Save to config
            self.config.update_section("Pattern", {
                "active_templates": selected
            })
            self.config.sync()
            logger.debug(f"Saved {len(selected)} selected templates")
            
        except Exception as e:
            logger.error(f"Error saving template selection: {e}")

    def _on_template_state_changed(self, item: QListWidgetItem) -> None:
        """Handle template selection change."""
        try:
            # Save selection
            self._save_template_selection()
            
            # Update matches
            self._update_matches()
            
        except Exception as e:
            logger.error(f"Error handling template state change: {e}")

    def _check_update(self) -> None:
        """Check if update should proceed."""
        try:
            if not self.is_updating:
                self._update_matches()
        except Exception as e:
            logger.error(f"Error checking update: {e}")

    def _update_matches(self) -> None:
        """Update pattern matches."""
        try:
            self.is_updating = True
            
            # Get selected templates
            selected_templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected_templates.append(item.text())
            
            if not selected_templates:
                logger.warning("No templates selected for matching")
                self.is_updating = False
                return
                
            # Find matches
            matches = self.pattern_matcher.find_matches(
                template_names=selected_templates,
                save_debug=True  # Always save debug image
            )
            
            # Clear previous results
            self.results_list.clear()
            
            # Add new results
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
            
        finally:
            self.is_updating = False

    def _update_metrics(self) -> None:
        """Update performance metrics."""
        try:
            # Get template info
            template_info = self.pattern_matcher.get_template_info()
            
            # Get selected templates
            selected_templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    selected_templates.append(item.text())
            
            # Format metrics text
            metrics_text = (
                f"Total Templates: {len(template_info)}\n"
                f"Selected Templates: {len(selected_templates)}\n"
                f"Active: {self.active}\n"
                f"Interval: {self.update_interval}ms\n"
                f"Confidence: {self.pattern_matcher.confidence_threshold:.2f}\n"
                f"Selected: {', '.join(selected_templates)}"
            )
            
            self.metrics_label.setText(metrics_text)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _on_match_found(
        self,
        template: str,
        confidence: float,
        position: QPoint
    ) -> None:
        """Handle match found event."""
        try:
            msg = f"Match found: {template} (conf={confidence:.2f}, pos={position})"
            logger.info(msg)
            
            # Add to results if not already present
            found = False
            for i in range(self.results_list.count()):
                if template in self.results_list.item(i).text():
                    found = True
                    break
                    
            if not found:
                self.results_list.addItem(msg)
                
        except Exception as e:
            logger.error(f"Error handling match found: {e}")

    def _on_match_failed(self, template: str, error: str) -> None:
        """Handle match failed event."""
        try:
            msg = f"Match failed for {template}: {error}"
            logger.warning(msg)
            
        except Exception as e:
            logger.error(f"Error handling match failed: {e}") 