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
        """
        Initialize debug visualizer.
        
        Args:
            window_tracker: Window tracker instance
            coordinate_manager: Coordinate manager instance
            capture_manager: Capture manager instance
            pattern_matcher: Pattern matcher instance
            ocr_processor: OCR processor instance
            update_interval: Preview update interval in ms
        """
        super().__init__()
        
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        self.capture_manager = capture_manager
        self.pattern_matcher = pattern_matcher
        self.ocr_processor = ocr_processor
        
        # Create coordinate visualizer
        self.coord_vis = CoordinateVisualizer(
            window_tracker,
            coordinate_manager
        )
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.setInterval(update_interval)
        
        # Debug state
        self.last_matches: List[MatchResult] = []
        self.last_ocr_text: Dict[str, str] = {}
        
        # Connect to capture events
        self.capture_manager.capture_complete.connect(
            self._on_capture_complete
        )
        
        # Connect to pattern matcher events
        self.pattern_matcher.match_found.connect(
            self._on_match_found
        )
        
        # Connect to OCR events
        self.ocr_processor.text_found.connect(
            self._on_text_found
        )
        
        logger.debug("Debug visualizer initialized")
        
    def start(self) -> None:
        """Start preview updates."""
        self.update_timer.start()
        logger.debug("Debug visualization started")
        
    def stop(self) -> None:
        """Stop preview updates."""
        self.update_timer.stop()
        logger.debug("Debug visualization stopped")
        
    def _update_preview(self) -> None:
        """Update preview image."""
        try:
            # Capture window
            image = self.capture_manager.capture_window()
            if image is None:
                return
                
            # Draw coordinate overlay
            image = self.coord_vis.draw_overlay(image)
            
            # Draw pattern matches
            for match in self.last_matches:
                rect = match.rect
                cv2.rectangle(
                    image,
                    (rect.left(), rect.top()),
                    (rect.right(), rect.bottom()),
                    (0, 255, 0),
                    2
                )
                
                # Draw confidence
                label = f"{match.template_name}: {match.confidence:.2f}"
                cv2.putText(
                    image,
                    label,
                    (rect.left(), rect.top() - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )
                
            # Draw OCR results
            for region_name, text in self.last_ocr_text.items():
                rect = self.coordinate_manager.get_region(
                    region_name,
                    CoordinateSpace.SCREEN
                )
                if not rect:
                    continue
                    
                cv2.putText(
                    image,
                    text,
                    (rect.left(), rect.bottom() + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1
                )
                
            # Convert to QImage
            height, width = image.shape[:2]
            bytes_per_line = 3 * width
            q_image = QImage(
                image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
            
            # Emit preview
            self.preview_updated.emit(q_image)
            
            # Update metrics
            self._update_metrics()
            
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
        """Handle pattern match event."""
        self._update_preview()
        
    def _on_text_found(self, region: str, text: str) -> None:
        """Handle OCR text event."""
        self.last_ocr_text[region] = text
        self._update_preview() 