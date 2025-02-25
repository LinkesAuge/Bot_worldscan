"""
Singleton Design Pattern

This module implements the Singleton design pattern as a metaclass. 
The Singleton pattern ensures that a class has only one instance and provides 
a global point of access to that instance.

Using a metaclass approach allows for a cleaner implementation where the 
singleton behavior is inherited rather than requiring specific code in each
singleton class.
"""

from typing import Dict, Any, Type


class Singleton(type):
    """
    Metaclass for implementing the Singleton pattern.
    
    This metaclass ensures that only one instance of a class is created,
    and provides global access to that instance.
    
    Usage:
        ```
        class MyClass(metaclass=Singleton):
            def __init__(self, arg1, arg2):
                # initialization code
        
        # Get the singleton instance
        instance1 = MyClass(arg1, arg2)  # Creates the instance
        instance2 = MyClass()  # Returns the existing instance
        assert instance1 is instance2  # Same instance
        ```
    
    When using with Protocol classes:
        ```
        # Declare a compatible metaclass
        class SingletonProtocol(Singleton):
            pass
            
        # Use it with a Protocol base class
        class MyService(MyProtocol, metaclass=SingletonProtocol):
            # Implementation
        ```
    """
    
    # Dictionary to store singleton instances
    _instances: Dict[Type, Any] = {}
    
    def __call__(cls, *args, **kwargs):
        """
        Called when the class is "called" to create an instance.
        
        Args:
            *args: Arguments to pass to the class constructor
            **kwargs: Keyword arguments to pass to the class constructor
            
        Returns:
            The singleton instance of the class
        """
        # Check if instance already exists
        if cls not in cls._instances:
            # Create new instance
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    
    @classmethod
    def clear_instance(cls, target_cls):
        """
        Clear a specific singleton instance.
        
        This is useful for testing when you need to reset a singleton.
        
        Args:
            target_cls: The class whose instance should be cleared
        """
        if target_cls in cls._instances:
            del cls._instances[target_cls]
    
    @classmethod
    def clear_all_instances(cls):
        """
        Clear all singleton instances.
        
        This is useful for resetting the application state.
        """
        cls._instances.clear()


# Metaclass that works with Protocol classes
class SingletonProtocol(Singleton):
    """
    Metaclass that combines Singleton functionality with Protocol compatibility.
    
    Use this metaclass when creating a singleton class that also implements a Protocol:
    
    ```
    class MyService(MyProtocol, metaclass=SingletonProtocol):
        # Implementation
    ```
    """
    pass 