"""
Automation Service Interface

This module re-exports the AutomationServiceInterface from the scout.core.interfaces package
for backward compatibility with existing code.
"""

from ..interfaces.service_interfaces import AutomationServiceInterface

# Re-export the AutomationServiceInterface class
__all__ = ['AutomationServiceInterface'] 