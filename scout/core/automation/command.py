"""
Command Pattern

This module implements the Command pattern for automation actions.
Commands encapsulate all the information needed to execute an action,
allowing for extensible automation capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from ..interfaces.service_interfaces import WindowServiceInterface

class Command(ABC):
    """
    Base class for automation commands.
    
    This implements the command pattern, encapsulating all the information
    needed to perform an action. Commands:
    
    - Are self-contained units of work
    - Store their own parameters
    - Can be executed and track their own results
    - Can be serialized and deserialized for storage
    
    Commands are used to represent individual steps in an automation sequence.
    """
    
    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize the command with parameters.
        
        Args:
            params: Dictionary of parameters specific to the command type
        """
        self.params = params
        self.result: bool = False
        self.message: str = ""
    
    @abstractmethod
    def execute(self, window_service: WindowServiceInterface) -> bool:
        """
        Execute the command.
        
        This method should be implemented by concrete command classes to
        perform the actual action.
        
        Args:
            window_service: Window service for window-related operations
            
        Returns:
            bool: Whether the command executed successfully
        """
        pass
    
    def set_result(self, success: bool, message: str) -> None:
        """
        Set the execution result.
        
        Args:
            success: Whether the command succeeded
            message: Result message or error
        """
        self.result = success
        self.message = message
    
    def get_result(self) -> Tuple[bool, str]:
        """
        Get the execution result.
        
        Returns:
            Tuple containing (success, message)
        """
        return (self.result, self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the command to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the command
        """
        return {
            'type': self.__class__.__name__,
            'params': self.params,
            'result': self.result,
            'message': self.message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """
        Create a command from a dictionary.
        
        This is a factory method that should be implemented by a command factory.
        Here we provide a placeholder implementation that will be overridden.
        
        Args:
            data: Dictionary containing command data
            
        Returns:
            A Command instance
            
        Raises:
            ValueError: If the command type is not recognized
        """
        from .command_factory import CommandFactory
        
        command_type = data.get('type')
        params = data.get('params', {})
        
        if not command_type:
            raise ValueError("Command data must contain 'type' field")
            
        command = CommandFactory.create_command(command_type, params)
        if not command:
            raise ValueError(f"Unknown command type: {command_type}")
            
        if 'result' in data:
            command.result = data['result']
        if 'message' in data:
            command.message = data['message']
            
        return command 