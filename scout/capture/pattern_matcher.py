"""Pattern matching system for game elements."""

from typing import Dict, List, Optional, Tuple, NamedTuple, Any
import logging
import cv2
import numpy as np
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect

from .capture_manager import CaptureManager

logger = logging.getLogger(__name__)

class MatchResult(NamedTuple):
    """
    Result of a template match.
    
    Attributes:
        template_name: Name of matched template
        confidence: Match confidence (0-1)
        position: Match center position
        rect: Match bounding rectangle
    """
    template_name: str
    confidence: float
    position: QPoint
    rect: QRect

class PatternMatcher(QObject):
    """
    Handles template matching operations.
    
    This class provides:
    - Template loading and management
    - Pattern matching against captured images
    - Match result filtering and validation
    - Debug visualization
    """
    
    # Signals
    match_found = pyqtSignal(str, float, QPoint)  # template, confidence, position
    match_failed = pyqtSignal(str, str)  # template, error
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(
        self,
        capture_manager: CaptureManager,
        template_dir: str = "scout/templates",
        confidence_threshold: float = 0.8
    ) -> None:
        """Initialize pattern matcher.
        
        Args:
            capture_manager: Capture manager instance
            template_dir: Directory containing template images
            confidence_threshold: Minimum confidence for matches (0-1)
        """
        super().__init__()
        
        self.capture_manager = capture_manager
        self.template_dir = Path(template_dir)
        self.confidence_threshold = confidence_threshold
        self.templates: Dict[str, np.ndarray] = {}
        
        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Load templates
        self.reload_templates()
        
        logger.debug(f"Pattern matcher initialized with template dir: {template_dir}")
        
    def reload_templates(self, subdir: Optional[str] = None) -> None:
        """Reload template images from disk.
        
        Args:
            subdir: Optional subdirectory to load from
        """
        try:
            # Clear existing templates
            self.templates.clear()
            
            # Get template path
            template_path = self.template_dir
            if subdir:
                template_path = template_path / subdir
                
            # Create directory if it doesn't exist
            template_path.mkdir(parents=True, exist_ok=True)
            
            # Load all template images
            for ext in ["*.png", "*.jpg", "*.jpeg"]:
                for file in template_path.glob(ext):
                    try:
                        # Load image
                        image = cv2.imread(str(file))
                        if image is None:
                            logger.error(f"Failed to load template: {file}")
                            continue
                            
                        # Convert to grayscale
                        if len(image.shape) == 3:
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                            
                        # Store template
                        name = file.stem
                        self.templates[name] = image
                        logger.debug(f"Loaded template '{name}' from {file}")
                        
                    except Exception as e:
                        logger.error(f"Error loading template {file}: {e}")
                        continue
                        
            if not self.templates:
                logger.warning(f"No templates found in {template_path}")
            else:
                logger.info(f"Loaded {len(self.templates)} templates from {template_path}")
                
        except Exception as e:
            logger.error(f"Error reloading templates: {e}")
            self.templates.clear()
        
    def _non_max_suppression(
        self,
        matches: List[MatchResult],
        overlap_threshold: float = 0.5
    ) -> List[MatchResult]:
        """
        Apply non-maxima suppression to remove overlapping matches.
        
        Args:
            matches: List of match results
            overlap_threshold: Maximum allowed overlap ratio
            
        Returns:
            Filtered list of matches
        """
        if not matches:
            return []
            
        # Sort matches by confidence
        matches = sorted(matches, key=lambda x: x.confidence, reverse=True)
        
        kept_matches = []
        for match in matches:
            should_keep = True
            match_rect = match.rect
            match_area = match_rect.width() * match_rect.height()
            
            # Check overlap with kept matches
            for kept in kept_matches:
                kept_rect = kept.rect
                
                # Calculate intersection
                intersection = match_rect.intersected(kept_rect)
                if intersection.isEmpty():
                    continue
                    
                # Calculate overlap ratio relative to both rectangles
                intersection_area = intersection.width() * intersection.height()
                kept_area = kept_rect.width() * kept_rect.height()
                
                overlap_ratio = max(
                    intersection_area / match_area,
                    intersection_area / kept_area
                )
                
                if overlap_ratio > overlap_threshold:
                    should_keep = False
                    break
                    
            if should_keep:
                kept_matches.append(match)
                
        return kept_matches

    def find_matches(
        self,
        template_names: Optional[List[str]] = None,
        save_debug: bool = False
    ) -> List[MatchResult]:
        """
        Find matches for loaded templates.
        
        Args:
            template_names: Optional list of template names to match (default: all)
            save_debug: Whether to save debug images
            
        Returns:
            List of match results
        """
        try:
            # Get screenshot in BGR format
            image = self.capture_manager.capture_window(save_debug)
            if image is None:
                logger.error("Failed to capture window")
                return []
            
            # Convert to grayscale for matching
            if len(image.shape) == 3:
                processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                processed = image
                
            if processed is None:
                logger.error("Failed to preprocess image")
                return []
            
            # Track results and failures
            results = []
            failed_templates = []
            
            # Get templates to match
            if template_names is None:
                template_names = list(self.templates.keys())
                
            if not template_names:
                logger.warning("No templates specified for matching")
                return []
                
            # Match each template
            for name in template_names:
                try:
                    if name not in self.templates:
                        failed_templates.append(
                            (name, f"Template '{name}' not found")
                        )
                        continue
                        
                    template = self.templates[name]  # Already in grayscale
                    
                    # Perform template matching
                    result = cv2.matchTemplate(
                        processed,
                        template,
                        cv2.TM_CCOEFF_NORMED
                    )
                    
                    # Find all matches above threshold
                    locations = np.where(result >= self.confidence_threshold)
                    for pt in zip(*locations[::-1]):  # Switch columns and rows
                        # Calculate match center and rectangle
                        template_w, template_h = template.shape[::-1]  # Width and height are reversed in shape
                        
                        # Calculate match rectangle in screen coordinates
                        rect = QRect(
                            int(pt[0]),  # Left
                            int(pt[1]),  # Top
                            template_w,   # Width
                            template_h    # Height
                        )
                        
                        # Calculate center point
                        center = QPoint(
                            rect.x() + rect.width() // 2,
                            rect.y() + rect.height() // 2
                        )
                        
                        # Get confidence at this point
                        confidence = float(result[pt[1], pt[0]])
                        
                        # Create match result
                        match = MatchResult(
                            template_name=name,
                            confidence=confidence,
                            position=center,
                            rect=rect
                        )
                        results.append(match)
                        
                        # Emit match found signal
                        self.match_found.emit(name, confidence, center)
                        logger.debug(f"Found match: {name} at {center} with confidence {confidence:.2f}")
                        
                except Exception as e:
                    error_msg = f"Error matching template {name}: {e}"
                    logger.error(error_msg)
                    failed_templates.append((name, error_msg))
                    continue
                    
            # Emit failures
            for name, error in failed_templates:
                self.match_failed.emit(name, error)
                
            # Apply non-maxima suppression to remove overlapping matches
            if results:
                results = self._non_max_suppression(results)
                
            return results
            
        except Exception as e:
            error_msg = f"Error finding matches: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
            
    def get_template_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about loaded templates."""
        return {
            name: {
                "size": self.templates[name].shape,
                "shape": self.templates[name].shape
            }
            for name in self.templates
        } 