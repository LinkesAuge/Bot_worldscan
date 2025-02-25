"""
Automation Service Interface

This module defines the interface for the Automation Service, which is responsible
for scheduling and executing automation tasks.
"""

from typing import Dict, List, Optional, Any, Protocol
from abc import abstractmethod

from .task import Task, TaskPriority, TaskStatus


class AutomationServiceInterface(Protocol):
    """
    Interface for automation services.
    
    The automation service is responsible for:
    - Scheduling and executing automation tasks
    - Managing task dependencies and priorities
    - Tracking task status and results
    - Notifying when tasks complete or fail
    """
    
    @abstractmethod
    def add_task(self, task: Task) -> None:
        """
        Add a task to the execution queue.
        
        Args:
            task: Task to add
        """
        ...
    
    @abstractmethod
    def add_tasks(self, tasks: List[Task]) -> None:
        """
        Add multiple tasks to the execution queue.
        
        Args:
            tasks: List of tasks to add
        """
        ...
    
    @abstractmethod
    def get_task(self, task_name: str) -> Optional[Task]:
        """
        Get a task by name.
        
        Args:
            task_name: Name of the task to get
            
        Returns:
            The task if found, None otherwise
        """
        ...
    
    @abstractmethod
    def get_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """
        Get all tasks, optionally filtered by status.
        
        Args:
            status: Status to filter by, or None for all tasks
            
        Returns:
            List of matching tasks
        """
        ...
    
    @abstractmethod
    def cancel_task(self, task_name: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_name: Name of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        ...
    
    @abstractmethod
    def cancel_all_tasks(self) -> None:
        """Cancel all pending tasks."""
        ...
    
    @abstractmethod
    def start_execution(self) -> None:
        """Start task execution."""
        ...
    
    @abstractmethod
    def pause_execution(self) -> None:
        """Pause task execution."""
        ...
    
    @abstractmethod
    def resume_execution(self) -> None:
        """Resume task execution."""
        ...
    
    @abstractmethod
    def stop_execution(self) -> None:
        """Stop task execution."""
        ...
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the automation service is running.
        
        Returns:
            True if the service is running, False otherwise
        """
        ...
    
    @abstractmethod
    def is_paused(self) -> bool:
        """
        Check if the automation service is paused.
        
        Returns:
            True if the service is paused, False otherwise
        """
        ...
    
    @abstractmethod
    def execute_task_synchronously(self, task: Task) -> bool:
        """
        Execute a task synchronously (blocking).
        
        This method is useful for simple automation sequences where
        you want to wait for the task to complete before continuing.
        
        Args:
            task: Task to execute
            
        Returns:
            True if the task was successful, False otherwise
        """
        ... 