"""
Text OCR Processor

This module provides OCR functionality for extracting text from the game window.
It handles:
- Region selection
- Text extraction
- Coordinate parsing
- Debug visualization
"""

from typing import Optional, Dict, Any, List
import numpy as np
import cv2
import logging
import pytesseract
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import re
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager
from scout.game_state import GameState
from scout.game_world_position import GameCoordinates
import mss
from pathlib import Path
from scout.config_manager import ConfigManager
import time
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TextOCR(QObject):
    """
    Handles continuous OCR processing of a selected screen region.
    
    This class provides:
    - Continuous capture of a specified screen region
    - OCR processing of the captured region
    - Coordinate extraction and validation
    - Debug visualization of the captured region and OCR results
    - Configurable update frequency
    """
    
    # Signals
    debug_image = pyqtSignal(str, object, dict)  # name, image, metadata
    coordinates_updated = pyqtSignal(object)  # Emits GameCoordinates from GameState
    
    def __init__(self, debug_window: DebugWindow, window_manager: WindowManager, game_state: GameState) -> None:
        """
        Initialize Text OCR processor.
        
        Args:
            debug_window: Debug window for visualization
            window_manager: Window manager instance for window tracking and coordinate handling
            game_state: Game state instance for coordinate tracking
        """
        super().__init__()
        self.debug_window = debug_window
        self.window_manager = window_manager
        self.game_state = game_state
        self._active = False
        self.region: Optional[Dict[str, int]] = None
        self.logical_region: Optional[Dict[str, int]] = None
        self._cancellation_requested = False  # Flag to indicate cancellation request
        
        # Load settings from config
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        self.update_frequency = ocr_settings.get('frequency', 0.5)  # Default 0.5 updates/sec
        self.max_frequency = ocr_settings.get('max_frequency', 2.0)  # Default max 2.0 updates/sec
        
        # OCR method preference
        self.preferred_method = 'thresh3'  # Default to thresh3 as it produces the best results
        
        # Create timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_region)
        
        logger.debug("TextOCR initialized")
    
    @property
    def active(self) -> bool:
        """
        Check if OCR is currently active.
        
        Returns:
            True if OCR is active, False otherwise
        """
        return self._active
    
    def set_region(self, region: Dict[str, Any]) -> None:
        """
        Set the OCR region for coordinate extraction.
        
        Args:
            region: Dictionary containing region coordinates and properties
                   Must have 'left', 'top', 'width', 'height', and 'dpi_scale'
        """
        try:
            # Get window dimensions
            window_rect = self.window_manager.get_window_position()
            if not window_rect:
                logger.error("Could not get window position")
                return
                
            window_x, window_y, window_width, window_height = window_rect
            
            # Convert region to window-relative coordinates
            logical_region = {
                'left': region['left'],
                'top': region['top'],
                'width': region['width'],
                'height': region['height'],
                'dpi_scale': region.get('dpi_scale', 1.0)
            }
            
            # Ensure region is within window bounds
            logical_region['left'] = max(0, min(logical_region['left'], window_width - logical_region['width']))
            logical_region['top'] = max(0, min(logical_region['top'], window_height - logical_region['height']))
            
            # Convert to screen coordinates
            screen_x = window_x + logical_region['left']
            screen_y = window_y + logical_region['top']
            
            physical_region = {
                'left': screen_x,
                'top': screen_y,
                'width': logical_region['width'],
                'height': logical_region['height'],
                'dpi_scale': logical_region['dpi_scale']
            }
            
            # Store both logical (window-relative) and physical (screen) coordinates
            self.region = physical_region
            self.logical_region = logical_region
            
            logger.info(f"OCR region set to: logical={logical_region}, physical={physical_region}")
            
        except Exception as e:
            logger.error(f"Error setting OCR region: {e}")
            self.region = None
            self.logical_region = None
            
    def set_frequency(self, frequency: float) -> None:
        """
        Set the update frequency, respecting the maximum allowed frequency.
        
        Args:
            frequency: Updates per second
        """
        # Ensure frequency doesn't exceed the maximum
        if frequency > self.max_frequency:
            logger.warning(f"Requested frequency {frequency} exceeds maximum allowed {self.max_frequency}. Using maximum.")
            frequency = self.max_frequency
            
        self.update_frequency = frequency
        if self._active:
            interval = int(1000 / frequency)  # Convert to milliseconds
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval}ms ({frequency} updates/sec)")
            
    def get_max_frequency(self) -> float:
        """
        Get the maximum allowed update frequency.
        
        Returns:
            The maximum allowed frequency in updates per second
        """
        # Refresh from config in case it was updated
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        self.max_frequency = ocr_settings.get('max_frequency', 2.0)
        return self.max_frequency
        
    def start(self) -> None:
        """Start OCR processing."""
        if self._active:
            return
            
        self._active = True
        self._cancellation_requested = False  # Reset cancellation flag
        interval = int(1000 / self.update_frequency)  # Convert to milliseconds
        self.update_timer.start(interval)
        logger.info(f"OCR started with {self.update_frequency} updates/sec (max: {self.max_frequency})")
        
    def stop(self) -> None:
        """Stop OCR processing."""
        if not self._active:
            return
            
        # Set cancellation flag first
        self._cancellation_requested = True
        logger.info("OCR cancellation requested")
        
        # Stop the timer
        self._active = False
        if self.update_timer.isActive():
            self.update_timer.stop()
            
        # Force a small delay to allow any ongoing operations to detect the cancellation flag
        QTimer.singleShot(100, self._ensure_stopped)
        
        logger.info("OCR stopped")
        
    def _ensure_stopped(self) -> None:
        """
        Ensure OCR is fully stopped.
        
        This method is called after a short delay to verify that OCR has been stopped
        and to log any issues if it hasn't.
        """
        if self._active:
            logger.warning("OCR still active after stop request - forcing inactive state")
            self._active = False
            
        # Double-check timer is stopped
        if self.update_timer.isActive():
            logger.warning("OCR timer still active after stop request - forcing stop")
            self.update_timer.stop()
            
        # Log confirmation
        logger.info("OCR process fully stopped")
        
    def set_preferred_method(self, method: str) -> None:
        """
        Set the preferred OCR preprocessing method.
        
        Args:
            method: The preprocessing method to prefer ('thresh1', 'thresh2', 'thresh3', 'morphed', 'auto')
                   'auto' will use the scoring system to select the best result
        """
        valid_methods = ['thresh1', 'thresh2', 'thresh3', 'morphed', 'auto']
        if method not in valid_methods:
            logger.warning(f"Invalid OCR method '{method}'. Using default 'thresh3'.")
            method = 'thresh3'
            
        self.preferred_method = method
        logger.info(f"OCR preferred method set to '{method}'")
        
    def get_preferred_method(self) -> str:
        """
        Get the current preferred OCR preprocessing method.
        
        Returns:
            The current preferred method
        """
        return self.preferred_method
        
    def _save_debug_image(self, name: str, image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save a debug image. In normal mode, only saves OCR processing images temporarily.
        In debug mode, saves all images with timestamps.
        
        Args:
            name: Name of the image
            image: Image data
            metadata: Optional metadata about the image
        """
        try:
            # Always emit debug image signal for visualization
            self.debug_image.emit(name, image, metadata or {})
            
            # Get debug settings
            config = ConfigManager()
            debug_settings = config.get_debug_settings()
            debug_enabled = debug_settings.get("enabled", False)
            
            # Create output directories
            debug_dir = Path('scout/ocr_output/debug')
            temp_dir = Path('scout/ocr_output/temp')
            debug_dir.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # In debug mode, save with timestamp in debug directory
            if debug_enabled:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}.png"
                cv2.imwrite(str(debug_dir / filename), image)
                logger.debug(f"Saved debug image: {filename}")
            
            # For OCR processing images, always save in temp directory
            if name.startswith(('ocr_', 'thresh', 'morphed')):
                filename = f"{name}_latest.png"
                cv2.imwrite(str(temp_dir / filename), image)
                logger.debug(f"Saved OCR processing image: {filename}")
                
        except Exception as e:
            logger.error(f"Error saving debug image: {e}")

    def _save_result_image(self, name: str, image: np.ndarray, is_match: bool = False) -> None:
        """
        Save the final result image. In normal mode, only saves the latest result.
        In case of a match, saves with timestamp.
        
        Args:
            name: Name of the image
            image: Image data
            is_match: Whether this result represents a match
        """
        try:
            # Create output directories
            results_dir = Path('scout/ocr_output/results')
            results_dir.mkdir(parents=True, exist_ok=True)
            
            if is_match:
                # For matches, save with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{name}_{timestamp}.png"
            else:
                # For normal results, always overwrite the latest
                filename = f"{name}_latest.png"
            
            filepath = results_dir / filename
            cv2.imwrite(str(filepath), image)
            
            if is_match:
                logger.info(f"Saved match result: {filename}")
            else:
                logger.debug("Updated latest result image")
            
            # Clean up temporary OCR processing files
            self._cleanup_temp_files()
                
        except Exception as e:
            logger.error(f"Error saving result image: {e}")

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary OCR processing files after successful processing."""
        try:
            temp_dir = Path('scout/ocr_output/temp')
            if temp_dir.exists():
                # Only remove files older than 5 minutes to avoid conflicts during calibration
                current_time = time.time()
                for file in temp_dir.glob('*'):
                    if file.is_file():
                        file_age = current_time - file.stat().st_mtime
                        if file_age > 300:  # 300 seconds = 5 minutes
                            try:
                                file.unlink()
                                logger.debug(f"Cleaned up temp file: {file.name}")
                            except Exception as e:
                                logger.warning(f"Failed to delete temp file {file.name}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

    def extract_text(self, image: np.ndarray) -> str:
        """
        Extract text from an image using OCR with enhanced preprocessing.
        """
        try:
            # Create temp directory for OCR processing
            temp_dir = Path('scout/ocr_output/temp')
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Always save the original image for OCR processing
            cv2.imwrite(str(temp_dir / 'ocr_original_latest.png'), image)
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply preprocessing methods
            enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            # Create all preprocessed versions and save them
            # Approach 1: Enhanced contrast with adaptive thresholding
            thresh1 = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            cv2.imwrite(str(temp_dir / 'ocr_thresh1_latest.png'), thresh1)
            
            # Approach 2: Inverse thresholding
            _, thresh2 = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY_INV)
            cv2.imwrite(str(temp_dir / 'ocr_thresh2_latest.png'), thresh2)
            
            # Approach 3: Otsu's thresholding
            _, thresh3 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            cv2.imwrite(str(temp_dir / 'ocr_thresh3_latest.png'), thresh3)
            
            # Approach 4: Morphological operations
            kernel = np.ones((2, 2), np.uint8)
            dilated = cv2.dilate(thresh1, kernel, iterations=1)
            eroded = cv2.erode(dilated, kernel, iterations=1)
            cv2.imwrite(str(temp_dir / 'ocr_morphed_latest.png'), eroded)
            
            # Approach 5: Enhanced contrast with sharpening
            kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
            _, thresh4 = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            cv2.imwrite(str(temp_dir / 'ocr_sharpened_latest.png'), thresh4)
            
            # Store preprocessed images in a dictionary for OCR
            preprocessed_images = {
                'thresh1': thresh1,
                'thresh2': thresh2,
                'thresh3': thresh3,
                'morphed': eroded,
                'sharpened': thresh4
            }
            
            # Get debug settings
            config = ConfigManager()
            debug_settings = config.get_debug_settings()
            debug_enabled = debug_settings.get("enabled", False)
            
            # If in debug mode, save copies with timestamps
            if debug_enabled:
                debug_dir = Path('scout/ocr_output/debug')
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                for name, img in preprocessed_images.items():
                    cv2.imwrite(str(debug_dir / f'ocr_{name}_{timestamp}.png'), img)
            
            # Process with OCR
            results = {}
            
            # Add config to disable temp files where possible
            base_config = '--psm 7'
            whitelist_config = f'{base_config} -c tessedit_char_whitelist=0123456789:KXYkxy'
            specific_config = f'{whitelist_config} -c tessedit_write_params=1'
            
            try:
                # Process each preprocessing method
                for method, img in preprocessed_images.items():
                    # Only process the preferred method if not in auto mode
                    if self.preferred_method != 'auto' and method != self.preferred_method:
                        continue
                        
                    # Standard OCR
                    text = pytesseract.image_to_string(img).strip()
                    results[f"{method}_standard"] = text
                    
                    # PSM 7: Treat the image as a single line of text
                    text_psm7 = pytesseract.image_to_string(img, config=base_config).strip()
                    results[f"{method}_psm7"] = text_psm7
                    
                    # Try with character whitelist for coordinates
                    text_whitelist = pytesseract.image_to_string(
                        img, 
                        config=whitelist_config
                    ).strip()
                    results[f"{method}_whitelist"] = text_whitelist
                    
                    # Try with a more specific configuration for the expected format
                    text_specific = pytesseract.image_to_string(
                        img,
                        config=specific_config
                    ).strip()
                    results[f"{method}_specific"] = text_specific
                
            except Exception as ocr_e:
                logger.error(f"Error during OCR processing: {ocr_e}", exc_info=True)
                results["error"] = "OCR Error"
            
            # Log all extracted texts for debugging
            for method, text in results.items():
                logger.debug(f"OCR Result ({method}): '{text}'")
            
            # Choose the best result
            best_text = ""
            
            if self.preferred_method == 'auto':
                best_text = self._select_best_text(results)
                logger.info(f"Auto-selected OCR text: '{best_text}'")
            else:
                preferred_results = [
                    results.get(f"{self.preferred_method}_standard", ""),
                    results.get(f"{self.preferred_method}_psm7", ""),
                    results.get(f"{self.preferred_method}_whitelist", ""),
                    results.get(f"{self.preferred_method}_specific", "")
                ]
                
                preferred_results = [r for r in preferred_results if r]
                
                if preferred_results:
                    best_text = self._select_best_text(preferred_results)
                    logger.info(f"Selected OCR text from {self.preferred_method}: '{best_text}'")
                else:
                    best_text = self._select_best_text(results)
                    logger.info(f"Fallback to auto-selected OCR text: '{best_text}'")
            
            # Save the result
            if best_text:
                # Save result with timestamp in debug mode
                if debug_enabled:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(str(debug_dir / f'ocr_result_{timestamp}.png'), image)
                    
                    # Save OCR output as JSON
                    final_output = {
                        'timestamp': timestamp,
                        'text': best_text,
                        'method': self.preferred_method,
                        'results_by_method': results
                    }
                    with open(str(debug_dir / f'ocr_result_{timestamp}.json'), 'w') as f:
                        json.dump(final_output, f, indent=4)
                
                # Always save latest result
                cv2.imwrite(str(temp_dir / 'ocr_result_latest.png'), image)
            
            # Update debug window if available
            if debug_enabled and hasattr(self, 'debug_window') and self.debug_window:
                debug_image = preprocessed_images.get(self.preferred_method, thresh1)
                self.debug_window.update_image(
                    "OCR Extract",
                    debug_image,
                    metadata={"raw_text": best_text, "method": self.preferred_method},
                    save=True
                )
            
            return best_text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}", exc_info=True)
            return ""

    def _select_best_text(self, texts: List[str]) -> str:
        """
        Select the best text from multiple OCR results.
        
        This method prioritizes text that matches the expected format of K: 000 X: 000 Y: 000.
        Any text that doesn't match this pattern is given a lower score.
        
        Args:
            texts: List of OCR result texts
            
        Returns:
            The best text containing coordinate information
        """
        best_score = -1
        best_text = ""
        
        # Define the expected format pattern
        expected_format = r'[kK]\s*:?\s*(\d{1,3}).*?[xX]\s*:?\s*(\d{1,3}).*?[yY]\s*:?\s*(\d{1,3})'
        
        for text in texts:
            score = 0
            
            # Skip empty texts
            if not text or text == "OCR Error":
                continue
                
            # Clean the text for better pattern matching
            cleaned = text.replace(';', ':').replace('|', ':').replace('l', '1').replace('O', '0').replace('o', '0')
            
            # Check if the text matches the expected format
            match = re.search(expected_format, cleaned, re.IGNORECASE)
            if match:
                # Give a high base score for matching the expected format
                score += 10
                
                # Extract the coordinate values
                try:
                    k_val = int(match.group(1))
                    x_val = int(match.group(2))
                    y_val = int(match.group(3))
                    
                    # Bonus for valid coordinate values
                    if 1 <= k_val <= 999:
                        score += 3
                    if 0 <= x_val <= 999:
                        score += 3
                    if 0 <= y_val <= 999:
                        score += 3
                        
                    # Extra bonus if all coordinates are valid
                    if 1 <= k_val <= 999 and 0 <= x_val <= 999 and 0 <= y_val <= 999:
                        score += 5
                except (ValueError, IndexError):
                    # Penalty for invalid coordinate values
                    score -= 5
            else:
                # Significant penalty for not matching the expected format
                score -= 10
                
            # Penalty for very long or very short texts
            if len(text) > 50:
                score -= 2
            if len(text) < 5:
                score -= 2
                
            logger.debug(f"Text score: {score} for '{text}'")
            
            if score > best_score:
                best_score = score
                best_text = text
                
        # If no good candidate found, return the longest text
        if best_score <= 0:
            return max(texts, key=len) if texts else ""
            
        return best_text
        
    def _apply_threshold1(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding with enhanced contrast."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        return cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

    def _apply_threshold2(self, image: np.ndarray) -> np.ndarray:
        """Apply inverse thresholding with enhanced contrast."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
        _, thresh = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY_INV)
        return thresh

    def _apply_threshold3(self, image: np.ndarray) -> np.ndarray:
        """Apply Otsu's thresholding with enhanced contrast."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def _apply_morphological(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations for text enhancement."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        eroded = cv2.erode(dilated, kernel, iterations=1)
        return eroded

    def _score_text(self, text: str) -> int:
        """Score OCR text based on expected format and content."""
        if not text:
            return -1
            
        score = 0
        
        # Check for expected format
        if re.search(r'[kK]\s*:?\s*\d{1,3}', text):
            score += 5
        if re.search(r'[xX]\s*:?\s*\d{1,3}', text):
            score += 5
        if re.search(r'[yY]\s*:?\s*\d{1,3}', text):
            score += 5
            
        # Penalty for unexpected characters
        unexpected = len(re.findall(r'[^kKxXyY\d\s:.,]', text))
        score -= unexpected
        
        # Bonus for clean format
        if re.match(r'^[kK]\s*:?\s*\d{1,3}\s*[xX]\s*:?\s*\d{1,3}\s*[yY]\s*:?\s*\d{1,3}$', text):
            score += 10
            
        return score

    def _process_region(self) -> None:
        """Process the current OCR region and emit coordinates if found."""
        try:
            if self._cancellation_requested:
                logger.info("OCR processing cancelled")
                return
                
            if not self.region:
                logger.warning("No OCR region set")
                return
                
            # Get current window position
            window_rect = self.window_manager.get_window_position()
            if not window_rect:
                logger.error("Could not get window position")
                return
                
            window_x, window_y, window_width, window_height = window_rect
            
            # Update physical region based on current window position and logical region
            if self.logical_region:
                # Ensure region is within window bounds
                left = max(0, min(self.logical_region['left'], window_width - self.logical_region['width']))
                top = max(0, min(self.logical_region['top'], window_height - self.logical_region['height']))
                
                # Update physical region with current window position
                self.region = {
                    'left': window_x + left,
                    'top': window_y + top,
                    'width': self.logical_region['width'],
                    'height': self.logical_region['height'],
                    'dpi_scale': self.logical_region.get('dpi_scale', 1.0)
                }
            
            # Take screenshot of region
            screenshot = self.window_manager.capture_region(self.region)
            if screenshot is None:
                logger.error("Failed to capture screenshot of OCR region")
                return
                
            # Save screenshot for debugging
            debug_path = Path('scout/ocr_output')
            debug_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = debug_path / f'ocr_region_{timestamp}.png'
            cv2.imwrite(str(screenshot_path), screenshot)
            
            # Extract text from screenshot
            text = self.extract_text(screenshot)
            if text:
                logger.debug(f"Extracted text: {text}")
                
                # Extract coordinates from text
                coords = self._extract_coordinates(text)
                if coords:
                    logger.info(f"Successfully extracted coordinates: K: {coords.k:03d}, X: {coords.x:03d}, Y: {coords.y:03d} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                    # Update game state with new coordinates
                    if self.game_state:
                        self.game_state.update_coordinates(coords.k, coords.x, coords.y)
                    self.coordinates_updated.emit(coords)
                else:
                    logger.debug("No coordinates found in text")
            else:
                logger.debug("No text extracted from screenshot")
                
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}", exc_info=True)

    def _is_valid_match(self, coords: GameCoordinates) -> bool:
        """
        Determine if the coordinates represent a valid match.
        
        Args:
            coords: The extracted coordinates
            
        Returns:
            bool: True if this is a valid match that should be saved
        """
        # Implement your match criteria here
        # For example, check if coordinates are within certain ranges
        # or match specific patterns you're looking for
        if coords and coords.is_valid():
            # Add your specific match criteria here
            # For now, we'll consider any valid coordinates as a match
            return True
        return False

    def _extract_coordinates(self, text: str) -> Optional[GameCoordinates]:
        """
        Extract coordinates from OCR text, handling noise and invalid characters.
        
        Strictly enforces the expected format of K: 000 X: 000 Y: 000 and rejects
        anything that doesn't match this pattern. If extraction fails but we have
        previous valid coordinates, those will still be emitted.
        
        Args:
            text: The OCR text to parse
            
        Returns:
            GameCoordinates object if valid coordinates were extracted, None otherwise
        """
        try:
            # Clean text by removing common OCR artifacts and normalizing separators
            cleaned_text = text.replace(';', ':').replace('|', ':').replace('l', '1').replace('O', '0').replace('o', '0')
            
            # Log the cleaned text for debugging
            logger.debug(f"Cleaned OCR text: '{cleaned_text}'")
            
            # Use a strict regex pattern to match the expected format
            # This pattern looks for K: followed by 1-3 digits, X: followed by 1-3 digits, and Y: followed by 1-3 digits
            # The pattern allows for some flexibility in spacing and order
            pattern = r'[kK]\s*:?\s*(\d{1,3}).*?[xX]\s*:?\s*(\d{1,3}).*?[yY]\s*:?\s*(\d{1,3})'
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            
            if match:
                # Extract the coordinate values
                k_val = int(match.group(1))
                x_val = int(match.group(2))
                y_val = int(match.group(3))
                
                # Validate the coordinate values
                k_val = self._validate_coordinate(k_val, "K")
                x_val = self._validate_coordinate(x_val, "X")
                y_val = self._validate_coordinate(y_val, "Y")
                
                # Log the extracted coordinates
                logger.info(f"Extracted coordinates - K: {k_val}, X: {x_val}, Y: {y_val}")
                
                # Only proceed if all coordinates are valid
                if k_val is not None and x_val is not None and y_val is not None:
                    # Update game state with new coordinates
                    if self.game_state:
                        # Update the game state with the new coordinates
                        updated = self.game_state.update_coordinates(k_val, x_val, y_val)
                        
                        # Get the updated coordinates from the game state
                        # This might include previously valid coordinates for any values that failed validation
                        coords = self.game_state.coordinates
                        
                        # Emit updated coordinates
                        self.coordinates_updated.emit(coords)
                        
                        # Log success
                        logger.info(f"Successfully extracted coordinates: K:{k_val} X:{x_val} Y:{y_val}")
                        
                        return coords
                    else:
                        logger.warning("No game state available to update coordinates")
                        return None
                else:
                    logger.warning("One or more coordinates failed validation")
                    # Even if validation fails, still emit the last known coordinates
                    if self.game_state and self.game_state.coordinates:
                        self.coordinates_updated.emit(self.game_state.coordinates)
                    return None
            else:
                logger.warning("Text does not match the expected coordinate format")
                # Even if pattern matching fails, still emit the last known coordinates
                if self.game_state and self.game_state.coordinates:
                    self.coordinates_updated.emit(self.game_state.coordinates)
                return None
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}", exc_info=True)
            # Even if an error occurs, still emit the last known coordinates
            if self.game_state and self.game_state.coordinates:
                self.coordinates_updated.emit(self.game_state.coordinates)
            return None
            
    def _validate_coordinate(self, value: int, coord_type: str) -> Optional[int]:
        """
        Validate a coordinate value.
        
        Args:
            value: Value to validate
            coord_type: Type of coordinate ('K', 'X', or 'Y')
            
        Returns:
            Validated value or None if invalid
        """
        try:
            if coord_type == 'K':
                if 1 <= value <= 999:  # Assuming kingdoms are numbered 1-999
                    return value
            elif coord_type in ('X', 'Y'):
                if 0 <= value <= 999:  # Game world coordinates are 0-999
                    return value
            return None
        except Exception:
            return None 