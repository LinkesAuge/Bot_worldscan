from dataclasses import dataclass
from typing import Optional

@dataclass
class GameWorldPosition:
    """
    Represents a position in the game world.
    
    This class stores coordinates in the game world's coordinate system,
    which consists of K (world number), X, and Y coordinates. It can also
    optionally store the corresponding screen coordinates.
    
    Attributes:
        x: X coordinate in the game world
        y: Y coordinate in the game world
        k: K coordinate (world number) in the game
        screen_x: Optional X coordinate on screen (pixels)
        screen_y: Optional Y coordinate on screen (pixels)
    """
    x: float
    y: float
    k: int = 0
    screen_x: Optional[int] = None
    screen_y: Optional[int] = None
    
    def __str__(self) -> str:
        """
        String representation of the position.
        
        Returns:
            Formatted string with K, X, and Y coordinates
        """
        # Format coordinates with a maximum of 3 digits
        k_str = f"{self.k:03d}" if self.k is not None else "---"
        x_str = f"{int(self.x):03d}" if self.x is not None else "---"
        y_str = f"{int(self.y):03d}" if self.y is not None else "---"
        
        return f"K:{k_str} X:{x_str} Y:{y_str}" 