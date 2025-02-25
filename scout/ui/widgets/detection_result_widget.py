"""
Detection Result Widget

This module provides a widget for displaying detection results with visualizations.
It renders the detection results on an image and provides interaction for selecting
and analyzing individual detections.
"""

import logging
from typing import Dict, List, Optional, Any
import cv2
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QSplitter,
    QHeaderView, QComboBox, QMessageBox
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont,
    QMouseEvent, QResizeEvent, QPaintEvent
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint

from scout.core.window.window_service_interface import WindowServiceInterface

# Set up logging
logger = logging.getLogger(__name__)

class ResultImageView(QWidget):
    """
    Widget for displaying an image with detection results.
    
    This widget:
    - Renders the screenshot with detection results visualizations
    - Handles zooming and panning
    - Provides selection of individual detections
    """
    
    # Signals
    result_selected = pyqtSignal(dict)  # Selected result data
    
    def __init__(self):
        """Initialize the result image view."""
        super().__init__()
        
        # Initialize state
        self._image = None  # Original image
        self._display_image = None  # Image with detection visualization
        self._scale = 1.0  # Zoom scale
        self._offset = QPoint(0, 0)  # Pan offset
        self._results = []  # Detection results
        self._result_rects = []  # QRect for each result (scaled)
        self._selected_index = -1  # Selected result index
        self._current_strategy = "template"  # Current detection strategy
        
        # Configure widget
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # To receive key events
        self.setMouseTracking(True)  # To receive mouse move events
        
        # Configure colors
        self._colors = {
            "template": QColor(0, 255, 0, 128),  # Semi-transparent green
            "ocr": QColor(255, 255, 0, 128),  # Semi-transparent yellow
            "yolo": QColor(0, 0, 255, 128),  # Semi-transparent blue
            "selection": QColor(255, 0, 0, 180),  # Semi-transparent red
            "text": QColor(255, 255, 255)  # White text
        }
    
    def set_image_and_results(self, image: np.ndarray, results: List[Dict[str, Any]], strategy: str) -> None:
        """
        Set the image and detection results.
        
        Args:
            image: Image as numpy array (BGR format)
            results: List of detection results
            strategy: Detection strategy used
        """
        if image is None or len(image.shape) < 2:
            logger.warning("Invalid image provided to ResultImageView")
            return
        
        # Store original image and results
        self._image = image.copy()
        self._results = results
        self._current_strategy = strategy
        self._selected_index = -1
        
        # Reset view parameters
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        
        # Create display image with visualizations
        self._create_display_image()
        
        # Force redraw
        self.update()
    
    def _create_display_image(self) -> None:
        """Create the display image with detection visualizations."""
        if self._image is None:
            return
        
        # Make a copy of the original image for drawing
        display = self._image.copy()
        
        # Convert from BGR to RGB for Qt
        if display.shape[2] == 3:
            display = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        
        # Calculate result rectangles at original scale
        self._result_rects = []
        
        # Draw each result
        for i, result in enumerate(self._results):
            # Get color for current strategy
            color = self._colors.get(self._current_strategy, QColor(0, 255, 0, 128))
            
            # Get opencv color (BGR)
            cv_color = (
                color.blue(),
                color.green(),
                color.red()
            )
            
            # Get rectangle coordinates
            x = result.get('x', 0)
            y = result.get('y', 0)
            
            width = result.get('width', 0)
            height = result.get('height', 0)
            
            # Store rectangle for later hit testing
            self._result_rects.append(QRect(x, y, width, height))
            
            # Draw rectangle
            cv2.rectangle(
                display,
                (x, y),
                (x + width, y + height),
                cv_color,
                2
            )
            
            # Add text based on result type
            text = ""
            if 'template_name' in result:
                text = f"{result['template_name']} ({result.get('confidence', 0):.2f})"
            elif 'text' in result:
                text = f"{result['text']} ({result.get('confidence', 0):.2f})"
            elif 'class_name' in result:
                text = f"{result['class_name']} ({result.get('confidence', 0):.2f})"
            
            if text:
                # Draw text background
                cv2.rectangle(
                    display,
                    (x, y - 20),
                    (x + width, y),
                    (0, 0, 0),
                    -1
                )
                
                # Draw text
                cv2.putText(
                    display,
                    text,
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )
        
        # Convert to QImage
        height, width, channels = display.shape
        bytes_per_line = channels * width
        
        self._display_image = QImage(
            display.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Handle paint event.
        
        Args:
            event: Paint event
        """
        if self._display_image is None:
            # Draw placeholder if no image is available
            painter = QPainter(self)
            painter.fillRect(self.rect(), Qt.GlobalColor.darkGray)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No detection results available"
            )
            return
        
        # Start painter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        
        # Calculate scaled image size
        scaled_width = int(self._display_image.width() * self._scale)
        scaled_height = int(self._display_image.height() * self._scale)
        
        # Calculate centered position
        x = (self.width() - scaled_width) // 2 + self._offset.x()
        y = (self.height() - scaled_height) // 2 + self._offset.y()
        
        # Draw image
        painter.drawImage(
            QRect(x, y, scaled_width, scaled_height),
            self._display_image
        )
        
        # Draw selection highlight if a result is selected
        if self._selected_index >= 0 and self._selected_index < len(self._result_rects):
            # Get selected rectangle
            rect = self._result_rects[self._selected_index]
            
            # Scale and position rectangle
            scaled_rect = QRect(
                int(rect.x() * self._scale) + x,
                int(rect.y() * self._scale) + y,
                int(rect.width() * self._scale),
                int(rect.height() * self._scale)
            )
            
            # Draw selection rectangle
            painter.setPen(QPen(self._colors["selection"], 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(scaled_rect)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press event.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is on a result
            self._select_result_at(event.pos())
        
        # Store position for panning
        self._last_mouse_pos = event.pos()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move event.
        
        Args:
            event: Mouse event
        """
        if event.buttons() & Qt.MouseButton.RightButton:
            # Pan image
            delta = event.pos() - self._last_mouse_pos
            self._offset += delta
            self._last_mouse_pos = event.pos()
            self.update()
    
    def wheelEvent(self, event) -> None:
        """
        Handle mouse wheel event for zooming.
        
        Args:
            event: Wheel event
        """
        # Calculate zoom factor
        zoom_factor = 1.1
        
        # Apply zoom
        if event.angleDelta().y() > 0:
            # Zoom in
            self._scale *= zoom_factor
        else:
            # Zoom out
            self._scale /= zoom_factor
        
        # Limit scale
        self._scale = max(0.1, min(5.0, self._scale))
        
        # Redraw
        self.update()
    
    def _select_result_at(self, pos: QPoint) -> None:
        """
        Select the result at the given position.
        
        Args:
            pos: Position to check
        """
        if self._display_image is None or not self._result_rects:
            return
        
        # Calculate image position and scale
        scaled_width = int(self._display_image.width() * self._scale)
        scaled_height = int(self._display_image.height() * self._scale)
        
        x = (self.width() - scaled_width) // 2 + self._offset.x()
        y = (self.height() - scaled_height) // 2 + self._offset.y()
        
        # Check each result
        for i, rect in enumerate(self._result_rects):
            # Scale and position rectangle
            scaled_rect = QRect(
                int(rect.x() * self._scale) + x,
                int(rect.y() * self._scale) + y,
                int(rect.width() * self._scale),
                int(rect.height() * self._scale)
            )
            
            # Check if point is inside
            if scaled_rect.contains(pos):
                # Select this result
                self._selected_index = i
                
                # Emit signal
                self.result_selected.emit(self._results[i])
                
                # Redraw
                self.update()
                return
        
        # No result found, clear selection
        self._selected_index = -1
        self.update()
    
    def keyPressEvent(self, event) -> None:
        """
        Handle key press event.
        
        Args:
            event: Key event
        """
        if event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            # Zoom in
            self._scale *= 1.1
            self.update()
            
        elif event.key() == Qt.Key.Key_Minus:
            # Zoom out
            self._scale /= 1.1
            self._scale = max(0.1, self._scale)
            self.update()
            
        elif event.key() == Qt.Key.Key_0:
            # Reset zoom
            self._scale = 1.0
            self._offset = QPoint(0, 0)
            self.update()
            
        elif event.key() == Qt.Key.Key_Left:
            # Pan left
            self._offset.setX(self._offset.x() + 10)
            self.update()
            
        elif event.key() == Qt.Key.Key_Right:
            # Pan right
            self._offset.setX(self._offset.x() - 10)
            self.update()
            
        elif event.key() == Qt.Key.Key_Up:
            # Pan up
            self._offset.setY(self._offset.y() + 10)
            self.update()
            
        elif event.key() == Qt.Key.Key_Down:
            # Pan down
            self._offset.setY(self._offset.y() - 10)
            self.update()
        
        else:
            # Let parent handle other keys
            super().keyPressEvent(event)

class DetectionResultWidget(QWidget):
    """
    Widget for displaying detection results.
    
    This widget:
    - Shows the screenshot with detection visualizations
    - Lists detection results in a table
    - Provides tools for analyzing and interacting with results
    """
    
    # Signals
    result_selected = pyqtSignal(dict)  # Selected result data
    
    def __init__(self, window_service: WindowServiceInterface):
        """
        Initialize the detection result widget.
        
        Args:
            window_service: Service for window management
        """
        super().__init__()
        
        self.window_service = window_service
        
        # Initialize state
        self._current_image = None
        self._current_results = []
        self._current_strategy = "template"
        
        # Create UI layout
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Detection result widget initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Image view
        self.image_view = ResultImageView()
        splitter.addWidget(self.image_view)
        
        # Bottom section - Results table
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        
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
        
        # Actions
        actions_layout = QHBoxLayout()
        
        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        actions_layout.addWidget(self.export_btn)
        
        # Click action button
        self.click_btn = QPushButton("Click at Selection")
        self.click_btn.setEnabled(False)
        actions_layout.addWidget(self.click_btn)
        
        results_layout.addLayout(actions_layout)
        
        splitter.addWidget(results_frame)
        
        # Set initial splitter sizes (70% image, 30% table)
        splitter.setSizes([700, 300])
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Image view
        self.image_view.result_selected.connect(self._on_result_selected_in_image)
        
        # Results table
        self.results_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        
        # Buttons
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.click_btn.clicked.connect(self._on_click_clicked)
    
    def display_results(self, results: List[Dict[str, Any]], strategy: str) -> None:
        """
        Display detection results.
        
        Args:
            results: List of detection results
            strategy: Detection strategy used
        """
        # Clear current results
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.click_btn.setEnabled(False)
        
        # Store results
        self._current_results = results
        self._current_strategy = strategy
        
        # Update export button state
        self.export_btn.setEnabled(len(results) > 0)
        
        if not results:
            logger.info("No detection results to display")
            
            # Clear image view
            self.image_view.set_image_and_results(
                np.zeros((300, 400, 3), dtype=np.uint8),  # Black image
                [],
                strategy
            )
            return
        
        # Get screenshot
        screenshot = self.window_service.capture_screenshot()
        if screenshot is None:
            logger.error("Failed to capture screenshot for result display")
            
            # Create empty image
            screenshot = np.zeros((300, 400, 3), dtype=np.uint8)  # Black image
        
        # Store current image
        self._current_image = screenshot
        
        # Update image view
        self.image_view.set_image_and_results(screenshot, results, strategy)
        
        # Populate results table
        self._populate_results_table(results, strategy)
        
        logger.info(f"Displayed {len(results)} detection results")
    
    def _populate_results_table(self, results: List[Dict[str, Any]], strategy: str) -> None:
        """
        Populate the results table.
        
        Args:
            results: List of detection results
            strategy: Detection strategy used
        """
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
    
    def _on_result_selected_in_image(self, result: Dict[str, Any]) -> None:
        """
        Handle result selection in image view.
        
        Args:
            result: Selected result data
        """
        # Find the result in the table
        for i, current_result in enumerate(self._current_results):
            if current_result is result:
                # Select the corresponding row in the table
                self.results_table.selectRow(i)
                break
        
        # Enable click button
        self.click_btn.setEnabled(True)
        
        # Emit signal
        self.result_selected.emit(result)
    
    def _on_table_selection_changed(self) -> None:
        """Handle selection change in results table."""
        # Get selected row
        selected_rows = self.results_table.selectedIndexes()
        if not selected_rows:
            self.click_btn.setEnabled(False)
            return
        
        # Get the row of the first selected cell
        row = selected_rows[0].row()
        
        # Select the result in the image view
        if 0 <= row < len(self._current_results):
            # This will indirectly call _on_result_selected_in_image
            # but we need to update the internal selection in the image view
            self.image_view._selected_index = row
            self.image_view.update()
            
            # Enable click button
            self.click_btn.setEnabled(True)
            
            # Emit signal
            self.result_selected.emit(self._current_results[row])
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        if not self._current_results:
            return
        
        # Create export options
        export_options = QComboBox()
        export_options.addItem("CSV", "csv")
        export_options.addItem("JSON", "json")
        export_options.addItem("Image with Annotations", "image")
        
        # Create message box with options
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Export Results")
        msg_box.setText("Choose export format:")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Add options to layout
        layout = msg_box.layout()
        layout.addWidget(export_options, 1, 1)
        
        # Add buttons
        msg_box.addButton("Export", QMessageBox.ButtonRole.AcceptRole)
        msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        # Show dialog
        result = msg_box.exec()
        
        if result == QMessageBox.StandardButton.AcceptRole:
            export_type = export_options.currentData()
            self._export_results(export_type)
    
    def _export_results(self, export_type: str) -> None:
        """
        Export results to the specified format.
        
        Args:
            export_type: Export format (csv, json, image)
        """
        # Implement export functionality
        # TODO: Implement export functionality
        logger.info(f"Export results as {export_type} not yet implemented")
        
        QMessageBox.information(
            self,
            "Export",
            f"Export as {export_type} not yet implemented."
        )
    
    def _on_click_clicked(self) -> None:
        """Handle click at selection button click."""
        # Get selected row
        selected_rows = self.results_table.selectedIndexes()
        if not selected_rows:
            return
        
        # Get the row of the first selected cell
        row = selected_rows[0].row()
        
        # Get the result
        if 0 <= row < len(self._current_results):
            result = self._current_results[row]
            
            # Calculate center position
            x = result.get('x', 0) + result.get('width', 0) // 2
            y = result.get('y', 0) + result.get('height', 0) // 2
            
            # TODO: Implement actual click using a service
            logger.info(f"Clicking at position ({x}, {y})")
            
            QMessageBox.information(
                self,
                "Click",
                f"Click at position ({x}, {y}) is not yet implemented."
            ) 