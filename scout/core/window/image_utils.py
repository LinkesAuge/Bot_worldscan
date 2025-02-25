"""
Image Utilities

This module provides utility functions for working with images in the Qt-based
window capture implementation, especially for converting between QImage and numpy arrays.
"""

import logging
import numpy as np
from typing import Optional

from PyQt6.QtGui import QImage
from PyQt6.QtCore import Qt, QSize

# Set up logging
logger = logging.getLogger(__name__)


def qimage_to_numpy(image: QImage) -> Optional[np.ndarray]:
    """
    Convert a QImage to a numpy array in BGR format (for OpenCV compatibility).
    
    Args:
        image: QImage to convert
        
    Returns:
        np.ndarray: Numpy array in BGR format, or None if conversion failed
    """
    if image is None or image.isNull():
        logger.error("Cannot convert null QImage to numpy array")
        return None
        
    try:
        # Convert to RGB32 format first for consistent handling
        if image.format() != QImage.Format.Format_RGB32:
            image = image.convertToFormat(QImage.Format.Format_RGB32)
            
        # Get image dimensions
        width = image.width()
        height = image.height()
        
        # Create numpy array from image data
        ptr = image.bits()
        ptr.setsize(height * width * 4)  # 4 bytes per pixel (RGBA)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        
        # Convert from RGBA to BGR (OpenCV format)
        bgr_array = arr[:, :, 2::-1].copy()  # Copy to ensure memory continuity
        
        logger.debug(f"Converted QImage {width}x{height} to numpy array")
        return bgr_array
        
    except Exception as e:
        logger.error(f"Error converting QImage to numpy array: {e}")
        return None


def numpy_to_qimage(array: np.ndarray) -> Optional[QImage]:
    """
    Convert a numpy array to a QImage.
    
    Args:
        array: Numpy array (BGR format expected for best results)
        
    Returns:
        QImage: Converted image, or None if conversion failed
    """
    if array is None or not isinstance(array, np.ndarray):
        logger.error("Invalid numpy array for conversion to QImage")
        return None
        
    try:
        height, width = array.shape[:2]
        
        # Handle different array formats
        if len(array.shape) == 2:  # Grayscale
            # Create a grayscale QImage
            bytes_per_line = width
            return QImage(array.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
            
        elif len(array.shape) == 3:
            if array.shape[2] == 3:  # BGR
                # Convert BGR to RGB
                rgb = array[:, :, ::-1].copy()  # Copy to ensure memory continuity
                bytes_per_line = width * 3
                return QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                
            elif array.shape[2] == 4:  # BGRA
                # Convert BGRA to RGBA
                rgba = array[:, :, [2, 1, 0, 3]].copy()  # Copy to ensure memory continuity
                bytes_per_line = width * 4
                return QImage(rgba.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
                
        logger.debug(f"Converted numpy array {width}x{height} to QImage")
        return None  # Unsupported format
        
    except Exception as e:
        logger.error(f"Error converting numpy array to QImage: {e}")
        return None


def resize_image(image: QImage, max_width: int = 1920, max_height: int = 1080) -> QImage:
    """
    Resize an image if it exceeds the specified dimensions, preserving aspect ratio.
    
    Args:
        image: QImage to resize
        max_width: Maximum width
        max_height: Maximum height
        
    Returns:
        QImage: Resized image (or original if no resizing needed)
    """
    if image is None or image.isNull():
        return image
        
    width = image.width()
    height = image.height()
    
    # Check if resize is needed
    if width <= max_width and height <= max_height:
        return image
        
    try:
        # Calculate new size preserving aspect ratio
        aspect_ratio = width / height
        
        if width > height:
            new_width = max_width
            new_height = int(new_width / aspect_ratio)
            if new_height > max_height:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)
        else:
            new_height = max_height
            new_width = int(new_height * aspect_ratio)
            if new_width > max_width:
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
                
        # Resize the image
        resized = image.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio, 
                              Qt.TransformationMode.SmoothTransformation)
                              
        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        return resized
        
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        return image 