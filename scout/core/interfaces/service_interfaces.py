"""
Service Interfaces

This module defines the protocol interfaces for all core services in the Scout application.
These interfaces establish contracts that concrete service implementations must follow,
enabling loose coupling and dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, List, Dict, Any, Tuple
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class WindowServiceInterface(Protocol):
    """
    Interface for window management service.
    
    This service is responsible for:
    - Finding and tracking the game window
    - Capturing screenshots of the game window
    - Converting between screen and client coordinates
    - Notifying when window state changes (position, focus, etc.)
    """
    
    def find_window(self) -> bool:
        """
        Find the game window by its title.
        
        Returns:
            bool: True if window found, False otherwise
        """
        ...
        
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the position and size of the game window.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: Tuple of (x, y, width, height) or None if window not found
        """
        ...
        
    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window.
        
        Returns:
            Optional[np.ndarray]: Screenshot as numpy array in BGR format, or None if failed
        """
        ...
        
    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert client (window-relative) coordinates to screen coordinates.
        
        Args:
            x: X coordinate relative to window client area
            y: Y coordinate relative to window client area
            
        Returns:
            Tuple[int, int]: Screen coordinates (x, y)
        """
        ...
        
    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to client (window-relative) coordinates.
        
        Args:
            screen_x: X coordinate on screen
            screen_y: Y coordinate on screen
            
        Returns:
            Tuple[int, int]: Client coordinates (x, y)
        """
        ...


class DetectionServiceInterface(Protocol):
    """
    Interface for detection service.
    
    This service is responsible for:
    - Template matching to find elements in the game
    - OCR processing to extract text from the game
    - Managing continuous detection processes
    - Notifying when elements are detected
    """
    
    def find_templates(self, image: np.ndarray, template_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find template matches in an image.
        
        Args:
            image: Image to search in
            template_names: List of template names to search for (None for all)
            
        Returns:
            List of matches, each as a dictionary with template name, position, size, and confidence
        """
        ...
        
    def process_ocr(self, image: np.ndarray, region: Optional[Dict[str, int]] = None) -> str:
        """
        Process OCR on an image.
        
        Args:
            image: Image to process
            region: Optional region to process {left, top, width, height}
            
        Returns:
            Extracted text as string
        """
        ...
        
    def start_continuous_detection(self, detector_type: str, **params) -> None:
        """
        Start continuous detection.
        
        Args:
            detector_type: Type of detector ('template' or 'ocr')
            **params: Parameters for the detection
        """
        ...
        
    def stop_continuous_detection(self, detector_type: str) -> None:
        """
        Stop continuous detection.
        
        Args:
            detector_type: Type of detector ('template' or 'ocr')
        """
        ...


class AutomationServiceInterface(Protocol):
    """
    Interface for automation service.
    
    This service is responsible for:
    - Managing automation sequences
    - Executing sequences of actions
    - Managing marked positions
    - Coordinating actions with other services
    """
    
    def execute_sequence(self, sequence_name: str, simulation: bool = False) -> None:
        """
        Execute a named automation sequence.
        
        Args:
            sequence_name: Name of the sequence to execute
            simulation: Whether to simulate actions rather than actually executing them
        """
        ...
        
    def add_position(self, name: str, x: int, y: int, description: Optional[str] = None) -> None:
        """
        Add a marked position.
        
        Args:
            name: Unique name for the position
            x: X coordinate
            y: Y coordinate
            description: Optional description of what this position represents
        """
        ...
        
    def add_sequence(self, name: str, actions: List[Dict[str, Any]], description: Optional[str] = None) -> None:
        """
        Add an automation sequence.
        
        Args:
            name: Unique name for the sequence
            actions: List of actions in the sequence
            description: Optional description of what this sequence does
        """
        ...
        
    def get_positions(self) -> Dict[str, Any]:
        """
        Get all marked positions.
        
        Returns:
            Dictionary of position name to position object
        """
        ...
        
    def get_sequences(self) -> Dict[str, Any]:
        """
        Get all automation sequences.
        
        Returns:
            Dictionary of sequence name to sequence object
        """
        ...


class ConfigServiceInterface(Protocol):
    """
    Interface for configuration service.
    
    This service is responsible for:
    - Reading and writing configuration values
    - Managing configuration sections
    - Persisting configuration to disk
    - Notifying when configuration changes
    """
    
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default if not found
        """
        ...
        
    def set_config(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        ...
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Dictionary of key to value for the section
        """
        ...
        
    def set_section(self, section: str, config: Dict[str, Any]) -> None:
        """
        Set an entire configuration section.
        
        Args:
            section: Section name
            config: Dictionary of key to value for the section
        """
        ...
        
    def save(self) -> None:
        """Save the configuration to disk."""
        ...


class EventBusInterface(Protocol):
    """
    Interface for event bus service.
    
    This service is responsible for:
    - Publishing events to subscribers
    - Managing event subscriptions
    - Facilitating communication between components
    """
    
    def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        ...
        
    def subscribe(self, event_type: str, callback: callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
        """
        ...
        
    def unsubscribe(self, event_type: str, callback: callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to unsubscribe
        """
        ...


class ActionsServiceInterface(Protocol):
    """
    Interface for game actions service.
    
    This service is responsible for:
    - Executing mouse actions (click, move, drag)
    - Executing keyboard actions (type, press)
    - Coordinating with window service for proper positioning
    """
    
    def click_at(self, x: int, y: int, relative_to_window: bool = True, 
                button: str = 'left', clicks: int = 1) -> None:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate to click at
            y: Y coordinate to click at
            relative_to_window: If True, coordinates are relative to game window
            button: Mouse button to click ('left', 'right', 'middle')
            clicks: Number of clicks to perform
        """
        ...
        
    def move_mouse_to(self, x: int, y: int, relative_to_window: bool = True) -> None:
        """
        Move the mouse cursor to specified coordinates.
        
        Args:
            x: X coordinate to move to
            y: Y coordinate to move to
            relative_to_window: If True, coordinates are relative to game window
        """
        ...
        
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                  relative_to_window: bool = True, duration: float = 0.5) -> None:
        """
        Perform a mouse drag operation from start to end coordinates.
        
        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            relative_to_window: If True, coordinates are relative to game window
            duration: Duration of the drag operation in seconds
        """
        ...
        
    def input_text(self, text: str) -> None:
        """
        Type text at current cursor position.
        
        Args:
            text: Text to type
        """
        ... 