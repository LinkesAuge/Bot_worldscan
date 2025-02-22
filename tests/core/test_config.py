"""Tests for the configuration manager."""

import os
from pathlib import Path
import pytest
from scout.core.config import ConfigManager

@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a temporary config file.
    
    Args:
        tmp_path: Pytest fixture providing a temporary directory.
        
    Returns:
        Path: Path to temporary config file.
    """
    return tmp_path / "config.ini"

@pytest.fixture
def config_manager(config_file: Path) -> ConfigManager:
    """Create a ConfigManager instance.
    
    Args:
        config_file: Path to temporary config file.
        
    Returns:
        ConfigManager: Instance with default configuration.
    """
    return ConfigManager(config_file)

def test_config_manager_init(config_file: Path) -> None:
    """Test ConfigManager initialization.
    
    Args:
        config_file: Path to temporary config file.
    """
    # Initialize with string path
    manager1 = ConfigManager(str(config_file))
    assert manager1.config_file == config_file
    assert config_file.exists()
    
    # Initialize with Path object
    manager2 = ConfigManager(config_file)
    assert manager2.config_file == config_file

def test_config_manager_default_config(config_manager: ConfigManager) -> None:
    """Test default configuration values.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Check Window section
    assert config_manager.get_bool("Window", "standalone_priority") is True
    assert config_manager.get_bool("Window", "browser_detection") is True
    assert config_manager.get_int("Window", "update_interval") == 1000
    
    # Check Capture section
    assert config_manager.get_bool("Capture", "debug_screenshots") is True
    assert config_manager.get_str("Capture", "debug_dir") == "debug_screenshots"
    assert config_manager.get_bool("Capture", "save_failures") is True
    
    # Check OCR section
    assert config_manager.get_str("OCR", "tesseract_path") == ""
    assert config_manager.get_str("OCR", "language") == "eng"
    assert config_manager.get_str("OCR", "psm_mode") == "7"
    assert config_manager.get_str("OCR", "oem_mode") == "3"
    assert config_manager.get_str("OCR", "char_whitelist") == "0123456789"
    
    # Check Pattern section
    assert config_manager.get_str("Pattern", "template_dir") == "images"
    assert config_manager.get_float("Pattern", "confidence_threshold") == 0.8
    assert config_manager.get_bool("Pattern", "save_matches") is True
    
    # Check Sound section
    assert config_manager.get_bool("Sound", "enabled") is True
    assert config_manager.get_float("Sound", "cooldown") == 5.0
    assert config_manager.get_str("Sound", "sounds_dir") == "sounds"
    
    # Check Debug section
    assert config_manager.get_bool("Debug", "enabled") is True
    assert config_manager.get_str("Debug", "log_level") == "DEBUG"
    assert config_manager.get_str("Debug", "log_dir") == "logs"
    assert config_manager.get_int("Debug", "update_interval") == 1000

def test_config_manager_set_get(config_manager: ConfigManager) -> None:
    """Test setting and getting configuration values.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Test string values
    config_manager.set("Test", "string", "value")
    assert config_manager.get_str("Test", "string") == "value"
    assert config_manager.get_str("Test", "nonexistent", "default") == "default"
    
    # Test integer values
    config_manager.set("Test", "int", 42)
    assert config_manager.get_int("Test", "int") == 42
    assert config_manager.get_int("Test", "nonexistent", 0) == 0
    
    # Test float values
    config_manager.set("Test", "float", 3.14)
    assert config_manager.get_float("Test", "float") == 3.14
    assert config_manager.get_float("Test", "nonexistent", 0.0) == 0.0
    
    # Test boolean values
    config_manager.set("Test", "bool", True)
    assert config_manager.get_bool("Test", "bool") is True
    assert config_manager.get_bool("Test", "nonexistent", False) is False

def test_config_manager_path_handling(config_manager: ConfigManager) -> None:
    """Test path handling in configuration.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Test relative path
    config_manager.set("Test", "rel_path", "test_dir")
    path = config_manager.get_path("Test", "rel_path")
    assert path.is_absolute()
    assert path == (config_manager.config_file.parent / "test_dir").resolve()
    
    # Test absolute path
    abs_path = config_manager.config_file.parent / "abs_test_dir"
    config_manager.set("Test", "abs_path", str(abs_path))
    path = config_manager.get_path("Test", "abs_path")
    assert path.is_absolute()
    assert path == abs_path.resolve()
    
    # Test empty path
    config_manager.set("Test", "empty_path", "")
    path = config_manager.get_path("Test", "empty_path")
    assert path == Path()
    
    # Test path with fallback
    path = config_manager.get_path("Test", "nonexistent", "fallback")
    assert path == (config_manager.config_file.parent / "fallback").resolve()

