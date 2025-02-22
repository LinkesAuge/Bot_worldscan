"""Tests for sound system."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import pygame
from scout.core import SoundManager
from pytest_mock import MockerFixture

@pytest.fixture
def mock_pygame():
    """Mock pygame for testing."""
    with patch("pygame.mixer") as mock_mixer:
        yield mock_mixer

@pytest.fixture
def mock_sound_file(tmp_path):
    """Create a mock sound file for testing."""
    sound_dir = tmp_path / "sounds"
    sound_dir.mkdir()
    sound_file = sound_dir / "alert.wav"
    sound_file.touch()
    return sound_dir

def test_sound_manager_initialization(mock_pygame):
    """Test SoundManager initialization."""
    manager = SoundManager()
    assert manager.enabled
    assert manager.cooldown == 5.0
    assert manager.last_play_time == 0.0
    mock_pygame.init.assert_called_once()

def test_sound_manager_with_custom_directory(mock_pygame, mock_sound_file):
    """Test SoundManager with custom sounds directory."""
    manager = SoundManager(sounds_dir=str(mock_sound_file))
    assert manager.sounds_dir == mock_sound_file
    assert manager.enabled
    mock_pygame.init.assert_called_once()

def test_sound_manager_load_sound(mock_pygame, mock_sound_file):
    """Test loading sound file."""
    mock_sound = MagicMock()
    mock_pygame.Sound.return_value = mock_sound
    
    manager = SoundManager(sounds_dir=str(mock_sound_file))
    assert manager.sound == mock_sound
    mock_pygame.Sound.assert_called_once_with(str(mock_sound_file / "alert.wav"))

def test_sound_manager_play_if_ready(mock_pygame, mock_sound_file):
    """Test playing sound with cooldown."""
    mock_sound = MagicMock()
    mock_pygame.Sound.return_value = mock_sound
    
    manager = SoundManager(sounds_dir=str(mock_sound_file), cooldown=0.1)
    
    # First play should work
    manager.play_if_ready()
    mock_sound.play.assert_called_once()
    
    # Second play should be blocked by cooldown
    mock_sound.play.reset_mock()
    manager.play_if_ready()
    mock_sound.play.assert_not_called()

def test_sound_manager_toggle(mock_pygame):
    """Test toggling sound on/off."""
    manager = SoundManager()
    assert manager.enabled
    
    manager.toggle()
    assert not manager.enabled
    
    manager.toggle()
    assert manager.enabled

def test_sound_manager_debug_info(mock_pygame, mock_sound_file):
    """Test getting debug information."""
    manager = SoundManager(sounds_dir=str(mock_sound_file))
    debug_info = manager.get_debug_info()
    
    assert debug_info["enabled"]
    assert debug_info["cooldown"] == 5.0
    assert debug_info["last_play"] == 0.0
    assert debug_info["sound_loaded"]
    assert debug_info["sounds_dir"] == str(mock_sound_file)

def test_sound_manager_no_sound_directory(mock_pygame, tmp_path):
    """Test behavior when sound directory doesn't exist."""
    nonexistent_dir = tmp_path / "nonexistent"
    manager = SoundManager(sounds_dir=str(nonexistent_dir))
    assert manager.sound is None

def test_sound_manager_empty_sound_directory(mock_pygame, tmp_path):
    """Test behavior with empty sound directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    manager = SoundManager(sounds_dir=str(empty_dir))
    assert manager.sound is None

def test_sound_manager_play_error(mock_pygame, mock_sound_file):
    """Test handling play errors."""
    # Setup mock sound
    mock_sound = MagicMock()
    mock_sound.play.side_effect = Exception("Test error")
    mock_pygame.Sound.return_value = mock_sound
    
    # Create manager
    manager = SoundManager(sounds_dir=str(mock_sound_file))
    
    # Try to play sound
    manager.play_if_ready()  # Should handle error gracefully 

def test_sound_manager_play_if_ready_edge_cases(tmp_path: Path) -> None:
    """Test edge cases in play_if_ready method.
    
    Args:
        tmp_path: Temporary directory path for testing.
    """
    # Test when sound is not loaded
    manager = SoundManager(tmp_path)
    manager.play_if_ready()  # Should handle gracefully when sound not loaded
    
    # Test when sound is disabled
    sound_dir = tmp_path / "sounds"
    sound_dir.mkdir()
    sound_file = sound_dir / "test.wav"
    sound_file.write_bytes(b"dummy wav data")
    
    manager = SoundManager(tmp_path)
    manager.enabled = False
    manager.play_if_ready()  # Should handle gracefully when sound is disabled 

def test_sound_manager_load_error(tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    """Test error handling when loading a corrupted sound file.
    
    Args:
        tmp_path: Temporary directory path for testing.
        mocker: Pytest mocker fixture.
        caplog: Pytest log capture fixture.
    """
    # Create a sound file
    sound_dir = tmp_path / "sounds"
    sound_dir.mkdir()
    sound_file = sound_dir / "test.wav"
    sound_file.write_bytes(b"dummy wav data")
    
    # Mock list(glob()) to return our test file
    mocker.patch("pathlib.Path.glob", return_value=[sound_file])
    
    # Mock pygame.mixer.Sound to raise an exception
    mock_sound = mocker.patch("pygame.mixer.Sound", side_effect=Exception("Test loading error"))
    
    # Loading should handle the error gracefully
    manager = SoundManager(tmp_path)
    assert manager.sound is None  # Sound should not be loaded due to error
    
    # Verify error was logged
    assert "Error loading sound: Test loading error" in caplog.text 