"""
Detection Service Module

This module implements the Detection Service, which coordinates different detection
strategies to identify objects and text in screenshots.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np

from scout.core.events.event_bus import EventBus
from scout.core.events.event_types import EventType
from scout.core.events.event import Event
from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.strategy import DetectionStrategy
from scout.core.utils.caching import cache_manager
from scout.core.utils.parallel import image_processor
from scout.core.utils.performance import ExecutionTimer, profile

# Set up logging
logger = logging.getLogger(__name__)

class DetectionService:
    """
    Service for detecting objects and text in screenshots.
    
    This service coordinates different detection strategies (template matching,
    OCR, object detection) and provides a unified interface for the rest of the
    application.
    """
    
    def __init__(self, event_bus: EventBus, window_service: WindowServiceInterface):
        """
        Initialize the detection service.
        
        Args:
            event_bus: Event bus for publishing and subscribing to events
            window_service: Window service for capturing screenshots
        """
        self.event_bus = event_bus
        self.window_service = window_service
        self.strategies: Dict[str, DetectionStrategy] = {}
        self.context = {}
        self._latest_screenshot = None
        self._latest_screenshot_time = 0
        self._cache_timeout = 0.5  # Screenshot cache timeout in seconds
        
    def register_strategy(self, name: str, strategy: DetectionStrategy) -> None:
        """
        Register a detection strategy.
        
        Args:
            name: Name of the strategy
            strategy: Detection strategy implementation
        """
        self.strategies[name] = strategy
        logger.info(f"Registered detection strategy: {name}")
        
    def set_context(self, context: Dict[str, Any]) -> None:
        """
        Set context data for detection operations.
        
        Args:
            context: Context data (e.g., window title, resolution)
        """
        self.context = context
        logger.debug(f"Set detection context: {context}")
        
    def _get_screenshot(self, use_cache: bool = True) -> Optional[np.ndarray]:
        """
        Get a screenshot from the window service.
        
        Args:
            use_cache: Whether to use cached screenshot if available
            
        Returns:
            Screenshot image or None if not available
        """
        # Use cached screenshot if it's recent enough
        current_time = time.time()
        if (use_cache and 
            self._latest_screenshot is not None and 
            current_time - self._latest_screenshot_time < self._cache_timeout):
            logger.debug("Using cached screenshot")
            return self._latest_screenshot
            
        # Get window title from context (for logging purposes)
        window_title = self.context.get('window_title')
        if not window_title:
            logger.warning("No window title in context")
            return None
            
        # Find the window (the window service already knows the title)
        if not self.window_service.find_window():
            logger.warning(f"Window not found: {window_title}")
            return None
            
        # Capture new screenshot
        with ExecutionTimer("Screenshot capture"):
            screenshot = self.window_service.capture_screenshot()
            
        if screenshot is None:
            logger.warning("Failed to capture screenshot")
            return None
            
        # Update cache
        self._latest_screenshot = screenshot
        self._latest_screenshot_time = current_time
        
        return screenshot
    
    @profile(name="detect_template")
    def detect_template(self, template_name: str, confidence_threshold: float = 0.7,
                      max_results: int = 10, region: Optional[Dict[str, int]] = None,
                      use_cache: bool = True) -> List[Dict]:
        """
        Detect a template in the current window.
        
        Args:
            template_name: Name of the template to detect
            confidence_threshold: Minimum confidence level (0.0-1.0)
            max_results: Maximum number of results to return
            region: Region to search in {left, top, width, height} (None for full image)
            use_cache: Whether to use cached results if available
            
        Returns:
            List of detection results with positions and confidence scores
        """
        if 'template' not in self.strategies:
            logger.error("Template matching strategy not registered")
            return []
            
        # Get the strategy
        strategy = self.strategies['template']
        
        # Get screenshot
        screenshot = self._get_screenshot(use_cache)
        if screenshot is None:
            return []
            
        # Crop region if specified
        if region:
            x = region.get('left', 0)
            y = region.get('top', 0)
            w = region.get('width', screenshot.shape[1] - x)
            h = region.get('height', screenshot.shape[0] - y)
            
            # Ensure region is within bounds
            x = max(0, min(x, screenshot.shape[1] - 1))
            y = max(0, min(y, screenshot.shape[0] - 1))
            w = max(1, min(w, screenshot.shape[1] - x))
            h = max(1, min(h, screenshot.shape[0] - y))
            
            detection_image = screenshot[y:y+h, x:x+w]
        else:
            detection_image = screenshot
            x, y = 0, 0
            
        # Check cache for this detection
        params = {
            'template_name': template_name,
            'confidence_threshold': confidence_threshold,
            'max_results': max_results
        }
        
        if use_cache:
            cached_result = cache_manager.detection_cache.get('template', detection_image, params)
            if cached_result is not None:
                logger.debug(f"Using cached template detection result for {template_name}")
                # Adjust coordinates for region if needed
                if region:
                    for result in cached_result:
                        result['x'] += x
                        result['y'] += y
                return cached_result
        
        # Perform detection in parallel tiles if image is large
        if detection_image.shape[0] > 800 or detection_image.shape[1] > 800:
            logger.debug(f"Using parallel processing for large image: {detection_image.shape}")
            
            # Define detection function for each tile
            def detect_in_tile(tile: np.ndarray) -> List[Dict]:
                return strategy.detect(
                    image=tile,
                    template_names=[template_name],
                    confidence_threshold=confidence_threshold,
                    max_results=max_results
                )
            
            # Process image in tiles
            with ExecutionTimer("Parallel template detection"):
                results = image_processor.apply_detection_in_tiles(
                    detection_image,
                    detect_in_tile,
                    tile_size=400,
                    overlap=50,
                    min_distance=20
                )
        else:
            # Regular detection for smaller images
            with ExecutionTimer("Template detection"):
                results = strategy.detect(
                    image=detection_image,
                    template_names=[template_name],
                    confidence_threshold=confidence_threshold,
                    max_results=max_results
                )
        
        # Cache the result
        if use_cache:
            cache_manager.detection_cache.put('template', detection_image, params, results)
        
        # Adjust coordinates for region if needed
        if region:
            for result in results:
                result['x'] += x
                result['y'] += y
                
        # Publish detection event
        self._publish_detection_event('template', results, template_name)
        
        return results
    
    @profile(name="detect_text")
    def detect_text(self, pattern: Optional[str] = None, confidence_threshold: float = 0.6,
                  region: Optional[Dict[str, int]] = None, use_cache: bool = True,
                  preprocess: Optional[str] = None) -> List[Dict]:
        """
        Detect text in the current window.
        
        Args:
            pattern: Regex pattern to match (None for all text)
            confidence_threshold: Minimum confidence level (0.0-1.0)
            region: Region to search in {left, top, width, height} (None for full image)
            use_cache: Whether to use cached results if available
            preprocess: Preprocessing method (None, 'threshold', 'adaptive')
            
        Returns:
            List of text detection results with positions and content
        """
        if 'ocr' not in self.strategies:
            logger.error("OCR strategy not registered")
            return []
            
        # Get the strategy
        strategy = self.strategies['ocr']
        
        # Get screenshot
        screenshot = self._get_screenshot(use_cache)
        if screenshot is None:
            return []
            
        # Crop region if specified
        if region:
            x = region.get('left', 0)
            y = region.get('top', 0)
            w = region.get('width', screenshot.shape[1] - x)
            h = region.get('height', screenshot.shape[0] - y)
            
            # Ensure region is within bounds
            x = max(0, min(x, screenshot.shape[1] - 1))
            y = max(0, min(y, screenshot.shape[0] - 1))
            w = max(1, min(w, screenshot.shape[1] - x))
            h = max(1, min(h, screenshot.shape[0] - y))
            
            detection_image = screenshot[y:y+h, x:x+w]
        else:
            detection_image = screenshot
            x, y = 0, 0
            
        # Check cache for this detection
        params = {
            'pattern': pattern,
            'confidence_threshold': confidence_threshold,
            'preprocess': preprocess
        }
        
        if use_cache:
            cached_result = cache_manager.detection_cache.get('ocr', detection_image, params)
            if cached_result is not None:
                logger.debug("Using cached OCR detection result")
                # Adjust coordinates for region if needed
                if region:
                    for result in cached_result:
                        result['x'] += x
                        result['y'] += y
                return cached_result
        
        # Perform detection - no parallel processing for OCR as it's usually better
        # to process the whole image at once for context
        with ExecutionTimer("OCR detection"):
            results = strategy.detect(
                detection_image,
                pattern=pattern,
                confidence_threshold=confidence_threshold,
                preprocess_method=preprocess
            )
        
        # Cache the result
        if use_cache:
            cache_manager.detection_cache.put('ocr', detection_image, params, results)
        
        # Adjust coordinates for region if needed
        if region:
            for result in results:
                result['x'] += x
                result['y'] += y
                
        # Publish detection event
        self._publish_detection_event('ocr', results, pattern)
        
        return results
    
    @profile(name="detect_objects")
    def detect_objects(self, class_names: Optional[List[str]] = None,
                     confidence_threshold: float = 0.5, region: Optional[Dict[str, int]] = None,
                     use_cache: bool = True, nms_threshold: float = 0.5) -> List[Dict]:
        """
        Detect objects in the current window using YOLO.
        
        Args:
            class_names: Names of object classes to detect (None for all)
            confidence_threshold: Minimum confidence level (0.0-1.0)
            region: Region to search in {left, top, width, height} (None for full image)
            use_cache: Whether to use cached results if available
            nms_threshold: Non-maximum suppression threshold
            
        Returns:
            List of object detection results with bounding boxes and classes
        """
        if 'yolo' not in self.strategies:
            logger.error("YOLO strategy not registered")
            return []
            
        # Get the strategy
        strategy = self.strategies['yolo']
        
        # Get screenshot
        screenshot = self._get_screenshot(use_cache)
        if screenshot is None:
            return []
            
        # Crop region if specified
        if region:
            x = region.get('left', 0)
            y = region.get('top', 0)
            w = region.get('width', screenshot.shape[1] - x)
            h = region.get('height', screenshot.shape[0] - y)
            
            # Ensure region is within bounds
            x = max(0, min(x, screenshot.shape[1] - 1))
            y = max(0, min(y, screenshot.shape[0] - 1))
            w = max(1, min(w, screenshot.shape[1] - x))
            h = max(1, min(h, screenshot.shape[0] - y))
            
            detection_image = screenshot[y:y+h, x:x+w]
        else:
            detection_image = screenshot
            x, y = 0, 0
            
        # Check cache for this detection
        params = {
            'class_names': class_names,
            'confidence_threshold': confidence_threshold,
            'nms_threshold': nms_threshold
        }
        
        if use_cache:
            cached_result = cache_manager.detection_cache.get('yolo', detection_image, params)
            if cached_result is not None:
                logger.debug("Using cached YOLO detection result")
                # Adjust coordinates for region if needed
                if region:
                    for result in cached_result:
                        if 'bbox' in result:
                            result['bbox'][0] += x
                            result['bbox'][1] += y
                return cached_result
        
        # YOLO is already optimized for parallel execution internally,
        # so we don't need to do tiled processing
        with ExecutionTimer("YOLO detection"):
            results = strategy.detect(
                detection_image,
                class_names=class_names,
                confidence_threshold=confidence_threshold,
                nms_threshold=nms_threshold
            )
        
        # Cache the result
        if use_cache:
            cache_manager.detection_cache.put('yolo', detection_image, params, results)
        
        # Adjust coordinates for region if needed
        if region:
            for result in results:
                if 'bbox' in result:
                    result['bbox'][0] += x
                    result['bbox'][1] += y
                    
        # Publish detection event
        self._publish_detection_event('yolo', results, class_names)
        
        return results
    
    def detect_all_templates(self, template_names: Optional[List[str]] = None,
                           confidence_threshold: float = 0.7,
                           region: Optional[Dict[str, int]] = None,
                           use_cache: bool = True) -> List[Dict]:
        """
        Detect multiple templates in the current window.
        
        Args:
            template_names: List of template names to detect (None for all)
            confidence_threshold: Minimum confidence level (0.0-1.0)
            region: Region to search in {left, top, width, height} (None for full image)
            use_cache: Whether to use cached results if available
            
        Returns:
            List of detection results with positions and confidence scores
        """
        if 'template' not in self.strategies:
            logger.error("Template matching strategy not registered")
            return []
            
        # Get the strategy
        strategy = self.strategies['template']
        
        # Get available templates if not specified
        if template_names is None:
            template_names = strategy.get_template_names()
            
        # Get screenshot
        screenshot = self._get_screenshot(use_cache)
        if screenshot is None:
            return []
            
        # Crop region if specified
        if region:
            x = region.get('left', 0)
            y = region.get('top', 0)
            w = region.get('width', screenshot.shape[1] - x)
            h = region.get('height', screenshot.shape[0] - y)
            
            # Ensure region is within bounds
            x = max(0, min(x, screenshot.shape[1] - 1))
            y = max(0, min(y, screenshot.shape[0] - 1))
            w = max(1, min(w, screenshot.shape[1] - x))
            h = max(1, min(h, screenshot.shape[0] - y))
            
            detection_image = screenshot[y:y+h, x:x+w]
        else:
            detection_image = screenshot
            x, y = 0, 0
            
        # Check cache for this detection
        params = {
            'template_names': template_names,
            'confidence_threshold': confidence_threshold
        }
        
        if use_cache:
            cached_result = cache_manager.detection_cache.get('template', detection_image, params)
            if cached_result is not None:
                logger.debug("Using cached multi-template detection result")
                # Adjust coordinates for region if needed
                if region:
                    for result in cached_result:
                        result['x'] += x
                        result['y'] += y
                return cached_result
        
        # Perform detection in parallel tiles if image is large
        if detection_image.shape[0] > 800 or detection_image.shape[1] > 800:
            logger.debug(f"Using parallel processing for large image: {detection_image.shape}")
            
            # Define detection function for each tile
            def detect_in_tile(tile: np.ndarray) -> List[Dict]:
                return strategy.detect(
                    image=tile,
                    template_names=template_names,
                    confidence_threshold=confidence_threshold
                )
            
            # Process image in tiles
            with ExecutionTimer("Parallel multi-template detection"):
                results = image_processor.apply_detection_in_tiles(
                    detection_image,
                    detect_in_tile,
                    tile_size=400,
                    overlap=50,
                    min_distance=20
                )
        else:
            # Regular detection for smaller images
            with ExecutionTimer("Multi-template detection"):
                results = strategy.detect(
                    image=detection_image,
                    template_names=template_names,
                    confidence_threshold=confidence_threshold
                )
        
        # Cache the result
        if use_cache:
            cache_manager.detection_cache.put('template', detection_image, params, results)
        
        # Adjust coordinates for region if needed
        if region:
            for result in results:
                result['x'] += x
                result['y'] += y
                
        # Publish detection event
        self._publish_detection_event('template', results, template_names)
        
        return results
    
    def run_template_detection(self, template_names: List[str], confidence_threshold: float = 0.7,
                           max_results: int = 10, region: Optional[Dict[str, int]] = None) -> List[Dict]:
        """
        Run template detection on the current window.
        
        This is a wrapper around detect_all_templates that limits the number of results.
        
        Args:
            template_names: List of template names to detect
            confidence_threshold: Minimum confidence level (0.0-1.0)
            max_results: Maximum number of results to return
            region: Region to search in {left, top, width, height} (None for full image)
            
        Returns:
            List of detection results with positions and confidence scores
        """
        try:
            logger.info(f"Starting template detection with templates: {template_names}")
            logger.debug(f"Detection parameters: confidence={confidence_threshold}, max_results={max_results}, region={region}")
            
            # Check if we have template strategy registered
            if 'template' not in self.strategies:
                logger.error("Template strategy not registered in detection service")
                return []
            
            # Check context
            if not self.context or not self.context.get('window_title'):
                logger.warning("Window title missing from context, detection might not work correctly")
                window_title = self.context.get('window_title', 'Unknown Window')
                logger.debug(f"Current context: {self.context}")
            else:
                window_title = self.context.get('window_title')
                logger.debug(f"Using window title from context: {window_title}")
            
            # Validate template names
            all_templates = self.strategies['template'].get_template_names()
            missing_templates = [t for t in template_names if t not in all_templates]
            if missing_templates:
                logger.warning(f"Some templates not found: {missing_templates}")
                logger.debug(f"Available templates: {all_templates}")
            
            valid_templates = [t for t in template_names if t in all_templates]
            if not valid_templates:
                logger.error("No valid templates found for detection")
                return []
            
            logger.debug(f"Using valid templates: {valid_templates}")
            
            # Call detect_all_templates with the given parameters
            logger.debug("Calling detect_all_templates")
            results = self.detect_all_templates(
                template_names=valid_templates,
                confidence_threshold=confidence_threshold,
                region=region
            )
            
            logger.debug(f"Got {len(results)} results from detect_all_templates")
            
            # Limit the number of results if needed
            if max_results > 0 and len(results) > max_results:
                logger.debug(f"Limiting results from {len(results)} to {max_results}")
                # Sort by confidence score (highest first) and take the top max_results
                results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
                results = results[:max_results]
                
            logger.info(f"Template detection complete: found {len(results)} matches")
            for i, result in enumerate(results):
                logger.debug(f"Result {i+1}: template={result.get('template_name')}, "
                            f"confidence={result.get('confidence'):.2f}, "
                            f"position=({result.get('x')}, {result.get('y')})")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in run_template_detection: {e}", exc_info=True)
            return []
    
    def clear_cache(self) -> None:
        """Clear the detection cache."""
        # Clear screenshot cache
        self._latest_screenshot = None
        self._latest_screenshot_time = 0
        
        # Clear strategy caches
        cache_manager.detection_cache.clear()
        logger.info("Cleared detection cache")
    
    def _publish_detection_event(self, strategy_name: str, results: List[Dict], query: Any) -> None:
        """
        Publish detection event to event bus.
        
        Args:
            strategy_name: Name of detection strategy used
            results: Detection results to publish
            query: Detection query (e.g., template name, OCR pattern)
        """
        if not self.event_bus:
            return
            
        # Prepare event data
        event_data = {
            'strategy': strategy_name,
            'query': query,
            'results': results,
            'result_count': len(results),
            'timestamp': time.time()
        }
        
        # Choose event type based on results
        if results:
            # Convert enum to string - the event_bus expects string event types
            event_type_str = 'detection_completed'
        else:
            event_type_str = 'detection_failed'
            
        # Publish event with string event type and data directly
        logger.debug(f"Publishing detection event: {event_type_str} with {len(results)} results")
        self.event_bus.publish(event_type_str, event_data) 