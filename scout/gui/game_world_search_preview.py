"""
Game World Search Preview Widget

This module provides a widget for displaying search result previews.
It shows:
- Screenshot of the found template
- Match region highlighting
- Zoom controls
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
    """Custom label for displaying images with zoom."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the image label.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumSize(1, 1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pixmap = None
        self._zoom = 1.0
        
    def setPixmap(self, pixmap: QPixmap):
        """
        Set the pixmap to display.
        
        Args:
            pixmap: The pixmap to display
        """
        self._pixmap = pixmap
        self._update_pixmap()
        
    def _update_pixmap(self):
        """Update the displayed pixmap with current zoom."""
        if not self._pixmap:
            return
            
        # Calculate size
        size = self._pixmap.size()
        scaled_size = QSize(
            int(size.width() * self._zoom),
            int(size.height() * self._zoom)
        )
        
        # Scale pixmap
        scaled_pixmap = self._pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        super().setPixmap(scaled_pixmap)
        
    def set_zoom(self, zoom: float):
        """
        Set the zoom level.
        
        Args:
            zoom: Zoom level (1.0 = 100%)
        """
        self._zoom = max(0.1, min(5.0, zoom))
        self._update_pixmap()

class SearchPreviewWidget(QWidget):
    """
    Widget for displaying search result previews.
    
    This widget shows:
    - Screenshot of the found template
    - Match region highlighting
    - Zoom controls
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the search preview widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create UI
        self._create_ui()
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Image label
        self.image_label = ImageLabel()
        scroll_area.setWidget(self.image_label)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(lambda: self._adjust_zoom(-0.1))
        zoom_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(lambda: self._adjust_zoom(0.1))
        zoom_layout.addWidget(self.zoom_in_btn)
        
        self.reset_zoom_btn = QPushButton("Reset")
        self.reset_zoom_btn.clicked.connect(self._reset_zoom)
        zoom_layout.addWidget(self.reset_zoom_btn)
        
        # Add stretch on both sides of zoom controls
        zoom_layout.insertStretch(0)
        zoom_layout.addStretch()
        
        # Add widgets to layout
        layout.addWidget(scroll_area)
        layout.addLayout(zoom_layout)
        
    def set_image(self, image_path: str):
        """
        Set the image to display.
        
        Args:
            image_path: Path to the image file
        """
        try:
            # Load image
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                logger.error(f"Failed to load image: {image_path}")
                return
                
            # Set image
            self.image_label.setPixmap(pixmap)
            self._reset_zoom()
            
        except Exception as e:
            logger.error(f"Error setting image: {e}")
            
    def _adjust_zoom(self, delta: float):
        """
        Adjust the zoom level.
        
        Args:
            delta: Amount to adjust zoom by
        """
        current_zoom = float(self.zoom_label.text().strip('%')) / 100
        new_zoom = current_zoom + delta
        self._set_zoom(new_zoom)
        
    def _set_zoom(self, zoom: float):
        """
        Set the zoom level.
        
        Args:
            zoom: Zoom level (1.0 = 100%)
        """
        # Update image
        self.image_label.set_zoom(zoom)
        
        # Update label
        self.zoom_label.setText(f"{int(zoom * 100)}%")
        
    def _reset_zoom(self):
        """Reset zoom to 100%."""
        self._set_zoom(1.0)

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