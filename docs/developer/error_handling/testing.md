# Testing the Error Reporting and Recovery System

This document provides guidance on how to test the Error Reporting and Recovery System to ensure it functions as expected in various error scenarios.

## Table of Contents

1. [Testing Approach](#testing-approach)
2. [Unit Testing Components](#unit-testing-components)
3. [Integration Testing](#integration-testing)
4. [UI Error Dialog Testing](#ui-error-dialog-testing)
5. [Recovery Testing](#recovery-testing)
6. [Stress Testing](#stress-testing)
7. [Test Error Injection](#test-error-injection)
8. [Testing Checklist](#testing-checklist)

## Testing Approach

The error handling system should be tested at multiple levels to ensure it works correctly:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **UI Tests**: Test error dialogs and user interactions
4. **Recovery Tests**: Test automatic recovery mechanisms
5. **Stress Tests**: Test under high load and failure conditions
6. **Manual Tests**: Test real-world error scenarios

## Unit Testing Components

### Testing the Logger

```python
# tests/core/error_reporting/test_logger.py

import unittest
import os
import tempfile
import logging
from scout.core.error_reporting import ScoutLogger


class TestScoutLogger(unittest.TestCase):
    """Test the ScoutLogger class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.logger = ScoutLogger(log_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove log files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_log_creation(self):
        """Test that log file is created."""
        # Log file should exist
        self.assertTrue(os.path.exists(self.logger.log_file_path))
    
    def test_logging_levels(self):
        """Test logging at different levels."""
        # Log messages at different levels
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        self.logger.critical("Critical message")
        
        # Read log file and check contents
        with open(self.logger.log_file_path, 'r') as f:
            log_content = f.read()
        
        # All messages should be in the log file
        self.assertIn("Debug message", log_content)
        self.assertIn("Info message", log_content)
        self.assertIn("Warning message", log_content)
        self.assertIn("Error message", log_content)
        self.assertIn("Critical message", log_content)
    
    def test_custom_log_level(self):
        """Test setting a custom log level."""
        # Create logger with INFO level (no DEBUG)
        custom_logger = ScoutLogger(log_dir=self.temp_dir, log_level=logging.INFO)
        
        # Log messages
        custom_logger.debug("Debug message")
        custom_logger.info("Info message")
        
        # Read log file and check contents
        with open(custom_logger.log_file_path, 'r') as f:
            log_content = f.read()
        
        # Debug message should not be in the log file
        self.assertNotIn("Debug message", log_content)
        # Info message should be in the log file
        self.assertIn("Info message", log_content)
    
    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        # Remove temp directory
        os.rmdir(self.temp_dir)
        
        # Create logger, which should recreate the directory
        new_logger = ScoutLogger(log_dir=self.temp_dir)
        
        # Directory should exist
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Log file should exist
        self.assertTrue(os.path.exists(new_logger.log_file_path))
```

### Testing the Error Handler

```python
# tests/core/error_reporting/test_error_handler.py

import unittest
from unittest.mock import MagicMock, patch
from scout.core.error_reporting import (
    ErrorHandler, ErrorSeverity, ScoutLogger, RecoverySystem, ErrorReporter
)


class TestErrorHandler(unittest.TestCase):
    """Test the ErrorHandler class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mocks
        self.mock_logger = MagicMock(spec=ScoutLogger)
        self.mock_recovery = MagicMock(spec=RecoverySystem)
        self.mock_reporter = MagicMock(spec=ErrorReporter)
        
        # Create error handler with mocks
        self.error_handler = ErrorHandler(
            self.mock_logger,
            self.mock_recovery,
            self.mock_reporter
        )
    
    def test_handle_exception_logging(self):
        """Test that exceptions are logged correctly."""
        # Create an exception
        test_exception = ValueError("Test error")
        
        # Handle exception with different severity levels
        self.error_handler.handle_exception(test_exception, ErrorSeverity.INFO)
        self.error_handler.handle_exception(test_exception, ErrorSeverity.WARNING)
        self.error_handler.handle_exception(test_exception, ErrorSeverity.SEVERE)
        self.error_handler.handle_exception(test_exception, ErrorSeverity.CRITICAL)
        
        # Check that logger was called correctly
        self.mock_logger.info.assert_called()
        self.mock_logger.warning.assert_called()
        self.mock_logger.error.assert_called()
        self.mock_logger.critical.assert_called()
    
    def test_handle_exception_recovery(self):
        """Test that recovery is attempted for non-critical errors."""
        # Create an exception
        test_exception = ValueError("Test error")
        
        # Configure recovery system to succeed
        self.mock_recovery.attempt_recovery.return_value = True
        
        # Handle exception
        result = self.error_handler.handle_exception(
            test_exception, ErrorSeverity.SEVERE, {"test_context": True}
        )
        
        # Check that recovery was attempted
        self.mock_recovery.attempt_recovery.assert_called_once_with(
            test_exception, ErrorSeverity.SEVERE, {"test_context": True}
        )
        
        # Check that result indicates successful recovery
        self.assertTrue(result)
    
    def test_handle_exception_no_recovery_critical(self):
        """Test that recovery is not attempted for critical errors."""
        # Create an exception
        test_exception = ValueError("Test error")
        
        # Handle critical exception
        self.error_handler.handle_exception(
            test_exception, ErrorSeverity.CRITICAL
        )
        
        # Check that recovery was not attempted
        self.mock_recovery.attempt_recovery.assert_not_called()
    
    def test_custom_exception_handler(self):
        """Test registering and using custom exception handlers."""
        # Create an exception
        test_exception = ValueError("Test error")
        
        # Create a custom handler
        custom_handler = MagicMock(return_value=True)
        
        # Register custom handler
        self.error_handler.register_handler(ValueError, custom_handler)
        
        # Handle exception
        result = self.error_handler.handle_exception(
            test_exception, ErrorSeverity.SEVERE
        )
        
        # Check that custom handler was called
        custom_handler.assert_called_once()
        
        # Check that result indicates successful handling
        self.assertTrue(result)
    
    def test_show_error_dialog(self):
        """Test that error dialog is shown for severe and critical errors."""
        # Create an exception
        test_exception = ValueError("Test error")
        
        # Handle exception with show_error_dialog=True
        self.error_handler.handle_exception(
            test_exception, ErrorSeverity.SEVERE, {"show_error_dialog": True}
        )
        
        # Check that error reporter's show_error_dialog was called
        self.mock_reporter.show_error_dialog.assert_called_once()
```

### Testing the Recovery System

```python
# tests/core/error_reporting/test_recovery.py

import unittest
from unittest.mock import MagicMock, patch
from scout.core.error_reporting import (
    RecoverySystem, RecoveryStrategy, ScoutLogger, ErrorSeverity
)


class TestRecoveryStrategy(RecoveryStrategy):
    """Test implementation of RecoveryStrategy."""
    
    def __init__(self, can_handle_result=True, execute_result=True):
        self.can_handle_result = can_handle_result
        self.execute_result = execute_result
        self.can_handle_called = False
        self.execute_called = False
    
    def can_handle(self, exception, context):
        """Determine if this strategy can handle the exception."""
        self.can_handle_called = True
        self.last_exception = exception
        self.last_context = context
        return self.can_handle_result
    
    def execute(self, exception, context):
        """Execute the recovery strategy."""
        self.execute_called = True
        self.last_exception = exception
        self.last_context = context
        return self.execute_result


class TestRecoverySystem(unittest.TestCase):
    """Test the RecoverySystem class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock logger
        self.mock_logger = MagicMock(spec=ScoutLogger)
        
        # Create recovery system with mock logger
        self.recovery = RecoverySystem(self.mock_logger)
        
        # Clear any existing strategies
        self.recovery.strategies = []
    
    def test_register_strategy(self):
        """Test registering a recovery strategy."""
        # Create test strategy
        test_strategy = TestRecoveryStrategy()
        
        # Register strategy
        self.recovery.register_strategy(test_strategy)
        
        # Check that strategy was added to list
        self.assertIn(test_strategy, self.recovery.strategies)
    
    def test_attempt_recovery_success(self):
        """Test successful recovery attempt."""
        # Create test strategy that will succeed
        test_strategy = TestRecoveryStrategy(can_handle_result=True, execute_result=True)
        
        # Register strategy
        self.recovery.register_strategy(test_strategy)
        
        # Attempt recovery
        test_exception = ValueError("Test error")
        test_context = {"test": True}
        result = self.recovery.attempt_recovery(
            test_exception, ErrorSeverity.WARNING, test_context
        )
        
        # Check that strategy methods were called
        self.assertTrue(test_strategy.can_handle_called)
        self.assertTrue(test_strategy.execute_called)
        
        # Check that result indicates successful recovery
        self.assertTrue(result)
    
    def test_attempt_recovery_cannot_handle(self):
        """Test recovery attempt with strategy that cannot handle the exception."""
        # Create test strategy that cannot handle
        test_strategy = TestRecoveryStrategy(can_handle_result=False)
        
        # Register strategy
        self.recovery.register_strategy(test_strategy)
        
        # Attempt recovery
        test_exception = ValueError("Test error")
        test_context = {"test": True}
        result = self.recovery.attempt_recovery(
            test_exception, ErrorSeverity.WARNING, test_context
        )
        
        # Check that can_handle was called but execute was not
        self.assertTrue(test_strategy.can_handle_called)
        self.assertFalse(test_strategy.execute_called)
        
        # Check that result indicates failed recovery
        self.assertFalse(result)
    
    def test_attempt_recovery_execution_failed(self):
        """Test recovery attempt with strategy that fails during execution."""
        # Create test strategy that will fail during execution
        test_strategy = TestRecoveryStrategy(can_handle_result=True, execute_result=False)
        
        # Register strategy
        self.recovery.register_strategy(test_strategy)
        
        # Attempt recovery
        test_exception = ValueError("Test error")
        test_context = {"test": True}
        result = self.recovery.attempt_recovery(
            test_exception, ErrorSeverity.WARNING, test_context
        )
        
        # Check that both methods were called
        self.assertTrue(test_strategy.can_handle_called)
        self.assertTrue(test_strategy.execute_called)
        
        # Check that result indicates failed recovery
        self.assertFalse(result)
    
    def test_attempt_recovery_multiple_strategies(self):
        """Test recovery attempt with multiple strategies."""
        # Create strategies, first fails, second succeeds
        failing_strategy = TestRecoveryStrategy(can_handle_result=True, execute_result=False)
        succeeding_strategy = TestRecoveryStrategy(can_handle_result=True, execute_result=True)
        
        # Register strategies
        self.recovery.register_strategy(failing_strategy)
        self.recovery.register_strategy(succeeding_strategy)
        
        # Attempt recovery
        test_exception = ValueError("Test error")
        test_context = {"test": True}
        result = self.recovery.attempt_recovery(
            test_exception, ErrorSeverity.WARNING, test_context
        )
        
        # Check that both strategies' methods were called
        self.assertTrue(failing_strategy.can_handle_called)
        self.assertTrue(failing_strategy.execute_called)
        self.assertTrue(succeeding_strategy.can_handle_called)
        self.assertTrue(succeeding_strategy.execute_called)
        
        # Check that result indicates successful recovery (from second strategy)
        self.assertTrue(result)
    
    def test_attempt_recovery_exception_in_strategy(self):
        """Test recovery attempt when strategy raises an exception."""
        # Create a strategy that raises an exception
        class ExceptionThrowingStrategy(TestRecoveryStrategy):
            def execute(self, exception, context):
                self.execute_called = True
                raise RuntimeError("Strategy failed")
        
        test_strategy = ExceptionThrowingStrategy(can_handle_result=True)
        
        # Register strategy
        self.recovery.register_strategy(test_strategy)
        
        # Attempt recovery
        test_exception = ValueError("Test error")
        test_context = {"test": True}
        result = self.recovery.attempt_recovery(
            test_exception, ErrorSeverity.WARNING, test_context
        )
        
        # Check that both methods were called
        self.assertTrue(test_strategy.can_handle_called)
        self.assertTrue(test_strategy.execute_called)
        
        # Check that result indicates failed recovery
        self.assertFalse(result)
        
        # Check that logger was called with warning
        self.mock_logger.warning.assert_called()
```

## Integration Testing

Integration tests ensure that the error handling components work together correctly.

```python
# tests/integration/test_error_handling.py

import unittest
import tempfile
import os
import shutil
from scout.core.error_reporting import (
    setup_error_handling, ErrorSeverity, RecoveryStrategy
)


class TestRecoveryIntegration(RecoveryStrategy):
    """Test recovery strategy for integration testing."""
    
    def __init__(self, test_case):
        self.test_case = test_case
        self.can_handle_called = False
        self.execute_called = False
        self.recovery_context = None
    
    def can_handle(self, exception, context):
        """Check if this strategy can handle the exception."""
        self.can_handle_called = True
        if isinstance(exception, ValueError) and context.get("test_id") == "integration":
            return True
        return False
    
    def execute(self, exception, context):
        """Execute the recovery strategy."""
        self.execute_called = True
        self.recovery_context = context
        return True


class ErrorHandlingIntegrationTest(unittest.TestCase):
    """Integration tests for the error handling system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory for logs
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize error handling system
        self.logger, self.error_handler, self.recovery_system, self.error_reporter = setup_error_handling(
            log_dir=self.temp_dir
        )
        
        # Create and register test recovery strategy
        self.test_strategy = TestRecoveryIntegration(self)
        self.recovery_system.register_strategy(self.test_strategy)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_error_handling_and_recovery(self):
        """Test error handling with recovery."""
        # Create test exception
        test_exception = ValueError("Integration test error")
        
        # Handle exception with test context
        result = self.error_handler.handle_exception(
            test_exception,
            ErrorSeverity.WARNING,
            {"test_id": "integration", "extra_data": "test"}
        )
        
        # Check that recovery was attempted
        self.assertTrue(self.test_strategy.can_handle_called)
        self.assertTrue(self.test_strategy.execute_called)
        
        # Check context was passed correctly
        self.assertEqual(self.test_strategy.recovery_context["test_id"], "integration")
        self.assertEqual(self.test_strategy.recovery_context["extra_data"], "test")
        
        # Check that result indicates successful recovery
        self.assertTrue(result)
        
        # Check that error was logged
        log_path = self.logger.get_log_file_path()
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Integration test error", log_content)
        self.assertIn("Successfully recovered", log_content)
    
    def test_error_reporting(self):
        """Test error reporting functionality."""
        # Create test exception
        test_exception = RuntimeError("Integration test error for reporting")
        
        # Create temp directory for reports
        reports_dir = os.path.join(self.temp_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Collect and save error report
        report = self.error_reporter.collect_error_report(
            test_exception,
            {"test_id": "integration_report"},
            user_description="Test user description"
        )
        
        report_path = self.error_reporter.save_error_report(report)
        
        # Check that report file exists
        self.assertTrue(os.path.exists(report_path))
        
        # Check report contents
        import json
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        self.assertEqual(report_data["error"]["type"], "RuntimeError")
        self.assertEqual(report_data["error"]["message"], "Integration test error for reporting")
        self.assertEqual(report_data["context"]["test_id"], "integration_report")
        self.assertEqual(report_data["user_description"], "Test user description")
```

## UI Error Dialog Testing

Testing the error dialog requires UI testing, which can be done using PyQt's test framework.

```python
# tests/ui/test_error_dialog.py

import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
import sys
import os
import tempfile

from scout.core.error_reporting import (
    ErrorDialog, ErrorSeverity, ErrorReporter, ScoutLogger
)


# Create QApplication instance for UI tests
app = QApplication(sys.argv)


class TestErrorDialog(unittest.TestCase):
    """Test the error dialog UI."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory for logs and reports
        self.temp_dir = tempfile.mkdtemp()
        
        # Create logger and error reporter
        self.logger = ScoutLogger(log_dir=self.temp_dir)
        self.error_reporter = ErrorReporter(self.logger)
        
        # Create test exception
        self.test_exception = ValueError("Test error for dialog")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_error_dialog_creation(self):
        """Test creating error dialog."""
        # Create dialog
        dialog = ErrorDialog(
            exception=self.test_exception,
            error_message="Test error message",
            error_reporter=self.error_reporter,
            severity=ErrorSeverity.SEVERE
        )
        
        # Check that dialog was created correctly
        self.assertEqual(dialog.windowTitle(), "Error")
        self.assertEqual(dialog.error_message, "Test error message")
    
    def test_critical_error_dialog(self):
        """Test critical error dialog."""
        # Create dialog with critical severity
        dialog = ErrorDialog(
            exception=self.test_exception,
            error_message="Critical error message",
            error_reporter=self.error_reporter,
            severity=ErrorSeverity.CRITICAL
        )
        
        # Check that dialog has correct title
        self.assertEqual(dialog.windowTitle(), "Critical Error")
    
    def test_error_dialog_report(self):
        """Test error reporting from dialog."""
        # Create dialog
        dialog = ErrorDialog(
            exception=self.test_exception,
            error_message="Error message",
            error_reporter=self.error_reporter,
            severity=ErrorSeverity.SEVERE
        )
        
        # Set user description
        user_description = "This is a test description"
        dialog.description_edit.setPlainText(user_description)
        
        # Simulate clicking report button
        # In a real test, you would use QTest.mouseClick
        # Here we directly call the handler
        dialog._on_report_clicked()
        
        # Check that report file was created
        reports_dir = os.path.join(os.path.dirname(self.logger.get_log_file_path()), "reports")
        self.assertTrue(os.path.exists(reports_dir))
        
        # Find the report file (should be only file in directory)
        report_files = [f for f in os.listdir(reports_dir) if os.path.isfile(os.path.join(reports_dir, f))]
        self.assertEqual(len(report_files), 1)
        
        # Check report contents
        import json
        with open(os.path.join(reports_dir, report_files[0]), 'r') as f:
            report_data = json.load(f)
        
        self.assertEqual(report_data["error"]["type"], "ValueError")
        self.assertEqual(report_data["error"]["message"], "Test error for dialog")
        self.assertEqual(report_data["user_description"], user_description)
```

## Recovery Testing

Test the recovery system with real recovery strategies:

```python
# tests/recovery/test_retry_strategy.py

import unittest
from unittest.mock import MagicMock
from scout.core.error_reporting import RetryStrategy


class TestRetryStrategy(unittest.TestCase):
    """Test the RetryStrategy recovery strategy."""
    
    def test_can_handle(self):
        """Test can_handle method."""
        # Create retry strategy
        strategy = RetryStrategy()
        
        # Test with valid context
        self.assertTrue(strategy.can_handle(
            Exception("Test"),
            {"retry_function": lambda: None}
        ))
        
        # Test with invalid context
        self.assertFalse(strategy.can_handle(
            Exception("Test"),
            {}
        ))
        self.assertFalse(strategy.can_handle(
            Exception("Test"),
            None
        ))
    
    def test_execute_success(self):
        """Test execute method with successful retry."""
        # Create retry strategy
        strategy = RetryStrategy(max_retries=3)
        
        # Create mock function that succeeds on second try
        mock_function = MagicMock(side_effect=[Exception("First try"), "Success"])
        
        # Execute strategy
        result = strategy.execute(
            Exception("Test"),
            {"retry_function": mock_function}
        )
        
        # Check that result indicates success
        self.assertTrue(result)
        
        # Check that function was called twice
        self.assertEqual(mock_function.call_count, 2)
    
    def test_execute_failure(self):
        """Test execute method with failed retry."""
        # Create retry strategy
        strategy = RetryStrategy(max_retries=3)
        
        # Create mock function that always fails
        mock_function = MagicMock(side_effect=Exception("Always fails"))
        
        # Execute strategy
        result = strategy.execute(
            Exception("Test"),
            {"retry_function": mock_function}
        )
        
        # Check that result indicates failure
        self.assertFalse(result)
        
        # Check that function was called three times (max retries)
        self.assertEqual(mock_function.call_count, 3)
    
    def test_execute_with_args(self):
        """Test execute method with arguments for retry function."""
        # Create retry strategy
        strategy = RetryStrategy()
        
        # Create mock function
        mock_function = MagicMock(return_value="Success")
        
        # Execute strategy with args and kwargs
        result = strategy.execute(
            Exception("Test"),
            {
                "retry_function": mock_function,
                "retry_args": [1, 2],
                "retry_kwargs": {"a": "b"}
            }
        )
        
        # Check that result indicates success
        self.assertTrue(result)
        
        # Check that function was called with correct args
        mock_function.assert_called_once_with(1, 2, a="b")
```

## Stress Testing

Stress testing simulates high-load error conditions:

```python
# tests/stress/test_error_handler_stress.py

import unittest
import threading
import random
import time
from scout.core.error_reporting import (
    setup_error_handling, ErrorSeverity
)


class ErrorHandlerStressTest(unittest.TestCase):
    """Stress test for the error handler."""
    
    def setUp(self):
        """Set up test environment."""
        # Initialize error handling system
        self.logger, self.error_handler, self.recovery_system, self.error_reporter = setup_error_handling()
    
    def test_concurrent_error_handling(self):
        """Test handling multiple errors concurrently."""
        # Number of concurrent errors
        num_errors = 100
        
        # Track results
        results = [None] * num_errors
        errors = [None] * num_errors
        
        # Create thread worker function
        def worker(index):
            try:
                # Generate random error
                error_type = random.choice([
                    ValueError, KeyError, RuntimeError, TypeError, IndexError
                ])
                error_msg = f"Stress test error {index}"
                exception = error_type(error_msg)
                
                # Random severity
                severity = random.choice([
                    ErrorSeverity.INFO,
                    ErrorSeverity.WARNING,
                    ErrorSeverity.SEVERE
                ])
                
                # Handle error
                results[index] = self.error_handler.handle_exception(
                    exception,
                    severity,
                    {"stress_test": True, "index": index}
                )
            except Exception as e:
                # Record any unexpected errors
                errors[index] = e
        
        # Create and start threads
        threads = []
        for i in range(num_errors):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        for i in range(num_errors):
            # No thread should have raised an unhandled exception
            self.assertIsNone(errors[i], f"Error in thread {i}: {errors[i]}")
            
            # Result should be False since we didn't register recovery strategies
            self.assertFalse(results[i])
        
        # Check log file for all errors
        log_path = self.logger.get_log_file_path()
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        # Log should contain entries for all errors
        for i in range(num_errors):
            self.assertIn(f"Stress test error {i}", log_content)
```

## Test Error Injection

Create tools for injecting errors for testing:

```python
# scout/core/testing/error_injection.py

"""
Error injection utilities for testing error handling.

This module provides functions for injecting errors into the application
to test error handling in a controlled way.
"""

import functools
import random
import time
from typing import Type, Callable, Any, Optional


def inject_error(
    exception_type: Type[Exception],
    message: str = "Injected error",
    probability: float = 1.0
) -> Callable:
    """
    Decorator to inject an error into a function.
    
    Args:
        exception_type: Type of exception to raise
        message: Error message
        probability: Probability of raising error (0.0-1.0)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if random.random() < probability:
                raise exception_type(message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def delayed_error(
    exception_type: Type[Exception],
    message: str = "Delayed error",
    min_delay: float = 0.1,
    max_delay: float = 1.0
) -> Callable:
    """
    Decorator to inject a delayed error.
    
    Args:
        exception_type: Type of exception to raise
        message: Error message
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            delay = random.uniform(min_delay, max_delay)
            time.sleep(delay)
            raise exception_type(f"{message} after {delay:.2f}s")
        return wrapper
    return decorator


def network_error(probability: float = 0.5) -> Callable:
    """
    Decorator to simulate network errors.
    
    Args:
        probability: Probability of raising error (0.0-1.0)
        
    Returns:
        Decorated function
    """
    from urllib.error import URLError
    return inject_error(
        URLError,
        message="Simulated network error",
        probability=probability
    )


def resource_error(resource_name: str, probability: float = 0.5) -> Callable:
    """
    Decorator to simulate resource errors.
    
    Args:
        resource_name: Name of the resource
        probability: Probability of raising error (0.0-1.0)
        
    Returns:
        Decorated function
    """
    return inject_error(
        IOError,
        message=f"Failed to access resource: {resource_name}",
        probability=probability
    )


class ErrorInjector:
    """
    Class for injecting errors during runtime.
    
    This class allows enabling and disabling error injection
    during runtime for testing.
    """
    
    def __init__(self):
        """Initialize the error injector."""
        self.enabled = False
        self.injection_points = {}
    
    def register_injection_point(
        self,
        name: str,
        exception_type: Type[Exception],
        message: str = "Injected error",
        probability: float = 1.0
    ) -> None:
        """
        Register an error injection point.
        
        Args:
            name: Unique name for the injection point
            exception_type: Type of exception to raise
            message: Error message
            probability: Probability of raising error (0.0-1.0)
        """
        self.injection_points[name] = {
            "exception_type": exception_type,
            "message": message,
            "probability": probability,
            "count": 0
        }
    
    def maybe_inject_error(self, name: str) -> None:
        """
        Possibly inject an error at a registered injection point.
        
        Args:
            name: Name of the injection point
        
        Raises:
            Exception: If enabled and probability check passes
        """
        if not self.enabled:
            return
            
        if name not in self.injection_points:
            return
            
        point = self.injection_points[name]
        if random.random() < point["probability"]:
            point["count"] += 1
            raise point["exception_type"](
                f"{point['message']} (injection point: {name}, count: {point['count']})"
            )
    
    def enable(self) -> None:
        """Enable error injection."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable error injection."""
        self.enabled = False
    
    def reset_counts(self) -> None:
        """Reset injection counts."""
        for point in self.injection_points.values():
            point["count"] = 0


# Create global injector instance
error_injector = ErrorInjector()
```

Example of using the error injection tool:

```python
# Example usage

from scout.core.testing.error_injection import inject_error, error_injector

# Using decorator
@inject_error(ValueError, "Database query failed", probability=0.1)
def query_database(query):
    # Normal implementation
    return ["result1", "result2"]

# Using error injector
def save_file(path, data):
    # Register injection point if not already registered
    if "file_save" not in error_injector.injection_points:
        error_injector.register_injection_point(
            "file_save",
            IOError,
            "Failed to save file",
            probability=0.2
        )
    
    # Maybe inject error
    error_injector.maybe_inject_error("file_save")
    
    # Normal implementation
    with open(path, "w") as f:
        f.write(data)

# Enable injector for tests
error_injector.enable()

# Disable injector in production
if not is_testing:
    error_injector.disable()
```

## Testing Checklist

Use this checklist when testing the error handling system:

1. **Unit Tests**
   - [ ] Logger component tests
   - [ ] Error handler component tests
   - [ ] Recovery system component tests
   - [ ] Error reporter component tests

2. **Integration Tests**
   - [ ] End-to-end error handling tests
   - [ ] Exception handling and recovery tests
   - [ ] Error reporting tests

3. **UI Tests**
   - [ ] Error dialog display tests
   - [ ] User interaction with error dialog tests
   - [ ] Status bar error display tests

4. **Recovery Tests**
   - [ ] Basic recovery strategy tests
   - [ ] Custom recovery strategy tests
   - [ ] Recovery from different error types

5. **Stress Tests**
   - [ ] Concurrent error handling tests
   - [ ] High-frequency error tests
   - [ ] Resource exhaustion tests

6. **Manual Tests**
   - [ ] Verify error message clarity
   - [ ] Confirm recovery behavior in real scenarios
   - [ ] Test error reporting in production-like environment 