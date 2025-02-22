"""Configuration management system."""

from typing import Dict, Any, Optional
import logging
import configparser
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WindowConfig:
    """Window tracking configuration."""
    standalone_priority: bool = True
    browser_detection: bool = True
    update_interval: int = 1000  # ms

@dataclass
class CaptureConfig:
    """Screen capture configuration."""
    debug_screenshots: bool = True
    debug_dir: str = "debug_screenshots"
    save_failures: bool = True

@dataclass
class OCRConfig:
    """OCR processing configuration."""
    tesseract_path: Optional[str] = None
    language: str = "eng"
    psm_mode: int = 7
    oem_mode: int = 3
    char_whitelist: str = "0123456789"

@dataclass
class PatternConfig:
    """Pattern matching configuration."""
    template_dir: str = "images"
    confidence_threshold: float = 0.8
    save_matches: bool = True

@dataclass
class SoundConfig:
    """Sound system configuration."""
    enabled: bool = True
    cooldown: float = 5.0
    sounds_dir: str = "sounds"

@dataclass
class DebugConfig:
    """Debug system configuration."""
    enabled: bool = True
    log_level: str = "DEBUG"
    log_dir: str = "logs"
    update_interval: int = 1000  # ms

class ConfigManager:
    """
    Manages application configuration.
    
    This class provides:
    - Configuration file loading/saving
    - Default configuration generation
    - Configuration validation
    - Type-safe configuration access
    
    The configuration is stored in an INI file format with sections
    for different components of the application.
    """
    
    def __init__(self, config_path: str = "config.ini") -> None:
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        
        # Load or create config
        if self.config_path.exists():
            self.load_config()
        else:
            self.create_default_config()
            
        logger.debug("Configuration manager initialized")
        
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            self.config.read(self.config_path)
            logger.info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.create_default_config()
            
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            logger.info(f"Saved configuration to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def create_default_config(self) -> None:
        """Create default configuration."""
        # Window section
        self.config["Window"] = {
            "standalone_priority": "true",
            "browser_detection": "true",
            "update_interval": "1000"
        }
        
        # Capture section
        self.config["Capture"] = {
            "debug_screenshots": "true",
            "debug_dir": "debug_screenshots",
            "save_failures": "true"
        }
        
        # OCR section
        self.config["OCR"] = {
            "tesseract_path": "",
            "language": "eng",
            "psm_mode": "7",
            "oem_mode": "3",
            "char_whitelist": "0123456789"
        }
        
        # Pattern section
        self.config["Pattern"] = {
            "template_dir": "images",
            "confidence_threshold": "0.8",
            "save_matches": "true"
        }
        
        # Sound section
        self.config["Sound"] = {
            "enabled": "true",
            "cooldown": "5.0",
            "sounds_dir": "sounds"
        }
        
        # Debug section
        self.config["Debug"] = {
            "enabled": "true",
            "log_level": "DEBUG",
            "log_dir": "logs",
            "update_interval": "1000"
        }
        
        # Save default config
        self.save_config()
        logger.info("Created default configuration")
        
    def get_window_config(self) -> WindowConfig:
        """Get window tracking configuration."""
        section = self.config["Window"]
        return WindowConfig(
            standalone_priority=section.getboolean("standalone_priority"),
            browser_detection=section.getboolean("browser_detection"),
            update_interval=section.getint("update_interval")
        )
        
    def get_capture_config(self) -> CaptureConfig:
        """Get screen capture configuration."""
        section = self.config["Capture"]
        return CaptureConfig(
            debug_screenshots=section.getboolean("debug_screenshots"),
            debug_dir=section.get("debug_dir"),
            save_failures=section.getboolean("save_failures")
        )
        
    def get_ocr_config(self) -> OCRConfig:
        """Get OCR processing configuration."""
        section = self.config["OCR"]
        return OCRConfig(
            tesseract_path=section.get("tesseract_path") or None,
            language=section.get("language"),
            psm_mode=section.getint("psm_mode"),
            oem_mode=section.getint("oem_mode"),
            char_whitelist=section.get("char_whitelist")
        )
        
    def get_pattern_config(self) -> PatternConfig:
        """Get pattern matching configuration."""
        section = self.config["Pattern"]
        return PatternConfig(
            template_dir=section.get("template_dir"),
            confidence_threshold=section.getfloat("confidence_threshold"),
            save_matches=section.getboolean("save_matches")
        )
        
    def get_sound_config(self) -> SoundConfig:
        """Get sound system configuration."""
        section = self.config["Sound"]
        return SoundConfig(
            enabled=section.getboolean("enabled"),
            cooldown=section.getfloat("cooldown"),
            sounds_dir=section.get("sounds_dir")
        )
        
    def get_debug_config(self) -> DebugConfig:
        """Get debug system configuration."""
        section = self.config["Debug"]
        return DebugConfig(
            enabled=section.getboolean("enabled"),
            log_level=section.get("log_level"),
            log_dir=section.get("log_dir"),
            update_interval=section.getint("update_interval")
        )
        
    def update_section(self, section: str, values: Dict[str, Any]) -> None:
        """
        Update configuration section.
        
        Args:
            section: Section name
            values: Dictionary of values to update
        """
        try:
            if section not in self.config:
                self.config[section] = {}
                
            # Update values
            for key, value in values.items():
                self.config[section][key] = str(value)
                
            # Save changes
            self.save_config()
            logger.debug(f"Updated configuration section: {section}")
            
        except Exception as e:
            logger.error(f"Error updating config section: {e}")
            
    def get_debug_info(self) -> Dict[str, Any]:
        """Get configuration state for debugging."""
        return {
            section: dict(self.config[section])
            for section in self.config.sections()
        } 