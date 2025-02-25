"""
Game-Specific Tasks

This module provides implementations of specialized tasks for Total Battle automation:
- NavigateToCoordinatesTask: Navigate to specific coordinates on the game map
- CollectResourcesTask: Collect resources from around the player's city
- ScanAreaTask: Scan an area around current position for specific objects
- WaitForElementTask: Wait for a specific element to appear on screen
"""

from typing import Dict, Any, Optional, List, Tuple
import time
import logging
import re

from ..task import Task, TaskPriority, CompositeTask
from .basic_tasks import ClickTask, TypeTask, WaitTask, DetectTask
from ...game.game_state import Coordinates

logger = logging.getLogger(__name__)

class NavigateToCoordinatesTask(CompositeTask):
    """
    Task to navigate to specific coordinates on the game map.
    
    This task:
    1. Clicks the coordinates input field
    2. Enters the coordinates
    3. Waits for navigation to complete
    
    Parameters:
    - coordinates: Target coordinates (kingdom, x, y)
    - input_field_position: Position of the coordinates input field
    """
    
    def __init__(
        self,
        name: str,
        coordinates: Coordinates,
        input_field_position: Tuple[int, int],
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a navigate to coordinates task."""
        super().__init__(name, priority=priority)
        
        # Store parameters
        self.params = {
            'coordinates': {
                'kingdom': coordinates.kingdom,
                'x': coordinates.x,
                'y': coordinates.y
            },
            'input_field_position': input_field_position
        }
        
        # Create subtasks
        x, y = input_field_position
        coords = f"{coordinates.x},{coordinates.y}"
        
        # 1. Click the input field
        click_task = ClickTask(
            f"{name}_click_input",
            x, y,
            relative_to_window=True
        )
        
        # 2. Type the coordinates
        type_task = TypeTask(
            f"{name}_type_coords",
            coords
        )
        
        # 3. Press Enter (part of type task)
        
        # 4. Wait for navigation to complete
        wait_task = WaitTask(
            f"{name}_wait",
            1.5  # Adjust based on navigation time
        )
        
        # Add tasks to sequence
        self.add_task(click_task)
        self.add_task(type_task)
        self.add_task(wait_task)

class WaitForElementTask(Task):
    """
    Task to wait for a specific element to appear on screen.
    
    This task repeatedly checks for an element using the detection
    service until it appears or a timeout is reached.
    
    Parameters:
    - strategy: Detection strategy ('template', 'ocr', 'yolo')
    - timeout: Maximum time to wait in seconds
    - check_interval: Time between checks in seconds
    
    Plus strategy-specific parameters:
    - templates: For template strategy
    - pattern: For OCR strategy
    - class_ids: For YOLO strategy
    """
    
    def __init__(
        self,
        name: str,
        strategy: str,
        timeout: float = 30.0,
        check_interval: float = 1.0,
        templates: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        class_ids: Optional[List[int]] = None,
        region: Optional[Dict[str, int]] = None,
        confidence: float = 0.7,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a wait for element task."""
        params = {
            'strategy': strategy,
            'timeout': timeout,
            'check_interval': check_interval,
            'templates': templates,
            'pattern': pattern,
            'class_ids': class_ids,
            'region': region,
            'confidence': confidence
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the wait for element task.
        
        Args:
            context: Execution context containing detection_service
            
        Returns:
            bool: True if element was found, False if timeout
        """
        try:
            # Get the detection service
            detection_service = context.get('detection_service')
            if not detection_service:
                self.fail("No detection service in context")
                return False
                
            # Extract parameters
            strategy = self.params.get('strategy')
            timeout = self.params.get('timeout', 30.0)
            check_interval = self.params.get('check_interval', 1.0)
            
            # Create detect task
            detect_task = DetectTask(
                f"{self.name}_detect",
                strategy=strategy,
                templates=self.params.get('templates'),
                region=self.params.get('region'),
                confidence=self.params.get('confidence', 0.7),
                pattern=self.params.get('pattern'),
                class_ids=self.params.get('class_ids')
            )
            
            # Track start time
            start_time = time.time()
            
            # Loop until timeout
            while time.time() - start_time < timeout:
                # Execute detection
                detect_task.execute(context)
                
                # Check if element was found
                if detect_task.result and len(detect_task.result) > 0:
                    # Store the detection results
                    self.result = detect_task.result
                    logger.debug(f"Element found after {time.time() - start_time:.1f} seconds")
                    return True
                
                # Wait before next check
                time.sleep(check_interval)
            
            # Timeout reached
            self.fail(f"Timeout waiting for element ({timeout} seconds)")
            return False
            
        except Exception as e:
            self.fail(f"Wait for element failed: {str(e)}")
            return False

class CollectResourcesTask(CompositeTask):
    """
    Task to collect resources from around the player's city.
    
    This task:
    1. Detects resource collection buttons
    2. Clicks on each resource button
    3. Waits between clicks
    
    Parameters:
    - resource_templates: List of template names for resource buttons
    - max_collections: Maximum number of resources to collect
    """
    
    def __init__(
        self,
        name: str,
        resource_templates: List[str],
        max_collections: int = 10,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a collect resources task."""
        super().__init__(name, priority=priority)
        
        # Store parameters
        self.params = {
            'resource_templates': resource_templates,
            'max_collections': max_collections
        }
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the collect resources task.
        
        This override dynamically creates the subtasks based on detection results.
        
        Args:
            context: Execution context with detection_service and actions_service
            
        Returns:
            bool: True if collection was successful, False otherwise
        """
        try:
            # Get required services
            detection_service = context.get('detection_service')
            actions_service = context.get('actions_service')
            
            if not detection_service or not actions_service:
                self.fail("Missing required services in context")
                return False
                
            # Extract parameters
            resource_templates = self.params.get('resource_templates', [])
            max_collections = self.params.get('max_collections', 10)
            
            # Detect resource buttons
            results = []
            for template in resource_templates:
                template_results = detection_service.detect_template(
                    template_name=template,
                    use_cache=False
                )
                results.extend(template_results)
                
            # Limit to max collections
            results = results[:max_collections]
            
            if not results:
                logger.debug("No resource buttons found")
                return True  # Not a failure, just nothing to collect
                
            # Log the number of resources to collect
            logger.debug(f"Found {len(results)} resource buttons to collect")
            
            # Create tasks for each resource button
            collection_count = 0
            for i, result in enumerate(results):
                # Extract position
                x = result['x'] + result['width'] // 2
                y = result['y'] + result['height'] // 2
                
                # Create click task
                click_task = ClickTask(
                    f"{self.name}_click_{i}",
                    x, y,
                    relative_to_window=True
                )
                
                # Create wait task
                wait_task = WaitTask(
                    f"{self.name}_wait_{i}",
                    0.5  # Small delay between collections
                )
                
                # Execute the tasks
                click_task.start()
                success = click_task.execute(context)
                if success:
                    click_task.complete()
                    collection_count += 1
                else:
                    click_task.fail("Click failed")
                    continue
                
                wait_task.start()
                wait_task.execute(context)
                wait_task.complete()
            
            # Set result to number of collected resources
            self.result = collection_count
            logger.debug(f"Collected {collection_count} resources")
            
            return True
            
        except Exception as e:
            self.fail(f"Resource collection failed: {str(e)}")
            return False

class ScanAreaTask(Task):
    """
    Task to scan an area around current position for specific objects.
    
    This task:
    1. Uses the game_service to get current position
    2. Uses detection_service to look for specified objects
    3. Records the found objects in the game state
    
    Parameters:
    - strategy: Detection strategy ('template', 'ocr', 'yolo')
    - area_size: Number of tiles to scan in each direction
    - object_templates: Templates to look for (for template strategy)
    """
    
    def __init__(
        self,
        name: str,
        strategy: str,
        area_size: int = 5,
        object_templates: Optional[List[str]] = None,
        pattern: Optional[str] = None,
        class_ids: Optional[List[int]] = None,
        confidence: float = 0.7,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a scan area task."""
        params = {
            'strategy': strategy,
            'area_size': area_size,
            'object_templates': object_templates,
            'pattern': pattern,
            'class_ids': class_ids,
            'confidence': confidence
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the scan area task.
        
        Args:
            context: Execution context with game_service and detection_service
            
        Returns:
            bool: True if scan was successful, False otherwise
        """
        try:
            # Get required services
            game_service = context.get('game_service')
            detection_service = context.get('detection_service')
            
            if not game_service or not detection_service:
                self.fail("Missing required services in context")
                return False
                
            # Extract parameters
            strategy = self.params.get('strategy')
            area_size = self.params.get('area_size', 5)
            
            # Get current position
            current_position = game_service.state.current_position
            if not current_position:
                self.fail("Unknown current position")
                return False
                
            logger.debug(f"Scanning area around {current_position}")
            
            # Create detect task based on strategy
            detect_task = DetectTask(
                f"{self.name}_detect",
                strategy=strategy,
                templates=self.params.get('object_templates'),
                region=None,  # Full screen
                confidence=self.params.get('confidence', 0.7),
                pattern=self.params.get('pattern'),
                class_ids=self.params.get('class_ids')
            )
            
            # Execute detection
            detect_task.execute(context)
            
            # Process results
            results = detect_task.result or []
            
            # Update game state with found objects
            objects_found = 0
            for result in results:
                try:
                    # Result processing depends on strategy type
                    if strategy == 'template':
                        template_name = result.get('template_name', '')
                        # Attempt to derive entity type from template name
                        entity_type = None
                        
                        # Try to identify entity type from template name patterns
                        if re.search(r'city|tower|castle', template_name, re.IGNORECASE):
                            entity_type = 'city'
                        elif re.search(r'resource|gold|wood|stone|food|iron', template_name, re.IGNORECASE):
                            entity_type = 'resource'
                        elif re.search(r'monster|creature|enemy', template_name, re.IGNORECASE):
                            entity_type = 'monster'
                        else:
                            entity_type = 'unknown'
                            
                        # Convert screen coordinates to game coordinates
                        screen_x = result.get('x', 0) + result.get('width', 0) // 2
                        screen_y = result.get('y', 0) + result.get('height', 0) // 2
                        
                        # Use the game service to convert to game coordinates
                        # (This simplified approach assumes each game_service implementation will
                        # provide a valid implementation of this method)
                        game_coords = game_service._screen_to_game_coords(screen_x, screen_y)
                        
                        if game_coords:
                            # Add to game state
                            game_service.state.add_or_update_entity({
                                'entity_type': entity_type,
                                'coordinates': game_coords,
                                'details': {
                                    'template_name': template_name,
                                    'confidence': result.get('confidence', 0)
                                }
                            })
                            objects_found += 1
                    
                    # Add other strategy processing if needed
                    
                except Exception as e:
                    logger.error(f"Error processing scan result: {e}")
            
            # Set result
            self.result = objects_found
            logger.debug(f"Found {objects_found} objects during scan")
            
            return True
            
        except Exception as e:
            self.fail(f"Area scan failed: {str(e)}")
            return False 