def test_config_manager_save_load(config_manager: ConfigManager) -> None:
    """Test saving and loading configuration.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Set some values
    config_manager.set("Test", "string", "value")
    config_manager.set("Test", "int", 42)
    config_manager.set("Test", "float", 3.14)
    config_manager.set("Test", "bool", True)
    
    # Save configuration
    config_manager.save()
    
    # Create new manager and load configuration
    new_manager = ConfigManager(config_manager.config_file)
    
    # Check values were preserved
    assert new_manager.get_str("Test", "string") == "value"
    assert new_manager.get_int("Test", "int") == 42
    assert new_manager.get_float("Test", "float") == 3.14
    assert new_manager.get_bool("Test", "bool") is True

def test_config_manager_section_handling(config_manager: ConfigManager) -> None:
    """Test section handling in configuration.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Test has_section
    assert config_manager.has_section("Window")
    assert not config_manager.has_section("NonexistentSection")
    
    # Test has_option
    assert config_manager.has_option("Window", "update_interval")
    assert not config_manager.has_option("Window", "nonexistent")
    assert not config_manager.has_option("NonexistentSection", "option")
    
    # Test adding new section
    config_manager.set("NewSection", "option", "value")
    assert config_manager.has_section("NewSection")
    assert config_manager.has_option("NewSection", "option")
    assert config_manager.get("NewSection", "option") == "value"

def test_config_manager_generic_get(config_manager: ConfigManager) -> None:
    """Test generic get method.
    
    Args:
        config_manager: ConfigManager instance.
    """
    # Test with existing value
    assert config_manager.get("Window", "update_interval") == "1000"
    
    # Test with fallback
    assert config_manager.get("Window", "nonexistent", "default") == "default"
    
    # Test with nonexistent section
    assert config_manager.get("NonexistentSection", "option", "default") == "default"

def test_config_manager_load_existing(tmp_path):
    """Test loading an existing configuration file."""
    config_file = tmp_path / "test_config.ini"
    test_path = tmp_path / "test" / "path"
    
    # Create test config file
    with open(config_file, "w") as f:
        f.write("[Test]\n")
        f.write("string_value = test\n")
        f.write("int_value = 42\n")
        f.write("float_value = 3.14\n")
        f.write("bool_value = true\n")
        f.write(f"path_value = {test_path}\n")
    
    manager = ConfigManager(config_file)
    
    assert manager.get_str("Test", "string_value") == "test"
    assert manager.get_int("Test", "int_value") == 42
    assert manager.get_float("Test", "float_value") == 3.14
    assert manager.get_bool("Test", "bool_value") is True
    
    # Test path value
    result_path = manager.get_path("Test", "path_value")
    assert result_path.resolve() == test_path.resolve()

