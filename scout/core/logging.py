"""Logging configuration for TB Scout application."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Union, Optional

class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A RotatingFileHandler that handles errors gracefully."""
    
    def handleError(self, record: logging.LogRecord) -> None:
        """Handle errors during logging without recursion.
        
        Args:
            record: The log record that caused the error.
        """
        try:
            # Write error to stderr without logging
            sys.stderr.write("Error in logging handler:\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
        except Exception:
            # If even that fails, give up silently
            pass

def setup_logging(
    log_dir: Union[str, Path],
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None,
) -> None:
    """Set up logging configuration with both console and file handlers.
    
    Args:
        log_dir: Directory where log files will be stored.
        console_level: Logging level for console output (default: INFO).
        file_level: Logging level for file output (default: DEBUG).
        max_bytes: Maximum size in bytes before rotating log file (default: 10MB).
        backup_count: Number of backup files to keep (default: 5).
        log_format: Custom log format string (default: None, uses predefined format).
        date_format: Custom date format string (default: None, uses predefined format).
    """
    try:
        if isinstance(log_dir, str):
            log_dir = Path(log_dir)
        
        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set default formats if not provided
        if log_format is None:
            log_format = (
                "%(asctime)s [%(levelname)8s] "
                "%(name)s:%(lineno)d - %(message)s"
            )
        if date_format is None:
            date_format = "%Y-%m-%d %H:%M:%S"
        
        # Create formatters
        formatter = logging.Formatter(log_format, date_format)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Create file handler
        log_file = log_dir / "tb_scout.log"
        file_handler = SafeRotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Log initial message
        logging.info("Logging initialized: console=%s, file=%s", 
                    logging.getLevelName(console_level),
                    logging.getLevelName(file_level))
                    
    except Exception as e:
        # Write error to stderr without logging
        sys.stderr.write(f"Error setting up logging: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    This is a convenience function that ensures consistent logger naming
    throughout the application.
    
    Args:
        name: Name of the logger, typically __name__ of the module.
    
    Returns:
        logging.Logger: Logger instance.
    """
    return logging.getLogger(name) 