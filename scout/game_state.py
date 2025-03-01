"""
Game State Tracker

This module provides centralized game state tracking including:
- Mouse drag operations (camera movement)
- Template match statistics
- Game window state
- Game coordinates
"""

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum, auto
import time
import logging
import win32api
import win32con
from PyQt6.QtCore import QDateTime
from scout.window_manager import WindowManager

logger = logging.getLogger(__name__)

@dataclass
class GameCoordinates:
    """Represents coordinates in the game world."""
    k: Optional[int] = None  # Kingdom/world number
    x: Optional[int] = None  # X coordinate
    y: Optional[int] = None  # Y coordinate
    timestamp: Optional[str] = None  # When coordinates were captured

    def is_valid(self) -> bool:
        """Check if all coordinates are present."""
        return all(isinstance(v, int) for v in [self.k, self.x, self.y])

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

class DragButton(Enum):
    """Mouse button used for dragging."""
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()

@dataclass
class DragState:
    """State of an ongoing drag operation."""
    active: bool = False
    button: Optional[DragButton] = None
    start_x: int = 0
    start_y: int = 0
    current_x: int = 0
    current_y: int = 0
    start_time: float = 0.0
    last_move_time: float = 0.0

@dataclass
class TemplateMatchState:
    """Current state of template matches."""
    count: int = 0
    locations: List[Tuple[str, int, int, int, int, float]] = None  # (name, x, y, w, h, conf)
    last_update_time: float = 0.0

    def __post_init__(self):
        if self.locations is None:
            self.locations = []

