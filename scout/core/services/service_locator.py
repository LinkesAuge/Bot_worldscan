"""
Service Locator

This module provides a centralized registry for application services,
allowing for easy access and dependency management.
"""

from typing import Dict, Any, Optional, Type, TypeVar

T = TypeVar('T')

class ServiceLocator:
    """
    Service locator for managing application services.
    
    This class implements the Service Locator pattern, providing a central
    registry for services in the application. It allows services to be
    registered and retrieved by name, facilitating dependency injection
    and making services accessible throughout the application.
    """
    
    # Class-level registry of services
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str, service: Any) -> None:
        """
        Register a service with the locator.
        
        Args:
            name: Name of the service
            service: Service instance to register
        """
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str) -> Any:
        """
        Get a service by name.
        
        Args:
            name: Name of the service to get
            
        Returns:
            The requested service
            
        Raises:
            KeyError: If the service is not registered
        """
        if name not in cls._services:
            raise KeyError(f"Service '{name}' is not registered")
        return cls._services[name]
    
    @classmethod
    def get_typed(cls, name: str, service_type: Type[T]) -> T:
        """
        Get a service by name with type checking.
        
        Args:
            name: Name of the service to get
            service_type: Expected type of the service
            
        Returns:
            The requested service
            
        Raises:
            KeyError: If the service is not registered
            TypeError: If the service is not of the expected type
        """
        service = cls.get(name)
        if not isinstance(service, service_type):
            raise TypeError(f"Service '{name}' is not of type {service_type.__name__}")
        return service
    
    @classmethod
    def get_event_bus(cls):
        """Get the event bus service."""
        return cls.get("event_bus")
    
    @classmethod
    def get_window_service(cls):
        """Get the window service."""
        return cls.get("window")
    
    @classmethod
    def get_detection_service(cls):
        """Get the detection service."""
        return cls.get("detection")
    
    @classmethod
    def get_game_service(cls):
        """Get the game service."""
        return cls.get("game")
    
    @classmethod
    def get_automation_service(cls):
        """Get the automation service."""
        return cls.get("automation")
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            name: Name of the service to check
            
        Returns:
            True if the service is registered, False otherwise
        """
        return name in cls._services
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a service.
        
        Args:
            name: Name of the service to unregister
            
        Raises:
            KeyError: If the service is not registered
        """
        if name not in cls._services:
            raise KeyError(f"Service '{name}' is not registered")
        del cls._services[name]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered services."""
        cls._services.clear() 