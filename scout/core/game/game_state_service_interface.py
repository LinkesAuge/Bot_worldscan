"""
Game State Service Interface

This module re-exports the GameServiceInterface from the game_service_interface module
as GameStateServiceInterface for backward compatibility.
"""

from .game_service_interface import GameServiceInterface as GameStateServiceInterface

# Re-export the GameStateServiceInterface class
__all__ = ['GameStateServiceInterface'] 