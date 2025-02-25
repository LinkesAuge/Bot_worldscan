"""
Template Matching Strategy

This module provides a concrete implementation of the DetectionStrategy
for template matching based detection.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import cv2
import logging
import os
from pathlib import Path

from ..strategy import DetectionStrategy

logger = logging.getLogger(__name__)

class TemplateMatchingStrategy(DetectionStrategy):
    """
    Strategy for template matching detection.
    
    This strategy:
    - Loads template images from disk
    - Searches for templates in captured screenshots
    - Configures confidence threshold and matching method
    - Returns standardized match results
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template matching strategy.
        
        Args:
            templates_dir: Directory containing template images (default: scout/resources/templates)
        """
        # Set default templates directory if not provided
        if templates_dir is None:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            templates_dir = current_dir.parent.parent.parent / "resources" / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, tuple] = {}
        self.match_method = cv2.TM_CCOEFF_NORMED
        
        # Load templates
        self._load_templates()
        
        logger.debug(f"Template matching strategy initialized with {len(self.templates)} templates")
    
    def get_name(self) -> str:
        """
        Get the name of this detection strategy.
        
        Returns:
            Strategy name for identification
        """
        return "template"
    
    def get_required_params(self) -> List[str]:
        """
        Get the required parameters for this strategy.
        
        Returns:
            List of parameter names that must be provided to detect()
        """
        return ["confidence"]
    
    def detect(self, image: np.ndarray, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform template matching on an image.
        
        Args:
            image: Image to analyze
            params: Detection parameters including:
                - confidence: Confidence threshold (0.0-1.0)
                - template_names: List of template names to search for (None for all)
                - match_method: OpenCV match method (optional)
                - max_matches: Maximum number of matches per template (optional)
                - group_threshold: Pixel distance for grouping matches (optional)
            
        Returns:
            List of match dictionaries, each containing:
            - 'type': 'template'
            - 'template_name': Name of matched template
            - 'x', 'y': Position coordinates
            - 'width', 'height': Template dimensions
            - 'confidence': Match confidence (0.0-1.0)
        """
        # Extract parameters with defaults
        confidence = params.get('confidence', 0.8)
        template_names = params.get('template_names')
        match_method = params.get('match_method', self.match_method)
        max_matches = params.get('max_matches', 10)
        group_threshold = params.get('group_threshold', 10)
        
        # Select templates to match
        if template_names:
            selected_templates = {
                name: template for name, template in self.templates.items()
                if name in template_names
            }
        else:
            selected_templates = self.templates
            
        logger.debug(f"Matching {len(selected_templates)} templates with confidence {confidence}")
        
        results = []
        
        # Process each template
        for name, template in selected_templates.items():
            # Skip if image is smaller than template
            if (image.shape[0] < template.shape[0] or 
                image.shape[1] < template.shape[1]):
                logger.warning(f"Image too small for template {name}")
                continue
                
            # Perform template matching
            try:
                result = cv2.matchTemplate(image, template, match_method)
            except Exception as e:
                logger.error(f"Error matching template {name}: {e}")
                continue
                
            # Find locations above threshold
            locations = np.where(result >= confidence)
            
            # Convert to list of matches
            matches = []
            for y, x in zip(*locations):
                matches.append((int(x), int(y), float(result[y, x])))
                
            # Sort by confidence (highest first)
            matches.sort(key=lambda m: m[2], reverse=True)
            
            # Limit to max matches
            matches = matches[:max_matches]
            
            # Group similar matches (non-maxima suppression)
            if group_threshold > 0:
                grouped_matches = []
                while matches:
                    # Take the best match
                    best_match = matches.pop(0)
                    best_x, best_y, best_conf = best_match
                    
                    # Compare with remaining matches
                    i = 0
                    while i < len(matches):
                        x, y, _ = matches[i]
                        # If too close to best match, remove
                        if (abs(x - best_x) <= group_threshold and 
                            abs(y - best_y) <= group_threshold):
                            matches.pop(i)
                        else:
                            i += 1
                            
                    grouped_matches.append(best_match)
                    
                matches = grouped_matches
                
            # Convert to result format
            width, height = self.template_sizes.get(name, (0, 0))
            for x, y, conf in matches:
                results.append({
                    'type': 'template',
                    'template_name': name,
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'confidence': conf
                })
                
        logger.debug(f"Found {len(results)} template matches")
        return results
    
    def _load_templates(self) -> None:
        """Load all template images from templates directory."""
        self.templates = {}
        self.template_sizes = {}
        
        try:
            if not self.templates_dir.exists():
                logger.warning(f"Templates directory not found: {self.templates_dir}")
                return
                
            # Look for PNG files in templates directory
            template_files = list(self.templates_dir.glob("*.png"))
            logger.debug(f"Found {len(template_files)} template files")
            
            # Load each template
            for template_file in template_files:
                try:
                    # Read as grayscale
                    template = cv2.imread(str(template_file), cv2.IMREAD_UNCHANGED)
                    
                    if template is None:
                        logger.warning(f"Failed to load template: {template_file}")
                        continue
                        
                    # If template has alpha channel, handle it
                    if template.shape[2] == 4:
                        # Use alpha as mask
                        bgr = template[:, :, :3]
                        alpha = template[:, :, 3]
                        
                        # Create mask from alpha channel
                        mask = alpha > 0
                        
                        # Convert to BGR only, make transparent regions black
                        template = bgr.copy()
                        template[~mask] = 0
                    
                    # Store template and its size
                    name = template_file.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    
                    logger.debug(f"Loaded template '{name}': {template.shape}")
                    
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def reload_templates(self) -> None:
        """Reload all template images from disk."""
        self._load_templates()
        
    def get_template_names(self) -> List[str]:
        """
        Get a list of all available template names.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys()) 