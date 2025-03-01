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
from scout.game_state import GameState, GameCoordinates
import mss
from pathlib import Path
from scout.config_manager import ConfigManager
import time

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
    
    def set_region(self, region: Dict[str, int]) -> None:
        """
        Set the region to process.
        
        Args:
            region: Dictionary with left, top, width, height in physical coordinates
        """
        self.region = region
        logger.info(f"OCR region set to: {region}")
        
        # If active, force an immediate capture
        if self._active:
            self._process_region()
            
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
        
    def extract_text(self, image: np.ndarray) -> str:
        """
        Extract text from an image using OCR with enhanced preprocessing.
        
        This method applies multiple preprocessing techniques and OCR configurations
        to maximize the chances of correctly extracting coordinate text from the game UI.
        It prioritizes the preferred method set via set_preferred_method().
        
        Args:
            image: The image to extract text from (numpy array)
            
        Returns:
            The extracted text as a string
        """
        try:
            # Check if cancellation was requested
            if self._cancellation_requested:
                logger.info("Text extraction cancelled")
                return ""
                
            # Check if Tesseract is properly configured
            try:
                tesseract_version = pytesseract.get_tesseract_version()
                logger.info(f"Using Tesseract OCR version: {tesseract_version}")
            except Exception as e:
                logger.error(f"Tesseract OCR not properly configured: {e}")
                logger.error("Please ensure Tesseract OCR is installed and the path is set correctly")
                logger.error("You can set the path using: pytesseract.pytesseract.tesseract_cmd = r'path_to_tesseract.exe'")
                
                # Try to set a default path as a fallback
                try:
                    import os
                    default_paths = [
                        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                        r'C:\Tesseract-OCR\tesseract.exe'
                    ]
                    
                    for path in default_paths:
                        if os.path.exists(path):
                            logger.info(f"Found Tesseract at: {path}")
                            pytesseract.pytesseract.tesseract_cmd = path
                            break
                except Exception as path_e:
                    logger.error(f"Error setting default Tesseract path: {path_e}")
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            # Get debug settings
            config = ConfigManager()
            debug_settings = config.get_debug_settings()
            debug_enabled = debug_settings["enabled"]
                
            # Ensure the debug directory exists
            debug_dir = Path('scout/debug_screenshots')
            debug_dir.mkdir(exist_ok=True, parents=True)
            
            # Create an ocr_output directory for final OCR results
            ocr_output_dir = Path('scout/ocr_output')
            ocr_output_dir.mkdir(exist_ok=True, parents=True)
                
            # Save the original image for debugging only if debug mode is enabled
            if debug_enabled:
                cv2.imwrite(str(debug_dir / 'ocr_original.png'), image)
                
            # Apply multiple preprocessing approaches for better results
            
            # Approach 1: Enhanced contrast with adaptive thresholding
            enhanced = cv2.convertScaleAbs(gray, alpha=2.5, beta=0)
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            thresh1 = cv2.adaptiveThreshold(
                blurred, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            
            # Approach 2: Inverse thresholding (often better for light text on dark background)
            _, thresh2 = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Approach 3: Otsu's thresholding (automatically determines optimal threshold)
            _, thresh3 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Approach 4: Morphological operations to enhance text
            kernel = np.ones((2, 2), np.uint8)
            dilated = cv2.dilate(thresh1, kernel, iterations=1)
            eroded = cv2.erode(dilated, kernel, iterations=1)
            
            # Approach 5: Enhanced contrast with sharpening for better text definition
            kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
            _, thresh4 = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Save the preprocessed images for debugging if debug mode is enabled
            if debug_enabled:
                cv2.imwrite(str(debug_dir / 'ocr_thresh1.png'), thresh1)
                cv2.imwrite(str(debug_dir / 'ocr_thresh2.png'), thresh2)
                cv2.imwrite(str(debug_dir / 'ocr_thresh3.png'), thresh3)
                cv2.imwrite(str(debug_dir / 'ocr_morphed.png'), eroded)
                cv2.imwrite(str(debug_dir / 'ocr_sharpened.png'), thresh4)
            
            # Store preprocessed images in a dictionary for easy access
            preprocessed_images = {
                'thresh1': thresh1,
                'thresh2': thresh2,
                'thresh3': thresh3,
                'morphed': eroded,
                'sharpened': thresh4
            }
            
            # Try multiple OCR approaches with different configurations
            results = []
            results_by_method = {}
            
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
                    results.append(text)
                    results_by_method[f"{method}_standard"] = text
                    
                    # PSM 7: Treat the image as a single line of text
                    text_psm7 = pytesseract.image_to_string(img, config=base_config).strip()
                    results.append(text_psm7)
                    results_by_method[f"{method}_psm7"] = text_psm7
                    
                    # Try with character whitelist for coordinates
                    text_whitelist = pytesseract.image_to_string(
                        img, 
                        config=whitelist_config
                    ).strip()
                    results.append(text_whitelist)
                    results_by_method[f"{method}_whitelist"] = text_whitelist
                    
                    # Try with a more specific configuration for the expected format
                    text_specific = pytesseract.image_to_string(
                        img,
                        config=specific_config
                    ).strip()
                    results.append(text_specific)
                    results_by_method[f"{method}_specific"] = text_specific
                
            except Exception as ocr_e:
                logger.error(f"Error during OCR processing: {ocr_e}", exc_info=True)
                # Add a dummy result to avoid empty results
                results.append("OCR Error")
                results_by_method["error"] = "OCR Error"
            
            # Log all extracted texts for debugging
            for method, text in results_by_method.items():
                logger.debug(f"OCR Result ({method}): '{text}'")
            
            # Choose the best result based on the preferred method or scoring
            best_text = ""
            
            if self.preferred_method == 'auto':
                # Use the scoring system to select the best result
                best_text = self._select_best_text(results)
                logger.info(f"Auto-selected OCR text: '{best_text}'")
            else:
                # Use the preferred method
                # Try different configurations of the preferred method
                preferred_results = [
                    results_by_method.get(f"{self.preferred_method}_standard", ""),
                    results_by_method.get(f"{self.preferred_method}_psm7", ""),
                    results_by_method.get(f"{self.preferred_method}_whitelist", ""),
                    results_by_method.get(f"{self.preferred_method}_specific", "")
                ]
                
                # Filter out empty results
                preferred_results = [r for r in preferred_results if r]
                
                if preferred_results:
                    # Use the scoring system to select the best result from the preferred method
                    best_text = self._select_best_text(preferred_results)
                    logger.info(f"Selected OCR text from {self.preferred_method}: '{best_text}'")
                else:
                    # Fall back to auto selection if no results from preferred method
                    best_text = self._select_best_text(results)
                    logger.info(f"Fallback to auto-selected OCR text: '{best_text}'")
            
            # Always save the final OCR output with timestamp
            timestamp = int(time.time())
            final_output = {
                'timestamp': timestamp,
                'text': best_text,
                'method': self.preferred_method,
                'results_by_method': results_by_method
            }
            
            # Save final OCR output as JSON
            import json
            with open(str(ocr_output_dir / f'ocr_result_{timestamp}.json'), 'w') as f:
                json.dump(final_output, f, indent=4)
            
            # Save the image that produced the best result
            if best_text:
                cv2.imwrite(str(ocr_output_dir / f'ocr_image_{timestamp}.png'), image)
            
            # Update debug window if available and debug mode is enabled
            if debug_enabled and hasattr(self, 'debug_window') and self.debug_window:
                # Use the preferred method's image for visualization
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
        
    def _process_region(self) -> None:
        """
        Process the selected region for OCR.
        
        This method:
        1. Takes a screenshot of the selected region
        2. Saves the screenshot for debugging if debug mode is enabled
        3. Processes the image to extract text
        4. Extracts coordinates from the text
        5. Updates the game state and emits signals
        """
        try:
            # Check if cancellation was requested
            if self._cancellation_requested:
                logger.info("OCR processing cancelled")
                return
                
            if not self.region:
                logger.warning("No region selected for OCR")
                # Even if no region is selected, still emit the last known coordinates
                if self.game_state and self.game_state.get_coordinates():
                    self.coordinates_updated.emit(self.game_state.get_coordinates())
                return
                
            logger.info(f"Processing OCR region: {self.region}")
            
            # Check for cancellation again before taking screenshot
            if self._cancellation_requested:
                logger.info("OCR processing cancelled before screenshot")
                return
                
            # Take a screenshot of the selected region
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(self.region))
                
            # Get debug settings
            config = ConfigManager()
            debug_settings = config.get_debug_settings()
            debug_enabled = debug_settings["enabled"]
                
            # Only save debug screenshots if debug mode is enabled
            if debug_enabled:
                # Ensure the debug directory exists
                debug_dir = Path('scout/debug_screenshots')
                debug_dir.mkdir(exist_ok=True, parents=True)
                
                # Save the original screenshot for debugging
                cv2.imwrite(str(debug_dir / 'OCR Region (Original).png'), screenshot)
                
                # Also save as coord_region.png for consistency with the old system
                cv2.imwrite(str(debug_dir / 'coord_region.png'), screenshot)
            
            # Check for cancellation again before OCR processing
            if self._cancellation_requested:
                logger.info("OCR processing cancelled before text extraction")
                return
                
            # Use our enhanced extract_text method instead of duplicating the OCR logic
            text = self.extract_text(screenshot)
            
            # Check for cancellation again after OCR processing
            if self._cancellation_requested:
                logger.info("OCR processing cancelled after text extraction")
                return
                
            # Log the extracted text
            logger.info(f"OCR extracted text: '{text}'")
            
            # Update debug window with the processed image only if debug mode is enabled
            if debug_enabled:
                # We'll use the image from extract_text which is already processed
                processed_image = cv2.imread(str(debug_dir / 'ocr_thresh1.png'))
                if processed_image is not None and hasattr(self, 'debug_window') and self.debug_window:
                    self.debug_window.update_image(
                        "OCR Region",
                        processed_image,
                        metadata={"raw_text": text},
                        save=True
                    )
                
                    # Also save a copy with a more descriptive name
                    cv2.imwrite(str(debug_dir / 'OCR Region (Processed).png'), processed_image)
            
            # Extract and validate coordinates
            coords = self._extract_coordinates(text)
            
            # Log the result of coordinate extraction
            if coords:
                logger.info(f"Successfully extracted coordinates: {coords}")
            else:
                logger.warning("Failed to extract valid coordinates from OCR text")
                # Even if extraction fails, still emit the last known coordinates
                if self.game_state and self.game_state.get_coordinates():
                    self.coordinates_updated.emit(self.game_state.get_coordinates())
            
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}", exc_info=True)
            # Even if an error occurs, still emit the last known coordinates
            if self.game_state and self.game_state.get_coordinates():
                self.coordinates_updated.emit(self.game_state.get_coordinates())
            
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
                        coords = self.game_state.get_coordinates()
                        
                        # Emit updated coordinates
                        self.coordinates_updated.emit(coords)
                        
                        return coords
                    else:
                        logger.warning("No game state available to update coordinates")
                        return None
                else:
                    logger.warning("One or more coordinates failed validation")
                    # Even if validation fails, still emit the last known coordinates
                    if self.game_state and self.game_state.get_coordinates():
                        self.coordinates_updated.emit(self.game_state.get_coordinates())
                    return None
            else:
                logger.warning("Text does not match the expected coordinate format")
                # Even if pattern matching fails, still emit the last known coordinates
                if self.game_state and self.game_state.get_coordinates():
                    self.coordinates_updated.emit(self.game_state.get_coordinates())
                return None
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}", exc_info=True)
            # Even if an error occurs, still emit the last known coordinates
            if self.game_state and self.game_state.get_coordinates():
                self.coordinates_updated.emit(self.game_state.get_coordinates())
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