"""World coordinate system types and utilities."""

from dataclasses import dataclass

@dataclass
class WorldPosition:
    """
    Represents a location in the game world's coordinate system.
    
    The game world uses a grid-based coordinate system where each position
    is defined by:
    - x: Horizontal position (0-999)
    - y: Vertical position (0-999)
    - k: World/kingdom number
    
    This class is used to track and navigate between different locations
    in the game world during scanning operations.
    
    Attributes:
        x: Horizontal position (0-999)
        y: Vertical position (0-999)
        k: World/kingdom number
    """
    x: int  # 0-999
    y: int  # 0-999
    k: int  # World number
    
    def __str__(self) -> str:
        """Return string representation of position."""
        return f"X={self.x}, Y={self.y}, K={self.k}" 