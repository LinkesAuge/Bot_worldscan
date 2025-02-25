"""
Command Factory

This module provides a factory for creating command objects based on their type.
The factory maintains a registry of command types and creates appropriate instances.
"""

from typing import Dict, Any, Optional, Type
from .command import Command

class CommandFactory:
    """
    Factory for creating command objects.
    
    This factory:
    - Maintains a registry of command types
    - Creates command instances based on type name
    - Allows dynamic registration of new command types
    
    This is part of the Command pattern implementation, handling
    the creation of command objects based on their type.
    """
    
    # Registry of command types (populated by subclass imports)
    _commands: Dict[str, Type[Command]] = {}
    
    @classmethod
    def create_command(cls, type_name: str, params: Dict[str, Any]) -> Optional[Command]:
        """
        Create a command of the specified type.
        
        Args:
            type_name: Type name of the command to create
            params: Parameters to pass to the command constructor
            
        Returns:
            Command instance or None if type not found
        """
        if type_name not in cls._commands:
            return None
        
        command_class = cls._commands[type_name]
        return command_class(params)
    
    @classmethod
    def register_command(cls, type_name: str, command_class: Type[Command]) -> None:
        """
        Register a new command type.
        
        Args:
            type_name: Type name for the command
            command_class: Command class to register
        """
        cls._commands[type_name] = command_class
    
    @classmethod
    def get_registered_types(cls) -> list[str]:
        """
        Get all registered command types.
        
        Returns:
            List of registered command type names
        """
        return list(cls._commands.keys()) 