from typing import Optional, Dict, Any, Tuple
import logging
import mss
import numpy as np
import cv2
from PyQt6.QtCore import QObject, QRect, pyqtSignal
from datetime import datetime
from pathlib import Path

from ..core.window_tracker import WindowTracker
from ..core.coordinate_manager import CoordinateManager, CoordinateSpace

logger = logging.getLogger(__name__)

class CaptureManager(QObject):
    """
    Manages screen capture operations.
    
    This class provides:
    - Window and region capture functionality
    - Image preprocessing for OCR and pattern matching
    - Capture timing and synchronization
    - Debug image storage
    """
    
    # Signals
    capture_complete = pyqtSignal(np.ndarray, str)  # image, capture_type
    capture_failed = pyqtSignal(str, str)  # error_msg, capture_type
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        coordinate_manager: CoordinateManager,
        debug_dir: str = "debug_screenshots"
    ) -> None:
        """
        Initialize capture manager.
        
        Args:
            window_tracker: Window tracker instance
            coordinate_manager: Coordinate manager instance
            debug_dir: Directory for debug screenshots
        """
        super().__init__()
        
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(exist_ok=True)
        
        self.sct = mss.mss()
        self.last_capture_time: Optional[datetime] = None
        self.capture_metrics: Dict[str, Any] = {
            "total_captures": 0,
            "failed_captures": 0,
            "avg_capture_time": 0.0
        }
        
        logger.debug("Capture manager initialized")
        
    def capture_window(self, save_debug: bool = False) -> Optional[np.ndarray]:
        """
        Capture entire game window.
        
        Args:
            save_debug: Whether to save debug screenshot
            
        Returns:
            Captured image as numpy array
        """
        try:
            window_rect = self.window_tracker.get_window_rect()
            if not window_rect:
                raise RuntimeError("Window not found")
                
            # Capture window
            monitor = {
                "top": window_rect.top(),
                "left": window_rect.left(),
                "width": window_rect.width(),
                "height": window_rect.height()
            }
            
            screenshot = self.sct.grab(monitor)
            image = np.array(screenshot)
            
            # Convert from BGRA to BGR
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            
            # Update metrics
            self._update_metrics(True)
            
            # Save debug image if requested
            if save_debug:
                self._save_debug_image(image, "window")
                
            self.capture_complete.emit(image, "window")
            return image
            
        except Exception as e:
            error_msg = f"Window capture failed: {str(e)}"
            logger.error(error_msg)
            self._update_metrics(False)
            self.capture_failed.emit(error_msg, "window")
            return None
            
    def capture_region(
        self,
        region_name: str,
        save_debug: bool = False
    ) -> Optional[np.ndarray]:
        """
        Capture specific region.
        
        Args:
            region_name: Name of region to capture
            save_debug: Whether to save debug screenshot
            
        Returns:
            Captured image as numpy array
        """
        try:
            # Get region in screen coordinates
            region_rect = self.coordinate_manager.get_region(
                region_name,
                CoordinateSpace.SCREEN
            )
            if not region_rect:
                raise RuntimeError(f"Region '{region_name}' not found")
                
            # Capture region
            monitor = {
                "top": region_rect.top(),
                "left": region_rect.left(),
                "width": region_rect.width(),
                "height": region_rect.height()
            }
            
            screenshot = self.sct.grab(monitor)
            image = np.array(screenshot)
            
            # Convert from BGRA to BGR
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            
            # Update metrics
            self._update_metrics(True)
            
            # Save debug image if requested
            if save_debug:
                self._save_debug_image(image, f"region_{region_name}")
                
            self.capture_complete.emit(image, f"region_{region_name}")
            return image
            
        except Exception as e:
            error_msg = f"Region capture failed: {str(e)}"
            logger.error(error_msg)
            self._update_metrics(False)
            self.capture_failed.emit(error_msg, f"region_{region_name}")
            return None
            
    def preprocess_image(
        self,
        image: np.ndarray,
        for_ocr: bool = False
    ) -> np.ndarray:
        """
        Preprocess image for OCR or pattern matching.
        
        Args:
            image: Input image
            for_ocr: Whether preprocessing is for OCR
            
        Returns:
            Preprocessed image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            if for_ocr:
                # OCR preprocessing
                # Increase contrast
                gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
                
                # Denoise
                gray = cv2.fastNlMeansDenoising(gray)
                
                # Threshold
                _, binary = cv2.threshold(
                    gray,
                    0,
                    255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                return binary
                
            else:
                # Pattern matching preprocessing
                # Equalize histogram
                gray = cv2.equalizeHist(gray)
                
                # Gaussian blur to reduce noise
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
                
                return gray
                
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image
            
    def _update_metrics(self, success: bool) -> None:
        """Update capture metrics."""
        now = datetime.now()
        
        # Update counters
        self.capture_metrics["total_captures"] += 1
        if not success:
            self.capture_metrics["failed_captures"] += 1
            
        # Update timing
        if self.last_capture_time:
            capture_time = (now - self.last_capture_time).total_seconds()
            avg = self.capture_metrics["avg_capture_time"]
            self.capture_metrics["avg_capture_time"] = (
                avg * 0.9 + capture_time * 0.1
            )
            
        self.last_capture_time = now
        
    def _save_debug_image(self, image: np.ndarray, prefix: str) -> None:
        """Save debug screenshot."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.debug_dir / f"{prefix}_{timestamp}.png"
            cv2.imwrite(str(filename), image)
            logger.debug(f"Saved debug image: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save debug image: {e}")
            
    def get_debug_info(self) -> Dict[str, Any]:
        """Get current capture state for debugging."""
        return {
            "metrics": self.capture_metrics,
            "last_capture": self.last_capture_time,
            "debug_dir": str(self.debug_dir)
        } 