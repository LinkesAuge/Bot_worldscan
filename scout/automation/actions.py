"""
Automation Actions

This module defines all available automation actions and their parameters.
Each action represents a specific operation that can be performed in the game,
such as clicking, typing, or waiting for conditions.
"""

from typing import Dict, Optional, Any, List
from enum import Enum, auto
from dataclasses import dataclass, asdict, field
import logging
from abc import ABC

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Enumeration of all available action types."""
    CLICK = auto()          # Single left click
    RIGHT_CLICK = auto()    # Single right click
    DOUBLE_CLICK = auto()   # Double left click
    DRAG = auto()           # Mouse drag operation
    TYPE_TEXT = auto()      # Type text at current position
    WAIT = auto()           # Wait for specified time
    WAIT_FOR_OCR = auto()   # Wait for OCR condition

@dataclass
class ActionParamsCommon:
    """Common parameters for all actions."""
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description

@dataclass
class ClickParams:
    """Parameters for click actions."""
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description

@dataclass
class DragParams:
    """Parameters for drag actions."""
    end_position_name: str  # Name of position to drag to
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description
    duration: float = 0.5   # Duration of drag operation

@dataclass
class TypeParams:
    """Parameters for text input actions."""
    text: str  # Text to type
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description

@dataclass
class WaitParams:
    """Parameters for wait actions."""
    duration: float  # Time to wait in seconds
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description

@dataclass
class OCRWaitParams:
    """Parameters for OCR wait actions."""
    expected_text: str  # Text to wait for
    position_name: Optional[str] = None  # Name of position to act on
    timeout: float = 30.0  # Timeout in seconds for conditions
    description: Optional[str] = None  # Optional description
    partial_match: bool = False  # Whether to accept partial matches

class AutomationAction:
    """
    Base class for all automation actions.
    
    This class represents a single action in an automation sequence.
    It contains the action type, parameters, and condition checking logic.
    """
    
    def __init__(self, action_type: ActionType, params: Any):
        """
        Initialize an automation action.
        
        Args:
            action_type: Type of action to perform
            params: Parameters for the action
        """
        self.action_type = action_type
        self.params = params
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for storage."""
        return {
            'type': self.action_type.name,
            'params': asdict(self.params)
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutomationAction':
        """Create action from dictionary."""
        action_type = ActionType[data['type']]
        params_dict = data['params']
        
        # Create appropriate params object based on action type
        params_class = {
            ActionType.CLICK: ClickParams,
            ActionType.RIGHT_CLICK: ClickParams,
            ActionType.DOUBLE_CLICK: ClickParams,
            ActionType.DRAG: DragParams,
            ActionType.TYPE_TEXT: TypeParams,
            ActionType.WAIT: WaitParams,
            ActionType.WAIT_FOR_OCR: OCRWaitParams
        }[action_type]
        
        params = params_class(**params_dict)
        return cls(action_type, params) 