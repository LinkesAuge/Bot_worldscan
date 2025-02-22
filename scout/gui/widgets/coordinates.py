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
    QLineEdit
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal

from ...core import WindowTracker, CoordinateManager, CoordinateSpace

logger = logging.getLogger(__name__)

class CoordinateWidget(QWidget):
    """
    Widget for coordinate system management.
    
    This widget provides:
    - Coordinate space selection
    - Region management
    - Coordinate transformation testing
    - Live coordinate display
    - DPI scaling configuration
    """
    
    # Signals
    coordinate_changed = pyqtSignal(QPoint, str)  # point, space
    region_selected = pyqtSignal(str)  # region_name
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        coordinate_manager: CoordinateManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize coordinate widget.
        
        Args:
            window_tracker: Window tracker instance
            coordinate_manager: Coordinate manager instance
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.debug("Coordinate widget initialized")
        
    def _setup_ui(self) -> None:
        """Setup user interface."""
        try:
            # Create main layout
            main_layout = QVBoxLayout(self)
            
            # Create space group
            space_group = QGroupBox("Coordinate Spaces")
            space_layout = QVBoxLayout(space_group)
            
            # Create space selector
            self.space_combo = QComboBox()
            self.space_combo.addItems([
                CoordinateSpace.SCREEN,
                CoordinateSpace.WINDOW,
                CoordinateSpace.CLIENT,
                CoordinateSpace.LOGICAL
            ])
            space_layout.addWidget(self.space_combo)
            
            main_layout.addWidget(space_group)
            
            # Create coordinate group
            coord_group = QGroupBox("Coordinate Test")
            coord_layout = QVBoxLayout(coord_group)
            
            # Create coordinate inputs
            input_layout = QHBoxLayout()
            
            self.x_input = QSpinBox()
            self.x_input.setRange(-10000, 10000)
            input_layout.addWidget(QLabel("X:"))
            input_layout.addWidget(self.x_input)
            
            self.y_input = QSpinBox()
            self.y_input.setRange(-10000, 10000)
            input_layout.addWidget(QLabel("Y:"))
            input_layout.addWidget(self.y_input)
            
            coord_layout.addLayout(input_layout)
            
            # Create transform controls
            transform_layout = QHBoxLayout()
            
            self.from_space = QComboBox()
            self.from_space.addItems([
                CoordinateSpace.SCREEN,
                CoordinateSpace.WINDOW,
                CoordinateSpace.CLIENT,
                CoordinateSpace.LOGICAL
            ])
            transform_layout.addWidget(QLabel("From:"))
            transform_layout.addWidget(self.from_space)
            
            self.to_space = QComboBox()
            self.to_space.addItems([
                CoordinateSpace.SCREEN,
                CoordinateSpace.WINDOW,
                CoordinateSpace.CLIENT,
                CoordinateSpace.LOGICAL
            ])
            transform_layout.addWidget(QLabel("To:"))
            transform_layout.addWidget(self.to_space)
            
            self.transform_button = QPushButton("Transform")
            transform_layout.addWidget(self.transform_button)
            
            coord_layout.addLayout(transform_layout)
            
            # Create result display
            self.result_label = QLabel()
            coord_layout.addWidget(self.result_label)
            
            main_layout.addWidget(coord_group)
            
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
            
            self.remove_region = QPushButton("Remove Region")
            region_controls.addWidget(self.remove_region)
            
            region_layout.addLayout(region_controls)
            
            # Create region list
            self.region_list = QListWidget()
            region_layout.addWidget(self.region_list)
            
            main_layout.addWidget(region_group)
            
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
            # Space signals
            self.space_combo.currentTextChanged.connect(
                self._on_space_changed
            )
            
            # Coordinate signals
            self.x_input.valueChanged.connect(self._on_coordinate_changed)
            self.y_input.valueChanged.connect(self._on_coordinate_changed)
            
            # Transform signals
            self.transform_button.clicked.connect(self._transform_coordinate)
            
            # Region signals
            self.add_region.clicked.connect(self._add_region)
            self.remove_region.clicked.connect(self._remove_region)
            self.region_list.itemSelectionChanged.connect(
                self._on_region_selected
            )
            
            # Window tracker signals
            self.window_tracker.window_found.connect(
                lambda _: self._update_metrics()
            )
            self.window_tracker.window_lost.connect(
                lambda: self._update_metrics()
            )
            self.window_tracker.window_moved.connect(
                lambda _: self._update_metrics()
            )
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _on_space_changed(self, space: str) -> None:
        """Handle coordinate space change."""
        try:
            # Update active spaces
            self.coordinate_manager.set_active_spaces([space])
            
            # Update metrics
            self._update_metrics()
            
            logger.debug(f"Active space changed to {space}")
            
        except Exception as e:
            logger.error(f"Error handling space change: {e}")
            
    def _on_coordinate_changed(self) -> None:
        """Handle coordinate input change."""
        try:
            # Get current point
            point = QPoint(
                self.x_input.value(),
                self.y_input.value()
            )
            
            # Get current space
            space = self.space_combo.currentText()
            
            # Emit signal
            self.coordinate_changed.emit(point, space)
            
            # Validate coordinate
            valid = self.coordinate_manager.is_valid_coordinate(
                point,
                space
            )
            
            # Update UI
            if valid:
                self.result_label.setText("Valid coordinate")
                self.result_label.setStyleSheet("color: green")
            else:
                self.result_label.setText("Invalid coordinate")
                self.result_label.setStyleSheet("color: red")
                
        except Exception as e:
            logger.error(f"Error handling coordinate change: {e}")
            
    def _transform_coordinate(self) -> None:
        """Transform coordinate between spaces."""
        try:
            # Get current point
            point = QPoint(
                self.x_input.value(),
                self.y_input.value()
            )
            
            # Get spaces
            from_space = self.from_space.currentText()
            to_space = self.to_space.currentText()
            
            # Transform point
            result = self.coordinate_manager.transform_point(
                point,
                from_space,
                to_space
            )
            
            # Update result display
            self.result_label.setText(
                f"Result: ({result.x()}, {result.y()})"
            )
            self.result_label.setStyleSheet("")
            
            logger.debug(
                f"Transformed ({point.x()}, {point.y()}) "
                f"from {from_space} to {to_space}: "
                f"({result.x()}, {result.y()})"
            )
            
        except Exception as e:
            logger.error(f"Error transforming coordinate: {e}")
            
    def _add_region(self) -> None:
        """Add new region."""
        try:
            # Get region name
            name = self.region_name.text().strip()
            if not name:
                return
                
            # Create region in current space
            space = self.space_combo.currentText()
            rect = QRect(0, 0, 100, 100)  # Default size
            
            # Add to coordinate manager
            self.coordinate_manager.add_region(name, rect, space)
            
            # Update region list
            self.region_list.addItem(name)
            
            # Clear input
            self.region_name.clear()
            
            logger.debug(f"Added region: {name}")
            
        except Exception as e:
            logger.error(f"Error adding region: {e}")
            
    def _remove_region(self) -> None:
        """Remove selected region."""
        try:
            # Get selected region
            item = self.region_list.currentItem()
            if not item:
                return
                
            name = item.text()
            
            # Remove from coordinate manager
            self.coordinate_manager.remove_region(name)
            
            # Remove from list
            self.region_list.takeItem(
                self.region_list.row(item)
            )
            
            logger.debug(f"Removed region: {name}")
            
        except Exception as e:
            logger.error(f"Error removing region: {e}")
            
    def _on_region_selected(self) -> None:
        """Handle region selection."""
        try:
            # Get selected region
            item = self.region_list.currentItem()
            if not item:
                return
                
            name = item.text()
            
            # Emit signal
            self.region_selected.emit(name)
            
            # Get region info
            region = self.coordinate_manager.get_region(
                name,
                self.space_combo.currentText()
            )
            
            if region:
                # Update coordinate inputs
                self.x_input.setValue(region.x())
                self.y_input.setValue(region.y())
                
            logger.debug(f"Selected region: {name}")
            
        except Exception as e:
            logger.error(f"Error handling region selection: {e}")
            
    def _update_metrics(self) -> None:
        """Update coordinate metrics."""
        try:
            # Get window info
            window_info = self.window_tracker.get_debug_info()
            
            # Format metrics text
            metrics_text = (
                f"Window Found: {window_info['window_found']}\n"
                f"Window Handle: {window_info['window_handle']}\n"
                f"Window Rect: {window_info['window_rect']}\n"
                f"Client Rect: {window_info['client_rect']}\n"
                f"DPI Scale: {window_info['dpi_scale']}\n"
                f"Active Space: {self.space_combo.currentText()}\n"
                f"Regions: {len(self.coordinate_manager.regions)}"
            )
            
            self.metrics_label.setText(metrics_text)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}") 