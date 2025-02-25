# Error Reporting and Recovery System Implementation

This document provides detailed implementation examples for the Scout Error Reporting and Recovery System, including code samples for each component.

## Table of Contents

1. [Core Components Implementation](#core-components-implementation)
   - [Logger Implementation](#logger-implementation)
   - [Error Handler Implementation](#error-handler-implementation)
   - [Recovery System Implementation](#recovery-system-implementation)
   - [Error Reporter Implementation](#error-reporter-implementation)
   - [Error Dialog Implementation](#error-dialog-implementation)

2. [File Organization](#file-organization)

3. [Example Usage Scenarios](#example-usage-scenarios)
   - [Handling Network Errors](#handling-network-errors)
   - [Handling File Access Errors](#handling-file-access-errors)
   - [Handling UI Component Errors](#handling-ui-component-errors)

## Core Components Implementation

### Logger Implementation

The Logger component is responsible for recording events and errors throughout the application.

#### ScoutLogger Class

```python
# scout/core/error_reporting/logger.py

import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler


class ScoutLogger:
    """
    Centralized logging system for the Scout application.
    
    This class provides methods for logging messages at different levels
    and directs log output to appropriate destinations including files
    and the console.
    """
    
    def __init__(self, log_dir: Optional[str] = None, log_level: int = logging.DEBUG):
        """
        Initialize the logger with appropriate handlers.
        
        Args:
            log_dir: Directory to store log files. If None, uses default location.
            log_level: Minimum log level to record (DEBUG, INFO, etc.)
        """
        # Get logger
        self.logger = logging.getLogger("scout")
        self.logger.setLevel(log_level)
        
        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Set up log directory
        if log_dir is None:
            log_dir = os.path.join(str(Path.home()), "scout", "logs")
        
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        
        # Get current date for log file name
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.log_file_path = os.path.join(log_dir, f"scout_{current_date}.log")
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Less verbose for console
        console_formatter = logging.Formatter(
            "%(levelname)s: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initial log entry
        self.info(f"Logging started. Log file: {self.log_file_path}")
    
    def debug(self, message: str) -> None:
        """
        Log a debug message.
        
        Args:
            message: Message to log
        """
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """
        Log an info message.
        
        Args:
            message: Message to log
        """
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            message: Message to log
        """
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None) -> None:
        """
        Log an error message with optional exception info.
        
        Args:
            message: Message to log
            exc_info: Exception information to include
        """
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None) -> None:
        """
        Log a critical error message with optional exception info.
        
        Args:
            message: Message to log
            exc_info: Exception information to include
        """
        self.logger.critical(message, exc_info=exc_info)
    
    def get_log_file_path(self) -> str:
        """
        Get the path to the current log file.
        
        Returns:
            Path to the log file
        """
        return self.log_file_path
```

### Error Handler Implementation

The Error Handler is the central component that manages error detection, classification, and processing.

#### ErrorSeverity Enum

```python
# scout/core/error_reporting/severity.py

from enum import Enum, auto

class ErrorSeverity(Enum):
    """
    Enumeration of error severity levels.
    
    Severity levels determine how errors are handled:
    - CRITICAL: Application cannot continue running
    - SEVERE: Major feature is unusable, but application can continue
    - WARNING: Non-critical issue that may affect functionality
    - INFO: Informational message that doesn't indicate an error
    """
    CRITICAL = auto()
    SEVERE = auto()
    WARNING = auto()
    INFO = auto()
```

#### ErrorHandler Class

```python
# scout/core/error_reporting/error_handler.py

from enum import Enum
from typing import Dict, Any, Optional, Type, Callable, List, Tuple
import sys
import traceback
from PyQt6.QtWidgets import QMessageBox, QApplication

from .logger import ScoutLogger
from .severity import ErrorSeverity
from .recovery import RecoverySystem
from .reporter import ErrorReporter


class ErrorHandler:
    """
    Handles exceptions and errors throughout the application.
    
    This class is responsible for intercepting exceptions, determining
    appropriate handling based on severity, and coordinating recovery
    attempts and error reporting.
    """
    
    def __init__(self, 
                logger: ScoutLogger, 
                recovery_system: Optional[RecoverySystem] = None,
                error_reporter: Optional[ErrorReporter] = None):
        """
        Initialize the error handler.
        
        Args:
            logger: Logger instance for recording errors
            recovery_system: System for attempting recovery from errors
            error_reporter: System for reporting errors
        """
        self.logger = logger
        self.recovery_system = recovery_system
        self.error_reporter = error_reporter
        self.registered_handlers: Dict[Type[Exception], Callable] = {}
        
        self.logger.info("Error handler initialized")
    
    def register_handler(self, 
                        exception_type: Type[Exception], 
                        handler: Callable[[Exception, Dict[str, Any]], bool]) -> None:
        """
        Register a custom handler for a specific exception type.
        
        Args:
            exception_type: The exception class to handle
            handler: Function that handles the exception.
                     Should return True if handled successfully.
        """
        self.registered_handlers[exception_type] = handler
        self.logger.info(f"Registered custom handler for {exception_type.__name__}")
    
    def handle_exception(self, 
                        exception: Exception, 
                        severity: ErrorSeverity = ErrorSeverity.SEVERE,
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle an exception with appropriate logging and recovery actions.
        
        Args:
            exception: The exception to handle
            severity: How severe the error is
            context: Additional contextual information about the error
            
        Returns:
            bool: True if the error was handled and recovered from, False otherwise
        """
        # Ensure context is not None
        if context is None:
            context = {}
        
        # Log the exception
        error_message = str(exception)
        tb = traceback.format_exc()
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL ERROR: {error_message}", exc_info=exception)
        elif severity == ErrorSeverity.SEVERE:
            self.logger.error(f"SEVERE ERROR: {error_message}", exc_info=exception)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(f"WARNING: {error_message}\n{tb}")
        else:
            self.logger.info(f"INFO: {error_message}")
        
        # Look for registered handler
        exception_type = type(exception)
        for base_type in self._get_exception_hierarchy(exception_type):
            if base_type in self.registered_handlers:
                try:
                    self.logger.info(f"Using registered handler for {base_type.__name__}")
                    handler_result = self.registered_handlers[base_type](exception, context)
                    if handler_result:
                        self.logger.info(f"Exception handled successfully by custom handler")
                        return True
                except Exception as handler_ex:
                    self.logger.error(f"Error in exception handler: {str(handler_ex)}")
        
        # Try automatic recovery if available and not critical
        if self.recovery_system and severity != ErrorSeverity.CRITICAL:
            try:
                recovery_success = self.recovery_system.attempt_recovery(
                    exception, severity, context
                )
                if recovery_success:
                    self.logger.info(f"Successfully recovered from {error_message}")
                    return True
            except Exception as recovery_ex:
                self.logger.error(f"Recovery system failed: {str(recovery_ex)}")
        
        # For critical or unrecovered errors, show error dialog
        show_dialog = context.get("show_error_dialog", True)
        if show_dialog and (severity == ErrorSeverity.CRITICAL or severity == ErrorSeverity.SEVERE):
            self._show_error_dialog(exception, error_message, severity, context)
        
        # For critical errors, prepare to exit the application
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Application cannot continue due to critical error")
            
            # Try to save any unsaved data if context provides a save function
            if "save_function" in context:
                try:
                    context["save_function"]()
                    self.logger.info("Successfully saved data before exit")
                except Exception as save_ex:
                    self.logger.error(f"Failed to save data before exit: {str(save_ex)}")
            
            # Schedule application exit with error code
            if context.get("exit_application", True):
                from scout.core.utils.codes import Codes
                app = QApplication.instance()
                if app:
                    app.exit(Codes.CRITICAL_ERROR_CODE)
        
        return False
    
    def _get_exception_hierarchy(self, exception_type: Type[Exception]) -> List[Type[Exception]]:
        """
        Get the hierarchy of exception types for a given exception.
        
        This allows handlers to be registered for base exception types
        and still catch derived exceptions.
        
        Args:
            exception_type: The exception type to get hierarchy for
            
        Returns:
            List of exception types, from most specific to most general
        """
        hierarchy = []
        current_type = exception_type
        
        while current_type is not object:
            hierarchy.append(current_type)
            current_type = current_type.__base__
        
        return hierarchy
    
    def _show_error_dialog(self, 
                          exception: Exception, 
                          error_message: str,
                          severity: ErrorSeverity,
                          context: Dict[str, Any]) -> None:
        """
        Show an error dialog to the user.
        
        Args:
            exception: The exception that occurred
            error_message: User-friendly error message
            severity: Error severity
            context: Error context information
        """
        # If we have an error reporter with dialog, use it
        if self.error_reporter and hasattr(self.error_reporter, "show_error_dialog"):
            self.error_reporter.show_error_dialog(exception, error_message, severity, context)
            return
        
        # Fallback to simple QMessageBox
        app = QApplication.instance()
        if app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(error_message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
    
    def global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """
        Global uncaught exception handler.
        
        This is set as sys.excepthook to catch otherwise uncaught exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't handle keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        self.logger.critical("Uncaught exception", 
                           exc_info=(exc_type, exc_value, exc_traceback))
        
        # Handle the uncaught exception
        self.handle_exception(
            exc_value,
            ErrorSeverity.CRITICAL,
            {"show_error_dialog": True}
        )
```

### Recovery System Implementation

The Recovery System attempts to restore application state after errors occur.

#### RecoveryStrategy Interface

```python
# scout/core/error_reporting/recovery_strategies.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .severity import ErrorSeverity


class RecoveryStrategy(ABC):
    """
    Base class for recovery strategies.
    
    Defines the interface for all recovery strategies.
    """
    
    @abstractmethod
    def can_handle(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Determine if this strategy can handle the given exception.
        
        Args:
            exception: The exception to handle
            context: Contextual information about the error
            
        Returns:
            Whether this strategy can handle the exception
        """
        pass
    
    @abstractmethod
    def execute(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Execute the recovery strategy.
        
        Args:
            exception: The exception to recover from
            context: Contextual information about the error
            
        Returns:
            Whether recovery was successful
        """
        pass
```

#### RetryStrategy Implementation

```python
# scout/core/error_reporting/recovery_strategies.py (continued)

import time


class RetryStrategy(RecoveryStrategy):
    """
    Strategy to retry a failed operation.
    
    This strategy attempts to retry an operation that failed with an exception.
    The retry can be configured with a maximum number of attempts and a delay
    between attempts.
    """
    
    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        """
        Initialize the retry strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.delay = delay
    
    def can_handle(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Check if this is a retriable operation.
        
        A retriable operation must provide a retry_function in the context.
        
        Args:
            exception: The exception to handle
            context: Contextual information, must contain 'retry_function'
            
        Returns:
            Whether this strategy can handle the exception
        """
        return (
            context is not None and
            "retry_function" in context
        )
    
    def execute(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Retry the operation several times.
        
        Args:
            exception: The exception to recover from
            context: Contextual information including:
                     - retry_function: Function to retry
                     - retry_args: Args for the function (optional)
                     - retry_kwargs: Kwargs for the function (optional)
            
        Returns:
            Whether recovery was successful
        """
        retry_function = context["retry_function"]
        retry_args = context.get("retry_args", [])
        retry_kwargs = context.get("retry_kwargs", {})
        
        for attempt in range(self.max_retries):
            try:
                # Wait before retrying (except first attempt)
                if attempt > 0:
                    time.sleep(self.delay)
                
                # Try again
                result = retry_function(*retry_args, **retry_kwargs)
                return True
            except Exception as e:
                # If it's the same error, continue trying
                # If it's a different error, it might be making progress
                continue
        
        return False


class ComponentResetStrategy(RecoveryStrategy):
    """
    Strategy to reset a malfunctioning component.
    
    This strategy attempts to recover by resetting a component to its
    initial state.
    """
    
    def can_handle(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Check if there's a component to reset.
        
        A resettable component must be provided in the context and must
        have a reset() method.
        
        Args:
            exception: The exception to handle
            context: Contextual information, must contain 'component'
            
        Returns:
            Whether this strategy can handle the exception
        """
        return (
            context is not None and
            "component" in context and
            hasattr(context["component"], "reset")
        )
    
    def execute(self, exception: Exception, context: Dict[str, Any]) -> bool:
        """
        Reset the component.
        
        Args:
            exception: The exception to recover from
            context: Contextual information, containing 'component'
            
        Returns:
            Whether recovery was successful
        """
        component = context["component"]
        try:
            component.reset()
            return True
        except Exception:
            return False
```

#### RecoverySystem Implementation

```python
# scout/core/error_reporting/recovery.py

from typing import Dict, Any, List, Optional
from .logger import ScoutLogger
from .severity import ErrorSeverity
from .recovery_strategies import RecoveryStrategy, RetryStrategy, ComponentResetStrategy


class RecoverySystem:
    """
    System for recovering from errors automatically.
    
    This system maintains a list of recovery strategies and attempts
    to apply them when errors occur.
    """
    
    def __init__(self, logger: ScoutLogger):
        """
        Initialize the recovery system.
        
        Args:
            logger: Logger for recovery operations
        """
        self.logger = logger
        self.strategies: List[RecoveryStrategy] = []
        
        # Register default strategies
        self.strategies.append(RetryStrategy())
        self.strategies.append(ComponentResetStrategy())
        
        self.logger.info("Recovery system initialized with default strategies")
    
    def register_strategy(self, strategy: RecoveryStrategy) -> None:
        """
        Register a new recovery strategy.
        
        Args:
            strategy: The strategy to register
        """
        self.strategies.append(strategy)
        self.logger.info(f"Registered recovery strategy: {strategy.__class__.__name__}")
    
    def attempt_recovery(self, 
                        exception: Exception,
                        severity: ErrorSeverity,
                        context: Dict[str, Any]) -> bool:
        """
        Attempt to recover from an error.
        
        Args:
            exception: The exception to recover from
            severity: The severity of the error
            context: Contextual information about the error
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        if not context:
            return False
            
        self.logger.info(f"Attempting recovery from {str(exception)}")
        
        # Try each strategy in order
        for strategy in self.strategies:
            if strategy.can_handle(exception, context):
                self.logger.info(f"Applying recovery strategy: {strategy.__class__.__name__}")
                try:
                    result = strategy.execute(exception, context)
                    if result:
                        self.logger.info(f"Recovery successful using {strategy.__class__.__name__}")
                        return True
                    self.logger.info(f"Recovery strategy {strategy.__class__.__name__} failed")
                except Exception as e:
                    self.logger.warning(f"Recovery strategy {strategy.__class__.__name__} raised exception: {str(e)}")
        
        self.logger.warning(f"All recovery strategies failed for {str(exception)}")
        return False
```

### Error Reporter Implementation

The Error Reporter collects diagnostic information and facilitates error reporting.

#### SystemInfo Class

```python
# scout/core/error_reporting/system_info.py

import platform
import socket
import os
import sys
from typing import Dict, Any


class SystemInfo:
    """
    Collects system information for diagnostics.
    
    This class provides static methods to gather information about
    the system and environment for error reporting.
    """
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Collect general system information.
        
        Returns:
            Dictionary of system information
        """
        try:
            info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "architecture": platform.architecture(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": socket.gethostname(),
                "username": os.getlogin(),
                "pid": os.getpid(),
                "cwd": os.getcwd(),
                "executable": sys.executable,
            }
            
            # Add IP address if available
            try:
                info["ip_address"] = socket.gethostbyname(socket.gethostname())
            except:
                info["ip_address"] = "Unknown"
                
            return info
        except Exception as e:
            # Return partial information on error
            return {
                "error": str(e),
                "python_version": platform.python_version(),
                "system": platform.system()
            }
        
    @staticmethod
    def get_installed_packages() -> Dict[str, str]:
        """
        Get list of installed Python packages.
        
        Returns:
            Dictionary mapping package names to versions
        """
        try:
            import pkg_resources
            packages = {}
            for package in pkg_resources.working_set:
                packages[package.key] = package.version
            return packages
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_application_config() -> Dict[str, Any]:
        """
        Get application configuration information.
        
        Returns:
            Dictionary of application configuration
        """
        # Implementation depends on how Scout stores configuration
        try:
            config = {
                "app_name": "Scout",
                "app_version": "1.0.0",  # Replace with actual version
                # Add other configuration items
            }
            return config
        except Exception as e:
            return {"error": str(e)}
```

#### ErrorReporter Class

```python
# scout/core/error_reporting/reporter.py

import json
import os
import time
import traceback
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import QApplication

from .logger import ScoutLogger
from .severity import ErrorSeverity
from .system_info import SystemInfo
from .error_dialog import ErrorDialog


class ErrorReporter:
    """
    Collects and reports error information.
    
    This class handles creating, saving, and submitting error reports.
    It also manages showing error dialogs to users.
    """
    
    def __init__(self, logger: ScoutLogger, report_url: Optional[str] = None):
        """
        Initialize the error reporter.
        
        Args:
            logger: Logger instance
            report_url: URL for submitting error reports, None if not used
        """
        self.logger = logger
        self.report_url = report_url
        
        # Create reports directory
        reports_dir = os.path.join(os.path.dirname(logger.get_log_file_path()), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        self.reports_dir = reports_dir
        
        self.logger.info("Error reporter initialized")
        if report_url:
            self.logger.info(f"Error reporting URL: {report_url}")
    
    def collect_error_report(self, 
                           exception: Exception,
                           context: Dict[str, Any],
                           user_description: str = "",
                           include_system_info: bool = True) -> Dict[str, Any]:
        """
        Collect information for an error report.
        
        Args:
            exception: The exception that occurred
            context: Contextual information about the error
            user_description: User's description of what happened
            include_system_info: Whether to include system information
            
        Returns:
            Dict containing the error report
        """
        report = {
            "error": {
                "type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc(),
            },
            "context": self._sanitize_context(context),
            "user_description": user_description,
            "timestamp": time.time(),
            "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
            "application": SystemInfo.get_application_config(),
        }
        
        if include_system_info:
            report["system"] = SystemInfo.get_system_info()
            report["packages"] = SystemInfo.get_installed_packages()
        
        return report
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive or non-serializable items from context.
        
        Args:
            context: Original context dictionary
            
        Returns:
            Sanitized context dictionary
        """
        if not context:
            return {}
            
        # Create a shallow copy
        sanitized = {}
        
        # Copy safe items, convert others to strings
        for key, value in context.items():
            # Skip callable objects
            if callable(value):
                continue
                
            # Skip objects with potentially sensitive info
            if key in ["password", "credentials", "token", "secret"]:
                continue
                
            try:
                # Test if value is JSON serializable
                json.dumps({key: value})
                sanitized[key] = value
            except (TypeError, OverflowError):
                # Convert non-serializable values to string representation
                sanitized[key] = str(value)
        
        return sanitized
    
    def save_error_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save error report to a file.
        
        Args:
            report: The error report to save
            filename: Optional filename, will generate one if not provided
            
        Returns:
            Path to the saved report file
        """
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            error_type = report["error"]["type"]
            filename = f"error_{error_type}_{timestamp}.json"
        
        report_path = os.path.join(self.reports_dir, filename)
        
        # Save report
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Error report saved to {report_path}")
            return report_path
        except Exception as e:
            self.logger.error(f"Failed to save error report to {report_path}: {str(e)}")
            
            # Fallback to temp directory
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)
                self.logger.info(f"Error report saved to alternate location: {temp_path}")
                return temp_path
            except Exception as e2:
                self.logger.error(f"Failed to save error report to alternate location: {str(e2)}")
                return ""
    
    def submit_error_report(self, report: Dict[str, Any]) -> bool:
        """
        Submit error report to the reporting server.
        
        Args:
            report: The error report to submit
            
        Returns:
            Whether the submission was successful
        """
        if not self.report_url:
            self.logger.warning("No report URL configured, cannot submit error report")
            return False
        
        try:
            # Convert report to JSON
            data = json.dumps(report).encode('utf-8')
            
            # Create request
            request = urllib.request.Request(
                self.report_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Send request
            with urllib.request.urlopen(request, timeout=10) as response:
                self.logger.info(f"Error report submitted successfully, status: {response.status}")
                return True
        
        except Exception as e:
            self.logger.error(f"Failed to submit error report: {str(e)}")
            return False
    
    def show_error_dialog(self, 
                       exception: Exception, 
                       error_message: str,
                       severity: ErrorSeverity,
                       context: Dict[str, Any]) -> None:
        """
        Show an error dialog to the user.
        
        Args:
            exception: The exception that occurred
            error_message: User-friendly error message
            severity: Error severity
            context: Error context information
        """
        app = QApplication.instance()
        if not app:
            self.logger.warning("Cannot show error dialog: No QApplication instance")
            return
            
        dialog = ErrorDialog(
            parent=None,  # Can specify a parent window if available in context
            exception=exception,
            error_message=error_message,
            error_reporter=self,
            severity=severity
        )
        dialog.exec()
```

### Error Dialog Implementation

The Error Dialog shows users information about errors and allows them to report issues.

```python
# scout/core/error_reporting/error_dialog.py

import traceback
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from .severity import ErrorSeverity


class ErrorDialog(QDialog):
    """
    Dialog for displaying errors and collecting error reports.
    
    This dialog shows error information to users and allows them to
    submit error reports with additional information.
    """
    
    def __init__(self, 
                parent=None, 
                exception: Optional[Exception] = None,
                error_message: Optional[str] = None,
                error_reporter=None,
                severity: ErrorSeverity = ErrorSeverity.SEVERE):
        """
        Initialize error dialog.
        
        Args:
            parent: Parent widget
            exception: The exception that occurred
            error_message: User-friendly error message
            error_reporter: Error reporter instance for submitting reports
            severity: Error severity level
        """
        super().__init__(parent)
        
        self.exception = exception
        self.error_message = error_message or str(exception)
        self.error_reporter = error_reporter
        self.severity = severity
        
        self.setWindowTitle(self.tr("Error"))
        self.setMinimumSize(QSize(500, 400))
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the dialog's UI components."""
        layout = QVBoxLayout(self)
        
        # Error icon and message
        error_layout = QHBoxLayout()
        icon_label = QLabel()
        
        if self.severity == ErrorSeverity.CRITICAL:
            icon = QIcon.fromTheme("dialog-error")
            self.setWindowTitle(self.tr("Critical Error"))
        elif self.severity == ErrorSeverity.SEVERE:
            icon = QIcon.fromTheme("dialog-warning")
            self.setWindowTitle(self.tr("Error"))
        else:
            icon = QIcon.fromTheme("dialog-information")
            self.setWindowTitle(self.tr("Warning"))
            
        icon_label.setPixmap(icon.pixmap(32, 32))
        error_layout.addWidget(icon_label)
        
        message_label = QLabel(self.error_message)
        message_label.setWordWrap(True)
        error_layout.addWidget(message_label, 1)
        
        layout.addLayout(error_layout)
        
        # Add explanation of what happened
        if self.severity == ErrorSeverity.CRITICAL:
            explanation = self.tr(
                "A critical error has occurred and the application cannot continue. "
                "Please report this error to help improve the application."
            )
        else:
            explanation = self.tr(
                "An error has occurred. You can continue using the application, "
                "but some functionality may be limited."
            )
            
        explanation_label = QLabel(explanation)
        explanation_label.setWordWrap(True)
        layout.addWidget(explanation_label)
        
        # Details section
        if self.exception:
            details_label = QLabel(self.tr("Technical Details:"))
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(100)
            details_text.setPlainText(traceback.format_exc())
            layout.addWidget(details_text)
        
        # User description
        if self.error_reporter:
            description_label = QLabel(
                self.tr("Please describe what you were doing when the error occurred:")
            )
            layout.addWidget(description_label)
            
            self.description_edit = QTextEdit()
            self.description_edit.setMaximumHeight(100)
            layout.addWidget(self.description_edit)
            
            # System info checkbox
            self.system_info_checkbox = QCheckBox(
                self.tr("Include system information (recommended)")
            )
            self.system_info_checkbox.setChecked(True)
            layout.addWidget(self.system_info_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if self.error_reporter:
            self.report_button = QPushButton(self.tr("Report Error"))
            self.report_button.clicked.connect(self._on_report_clicked)
            button_layout.addWidget(self.report_button)
        
        if self.severity == ErrorSeverity.CRITICAL:
            close_button = QPushButton(self.tr("Close Application"))
            close_button.clicked.connect(self._on_close_app_clicked)
        else:
            close_button = QPushButton(self.tr("Close"))
            close_button.clicked.connect(self.accept)
            
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _on_report_clicked(self):
        """Handle error report submission."""
        if not self.error_reporter:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Error reporting is not configured.")
            )
            return
        
        # Collect report
        user_description = ""
        include_system_info = True
        
        if hasattr(self, "description_edit"):
            user_description = self.description_edit.toPlainText()
            
        if hasattr(self, "system_info_checkbox"):
            include_system_info = self.system_info_checkbox.isChecked()
        
        # Collect report
        report = self.error_reporter.collect_error_report(
            self.exception,
            context={},  # Context is passed elsewhere
            user_description=user_description,
            include_system_info=include_system_info
        )
        
        # Save report locally
        report_path = self.error_reporter.save_error_report(report)
        
        # Submit report if URL is configured
        if self.error_reporter.report_url:
            progress = QProgressDialog(
                self.tr("Submitting error report..."),
                self.tr("Cancel"),
                0, 0, self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # In a real app, this would be done in a separate thread
            success = self.error_reporter.submit_error_report(report)
            progress.close()
            
            if success:
                QMessageBox.information(
                    self,
                    self.tr("Report Submitted"),
                    self.tr("Thank you for submitting an error report.")
                )
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Submission Failed"),
                    self.tr("The error report could not be submitted. "
                          "It has been saved locally and can be submitted later.")
                )
        else:
            # Just inform that report was saved
            QMessageBox.information(
                self,
                self.tr("Report Saved"),
                self.tr("The error report has been saved to:\n{0}").format(report_path)
            )
    
    def _on_close_app_clicked(self):
        """Handle close application button for critical errors."""
        self.accept()
        
        # Application exit will be handled by the error handler
```

## File Organization

The Error Reporting and Recovery System is organized into the following file structure:

```
scout/
├── core/
│   ├── error_reporting/
│   │   ├── __init__.py
│   │   ├── logger.py               # ScoutLogger class
│   │   ├── severity.py             # ErrorSeverity enum
│   │   ├── error_handler.py        # ErrorHandler class
│   │   ├── recovery.py             # RecoverySystem class
│   │   ├── recovery_strategies.py  # RecoveryStrategy classes
│   │   ├── system_info.py          # SystemInfo class
│   │   ├── reporter.py             # ErrorReporter class
│   │   ├── error_dialog.py         # ErrorDialog class
│   │   └── setup.py                # Setup functions
```

### Main Entry Point: setup.py

The setup.py file provides a simple API for initializing the Error Reporting and Recovery System:

```python
# scout/core/error_reporting/setup.py

from typing import Tuple

from .logger import ScoutLogger
from .error_handler import ErrorHandler
from .recovery import RecoverySystem
from .reporter import ErrorReporter


def setup_error_handling(
    log_dir=None,
    log_level=None,
    report_url=None
) -> Tuple[ScoutLogger, ErrorHandler, RecoverySystem, ErrorReporter]:
    """
    Set up the error handling system.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        report_url: URL for error reporting
        
    Returns:
        Tuple of (logger, error_handler, recovery_system, error_reporter)
    """
    # Create logger
    logger = ScoutLogger(log_dir=log_dir, log_level=log_level)
    
    # Create recovery system
    recovery_system = RecoverySystem(logger)
    
    # Create error reporter
    error_reporter = ErrorReporter(logger, report_url=report_url)
    
    # Create error handler
    error_handler = ErrorHandler(logger, recovery_system, error_reporter)
    
    # Set up global exception handler
    import sys
    sys.excepthook = error_handler.global_exception_handler
    
    return logger, error_handler, recovery_system, error_reporter
```

### Package Initialization: __init__.py

The __init__.py file exports the main components of the system:

```python
# scout/core/error_reporting/__init__.py

from .logger import ScoutLogger
from .severity import ErrorSeverity
from .error_handler import ErrorHandler
from .recovery import RecoverySystem
from .recovery_strategies import RecoveryStrategy, RetryStrategy, ComponentResetStrategy
from .reporter import ErrorReporter
from .error_dialog import ErrorDialog
from .system_info import SystemInfo
from .setup import setup_error_handling

__all__ = [
    'ScoutLogger',
    'ErrorSeverity',
    'ErrorHandler',
    'RecoverySystem',
    'RecoveryStrategy',
    'RetryStrategy',
    'ComponentResetStrategy',
    'ErrorReporter',
    'ErrorDialog',
    'SystemInfo',
    'setup_error_handling'
]
```

## Example Usage Scenarios

### Handling Network Errors

This example shows how to handle network errors when downloading resources:

```python
from scout.core.error_reporting import ErrorSeverity
import urllib.request
import urllib.error
import time

def download_resources(url, retries=3):
    """
    Download resources from a URL with error handling.
    
    Args:
        url: URL to download from
        retries: Number of retries
        
    Returns:
        Downloaded content
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read()
    except urllib.error.URLError as e:
        context = {
            "operation": "download_resources",
            "url": url,
            "retry_function": download_resources,
            "retry_args": [url],
            "retry_kwargs": {},
            "show_error_dialog": True
        }
        if error_handler.handle_exception(e, ErrorSeverity.WARNING, context):
            # If recovery was successful (retry worked), return the result
            # This shouldn't be needed since the retry would have returned,
            # but we include it for clarity
            return download_resources(url)
        else:
            # Fall back to cached resources
            return load_cached_resources()
    except Exception as e:
        # Handle other exceptions
        context = {
            "operation": "download_resources",
            "url": url
        }
        error_handler.handle_exception(e, ErrorSeverity.SEVERE, context)
        return load_cached_resources()

def load_cached_resources():
    """Load resources from cache as a fallback."""
    # Implementation
    return b"Cached data"
```

### Handling File Access Errors

This example shows how to handle file access errors when saving data:

```python
import os
import json

def save_data(data, file_path):
    """
    Save data to a file with error handling.
    
    Args:
        data: Data to save
        file_path: Path to save to
        
    Returns:
        Whether the save was successful
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save data
        with open(file_path, 'w') as f:
            json.dump(data, f)
        return True
    except (PermissionError, IOError) as e:
        # Handle file access errors
        context = {
            "operation": "save_data",
            "file_path": file_path,
            "data": data,
            "retry_function": save_data,
            "retry_args": [data, file_path]
        }
        if error_handler.handle_exception(e, ErrorSeverity.WARNING, context):
            # If recovery was successful, we're done
            return True
        
        # If error handler couldn't handle it, try a different location
        backup_path = os.path.join(os.path.expanduser("~"), "scout_backup.json")
        try:
            with open(backup_path, 'w') as f:
                json.dump(data, f)
            logger.info(f"Data saved to backup location: {backup_path}")
            return True
        except Exception as backup_error:
            # Last resort: in-memory backup
            global in_memory_backup
            in_memory_backup = data
            logger.error(f"Failed to save backup: {str(backup_error)}")
            return False
    except Exception as e:
        # Handle other exceptions
        context = {
            "operation": "save_data",
            "file_path": file_path
        }
        error_handler.handle_exception(e, ErrorSeverity.SEVERE, context)
        return False
```

### Handling UI Component Errors

This example shows how to handle errors in UI components:

```python
class ResultsWidget(QWidget):
    """Widget for displaying detection results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()
        self._results = []
    
    def _create_ui(self):
        """Create the UI components."""
        # Implementation
        
    def reset(self):
        """Reset the widget to initial state."""
        self._results = []
        # Reset UI components
        
    def update_results(self, results):
        """
        Update the displayed results.
        
        Args:
            results: Detection results to display
        """
        try:
            self._results = results
            # Update UI components with results
        except Exception as e:
            # Provide context for error handler
            context = {
                "operation": "update_results",
                "component": self,
                "results": results,
                "show_error_dialog": False  # Don't show dialog for UI errors
            }
            if not error_handler.handle_exception(e, ErrorSeverity.WARNING, context):
                # If recovery failed, reset the component
                self.reset()
                
                # Try again with simple representation
                try:
                    # Simplified update that's less likely to fail
                    pass
                except Exception as e2:
                    # If all else fails, log and show error message
                    error_handler.handle_exception(
                        e2, 
                        ErrorSeverity.SEVERE,
                        {"operation": "update_results_fallback"}
                    )
```

### Creating a Custom Recovery Strategy

This example shows how to create and register a custom recovery strategy:

```python
from scout.core.error_reporting import RecoveryStrategy

class DatabaseReconnectStrategy(RecoveryStrategy):
    """Strategy to recover from database connection issues."""
    
    def __init__(self, max_attempts=3, delay=2.0):
        """Initialize the strategy."""
        self.max_attempts = max_attempts
        self.delay = delay
    
    def can_handle(self, exception, context):
        """Check if this is a database connection error."""
        # Check if it's a database connection exception
        return (
            isinstance(exception, DatabaseConnectionError) or
            (context and "database" in context)
        )
    
    def execute(self, exception, context):
        """Attempt to reconnect to the database."""
        db_manager = context.get("database")
        if not db_manager:
            return False
            
        for attempt in range(self.max_attempts):
            try:
                if attempt > 0:
                    import time
                    time.sleep(self.delay)
                
                db_manager.reconnect()
                return db_manager.is_connected()
            except Exception:
                continue
                
        return False

# Register the strategy
recovery_system.register_strategy(DatabaseReconnectStrategy())
``` 