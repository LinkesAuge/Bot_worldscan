"""
Game Service Interface

This module defines the interface for the Game Service, which is responsible for
managing the game state and providing access to game-related functionality.
"""

from typing import Dict, Optional, Protocol
from abc import abstractmethod

from .game_state import GameState


class GameServiceInterface(Protocol):
    """
    Interface for game services.
    
    The GameService is responsible for:
    - Maintaining the current game state
    - Updating the state based on screen detection
    - Providing methods to query and manipulate the game state
    - Publishing events when the game state changes
    """
    
    @property
    @abstractmethod
    def state(self) -> GameState:
        """
        Get the current game state.
        
        Returns:
            The current GameState
        """
        ...
    
    @abstractmethod
    def configure_detection_regions(self, regions: Dict[str, Dict[str, int]]) -> None:
        """
        Configure detection regions for different game elements.
        
        Args:
            regions: Dictionary mapping region name to bounding box
        """
        ...
    
    @abstractmethod
    def update_state(self, force_detection: bool = False) -> None:
        """
        Update the game state by performing detections.
        
        This method:
        1. Captures the current game view
        2. Detects game elements using the Detection Service
        3. Updates the game state based on detected elements
        
        Args:
            force_detection: Whether to bypass caching in the Detection Service
        """
        ... 