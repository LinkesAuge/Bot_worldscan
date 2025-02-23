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
                
            # Create directory if it doesn't exist
            template_path.mkdir(parents=True, exist_ok=True)
                
            # Load template images
            for img_path in template_path.glob("*.png"):
                try:
                    # Load template in BGR format
                    template = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                    if template is None:
                        logger.error(f"Failed to load template: {img_path}")
                        continue
                    
                    # Store template size before conversion
                    template_size = (template.shape[1], template.shape[0])
                    
                    # Convert to grayscale for matching
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    
                    # Store template
                    name = img_path.stem
                    self.templates[name] = template_gray  # Store grayscale version
                    self.template_sizes[name] = template_size
                    logger.debug(f"Loaded template '{name}': {template_size}")
                    
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
                        template_w, template_h = self.template_sizes[name]
                        center_x = pt[0] + template_w // 2
                        center_y = pt[1] + template_h // 2
                        
                        # Get confidence at this point
                        confidence = float(result[pt[1], pt[0]])
                        
                        # Apply DPI scaling
                        dpi_scale = self.capture_manager.dpi_scale
                        scaled_x = int(center_x / dpi_scale)
                        scaled_y = int(center_y / dpi_scale)
                        scaled_w = int(template_w / dpi_scale)
                        scaled_h = int(template_h / dpi_scale)
                        
                        # Create match result
                        match = MatchResult(
                            template_name=name,
                            confidence=confidence,
                            position=QPoint(scaled_x, scaled_y),
                            rect=QRect(
                                scaled_x - scaled_w // 2,
                                scaled_y - scaled_h // 2,
                                scaled_w,
                                scaled_h
                            )
                        )
                        results.append(match)
                        
                        logger.debug(
                            f"Found match for '{name}': "
                            f"confidence={confidence:.2f}, "
                            f"position=({scaled_x}, {scaled_y})"
                        )
                        
                    if not locations[0].size:
                        msg = f"No matches above threshold {self.confidence_threshold:.2f}"
                        failed_templates.append((name, msg))
                        logger.debug(f"No match for '{name}': {msg}")
                        
                except Exception as e:
                    error_msg = f"Error matching template '{name}': {e}"
                    failed_templates.append((name, error_msg))
                    logger.error(error_msg)
                    
            # Apply non-maxima suppression
            if results:
                results = self._non_max_suppression(results)
                
            # Save debug image if requested
            if save_debug:
                debug_img = image.copy()  # Use original BGR image for visualization
                
                # Draw all template matches
                for match in results:
                    # Draw rectangle in green
                    pt1 = (
                        int(match.rect.left() * self.capture_manager.dpi_scale),
                        int(match.rect.top() * self.capture_manager.dpi_scale)
                    )
                    pt2 = (
                        int(match.rect.right() * self.capture_manager.dpi_scale),
                        int(match.rect.bottom() * self.capture_manager.dpi_scale)
                    )
                    cv2.rectangle(
                        debug_img,
                        pt1,
                        pt2,
                        (0, 255, 0),  # BGR green
                        2
                    )
                    
                    # Draw label
                    label = f"{match.template_name} ({match.confidence:.2f})"
                    label_pt = (
                        pt1[0],
                        max(0, pt1[1] - 10)  # Ensure label is in image
                    )
                    cv2.putText(
                        debug_img,
                        label,
                        label_pt,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),  # BGR green
                        1
                    )
                
                # Save debug image
                cv2.imwrite("debug_screenshots/matches.png", debug_img)
                logger.debug(f"Saved debug image with {len(results)} matches")
                
            # Emit signals for matches
            for match in results:
                self.match_found.emit(
                    match.template_name,
                    match.confidence,
                    match.position
                )
                
            # Emit failure signals in batch
            for name, error in failed_templates:
                self.match_failed.emit(name, error)
                
            return results
            
        except Exception as e:
            error_msg = f"Pattern matching failed: {e}"
            logger.error(error_msg)
            self.match_failed.emit("", error_msg)
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