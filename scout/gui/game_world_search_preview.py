"""
Game World Search Preview Widget

This module provides a widget for displaying live preview of the search process.
"""

from typing import Optional, Union
import logging
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QSize

logger = logging.getLogger(__name__)

class SearchPreviewWidget(QWidget):
    """Widget for displaying live preview of the search process."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the preview widget."""
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 1px solid #d0d0d0; }")
        layout.addWidget(self.preview_label)
        
        # Store current preview
        self.current_preview: Optional[QImage] = None
        
    def set_preview(self, image: Union[QImage, np.ndarray]) -> None:
        """
        Set the preview image.
        
        Args:
            image: QImage or OpenCV image (numpy array) to display
        """
        try:
            if image is None:
                return
                
            # Convert OpenCV image to QImage if needed
            if isinstance(image, np.ndarray):
                # Convert BGR to RGB if image has 3 channels
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                height, width = image.shape[:2]
                bytes_per_line = 3 * width
                image = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Store current preview
            self.current_preview = image
            
            # Scale image to fit widget while maintaining aspect ratio
            scaled_image = image.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Convert to pixmap and display
            pixmap = QPixmap.fromImage(scaled_image)
            self.preview_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Error setting preview: {e}")
            
    def clear_preview(self) -> None:
        """Clear the current preview."""
        self.current_preview = None
        self.preview_label.clear()
        
    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        
        # Rescale current preview if available
        if self.current_preview is not None:
            self.set_preview(self.current_preview) 