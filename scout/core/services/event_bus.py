"""
Event Bus

This module provides a central event bus for application-wide event handling. It implements
the observer pattern using PyQt signals and slots, allowing components to communicate
without direct coupling.
"""

from typing import Dict, List, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """
    Central event bus for application-wide events.
    
    This implements the observer pattern using PyQt signals and slots,
    allowing components to communicate without direct coupling. The event bus:
    
    - Allows publishing events by type with optional data
    - Manages subscriptions to event types
    - Dispatches events to all subscribers
    - Provides both signal-based and callback-based subscriptions
    
    Common event types include:
    - template_match: Template matching results
    - ocr_result: OCR processing results
    - window_change: Window state changes
    - action_executed: Action execution events
    - config_changed: Configuration changes
    """
    
    # Define signals for different event types
    # These allow components to connect via Qt's signal/slot mechanism
    template_match_signal = pyqtSignal(object)  # Template match events
    ocr_result_signal = pyqtSignal(object)      # OCR result events
    window_change_signal = pyqtSignal(object)   # Window position/state changes
    action_executed_signal = pyqtSignal(object) # Action execution events
    config_changed_signal = pyqtSignal(object)  # Config change events
    
    # Generic event signal for any event type (event_type, data)
    generic_event_signal = pyqtSignal(str, object)
    
    def __init__(self):
        """Initialize the event bus."""
        super().__init__()
        # Dictionary of event type to list of handlers
        self._handlers: Dict[str, List[Callable]] = {}
    
    def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event to all subscribers.
        
        This method:
        1. Emits the generic event signal with type and data
        2. Emits the specific signal for the event type if it exists
        3. Calls any registered callback handlers
        
        Args:
            event_type: Type of event (e.g., 'template_match')
            data: Event data to send to subscribers
        """
        # Log the event for debugging if needed
        # logger.debug(f"Publishing event: {event_type}")
        
        # Emit the generic signal that can be used to listen to all events
        self.generic_event_signal.emit(event_type, data)
        
        # Emit specific signals based on event type
        if event_type == 'template_match':
            self.template_match_signal.emit(data)
        elif event_type == 'ocr_result':
            self.ocr_result_signal.emit(data)
        elif event_type == 'window_change':
            self.window_change_signal.emit(data)
        elif event_type == 'action_executed':
            self.action_executed_signal.emit(data)
        elif event_type == 'config_changed':
            self.config_changed_signal.emit(data)
        
        # Call any registered callback handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    # Log handler errors but don't let them break event propagation
                    # logger.error(f"Error in event handler for {event_type}: {e}")
                    pass
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type with a callback function.
        
        This method registers a callback to be called when an event of the
        specified type is published. This is an alternative to using Qt's
        signal/slot mechanism.
        
        Args:
            event_type: Type of event to subscribe to (e.g., 'template_match')
            callback: Function to call when event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        if callback not in self._handlers[event_type]:
            self._handlers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe a callback from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to unsubscribe
        """
        if event_type in self._handlers and callback in self._handlers[event_type]:
            self._handlers[event_type].remove(callback)
            
            # Clean up empty handler lists
            if not self._handlers[event_type]:
                del self._handlers[event_type] 