from typing import List, Tuple, Optional, Dict
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
    Represents a group of similar matches that are close together.
    
    When multiple matches of the same template are found near each other,
    they are grouped together to avoid duplicate detections. This class
    represents such a group with averaged properties.
    
    Attributes:
        position: Top-left coordinates of the group's bounding box
        width: Average width of all matches in the group
        height: Average height of all matches in the group
        confidence: Highest confidence score among all matches
        template_name: Name of the matched template
        match_count: Number of individual matches in this group
        bounds: (min_x, min_y, max_x, max_y) of the group's bounding box
        group_id: Unique identifier for this group
    """
    position: Tuple[int, int]
    width: int
    height: int
    confidence: float
    template_name: str
    match_count: int
    bounds: Tuple[int, int, int, int]
    group_id: int

class PatternMatcher:
    """
    Core image recognition system for detecting game elements.
    
    This class handles:
    1. Loading template images that represent game elements to detect
    2. Capturing the game window for analysis
    3. Using OpenCV to find matches between templates and the game window
    4. Grouping nearby matches to avoid duplicates
    5. Maintaining performance metrics (FPS)
    
    The pattern matcher can be configured for different sensitivity levels
    and performance targets. It works with the overlay system to visualize
    detected elements.
    """
    
    def __init__(self, window_manager: WindowManager, confidence: float = 0.8, 
                 target_fps: float = 1.0, sound_enabled: bool = False,
                 images_dir: str = "scout/images", grouping_threshold: int = 10) -> None:
        """
        Initialize pattern matcher.
        
        Args:
            window_manager: Window manager instance for capturing
            confidence: Minimum confidence threshold for matches
            target_fps: Target frames per second for scanning
            sound_enabled: Whether to enable sound alerts
            images_dir: Directory containing template images (relative to workspace root)
            grouping_threshold: Pixel distance threshold for grouping matches
        """
        self.window_manager = window_manager
        self.confidence = confidence
        self.target_fps = target_fps
        self.sound_enabled = sound_enabled
        self.images_dir = Path(images_dir)
        self.templates: Dict[str, np.ndarray] = {}
        self.fps = 0.0
        self.last_capture_time = 0.0
        self.grouping_threshold = grouping_threshold
        self.client_offset_x = 0
        self.client_offset_y = 0
        
        # Initialize sound manager
        self.sound_manager = SoundManager()
        
        # Load templates on initialization
        self.reload_templates()
        logger.debug("PatternMatcher initialized")
    
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
                    
                # Save original template for debugging
                debug_dir = Path("debug_screenshots")
                debug_dir.mkdir(exist_ok=True)
                cv2.imwrite(str(debug_dir / f"template_original_{file.stem}.png"), template)
                
                # Convert to grayscale and ensure correct format
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                cv2.imwrite(str(debug_dir / f"template_gray_{file.stem}.png"), template)
                
                template = np.array(template, dtype=np.uint8)
                
                self.templates[file.stem] = template
                logger.debug(f"Loaded template: {file.stem} with shape {template.shape}")
                
            except Exception as e:
                logger.error(f"Error loading template {file}: {str(e)}", exc_info=True)
        
        logger.info(f"Successfully loaded {len(self.templates)} templates")
    
    def find_matches(self, confidence_threshold: float = None) -> List[GroupedMatch]:
        """
        Find matches for all templates in the window.
        
        Args:
            confidence_threshold: Optional override for confidence threshold. If None, uses class's confidence value.
            
        Returns:
            List[GroupedMatch]: List of grouped matches above the confidence threshold
        """
        # Use class confidence if no threshold provided
        threshold = confidence_threshold if confidence_threshold is not None else self.confidence
        logger.info(f"Starting pattern matching with confidence threshold: {threshold}")
        
        if not self.templates:
            logger.warning("No templates loaded!")
            return []
            
        logger.info(f"Loaded templates: {list(self.templates.keys())}")
        
        try:
            # Capture window
            img = self.capture_window()
            if img is None:
                logger.warning("Failed to capture window")
                return []
            
            logger.debug(f"Captured image size: {img.shape}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Save debug image
            debug_dir = Path("debug_screenshots")
            debug_dir.mkdir(exist_ok=True)
            cv2.imwrite(str(debug_dir / "captured_window.png"), img)
            cv2.imwrite(str(debug_dir / "captured_window_gray.png"), gray)
            
            # Calculate FPS
            current_time = time()
            if self.last_capture_time > 0:
                self.fps = 1.0 / (current_time - self.last_capture_time)
                logger.debug(f"Current FPS: {self.fps:.2f}")
            self.last_capture_time = current_time
            
            # Process each template
            all_matches = []
            for name, template in self.templates.items():
                try:
                    logger.debug(f"Processing template '{name}' with shape {template.shape}")
                    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                    locations = np.where(result >= threshold)  # Use current threshold
                    match_count = len(locations[0])
                    logger.debug(f"Found {match_count} potential matches for template '{name}'")
                    
                    for pt in zip(*locations[::-1]):
                        confidence = result[pt[1], pt[0]]
                        match = MatchResult(
                            position=pt,
                            confidence=confidence,
                            width=template.shape[1],
                            height=template.shape[0],
                            template_name=name
                        )
                        all_matches.append(match)
                        logger.debug(f"Match: {name} at {pt} with confidence {confidence:.2f}")
                        
                except Exception as e:
                    logger.error(f"Error matching template {name}: {e}", exc_info=True)
            
            # Group matches
            grouped_matches = self._group_matches(all_matches)
            
            # Play sound if matches found and sound is enabled
            if grouped_matches and self.sound_enabled:
                self.sound_manager.play_if_ready()
                
            logger.info(f"Found {len(grouped_matches)} grouped matches from {len(all_matches)} total matches")
            return grouped_matches
            
        except Exception as e:
            logger.error(f"Error in pattern matching: {e}", exc_info=True)
            return []
    
    def _group_matches(self, matches: List[MatchResult]) -> List[GroupedMatch]:
        """Group nearby matches together."""
        if not matches:
            return []
            
        groups = []
        used = set()
        group_id = 0
        
        for i, match in enumerate(matches):
            if i in used:
                continue
                
            # Start new group
            group = [match]
            used.add(i)
            
            # Find nearby matches
            for j, other in enumerate(matches[i+1:], i+1):
                if j in used:
                    continue
                    
                # Check if match is close to any in current group
                for grouped_match in group:
                    dist = np.sqrt(
                        (other.position[0] - grouped_match.position[0])**2 +
                        (other.position[1] - grouped_match.position[1])**2
                    )
                    if dist <= self.grouping_threshold:
                        group.append(other)
                        used.add(j)
                        break
            
            # Create group summary
            min_x = min(m.position[0] for m in group)
            min_y = min(m.position[1] for m in group)
            max_x = max(m.position[0] + m.width for m in group)
            max_y = max(m.position[1] + m.height for m in group)
            
            groups.append(GroupedMatch(
                position=(min_x, min_y),
                width=int((max_x - min_x) / len(group)),
                height=int((max_y - min_y) / len(group)),
                confidence=max(m.confidence for m in group),
                template_name=group[0].template_name,
                match_count=len(group),
                bounds=(min_x, min_y, max_x, max_y),
                group_id=group_id
            ))
            group_id += 1
        
        return groups 

    def capture_window(self) -> Optional[np.ndarray]:
        """Capture the game window."""
        try:
            if not self.window_manager.find_window():
                return None
            
            # Get window position
            pos = self.window_manager.get_window_position()
            if not pos:
                return None
            
            x, y, width, height = pos
            window_title = win32gui.GetWindowText(self.window_manager.hwnd)
            logger.info(f"Capturing window: '{window_title}' at ({x}, {y}) size: {width}x{height}")
            
            # Try to get the actual client area for Chrome
            if "Chrome" in window_title:
                try:
                    import ctypes
                    from ctypes.wintypes import RECT
                    
                    # Get client rect (actual content area)
                    rect = RECT()
                    ctypes.windll.user32.GetClientRect(self.window_manager.hwnd, ctypes.byref(rect))
                    client_width = rect.right - rect.left
                    client_height = rect.bottom - rect.top
                    
                    # Get client area position
                    point = ctypes.wintypes.POINT(0, 0)
                    ctypes.windll.user32.ClientToScreen(self.window_manager.hwnd, ctypes.byref(point))
                    client_x, client_y = point.x, point.y
                    
                    # Calculate offset from window to client
                    self.client_offset_x = client_x - x
                    self.client_offset_y = client_y - y
                    
                    logger.info(f"Client area: ({client_x}, {client_y}) size: {client_width}x{client_height}")
                    logger.debug(f"Client offset: ({self.client_offset_x}, {self.client_offset_y})")
                    
                    # Update coordinates to use client area
                    x, y = client_x, client_y
                    width, height = client_width, client_height
                    
                except Exception as e:
                    logger.warning(f"Failed to get client area: {e}")
            
            # Create screenshot
            with mss.mss() as sct:
                monitor = {
                    "left": x,
                    "top": y,
                    "width": width,
                    "height": height
                }
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
            
            # Save debug screenshots
            debug_dir = Path("debug_screenshots")
            debug_dir.mkdir(exist_ok=True)
            
            # Save original screenshot
            cv2.imwrite(str(debug_dir / "last_capture.png"), img)
            
            # Save grayscale version
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(str(debug_dir / "last_capture_gray.png"), gray)
            
            # Save template images for comparison
            for name, template in self.templates.items():
                cv2.imwrite(str(debug_dir / f"template_{name}.png"), template)
            
            logger.info(f"Saved debug screenshots to {debug_dir}")
            
            return img
            
        except Exception as e:
            logger.error(f"Error capturing window: {str(e)}", exc_info=True)
            return None 