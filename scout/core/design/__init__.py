"""
Design Patterns Module

This package contains implementations of common design patterns used throughout the Scout application.
These patterns help improve code organization, reduce coupling, and enhance maintainability.

Patterns implemented in this package:
- Singleton: Ensures a class has only one instance with global access
- SingletonProtocol: Variant of Singleton that works with Protocol classes
- Observer: Allows objects to notify other objects of state changes
- Strategy: Defines a family of algorithms and makes them interchangeable
- Factory: Creates objects without specifying the exact class to create
"""

from .singleton import Singleton, SingletonProtocol

__all__ = ['Singleton', 'SingletonProtocol'] 