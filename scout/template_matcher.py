"""
Template Matcher

This module provides template matching functionality for detecting game elements.
It uses OpenCV's template matching to find and track specific visual elements
in the game window.
"""

from typing import List, Dict, Optional, Tuple, Any, Union
import cv2
import numpy as np
import logging
from pathlib import Path
from dataclasses import dataclass
from scout.window_manager import WindowManager
from scout.sound_manager import SoundManager
import time

logger = logging.getLogger(__name__)

@dataclass
class TemplateMatch:
    """Represents a single template match result."""
    template_name: str
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get the center point of the match."""
        x, y, w, h = self.bounds
        return (x + w // 2, y + h // 2)

@dataclass
class GroupedMatch:
    """Represents a group of similar template matches."""
    template_name: str
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    matches: List[TemplateMatch]

class TemplateMatcher:
    """
    Handles template matching for game elements.
    
    This class provides functionality to:
    - Load and manage templates
    - Find matches in screenshots
    - Group similar matches
    - Track match frequency and performance
    - Provide visual feedback through overlay
    """
    
    def __init__(self, window_manager: WindowManager, confidence: float = 0.8,
                 target_frequency: float = 1.0, sound_enabled: bool = False):
        """
        Initialize the template matcher.
        
        Args:
            window_manager: WindowManager instance for capturing screenshots
            confidence: Minimum confidence threshold for matches (0.0-1.0)
            target_frequency: Target updates per second
            sound_enabled: Whether to play sounds on matches
        """
        self.window_manager = window_manager
        self.confidence = confidence
        self._target_frequency = target_frequency  # Use private variable
        self.sound_enabled = sound_enabled
        
        # Create sound manager
        self.sound_manager = SoundManager()
        
        # Initialize template storage
        self.templates: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, Tuple[int, int]] = {}
        
        # Performance tracking
        self._update_frequency = 0.0  # Use private variable
        self._last_update_time = 0.0  # Use private variable
        self._update_count = 0  # Track number of updates
        self._frequency_window = 1.0  # Calculate frequency over 1 second window
        self._update_times = []  # Store update timestamps
        
        # Debug settings
        self.debug_mode = False
        self.debug_screenshots_dir = Path("scout/debug_screenshots")
        
        # Load templates
        self.reload_templates()
        
    @property
    def target_frequency(self) -> float:
        """Get target update frequency."""
        return self._target_frequency

    @target_frequency.setter
    def target_frequency(self, value: float) -> None:
        """Set target update frequency."""
        self._target_frequency = max(0.1, min(60.0, value))  # Clamp between 0.1 and 60 Hz
        logger.debug(f"Target frequency set to {self._target_frequency} updates/sec")

    @property
    def update_frequency(self) -> float:
        """Get actual update frequency."""
        return self._update_frequency

    def reset_frequency_tracking(self) -> None:
        """Reset all frequency tracking values."""
        self._update_frequency = 0.0
        self._last_update_time = 0.0
        self._update_count = 0
        self._update_times.clear()
        logger.debug("Frequency tracking reset")

    def update_frequency_tracking(self) -> None:
        """Update the frequency tracking."""
        current_time = time.time()
        
        # Add current update time
        self._update_times.append(current_time)
        
        # Remove old timestamps outside the window
        window_start = current_time - self._frequency_window
        self._update_times = [t for t in self._update_times if t >= window_start]
        
        # Calculate actual frequency over the window
        if len(self._update_times) > 1:
            # Calculate average time between updates
            time_diffs = [self._update_times[i] - self._update_times[i-1] 
                         for i in range(1, len(self._update_times))]
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            self._update_frequency = 1.0 / avg_time_diff if avg_time_diff > 0 else 0.0
        else:
            self._update_frequency = 0.0
            
        self._last_update_time = current_time
        logger.debug(f"Current update frequency: {self._update_frequency:.2f} updates/sec")

    def reload_templates(self) -> None:
        """Reload all template images from the templates directory."""
        try:
            # Clear existing templates
            self.templates.clear()
            self.template_sizes.clear()
            logger.debug("Cleared existing templates")
            
            # Load templates from directory
            templates_dir = Path("scout/templates")
            logger.debug(f"Looking for templates in: {templates_dir.absolute()}")
            
            if not templates_dir.exists():
                logger.warning(f"Templates directory not found at {templates_dir.absolute()}")
                return
                
            template_files = list(templates_dir.glob("*.png"))
            logger.debug(f"Found {len(template_files)} template files: {[f.name for f in template_files]}")
            
            for template_file in template_files:
                try:
                    # Read template image
                    template = cv2.imread(str(template_file))
                    if template is None:
                        logger.error(f"Failed to load template: {template_file}")
                        continue
                        
                    # Store template and its size
                    name = template_file.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    logger.debug(f"Successfully loaded template: {name} ({template.shape[1]}x{template.shape[0]})")
                    
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
                    
            logger.info(f"Loaded {len(self.templates)} templates: {list(self.templates.keys())}")
            
        except Exception as e:
            logger.error(f"Error reloading templates: {e}", exc_info=True)
            
    def find_matches(self, templates_or_image: Union[List[str], np.ndarray], screenshot: Optional[np.ndarray] = None) -> List[GroupedMatch]:
        """
        Find matches for specified templates in a screenshot.
        
        Args:
            templates_or_image: Either a list of template names to search for, or a screenshot to search in
            screenshot: Optional screenshot to search in. If None and templates_or_image is a list, a new screenshot will be taken.
            
        Returns:
            List of GroupedMatch objects
        """
        try:
            # Handle input parameters
            if isinstance(templates_or_image, np.ndarray):
                # Called with a screenshot as first parameter (legacy mode)
                screenshot = templates_or_image
                template_names = list(self.templates.keys())
            else:
                # Called with template names list
                template_names = templates_or_image
                if screenshot is None:
                    screenshot = self.window_manager.capture_screenshot()
                    if screenshot is None:
                        logger.error("Failed to capture screenshot for template matching")
                        return []

            # Convert screenshot to numpy array if needed
            if not isinstance(screenshot, np.ndarray):
                screenshot = np.array(screenshot)
            
            # Convert to grayscale for matching
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            matches = []
            
            # Find matches for each template
            for template_name in template_names:
                if template_name not in self.templates:
                    logger.warning(f"Template '{template_name}' not found")
                    continue
                    
                template = self.templates[template_name]
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # Perform template matching
                result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                
                # Find matches above threshold
                locations = np.where(result >= self.confidence)
                for pt in zip(*locations[::-1]):  # Switch columns and rows
                    x, y = pt
                    confidence = result[y, x]
                    
                    # Create match object
                    match = TemplateMatch(
                        template_name=template_name,
                        bounds=(int(x), int(y), template.shape[1], template.shape[0]),
                        confidence=float(confidence)
                    )
                    matches.append(match)
            
            # Group similar matches
            return self._group_matches(matches)
            
        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return []
            
    def _group_matches(self, matches: List[TemplateMatch], distance_threshold: int = 10) -> List[GroupedMatch]:
        """
        Group similar matches together.
        
        Args:
            matches: List of matches to group
            distance_threshold: Maximum pixel distance between matches to group
            
        Returns:
            List of GroupedMatch objects
        """
        if not matches:
            return []
            
        # Sort matches by confidence
        matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        
        groups: List[List[TemplateMatch]] = []
        used_indices = set()
        
        # Group matches
        for i, match in enumerate(matches):
            if i in used_indices:
                continue
                
            # Start new group
            current_group = [match]
            used_indices.add(i)
            
            # Find similar matches
            for j, other in enumerate(matches):
                if j in used_indices:
                    continue
                    
                # Check if matches are close enough
                if (abs(match.bounds[0] - other.bounds[0]) <= distance_threshold and
                    abs(match.bounds[1] - other.bounds[1]) <= distance_threshold and
                    match.template_name == other.template_name):
                    current_group.append(other)
                    used_indices.add(j)
                    
            groups.append(current_group)
            
        # Convert groups to GroupedMatch objects
        return [
            GroupedMatch(
                template_name=group[0].template_name,
                bounds=group[0].bounds,
                confidence=group[0].confidence,
                matches=group
            )
            for group in groups
        ]
        
    def set_debug_mode(self, enabled: bool) -> None:
        """
        Enable or disable debug mode.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self.debug_mode = enabled
        logger.debug(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
    def capture_window(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window using the window manager.
        
        This method delegates to the window manager's capture_screenshot() method
        to ensure consistent coordinate spaces and capture behavior across the application.
        
        Returns:
            Screenshot as numpy array in BGR format, or None if failed
        """
        # Use window manager's screenshot method to ensure consistency
        screenshot = self.window_manager.capture_screenshot()
        if screenshot is None:
            logger.warning("Failed to capture window through window manager")
            return None
            
        logger.debug(f"Captured window screenshot with shape: {screenshot.shape}")
        return screenshot
        
    def find_all_templates(self, image: np.ndarray) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Find all templates in an image.
        
        Args:
            image: Image to search in (BGR format)
            
        Returns:
            List of tuples (template_name, x, y, w, h, confidence)
        """
        matches = self.find_matches(image)
        
        # Convert to legacy format
        return [
            (match.template_name, *match.bounds, match.confidence)
            for match in matches
        ]
        
    def start_template_matching(self) -> None:
        """Start continuous template matching."""
        logger.info("Starting template matching")
        # This is handled by the overlay system
        
    def stop_template_matching(self) -> None:
        """Stop continuous template matching."""
        logger.info("Stopping template matching")
        # This is handled by the overlay system 

    def get_matches(self) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Get the current matches in a standardized format.
        
        Returns:
            List of tuples (template_name, x, y, width, height, confidence)
        """
        # If there's a current overlay instance and it has cached matches
        if hasattr(self, 'overlay') and hasattr(self.overlay, 'cached_matches'):
            return self.overlay.cached_matches
            
        # Otherwise return empty list
        return [] 