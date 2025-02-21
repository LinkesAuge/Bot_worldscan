from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
import mss
import os
from pathlib import Path
from dataclasses import dataclass
from time import time
import logging
import win32gui
import win32ui
import win32con
from scout.window_manager import WindowManager
from scout.sound_manager import SoundManager
from scout.debug_window import DebugWindow
from scout.window_capture import WindowCapture

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """
    Represents a single pattern match result from image recognition.
    
    This class stores information about where a template was found in the game window,
    how confident we are in the match, and the template's properties. Each match
    represents one detected game element.
    
    Attributes:
        position: (x, y) pixel coordinates where the match was found
        confidence: How certain we are about the match (0.0 to 1.0, higher is better)
        width: Width of the matched template in pixels
        height: Height of the matched template in pixels
        template_name: Name of the template image that was matched
    """
    position: Tuple[int, int]
    confidence: float
    width: int
    height: int
    template_name: str

@dataclass
class GroupedMatch:
    """
    Represents a group of similar matches.
    
    Attributes:
        bounds: Tuple of (x1, y1, x2, y2) coordinates
        confidence: Average confidence of matches in group
        template_name: Name of the matched template
    """
    bounds: Tuple[int, int, int, int]
    confidence: float
    template_name: str

class PatternMatcher:
    """
    Core image recognition system for detecting game elements.
    
    This class handles:
    1. Loading template images that represent game elements to detect
    2. Capturing the game window for analysis
    3. Using OpenCV to find matches between templates and the game window
    4. Grouping nearby matches to avoid duplicates
    5. Maintaining performance metrics (updates per second)
    
    The pattern matcher can be configured for different sensitivity levels
    and performance targets. It works with the overlay system to visualize
    detected elements.
    """
    
    def __init__(self, window_manager: WindowManager, confidence: float = 0.8, 
                 target_frequency: float = 1.0, sound_enabled: bool = False,
                 images_dir: str = "scout/images", grouping_threshold: int = 10) -> None:
        """
        Initialize pattern matcher.
        
        Args:
            window_manager: Window manager instance for capturing
            confidence: Minimum confidence threshold for matches
            target_frequency: Target updates per second for scanning
            sound_enabled: Whether to enable sound alerts
            images_dir: Directory containing template images (relative to workspace root)
            grouping_threshold: Pixel distance threshold for grouping matches
        """
        self.window_manager = window_manager
        # Initialize window capture with the same window title as window manager
        self.window_capture = WindowCapture(window_manager.window_title)
        self.confidence = confidence
        self.target_frequency = target_frequency
        self.sound_enabled = sound_enabled
        self.images_dir = Path(images_dir)
        self.templates: Dict[str, np.ndarray] = {}
        self.update_frequency = 0.0
        self.last_update_time = 0.0
        self.grouping_threshold = grouping_threshold
        self.debug_mode = False
        
        # Initialize managers
        self.sound_manager = SoundManager()
        self.debug_window = DebugWindow()
        
        # Connect debug window close signal
        self.debug_window.window_closed.connect(self._on_debug_window_closed)
        
        # Load templates on initialization
        self.reload_templates()
        logger.debug("PatternMatcher initialized")
    
    def _on_debug_window_closed(self) -> None:
        """Handle debug window close event."""
        logger.debug("Debug window was closed, disabling debug mode")
        self.debug_mode = False
        # Notify GUI to update debug button state
        if hasattr(self, 'gui_callback'):
            self.gui_callback()
    
    def set_gui_callback(self, callback: callable) -> None:
        """Set callback for notifying GUI of state changes."""
        self.gui_callback = callback
    
    def reload_templates(self) -> None:
        """Reload all template images from the images directory."""
        logger.info(f"Reloading templates from directory: {self.images_dir}")
        self.templates.clear()
        
        if not self.images_dir.exists():
            logger.warning(f"Template directory not found: {self.images_dir}")
            return
            
        template_files = list(self.images_dir.glob("*.png"))
        logger.info(f"Found {len(template_files)} template files: {[f.name for f in template_files]}")
        
        for file in template_files:
            try:
                # Read template and convert to grayscale
                template = cv2.imread(str(file))
                if template is None:
                    logger.warning(f"Failed to load template: {file}")
                    continue
                    
                # Save debug images if debug mode is enabled
                if self.debug_mode:
                    # Update debug window with original and grayscale versions
                    self.debug_window.update_image(
                        f"Template {file.stem} (Original)",
                        template,
                        metadata={"size": f"{template.shape[1]}x{template.shape[0]}"},
                        save=True
                    )
                    
                    # Convert to grayscale for debug view
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    self.debug_window.update_image(
                        f"Template {file.stem} (Gray)",
                        template_gray,
                        metadata={"size": f"{template_gray.shape[1]}x{template_gray.shape[0]}"},
                        save=True
                    )
                    logger.debug(f"Saved debug images for template: {file.stem}")
                
                # Convert to grayscale for actual use
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                template = np.array(template, dtype=np.uint8)
                
                self.templates[file.stem] = template
                logger.debug(f"Loaded template: {file.stem} with shape {template.shape}")
                
            except Exception as e:
                logger.error(f"Error loading template {file}: {str(e)}", exc_info=True)
        
        logger.info(f"Successfully loaded {len(self.templates)} templates")
    
    def set_debug_mode(self, enabled: bool) -> None:
        """
        Enable or disable debug mode.
        
        When debug mode is enabled:
        1. Window captures will be saved during pattern matching
        2. Template debug screenshots will be saved immediately
        3. Debug window will be shown/hidden based on state
        
        Args:
            enabled: Whether to enable debug mode
        """
        self.debug_mode = enabled
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
        if enabled:
            # Show debug window
            self.debug_window.show()
            # Reload templates to generate debug images
            self.reload_templates()
            # Force a capture to show initial state
            screenshot = self.capture_window()
            if screenshot is not None:
                self.find_matches(screenshot)
        else:
            # Hide debug window when disabled
            self.debug_window.hide()
    
    def capture_window(self) -> Optional[np.ndarray]:
        """
        Capture the game window using WindowCapture.
        
        Returns:
            Optional[np.ndarray]: Screenshot as numpy array, or None if capture failed
        """
        try:
            # Use WindowCapture to get the screenshot
            screenshot = self.window_capture.capture_screenshot(method="mss")
            
            if screenshot is None:
                logger.warning("Failed to capture window")
                return None
            
            # Update debug window if debug mode is enabled
            if self.debug_mode:
                self.debug_window.update_image(
                    "Last Capture",
                    screenshot,
                    metadata={
                        "size": f"{screenshot.shape[1]}x{screenshot.shape[0]}",
                        "method": "mss"
                    },
                    save=True
                )
                
                # Save grayscale version
                gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                self.debug_window.update_image(
                    "Last Capture (Gray)",
                    gray,
                    metadata={"size": f"{gray.shape[1]}x{gray.shape[0]}"},
                    save=True
                )
                
                logger.debug("Updated debug window with capture images")
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Error capturing window: {e}", exc_info=True)
            return None
    
    def find_matches(self, image: np.ndarray) -> List[GroupedMatch]:
        """
        Find all template matches in the image.
        
        Args:
            image: Image to search in
        
        Returns:
            List of GroupedMatch objects
        """
        try:
            # Convert image to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Update debug window with processed images if debug mode is enabled
            if self.debug_mode:
                # Show original capture
                self.debug_window.update_image(
                    "Current Search Image",
                    image,
                    metadata={
                        "size": f"{image.shape[1]}x{image.shape[0]}",
                        "type": "Original"
                    },
                    save=True
                )
                
                # Show grayscale version
                self.debug_window.update_image(
                    "Current Search Image (Gray)",
                    gray,
                    metadata={
                        "size": f"{gray.shape[1]}x{gray.shape[0]}",
                        "type": "Grayscale"
                    },
                    save=True
                )
            
            all_matches = []
            
            # Process each template
            for template_name, template in self.templates.items():
                # Match template
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                
                # Find matches above threshold
                locations = np.where(result >= self.confidence)
                for y, x in zip(*locations):
                    match = GroupedMatch(
                        bounds=(
                            x,
                            y,
                            x + template.shape[1],
                            y + template.shape[0]
                        ),
                        confidence=result[y, x],
                        template_name=template_name
                    )
                    all_matches.append(match)
                    
                # Update debug window with match visualization if in debug mode
                if self.debug_mode and len(locations[0]) > 0:
                    # Create visualization
                    debug_img = image.copy()
                    for match in all_matches:
                        if match.template_name == template_name:
                            x1, y1, x2, y2 = match.bounds
                            cv2.rectangle(
                                debug_img,
                                (x1, y1),
                                (x2, y2),
                                (0, 255, 0),
                                2
                            )
                            # Add confidence score
                            cv2.putText(
                                debug_img,
                                f"{match.confidence:.2f}",
                                (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                1
                            )
                    
                    self.debug_window.update_image(
                        f"Matches - {template_name}",
                        debug_img,
                        metadata={
                            "matches": len(locations[0]),
                            "confidence_threshold": f"{self.confidence:.2f}"
                        },
                        save=True
                    )
                    
                    # Also show the correlation result
                    # Scale to 0-255 for better visualization
                    result_normalized = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
                    self.debug_window.update_image(
                        f"Correlation - {template_name}",
                        result_normalized,
                        metadata={
                            "max_confidence": f"{np.max(result):.2f}",
                            "threshold": f"{self.confidence:.2f}"
                        },
                        save=True
                    )
            
            # Group matches
            grouped = self._group_matches(all_matches)
            
            # If in debug mode, show final grouped matches
            if self.debug_mode and grouped:
                final_img = image.copy()
                for match in grouped:
                    x1, y1, x2, y2 = match.bounds
                    cv2.rectangle(
                        final_img,
                        (x1, y1),
                        (x2, y2),
                        (0, 0, 255),  # Red for grouped matches
                        2
                    )
                    # Add template name and confidence
                    cv2.putText(
                        final_img,
                        f"{match.template_name} ({match.confidence:.2f})",
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1
                    )
                
                self.debug_window.update_image(
                    "Final Grouped Matches",
                    final_img,
                    metadata={
                        "matches": len(grouped),
                        "grouping_threshold": self.grouping_threshold
                    },
                    save=True
                )
            
            return grouped
            
        except Exception as e:
            logger.error(f"Error finding matches: {e}", exc_info=True)
            return []
    
    def _group_matches(self, matches: List[GroupedMatch]) -> List[GroupedMatch]:
        """
        Group nearby matches to avoid duplicates.
        
        Args:
            matches: List of matches to group
        
        Returns:
            List of grouped matches
        """
        if not matches:
            return []
            
        # Sort matches by confidence
        matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        
        # Group matches
        grouped = []
        used = set()
        
        for i, match in enumerate(matches):
            if i in used:
                continue
                
            # Find all matches close to this one
            group = [match]
            center_x = (match.bounds[0] + match.bounds[2]) // 2
            center_y = (match.bounds[1] + match.bounds[3]) // 2
            
            for j, other in enumerate(matches):
                if j == i or j in used:
                    continue
                    
                other_x = (other.bounds[0] + other.bounds[2]) // 2
                other_y = (other.bounds[1] + other.bounds[3]) // 2
                
                # Check if centers are close
                distance = np.sqrt(
                    (center_x - other_x) ** 2 +
                    (center_y - other_y) ** 2
                )
                
                if distance <= self.grouping_threshold:
                    group.append(other)
                    used.add(j)
            
            # Create grouped match
            if len(group) > 1:
                # Average the bounds
                x1 = sum(m.bounds[0] for m in group) // len(group)
                y1 = sum(m.bounds[1] for m in group) // len(group)
                x2 = sum(m.bounds[2] for m in group) // len(group)
                y2 = sum(m.bounds[3] for m in group) // len(group)
                
                grouped_match = GroupedMatch(
                    bounds=(x1, y1, x2, y2),
                    confidence=sum(m.confidence for m in group) / len(group),
                    template_name=group[0].template_name
                )
            else:
                grouped_match = group[0]
            
            grouped.append(grouped_match)
            used.add(i)
        
        return grouped 