"""
Game World Search Preview

This module provides the widget for previewing search results with screenshots.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from scout.game_world_search import SearchResult

logger = logging.getLogger(__name__)

class ImageLabel(QLabel):
    """
    Label for displaying images with overlays.
    
    This label can display an image with optional overlays for
    highlighting search results.
    """
    
    def __init__(self):
        """Initialize the image label."""
        super().__init__()
        
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.overlay_enabled = True
        self.overlay_data = []
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def set_image(self, image_path: str):
        """
        Set the image to display.
        
        Args:
            image_path: Path to the image file
        """
        try:
            # Load image
            self.original_pixmap = QPixmap(image_path)
            
            if self.original_pixmap.isNull():
                logger.error(f"Failed to load image: {image_path}")
                self.setText("Failed to load image")
                return
                
            # Scale and display
            self._update_display()
            
            logger.info(f"Loaded image: {image_path}")
            
        except Exception as e:
            logger.error(f"Error loading image: {e}", exc_info=True)
            self.setText(f"Error: {str(e)}")
            
    def set_image_from_cv(self, cv_image):
        """
        Set the image from an OpenCV image.
        
        Args:
            cv_image: OpenCV image (numpy array)
        """
        try:
            # Convert OpenCV image to QPixmap
            height, width, channels = cv_image.shape
            bytes_per_line = channels * width
            
            # Convert BGR to RGB
            cv_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
            # Create QImage and QPixmap
            q_image = QImage(cv_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            self.original_pixmap = QPixmap.fromImage(q_image)
            
            # Scale and display
            self._update_display()
            
            logger.info("Loaded image from OpenCV")
            
        except Exception as e:
            logger.error(f"Error loading image from OpenCV: {e}", exc_info=True)
            self.setText(f"Error: {str(e)}")
            
    def set_overlay_data(self, data: List[Dict[str, Any]]):
        """
        Set overlay data for highlighting regions.
        
        Args:
            data: List of overlay data dictionaries with keys:
                 - 'type': Type of overlay ('rect', 'point', 'text')
                 - 'x', 'y': Position
                 - 'width', 'height': Size (for 'rect')
                 - 'color': Color as (r, g, b) tuple
                 - 'text': Text to display (for 'text')
        """
        self.overlay_data = data
        self._update_display()
        
    def set_overlay_enabled(self, enabled: bool):
        """
        Enable or disable overlays.
        
        Args:
            enabled: Whether overlays should be displayed
        """
        self.overlay_enabled = enabled
        self._update_display()
        
    def _update_display(self):
        """Update the displayed image with overlays."""
        if not self.original_pixmap:
            return
            
        # Scale pixmap to fit label
        self.scaled_pixmap = self.original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # If overlays are disabled or no overlay data, just display the scaled pixmap
        if not self.overlay_enabled or not self.overlay_data:
            self.setPixmap(self.scaled_pixmap)
            return
            
        # Create a copy of the scaled pixmap to draw on
        pixmap_with_overlay = self.scaled_pixmap.copy()
        painter = QPainter(pixmap_with_overlay)
        
        # Calculate scale factor between original and scaled pixmap
        scale_x = self.scaled_pixmap.width() / self.original_pixmap.width()
        scale_y = self.scaled_pixmap.height() / self.original_pixmap.height()
        
        # Draw overlays
        for item in self.overlay_data:
            overlay_type = item.get('type', 'rect')
            x = int(item.get('x', 0) * scale_x)
            y = int(item.get('y', 0) * scale_y)
            color = item.get('color', (0, 255, 0))
            
            # Set pen
            pen = QPen(QColor(*color))
            pen.setWidth(2)
            painter.setPen(pen)
            
            if overlay_type == 'rect':
                width = int(item.get('width', 10) * scale_x)
                height = int(item.get('height', 10) * scale_y)
                painter.drawRect(x, y, width, height)
                
            elif overlay_type == 'point':
                size = item.get('size', 5)
                painter.drawEllipse(x - size, y - size, size * 2, size * 2)
                
            elif overlay_type == 'text':
                text = item.get('text', '')
                painter.drawText(x, y, text)
                
        painter.end()
        
        # Display the pixmap with overlays
        self.setPixmap(pixmap_with_overlay)
        
    def resizeEvent(self, event):
        """Handle resize events to update the scaled image."""
        super().resizeEvent(event)
        self._update_display()


class SearchPreviewWidget(QWidget):
    """
    Widget for previewing search results.
    
    This widget provides:
    - Display of result screenshots
    - Overlay of match locations
    - Controls for overlay display
    """
    
    def __init__(self):
        """Initialize the search preview widget."""
        super().__init__()
        
        self._create_ui()
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create image display
        self.image_label = ImageLabel()
        
        # Create scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Create controls
        controls_layout = QHBoxLayout()
        
        # Overlay toggle
        self.overlay_check = QCheckBox("Show Overlays")
        self.overlay_check.setChecked(True)
        self.overlay_check.stateChanged.connect(self._on_overlay_toggled)
        controls_layout.addWidget(self.overlay_check)
        
        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QHBoxLayout()
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(self._zoom_fit)
        zoom_layout.addWidget(self.zoom_fit_btn)
        
        zoom_group.setLayout(zoom_layout)
        controls_layout.addWidget(zoom_group)
        
        layout.addLayout(controls_layout)
        
        # Set initial state
        self.current_zoom = 1.0
        self.current_image_path = None
        
    def set_image(self, image_path: str):
        """
        Set the image to display.
        
        Args:
            image_path: Path to the image file
        """
        self.current_image_path = image_path
        self.image_label.set_image(image_path)
        
    def set_image_from_cv(self, cv_image):
        """
        Set the image from an OpenCV image.
        
        Args:
            cv_image: OpenCV image (numpy array)
        """
        self.current_image_path = None
        self.image_label.set_image_from_cv(cv_image)
        
    def set_result(self, result: SearchResult):
        """
        Set the search result to display.
        
        Args:
            result: Search result to display
        """
        if not result.screenshot_path:
            return
            
        # Load the image
        self.set_image(result.screenshot_path)
        
        # Create overlay data
        overlay_data = []
        
        if result.success and result.screen_position:
            x, y = result.screen_position
            
            # Add rectangle around match
            if hasattr(result, 'match_width') and hasattr(result, 'match_height'):
                width = result.match_width
                height = result.match_height
            else:
                # Default size if not available
                width = 50
                height = 50
                
            overlay_data.append({
                'type': 'rect',
                'x': x - width // 2,
                'y': y - height // 2,
                'width': width,
                'height': height,
                'color': (0, 255, 0)  # Green
            })
            
            # Add point at match center
            overlay_data.append({
                'type': 'point',
                'x': x,
                'y': y,
                'size': 5,
                'color': (255, 0, 0)  # Red
            })
            
            # Add text with template name and confidence
            overlay_data.append({
                'type': 'text',
                'x': x + width // 2 + 5,
                'y': y,
                'text': f"{result.template_name} ({result.confidence:.2f})",
                'color': (0, 0, 255)  # Blue
            })
            
        # Set overlay data
        self.image_label.set_overlay_data(overlay_data)
        
    def _on_overlay_toggled(self, state):
        """
        Handle overlay toggle.
        
        Args:
            state: Checkbox state
        """
        self.image_label.set_overlay_enabled(state == Qt.CheckState.Checked)
        
    def _zoom_in(self):
        """Zoom in on the image."""
        self.current_zoom *= 1.2
        self._apply_zoom()
        
    def _zoom_out(self):
        """Zoom out on the image."""
        self.current_zoom /= 1.2
        self._apply_zoom()
        
    def _zoom_fit(self):
        """Reset zoom to fit the image to the view."""
        self.current_zoom = 1.0
        self._apply_zoom()
        
    def _apply_zoom(self):
        """Apply the current zoom level."""
        # For now, just reload the image
        # In a more advanced implementation, we would scale the image
        if self.current_image_path:
            self.set_image(self.current_image_path) 