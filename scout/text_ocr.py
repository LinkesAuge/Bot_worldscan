from typing import Optional, Dict, Any, Tuple
import numpy as np
import cv2
import logging
from pathlib import Path
import pytesseract
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from scout.window_capture import WindowCapture
from scout.debug_window import DebugWindow

logger = logging.getLogger(__name__)

class TextOCR(QObject):
    """
    Handles continuous OCR processing of a selected screen region.
    
    This class provides:
    - Continuous capture of a specified screen region
    - OCR processing of the captured region
    - Debug visualization of the captured region and OCR results
    - Configurable update frequency
    
    The OCR processing is independent of pattern matching and runs at its own
    configurable frequency.
    """
    
    # Signal for debug images
    debug_image = pyqtSignal(str, object, dict)  # name, image, metadata
    
    def __init__(self, debug_window: DebugWindow) -> None:
        """
        Initialize Text OCR processor.
        
        Args:
            debug_window: Debug window for visualization
        """
        super().__init__()
        self.debug_window = debug_window
        self.window_capture = WindowCapture()  # For region capture
        self.active = False
        self.region: Optional[Dict[str, int]] = None
        self.update_frequency = 0.5  # Default 0.5 updates/sec
        
        # Create timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_region)
        
        logger.debug("TextOCR initialized")
    
    def set_region(self, region: Dict[str, int]) -> None:
        """
        Set the region to process.
        
        Args:
            region: Dictionary with left, top, width, height
        """
        self.region = region
        logger.info(f"OCR region set to: {region}")
        
        # If active, force an immediate capture
        if self.active:
            self._process_region()
    
    def set_frequency(self, frequency: float) -> None:
        """
        Set update frequency.
        
        Args:
            frequency: Updates per second
        """
        self.update_frequency = frequency
        interval = int(1000 / frequency)  # Convert to milliseconds
        
        if self.active:
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval}ms ({frequency} updates/sec)")
    
    def start(self) -> None:
        """Start OCR processing."""
        if not self.region:
            logger.warning("Cannot start OCR - no region set")
            return
            
        self.active = True
        interval = int(1000 / self.update_frequency)
        self.update_timer.start(interval)
        logger.info(f"OCR processing started with {self.update_frequency} updates/sec")
        
        # Force initial capture
        self._process_region()
    
    def stop(self) -> None:
        """Stop OCR processing."""
        self.active = False
        self.update_timer.stop()
        logger.info("OCR processing stopped")
    
    def _process_region(self) -> None:
        """Capture and process the OCR region."""
        if not self.region:
            return
            
        try:
            # Capture region
            screenshot = self.window_capture.capture_screenshot(
                method="mss",
                region=self.region
            )
            
            if screenshot is None:
                logger.warning("Failed to capture OCR region")
                return
            
            # Convert to grayscale
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Process for OCR
            processed = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
            blurred = cv2.GaussianBlur(processed, (3, 3), 0)
            thresh = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # Perform OCR
            text = pytesseract.image_to_string(
                thresh,
                config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            )
            
            # Clean text
            value = ''.join(filter(str.isdigit, text.strip()))
            
            # Update debug window
            self.debug_window.update_image(
                "OCR Region",
                screenshot,
                metadata={
                    "size": f"{screenshot.shape[1]}x{screenshot.shape[0]}",
                    "raw_text": text.strip(),
                    "value": value
                },
                save=True
            )
            
            # Show processed image
            self.debug_window.update_image(
                "OCR Processed",
                thresh,
                metadata={
                    "raw_text": text.strip(),
                    "value": value
                },
                save=True
            )
            
            logger.debug(f"OCR processed region - text: {text.strip()}, value: {value}")
            
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}", exc_info=True) 