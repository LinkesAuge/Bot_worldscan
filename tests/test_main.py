"""Tests for the main entry point module."""

import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from scout.__main__ import (
    init_logging,
    init_settings,
    init_config,
    run_app,
    main,
)
from scout import (
    APP_NAME,
    APP_DESCRIPTION,
    APP_ORGANIZATION,
    APP_DOMAIN,
)

@pytest.fixture
def mock_qapp() -> MagicMock:
    """Create a mock QApplication instance.
    
    Returns:
        MagicMock: Mock QApplication instance.
    """
    with patch("scout.__main__.QApplication") as mock:
        instance = mock.return_value
        instance.exec.return_value = 0
        yield instance

@pytest.fixture
def mock_window() -> MagicMock:
    """Create a mock MainWindow instance.
    
    Returns:
        MagicMock: Mock MainWindow instance.
    """
    with patch("scout.__main__.MainWindow") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock ConfigManager instance.
    
    Returns:
        MagicMock: Mock ConfigManager instance.
    """
    with patch("scout.__main__.ConfigManager") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_settings() -> MagicMock:
    """Create a mock QSettings instance.
    
    Returns:
        MagicMock: Mock QSettings instance.
    """
    with patch("scout.__main__.QSettings") as mock:
        instance = mock.return_value
        yield instance

def test_init_logging(tmp_path: Path) -> None:
    """Test initialization of logging.
    
    Args:
        tmp_path: Pytest fixture providing temporary directory.
    """
    log_dir = tmp_path / "logs"
    with patch("scout.__main__.LOG_DIR", str(log_dir)):
        init_logging()
        assert log_dir.exists()
        assert log_dir.is_dir()
        assert any(log_dir.iterdir())

def test_init_settings() -> None:
    """Test initialization of application settings."""
    settings = init_settings()
    assert isinstance(settings, QSettings)
    assert settings.organizationName() == APP_ORGANIZATION
    assert settings.applicationName() == APP_NAME

def test_init_config() -> None:
    """Test initialization of configuration manager."""
    with patch("scout.__main__.CONFIG_FILE", "test_config.ini"):
        config = init_config()
        assert config.config_file.name == "test_config.ini"

def test_run_app(mock_qapp: MagicMock, mock_window: MagicMock) -> None:
    """Test running the application.
    
    Args:
        mock_qapp: Mock QApplication instance.
        mock_window: Mock MainWindow instance.
    """
    exit_code = run_app(mock_qapp, mock_window)
    assert mock_window.show.called
    assert mock_qapp.exec.called
    assert exit_code == 0

def test_main_normal_execution(
    mock_qapp,
    mock_window,
    mock_config,
    mock_settings,
    tmp_path
):
    """Test normal execution of main function.
    
    Args:
        mock_qapp: Mock QApplication instance.
        mock_window: Mock MainWindow instance.
        mock_config: Mock ConfigManager instance.
        mock_settings: Mock QSettings instance.
        tmp_path: Pytest fixture providing temporary directory.
    """
    log_dir = tmp_path / "logs"
    
    with patch("scout.__main__.LOG_DIR", str(log_dir)), \
         patch("scout.__main__.sys.exit") as mock_exit, \
         patch("scout.__main__.MainWindow", return_value=mock_window):
        
        main(["test"])
        
        # Check application setup
        assert mock_qapp.setApplicationName.called_with(APP_NAME)
        assert mock_qapp.setApplicationDisplayName.called_with(APP_DESCRIPTION)
        assert mock_qapp.setOrganizationName.called_with(APP_ORGANIZATION)
        assert mock_qapp.setOrganizationDomain.called_with(APP_DOMAIN)
        
        # Check window creation and execution
        assert mock_window.show.called
        assert mock_qapp.exec.called
        assert mock_exit.called_with(0)

def test_main_exception_handling(
    mock_qapp: MagicMock,
    mock_window: MagicMock,
    tmp_path: Path,
) -> None:
    """Test exception handling in main function.
    
    Args:
        mock_qapp: Mock QApplication instance.
        mock_window: Mock MainWindow instance.
        tmp_path: Pytest fixture providing temporary directory.
    """
    log_dir = tmp_path / "logs"
    mock_qapp.exec.side_effect = Exception("Test error")
    
    with patch("scout.__main__.LOG_DIR", str(log_dir)), \
         patch("scout.__main__.sys.exit") as mock_exit:
        main(["test"])
        
        # Check error handling
        mock_exit.assert_called_with(1)
        
        # Check error was logged
        log_file = log_dir / "tb_scout.log"
        log_content = log_file.read_text()
        assert "Test error" in log_content
        assert "Unhandled exception in main" in log_content

def test_main_no_args(
    mock_qapp: MagicMock,
    mock_window: MagicMock,
    tmp_path: Path,
) -> None:
    """Test main function with no arguments.
    
    Args:
        mock_qapp: Mock QApplication instance.
        mock_window: Mock MainWindow instance.
        tmp_path: Pytest fixture providing temporary directory.
    """
    log_dir = tmp_path / "logs"
    with patch("scout.__main__.LOG_DIR", str(log_dir)), \
         patch("scout.__main__.sys.exit") as mock_exit, \
         patch("scout.__main__.sys.argv", ["test"]):
        main()
        assert mock_qapp.exec.called
        assert mock_exit.called_with(0) 