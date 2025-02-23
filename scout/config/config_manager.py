"""Configuration management system."""

from typing import Dict, Any, Optional, Tuple
import logging
import configparser
from pathlib import Path
from dataclasses import dataclass, asdict, fields
from PyQt6.QtCore import QRect

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

@dataclass
class PatternMatchingOverlayConfig:
    """Pattern matching overlay configuration."""
    # Update settings
    update_rate: float = 1.0  # updates per second
    
    # Rectangle settings
    rect_color: Tuple[int, int, int] = (0, 255, 0)  # BGR Green
    rect_thickness: int = 2
    rect_scale: float = 1.0
    rect_min_size: int = 20
    rect_max_size: int = 500
    
    # Crosshair settings
    crosshair_color: Tuple[int, int, int] = (255, 0, 0)  # BGR Red
    crosshair_size: int = 20
    crosshair_thickness: int = 1
    
    # Label settings
    label_color: Tuple[int, int, int] = (0, 255, 0)  # BGR Green
    label_size: float = 0.8
    label_thickness: int = 2
    label_format: str = "{name} ({conf:.2f})"
    
    # Grouping settings
    group_distance: int = 50  # Pixels
    max_matches: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for saving to config."""
        return {
            k: str(v) if isinstance(v, tuple) else v
            for k, v in asdict(self).items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternMatchingOverlayConfig':
        """Create settings from dictionary loaded from config."""
        # Helper function to parse color tuple
        def parse_color(s: str) -> Tuple[int, int, int]:
            try:
                return eval(s)
            except:
                return (0, 255, 0)  # Default to green on error
        
        # Convert string values to appropriate types
        field_types = {f.name: f.type for f in fields(cls)}
        converted = {}
        
        for key, value in data.items():
            if key not in field_types:
                continue
                
            field_type = field_types[key]
            try:
                if field_type == Tuple[int, int, int]:
                    converted[key] = parse_color(value)
                elif field_type == float:
                    converted[key] = float(value)
                elif field_type == int:
                    converted[key] = int(value)
                else:
                    converted[key] = value
            except:
                # Use default value on error
                converted[key] = getattr(cls, key).default
        
        return cls(**converted)

    def scale_match_rect(self, rect: QRect) -> QRect:
        """Scale a match rectangle based on current settings.
        
        Args:
            rect: Original rectangle from pattern match
            
        Returns:
            Scaled rectangle maintaining the center point
        """
        logger.debug(f"Scaling match rect: {rect} with scale={self.rect_scale}")
        
        # Get center point
        center = rect.center()
        
        # Calculate new dimensions
        new_width = max(self.rect_min_size, 
                       min(int(rect.width() * self.rect_scale), 
                           self.rect_max_size))
        new_height = max(self.rect_min_size,
                        min(int(rect.height() * self.rect_scale),
                            self.rect_max_size))
        
        # Calculate new top-left point to maintain center
        new_left = center.x() - new_width // 2
        new_top = center.y() - new_height // 2
        
        scaled_rect = QRect(new_left, new_top, new_width, new_height)
        logger.debug(f"Scaled rect result: {scaled_rect}")
        return scaled_rect

class ConfigManager:
    """Configuration manager for TB Scout application."""
    
    def __init__(self, config_path: str = "config.ini") -> None:
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.parser = configparser.ConfigParser()
        
        # Load or create config
        if self.config_path.exists():
            logger.info(f"Loading configuration from {self.config_path}")
            self.load_config()
        else:
            logger.info(f"Creating new configuration at {self.config_path}")
            self._create_default_config()
            
        logger.debug("Configuration manager initialized")
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            self.parser.read(self.config_path, encoding="utf-8")
            logger.debug("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Creating default configuration")
            self._create_default_config()
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.parser.write(f)
            logger.debug("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
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
            "template_dir": "scout/templates",
            "confidence_threshold": "0.9",  # Updated to 0.9
            "save_matches": "true",
        }
        
        # Pattern matching overlay settings
        self.parser["PatternMatchingOverlay"] = {
            "update_rate": "1.0",
            "rect_color": "(0, 255, 0)",
            "rect_thickness": "2",
            "rect_scale": "1.0",
            "rect_min_size": "20",
            "rect_max_size": "500",
            "crosshair_color": "(255, 0, 0)",
            "crosshair_size": "20",
            "crosshair_thickness": "1",
            "label_color": "(0, 255, 0)",
            "label_size": "0.8",
            "label_thickness": "2",
            "label_format": "{name} ({conf:.2f})",
            "group_distance": "50",
            "max_matches": "100"
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
        self.save_config()
        logger.info("Created default configuration")
    
    def get_pattern_matching_overlay_config(self) -> PatternMatchingOverlayConfig:
        """Get pattern matching overlay configuration."""
        try:
            section = self.parser["PatternMatchingOverlay"]
            return PatternMatchingOverlayConfig.from_dict(dict(section))
        except Exception as e:
            logger.error(f"Error loading overlay config: {e}")
            return PatternMatchingOverlayConfig()  # Return defaults
    
    def update_section(self, section: str, values: Dict[str, Any]) -> None:
        """Update configuration section.
        
        Args:
            section: Section name to update
            values: Dictionary of values to update
        """
        try:
            if section not in self.parser:
                self.parser[section] = {}
                
            # Update values
            for key, value in values.items():
                self.parser[section][key] = str(value)
                
            # Save changes
            self.save_config()
            logger.debug(f"Updated configuration section: {section}")
            
        except Exception as e:
            logger.error(f"Error updating config section: {e}")
    
    def get_pattern_config(self) -> PatternConfig:
        """Get pattern matching configuration."""
        try:
            section = self.parser["Pattern"]
            return PatternConfig(
                template_dir=section.get("template_dir", "scout/templates"),
                confidence_threshold=float(section.get("confidence_threshold", "0.9")),
                save_matches=section.getboolean("save_matches", True)
            )
        except Exception as e:
            logger.error(f"Error loading pattern config: {e}")
            return PatternConfig()  # Return defaults

    def get_window_config(self) -> WindowConfig:
        """Get window tracking configuration."""
        section = self.parser["Window"]
        return WindowConfig(
            standalone_priority=section.getboolean("standalone_priority"),
            browser_detection=section.getboolean("browser_detection"),
            update_interval=section.getint("update_interval")
        )
        
    def get_capture_config(self) -> CaptureConfig:
        """Get screen capture configuration."""
        section = self.parser["Capture"]
        return CaptureConfig(
            debug_screenshots=section.getboolean("debug_screenshots"),
            debug_dir=section.get("debug_dir"),
            save_failures=section.getboolean("save_failures")
        )
        
    def get_ocr_config(self) -> OCRConfig:
        """Get OCR processing configuration."""
        section = self.parser["OCR"]
        return OCRConfig(
            tesseract_path=section.get("tesseract_path") or None,
            language=section.get("language"),
            psm_mode=section.getint("psm_mode"),
            oem_mode=section.getint("oem_mode"),
            char_whitelist=section.get("char_whitelist")
        )
        
    def get_sound_config(self) -> SoundConfig:
        """Get sound system configuration."""
        section = self.parser["Sound"]
        return SoundConfig(
            enabled=section.getboolean("enabled"),
            cooldown=section.getfloat("cooldown"),
            sounds_dir=section.get("sounds_dir")
        )
        
    def get_debug_config(self) -> DebugConfig:
        """Get debug system configuration."""
        section = self.parser["Debug"]
        return DebugConfig(
            enabled=section.getboolean("enabled"),
            log_level=section.get("log_level"),
            log_dir=section.get("log_dir"),
            update_interval=section.getint("update_interval")
        ) 