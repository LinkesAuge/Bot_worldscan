"""
Events Module

This package contains event-related components of the Scout application, including:
- EventBus: Central message broker for application-wide communication
- EventType: Enumeration of event types used in the application
- Event: Class representing events passed through the event bus
"""

from .event_bus import EventBus
from .event_types import EventType
from .event import Event

__all__ = ['EventBus', 'EventType', 'Event'] 