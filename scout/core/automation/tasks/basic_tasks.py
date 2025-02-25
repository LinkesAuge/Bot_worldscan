"""
Basic Task Types

This module provides implementations of basic task types for game automation:
- ClickTask: Click at a specific position
- DragTask: Drag from one position to another
- TypeTask: Type text
- WaitTask: Wait for a specified duration
- DetectTask: Detect game elements using detection service
"""

from typing import Dict, Any, Optional, List, Tuple
import time
import logging

from ..task import Task, TaskPriority
from ...interfaces.service_interfaces import WindowServiceInterface, DetectionServiceInterface

logger = logging.getLogger(__name__)

class ClickTask(Task):
    """
    Task to click at a specific position in the game window.
    
    Parameters:
    - x: X coordinate
    - y: Y coordinate
    - button: Mouse button ('left', 'right', 'middle')
    - clicks: Number of clicks
    - relative_to_window: Whether coordinates are relative to game window
    """
    
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        button: str = 'left',
        clicks: int = 1,
        relative_to_window: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a click task."""
        params = {
            'x': x,
            'y': y,
            'button': button,
            'clicks': clicks,
            'relative_to_window': relative_to_window
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the click task.
        
        Args:
            context: Execution context containing actions_service
            
        Returns:
            bool: True if the click was successful, False otherwise
        """
        try:
            # Get the game actions service
            actions_service = context.get('actions_service')
            if not actions_service:
                self.fail("No actions service in context")
                return False
                
            # Extract parameters
            x = self.params.get('x')
            y = self.params.get('y')
            button = self.params.get('button', 'left')
            clicks = self.params.get('clicks', 1)
            relative_to_window = self.params.get('relative_to_window', True)
            
            # Perform the click
            actions_service.click_at(x, y, relative_to_window, button, clicks)
            
            logger.debug(f"Clicked at ({x}, {y}) with {button} button, {clicks} clicks")
            return True
            
        except Exception as e:
            self.fail(f"Click failed: {str(e)}")
            return False

