"""Configuration management for TB Scout application."""

import os
import logging
from pathlib import Path
from configparser import ConfigParser
from typing import Any, Optional, Union, cast
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WindowConfig:
    """Window tracking configuration."""
    standalone_priority: bool = True
    browser_detection: bool = True
    update_interval: int = 1000  # ms

class ConfigManager:
    """Configuration manager for TB Scout application.
    
    This class handles reading and writing configuration settings from/to an INI file.
    It provides type-safe access to configuration values with default fallbacks.
    
    Attributes:
        config_file (Path): Path to the configuration file.
        parser (ConfigParser): The underlying configuration parser.
    """
    
    def __init__(self, config_file: Union[str, Path]) -> None:
        """Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file.
        """
        self.config_file = Path(config_file)
        self.parser = ConfigParser()
        
        # Load configuration
        self.load()
    
    def load(self) -> None:
        """Load configuration from file.
        
        If the file doesn't exist, creates it with default values.
        """
        if self.config_file.exists():
            logger.info("Loading configuration from %s", self.config_file)
            self.parser.read(self.config_file, encoding="utf-8")
        else:
            logger.info("Configuration file %s not found, creating with defaults",
                       self.config_file)
            self._create_default_config()
    
    def save(self) -> None:
        """Save current configuration to file."""
        logger.info("Saving configuration to %s", self.config_file)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.parser.write(f)
    
    def _create_default_config(self) -> None:
        """Create default configuration."""
        # Window settings
        self.parser["Window"] = {
            "standalone_priority": "true",
            "browser_detection": "true",
            "update_interval": "1000",
        }
        
        # Capture settings
        self.parser["Capture"] = {
            "debug_screenshots": "true",
            "debug_dir": "debug_screenshots",
            "save_failures": "true",
        }
        
        # OCR settings
        self.parser["OCR"] = {
            "tesseract_path": "",
            "language": "eng",
            "psm_mode": "7",
            "oem_mode": "3",
            "char_whitelist": "0123456789",
        }
        
        # Pattern matching settings
        self.parser["Pattern"] = {
            "template_dir": "images",
            "confidence_threshold": "0.8",
            "save_matches": "true",
        }
        
        # Sound settings
        self.parser["Sound"] = {
            "enabled": "true",
            "cooldown": "5.0",
            "sounds_dir": "sounds",
        }
        
        # Debug settings
        self.parser["Debug"] = {
            "enabled": "true",
            "log_level": "DEBUG",
            "log_dir": "logs",
            "update_interval": "1000",
        }
        
        # Save default configuration
        self.save()
    
    def get_str(self, section: str, option: str, fallback: Optional[str] = None) -> str:
        """Get a string value from the configuration.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            fallback: Default value if option is not found.
        
        Returns:
            str: The configuration value.
        """
        return cast(str, self.parser.get(section, option, fallback=fallback))
    
    def get_int(self, section: str, option: str, fallback: Optional[int] = None) -> int:
        """Get an integer value from the configuration.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            fallback: Default value if option is not found.
        
        Returns:
            int: The configuration value.
        """
        return cast(int, self.parser.getint(section, option, fallback=fallback))
    
    def get_float(self, section: str, option: str, fallback: Optional[float] = None) -> float:
        """Get a float value from the configuration.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            fallback: Default value if option is not found.
        
        Returns:
            float: The configuration value.
        """
        return cast(float, self.parser.getfloat(section, option, fallback=fallback))
    
    def get_bool(self, section: str, option: str, fallback: Optional[bool] = None) -> bool:
        """Get a boolean value from the configuration.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            fallback: Default value if option is not found.
        
        Returns:
            bool: The configuration value.
        """
        return cast(bool, self.parser.getboolean(section, option, fallback=fallback))
    
    def get_path(self, section: str, option: str, fallback: Optional[str] = None) -> Path:
        """Get a path value from the configuration.
        
        The path is returned as an absolute path. If the path in the configuration
        is relative, it is resolved relative to the configuration file's directory.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            fallback: Default value if option is not found.
        
        Returns:
            Path: The configuration value as an absolute path.
        """
        path_str = self.get_str(section, option, fallback=fallback)
        if not path_str:
            return Path()
        
        path = Path(path_str)
        if not path.is_absolute():
            path = self.config_file.parent / path
        
        return path.resolve()
    
    def set(self, section: str, option: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
            value: Value to set.
        """
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        
        self.parser.set(section, option, str(value))
    
    def has_option(self, section: str, option: str) -> bool:
        """Check if an option exists in the configuration.
        
        Args:
            section: Configuration section name.
            option: Option name within the section.
        
        Returns:
            bool: True if the option exists, False otherwise.
        """
        return self.parser.has_option(section, option)
    
    def has_section(self, section: str) -> bool:
        """Check if a section exists in the configuration.
        
        Args:
            section: Configuration section name.
        
        Returns:
            bool: True if the section exists, False otherwise.
        """
        return self.parser.has_section(section)
    
    def get(self, section: str, option: str, fallback: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: The configuration section.
            option: The option name.
            fallback: Value to return if the option is not found.
            
        Returns:
            The configuration value or fallback if not found.
        """
        return self.parser.get(section, option, fallback=fallback)
    
    def get_window_config(self) -> WindowConfig:
        """Get window tracking configuration.
        
        Returns:
            WindowConfig: Window configuration settings.
        """
        return WindowConfig(
            standalone_priority=self.get_bool("Window", "standalone_priority", True),
            browser_detection=self.get_bool("Window", "browser_detection", True),
            update_interval=self.get_int("Window", "update_interval", 1000)
        ) 