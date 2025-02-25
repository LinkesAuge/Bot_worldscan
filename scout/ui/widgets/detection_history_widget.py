"""
Detection History Widget

This module provides a widget for visualizing historical detection data over time.
It enables users to track patterns, trends, and changes in detection results across
multiple detection runs.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime, timedelta
import cv2
from collections import deque
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QSplitter,
    QHeaderView, QComboBox, QMessageBox, QGroupBox, QRadioButton,
    QButtonGroup, QSlider, QSpinBox, QToolBar, QFileDialog, QSizePolicy,
    QTabWidget
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont,
    QMouseEvent, QResizeEvent, QPaintEvent, QAction, QIcon
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRect, QSize, QPoint, QTimer, QDateTime
)

from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface

# Set up logging
logger = logging.getLogger(__name__)

class TimelineView(QWidget):
    """
    Widget for displaying a timeline of detection results.
    
    This widget provides a visual representation of detection events over time,
    allowing users to see patterns and trends.
    """
    
    # Signals
    timestamp_selected = pyqtSignal(datetime)  # Selected timestamp
    
    def __init__(self):
        """Initialize the timeline view."""
        super().__init__()
        
        # Initialize state
        self._history = []  # List of (timestamp, results) tuples
        self._timestamps = []  # List of timestamps only
        self._current_index = -1  # Current selected index
        self._start_time = datetime.now()  # Start time for visualization
        self._end_time = datetime.now()  # End time for visualization
        self._time_range = timedelta(minutes=30)  # Default time range
        
        # Configure widget
        self.setMinimumSize(400, 100)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # To receive key events
        self.setMouseTracking(True)  # To receive mouse move events
        
        # Configure colors
        self._colors = {
            "template": QColor(0, 255, 0, 180),  # Semi-transparent green
            "ocr": QColor(255, 255, 0, 180),  # Semi-transparent yellow
            "yolo": QColor(0, 0, 255, 180),  # Semi-transparent blue
            "background": QColor(40, 40, 40),  # Dark gray
            "grid": QColor(80, 80, 80),  # Light gray
            "text": QColor(220, 220, 220),  # Light gray text
            "selection": QColor(255, 0, 0, 180)  # Semi-transparent red
        }
    
    def add_detection_event(self, timestamp: datetime, results: List[Dict], strategy: str) -> None:
        """
        Add a detection event to the timeline.
        
        Args:
            timestamp: Timestamp of the detection
            results: List of detection results
            strategy: Detection strategy used
        """
        # Create event data
        event = {
            'timestamp': timestamp,
            'results': results,
            'strategy': strategy,
            'count': len(results)
        }
        
        # Add to history
        self._history.append(event)
        self._timestamps.append(timestamp)
        
        # Update time range if needed
        if len(self._history) == 1:
            # First entry, set start and end time
            self._start_time = timestamp
            self._end_time = timestamp + self._time_range
        elif timestamp > self._end_time:
            # New event is after current end time, update range
            self._end_time = timestamp
            self._start_time = self._end_time - self._time_range
        
        # Force redraw
        self.update()
    
    def clear_history(self) -> None:
        """Clear all history data."""
        self._history = []
        self._timestamps = []
        self._current_index = -1
        self._start_time = datetime.now()
        self._end_time = datetime.now()
        self.update()
    
    def set_time_range(self, minutes: int) -> None:
        """
        Set the visible time range.
        
        Args:
            minutes: Time range in minutes
        """
        self._time_range = timedelta(minutes=minutes)
        
        # Update start time based on end time
        if self._timestamps:
            self._end_time = self._timestamps[-1]
            self._start_time = self._end_time - self._time_range
        
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the timeline.
        
        Args:
            event: Paint event
        """
        # Init painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self._colors["background"])
        
        # Draw timeline grid
        self._draw_timeline_grid(painter)
        
        # Draw detection events
        self._draw_detection_events(painter)
        
        # Draw current selection
        if self._current_index >= 0 and self._current_index < len(self._history):
            self._draw_selection(painter)
    
    def _draw_timeline_grid(self, painter: QPainter) -> None:
        """
        Draw the timeline grid.
        
        Args:
            painter: QPainter instance
        """
        # Set up drawing tools
        painter.setPen(QPen(self._colors["grid"], 1))
        painter.setFont(QFont("Arial", 8))
        
        # Calculate time intervals
        time_span = (self._end_time - self._start_time).total_seconds()
        interval_seconds = self._get_interval_for_timespan(time_span)
        
        # Calculate widget dimensions
        width = self.width()
        height = self.height()
        
        # Draw horizontal grid line
        painter.drawLine(0, height - 20, width, height - 20)
        
        # Draw time markers
        current_time = self._round_time_to_interval(self._start_time, interval_seconds)
        
        while current_time <= self._end_time:
            # Calculate x position
            x_pos = self._time_to_x(current_time)
            
            # Draw vertical line
            painter.drawLine(x_pos, height - 20, x_pos, height - 15)
            
            # Draw time label
            time_str = current_time.strftime("%H:%M:%S")
            painter.drawText(x_pos - 20, height - 5, 40, 20, 
                          Qt.AlignmentFlag.AlignCenter, time_str)
            
            # Move to next interval
            current_time += timedelta(seconds=interval_seconds)
    
    def _draw_detection_events(self, painter: QPainter) -> None:
        """
        Draw the detection events.
        
        Args:
            painter: QPainter instance
        """
        # Early exit if no history
        if not self._history:
            return
        
        # Calculate height for bars (leave space for labels)
        bar_height = self.height() - 25
        
        # Draw each event
        for event in self._history:
            # Skip events outside the current view
            timestamp = event['timestamp']
            if timestamp < self._start_time or timestamp > self._end_time:
                continue
            
            # Calculate x position
            x_pos = self._time_to_x(timestamp)
            
            # Calculate height based on result count
            result_count = event['count']
            event_height = min(5 + (result_count * 3), bar_height)
            
            # Get color based on strategy
            strategy = event['strategy']
            color = self._colors.get(strategy, self._colors["template"])
            
            # Draw event bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(
                x_pos - 2, 
                bar_height - event_height, 
                4, 
                event_height
            )
    
    def _draw_selection(self, painter: QPainter) -> None:
        """
        Draw the current selection.
        
        Args:
            painter: QPainter instance
        """
        # Get selected event
        event = self._history[self._current_index]
        timestamp = event['timestamp']
        
        # Calculate x position
        x_pos = self._time_to_x(timestamp)
        
        # Draw selection marker
        painter.setPen(QPen(self._colors["selection"], 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw vertical line
        painter.drawLine(x_pos, 0, x_pos, self.height() - 5)
        
        # Draw circle at top
        painter.setBrush(QBrush(self._colors["selection"]))
        painter.drawEllipse(QPoint(x_pos, 10), 5, 5)
        
        # Draw timestamp
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        painter.setPen(QPen(self._colors["text"], 1))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(x_pos + 10, 5, 150, 20, 
                      Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                      time_str)
        
        # Draw result count
        count_str = f"Results: {event['count']}"
        painter.drawText(x_pos + 10, 25, 100, 20, 
                      Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                      count_str)
    
    def _time_to_x(self, timestamp: datetime) -> int:
        """
        Convert a timestamp to an x-coordinate.
        
        Args:
            timestamp: Timestamp to convert
            
        Returns:
            X-coordinate for the timestamp
        """
        # Calculate time position as percentage of time range
        time_span = (self._end_time - self._start_time).total_seconds()
        time_pos = (timestamp - self._start_time).total_seconds()
        percentage = time_pos / time_span
        
        # Convert to x-coordinate
        return int(percentage * self.width())
    
    def _x_to_time(self, x: int) -> datetime:
        """
        Convert an x-coordinate to a timestamp.
        
        Args:
            x: X-coordinate to convert
            
        Returns:
            Timestamp for the x-coordinate
        """
        # Calculate percentage of width
        percentage = x / self.width()
        
        # Convert to time
        time_span = (self._end_time - self._start_time).total_seconds()
        time_offset = time_span * percentage
        
        # Add to start time
        return self._start_time + timedelta(seconds=time_offset)
    
    def _get_interval_for_timespan(self, seconds: float) -> int:
        """
        Get an appropriate time interval for the current timespan.
        
        Args:
            seconds: Timespan in seconds
            
        Returns:
            Appropriate interval in seconds
        """
        # Select an interval that will give approximately 5-10 divisions
        if seconds < 60:  # Less than 1 minute
            return 5  # 5 seconds
        elif seconds < 300:  # Less than 5 minutes
            return 30  # 30 seconds
        elif seconds < 3600:  # Less than 1 hour
            return 300  # 5 minutes
        elif seconds < 86400:  # Less than 1 day
            return 3600  # 1 hour
        else:
            return 86400  # 1 day
    
    def _round_time_to_interval(self, dt: datetime, interval_seconds: int) -> datetime:
        """
        Round a datetime to the nearest interval.
        
        Args:
            dt: Datetime to round
            interval_seconds: Interval in seconds
            
        Returns:
            Rounded datetime
        """
        seconds = (dt.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds()
        rounded = int(seconds / interval_seconds) * interval_seconds
        return datetime(1970, 1, 1) + timedelta(seconds=rounded)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert x-coordinate to time
            click_time = self._x_to_time(event.pos().x())
            
            # Find closest event
            closest_index = -1
            closest_diff = timedelta.max
            
            for i, event_data in enumerate(self._history):
                timestamp = event_data['timestamp']
                diff = abs(timestamp - click_time)
                
                if diff < closest_diff:
                    closest_diff = diff
                    closest_index = i
            
            # If we found a close enough event, select it
            if closest_index >= 0 and closest_diff < timedelta(seconds=30):
                self._current_index = closest_index
                
                # Emit signal with timestamp
                self.timestamp_selected.emit(self._history[closest_index]['timestamp'])
                
                # Redraw
                self.update()
    
    def keyPressEvent(self, event) -> None:
        """
        Handle key press events.
        
        Args:
            event: Key event
        """
        if event.key() == Qt.Key.Key_Left:
            # Select previous event
            if self._current_index > 0:
                self._current_index -= 1
                
                # Emit signal with timestamp
                self.timestamp_selected.emit(self._history[self._current_index]['timestamp'])
                
                # Redraw
                self.update()
                
        elif event.key() == Qt.Key.Key_Right:
            # Select next event
            if self._current_index < len(self._history) - 1:
                self._current_index += 1
                
                # Emit signal with timestamp
                self.timestamp_selected.emit(self._history[self._current_index]['timestamp'])
                
                # Redraw
                self.update()
        else:
            # Let parent handle other keys
            super().keyPressEvent(event)


class DetectionHistoryWidget(QWidget):
    """
    Widget for visualizing and analyzing historical detection data.
    
    This widget provides:
    - Timeline view of detection events
    - Historical detection results visualization
    - Trend analysis for detection results
    - Export and playback functionality
    """
    
    def __init__(self, window_service: WindowServiceInterface,
                detection_service: DetectionServiceInterface):
        """
        Initialize the detection history widget.
        
        Args:
            window_service: Service for window management
            detection_service: Service for detection operations
        """
        super().__init__()
        
        # Store services
        self.window_service = window_service
        self.detection_service = detection_service
        
        # Initialize state
        self._history_data = []  # List of (timestamp, results, screenshot) tuples
        self._max_history_size = 100  # Maximum number of history entries to keep
        
        # Create UI layout
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Set up event listeners
        self._setup_event_listeners()
        
        logger.info("Detection history widget initialized")
    
    def _create_ui(self) -> None:
        """Create the user interface."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar = QToolBar()
        
        # Clear history action
        self.clear_action = QAction("Clear History")
        toolbar.addAction(self.clear_action)
        
        # Export history action
        self.export_action = QAction("Export Data")
        toolbar.addAction(self.export_action)
        
        # Add separator
        toolbar.addSeparator()
        
        # Time range selector
        toolbar.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["5 minutes", "15 minutes", "30 minutes", "1 hour", "3 hours", "All"])
        self.time_range_combo.setCurrentIndex(2)  # Default 30 minutes
        toolbar.addWidget(self.time_range_combo)
        
        # Add to main layout
        main_layout.addWidget(toolbar)
        
        # Create splitter for timeline and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Timeline view
        timeline_group = QGroupBox("Detection Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        
        self.timeline = TimelineView()
        timeline_layout.addWidget(self.timeline)
        
        # Add controls for timeline
        timeline_controls = QHBoxLayout()
        
        # Playback controls
        self.play_btn = QPushButton("Play")
        timeline_controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        timeline_controls.addWidget(self.stop_btn)
        
        # Playback speed
        timeline_controls.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        timeline_controls.addWidget(self.speed_slider)
        
        timeline_layout.addLayout(timeline_controls)
        
        splitter.addWidget(timeline_group)
        
        # Create tabs for different views
        tabs = QTabWidget()
        
        # Results tab
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)
        
        # Results header
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Event Time:"))
        self.event_time_label = QLabel("None")
        self.event_time_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        results_header.addWidget(self.event_time_label)
        
        results_header.addSpacing(20)
        
        results_header.addWidget(QLabel("Strategy:"))
        self.strategy_label = QLabel("None")
        results_header.addWidget(self.strategy_label)
        
        results_header.addSpacing(20)
        
        results_header.addWidget(QLabel("Results:"))
        self.result_count_label = QLabel("0")
        results_header.addWidget(self.result_count_label)
        
        results_header.addStretch()
        
        # Navigate buttons
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setEnabled(False)
        results_header.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setEnabled(False)
        results_header.addWidget(self.next_btn)
        
        results_layout.addLayout(results_header)
        
        # Create results display
        from scout.ui.widgets.detection_result_widget import ResultImageView
        self.result_view = ResultImageView()
        results_layout.addWidget(self.result_view)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Type", "Position", "Size", "Confidence", "Data"])
        
        # Configure table
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)
        
        results_layout.addWidget(self.results_table)
        
        tabs.addTab(self.results_tab, "Results View")
        
        # Trends tab
        self.trends_tab = QWidget()
        trends_layout = QVBoxLayout(self.trends_tab)
        
        trends_layout.addWidget(QLabel("Detection Result Trends"))
        trends_layout.addWidget(QLabel("(Placeholder for trend charts)"))
        
        tabs.addTab(self.trends_tab, "Trends Analysis")
        
        splitter.addWidget(tabs)
        
        # Set initial splitter sizes (30% timeline, 70% details)
        splitter.setSizes([200, 600])
        
        main_layout.addWidget(splitter)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Toolbar actions
        self.clear_action.triggered.connect(self._on_clear_history)
        self.export_action.triggered.connect(self._on_export_history)
        
        # Time range combo
        self.time_range_combo.currentIndexChanged.connect(self._on_time_range_changed)
        
        # Timeline
        self.timeline.timestamp_selected.connect(self._on_timestamp_selected)
        
        # Playback controls
        self.play_btn.clicked.connect(self._on_play_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        
        # Navigation buttons
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        self.next_btn.clicked.connect(self._on_next_clicked)
    
    def _setup_event_listeners(self) -> None:
        """Set up event listeners for detection events."""
        # In a real implementation, we would subscribe to detection events
        # from the detection service
        pass
    
    def add_detection_result(self, results: List[Dict[str, Any]], strategy: str) -> None:
        """
        Add a detection result to the history.
        
        Args:
            results: List of detection results
            strategy: Detection strategy used
        """
        # Capture current time
        timestamp = datetime.now()
        
        # Capture screenshot
        screenshot = self.window_service.capture_screenshot()
        
        # Create history entry
        entry = {
            'timestamp': timestamp,
            'results': results,
            'strategy': strategy,
            'screenshot': screenshot
        }
        
        # Add to history data
        self._history_data.append(entry)
        
        # Limit history size
        if len(self._history_data) > self._max_history_size:
            self._history_data.pop(0)
        
        # Add to timeline
        self.timeline.add_detection_event(timestamp, results, strategy)
        
        logger.debug(f"Added detection result to history, count: {len(results)}")
    
    def _on_clear_history(self) -> None:
        """Handle clear history action."""
        # Confirm with user
        result = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all detection history data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # Clear history data
            self._history_data = []
            
            # Clear timeline
            self.timeline.clear_history()
            
            # Clear display
            self._clear_result_display()
            
            logger.info("Detection history cleared")
    
    def _on_export_history(self) -> None:
        """Handle export history action."""
        if not self._history_data:
            QMessageBox.information(
                self,
                "Export History",
                "No history data to export."
            )
            return
        
        # Create file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Detection History",
            "",
            "CSV Files (*.csv);;JSON Files (*.json);;HTML Report (*.html)"
        )
        
        if not file_path:
            return
        
        # TODO: Implement export functionality
        logger.info(f"Export history to {file_path} (not yet implemented)")
        
        QMessageBox.information(
            self,
            "Export History",
            f"Export to {file_path} is not yet implemented."
        )
    
    def _on_time_range_changed(self, index: int) -> None:
        """
        Handle time range changed.
        
        Args:
            index: Selected index
        """
        # Get selected time range
        time_range_text = self.time_range_combo.currentText()
        
        # Set timeline time range
        if time_range_text == "All":
            # Use all history
            if self._history_data:
                first_time = self._history_data[0]['timestamp']
                last_time = self._history_data[-1]['timestamp']
                range_minutes = max(30, (last_time - first_time).total_seconds() // 60)
                self.timeline.set_time_range(int(range_minutes))
        else:
            # Parse minutes from text
            time_parts = time_range_text.split()
            try:
                if time_parts[1] == "minutes":
                    minutes = int(time_parts[0])
                    self.timeline.set_time_range(minutes)
                elif time_parts[1] == "hour" or time_parts[1] == "hours":
                    hours = int(time_parts[0])
                    self.timeline.set_time_range(hours * 60)
            except (IndexError, ValueError):
                # Default to 30 minutes
                self.timeline.set_time_range(30)
    
    def _on_timestamp_selected(self, timestamp: datetime) -> None:
        """
        Handle timestamp selection from timeline.
        
        Args:
            timestamp: Selected timestamp
        """
        # Find entry with this timestamp
        for i, entry in enumerate(self._history_data):
            if entry['timestamp'] == timestamp:
                # Display this entry
                self._display_history_entry(entry)
                
                # Update navigation buttons
                self.prev_btn.setEnabled(i > 0)
                self.next_btn.setEnabled(i < len(self._history_data) - 1)
                
                # Store current index
                self._current_index = i
                
                return
    
    def _on_play_clicked(self) -> None:
        """Handle play button click."""
        # TODO: Implement playback functionality
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        # TODO: Implement stop functionality
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def _on_prev_clicked(self) -> None:
        """Handle previous button click."""
        if hasattr(self, '_current_index') and self._current_index > 0:
            self._current_index -= 1
            entry = self._history_data[self._current_index]
            
            # Update timeline selection
            self.timeline._current_index = self._current_index
            self.timeline.update()
            
            # Display entry
            self._display_history_entry(entry)
            
            # Update navigation buttons
            self.prev_btn.setEnabled(self._current_index > 0)
            self.next_btn.setEnabled(self._current_index < len(self._history_data) - 1)
    
    def _on_next_clicked(self) -> None:
        """Handle next button click."""
        if hasattr(self, '_current_index') and self._current_index < len(self._history_data) - 1:
            self._current_index += 1
            entry = self._history_data[self._current_index]
            
            # Update timeline selection
            self.timeline._current_index = self._current_index
            self.timeline.update()
            
            # Display entry
            self._display_history_entry(entry)
            
            # Update navigation buttons
            self.prev_btn.setEnabled(self._current_index > 0)
            self.next_btn.setEnabled(self._current_index < len(self._history_data) - 1)
    
    def _display_history_entry(self, entry: Dict) -> None:
        """
        Display a history entry.
        
        Args:
            entry: History entry to display
        """
        # Update header labels
        timestamp = entry['timestamp']
        self.event_time_label.setText(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        
        strategy = entry['strategy']
        self.strategy_label.setText(strategy)
        
        results = entry['results']
        self.result_count_label.setText(str(len(results)))
        
        # Update image view
        screenshot = entry.get('screenshot')
        if screenshot is not None:
            self.result_view.set_image_and_results(screenshot, results, strategy)
        
        # Update results table
        self._populate_results_table(results, strategy)
    
    def _populate_results_table(self, results: List[Dict[str, Any]], strategy: str) -> None:
        """
        Populate the results table.
        
        Args:
            results: List of detection results
            strategy: Detection strategy used
        """
        # Clear table
        self.results_table.setRowCount(0)
        
        # Set row count
        self.results_table.setRowCount(len(results))
        
        # Add each result
        for i, result in enumerate(results):
            # Determine result type
            result_type = "Unknown"
            if strategy == "template":
                result_type = "Template"
            elif strategy == "ocr":
                result_type = "OCR Text"
            elif strategy == "yolo":
                result_type = "Object"
            
            # Create type cell
            type_item = QTableWidgetItem(result_type)
            self.results_table.setItem(i, 0, type_item)
            
            # Create position cell
            x = result.get('x', 0)
            y = result.get('y', 0)
            position_item = QTableWidgetItem(f"({x}, {y})")
            self.results_table.setItem(i, 1, position_item)
            
            # Create size cell
            width = result.get('width', 0)
            height = result.get('height', 0)
            size_item = QTableWidgetItem(f"{width}x{height}")
            self.results_table.setItem(i, 2, size_item)
            
            # Create confidence cell
            confidence = result.get('confidence', 0)
            confidence_item = QTableWidgetItem(f"{confidence:.2f}")
            self.results_table.setItem(i, 3, confidence_item)
            
            # Create data cell
            data = ""
            if 'template_name' in result:
                data = result['template_name']
            elif 'text' in result:
                data = result['text']
            elif 'class_name' in result:
                data = result['class_name']
            
            data_item = QTableWidgetItem(data)
            self.results_table.setItem(i, 4, data_item)
    
    def _clear_result_display(self) -> None:
        """Clear the result display."""
        # Clear header labels
        self.event_time_label.setText("None")
        self.strategy_label.setText("None")
        self.result_count_label.setText("0")
        
        # Clear image view
        self.result_view.set_image_and_results(
            np.zeros((300, 400, 3), dtype=np.uint8),  # Black image
            [],
            "template"
        )
        
        # Clear results table
        self.results_table.setRowCount(0)
        
        # Disable navigation buttons
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        # Clear current index
        if hasattr(self, '_current_index'):
            del self._current_index 