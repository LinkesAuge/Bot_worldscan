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
    
    def detect(self, image: np.ndarray, template_names: Optional[List[str]] = None,
                 confidence_threshold: float = 0.7, match_method: Optional[int] = None,
                 max_results: int = 10, group_threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Perform template matching on an image.
        
        Args:
            image: Image to analyze
            template_names: List of template names to search for (None for all)
            confidence_threshold: Minimum confidence level (0.0-1.0)
            match_method: OpenCV match method (None for default)
            max_results: Maximum number of matches per template
            group_threshold: Pixel distance for grouping matches
            
        Returns:
            List of match dictionaries, each containing:
            - 'type': 'template'
            - 'template_name': Name of matched template
            - 'x', 'y': Position coordinates
            - 'width', 'height': Template dimensions
            - 'confidence': Match confidence (0.0-1.0)
        """
        # Use default match method if not specified
        if match_method is None:
            match_method = self.match_method
        
        # Select templates to match
        if template_names:
            logger.debug(f"Requested templates for matching: {template_names}")
            selected_templates = {}
            missing_templates = []
            
            # Filter to only include templates that exist
            for name in template_names:
                if name in self.templates:
                    selected_templates[name] = self.templates[name]
                else:
                    missing_templates.append(name)
            
            if missing_templates:
                logger.warning(f"Some requested templates not found: {missing_templates}")
                logger.debug(f"Available templates: {sorted(list(self.templates.keys()))}")
        else:
            selected_templates = self.templates
            
        if not selected_templates:
            logger.warning("No valid templates available for matching")
            return []
            
        logger.info(f"Matching {len(selected_templates)} templates with confidence threshold {confidence_threshold}")
        logger.debug(f"Using templates: {sorted(list(selected_templates.keys()))}")
        logger.debug(f"Image dimensions: {image.shape}")
        
        results = []
        
        # Process each template
        for name, template in selected_templates.items():
            logger.debug(f"Processing template '{name}': {template.shape}")
            
            # Skip if image is smaller than template
            if (image.shape[0] < template.shape[0] or 
                image.shape[1] < template.shape[1]):
                logger.warning(f"Image too small for template '{name}': image={image.shape}, template={template.shape}")
                continue
                
            # Perform template matching
            try:
                logger.debug(f"Running template matching for '{name}' with method {match_method}")
                result = cv2.matchTemplate(image, template, match_method)
                
                # Find locations above threshold
                locations = np.where(result >= confidence_threshold)
                match_count = len(locations[0]) if locations[0].size > 0 else 0
                
                logger.debug(f"Found {match_count} potential matches for template '{name}' above threshold {confidence_threshold}")
                
                # Convert to list of matches
                matches = []
                for y, x in zip(*locations):
                    matches.append((int(x), int(y), float(result[y, x])))
                    
                # Sort by confidence (highest first)
                matches.sort(key=lambda m: m[2], reverse=True)
                
                # Limit to max matches
                if len(matches) > max_results:
                    logger.debug(f"Limiting {len(matches)} matches to {max_results} for template '{name}'")
                    matches = matches[:max_results]
                
                # Group similar matches (non-maxima suppression)
                if group_threshold > 0 and len(matches) > 1:
                    before_count = len(matches)
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
                    logger.debug(f"Grouped matches from {before_count} to {len(matches)} for template '{name}'")
                
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
                
            except Exception as e:
                logger.error(f"Error matching template '{name}': {e}", exc_info=True)
                
        logger.info(f"Found total of {len(results)} template matches across all templates")
        
        # Log top matches for debugging
        if results:
            # Sort by confidence score
            sorted_results = sorted(results, key=lambda r: r.get('confidence', 0), reverse=True)
            top_matches = sorted_results[:min(5, len(sorted_results))]
            
            logger.debug("Top matches:")
            for i, match in enumerate(top_matches):
                logger.debug(f"  {i+1}. Template: {match.get('template_name')}, "
                            f"Confidence: {match.get('confidence'):.3f}, "
                            f"Position: ({match.get('x')}, {match.get('y')})")
        
        return results
    
    def _load_templates(self) -> None:
        """Load all template images from templates directory."""
        self.templates = {}
        self.template_sizes = {}
        
        try:
            logger.info(f"Loading templates from directory: {self.templates_dir}")
            
            if not self.templates_dir.exists():
                logger.warning(f"Templates directory not found: {self.templates_dir}")
                # Try to create the directory
                try:
                    self.templates_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created templates directory: {self.templates_dir}")
                except Exception as e:
                    logger.error(f"Failed to create templates directory: {e}")
                return
                
            # Log directory contents for debugging
            all_files = list(self.templates_dir.glob("*"))
            logger.debug(f"Directory contains {len(all_files)} files/dirs: {[f.name for f in all_files]}")
            
            # Look for PNG files in templates directory
            template_files = list(self.templates_dir.glob("*.png"))
            logger.info(f"Found {len(template_files)} PNG template files")
            
            if not template_files:
                # Try checking for other image formats
                other_image_files = list(self.templates_dir.glob("*.jp*g")) + list(self.templates_dir.glob("*.bmp"))
                if other_image_files:
                    logger.warning(f"Found {len(other_image_files)} non-PNG image files which won't be used: {[f.name for f in other_image_files]}")
                    logger.warning("Only PNG files are supported for templates")
                else:
                    logger.warning("No image files found in templates directory")
            
            # Load each template
            successful_loads = 0
            for template_file in template_files:
                try:
                    logger.debug(f"Loading template: {template_file.name}")
                    
                    # Read as grayscale
                    template = cv2.imread(str(template_file), cv2.IMREAD_UNCHANGED)
                    
                    if template is None:
                        logger.warning(f"Failed to load template: {template_file} - file may be corrupt or empty")
                        continue
                        
                    # Log template details
                    logger.debug(f"Template dimensions: {template.shape}")
                    
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
                        
                        logger.debug(f"Processed template with alpha channel: {template_file.name}")
                    
                    # Store template and its size
                    name = template_file.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    
                    logger.debug(f"Successfully loaded template '{name}': {template.shape}")
                    successful_loads += 1
                    
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}", exc_info=True)
            
            # Log summary
            logger.info(f"Successfully loaded {successful_loads} of {len(template_files)} templates")
            logger.info(f"Available templates: {sorted(list(self.templates.keys()))}")
                    
        except Exception as e:
            logger.error(f"Error loading templates: {e}", exc_info=True)
    
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