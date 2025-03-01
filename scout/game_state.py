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
from scout.game_world_position import GameWorldPosition, GameCoordinates

logger = logging.getLogger(__name__)

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
        self._coordinates = GameCoordinates()  # Current game coordinates
        
        # Configuration
        self.drag_start_delay = 0.1  # seconds
        self.drag_timeout = 0.5  # seconds
        
        # Internal state
        self._last_check_time = 0.0
        
    @property
    def coordinates(self) -> GameCoordinates:
        """Get the current coordinates."""
        return self._coordinates
        
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
        if k is not None and isinstance(k, int) and 0 <= k <= 999:
            self._coordinates.k = k
            updated = True
            
        if x is not None and isinstance(x, int) and 0 <= x <= 999:
            self._coordinates.x = x
            updated = True
            
        if y is not None and isinstance(y, int) and 0 <= y <= 999:
            self._coordinates.y = y
            updated = True
            
        if updated:
            # Update timestamp only if something changed
            self._coordinates.timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            logger.info(f"Updated game coordinates: {self._coordinates}")
            
            # Log validity state
            if self._coordinates.is_valid():
                logger.debug("Coordinates are now valid")
            else:
                logger.warning("Coordinates are still incomplete or invalid")
        
        return updated
        
    def get_coordinates(self) -> Optional[GameWorldPosition]:
        """Get the current game world coordinates."""
        if self._coordinates and self._coordinates.is_valid():
            return GameWorldPosition(
                k=self._coordinates.k,
                x=self._coordinates.x,
                y=self._coordinates.y
            )
        return None
        
    def reset_coordinates(self) -> None:
        """
        Reset all coordinates to None.
        
        This should only be called when explicitly needed, such as when
        the application is restarted or when coordinates need to be
        completely reset.
        """
        self._coordinates = GameCoordinates()
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