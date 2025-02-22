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
    
    def __init__(
        self,
        capture_manager: CaptureManager,
        template_dir: str = "images",
        confidence_threshold: float = 0.95
    ) -> None:
        """
        Initialize pattern matcher.
        
        Args:
            capture_manager: Capture manager instance
            template_dir: Directory containing template images
            confidence_threshold: Minimum confidence for valid matches (0.0 to 1.0)
        """
        super().__init__()
        
        self.capture_manager = capture_manager
        self.template_dir = Path(template_dir)
        self.confidence_threshold = confidence_threshold
        
        # Template storage
        self.templates: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, Tuple[int, int]] = {}
        
        # Load initial templates
        self.reload_templates()
        
        logger.debug("Pattern matcher initialized")
        
    def reload_templates(self, subdir: Optional[str] = None) -> None:
        """
        Reload template images from directory.
        
        Args:
            subdir: Optional subdirectory to load from
        """
        try:
            # Clear existing templates
            self.templates.clear()
            self.template_sizes.clear()
            
            # Build template path
            template_path = self.template_dir
            if subdir:
                template_path = template_path / subdir
                
            # Load template images
            for img_path in template_path.glob("*.png"):
                try:
                    # Load and preprocess template
                    template = cv2.imread(str(img_path))
                    if template is None:
                        raise ValueError(f"Failed to load template: {img_path}")
                        
                    # Convert to grayscale
                    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    
                    # Store template
                    name = img_path.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    logger.debug(f"Loaded template '{name}': {self.template_sizes[name]}")
                    
                except Exception as e:
                    logger.error(f"Error loading template {img_path}: {e}")
                    
            logger.info(f"Loaded {len(self.templates)} templates from {template_path}")
            
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            
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
        Find template matches in current window.
        
        Args:
            template_names: Optional list of templates to match
            save_debug: Whether to save debug visualization
            
        Returns:
            List of match results after non-maxima suppression
        """
        try:
            # Capture and preprocess window
            image = self.capture_manager.capture_window(save_debug)
            if image is None:
                error_msg = "Window capture failed"
                logger.error(f"Pattern matching failed: {error_msg}")
                self.match_failed.emit("test", error_msg)
                return []
                
            # Preprocess for pattern matching
            try:
                image = self.capture_manager.preprocess_image(image)
            except Exception as e:
                error_msg = f"Preprocessing error: {e}"
                logger.error(f"Pattern matching failed: {error_msg}")
                self.match_failed.emit("test", error_msg)
                return []
                
            # Select templates to match
            if template_names is None:
                template_names = list(self.templates.keys())
                
            results: List[MatchResult] = []
            
            for name in template_names:
                if name not in self.templates:
                    error_msg = f"Template '{name}' not found"
                    logger.warning(error_msg)
                    self.match_failed.emit(name, error_msg)
                    continue
                    
                try:
                    # Get template
                    template = self.templates[name]
                    
                    # Perform template matching
                    result = cv2.matchTemplate(
                        image,
                        template,
                        cv2.TM_CCOEFF_NORMED
                    )
                    
                    # Find matches above threshold
                    matches = []
                    result_copy = result.copy()
                    
                    # Find initial max value to check threshold
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_copy)
                    
                    # If best match is below threshold, report and continue
                    if max_val < self.confidence_threshold:
                        error_msg = f"Match confidence {max_val:.2f} below threshold {self.confidence_threshold:.2f}"
                        logger.warning(f"Template '{name}' failed: {error_msg}")
                        self.match_failed.emit(name, error_msg)
                        continue
                    
                    # Find all matches above threshold
                    while max_val >= self.confidence_threshold:
                        # Calculate match position and rectangle
                        w, h = self.template_sizes[name]
                        x, y = max_loc
                        
                        # Calculate center position before scaling
                        center_x = x + w//2
                        center_y = y + h//2
                        
                        # Apply DPI scaling
                        dpi_scale = self.capture_manager.dpi_scale
                        scaled_x = int(x * dpi_scale)
                        scaled_y = int(y * dpi_scale)
                        scaled_w = int(w * dpi_scale)
                        scaled_h = int(h * dpi_scale)
                        scaled_center_x = int(center_x * dpi_scale)
                        scaled_center_y = int(center_y * dpi_scale)
                        
                        position = QPoint(scaled_center_x, scaled_center_y)
                        rect = QRect(scaled_x, scaled_y, scaled_w, scaled_h)
                        
                        # Create match result
                        match = MatchResult(
                            name,
                            float(max_val),
                            position,
                            rect
                        )
                        matches.append(match)
                        
                        # Blank out this match to find the next one
                        cv2.rectangle(
                            result_copy,
                            max_loc,
                            (max_loc[0] + w, max_loc[1] + h),
                            0,
                            -1
                        )
                        
                        # Find next best match
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_copy)
                    
                    # Add matches to results and emit signals
                    results.extend(matches)
                    for match in matches:
                        self.match_found.emit(
                            match.template_name,
                            match.confidence,
                            match.position
                        )
                        logger.debug(
                            f"Found match for '{match.template_name}': "
                            f"pos={match.position}, conf={match.confidence:.2f}"
                        )
                        
                except Exception as e:
                    error_msg = f"Matching failed: {e}"
                    logger.error(f"Error matching template '{name}': {error_msg}")
                    self.match_failed.emit(name, error_msg)
                    
            return results
            
        except Exception as e:
            error_msg = f"Pattern matching failed: {e}"
            logger.error(error_msg)
            self.match_failed.emit("test", error_msg)
            return []
            
    def get_template_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about loaded templates."""
        return {
            name: {
                "size": self.template_sizes[name],
                "shape": self.templates[name].shape
            }
            for name in self.templates
        } 