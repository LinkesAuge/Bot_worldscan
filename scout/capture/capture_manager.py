from typing import Optional, Dict, Any, Tuple
import logging
import mss
import numpy as np
import cv2
import sys
from PyQt6.QtCore import QObject, QRect, pyqtSignal
from datetime import datetime
from pathlib import Path
import time

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
        
        # Initialize screen capture
        self.sct = None
        self._init_screen_capture()
        
        self.last_capture_time: Optional[datetime] = None
        self.capture_metrics: Dict[str, Any] = {
            "total_captures": 0,
            "failed_captures": 0,
            "avg_capture_time": 0.0
        }
        
        # Track capture state to prevent recursion
        self._is_capturing = False
        self._capture_retry_count = 0
        self._last_capture_start = 0.0
        self.MAX_RETRIES = 3  # Increased from 1
        self.CAPTURE_TIMEOUT = 5.0  # Increased from 1.0 seconds
        
        # Get DPI scale from window tracker
        self.dpi_scale = self.window_tracker.dpi_scale
        
        logger.debug("Capture manager initialized")
        
    def _init_screen_capture(self) -> None:
        """Initialize screen capture safely."""
        try:
            if self.sct is not None:
                try:
                    self.sct.close()
                except Exception:
                    pass
            self.sct = mss.mss()
        except Exception as e:
            # Log error without using logger to avoid potential recursion
            sys.stderr.write(f"Failed to initialize screen capture: {e}\n")
            self.sct = None
        
    def _check_capture_timeout(self) -> bool:
        """Check if previous capture has timed out."""
        if not self._is_capturing:
            return False
            
        current_time = time.time()
        elapsed = current_time - self._last_capture_start
        if elapsed > self.CAPTURE_TIMEOUT:
            logger.warning(f"Previous capture timed out after {elapsed:.2f}s, resetting state")
            self._is_capturing = False
            self._capture_retry_count = 0
            return True
            
        return False
        
    def capture_window(self, save_debug: bool = False) -> Optional[np.ndarray]:
        """
        Capture the game window.
        
        Args:
            save_debug: Whether to save debug image
            
        Returns:
            Captured image or None if failed
        """
        try:
            # Check if capture is in progress
            if self._check_capture_timeout():
                logger.debug("Previous capture timed out, resetting state")
                self._is_capturing = False
            
            if self._is_capturing:
                logger.debug("Capture already in progress, waiting...")
                # Wait briefly for previous capture
                time.sleep(0.1)  # Short sleep
                if self._is_capturing:
                    return None
            
            self._is_capturing = True
            self._last_capture_start = time.time()
            logger.debug("Starting window capture")
            
            # Get window rect
            window_rect = self.window_tracker.get_window_rect()
            if not window_rect:
                logger.warning("Could not get window rect for capture")
                self._is_capturing = False
                return None
                
            # Convert to screen coordinates
            left = window_rect.left()
            top = window_rect.top()
            width = window_rect.width()
            height = window_rect.height()
            
            # Ensure valid dimensions
            if width <= 0 or height <= 0:
                logger.error(f"Invalid window dimensions: {width}x{height}")
                self._is_capturing = False
                return None
                
            try:
                # Take screenshot
                if self.sct is None:
                    logger.debug("Reinitializing screen capture")
                    self._init_screen_capture()
                    
                monitor = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                }
                
                logger.debug(f"Capturing region: {monitor}")
                screenshot = self.sct.grab(monitor)
                
                # Convert to numpy array
                image = np.array(screenshot)
                
                # Convert from BGRA to BGR
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
                
                # Save debug image
                if save_debug:
                    self._save_debug_image(image, "window")
                    
                # Update metrics
                self._update_metrics(True)
                
                # Emit success signal
                self.capture_complete.emit(image, "window")
                logger.debug(f"Window capture successful: {image.shape}")
                
                return image
                
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")
                self._update_metrics(False)
                self.capture_failed.emit(str(e), "window")
                return None
                
        except Exception as e:
            logger.error(f"Capture error: {e}")
            self._update_metrics(False)
            self.capture_failed.emit(str(e), "window")
            return None
            
        finally:
            capture_time = time.time() - self._last_capture_start
            logger.debug(f"Capture completed in {capture_time:.3f}s")
            self._is_capturing = False
            self._capture_retry_count = 0
        
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
        if self._is_capturing:
            sys.stderr.write("Region capture already in progress, skipping\n")
            return None
            
        self._is_capturing = True
        try:
            # Get region in screen coordinates
            region_rect = self.coordinate_manager.get_region(
                region_name,
                CoordinateSpace.SCREEN
            )
            if not region_rect:
                raise RuntimeError(f"Region '{region_name}' not found")
                
            # Update DPI scale
            self.dpi_scale = self.window_tracker.dpi_scale
                
            # Capture region
            monitor = {
                "top": region_rect.top(),
                "left": region_rect.left(),
                "width": region_rect.width(),
                "height": region_rect.height()
            }
            
            try:
                screenshot = self.sct.grab(monitor)
                image = np.array(screenshot)
            except (RecursionError, Exception) as e:
                # If capture fails, try one more time with fresh mss instance
                if self._capture_retry_count < self.MAX_RETRIES:
                    self._capture_retry_count += 1
                    sys.stderr.write(f"Region capture error ({type(e).__name__}), retrying...\n")
                    self._init_screen_capture()
                    if self.sct is None:
                        raise RuntimeError("Failed to reinitialize screen capture")
                    
                    # Try capture one more time
                    screenshot = self.sct.grab(monitor)
                    image = np.array(screenshot)
                else:
                    raise RuntimeError(f"Region capture failed after {self.MAX_RETRIES} retries")
            
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
            sys.stderr.write(f"{error_msg}\n")  # Write to stderr to avoid logger recursion
            self._update_metrics(False)
            self.capture_failed.emit(error_msg, f"region_{region_name}")
            return None
            
        finally:
            self._is_capturing = False
            self._capture_retry_count = 0
        
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