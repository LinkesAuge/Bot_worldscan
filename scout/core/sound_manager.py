"""Audio feedback system for game events."""

from typing import Optional, Dict, Any
from pathlib import Path
import pygame
import time
import logging
import os

logger = logging.getLogger(__name__)

class SoundManager:
    """
    Manages audio alerts for important game events.
    
    This class provides audio feedback when significant events occur,
    such as pattern matches being found. It includes features for:
    - Loading and playing sound files
    - Controlling sound frequency with cooldowns
    - Enabling/disabling sound alerts
    - Managing sound resources
    
    The sound system helps users stay aware of detections without
    having to constantly watch the screen. It includes cooldown
    functionality to prevent sound spam.
    
    Attributes:
        enabled: Whether sound alerts are enabled
        cooldown: Minimum seconds between sound plays
        sounds_dir: Directory containing sound files
    """
    
    def __init__(self, sounds_dir: Optional[str] = None, cooldown: float = 5.0) -> None:
        """
        Initialize the sound system with specified settings.
        
        Sets up the pygame audio system and loads sound files from the
        specified directory. Includes cooldown management to prevent
        sounds from playing too frequently.
        
        Args:
            sounds_dir: Directory containing .wav sound files (default: "scout/sounds")
            cooldown: Minimum seconds between sound plays
        """
        pygame.mixer.init()
        
        if sounds_dir is None:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            sounds_dir = str(current_dir.parent.parent / "sounds")
            
        self.sounds_dir = Path(sounds_dir)
        self.cooldown = cooldown
        self.last_play_time = 0.0
        self.enabled = True
        self.sound: Optional[pygame.mixer.Sound] = None
        
        self.load_sound()
        logger.debug("Sound manager initialized")
    
    def load_sound(self) -> None:
        """
        Load the alert sound file from disk.
        
        Searches the sounds directory for .wav files and loads the first
        one found. Logs warnings if no sound files are available or if
        loading fails.
        """
        try:
            if not self.sounds_dir.exists():
                logger.warning(f"Sounds directory not found: {self.sounds_dir}")
                return
            
            sound_files = list(self.sounds_dir.glob("*.wav"))
            if not sound_files:
                logger.warning("No .wav files found in sounds directory")
                return
            
            self.sound = pygame.mixer.Sound(str(sound_files[0]))
            logger.debug(f"Loaded sound: {sound_files[0]}")
            
        except Exception as e:
            logger.error(f"Error loading sound: {str(e)}", exc_info=True)
    
    def play_if_ready(self) -> None:
        """
        Play sound if enabled and cooldown has elapsed.
        
        This method checks if sound alerts are enabled and if enough time
        has passed since the last sound was played (based on cooldown).
        If both conditions are met, plays the alert sound.
        """
        if not self.enabled or not self.sound:
            return
            
        current_time = time.time()
        if current_time - self.last_play_time >= self.cooldown:
            try:
                self.sound.play()
                self.last_play_time = current_time
                logger.debug("Played alert sound")
            except Exception as e:
                logger.error(f"Error playing sound: {str(e)}", exc_info=True)
    
    def toggle(self) -> None:
        """
        Toggle sound on/off.
        
        Switches the enabled state between True and False, effectively
        turning sound alerts on or off.
        """
        self.enabled = not self.enabled
        logger.info(f"Sound {'enabled' if self.enabled else 'disabled'}")
        
    def get_debug_info(self) -> Dict[str, Any]:
        """Get current sound system state for debugging."""
        return {
            "enabled": self.enabled,
            "cooldown": self.cooldown,
            "last_play": self.last_play_time,
            "sound_loaded": self.sound is not None,
            "sounds_dir": str(self.sounds_dir)
        } 