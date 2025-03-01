"""
Game World Position

This module provides classes for representing positions and coordinates in the game world.
"""

from dataclasses import dataclass
from typing import Optional, Union
from PyQt6.QtCore import QDateTime

@dataclass
class GameCoordinates:
    """Represents coordinates in the game world."""
    k: Optional[int] = None  # Kingdom/world number
    x: Optional[int] = None  # X coordinate
    y: Optional[int] = None  # Y coordinate
    timestamp: Optional[str] = None  # When coordinates were captured

    def __post_init__(self):
        """Convert and validate coordinates after initialization."""
        # Convert to integers if values are provided
        if self.k is not None:
            self.k = int(self.k)
        if self.x is not None:
            self.x = int(self.x)
        if self.y is not None:
            self.y = int(self.y)
            
        # Validate ranges
        if self.k is not None and (self.k < 0 or self.k > 999):
            raise ValueError(f"Kingdom number must be between 0 and 999, got {self.k}")
        if self.x is not None and (self.x < 0 or self.x > 999):
            raise ValueError(f"X coordinate must be between 0 and 999, got {self.x}")
        if self.y is not None and (self.y < 0 or self.y > 999):
            raise ValueError(f"Y coordinate must be between 0 and 999, got {self.y}")

    def is_valid(self) -> bool:
        """Check if all coordinates are present and within valid ranges."""
        return (self.k is not None and self.x is not None and self.y is not None and
                isinstance(self.k, int) and isinstance(self.x, int) and isinstance(self.y, int) and
                0 <= self.k <= 999 and 0 <= self.x <= 999 and 0 <= self.y <= 999)

    def __str__(self) -> str:
        """String representation of coordinates with timestamp."""
        # Format coordinates with a maximum of 3 digits
        k_str = f"{self.k:03d}" if self.k is not None else "---"
        x_str = f"{self.x:03d}" if self.x is not None else "---"
        y_str = f"{self.y:03d}" if self.y is not None else "---"
        
        coords = f"K: {k_str}, X: {x_str}, Y: {y_str}"
        if self.timestamp:
            coords += f" ({self.timestamp})"
        return coords

@dataclass
class GameWorldPosition:
    """
    Represents a position in the game world using K (kingdom), X, and Y coordinates.
    
    All coordinates are converted to integers and validated during initialization.
    """
    k: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    
    def __post_init__(self):
        """Convert and validate coordinates after initialization."""
        # Convert to integers if values are provided
        if self.k is not None:
            self.k = int(self.k)
        if self.x is not None:
            self.x = int(self.x)
        if self.y is not None:
            self.y = int(self.y)
            
        # Validate ranges
        if self.k is not None and (self.k < 0 or self.k > 999):
            raise ValueError(f"Kingdom number must be between 0 and 999, got {self.k}")
        if self.x is not None and (self.x < 0 or self.x > 999):
            raise ValueError(f"X coordinate must be between 0 and 999, got {self.x}")
        if self.y is not None and (self.y < 0 or self.y > 999):
            raise ValueError(f"Y coordinate must be between 0 and 999, got {self.y}")
    
    def __str__(self) -> str:
        """String representation in K:X:Y format."""
        return f"K:{self.k or '???'} X:{self.x or '???'} Y:{self.y or '???'}"
    
    def is_valid(self) -> bool:
        """Check if all coordinates are valid."""
        return (self.k is not None and self.x is not None and self.y is not None and
                isinstance(self.k, int) and isinstance(self.x, int) and isinstance(self.y, int) and
                0 <= self.k <= 999 and 0 <= self.x <= 999 and 0 <= self.y <= 999)
    
    def __eq__(self, other: object) -> bool:
        """Check if two positions are equal."""
        if not isinstance(other, GameWorldPosition):
            return NotImplemented
        if not self.is_valid() or not other.is_valid():
            return False
        return (self.k == other.k and 
                self.x == other.x and 
                self.y == other.y)
    
    def __lt__(self, other: 'GameWorldPosition') -> bool:
        """Compare positions for less than."""
        if not isinstance(other, GameWorldPosition):
            return NotImplemented
        if not self.is_valid() or not other.is_valid():
            return False
        return (self.k, self.x, self.y) < (other.k, other.x, other.y)
    
    def __le__(self, other: 'GameWorldPosition') -> bool:
        """Compare positions for less than or equal."""
        if not isinstance(other, GameWorldPosition):
            return NotImplemented
        if not self.is_valid() or not other.is_valid():
            return False
        return (self.k, self.x, self.y) <= (other.k, other.x, other.y)
    
    def __gt__(self, other: 'GameWorldPosition') -> bool:
        """Compare positions for greater than."""
        if not isinstance(other, GameWorldPosition):
            return NotImplemented
        if not self.is_valid() or not other.is_valid():
            return False
        return (self.k, self.x, self.y) > (other.k, other.x, other.y)
    
    def __ge__(self, other: 'GameWorldPosition') -> bool:
        """Compare positions for greater than or equal."""
        if not isinstance(other, GameWorldPosition):
            return NotImplemented
        if not self.is_valid() or not other.is_valid():
            return False
        return (self.k, self.x, self.y) >= (other.k, other.x, other.y)
    
    def __sub__(self, other: 'GameWorldPosition') -> Optional['GameWorldPosition']:
        """Calculate coordinate differences with wrapping."""
        if not isinstance(other, GameWorldPosition):
            raise TypeError("Can only subtract GameWorldPosition objects")
            
        if not self.is_valid() or not other.is_valid():
            return None
            
        return GameWorldPosition(
            k=self.k,  # Keep original kingdom
            x=(self.x - other.x) % 1000,
            y=(self.y - other.y) % 1000
        )
    
    def distance_to(self, other: 'GameWorldPosition') -> Optional[tuple[int, int]]:
        """
        Calculate wrapped distance to another position.
        
        Returns:
            tuple[int, int]: (dx, dy) where each is the shortest wrapped distance,
            or None if either position is invalid
        """
        if not isinstance(other, GameWorldPosition):
            raise TypeError("Can only calculate distance to GameWorldPosition objects")
            
        if not self.is_valid() or not other.is_valid():
            return None
            
        dx = (other.x - self.x) % 1000
        dy = (other.y - self.y) % 1000
        
        # Adjust for shortest path (if wrapped distance is more than half world size)
        if dx > 500:
            dx = dx - 1000
        if dy > 500:
            dy = dy - 1000
            
        return (dx, dy) 