class DragTask(Task):
    """
    Task to drag from one position to another.
    
    Parameters:
    - start_x: Starting X coordinate
    - start_y: Starting Y coordinate
    - end_x: Ending X coordinate
    - end_y: Ending Y coordinate
    - duration: Duration of drag operation in seconds
    - relative_to_window: Whether coordinates are relative to game window
    """
    
    def __init__(
        self,
        name: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        relative_to_window: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a drag task."""
        params = {
            'start_x': start_x,
            'start_y': start_y,
            'end_x': end_x,
            'end_y': end_y,
            'duration': duration,
            'relative_to_window': relative_to_window
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the drag task.
        
        Args:
            context: Execution context containing actions_service
            
        Returns:
            bool: True if the drag was successful, False otherwise
        """
        try:
            # Get the game actions service
            actions_service = context.get('actions_service')
            if not actions_service:
                self.fail("No actions service in context")
                return False
                
            # Extract parameters
            start_x = self.params.get('start_x')
            start_y = self.params.get('start_y')
            end_x = self.params.get('end_x')
            end_y = self.params.get('end_y')
            duration = self.params.get('duration', 0.5)
            relative_to_window = self.params.get('relative_to_window', True)
            
            # Perform the drag
            actions_service.drag_mouse(
                start_x, start_y, end_x, end_y, 
                relative_to_window, duration
            )
            
            logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
            
        except Exception as e:
            self.fail(f"Drag failed: {str(e)}")
            return False

class TypeTask(Task):
    """
    Task to type text.
    
    Parameters:
    - text: Text to type
    - click_position: Optional position to click before typing (x, y)
    - relative_to_window: Whether click position is relative to game window
    """
    
    def __init__(
        self,
        name: str,
        text: str,
        click_position: Optional[Tuple[int, int]] = None,
        relative_to_window: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a type task."""
        params = {
            'text': text,
            'click_position': click_position,
            'relative_to_window': relative_to_window
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the type task.
        
        Args:
            context: Execution context containing actions_service
            
        Returns:
            bool: True if typing was successful, False otherwise
        """
        try:
            # Get the game actions service
            actions_service = context.get('actions_service')
            if not actions_service:
                self.fail("No actions service in context")
                return False
                
            # Extract parameters
            text = self.params.get('text', '')
            click_position = self.params.get('click_position')
            relative_to_window = self.params.get('relative_to_window', True)
            
            # Click at position if specified
            if click_position:
                x, y = click_position
                actions_service.click_at(x, y, relative_to_window)
                time.sleep(0.2)  # Small delay after clicking
            
            # Type the text
            actions_service.input_text(text)
            
            logger.debug(f"Typed text: '{text}'")
            return True
            
        except Exception as e:
            self.fail(f"Type failed: {str(e)}")
            return False

class WaitTask(Task):
    """
    Task to wait for a specified duration.
    
    Parameters:
    - duration: Time to wait in seconds
    """
    
    def __init__(
        self,
        name: str,
        duration: float,
        priority: TaskPriority = TaskPriority.LOW
    ):
        """Initialize a wait task."""
        params = {'duration': duration}
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the wait task.
        
        Args:
            context: Execution context (not used)
            
        Returns:
            bool: True (wait tasks always succeed)
        """
        try:
            # Extract parameters
            duration = self.params.get('duration', 0)
            
            # Wait for the specified duration
            logger.debug(f"Waiting for {duration} seconds")
            time.sleep(duration)
            
            return True
            
        except Exception as e:
            self.fail(f"Wait failed: {str(e)}")
            return False

class DetectTask(Task):
    """
    Task to detect game elements using detection service.
    
    Parameters:
    - strategy: Detection strategy ('template', 'ocr', 'yolo')
    - templates: List of template names (for template strategy)
    - region: Region to detect in {left, top, width, height}
    - confidence: Confidence threshold
    - pattern: Text pattern to match (for OCR strategy)
    - class_ids: List of class IDs to detect (for YOLO strategy)
    """
    
    def __init__(
        self,
        name: str,
        strategy: str,
        templates: Optional[List[str]] = None,
        region: Optional[Dict[str, int]] = None,
        confidence: float = 0.8,
        pattern: Optional[str] = None,
        class_ids: Optional[List[int]] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ):
        """Initialize a detect task."""
        params = {
            'strategy': strategy,
            'templates': templates,
            'region': region,
            'confidence': confidence,
            'pattern': pattern,
            'class_ids': class_ids
        }
        super().__init__(name, priority, params)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the detect task.
        
        Args:
            context: Execution context containing detection_service
            
        Returns:
            bool: True if detection was successful, False otherwise
        """
        try:
            # Get the detection service
            detection_service = context.get('detection_service')
            if not detection_service:
                self.fail("No detection service in context")
                return False
                
            # Extract parameters
            strategy = self.params.get('strategy')
            region = self.params.get('region')
            
            # Choose detection method based on strategy
            if strategy == 'template':
                templates = self.params.get('templates')
                confidence = self.params.get('confidence', 0.8)
                
                # Detect templates
                results = detection_service.detect_template(
                    template_name=templates[0] if templates and len(templates) == 1 else None,
                    region=region,
                    confidence_threshold=confidence,
                    use_cache=False
                )
                
            elif strategy == 'ocr':
                pattern = self.params.get('pattern')
                confidence = self.params.get('confidence', 0)
                
                # Detect text
                results = detection_service.detect_text(
                    region=region,
                    pattern=pattern,
                    confidence_threshold=confidence,
                    use_cache=False
                )
                
            elif strategy == 'yolo':
                class_ids = self.params.get('class_ids')
                confidence = self.params.get('confidence', 0.5)
                
                # Detect objects
                results = detection_service.detect_objects(
                    class_ids=class_ids,
                    region=region,
                    confidence_threshold=confidence,
                    use_cache=False
                )
                
            else:
                self.fail(f"Unknown detection strategy: {strategy}")
                return False
            
            # Store results in task result
            self.result = results
            
            if results:
                logger.debug(f"Detection found {len(results)} results with strategy {strategy}")
                return True
            else:
                logger.debug(f"No results found with strategy {strategy}")
                return False
                
        except Exception as e:
            self.fail(f"Detection failed: {str(e)}")
            return False 