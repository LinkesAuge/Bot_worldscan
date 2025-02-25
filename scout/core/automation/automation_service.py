"""
Automation Service

This module provides the AutomationService class, which is responsible for
scheduling and executing automation tasks.
"""

from typing import Dict, List, Optional, Any, Set, Callable
import threading
import time
import logging
import queue
import uuid
from datetime import datetime
from functools import cmp_to_key

from ..design.singleton import Singleton
from ..events.event_bus import EventBus
from ..events.event import Event
from ..events.event_types import EventType
from .automation_service_interface import AutomationServiceInterface
from .task import Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)

class AutomationService(AutomationServiceInterface, metaclass=Singleton):
    """
    Service for managing and executing automation tasks.
    
    This service:
    - Maintains a queue of tasks to execute
    - Handles task dependencies and priorities
    - Executes tasks in a background thread
    - Publishes events for task lifecycle events
    - Provides methods for monitoring and controlling task execution
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize the automation service.
        
        Args:
            event_bus: Event bus for publishing task events
        """
        self.event_bus = event_bus
        self.tasks: Dict[str, Task] = {}
        self.pending_tasks: Set[str] = set()
        self.running: bool = False
        self.paused: bool = False
        self.worker_thread: Optional[threading.Thread] = None
        self.execution_context: Dict[str, Any] = {}
        self._task_queue = queue.PriorityQueue()
        self._task_lock = threading.RLock()
        self._execution_event = threading.Event()
        self._stop_requested = threading.Event()
        self._pause_requested = threading.Event()
        
        logger.debug("AutomationService initialized")
    
    def add_task(self, task: Task) -> None:
        """
        Add a task to the execution queue.
        
        Args:
            task: Task to add
        """
        with self._task_lock:
            # Check if task with same name already exists
            if task.name in self.tasks:
                logger.warning(f"Task with name '{task.name}' already exists, adding with unique name")
                # Generate a unique name by appending a UUID
                original_name = task.name
                task.name = f"{original_name}_{uuid.uuid4().hex[:8]}"
                
            # Add to task dictionary
            self.tasks[task.name] = task
            
            # Add to pending set if not already completed
            if task.status == TaskStatus.PENDING:
                self.pending_tasks.add(task.name)
                
                # If running, add to priority queue
                if self.running:
                    priority_value = task.priority.value
                    self._task_queue.put((priority_value, task.name))
                    
            logger.debug(f"Added task: {task.name} (priority: {task.priority.name})")
            
            # Publish event
            self._publish_task_event(EventType.AUTOMATION_TASK_ADDED, task)
    
    def add_tasks(self, tasks: List[Task]) -> None:
        """
        Add multiple tasks to the execution queue.
        
        Args:
            tasks: List of tasks to add
        """
        for task in tasks:
            self.add_task(task)
    
    def get_task(self, task_name: str) -> Optional[Task]:
        """
        Get a task by name.
        
        Args:
            task_name: Name of the task to get
            
        Returns:
            The task if found, None otherwise
        """
        return self.tasks.get(task_name)
    
    def get_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """
        Get all tasks, optionally filtered by status.
        
        Args:
            status: Status to filter by, or None for all tasks
            
        Returns:
            List of matching tasks
        """
        if status is None:
            return list(self.tasks.values())
        else:
            return [task for task in self.tasks.values() if task.status == status]
    
    def cancel_task(self, task_name: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_name: Name of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        with self._task_lock:
            task = self.tasks.get(task_name)
            if not task:
                logger.warning(f"Cannot cancel: task '{task_name}' not found")
                return False
                
            if task.status != TaskStatus.PENDING:
                logger.warning(f"Cannot cancel: task '{task_name}' is not pending")
                return False
                
            # Mark task as cancelled
            task.cancel()
            
            # Remove from pending set
            if task_name in self.pending_tasks:
                self.pending_tasks.remove(task_name)
                
            logger.debug(f"Cancelled task: {task_name}")
            
            # Publish event
            self._publish_task_event(EventType.AUTOMATION_TASK_CANCELLED, task)
            
            return True
    
    def cancel_all_tasks(self) -> None:
        """Cancel all pending tasks."""
        with self._task_lock:
            pending_task_names = list(self.pending_tasks)  # Create a copy to avoid modification during iteration
            
            for task_name in pending_task_names:
                self.cancel_task(task_name)
            
            logger.debug(f"Cancelled all pending tasks ({len(pending_task_names)} tasks)")
    
    def start_execution(self) -> None:
        """Start task execution in a background thread."""
        if self.running:
            logger.warning("Task execution already running")
            return
            
        logger.debug("Starting task execution")
        
        # Reset events
        self._stop_requested.clear()
        self._pause_requested.clear()
        self._execution_event.set()
        
        # Set running state
        self.running = True
        self.paused = False
        
        # Create execution thread
        self.worker_thread = threading.Thread(
            target=self._execution_loop,
            name="AutomationExecutionThread",
            daemon=True
        )
        
        # Start the thread
        self.worker_thread.start()
        
        # Publish event
        self._publish_event(EventType.AUTOMATION_STARTED, {
            'pending_tasks': len(self.pending_tasks)
        })
    
    def pause_execution(self) -> None:
        """Pause task execution."""
        if not self.running or self.paused:
            logger.warning("Cannot pause: execution not running or already paused")
            return
            
        logger.debug("Pausing task execution")
        
        # Set paused state
        self.paused = True
        
        # Signal pause
        self._pause_requested.set()
        self._execution_event.clear()
        
        # Publish event
        self._publish_event(EventType.AUTOMATION_PAUSED, {
            'pending_tasks': len(self.pending_tasks)
        })
    
    def resume_execution(self) -> None:
        """Resume task execution."""
        if not self.running or not self.paused:
            logger.warning("Cannot resume: execution not running or not paused")
            return
            
        logger.debug("Resuming task execution")
        
        # Clear paused state
        self.paused = False
        
        # Clear pause signal and set execution event
        self._pause_requested.clear()
        self._execution_event.set()
        
        # Publish event
        self._publish_event(EventType.AUTOMATION_RESUMED, {
            'pending_tasks': len(self.pending_tasks)
        })
    
    def stop_execution(self) -> None:
        """Stop task execution."""
        if not self.running:
            logger.warning("Cannot stop: execution not running")
            return
            
        logger.debug("Stopping task execution")
        
        # Signal stop
        self._stop_requested.set()
        self._execution_event.set()  # In case execution is paused
        
        # Wait for thread to finish (with timeout)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
            
        # Reset state
        self.running = False
        self.paused = False
        
        # Publish event
        self._publish_event(EventType.AUTOMATION_STOPPED, {
            'pending_tasks': len(self.pending_tasks)
        })
    
    def is_running(self) -> bool:
        """
        Check if the automation service is running.
        
        Returns:
            True if the service is running, False otherwise
        """
        return self.running
    
    def is_paused(self) -> bool:
        """
        Check if the automation service is paused.
        
        Returns:
            True if the service is paused, False otherwise
        """
        return self.paused
    
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
        if not self.execution_context:
            logger.warning("Execution context not set, task may fail")
            
        logger.debug(f"Executing task synchronously: {task.name}")
        
        # Mark task as running
        task.start()
        
        # Publish start event
        self._publish_task_event(EventType.AUTOMATION_TASK_STARTED, task)
        
        # Execute the task
        success = task.execute(self.execution_context)
        
        # Mark task as completed or failed
        if success:
            task.complete()
            self._publish_task_event(EventType.AUTOMATION_TASK_COMPLETED, task)
        else:
            task.fail(task.error_message or "Task failed")
            self._publish_task_event(EventType.AUTOMATION_TASK_FAILED, task)
            
        return success
    
    def set_execution_context(self, context: Dict[str, Any]) -> None:
        """
        Set the execution context for tasks.
        
        The execution context is a dictionary of services and state
        that will be passed to tasks during execution.
        
        Args:
            context: Execution context dictionary
        """
        self.execution_context = context
        logger.debug(f"Execution context set with keys: {list(context.keys())}")
    
    def add_to_execution_context(self, key: str, value: Any) -> None:
        """
        Add a value to the execution context.
        
        Args:
            key: Key for the value
            value: Value to add
        """
        self.execution_context[key] = value
        logger.debug(f"Added '{key}' to execution context")
    
    def register_task_completion_callback(self, task_name: str, callback: Callable[[Task], None]) -> bool:
        """
        Register a callback for when a task completes.
        
        Args:
            task_name: Name of the task to register for
            callback: Function to call when task completes
            
        Returns:
            True if callback was registered, False if task not found
        """
        task = self.tasks.get(task_name)
        if not task:
            logger.warning(f"Cannot register callback: task '{task_name}' not found")
            return False
            
        task.add_completion_callback(callback)
        return True
    
    def register_task_failure_callback(self, task_name: str, callback: Callable[[Task, str], None]) -> bool:
        """
        Register a callback for when a task fails.
        
        Args:
            task_name: Name of the task to register for
            callback: Function to call when task fails
            
        Returns:
            True if callback was registered, False if task not found
        """
        task = self.tasks.get(task_name)
        if not task:
            logger.warning(f"Cannot register callback: task '{task_name}' not found")
            return False
            
        task.add_failure_callback(callback)
        return True
    
    def _execution_loop(self) -> None:
        """
        Main task execution loop.
        
        This method runs in a separate thread and executes tasks from the queue.
        """
        logger.debug("Task execution loop started")
        
        try:
            while not self._stop_requested.is_set():
                # Wait for execution event
                if not self._execution_event.is_set():
                    logger.debug("Execution paused, waiting to resume")
                    self._execution_event.wait()
                    
                    # Check if stop was requested while waiting
                    if self._stop_requested.is_set():
                        break
                        
                # Check if we need to refill the queue
                self._refill_task_queue()
                
                # Get the next task to execute
                try:
                    # Try to get a task with a short timeout
                    priority, task_name = self._task_queue.get(timeout=0.1)
                except queue.Empty:
                    # No tasks in queue, sleep briefly and check for more tasks
                    time.sleep(0.1)
                    continue
                    
                # Get the task
                with self._task_lock:
                    task = self.tasks.get(task_name)
                    
                    # Skip if task was removed or is no longer pending
                    if not task or task.status != TaskStatus.PENDING:
                        self._task_queue.task_done()
                        continue
                        
                    # Check if task has pending dependencies
                    if not task.is_ready():
                        # Put back in queue with lower priority (to avoid starvation)
                        self._task_queue.put((priority + 10, task_name))
                        self._task_queue.task_done()
                        continue
                        
                    # Remove from pending set
                    if task_name in self.pending_tasks:
                        self.pending_tasks.remove(task_name)
                        
                    # Mark task as running
                    task.start()
                
                # Publish task started event
                self._publish_task_event(EventType.AUTOMATION_TASK_STARTED, task)
                
                try:
                    # Execute the task
                    logger.debug(f"Executing task: {task.name}")
                    success = task.execute(self.execution_context)
                    
                    # Mark task as completed or failed
                    if success:
                        task.complete()
                        logger.debug(f"Task completed successfully: {task.name}")
                        self._publish_task_event(EventType.AUTOMATION_TASK_COMPLETED, task)
                    else:
                        task.fail(task.error_message or "Task failed")
                        logger.debug(f"Task failed: {task.name} - {task.error_message}")
                        self._publish_task_event(EventType.AUTOMATION_TASK_FAILED, task)
                        
                except Exception as e:
                    # Handle exceptions during task execution
                    error_message = f"Error executing task: {str(e)}"
                    logger.error(error_message, exc_info=True)
                    
                    # Mark task as failed
                    task.fail(error_message)
                    self._publish_task_event(EventType.AUTOMATION_TASK_FAILED, task)
                    
                finally:
                    # Mark task as done in queue
                    self._task_queue.task_done()
                    
            logger.debug("Task execution loop stopped")
            
        except Exception as e:
            logger.error(f"Error in task execution loop: {str(e)}", exc_info=True)
            
        finally:
            # Reset running state
            self.running = False
    
    def _refill_task_queue(self) -> None:
        """
        Refill the task queue with pending tasks.
        
        This method is called when the queue is empty or
        when new tasks are added.
        """
        with self._task_lock:
            # Skip if no pending tasks
            if not self.pending_tasks:
                return
                
            # Get all pending tasks
            pending_tasks = [self.tasks[name] for name in self.pending_tasks
                           if name in self.tasks]
            
            # Sort by priority
            pending_tasks.sort(key=lambda t: t.priority.value, reverse=True)
            
            # Add to queue
            for task in pending_tasks:
                priority_value = task.priority.value
                self._task_queue.put((priority_value, task.name))
    
    def _publish_task_event(self, event_type: EventType, task: Task) -> None:
        """
        Publish a task-related event.
        
        Args:
            event_type: Type of event
            task: Task associated with the event
        """
        if not self.event_bus:
            return
            
        # Create event data
        event_data = {
            'task_name': task.name,
            'task_type': task.__class__.__name__,
            'task_status': task.status.name,
            'task_priority': task.priority.name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add additional data based on task status
        if task.status == TaskStatus.COMPLETED:
            event_data['execution_time'] = task.get_execution_time()
            if task.result is not None:
                event_data['result'] = task.result
                
        elif task.status == TaskStatus.FAILED:
            event_data['execution_time'] = task.get_execution_time()
            event_data['error_message'] = task.error_message
            
        # Create and publish event
        event = Event(event_type, event_data)
        self.event_bus.publish(event)
    
    def _publish_event(self, event_type: EventType, event_data: Dict[str, Any]) -> None:
        """
        Publish a service-level event.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        if not self.event_bus:
            return
            
        # Add timestamp
        event_data['timestamp'] = datetime.now().isoformat()
        
        # Create and publish event
        event = Event(event_type, event_data)
        self.event_bus.publish(event) 