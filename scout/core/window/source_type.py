"""
Source Type Enumeration

This module defines the enumeration for different types of capture sources
in the Qt-based window capture implementation.
"""

from enum import Enum, auto


class SourceType(Enum):
    """
    Enumeration of capture source types.
    
    This enumeration defines the different types of sources that can be captured
    using the Qt-based window capture system. Currently supports:
    - Window: A specific application window
    - Screen: An entire screen/monitor
    """
    
    Window = auto()  # Capture a specific window
    Screen = auto()  # Capture an entire screen/monitor 