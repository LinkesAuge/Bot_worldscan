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
import mss
from pathlib import Path

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
            region: Dictionary with left, top, width, height in physical coordinates
        """
        self.region = region
        logger.info(f"OCR region set to: {region}")
        
        # If active, force an immediate capture
        if self.active:
            self._process_region()
            
    def set_frequency(self, frequency: float) -> None:
        """
        Set the update frequency.
        
        Args:
            frequency: Updates per second
        """
        self.update_frequency = frequency
        if self.active:
            interval = int(1000 / frequency)  # Convert to milliseconds
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval}ms ({frequency} updates/sec)")
            
    def start(self) -> None:
        """Start OCR processing."""
        if self.active:
            return
            
        self.active = True
        interval = int(1000 / self.update_frequency)  # Convert to milliseconds
        self.update_timer.start(interval)
        logger.info(f"OCR started with {self.update_frequency} updates/sec")
        
    def stop(self) -> None:
        """Stop OCR processing."""
        if not self.active:
            return
            
        self.active = False
        self.update_timer.stop()
        logger.info("OCR stopped")
        
    def extract_text(self, image: np.ndarray) -> str:
        """
        Extract text from an image using OCR with enhanced preprocessing.
        
        This method applies multiple preprocessing techniques and OCR configurations
        to maximize the chances of correctly extracting coordinate text from the game UI.
        
        Args:
            image: The image to extract text from (numpy array)
            
        Returns:
            The extracted text as a string
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            # Save the original image for debugging
            debug_dir = Path('scout/debug_screenshots')
            debug_dir.mkdir(exist_ok=True, parents=True)
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
            
            # Save the preprocessed images for debugging
            cv2.imwrite(str(debug_dir / 'ocr_thresh1.png'), thresh1)
            cv2.imwrite(str(debug_dir / 'ocr_thresh2.png'), thresh2)
            cv2.imwrite(str(debug_dir / 'ocr_thresh3.png'), thresh3)
            cv2.imwrite(str(debug_dir / 'ocr_morphed.png'), eroded)
            
            # Try multiple OCR approaches with different configurations
            results = []
            
            # Standard OCR with different preprocessing
            results.append(pytesseract.image_to_string(thresh1).strip())
            results.append(pytesseract.image_to_string(thresh2).strip())
            results.append(pytesseract.image_to_string(thresh3).strip())
            results.append(pytesseract.image_to_string(eroded).strip())
            
            # Try with different PSM modes
            # PSM 6: Assume a single uniform block of text
            results.append(pytesseract.image_to_string(thresh1, config='--psm 6').strip())
            # PSM 7: Treat the image as a single line of text
            results.append(pytesseract.image_to_string(thresh1, config='--psm 7').strip())
            # PSM 8: Treat the image as a single word
            results.append(pytesseract.image_to_string(thresh1, config='--psm 8').strip())
            # PSM 10: Treat the image as a single character
            results.append(pytesseract.image_to_string(thresh1, config='--psm 10').strip())
            
            # Try with character whitelist for coordinates
            results.append(pytesseract.image_to_string(
                thresh1, 
                config='--psm 7 -c tessedit_char_whitelist="0123456789:KXYkxy "'
            ).strip())
            
            results.append(pytesseract.image_to_string(
                thresh2, 
                config='--psm 7 -c tessedit_char_whitelist="0123456789:KXYkxy "'
            ).strip())
            
            # Log all extracted texts for debugging
            for i, text in enumerate(results):
                logger.debug(f"OCR Result {i+1}: '{text}'")
            
            # Choose the best result based on coordinate patterns
            best_text = self._select_best_text(results)
            
            # Log the selected text
            logger.info(f"Selected OCR text: '{best_text}'")
            
            # Update debug window if available
            if hasattr(self, 'debug_window') and self.debug_window:
                self.debug_window.update_image(
                    "OCR Extract",
                    thresh1,  # Use the first preprocessing method for visualization
                    metadata={"raw_text": best_text},
                    save=True
                )
                
            return best_text
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}", exc_info=True)
            return ""
        
    def _select_best_text(self, texts: List[str]) -> str:
        """
        Select the best text from multiple OCR results.
        
        This method uses a scoring system to find the text that most likely 
        contains valid coordinate information in the format K:xxx X:xxx Y:xxx.
        
        Args:
            texts: List of OCR result texts
            
        Returns:
            The best text containing coordinate information
        """
        best_score = -1
        best_text = ""
        
        for text in texts:
            score = 0
            
            # Check for coordinate patterns (K:, X:, Y:)
            if re.search(r'[kK]\s*:?\s*\d+', text):
                score += 3
            if re.search(r'[xX]\s*:?\s*\d+', text):
                score += 3
            if re.search(r'[yY]\s*:?\s*\d+', text):
                score += 3
                
            # Bonus for having all three coordinates
            if (re.search(r'[kK]\s*:?\s*\d+', text) and 
                re.search(r'[xX]\s*:?\s*\d+', text) and 
                re.search(r'[yY]\s*:?\s*\d+', text)):
                score += 5
                
            # Check for numbers (at least 3 digits is good)
            numbers = re.findall(r'\d+', text)
            score += min(len(numbers), 3)
            
            # Bonus for having 3-digit numbers (game coordinates are 3 digits)
            for num in numbers:
                if len(num) == 3:
                    score += 1
                    
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
        Process the selected region for text extraction and coordinate parsing.
        
        This method:
        1. Captures a screenshot of the selected region
        2. Passes it to the extract_text method for OCR processing
        3. Parses coordinates from the extracted text
        4. Updates the game state with the parsed coordinates
        5. Saves debug images for troubleshooting
        """
        if not self.active or not self.region:
            return
        
        try:
            # Take screenshot of region
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(self.region))
            
            # Save the original screenshot for debugging
            debug_dir = Path('scout/debug_screenshots')
            debug_dir.mkdir(exist_ok=True, parents=True)
            cv2.imwrite(str(debug_dir / 'OCR Region (Original).png'), screenshot)
            
            # Use our enhanced extract_text method instead of duplicating the OCR logic
            text = self.extract_text(screenshot)
            
            # Update debug window with the processed image
            # We'll use the image from extract_text which is already processed
            processed_image = cv2.imread(str(debug_dir / 'ocr_thresh1.png'))
            if processed_image is not None:
                self.debug_window.update_image(
                    "OCR Region",
                    processed_image,
                    metadata={"raw_text": text},
                    save=True
                )
                
                # Also save a copy with a more descriptive name
                cv2.imwrite(str(debug_dir / 'OCR Region (Processed).png'), processed_image)
            
            # Extract and validate coordinates
            self._extract_coordinates(text)
            
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}", exc_info=True)
            
    def _extract_coordinates(self, text: str) -> None:
        """
        Extract coordinates from OCR text, handling noise and invalid characters.
        
        Uses advanced regex patterns to find coordinates in various formats:
        - K: number, X: number, Y: number
        - K number X number Y number
        - number number number (assuming K X Y order)
        
        Handles common OCR misrecognitions and cleans the text before parsing.
        
        Args:
            text: The OCR text to parse
        """
        try:
            # Clean text by removing common OCR artifacts and normalizing separators
            cleaned_text = text.replace(';', ':').replace('|', ':').replace('l', '1').replace('O', '0').replace('o', '0')
            
            # Log the cleaned text for debugging
            logger.debug(f"Cleaned OCR text: '{cleaned_text}'")
            
            # Try multiple approaches to extract coordinates
            
            # Approach 1: Look for labeled coordinates with flexible formatting
            # This handles formats like "K:123 X:456 Y:789", "K 123 X 456 Y 789", etc.
            k_match = re.search(r'[kK][^0-9]*(\d+)', cleaned_text)
            x_match = re.search(r'[xX][^0-9]*(\d+)', cleaned_text)
            y_match = re.search(r'[yY][^0-9]*(\d+)', cleaned_text)
            
            # Log the regex matches for debugging
            logger.debug(f"Regex matches - K: {k_match.group(1) if k_match else 'None'}, "
                        f"X: {x_match.group(1) if x_match else 'None'}, "
                        f"Y: {y_match.group(1) if y_match else 'None'}")
            
            # Extract and validate each coordinate
            k_val = None
            x_val = None
            y_val = None
            
            if k_match:
                try:
                    k_val = self._validate_coordinate(int(k_match.group(1)), "K")
                except ValueError:
                    logger.warning(f"Invalid K value found: {k_match.group(1)}")
            
            if x_match:
                try:
                    x_val = self._validate_coordinate(int(x_match.group(1)), "X")
                except ValueError:
                    logger.warning(f"Invalid X value found: {x_match.group(1)}")
            
            if y_match:
                try:
                    y_val = self._validate_coordinate(int(y_match.group(1)), "Y")
                except ValueError:
                    logger.warning(f"Invalid Y value found: {y_match.group(1)}")
            
            # Approach 2: If we couldn't find labeled coordinates, try to extract just numbers
            if k_val is None and x_val is None and y_val is None:
                # Look for sequences of digits
                numbers = re.findall(r'\d+', cleaned_text)
                logger.debug(f"Found numbers: {numbers}")
                
                # If we have exactly 3 numbers, assume they are K, X, Y in that order
                if len(numbers) == 3:
                    try:
                        k_val = self._validate_coordinate(int(numbers[0]), "K")
                        x_val = self._validate_coordinate(int(numbers[1]), "X")
                        y_val = self._validate_coordinate(int(numbers[2]), "Y")
                        logger.debug(f"Extracted from number sequence - K: {k_val}, X: {x_val}, Y: {y_val}")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing number sequence: {e}")
            
            # Log the final extracted coordinates
            logger.info(f"Extracted coordinates - K: {k_val}, X: {x_val}, Y: {y_val}")
            
            # Update game state with new coordinates
            self.game_state.update_coordinates(k_val, x_val, y_val)
            
            # Emit updated coordinates
            self.coordinates_updated.emit(self.game_state.get_coordinates())
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}", exc_info=True)
            
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