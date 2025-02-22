"""Tests for the logging module."""

import logging
import pytest
from pathlib import Path
from scout.core.logging import setup_logging, get_logger

@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for log files.
    
    Args:
        tmp_path: Pytest fixture providing a temporary directory.
        
    Returns:
        Path: Path to temporary log directory.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

def test_setup_logging_default_config(temp_log_dir: Path) -> None:
    """Test setup_logging with default configuration.
    
    Args:
        temp_log_dir: Temporary directory for log files.
    """
    # Setup logging with default config
    setup_logging(temp_log_dir)
    
    # Check that log file was created
    log_file = temp_log_dir / "tb_scout.log"
    assert log_file.exists()
    
    # Check root logger configuration
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    
    # Check handlers
    assert len(root_logger.handlers) == 2
    
    # Check console handler
    console_handler = root_logger.handlers[0]
    assert isinstance(console_handler, logging.StreamHandler)
    assert console_handler.level == logging.INFO
    
    # Check file handler
    file_handler = root_logger.handlers[1]
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler)
    assert file_handler.level == logging.DEBUG
    assert file_handler.maxBytes == 10 * 1024 * 1024  # 10MB
    assert file_handler.backupCount == 5

def test_setup_logging_custom_config(temp_log_dir: Path) -> None:
    """Test setup_logging with custom configuration.
    
    Args:
        temp_log_dir: Temporary directory for log files.
    """
    # Setup logging with custom config
    setup_logging(
        log_dir=temp_log_dir,
        console_level=logging.WARNING,
        file_level=logging.ERROR,
        max_bytes=5 * 1024 * 1024,  # 5MB
        backup_count=3,
        log_format="%(levelname)s - %(message)s",
        date_format="%H:%M:%S"
    )
    
    # Check root logger configuration
    root_logger = logging.getLogger()
    
    # Check handlers
    console_handler = root_logger.handlers[0]
    assert console_handler.level == logging.WARNING
    
    file_handler = root_logger.handlers[1]
    assert file_handler.level == logging.ERROR
    assert file_handler.maxBytes == 5 * 1024 * 1024
    assert file_handler.backupCount == 3
    
    # Check formatter
    assert file_handler.formatter._fmt == "%(levelname)s - %(message)s"
    assert file_handler.formatter.datefmt == "%H:%M:%S"

def test_setup_logging_string_path(tmp_path: Path) -> None:
    """Test setup_logging with string path instead of Path object.
    
    Args:
        tmp_path: Temporary directory for log files.
    """
    log_dir = str(tmp_path / "logs")
    setup_logging(log_dir)
    
    # Check that log directory was created
    assert Path(log_dir).exists()
    assert (Path(log_dir) / "tb_scout.log").exists()

def test_get_logger() -> None:
    """Test get_logger function."""
    # Get logger with test name
    logger = get_logger("test_logger")
    
    # Check logger properties
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    
    # Get same logger again and verify it's the same instance
    logger2 = get_logger("test_logger")
    assert logger is logger2  # Should return same instance

def test_logging_output(temp_log_dir: Path, capsys: pytest.CaptureFixture) -> None:
    """Test actual logging output with different levels.
    
    Args:
        temp_log_dir: Temporary directory for log files.
        capsys: Pytest fixture for capturing stdout/stderr.
    """
    # Setup logging with DEBUG level for console to capture all messages
    setup_logging(temp_log_dir, console_level=logging.DEBUG)
    logger = get_logger("test_logger")
    
    # Log messages at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Get captured output
    captured = capsys.readouterr()
    stderr = captured.err
    
    # Check that each message appears in stderr
    assert "Debug message" in stderr
    assert "Info message" in stderr
    assert "Warning message" in stderr
    assert "Error message" in stderr
    
    # Check file output (should contain all levels)
    log_file = temp_log_dir / "tb_scout.log"
    log_content = log_file.read_text()
    assert "Debug message" in log_content
    assert "Info message" in log_content
    assert "Warning message" in log_content
    assert "Error message" in log_content 