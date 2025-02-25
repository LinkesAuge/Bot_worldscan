"""
OCR Detection Strategy

This module provides a concrete implementation of the DetectionStrategy
for OCR-based text detection.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import cv2
import logging
import pytesseract
import re

from ..strategy import DetectionStrategy

logger = logging.getLogger(__name__)

class OCRStrategy(DetectionStrategy):
    """
    Strategy for OCR-based text detection.
    
    This strategy:
    - Processes images to extract text using Tesseract OCR
    - Configures preprocessing parameters for optimal text recognition
    - Returns detected text with position information
    - Can filter text based on patterns
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize the OCR strategy.
        
        Args:
            tesseract_cmd: Path to Tesseract executable (if not in system PATH)
        """
        # Set Tesseract command if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
        # Test if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.debug(f"Tesseract version: {pytesseract.get_tesseract_version()}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            
        logger.debug("OCR strategy initialized")
    
    def get_name(self) -> str:
        """
        Get the name of this detection strategy.
        
        Returns:
            Strategy name for identification
        """
        return "ocr"
    
    def get_required_params(self) -> List[str]:
        """
        Get the required parameters for this strategy.
        
        Returns:
            List of parameter names that must be provided to detect()
        """
        return []  # No required parameters, all have defaults
    
    def detect(self, image: np.ndarray, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform OCR on an image.
        
        Args:
            image: Image to analyze
            params: Detection parameters including:
                - region: Region to process {left, top, width, height} (None for full image)
                - lang: OCR language (default: 'eng')
                - preprocess: Preprocessing method ('none', 'thresh', 'blur', 'adaptive')
                - psm: Page segmentation mode (default: 6)
                - oem: OCR engine mode (default: 3)
                - whitelist: Character whitelist
                - pattern: Regular expression to match text
                - confidence_threshold: Minimum confidence for text detection (0-100)
            
        Returns:
            List of text detection dictionaries, each containing:
            - 'type': 'text'
            - 'text': Detected text
            - 'x', 'y': Position coordinates
            - 'width', 'height': Text region dimensions
            - 'confidence': Detection confidence (0-100)
        """
        # Extract parameters with defaults
        region = params.get('region')
        lang = params.get('lang', 'eng')
        preprocess_method = params.get('preprocess', 'none')
        psm = params.get('psm', 6)
        oem = params.get('oem', 3)
        whitelist = params.get('whitelist')
        pattern = params.get('pattern')
        confidence_threshold = params.get('confidence_threshold', 0)
        
        # Process region if specified
        if region:
            left, top, width, height = region.get('left', 0), region.get('top', 0), region.get('width', 0), region.get('height', 0)
            
            # Make sure coordinates are valid
            if (left >= 0 and top >= 0 and
                width > 0 and height > 0 and
                left + width <= image.shape[1] and
                top + height <= image.shape[0]):
                
                # Extract region
                image = image[top:top+height, left:left+width]
            else:
                logger.warning(f"Invalid region: {region}, using full image")
        else:
            left, top = 0, 0
        
        # Preprocess image
        processed_image = self._preprocess_image(image, preprocess_method)
        
        # Build configuration string
        config = f'--psm {psm} --oem {oem}'
        if whitelist:
            config += f' -c tessedit_char_whitelist={whitelist}'
            
        # Perform OCR with detailed data
        try:
            ocr_data = pytesseract.image_to_data(
                processed_image,
                lang=lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return []
        
        # Extract text with confidence and bounding boxes
        results = []
        
        for i in range(len(ocr_data['text'])):
            # Skip empty text or low confidence
            if not ocr_data['text'][i].strip() or ocr_data['conf'][i] < confidence_threshold:
                continue
                
            # Apply pattern filter if specified
            if pattern and not re.search(pattern, ocr_data['text'][i]):
                continue
                
            # Create result with absolute coordinates
            x = ocr_data['left'][i] + left
            y = ocr_data['top'][i] + top
            width = ocr_data['width'][i]
            height = ocr_data['height'][i]
            confidence = ocr_data['conf'][i]
            
            results.append({
                'type': 'text',
                'text': ocr_data['text'][i],
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'confidence': confidence
            })
        
        logger.debug(f"Detected {len(results)} text regions")
        return results
    
    def _preprocess_image(self, image: np.ndarray, method: str) -> np.ndarray:
        """
        Preprocess image for OCR.
        
        Args:
            image: Input image
            method: Preprocessing method ('none', 'thresh', 'blur', 'adaptive')
            
        Returns:
            Processed image ready for OCR
        """
        # Convert to grayscale if necessary
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        # Apply preprocessing based on method
        if method == 'none':
            return gray
        elif method == 'thresh':
            # Simple thresholding
            _, processed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return processed
        elif method == 'blur':
            # Gaussian blur then threshold
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, processed = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return processed
        elif method == 'adaptive':
            # Adaptive thresholding
            processed = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            return processed
        else:
            logger.warning(f"Unknown preprocessing method: {method}, using none")
            return gray
    
    def get_text(self, image: np.ndarray, params: Dict[str, Any] = None) -> str:
        """
        Extract text from an image without position information.
        
        This is a convenience method for simple text extraction.
        
        Args:
            image: Image to analyze
            params: OCR parameters (same as detect method)
            
        Returns:
            Extracted text as a string
        """
        params = params or {}
        
        # Extract relevant parameters
        lang = params.get('lang', 'eng')
        preprocess_method = params.get('preprocess', 'none')
        psm = params.get('psm', 6)
        oem = params.get('oem', 3)
        whitelist = params.get('whitelist')
        
        # Process region if specified
        region = params.get('region')
        if region:
            left, top, width, height = region.get('left', 0), region.get('top', 0), region.get('width', 0), region.get('height', 0)
            
            # Make sure coordinates are valid
            if (left >= 0 and top >= 0 and
                width > 0 and height > 0 and
                left + width <= image.shape[1] and
                top + height <= image.shape[0]):
                
                # Extract region
                image = image[top:top+height, left:left+width]
        
        # Preprocess image
        processed_image = self._preprocess_image(image, preprocess_method)
        
        # Build configuration string
        config = f'--psm {psm} --oem {oem}'
        if whitelist:
            config += f' -c tessedit_char_whitelist={whitelist}'
            
        # Perform OCR
        try:
            text = pytesseract.image_to_string(
                processed_image,
                lang=lang,
                config=config
            ).strip()
            return text
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "" 