"""Detection Heatmap Widget

This module provides a widget for visualizing the frequency of detections across
different areas of the game window. It generates heatmaps showing where detections
occur most frequently to help identify patterns and important regions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib
import numpy as np

matplotlib.use('Qt5Agg')  # Use Qt5Agg backend for PyQt6 compatibility
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PyQt6.QtCore import Qt
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

# Set up logging
logger = logging.getLogger(__name__)

class HeatmapCanvas(FigureCanvas):
    """A canvas for drawing detection heatmaps using matplotlib."""

    def __init__(self, width=8, height=6, dpi=100):
        """Initialize the canvas with a specified size and resolution.
        
        Args:
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Resolution in dots per inch
        """
        # Create figure and axes
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)

        # Initialize FigureCanvas
        super().__init__(self.fig)

        # Configure figure
        self.fig.tight_layout()
        self.fig.patch.set_facecolor('#f0f0f0')

        # Configure the axes
        self.axes.set_title('Detection Frequency Heatmap')
        self.axes.set_xlabel('X Coordinate')
        self.axes.set_ylabel('Y Coordinate')

        # Set canvas size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)

        # Store references to the colorbar and heatmap for updates
        self.colorbar = None
        self.heatmap_img = None

        # Initialize with empty data
        self._initialize_empty()

    def _initialize_empty(self):
        """Initialize with an empty heatmap."""
        # Clear the axes
        self.axes.clear()

        # Create empty data (10x10 grid of zeros)
        empty_data = np.zeros((10, 10))

        # Create the heatmap
        self.heatmap_img = self.axes.imshow(
            empty_data,
            interpolation='nearest',
            cmap='viridis',
            aspect='auto',
            extent=[0, 1000, 0, 1000],  # Example game window coordinates
            alpha=0.8
        )

        # Add colorbar
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.fig.colorbar(self.heatmap_img, ax=self.axes)
        self.colorbar.set_label('Detection Frequency')

        # Add title and labels
        self.axes.set_title('Detection Frequency Heatmap')
        self.axes.set_xlabel('X Coordinate')
        self.axes.set_ylabel('Y Coordinate')

        # Draw the canvas
        self.draw()

    def update_heatmap(self, data: np.ndarray, extent: List[int], title: str = None):
        """Update the heatmap with new data.
        
        Args:
            data: 2D numpy array of detection frequencies
            extent: [xmin, xmax, ymin, ymax] for the heatmap boundaries
            title: Optional title for the heatmap
        """
        # Clear the axes
        self.axes.clear()

        # Create the heatmap
        self.heatmap_img = self.axes.imshow(
            data,
            interpolation='nearest',
            cmap='hot',  # Red-yellow colormap is good for heatmaps
            aspect='auto',
            extent=extent,
            alpha=0.8
        )

        # Add colorbar
        if self.colorbar:
            self.colorbar.remove()
        self.colorbar = self.fig.colorbar(self.heatmap_img, ax=self.axes)
        self.colorbar.set_label('Detection Frequency')

        # Add title and labels
        if title:
            self.axes.set_title(title)
        else:
            self.axes.set_title('Detection Frequency Heatmap')
        self.axes.set_xlabel('X Coordinate')
        self.axes.set_ylabel('Y Coordinate')

        # Draw the canvas
        self.draw()

    def add_reference_image(self, image: np.ndarray, extent: List[int], alpha: float = 0.3):
        """Add a reference image behind the heatmap for context.
        
        Args:
            image: Game screenshot as background
            extent: [xmin, xmax, ymin, ymax] for the image boundaries
            alpha: Transparency of the reference image
        """
        # Add the image below the heatmap
        if image is not None and image.size > 0:
            # Convert BGR to RGB (matplotlib uses RGB)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                # Add the image
                self.axes.imshow(
                    image_rgb,
                    extent=extent,
                    alpha=alpha,
                    zorder=0  # Place below the heatmap
                )

                # Redraw
                self.draw()

    def add_custom_marks(self, marks: List[Dict[str, Any]]):
        """Add custom marks (rectangles, points) to the heatmap.
        
        Args:
            marks: List of dictionaries with mark information:
                  {'type': 'rectangle', 'coords': [x, y, width, height], 'color': 'r', 'label': 'Target'}
        """
        for mark in marks:
            mark_type = mark.get('type', 'rectangle')
            coords = mark.get('coords', [0, 0, 0, 0])
            color = mark.get('color', 'r')
            label = mark.get('label', '')

            if mark_type == 'rectangle':
                # Create rectangle patch
                x, y, width, height = coords
                rect = Rectangle(
                    (x, y), width, height,
                    linewidth=2,
                    edgecolor=color,
                    facecolor='none',
                    label=label if marks.index(mark) == 0 else ""  # Only label the first one
                )
                self.axes.add_patch(rect)

                # Add label text near the rectangle
                if label:
                    self.axes.text(
                        x + width/2,
                        y - 10,
                        label,
                        color=color,
                        fontsize=9,
                        ha='center'
                    )

            elif mark_type == 'point':
                # Create point marker
                x, y = coords[:2]
                self.axes.plot(
                    x, y,
                    marker='o',
                    markersize=8,
                    color=color,
                    label=label if marks.index(mark) == 0 else ""
                )

                # Add label text near the point
                if label:
                    self.axes.text(
                        x + 5,
                        y + 5,
                        label,
                        color=color,
                        fontsize=9
                    )

        # Add legend if there are labeled marks
        if any(mark.get('label') for mark in marks):
            self.axes.legend(loc='upper right')

        # Redraw
        self.draw()

    def save_figure(self, file_path: str, dpi: int = 300):
        """Save the current figure to a file.
        
        Args:
            file_path: Path to save the figure
            dpi: Resolution for the saved figure
        """
        self.fig.savefig(file_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"Heatmap saved to {file_path}")

class DetectionHeatmapWidget(QWidget):
    """Widget for visualizing detection frequency heatmaps.
    
    This widget provides tools for:
    - Generating heatmaps based on historical detection data
    - Filtering by detection type and time range
    - Adjusting visualization parameters
    - Exporting heatmaps for reporting
    
    The heatmap shows where detections occur most frequently in the game window,
    helping identify important areas and patterns in the detection process.
    """

    def __init__(self, window_service: WindowServiceInterface,
                detection_service: DetectionServiceInterface):
        """Initialize the Detection Heatmap Widget.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
        """
        super().__init__()

        self._window_service = window_service
        self._detection_service = detection_service

        # Initialize detection data
        self._detection_data = []  # List of detection results with timestamps
        self._last_screenshot = None  # Latest screenshot
        self._binning_resolution = 20  # Default 20x20 grid

        # Create UI
        self._create_ui()

        # Connect signals
        self._connect_signals()

        logger.info("Detection Heatmap Widget initialized")

    def _create_ui(self):
        """Create the user interface for the heatmap widget."""
        main_layout = QVBoxLayout(self)

        # Create controls section
        controls_layout = self._create_controls()
        main_layout.addLayout(controls_layout)

        # Create the heatmap canvas
        self._heatmap_canvas = HeatmapCanvas(width=8, height=6)
        main_layout.addWidget(self._heatmap_canvas, 1)

        # Create status bar
        status_layout = QHBoxLayout()

        self._status_label = QLabel("Ready. No data loaded.")
        status_layout.addWidget(self._status_label)

        status_layout.addStretch()

        self._export_button = QPushButton("Export Heatmap")
        self._export_button.clicked.connect(self._on_export_clicked)
        status_layout.addWidget(self._export_button)

        main_layout.addLayout(status_layout)

    def _create_controls(self) -> QHBoxLayout:
        """Create control elements for the heatmap widget.
        
        Returns:
            Layout containing the controls
        """
        controls_layout = QHBoxLayout()

        # Data source group
        data_group = QGroupBox("Data Source")
        data_layout = QVBoxLayout(data_group)

        self._load_from_history_radio = QRadioButton("From Detection History")
        self._load_from_history_radio.setChecked(True)
        self._load_recent_session_radio = QRadioButton("Current Session Only")
        self._load_from_file_radio = QRadioButton("From File")

        self._source_group = QButtonGroup()
        self._source_group.addButton(self._load_from_history_radio)
        self._source_group.addButton(self._load_recent_session_radio)
        self._source_group.addButton(self._load_from_file_radio)

        data_layout.addWidget(self._load_from_history_radio)
        data_layout.addWidget(self._load_recent_session_radio)
        data_layout.addWidget(self._load_from_file_radio)

        # Action button
        self._load_data_button = QPushButton("Load Data")
        self._load_data_button.clicked.connect(self._on_load_data_clicked)
        data_layout.addWidget(self._load_data_button)

        controls_layout.addWidget(data_group)

        # Filter group
        filter_group = QGroupBox("Filters")
        filter_layout = QGridLayout(filter_group)

        # Strategy filter
        filter_layout.addWidget(QLabel("Detection Strategy:"), 0, 0)
        self._strategy_combo = QComboBox()
        self._strategy_combo.addItems(["All", "Template", "OCR", "YOLO"])
        filter_layout.addWidget(self._strategy_combo, 0, 1)

        # Time range filter
        filter_layout.addWidget(QLabel("Time Range:"), 1, 0)
        self._time_range_combo = QComboBox()
        self._time_range_combo.addItems([
            "All Time",
            "Last Hour",
            "Last 24 Hours",
            "Last 7 Days"
        ])
        filter_layout.addWidget(self._time_range_combo, 1, 1)

        # Confidence threshold
        filter_layout.addWidget(QLabel("Min Confidence:"), 2, 0)
        confidence_layout = QHBoxLayout()
        self._min_confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self._min_confidence_slider.setRange(0, 100)
        self._min_confidence_slider.setValue(50)  # Default to 0.5 (50%)
        self._min_confidence_label = QLabel("0.50")
        confidence_layout.addWidget(self._min_confidence_slider)
        confidence_layout.addWidget(self._min_confidence_label)
        filter_layout.addLayout(confidence_layout, 2, 1)

        controls_layout.addWidget(filter_group)

        # Visualization group
        visual_group = QGroupBox("Visualization")
        visual_layout = QGridLayout(visual_group)

        # Resolution
        visual_layout.addWidget(QLabel("Grid Resolution:"), 0, 0)
        self._resolution_spin = QSpinBox()
        self._resolution_spin.setRange(5, 100)
        self._resolution_spin.setValue(self._binning_resolution)
        self._resolution_spin.setSingleStep(5)
        visual_layout.addWidget(self._resolution_spin, 0, 1)

        # Background image
        visual_layout.addWidget(QLabel("Background:"), 1, 0)
        self._show_background_check = QCheckBox("Show Screenshot")
        self._show_background_check.setChecked(True)
        visual_layout.addWidget(self._show_background_check, 1, 1)

        # Opacity
        visual_layout.addWidget(QLabel("Heatmap Opacity:"), 2, 0)
        opacity_layout = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)  # 10-100%
        self._opacity_slider.setValue(80)  # Default to 80%
        self._opacity_label = QLabel("80%")
        opacity_layout.addWidget(self._opacity_slider)
        opacity_layout.addWidget(self._opacity_label)
        visual_layout.addLayout(opacity_layout, 2, 1)

        # Generate button
        self._generate_button = QPushButton("Generate Heatmap")
        self._generate_button.clicked.connect(self._on_generate_clicked)
        visual_layout.addWidget(self._generate_button, 3, 0, 1, 2)

        controls_layout.addWidget(visual_group)

        return controls_layout

    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Connect slider signals
        self._min_confidence_slider.valueChanged.connect(self._on_confidence_changed)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)

        # Connect radio button signals
        self._source_group.buttonClicked.connect(self._on_source_changed)

    def _on_confidence_changed(self, value: int):
        """Handle confidence slider value changed.
        
        Args:
            value: Slider value (0-100)
        """
        confidence = value / 100.0
        self._min_confidence_label.setText(f"{confidence:.2f}")

    def _on_opacity_changed(self, value: int):
        """Handle opacity slider value changed.
        
        Args:
            value: Slider value (10-100)
        """
        self._opacity_label.setText(f"{value}%")

    def _on_source_changed(self, button):
        """Handle data source selection changed.
        
        Args:
            button: Selected radio button
        """
        is_file = button == self._load_from_file_radio
        self._load_data_button.setText("Browse..." if is_file else "Load Data")

    def _on_load_data_clicked(self):
        """Handle load data button clicked."""
        if self._load_from_file_radio.isChecked():
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Detection Data",
                "",
                "JSON Files (*.json);;CSV Files (*.csv)"
            )

            if file_path:
                self._load_data_from_file(file_path)
        else:
            # Load from history or current session
            use_current_session = self._load_recent_session_radio.isChecked()
            self._load_data_from_history(use_current_session)

        # Update status
        if self._detection_data:
            self._status_label.setText(
                f"Loaded {len(self._detection_data)} detection events."
            )

    def _load_data_from_history(self, current_session_only: bool = False):
        """Load detection data from history.
        
        Args:
            current_session_only: Whether to load only data from the current session
        """
        # In a real implementation, this would retrieve data from a detection history service
        # For now, we'll just use dummy data

        # Clear existing data
        self._detection_data = []

        # TODO: Replace with actual implementation that gets data from detection history
        self._load_dummy_data()

    def _load_data_from_file(self, file_path: str):
        """Load detection data from a file.
        
        Args:
            file_path: Path to the data file
        """
        import csv
        import json

        # Clear existing data
        self._detection_data = []

        try:
            if file_path.lower().endswith('.json'):
                # Load JSON file
                with open(file_path, 'r') as f:
                    data = json.load(f)

                    # Process the data
                    if isinstance(data, list):
                        # Assume list of detection events
                        for event in data:
                            if 'timestamp' in event and 'results' in event and 'strategy' in event:
                                # Convert timestamp string to datetime if needed
                                timestamp = event['timestamp']
                                if isinstance(timestamp, str):
                                    timestamp = datetime.fromisoformat(timestamp)

                                # Add to detection data
                                self._detection_data.append({
                                    'timestamp': timestamp,
                                    'results': event['results'],
                                    'strategy': event['strategy']
                                })

            elif file_path.lower().endswith('.csv'):
                # Load CSV file
                with open(file_path, 'r', newline='') as f:
                    reader = csv.reader(f)
                    headers = next(reader)  # Skip header row

                    # Check if we have the expected columns
                    if 'Timestamp' in headers and 'Strategy' in headers:
                        # Find column indices
                        ts_idx = headers.index('Timestamp')
                        strat_idx = headers.index('Strategy')

                        # Create a dictionary to group by timestamp
                        events_by_timestamp = {}

                        for row in reader:
                            timestamp_str = row[ts_idx]
                            strategy = row[strat_idx]

                            # Parse timestamp
                            try:
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                continue

                            # Add to events by timestamp
                            if timestamp not in events_by_timestamp:
                                events_by_timestamp[timestamp] = {
                                    'timestamp': timestamp,
                                    'strategy': strategy,
                                    'results': []
                                }

                            # Add result data
                            # TODO: Extract and add result data from CSV row

                        # Add events to detection data
                        self._detection_data.extend(events_by_timestamp.values())

            logger.info(f"Loaded {len(self._detection_data)} detection events from {file_path}")

        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            self._status_label.setText(f"Error loading data: {e}")

    def _load_dummy_data(self):
        """Load dummy detection data for testing."""
        # Create a sample game screenshot
        if self._last_screenshot is None:
            self._last_screenshot = np.zeros((600, 800, 3), dtype=np.uint8)
            self._last_screenshot.fill(64)  # Dark gray background

            # Add some visual elements to the screenshot
            cv2.rectangle(self._last_screenshot, (100, 100), (300, 200), (0, 0, 255), -1)  # Red rectangle
            cv2.rectangle(self._last_screenshot, (500, 300), (700, 500), (0, 255, 0), -1)  # Green rectangle
            cv2.circle(self._last_screenshot, (400, 300), 50, (255, 0, 0), -1)  # Blue circle

        # Generate timestamps over the past week
        now = datetime.now()

        # Generate random detection clusters
        clusters = [
            (150, 150, 50, 40, 20),   # (x, y, x_spread, y_spread, count) - around red rectangle
            (600, 400, 30, 60, 30),   # Around green rectangle
            (400, 300, 20, 20, 15),   # Around blue circle
            (700, 100, 40, 30, 10),   # Top right corner
            (200, 500, 30, 40, 5)     # Bottom left-ish
        ]

        # Generate random detections for each cluster
        import random
        for x, y, x_spread, y_spread, count in clusters:
            for _ in range(count):
                # Random position within the cluster
                rx = int(random.gauss(x, x_spread/3))
                ry = int(random.gauss(y, y_spread/3))

                # Ensure coordinates are within screen bounds
                rx = max(0, min(rx, 800))
                ry = max(0, min(ry, 600))

                # Random size
                w = random.randint(20, 60)
                h = random.randint(20, 60)

                # Random strategy
                strategy = random.choice(['template', 'ocr', 'yolo'])

                # Random confidence
                confidence = random.uniform(0.6, 0.95)

                # Random timestamp within the past week
                days_ago = random.uniform(0, 7)
                timestamp = now - timedelta(days=days_ago)

                # Create detection result
                result = {
                    'x': rx,
                    'y': ry,
                    'width': w,
                    'height': h,
                    'confidence': confidence,
                }

                # Add strategy-specific data
                if strategy == 'template':
                    result['template_name'] = random.choice(
                        ['button', 'icon', 'resource', 'building', 'unit']
                    )
                elif strategy == 'ocr':
                    result['text'] = random.choice(
                        ['Attack', 'Defend', 'Build', 'Upgrade', 'Resources']
                    )
                elif strategy == 'yolo':
                    result['class_name'] = random.choice(
                        ['building', 'unit', 'resource', 'enemy', 'ally']
                    )

                # Add to detection data
                self._detection_data.append({
                    'timestamp': timestamp,
                    'strategy': strategy,
                    'results': [result]
                })

        # Sort by timestamp
        self._detection_data.sort(key=lambda x: x['timestamp'])

        logger.info(f"Generated {len(self._detection_data)} sample detection events")

    def _on_generate_clicked(self):
        """Handle generate heatmap button clicked."""
        # Check if we have data
        if not self._detection_data:
            self._status_label.setText("No data available. Please load data first.")
            return

        # Get filter settings
        strategy_filter = self._strategy_combo.currentText()
        time_range = self._time_range_combo.currentText()
        min_confidence = self._min_confidence_slider.value() / 100.0
        resolution = self._resolution_spin.value()
        show_background = self._show_background_check.isChecked()
        opacity = self._opacity_slider.value() / 100.0

        # Generate heatmap
        self._generate_heatmap(
            strategy_filter,
            time_range,
            min_confidence,
            resolution,
            show_background,
            opacity
        )

    def _generate_heatmap(
        self,
        strategy_filter: str,
        time_range: str,
        min_confidence: float,
        resolution: int,
        show_background: bool,
        opacity: float
    ):
        """Generate a heatmap based on the specified filters.
        
        Args:
            strategy_filter: Strategy to filter by ('All' or specific strategy)
            time_range: Time range to include ('All Time' or specific range)
            min_confidence: Minimum confidence threshold (0.0-1.0)
            resolution: Binning resolution (grid size)
            show_background: Whether to show the background screenshot
            opacity: Opacity of the heatmap (0.0-1.0)
        """
        # Filter data based on criteria
        filtered_data = self._filter_detection_data(
            strategy_filter,
            time_range,
            min_confidence
        )

        if not filtered_data:
            self._status_label.setText("No data matches the current filters.")
            return

        # Generate the heatmap data
        heatmap_data, extent = self._create_heatmap_data(filtered_data, resolution)

        # Update the heatmap canvas
        title = f"Detection Frequency: {strategy_filter} ({len(filtered_data)} events)"
        self._heatmap_canvas.update_heatmap(heatmap_data, extent, title)

        # Add background if requested
        if show_background and self._last_screenshot is not None:
            # Calculate the extent based on screenshot dimensions
            height, width = self._last_screenshot.shape[:2]
            bg_extent = [0, width, height, 0]  # Note: y-axis is flipped in imshow

            # Add the background image
            self._heatmap_canvas.add_reference_image(
                self._last_screenshot,
                bg_extent,
                alpha=0.3
            )

        # Add key regions of interest
        # This is just an example - in a real implementation, you might
        # identify key regions of interest from the detection data
        self._add_regions_of_interest(heatmap_data)

        # Update status
        self._status_label.setText(
            f"Generated heatmap from {len(filtered_data)} events "
            f"({strategy_filter}, {time_range}, conf>{min_confidence:.2f})"
        )

    def _filter_detection_data(
        self,
        strategy_filter: str,
        time_range: str,
        min_confidence: float
    ) -> List[Dict]:
        """Filter detection data based on criteria.
        
        Args:
            strategy_filter: Strategy to filter by ('All' or specific strategy)
            time_range: Time range to include ('All Time' or specific range)
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            Filtered detection data
        """
        # Start with all data
        filtered_data = self._detection_data.copy()

        # Filter by strategy
        if strategy_filter != "All":
            strategy_name = strategy_filter.lower()
            filtered_data = [
                event for event in filtered_data
                if event['strategy'].lower() == strategy_name
            ]

        # Filter by time range
        now = datetime.now()
        if time_range == "Last Hour":
            cutoff = now - timedelta(hours=1)
            filtered_data = [
                event for event in filtered_data
                if event['timestamp'] >= cutoff
            ]
        elif time_range == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
            filtered_data = [
                event for event in filtered_data
                if event['timestamp'] >= cutoff
            ]
        elif time_range == "Last 7 Days":
            cutoff = now - timedelta(days=7)
            filtered_data = [
                event for event in filtered_data
                if event['timestamp'] >= cutoff
            ]

        # Filter by confidence
        # We need to check the confidence of individual results
        results_filtered_data = []
        for event in filtered_data:
            # Find results that meet the confidence threshold
            filtered_results = [
                result for result in event['results']
                if result.get('confidence', 0) >= min_confidence
            ]

            # Only include the event if it has matching results
            if filtered_results:
                # Create a new event with only the filtered results
                filtered_event = event.copy()
                filtered_event['results'] = filtered_results
                results_filtered_data.append(filtered_event)

        return results_filtered_data

    def _create_heatmap_data(
        self,
        detection_data: List[Dict],
        resolution: int
    ) -> Tuple[np.ndarray, List[int]]:
        """Create heatmap data from detection results.
        
        Args:
            detection_data: Filtered detection data to visualize
            resolution: Binning resolution (grid size)
            
        Returns:
            Tuple of (heatmap_data, extent) where:
                heatmap_data: 2D numpy array of detection counts
                extent: [xmin, xmax, ymin, ymax] for the heatmap
        """
        # Determine the extent of our data
        if self._last_screenshot is not None:
            height, width = self._last_screenshot.shape[:2]
        else:
            # Use default bounds if no screenshot is available
            width, height = 800, 600

        # Create a grid for the heatmap
        grid = np.zeros((resolution, resolution))

        # Map each detection to a grid cell
        cell_width = width / resolution
        cell_height = height / resolution

        # Count detections in each grid cell
        for event in detection_data:
            for result in event['results']:
                # Get the center of the detection
                x = result.get('x', 0) + result.get('width', 0) / 2
                y = result.get('y', 0) + result.get('height', 0) / 2

                # Map to grid cell
                cell_x = int(min(resolution - 1, max(0, x // cell_width)))
                cell_y = int(min(resolution - 1, max(0, y // cell_height)))

                # Increment the count
                grid[cell_y, cell_x] += 1

        # Smooth the grid (optional)
        from scipy.ndimage import gaussian_filter
        smoothed_grid = gaussian_filter(grid, sigma=1.0)

        # Calculate the extent for visualization
        extent = [0, width, height, 0]  # [xmin, xmax, ymin, ymax]

        return smoothed_grid, extent

    def _add_regions_of_interest(self, heatmap_data: np.ndarray):
        """Add regions of interest to the heatmap.
        
        This identifies and marks important regions based on the heatmap data.
        
        Args:
            heatmap_data: 2D numpy array of detection counts
        """
        # Find hotspots (regions with high detection counts)
        # This is a simple example - in a real implementation, you might use
        # more sophisticated cluster detection algorithms
        if heatmap_data.size == 0:
            return

        # Find peaks in the heatmap
        from scipy.ndimage import label, maximum_filter

        # Find local maxima
        max_filtered = maximum_filter(heatmap_data, size=3)
        maxima = (heatmap_data == max_filtered) & (heatmap_data > np.mean(heatmap_data) + np.std(heatmap_data))

        # Label connected regions
        labeled, num_objects = label(maxima)

        # Extract coordinates of hotspots
        hotspots = []

        if self._last_screenshot is not None:
            height, width = self._last_screenshot.shape[:2]
        else:
            # Use default bounds if no screenshot is available
            width, height = 800, 600

        grid_height, grid_width = heatmap_data.shape

        for i in range(1, num_objects + 1):
            # Find all cells in this hotspot
            y_indices, x_indices = np.where(labeled == i)

            if len(y_indices) > 0:
                # Calculate center of hotspot in grid coordinates
                center_y = np.mean(y_indices)
                center_x = np.mean(x_indices)

                # Convert to screen coordinates
                screen_x = center_x / grid_width * width
                screen_y = center_y / grid_height * height

                # Get value at this hotspot
                value = heatmap_data[int(center_y), int(center_x)]

                hotspots.append((screen_x, screen_y, value))

        # Sort hotspots by value (highest first) and take top 3
        hotspots.sort(key=lambda x: x[2], reverse=True)
        hotspots = hotspots[:3]

        # Create marks for the hotspots
        marks = []
        for i, (x, y, value) in enumerate(hotspots):
            # Generate a color based on value
            color = plt.cm.jet(value / np.max(heatmap_data) if np.max(heatmap_data) > 0 else 0)

            marks.append({
                'type': 'rectangle',
                'coords': [x - 40, y - 40, 80, 80],  # Arbitrary size
                'color': color,
                'label': f"Hotspot {i+1}"
            })

        # Add the marks to the canvas
        if marks:
            self._heatmap_canvas.add_custom_marks(marks)

    def _on_export_clicked(self):
        """Handle export heatmap button clicked."""
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Heatmap",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)"
        )

        if file_path:
            # Save the figure
            self._heatmap_canvas.save_figure(file_path)
            self._status_label.setText(f"Heatmap exported to {file_path}")

    def add_detection_event(self, timestamp: datetime, results: List[Dict], strategy: str, screenshot: Optional[np.ndarray] = None):
        """Add a new detection event to the heatmap data.
        
        Args:
            timestamp: Time of the detection
            results: Detection results
            strategy: Detection strategy used
            screenshot: Optional screenshot from the detection
        """
        # Create detection event
        event = {
            'timestamp': timestamp,
            'results': results,
            'strategy': strategy
        }

        # Add to detection data
        self._detection_data.append(event)

        # Update screenshot if provided
        if screenshot is not None:
            self._last_screenshot = screenshot

        # Log the event
        logger.debug(f"Added detection event to heatmap data: {strategy} with {len(results)} results")

        # Update status if this is the first event
        if len(self._detection_data) == 1:
            self._status_label.setText("Data available. Click 'Generate Heatmap' to visualize.")

    def clear_data(self):
        """Clear all detection data and reset the heatmap."""
        self._detection_data = []
        self._last_screenshot = None
        self._heatmap_canvas._initialize_empty()
        self._status_label.setText("Ready. No data loaded.")
        logger.info("Cleared heatmap data")
