"""
Tests for Automation Service

This module contains unit tests for the AutomationService and Task classes,
which provide task scheduling and execution functionality.
"""

import unittest
from unittest.mock import MagicMock, patch
import time
import threading

from scout.core.events.event_bus import EventBus
from scout.core.automation.automation_service import AutomationService
from scout.core.automation.task import Task, TaskStatus, TaskPriority


class TestTask(Task):
    """Test implementation of Task for testing."""
    
    def __init__(self, name, priority=TaskPriority.NORMAL, should_succeed=True):
        super().__init__(name, priority)
        self.should_succeed = should_succeed
        self.executed = False
    
    def execute(self, context):
        self.executed = True
        if not self.should_succeed:
            self.error_message = "Test task configured to fail"
            return False
        return True


class TestAutomationService(unittest.TestCase):
    """
    Tests for the AutomationService class.
    """
    
    def setUp(self):
        """Set up test fixture."""
        # Create mock dependencies
        self.event_bus = MagicMock(spec=EventBus)
        
        # Create service with its own instance (bypassing singleton)
        with patch('scout.core.automation.automation_service.Singleton'):
            self.service = AutomationService(self.event_bus)
        
        # Create execution context
        self.service.set_execution_context({'test_key': 'test_value'})
    
    def test_add_and_get_task(self):
        """Test adding and retrieving tasks."""
        # Create test tasks
        task1 = TestTask("task1", TaskPriority.NORMAL)
        task2 = TestTask("task2", TaskPriority.HIGH)
        
        # Add tasks
        self.service.add_task(task1)
        self.service.add_task(task2)
        
        # Verify tasks were added
        self.assertEqual(len(self.service.tasks), 2)
        self.assertEqual(len(self.service.pending_tasks), 2)
        
        # Get tasks
        retrieved_task1 = self.service.get_task("task1")
        retrieved_task2 = self.service.get_task("task2")
        
        # Verify retrieval
        self.assertEqual(retrieved_task1, task1)
        self.assertEqual(retrieved_task2, task2)
        
        # Get all tasks
        all_tasks = self.service.get_tasks()
        self.assertEqual(len(all_tasks), 2)
        
        # Get pending tasks
        pending_tasks = self.service.get_tasks(TaskStatus.PENDING)
        self.assertEqual(len(pending_tasks), 2)
    
    def test_cancel_task(self):
        """Test cancelling a task."""
        # Create and add test task
        task = TestTask("cancel_test")
        self.service.add_task(task)
        
        # Verify task was added
        self.assertIn("cancel_test", self.service.pending_tasks)
        
        # Cancel task
        result = self.service.cancel_task("cancel_test")
        
        # Verify cancellation
        self.assertTrue(result)
        self.assertNotIn("cancel_test", self.service.pending_tasks)
        self.assertEqual(task.status, TaskStatus.CANCELLED)
    
    def test_cancel_nonexistent_task(self):
        """Test cancelling a task that doesn't exist."""
        # Try to cancel a non-existent task
        result = self.service.cancel_task("nonexistent")
        
        # Verify cancellation failed
        self.assertFalse(result)
    
    def test_cancel_all_tasks(self):
        """Test cancelling all tasks."""
        # Create and add test tasks
        for i in range(5):
            self.service.add_task(TestTask(f"task{i}"))
            
        # Verify tasks were added
        self.assertEqual(len(self.service.pending_tasks), 5)
        
        # Cancel all tasks
        self.service.cancel_all_tasks()
        
        # Verify all tasks were cancelled
        self.assertEqual(len(self.service.pending_tasks), 0)
        for task in self.service.tasks.values():
            self.assertEqual(task.status, TaskStatus.CANCELLED)
    
    def test_execute_task_synchronously_success(self):
        """Test executing a task synchronously that succeeds."""
        # Create test task
        task = TestTask("sync_success", should_succeed=True)
        
        # Execute task
        result = self.service.execute_task_synchronously(task)
        
        # Verify execution
        self.assertTrue(result)
        self.assertTrue(task.executed)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
    
    def test_execute_task_synchronously_failure(self):
        """Test executing a task synchronously that fails."""
        # Create test task
        task = TestTask("sync_failure", should_succeed=False)
        
        # Execute task
        result = self.service.execute_task_synchronously(task)
        
        # Verify execution
        self.assertFalse(result)
        self.assertTrue(task.executed)
        self.assertEqual(task.status, TaskStatus.FAILED)
    
    def test_task_dependencies(self):
        """Test task dependencies."""
        # Create tasks
        task1 = TestTask("dependency1")
        task2 = TestTask("dependency2")
        task3 = TestTask("dependent")
        
        # Set dependencies
        task3.add_dependency(task1)
        task3.add_dependency(task2)
        
        # Verify dependency status
        self.assertFalse(task3.is_ready())
        
        # Mark dependencies as complete
        task1.status = TaskStatus.COMPLETED
        self.assertFalse(task3.is_ready())
        
        task2.status = TaskStatus.COMPLETED
        self.assertTrue(task3.is_ready())
    
    def test_execution_thread(self):
        """Test task execution in a background thread."""
        # Create test tasks
        tasks = [TestTask(f"thread_task{i}") for i in range(3)]
        
        # Initialize execution state
        for task in tasks:
            self.service.add_task(task)
        
        # Start execution
        self.service.start_execution()
        
        # Wait for execution to complete (with timeout)
        for _ in range(10):  # Try for at most 1 second
            if all(task.status == TaskStatus.COMPLETED for task in tasks):
                break
            time.sleep(0.1)
            
        # Stop execution
        self.service.stop_execution()
        
        # Verify tasks were executed
        for task in tasks:
            self.assertTrue(task.executed)
            self.assertEqual(task.status, TaskStatus.COMPLETED)
    
    def test_pause_resume(self):
        """Test pausing and resuming execution."""
        # Add a task
        task = TestTask("pause_test")
        self.service.add_task(task)
        
        # Start execution
        self.service.start_execution()
        
        # Wait for task to complete (with timeout)
        for _ in range(10):  # Try for at most 1 second
            if task.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.1)
        
        # Add another task
        task2 = TestTask("resume_test")
        self.service.add_task(task2)
        
        # Pause execution
        self.service.pause_execution()
        self.assertTrue(self.service.is_paused())
        
        # Task should remain pending during pause
        time.sleep(0.2)
        self.assertEqual(task2.status, TaskStatus.PENDING)
        
        # Resume execution
        self.service.resume_execution()
        self.assertFalse(self.service.is_paused())
        
        # Wait for second task to complete (with timeout)
        for _ in range(10):  # Try for at most 1 second
            if task2.status == TaskStatus.COMPLETED:
                break
            time.sleep(0.1)
            
        # Stop execution
        self.service.stop_execution()
        
        # Verify second task was executed
        self.assertTrue(task2.executed)
        self.assertEqual(task2.status, TaskStatus.COMPLETED)
    
    def test_task_callbacks(self):
        """Test task completion and failure callbacks."""
        # Create mock callbacks
        completion_callback = MagicMock()
        failure_callback = MagicMock()
        
        # Create tasks
        success_task = TestTask("callback_success", should_succeed=True)
        failure_task = TestTask("callback_failure", should_succeed=False)
        
        # Add tasks
        self.service.add_task(success_task)
        self.service.add_task(failure_task)
        
        # Register callbacks
        self.service.register_task_completion_callback("callback_success", completion_callback)
        self.service.register_task_failure_callback("callback_failure", failure_callback)
        
        # Start execution
        self.service.start_execution()
        
        # Wait for tasks to complete (with timeout)
        for _ in range(10):  # Try for at most 1 second
            if (success_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and
                failure_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]):
                break
            time.sleep(0.1)
            
        # Stop execution
        self.service.stop_execution()
        
        # Wait for callbacks to be called
        time.sleep(0.1)
        
        # Verify callbacks were called
        completion_callback.assert_called_once_with(success_task)
        failure_callback.assert_called_once()  # Args include the error message, which may vary


if __name__ == '__main__':
    unittest.main() 