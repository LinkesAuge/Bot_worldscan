from typing import Optional
from pathlib import Path
import pygame
import time
import logging

logger = logging.getLogger(__name__)

class SoundManager:
    """Manages sound playback for pattern matching alerts."""
    
    def __init__(self, sounds_dir: str = "sounds", cooldown: float = 5.0) -> None:
        """
        Initialize the sound manager.
        
        Args:
            sounds_dir: Directory containing sound files
            cooldown: Minimum time between sounds in seconds
        """
        pygame.mixer.init()
        self.sounds_dir = Path(sounds_dir)
        self.cooldown = cooldown
        self.last_play_time = 0.0
        self.enabled = True
        self.sound: Optional[pygame.mixer.Sound] = None
        
        self.load_sound()
    
    def load_sound(self) -> None:
        """Load the alert sound file."""
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
        """Play sound if enabled and cooldown has elapsed."""
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
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        logger.info(f"Sound {'enabled' if self.enabled else 'disabled'}") 