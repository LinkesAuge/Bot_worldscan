"""
Event Module

This module defines the Event class, which represents events that can be published
through the EventBus. Events have a type and associated data.
"""

from typing import Any, Dict, Optional
import time

from .event_types import EventType

class Event:
    """
    Represents an event in the application.
    
    Events are objects that contain information about something that has happened
    in the application, such as a detection result, a state change, or an error.
    They have a type and associated data, and can be published through the EventBus
    to notify interested subscribers.
    
    Attributes:
        event_type: The type of the event, from the EventType enum
        data: Dictionary containing event-specific data
        timestamp: When the event was created (unix timestamp)
    """
    
    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None):
        """
        Create a new event.
        
        Args:
            event_type: The type of the event, from the EventType enum
            data: Dictionary containing event-specific data
        """
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        """Return a string representation of the event."""
        return f"Event({self.event_type.name}, {self.data})"
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the event."""
        return f"Event(type={self.event_type.name}, data={self.data}, timestamp={self.timestamp})" 