"""
Base Model

This module provides a base class for all UI models in the Scout application.
It implements common functionality needed by models in the MVC pattern.
"""

from typing import Any, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class BaseModel(QObject):
    """
    Base class for all UI models.
    
    This class implements the model part of the MVC pattern. It provides:
    - Property change notifications
    - Data validation methods
    - Serialization capabilities
    
    Models are responsible for managing data and business logic,
    notifying views when data changes.
    """
    
    # Signal emitted when any property changes
    property_changed = pyqtSignal(str, object)  # property_name, new_value
    
    def __init__(self):
        """Initialize the base model."""
        super().__init__()
        self._data: Dict[str, Any] = {}
        self._changed: bool = False
    
    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get a property value.
        
        Args:
            name: Property name
            default: Default value if property doesn't exist
            
        Returns:
            Property value or default
        """
        return self._data.get(name, default)
    
    def set_property(self, name: str, value: Any) -> None:
        """
        Set a property value and notify listeners.
        
        Args:
            name: Property name
            value: New property value
        """
        old_value = self._data.get(name)
        
        # Only update and notify if value actually changed
        if old_value != value:
            self._data[name] = value
            self._changed = True
            self.property_changed.emit(name, value)
    
    def has_property(self, name: str) -> bool:
        """
        Check if a property exists.
        
        Args:
            name: Property name
            
        Returns:
            True if property exists, False otherwise
        """
        return name in self._data
    
    def is_changed(self) -> bool:
        """
        Check if the model has been changed since last reset.
        
        Returns:
            True if model has been changed, False otherwise
        """
        return self._changed
    
    def reset_changed(self) -> None:
        """Reset the changed flag."""
        self._changed = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to a dictionary.
        
        Returns:
            Dictionary representation of model data
        """
        return self._data.copy()
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model from a dictionary.
        
        Args:
            data: Dictionary containing property values
        """
        for name, value in data.items():
            self.set_property(name, value) 