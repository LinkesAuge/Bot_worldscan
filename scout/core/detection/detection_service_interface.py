"""
Detection Service Interface

This module re-exports the DetectionServiceInterface from the scout.core.interfaces package
for backward compatibility with existing code.
"""

from ..interfaces.service_interfaces import DetectionServiceInterface

# Re-export the DetectionServiceInterface class
__all__ = ['DetectionServiceInterface'] 