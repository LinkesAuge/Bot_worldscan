"""
Task Core Types

This module defines the base Task classes and supporting types used by the automation system:
- Task: Base class for automation tasks
- CompositeTask: Container for multiple tasks
- TaskPriority: Task priority enum
- TaskStatus: Task status enum
"""

from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class TaskPriority(Enum):
    """Priority levels for tasks."""
    HIGH = auto()      # Critical tasks that should be executed first
    NORMAL = auto()    # Default priority for most tasks
    LOW = auto()       # Background tasks that can be delayed


class TaskStatus(Enum):
    """Status of task execution."""
    PENDING = auto()    # Task has not started execution
    RUNNING = auto()    # Task is currently executing
    COMPLETED = auto()  # Task completed successfully
    FAILED = auto()     # Task failed to complete
    CANCELED = auto()   # Task was canceled before completion


class Task(ABC):
    """
    Base class for automation tasks.
    
    A task represents a single action to be performed as part of an automation sequence,
    such as clicking, typing, or waiting. Tasks can be composed into complex operations.
    """
    
    def __init__(self, name: str, priority: TaskPriority = TaskPriority.NORMAL):
        """
        Initialize a task.
        
        Args:
            name: Task name for identification
            priority: Task priority level
        """
        self.name = name
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.error = None
        self.result = None
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the task with the given context.
        
        Args:
            context: Execution context with services and state information
            
        Returns:
            True if task executed successfully, False otherwise
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of the task."""
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.priority}, status={self.status})"


class CompositeTask(Task):
    """
    A task that contains multiple sub-tasks to be executed in sequence.
    
    This allows complex operations to be built from simpler tasks.
    """
    
    def __init__(self, name: str, tasks: List[Task], priority: TaskPriority = TaskPriority.NORMAL):
        """
        Initialize a composite task.
        
        Args:
            name: Task name for identification
            tasks: List of sub-tasks to execute
            priority: Task priority level
        """
        super().__init__(name, priority)
        self.tasks = tasks
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute all sub-tasks in sequence.
        
        Args:
            context: Execution context with services and state information
            
        Returns:
            True if all tasks executed successfully, False otherwise
        """
        self.status = TaskStatus.RUNNING
        
        for task in self.tasks:
            success = task.execute(context)
            if not success:
                self.error = f"Sub-task '{task.name}' failed: {task.error}"
                self.status = TaskStatus.FAILED
                return False
        
        self.status = TaskStatus.COMPLETED
        return True 