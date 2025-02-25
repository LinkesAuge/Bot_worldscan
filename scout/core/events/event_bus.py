"""
Event Bus

This module re-exports the EventBus from the scout.core.services package
for backward compatibility with existing code.
"""

from ..services.event_bus import EventBus

# Re-export the EventBus class
__all__ = ['EventBus'] 