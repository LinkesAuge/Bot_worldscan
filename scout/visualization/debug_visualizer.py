from typing import Dict, Any, Optional, List
import logging
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QRect, QPoint
from PyQt6.QtGui import QImage, QPixmap

from ..core.window_tracker import WindowTracker
from ..core.coordinate_manager import CoordinateManager, CoordinateSpace
from ..capture.capture_manager import CaptureManager
from ..capture.pattern_matcher import PatternMatcher, MatchResult
from ..capture.ocr_processor import OCRProcessor

logger = logging.getLogger(__name__)

class CoordinateVisualizer:
    """
    Visualizes coordinate system state.
    
    This class provides:
    - Window boundary visualization
    - Client area visualization
    - Pattern matching region visualization
    - OCR region visualization
    """
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        coordinate_manager: CoordinateManager
    ) -> None:
        """
        Initialize coordinate visualizer.
        
        Args:
            window_tracker: Window tracker instance
            coordinate_manager: Coordinate manager instance
        """
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        
        # Colors for different elements (in BGR format)
        self.colors = {
            "window": (0, 255, 0),    # Green
            "client": (0, 0, 255),    # Red 
            "pattern": (255, 0, 0),   # Blue
            "ocr": (0, 255, 255)      # Yellow
        }
        
        logger.debug("Coordinate visualizer initialized")
        
    def draw_overlay(self, image: np.ndarray) -> np.ndarray:
        """
        Draw coordinate system overlay.
        
        Args:
            image: Base image to draw on (BGR format)
            
        Returns:
            Image with overlay
        """
        try:
            # Get window geometry
            window_rect = self.window_tracker.get_window_rect()
            client_rect = self.window_tracker.get_client_rect()
            
            # Return unmodified copy if no window or client rect
            if not window_rect or not client_rect:
                return image.copy()
                
            # Create copy for drawing
            overlay = image.copy()
            
            # Draw window boundary
            self._draw_rect(
                overlay,
                window_rect,
                self.colors["window"],
                "Window"
            )
            
            # Draw client area
            self._draw_rect(
                overlay,
                client_rect,
                self.colors["client"],
                "Client"
            )
            
            # Draw regions
            for name, region in self.coordinate_manager.regions.items():
                rect = region["rect"]
                space = region["space"]
                
                # Transform to screen space if needed
                if space != CoordinateSpace.SCREEN:
                    rect = self.coordinate_manager.get_region(
                        name,
                        CoordinateSpace.SCREEN
                    )
                    if not rect:
                        continue
                        
                # Choose color based on region type
                color = (
                    self.colors["ocr"]
                    if "ocr" in name.lower()
                    else self.colors["pattern"]
                )
                
                self._draw_rect(overlay, rect, color, name)
                
            return overlay
            
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}")
            return image.copy()  # Return unmodified copy on error
            
    def _draw_rect(
        self,
        image: np.ndarray,
        rect: QRect,
        color: tuple,
        label: str
    ) -> None:
        """Draw rectangle with label."""
        try:
            # Draw rectangle
            cv2.rectangle(
                image,
                (rect.left(), rect.top()),
                (rect.right(), rect.bottom()),
                color,
                2
            )
            
            # Draw label
            cv2.putText(
                image,
                label,
                (rect.left(), rect.top() - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1
            )
            
        except Exception as e:
            logger.error(f"Error drawing rectangle: {e}")

class DebugVisualizer(QObject):
    """
    Handles debug visualization and logging.
    
    This class provides:
    - Coordinate system visualization
    - Capture preview
    - OCR region preview
    - Pattern match visualization
    - Performance metrics display
    """
    
    # Signals
    preview_updated = pyqtSignal(QImage)  # Preview image
    metrics_updated = pyqtSignal(dict)    # Debug metrics
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        coordinate_manager: CoordinateManager,
        capture_manager: CaptureManager,
        pattern_matcher: PatternMatcher,
        ocr_processor: OCRProcessor,
        update_interval: int = 1000
    ) -> None:
        """Initialize debug visualizer."""
        super().__init__()
        
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        self.capture_manager = capture_manager
        self.pattern_matcher = pattern_matcher
        self.ocr_processor = ocr_processor
        
        # Initialize state
        self.last_matches = []  # Store matches
        self.last_ocr_text = {}  # Store OCR results
        
        # Create coordinate visualizer
        self.coord_vis = CoordinateVisualizer(
            window_tracker,
            coordinate_manager
        )
        
        # Create update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.setInterval(update_interval)
        
        # Connect signals
        self.capture_manager.capture_complete.connect(
            self._on_capture_complete
        )
        self.pattern_matcher.match_found.connect(
            self._on_match_found
        )
        self.ocr_processor.text_found.connect(
            self._on_text_found
        )
        
        # Start by default
        self.start()
        
        logger.debug("Debug visualizer initialized")
        
    def start(self) -> None:
        """Start preview updates."""
        if not self.update_timer.isActive():
            self.update_timer.start()
            logger.debug("Debug visualization started")
        
    def stop(self) -> None:
        """Stop preview updates."""
        if self.update_timer.isActive():
            self.update_timer.stop()
            logger.debug("Debug visualization stopped")
        
    def _update_preview(self) -> None:
        """Update preview display."""
        try:
            # Capture window
            image = self.capture_manager.capture_window(save_debug=False)
            if image is None:
                logger.error("Failed to capture window for preview")
                return
                
            # Create copy for drawing
            debug_img = image.copy()
            
            # Draw coordinate system if enabled
            if self.coord_vis:
                debug_img = self.coord_vis.draw_overlay(debug_img)
            
            # Draw pattern matches
            if self.last_matches:
                for match in self.last_matches:
                    # Draw rectangle
                    pt1 = (
                        int(match.rect.left() * self.capture_manager.dpi_scale),
                        int(match.rect.top() * self.capture_manager.dpi_scale)
                    )
                    pt2 = (
                        int(match.rect.right() * self.capture_manager.dpi_scale),
                        int(match.rect.bottom() * self.capture_manager.dpi_scale)
                    )
                    cv2.rectangle(
                        debug_img,
                        pt1,
                        pt2,
                        (0, 255, 0),  # BGR green
                        2
                    )
                    
                    # Draw crosshair at center
                    center = (
                        int(match.position.x() * self.capture_manager.dpi_scale),
                        int(match.position.y() * self.capture_manager.dpi_scale)
                    )
                    size = 10
                    cv2.line(
                        debug_img,
                        (center[0] - size, center[1]),
                        (center[0] + size, center[1]),
                        (0, 0, 255),  # BGR red
                        2
                    )
                    cv2.line(
                        debug_img,
                        (center[0], center[1] - size),
                        (center[0], center[1] + size),
                        (0, 0, 255),  # BGR red
                        2
                    )
                    
                    # Draw label
                    label = f"{match.template_name} ({match.confidence:.2f})"
                    label_pt = (
                        pt1[0],
                        max(0, pt1[1] - 10)  # Ensure label is in image
                    )
                    cv2.putText(
                        debug_img,
                        label,
                        label_pt,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),  # BGR green
                        1
                    )
            
            # Save debug image
            cv2.imwrite("debug_screenshots/preview.png", debug_img)
            
            # Convert to QImage for display
            height, width = debug_img.shape[:2]
            bytes_per_line = 3 * width
            image = QImage(
                debug_img.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            ).rgbSwapped()  # Convert BGR to RGB
            
            # Emit preview update
            self.preview_updated.emit(image)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            
    def _update_metrics(self) -> None:
        """Update debug metrics."""
        try:
            metrics = {
                "window": self.window_tracker.get_debug_info(),
                "capture": self.capture_manager.get_debug_info(),
                "pattern": {
                    "templates": self.pattern_matcher.get_template_info(),
                    "last_matches": len(self.last_matches)
                },
                "ocr": self.ocr_processor.get_debug_info()
            }
            
            self.metrics_updated.emit(metrics)
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _on_capture_complete(
        self,
        image: np.ndarray,
        capture_type: str
    ) -> None:
        """Handle capture complete event."""
        self._update_preview()
        
    def _on_match_found(
        self,
        template: str,
        confidence: float,
        position: QPoint
    ) -> None:
        """Handle match found event."""
        try:
            # Create match result
            match = MatchResult(
                template_name=template,
                confidence=confidence,
                position=position,
                rect=QRect(
                    position.x() - 16,  # Assuming 32x32 template
                    position.y() - 16,
                    32,
                    32
                )
            )
            
            # Update matches list
            self.last_matches = [match]  # Keep only latest match
            
            # Update preview
            self._update_preview()
            
        except Exception as e:
            logger.error(f"Error handling match: {e}")
        
    def _on_text_found(self, region: str, text: str) -> None:
        """Handle OCR text event."""
        self.last_ocr_text[region] = text
        self._update_preview() 