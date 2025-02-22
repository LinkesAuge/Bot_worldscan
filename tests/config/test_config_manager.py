"""Tests for configuration management system."""

import pytest
from pathlib import Path
from scout.config import (
    ConfigManager,
    WindowConfig,
    CaptureConfig,
    OCRConfig,
    PatternConfig,
    SoundConfig,
    DebugConfig
)

@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "test_config.ini"
    return config_path

@pytest.fixture
def config_manager(config_file):
    """Create a ConfigManager instance with test config."""
    manager = ConfigManager(str(config_file))
    return manager

def test_config_manager_initialization(config_manager, config_file):
    """Test ConfigManager initialization."""
    assert config_manager.config_path == config_file
    assert config_file.exists()

def test_config_manager_default_config(config_manager):
    """Test default configuration creation."""
    # Test window config
    window_config = config_manager.get_window_config()
    assert isinstance(window_config, WindowConfig)
    assert window_config.standalone_priority
    assert window_config.browser_detection
    assert window_config.update_interval == 1000

    # Test capture config
    capture_config = config_manager.get_capture_config()
    assert isinstance(capture_config, CaptureConfig)
    assert capture_config.debug_screenshots
    assert capture_config.debug_dir == "debug_screenshots"
    assert capture_config.save_failures

    # Test OCR config
    ocr_config = config_manager.get_ocr_config()
    assert isinstance(ocr_config, OCRConfig)
    assert ocr_config.language == "eng"
    assert ocr_config.psm_mode == 7
    assert ocr_config.oem_mode == 3
    assert ocr_config.char_whitelist == "0123456789"

    # Test pattern config
    pattern_config = config_manager.get_pattern_config()
    assert isinstance(pattern_config, PatternConfig)
    assert pattern_config.template_dir == "images"
    assert pattern_config.confidence_threshold == 0.8
    assert pattern_config.save_matches

    # Test sound config
    sound_config = config_manager.get_sound_config()
    assert isinstance(sound_config, SoundConfig)
    assert sound_config.enabled
    assert sound_config.cooldown == 5.0
    assert sound_config.sounds_dir == "sounds"

    # Test debug config
    debug_config = config_manager.get_debug_config()
    assert isinstance(debug_config, DebugConfig)
    assert debug_config.enabled
    assert debug_config.log_level == "DEBUG"
    assert debug_config.log_dir == "logs"
    assert debug_config.update_interval == 1000

def test_config_manager_update_section(config_manager):
    """Test updating configuration sections."""
    # Update window section
    config_manager.update_section("Window", {
        "standalone_priority": False,
        "browser_detection": False,
        "update_interval": 2000
    })
    
    window_config = config_manager.get_window_config()
    assert not window_config.standalone_priority
    assert not window_config.browser_detection
    assert window_config.update_interval == 2000

    # Update OCR section
    config_manager.update_section("OCR", {
        "language": "deu",
        "psm_mode": 6,
        "oem_mode": 2,
        "char_whitelist": "abcdefghijklmnopqrstuvwxyz"
    })
    
    ocr_config = config_manager.get_ocr_config()
    assert ocr_config.language == "deu"
    assert ocr_config.psm_mode == 6
    assert ocr_config.oem_mode == 2
    assert ocr_config.char_whitelist == "abcdefghijklmnopqrstuvwxyz"

def test_config_manager_save_load(config_manager, config_file):
    """Test saving and loading configuration."""
    # Update some settings
    config_manager.update_section("Window", {
        "standalone_priority": False
    })
    
    # Create new manager with same file
    new_manager = ConfigManager(str(config_file))
    window_config = new_manager.get_window_config()
    assert not window_config.standalone_priority

def test_config_manager_invalid_section(config_manager):
    """Test handling invalid section updates."""
    config_manager.update_section("InvalidSection", {
        "some_setting": "value"
    })
    
    # Section should be created
    assert "InvalidSection" in config_manager.config.sections()
    assert config_manager.config["InvalidSection"]["some_setting"] == "value"

def test_config_manager_debug_info(config_manager):
    """Test getting debug information."""
    debug_info = config_manager.get_debug_info()
    
    assert "Window" in debug_info
    assert "Capture" in debug_info
    assert "OCR" in debug_info
    assert "Pattern" in debug_info
    assert "Sound" in debug_info
    assert "Debug" in debug_info
    
    # Check some values
    assert debug_info["Window"]["standalone_priority"] == "true"
    assert debug_info["OCR"]["language"] == "eng"
    assert debug_info["Pattern"]["confidence_threshold"] == "0.8" 