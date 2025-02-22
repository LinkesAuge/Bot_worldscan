from typing import Optional, Dict, Any, List
import logging
import pytesseract
import re
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime

from .capture_manager import CaptureManager

logger = logging.getLogger(__name__)

class OCRProcessor(QObject):
    """
    Handles OCR processing operations.
    
    This class provides:
    - Text extraction from captured regions
    - OCR result filtering and cleaning
    - Performance metrics tracking
    - Debug information
    """
    
    # Signals
    text_found = pyqtSignal(str, str)  # region_name, text
    text_failed = pyqtSignal(str, str)  # region_name, error
    
    def __init__(
        self,
        capture_manager: CaptureManager,
        tesseract_cmd: Optional[str] = None,
        lang: str = "eng"
    ) -> None:
        """
        Initialize OCR processor.
        
        Args:
            capture_manager: Capture manager instance
            tesseract_cmd: Optional path to tesseract executable
            lang: OCR language
        """
        super().__init__()
        
        self.capture_manager = capture_manager
        
        # Configure tesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
        self.lang = lang
        self.config = {
            "lang": lang,
            "tesseract_config": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789"
        }
        
        # Performance metrics
        self.ocr_metrics: Dict[str, Any] = {
            "total_extractions": 0,
            "failed_extractions": 0,
            "avg_processing_time": 0.0,
            "last_extraction": None
        }
        
        logger.debug("OCR processor initialized")
        
    def _process_region(
        self,
        region_name: str,
        save_debug: bool = False
    ) -> Optional[str]:
        """
        Process OCR region and extract text.
        
        Args:
            region_name: Name of region to process
            save_debug: Whether to save debug image
            
        Returns:
            Extracted text if successful
        """
        try:
            start_time = datetime.now()
            
            # Capture region
            image = self.capture_manager.capture_region(
                region_name,
                save_debug
            )
            if image is None:
                raise RuntimeError("Region capture failed")
                
            # Preprocess for OCR
            image = self.capture_manager.preprocess_image(
                image,
                for_ocr=True
            )
            
            # Perform OCR
            text = pytesseract.image_to_string(
                image,
                lang=self.config["lang"],
                config=self.config["tesseract_config"]
            )
            
            # Clean result
            text = self._clean_text(text)
            
            # Update metrics
            self._update_metrics(True, start_time)
            
            if text:
                self.text_found.emit(region_name, text)
                logger.debug(f"Extracted text from '{region_name}': {text}")
            else:
                logger.debug(f"No text found in region '{region_name}'")
                
            return text
            
        except Exception as e:
            error_msg = f"OCR processing failed: {str(e)}"
            logger.error(error_msg)
            self._update_metrics(False, start_time)
            self.text_failed.emit(region_name, error_msg)
            return None
            
    def _clean_text(self, text: str) -> str:
        """
        Clean OCR result text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        try:
            # Remove whitespace
            text = text.strip()
            
            # Remove non-digit characters
            text = re.sub(r'[^0-9]', '', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            return text
            
    def _update_metrics(
        self,
        success: bool,
        start_time: datetime
    ) -> None:
        """
        Update OCR performance metrics.
        
        Args:
            success: Whether extraction was successful
            start_time: Start time of processing
        """
        try:
            # Calculate processing time
            processing_time = (
                datetime.now() - start_time
            ).total_seconds()
            
            # Update counters
            self.ocr_metrics["total_extractions"] += 1
            if not success:
                self.ocr_metrics["failed_extractions"] += 1
                
            # Update timing metrics
            avg = self.ocr_metrics["avg_processing_time"]
            self.ocr_metrics["avg_processing_time"] = (
                avg * 0.9 + processing_time * 0.1
            )
            self.ocr_metrics["last_extraction"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def get_debug_info(self) -> Dict[str, Any]:
        """Get current OCR state for debugging."""
        return {
            "metrics": self.ocr_metrics,
            "config": self.config
        }
        
    def set_tesseract_config(
        self,
        config: Dict[str, str]
    ) -> None:
        """
        Update tesseract configuration.
        
        Args:
            config: Dictionary containing OCR configuration
                - lang: OCR language
                - tesseract_config: Tesseract configuration string
        """
        try:
            self.config.update(config)
            logger.debug(f"Updated tesseract config: {self.config}")
            
        except Exception as e:
            logger.error(f"Error updating tesseract config: {e}")
            
    def get_supported_languages(self) -> List[str]:
        """Get list of supported OCR languages."""
        try:
            languages = pytesseract.get_languages()
            if not languages:
                logger.warning("No languages found, falling back to English")
                return ["eng"]
            return languages
            
        except Exception as e:
            logger.error(f"Error getting languages: {e}")
            return ["eng"]  # Fallback to English

# Alias for backward compatibility
process_region = OCRProcessor._process_region 