def test_config_manager_save(config_manager: ConfigManager) -> None:
    """Test saving configuration changes.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    config_manager.set("Test", "new_value", "test")
    config_manager.save()
    
    # Create new manager to verify saved values
    new_manager = ConfigManager(config_manager.config_file)
    assert new_manager.get_str("Test", "new_value") == "test"

def test_config_manager_get_with_fallback():
    """Test getting values with fallback."""
    config_manager = ConfigManager("test_config.ini")
    
    # Test getting string with fallback
    assert config_manager.get_str("NonExistent", "option", fallback="default") == "default"
    
    # Test getting int with fallback
    assert config_manager.get_int("NonExistent", "option", fallback=42) == 42
    
    # Test getting float with fallback
    assert config_manager.get_float("NonExistent", "option", fallback=3.14) == 3.14
    
    # Test getting bool with fallback
    assert config_manager.get_bool("NonExistent", "option", fallback=True) is True
    
    # Test getting path with fallback
    fallback_path = Path("/default").resolve()
    result_path = config_manager.get_path("NonExistent", "option", fallback=str(fallback_path))
    assert result_path.resolve() == fallback_path

def test_config_manager_relative_paths(config_manager: ConfigManager) -> None:
    """Test handling of relative paths.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    config_manager.set("Test", "rel_path", "relative/path")
    expected_path = (config_manager.config_file.parent / "relative/path").resolve()
    assert config_manager.get_path("Test", "rel_path") == expected_path

def test_config_manager_empty_path(config_manager: ConfigManager) -> None:
    """Test handling of empty paths.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    config_manager.set("Test", "empty_path", "")
    assert config_manager.get_path("Test", "empty_path") == Path()

def test_config_manager_has_option(config_manager: ConfigManager) -> None:
    """Test checking for option existence.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    config_manager.set("Test", "option", "value")
    assert config_manager.has_option("Test", "option") is True
    assert config_manager.has_option("Test", "nonexistent") is False

def test_config_manager_has_section(config_manager: ConfigManager) -> None:
    """Test checking for section existence.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    config_manager.set("Test", "option", "value")
    assert config_manager.has_section("Test") is True
    assert config_manager.has_section("NonExistent") is False

def test_config_manager_default_values(config_manager: ConfigManager) -> None:
    """Test default configuration values.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    assert config_manager.get_bool("Window", "standalone_priority") is True
    assert config_manager.get_bool("Window", "browser_detection") is True
    assert config_manager.get_int("Window", "update_interval") == 1000
    
    assert config_manager.get_bool("Capture", "debug_screenshots") is True
    assert config_manager.get_str("Capture", "debug_dir") == "debug_screenshots"
    assert config_manager.get_bool("Capture", "save_failures") is True
    
    assert config_manager.get_str("OCR", "language") == "eng"
    assert config_manager.get_int("OCR", "psm_mode") == 7
    assert config_manager.get_int("OCR", "oem_mode") == 3
    assert config_manager.get_str("OCR", "char_whitelist") == "0123456789"
    
    assert config_manager.get_str("Pattern", "template_dir") == "images"
    assert config_manager.get_float("Pattern", "confidence_threshold") == 0.8
    assert config_manager.get_bool("Pattern", "save_matches") is True
    
    assert config_manager.get_bool("Sound", "enabled") is True
    assert config_manager.get_float("Sound", "cooldown") == 5.0
    assert config_manager.get_str("Sound", "sounds_dir") == "sounds"
    
    assert config_manager.get_bool("Debug", "enabled") is True
    assert config_manager.get_str("Debug", "log_level") == "DEBUG"
    assert config_manager.get_str("Debug", "log_dir") == "logs"
    assert config_manager.get_int("Debug", "update_interval") == 1000

def test_config_manager_absolute_paths(config_manager: ConfigManager) -> None:
    """Test handling of absolute paths.
    
    Args:
        config_manager: ConfigManager instance for testing.
    """
    # Get an absolute path
    abs_path = Path(__file__).resolve()
    config_manager.set("Test", "abs_path", str(abs_path))
    
    # Get path from config
    result_path = config_manager.get_path("Test", "abs_path")
    
    # Should return the same absolute path
    assert result_path == abs_path 