"""
Event Types

This module defines the types of events that can be published through the event bus.
"""

from enum import Enum, auto

class EventType(Enum):
    """
    Enumeration of all event types in the system.
    
    These event types are used to categorize events and allow subscribers
    to filter the events they receive.
    """
    
    # Generic events
    GENERIC = auto()
    
    # Window events
    WINDOW_FOUND = auto()
    WINDOW_LOST = auto()
    WINDOW_POSITION_CHANGED = auto()
    WINDOW_SIZE_CHANGED = auto()
    WINDOW_TITLE_CHANGED = auto()
    
    # Detection events
    DETECTION_COMPLETED = auto()
    DETECTION_FAILED = auto()
    
    # Game state events
    GAME_STATE_CHANGED = auto()
    
    # Automation events
    AUTOMATION_STARTED = auto()
    AUTOMATION_PAUSED = auto()
    AUTOMATION_RESUMED = auto()
    AUTOMATION_COMPLETED = auto()
    AUTOMATION_FAILED = auto()
    AUTOMATION_STOPPED = auto()
    
    # Automation task events
    AUTOMATION_TASK_ADDED = auto()
    AUTOMATION_TASK_STARTED = auto()
    AUTOMATION_TASK_COMPLETED = auto()
    AUTOMATION_TASK_FAILED = auto()
    AUTOMATION_TASK_CANCELLED = auto()
    
    # Configuration events
    CONFIG_LOADED = auto()
    CONFIG_SAVED = auto()
    CONFIG_CHANGED = auto()
    
    # User interface events
    UI_ACTION = auto()
    
    # Application events
    APP_STARTED = auto()
    APP_STOPPING = auto()
    APP_ERROR = auto() 