class GameState:
    """
    Tracks the current state of the game including mouse operations and template matches.
    
    This class provides centralized state tracking for:
    - Mouse drag operations (camera movement)
    - Template match statistics and locations
    - Game window state and activity
    - Game world coordinates
    
    It uses the Win32 API to track mouse events within the game window.
    """
    
    def __init__(self, window_manager: WindowManager):
        """
        Initialize game state tracking.
        
        Args:
            window_manager: WindowManager instance for window state tracking
        """
        self.window_manager = window_manager
        self.drag_state = DragState()
        self.template_state = TemplateMatchState()
        self.coordinates = GameCoordinates()  # Current game coordinates
        
        # Configuration
        self.drag_start_delay = 0.1  # seconds
        self.drag_timeout = 0.5  # seconds
        
        # Internal state
        self._last_check_time = 0.0
        
    def update(self) -> None:
        """Update game state including drag detection and timeout checking."""
        current_time = time.time()
        
        # Only check every few milliseconds to avoid excessive CPU usage
        if current_time - self._last_check_time < 0.016:  # ~60 Hz
            return
            
        self._last_check_time = current_time
        
        # Check if we're in the game window
        if not self.window_manager.find_window():
            self._reset_drag_state()
            return
            
        # Get mouse position
        cursor_pos = win32api.GetCursorPos()
        
        # Convert to client coordinates
        client_x, client_y = self.window_manager.screen_to_client(*cursor_pos)
        
        # Check mouse buttons and update drag state
        left_pressed = win32api.GetKeyState(win32con.VK_LBUTTON) < 0
        right_pressed = win32api.GetKeyState(win32con.VK_RBUTTON) < 0
        
        # Handle drag start
        if not self.drag_state.active:
            if left_pressed or right_pressed:
                button = DragButton.LEFT if left_pressed else DragButton.RIGHT
                self._start_drag(client_x, client_y, button)
        # Handle ongoing drag
        elif self.drag_state.active:
            # Check if button released
            if (self.drag_state.button == DragButton.LEFT and not left_pressed) or \
               (self.drag_state.button == DragButton.RIGHT and not right_pressed):
                self._end_drag()
            else:
                self._update_drag(client_x, client_y)
                
        # Check for drag timeout
        if self.drag_state.active and \
           current_time - self.drag_state.last_move_time > self.drag_timeout:
            self._end_drag()
            
    def _start_drag(self, x: int, y: int, button: DragButton) -> None:
        """Start tracking a new drag operation."""
        current_time = time.time()
        self.drag_state = DragState(
            active=True,
            button=button,
            start_x=x,
            start_y=y,
            current_x=x,
            current_y=y,
            start_time=current_time,
            last_move_time=current_time
        )
        logger.debug(f"Started {button.name} drag at ({x}, {y})")
        
    def _update_drag(self, x: int, y: int) -> None:
        """Update current drag position."""
        if not self.drag_state.active:
            return
            
        # Only update if position changed
        if x != self.drag_state.current_x or y != self.drag_state.current_y:
            self.drag_state.current_x = x
            self.drag_state.current_y = y
            self.drag_state.last_move_time = time.time()
            
    def _end_drag(self) -> None:
        """End current drag operation."""
        if self.drag_state.active:
            logger.debug(f"Ended {self.drag_state.button.name} drag at "
                        f"({self.drag_state.current_x}, {self.drag_state.current_y})")
            self._reset_drag_state()
            
    def _reset_drag_state(self) -> None:
        """Reset drag state to inactive."""
        self.drag_state = DragState()
        
    def update_template_matches(self, matches: List[Tuple[str, int, int, int, int, float]]) -> None:
        """
        Update template match state.
        
        Args:
            matches: List of (name, x, y, w, h, confidence) tuples
        """
        self.template_state.count = len(matches)
        self.template_state.locations = matches
        self.template_state.last_update_time = time.time()
        
    def update_coordinates(self, k: Optional[int] = None, x: Optional[int] = None, 
                         y: Optional[int] = None) -> bool:
        """
        Update game world coordinates.
        
        This method only updates coordinates if they are valid. If any coordinate
        is None or invalid, it will not update that specific coordinate and will
        maintain the last valid value.
        
        Args:
            k: Kingdom/world number
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if any coordinates were updated, False otherwise
        """
        updated = False
        
        # Only update valid values
        if k is not None and self._is_valid_coordinate(k, 'k'):
            self.coordinates.k = k
            updated = True
            
        if x is not None and self._is_valid_coordinate(x, 'x'):
            self.coordinates.x = x
            updated = True
            
        if y is not None and self._is_valid_coordinate(y, 'y'):
            self.coordinates.y = y
            updated = True
            
        if updated:
            # Update timestamp only if something changed
            self.coordinates.timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            logger.info(f"Updated game coordinates: {self.coordinates}")
        
        return updated
        
    def _is_valid_coordinate(self, value: int, coord_type: str) -> bool:
        """
        Validate a coordinate value.
        
        Args:
            value: Value to validate
            coord_type: Type of coordinate ('k', 'x', or 'y')
            
        Returns:
            True if the coordinate is valid, False otherwise
        """
        try:
            if coord_type.lower() == 'k':
                return 1 <= value <= 999  # Kingdom numbers are typically 1-999
            elif coord_type.lower() in ('x', 'y'):
                return 0 <= value <= 999  # Game world coordinates are typically 0-999
            return False
        except (TypeError, ValueError):
            return False
            
    def get_coordinates(self) -> GameCoordinates:
        """
        Get current game coordinates.
        
        This will always return the last valid coordinates, even if some values
        are missing. The coordinates object has an is_valid() method that can be
        used to check if all coordinates are present.
        
        Returns:
            GameCoordinates object with the current coordinates
        """
        return self.coordinates
        
    def reset_coordinates(self) -> None:
        """
        Reset all coordinates to None.
        
        This should only be called when explicitly needed, such as when
        the application is restarted or when coordinates need to be
        completely reset.
        """
        self.coordinates = GameCoordinates()
        logger.info("Reset game coordinates to None")
        
    def is_dragging(self) -> bool:
        """Check if drag operation is in progress."""
        return self.drag_state.active
        
    def get_drag_info(self) -> Optional[Tuple[DragButton, int, int, int, int, float]]:
        """
        Get information about current drag operation.
        
        Returns:
            Tuple of (button, start_x, start_y, current_x, current_y, duration) or None if not dragging
        """
        if not self.drag_state.active:
            return None
            
        return (
            self.drag_state.button,
            self.drag_state.start_x,
            self.drag_state.start_y,
            self.drag_state.current_x,
            self.drag_state.current_y,
            time.time() - self.drag_state.start_time
        )
        
    def get_template_info(self) -> Tuple[int, float]:
        """
        Get template match statistics.
        
        Returns:
            Tuple of (match_count, time_since_last_update)
        """
        return (
            self.template_state.count,
            time.time() - self.template_state.last_update_time
        ) 