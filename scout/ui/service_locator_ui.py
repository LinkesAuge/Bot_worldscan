"""
UI Service Locator

This module provides a service locator specific to the UI layer of the Scout application.
It allows UI components to access core services without creating circular imports.
"""

import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)


class ServiceLocator:
    """
    Service locator for managing application services in the UI layer.
    
    This class provides access to core services needed by the UI components,
    ensuring type-safe access and proper initialization/shutdown.
    """
    
    _services = {}  # Static dictionary of services
    
    @classmethod
    def register(cls, interface_class, implementation):
        """
        Register a service implementation for a given interface.
        
        Args:
            interface_class: Interface class that the implementation implements
            implementation: Service implementation instance
        """
        cls._services[interface_class] = implementation
        logger.debug(f"Registered service: {interface_class.__name__}")
    
    @classmethod
    def get(cls, interface_class):
        """
        Get a service by its interface.
        
        Args:
            interface_class: Interface class to look up
            
        Returns:
            Implementation instance or None if not found
        """
        if interface_class in cls._services:
            return cls._services[interface_class]
        
        logger.error(f"Service not found: {interface_class.__name__}")
        return None
    
    @classmethod
    def shutdown(cls):
        """
        Shut down all registered services.
        
        This method should be called when the application is shutting down to
        ensure a clean exit.
        """
        for service in cls._services.values():
            if hasattr(service, 'shutdown'):
                try:
                    service.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down service: {e}")
        
        cls._services.clear()
        logger.debug("All services shut down") 