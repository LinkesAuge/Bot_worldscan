"""
Window Service Interface

This module re-exports the WindowServiceInterface from the scout.core.interfaces package
for backward compatibility with existing code.
"""

from ..interfaces.service_interfaces import WindowServiceInterface

# Re-export the WindowServiceInterface class
__all__ = ['WindowServiceInterface'] 