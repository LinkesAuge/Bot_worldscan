# Integrating the Error Reporting and Recovery System

This document provides guidance on how to integrate the Error Reporting and Recovery System into the Scout application code. It includes step-by-step instructions, code examples, and best practices.

## Table of Contents

1. [System Initialization](#system-initialization)
2. [Basic Exception Handling](#basic-exception-handling)
3. [Contextual Error Handling](#contextual-error-handling)
4. [Recovery Strategies](#recovery-strategies)
5. [UI Integration](#ui-integration)
6. [Centralized vs. Local Error Handling](#centralized-vs-local-error-handling)
7. [Integration Checklist](#integration-checklist)

## System Initialization

Before using the error handling system, you need to initialize it in your application.

### Application Entry Point Integration

Add this code to your application's entry point file (`main.py`):

```python
# main.py

import sys
from scout.core.error_reporting import setup_error_handling

def main():
    """Main application entry point."""
    # Initialize error handling system before creating UI
    global logger, error_handler, recovery_system, error_reporter
    logger, error_handler, recovery_system, error_reporter = setup_error_handling(
        log_dir=None,  # Use default log directory
        log_level=None,  # Use default log level
        report_url=None  # No error reporting URL in development
    )
    
    try:
        # Import Qt modules and start application
        from PyQt6.QtWidgets import QApplication
        from scout.ui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        # This will be caught by the global exception handler
        # but we include it for completeness and to handle
        # initialization errors specifically
        raise e

if __name__ == "__main__":
    main()
```

### Making Components Error-Aware

To make a component error-aware, you need to pass the error handling components to it:

```python
# scout/ui/main_window.py

from PyQt6.QtWidgets import QMainWindow
from scout.core.error_reporting import ErrorHandler, ErrorSeverity


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scout")
        
        # Get error handler from global scope
        from scout.main import error_handler, logger
        self.error_handler = error_handler
        self.logger = logger
        
        # Initialize UI components
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        try:
            # UI initialization code
            pass
        except Exception as e:
            self.error_handler.handle_exception(
                e,
                ErrorSeverity.CRITICAL,
                {"component": "MainWindow", "operation": "init_ui"}
            )
```

## Basic Exception Handling

Here's how to handle exceptions using the error handling system:

### Simple try-except Pattern

```python
from scout.core.error_reporting import ErrorSeverity

def load_game_state(path):
    """Load game state from file."""
    try:
        # Attempt to load game state
        with open(path, 'r') as f:
            # Process file
            pass
        return True
    except FileNotFoundError as e:
        # Handle specific exception
        from scout.main import error_handler
        error_handler.handle_exception(
            e,
            ErrorSeverity.WARNING,
            {
                "message": f"Game state file not found: {path}",
                "show_error_dialog": True
            }
        )
        return False
    except Exception as e:
        # Handle general exceptions
        from scout.main import error_handler
        error_handler.handle_exception(
            e,
            ErrorSeverity.SEVERE,
            {
                "message": f"Failed to load game state from {path}",
                "show_error_dialog": True
            }
        )
        return False
```

### Handling Different Severity Levels

```python
from scout.core.error_reporting import ErrorSeverity

def connect_to_server(url, retries=3):
    """Connect to the server."""
    from scout.main import error_handler, logger
    
    for attempt in range(retries):
        try:
            # Attempt connection
            logger.info(f"Connecting to server: {url} (attempt {attempt+1}/{retries})")
            # ... connection code ...
            return True
        except ConnectionRefusedError as e:
            # Server might be temporarily down, retry
            severity = ErrorSeverity.WARNING if attempt < retries - 1 else ErrorSeverity.SEVERE
            error_handler.handle_exception(
                e,
                severity,
                {
                    "url": url,
                    "attempt": attempt + 1,
                    "max_attempts": retries,
                    "show_error_dialog": attempt == retries - 1  # Only show dialog on last attempt
                }
            )
            if attempt < retries - 1:
                # Wait before retrying
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
    
    # All attempts failed
    return False
```

## Contextual Error Handling

Providing context in the error handler allows for better diagnostics and automatic recovery.

### Providing Rich Context

```python
def process_detection_results(results, game_state):
    """Process detection results and update game state."""
    from scout.main import error_handler, logger
    
    try:
        # Process results
        pass
    except KeyError as e:
        # Missing key in results
        error_handler.handle_exception(
            e,
            ErrorSeverity.WARNING,
            {
                "operation": "process_detection_results",
                "results": results,  # Include the actual data
                "game_state": game_state,
                "missing_key": str(e),
                "component": "Detection",
                "retry_function": process_detection_results,
                "retry_args": [results, game_state],
                "show_error_dialog": False  # Don't distract user for non-critical error
            }
        )
        return False
    except Exception as e:
        # General exception
        error_handler.handle_exception(
            e,
            ErrorSeverity.SEVERE,
            {
                "operation": "process_detection_results",
                "component": "Detection",
                "show_error_dialog": True
            }
        )
        return False
```

### Handling Multiple Operations in a Sequence

```python
def save_settings(settings, path):
    """Save settings to a file."""
    from scout.main import error_handler, logger
    
    # Track operations for context
    operations = []
    
    try:
        # Operation 1: Convert settings to JSON
        operations.append("convert_settings")
        import json
        settings_json = json.dumps(settings, indent=2)
        
        # Operation 2: Ensure directory exists
        operations.append("ensure_directory")
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Operation 3: Save to temporary file first
        operations.append("save_to_temp")
        temp_path = path + ".tmp"
        with open(temp_path, 'w') as f:
            f.write(settings_json)
        
        # Operation 4: Rename temp file to final file
        operations.append("rename_to_final")
        import os
        if os.path.exists(path):
            os.remove(path)
        os.rename(temp_path, path)
        
        logger.info(f"Settings saved to {path}")
        return True
        
    except Exception as e:
        # Include current operation in context
        current_operation = operations[-1] if operations else "unknown"
        
        error_handler.handle_exception(
            e,
            ErrorSeverity.SEVERE,
            {
                "operation": f"save_settings.{current_operation}",
                "settings_path": path,
                "completed_operations": operations,
                "show_error_dialog": True,
                "save_function": lambda: _emergency_save_settings(settings)
            }
        )
        return False


def _emergency_save_settings(settings):
    """Emergency function to save settings to a fallback location."""
    import os
    import json
    
    # Use user's home directory as fallback
    fallback_path = os.path.join(os.path.expanduser("~"), "scout_settings_backup.json")
    
    try:
        with open(fallback_path, 'w') as f:
            json.dump(settings, f)
        return True
    except Exception:
        # Last resort - print to log
        from scout.main import logger
        logger.critical(f"EMERGENCY SETTINGS DUMP: {settings}")
        return False
```

## Recovery Strategies

Creating and using recovery strategies for common error scenarios.

### Creating a Custom Recovery Strategy

```python
# scout/core/detection/recovery.py

from scout.core.error_reporting import RecoveryStrategy


class DetectionFailureRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for detection failures."""
    
    def can_handle(self, exception, context):
        """Check if this strategy can handle the exception."""
        return (
            context and
            context.get("component") == "Detection" and
            "window_handle" in context
        )
    
    def execute(self, exception, context):
        """Execute recovery by retrying detection with different parameters."""
        from scout.core.detection import get_detector
        
        window_handle = context.get("window_handle")
        if not window_handle:
            return False
            
        try:
            # Get detection instance
            detector = get_detector()
            
            # Try a different detection method
            if context.get("detection_method") == "template":
                # Try contour detection instead
                detector.set_method("contour")
            else:
                # Try template matching instead
                detector.set_method("template")
                
            # Retry detection
            result = detector.detect(window_handle)
            
            # If we get here, recovery succeeded
            return True
        except Exception:
            # Recovery failed
            return False


# Register the strategy
def register_detection_recovery_strategies():
    """Register recovery strategies for detection errors."""
    from scout.main import recovery_system
    recovery_system.register_strategy(DetectionFailureRecoveryStrategy())
```

### Using Recovery Context in Code

```python
def run_detection(window_handle, method="template"):
    """Run detection on the window."""
    from scout.main import error_handler, logger
    
    try:
        # Run detection
        detector = get_detector()
        detector.set_method(method)
        result = detector.detect(window_handle)
        return result
    except Exception as e:
        # Provide context for recovery
        error_handler.handle_exception(
            e,
            ErrorSeverity.WARNING,
            {
                "component": "Detection",
                "operation": "run_detection",
                "window_handle": window_handle,
                "detection_method": method,
                "retry_function": run_detection,
                "retry_args": [window_handle],
                "retry_kwargs": {"method": "contour" if method == "template" else "template"}
            }
        )
        return None
```

## UI Integration

Integrating with the UI for a better error reporting experience.

### Adding a "Report Issue" Button

```python
# scout/ui/main_window.py

def _create_help_menu(self):
    """Create the help menu."""
    from scout.main import error_reporter, logger
    
    help_menu = self.menuBar().addMenu("&Help")
    
    # Add Report Issue action
    report_action = help_menu.addAction("&Report Issue...")
    report_action.triggered.connect(self._on_report_issue)
    
    # Other menu items
    help_menu.addAction("&About").triggered.connect(self._on_about)

def _on_report_issue(self):
    """Handle Report Issue menu item."""
    from scout.main import error_reporter
    
    try:
        # Create a dummy exception to use the report mechanism
        dummy_exception = Exception("User-reported issue")
        
        # Show error dialog with reporting
        from scout.core.error_reporting import ErrorSeverity
        error_reporter.show_error_dialog(
            dummy_exception,
            "Please describe the issue you're experiencing:",
            ErrorSeverity.INFO,
            {"component": "UserReport"}
        )
    except Exception as e:
        # Handle exception in error reporting
        from scout.main import error_handler
        error_handler.handle_exception(
            e,
            ErrorSeverity.SEVERE,
            {"operation": "report_issue"}
        )
```

### Displaying Error Information in the UI

```python
# scout/ui/status_bar.py

from PyQt6.QtWidgets import QStatusBar, QLabel
from PyQt6.QtCore import Qt

class StatusBar(QStatusBar):
    """Custom status bar with error information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize labels
        self.status_label = QLabel()
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        
        # Add to status bar
        self.addWidget(self.status_label, 1)
        self.addPermanentWidget(self.error_label)
        
        # Hide error label initially
        self.error_label.setVisible(False)
    
    def set_status(self, message):
        """Set the status message."""
        self.status_label.setText(message)
    
    def show_error(self, message, timeout=5000):
        """
        Show an error message in the status bar.
        
        Args:
            message: Error message to display
            timeout: Time in ms to display the message, 0 for no timeout
        """
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        
        if timeout > 0:
            # Clear after timeout
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(timeout, self.clear_error)
    
    def clear_error(self):
        """Clear the error message."""
        self.error_label.setText("")
        self.error_label.setVisible(False)


# Using the StatusBar in MainWindow
class MainWindow(QMainWindow):
    # ...
    
    def _init_ui(self):
        # ...
        
        # Create status bar
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)
        
        # Connect to error handler
        from scout.main import error_handler
        error_handler.status_error_signal.connect(self.status_bar.show_error)
```

## Centralized vs. Local Error Handling

Guidelines for deciding when to use centralized error handling vs. local handling.

### Centralized Error Handling

Use the central error handler for:

- Errors that might be recoverable
- Errors that should be logged
- Errors that should be reported
- Errors that require user notification

```python
# Using centralized error handling
try:
    # Operation that might fail
    result = process_data(data)
except Exception as e:
    from scout.main import error_handler
    from scout.core.error_reporting import ErrorSeverity
    
    error_handler.handle_exception(
        e,
        ErrorSeverity.WARNING,
        {"operation": "process_data"}
    )
    result = None
```

### Local Error Handling

Use local error handling for:

- Expected exceptions that are part of normal control flow
- Errors that can be fully handled locally
- Performance-critical code sections

```python
# Using local error handling for expected cases
try:
    value = data["key"]
except KeyError:
    # Default value if key doesn't exist
    value = default_value
    
# Only log unexpected issues
if value is None and default_value is not None:
    from scout.main import logger
    logger.warning(f"Unexpected None value for 'key' in data: {data}")
```

### Mixing Approaches

You can also mix the approaches:

```python
def load_configuration(path):
    """Load configuration from file."""
    from scout.main import logger, error_handler
    from scout.core.error_reporting import ErrorSeverity
    
    try:
        with open(path, 'r') as f:
            import json
            try:
                # Parse JSON (handled locally, common error)
                config = json.loads(f.read())
            except json.JSONDecodeError as e:
                # Handle locally, expected error
                logger.warning(f"Invalid JSON in configuration file: {path}")
                return {}
                
            # Validate configuration
            return config
    except FileNotFoundError:
        # Handle locally, expected error
        logger.info(f"Configuration file not found, using defaults: {path}")
        return {}
    except Exception as e:
        # Use central handler for unexpected errors
        error_handler.handle_exception(
            e,
            ErrorSeverity.SEVERE,
            {"operation": "load_configuration", "path": path}
        )
        return {}
```

## Integration Checklist

Use this checklist when integrating the error handling system:

1. **Initialization**
   - [ ] Error handling system is initialized at application startup
   - [ ] Global exception handler is set up
   - [ ] Custom recovery strategies are registered

2. **Exception Handling**
   - [ ] All code that could throw exceptions is wrapped in try-except blocks
   - [ ] Appropriate severity levels are used for different types of errors
   - [ ] Rich context is provided to the error handler

3. **Recovery**
   - [ ] Recovery strategies are defined for common error scenarios
   - [ ] Recovery context is provided in error handling calls
   - [ ] Fallback mechanisms are implemented for critical operations

4. **UI Integration**
   - [ ] Error messages are displayed to the user when appropriate
   - [ ] Error reporting mechanism is accessible to users
   - [ ] Status bar shows error information

5. **Logging**
   - [ ] Debug logs are added for troubleshooting
   - [ ] Log levels are appropriately set
   - [ ] Sensitive information is not logged

6. **Testing**
   - [ ] Error handling has been tested for all critical components
   - [ ] Recovery mechanisms have been tested
   - [ ] Error reporting has been tested 