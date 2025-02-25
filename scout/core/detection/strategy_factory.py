"""
Detection Strategy Factory

This module provides a factory for creating detection strategy objects.
It maintains a registry of strategy types and creates appropriate instances.
"""

from typing import Dict, Optional, Type
from .strategy import DetectionStrategy

class StrategyFactory:
    """
    Factory for creating detection strategy objects.
    
    This factory:
    - Maintains a registry of strategy types
    - Creates strategy instances based on type name
    - Allows dynamic registration of new strategy types
    
    This is part of the Strategy pattern implementation, handling
    the creation of strategy objects based on their type.
    """
    
    # Registry of strategy types (populated by subclass imports)
    _strategies: Dict[str, Type[DetectionStrategy]] = {}
    
    @classmethod
    def create_strategy(cls, strategy_type: str) -> Optional[DetectionStrategy]:
        """
        Create a strategy of the specified type.
        
        Args:
            strategy_type: Type name of the strategy to create
            
        Returns:
            DetectionStrategy instance or None if type not found
        """
        if strategy_type not in cls._strategies:
            return None
        
        strategy_class = cls._strategies[strategy_type]
        return strategy_class()
    
    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: Type[DetectionStrategy]) -> None:
        """
        Register a new strategy type.
        
        Args:
            strategy_type: Type name for the strategy
            strategy_class: Strategy class to register
        """
        cls._strategies[strategy_type] = strategy_class
    
    @classmethod
    def get_registered_types(cls) -> list[str]:
        """
        Get all registered strategy types.
        
        Returns:
            List of registered strategy type names
        """
        return list(cls._strategies.keys()) 