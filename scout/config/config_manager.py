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
        """Initialize configuration manager."""
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        
        # Load or create config
        if self.config_path.exists():
            self.load_config()
        else:
            self.create_default_config()
            
        logger.debug("Configuration manager initialized")
    
    def create_default_config(self) -> None:
        """Create default configuration."""
        # Window section
        window_config = WindowConfig()
        self.config["Window"] = {
            "standalone_priority": str(window_config.standalone_priority),
            "browser_detection": str(window_config.browser_detection),
            "update_interval": str(window_config.update_interval)
        }
        
        # Capture section
        capture_config = CaptureConfig()
        self.config["Capture"] = {
            "debug_screenshots": str(capture_config.debug_screenshots),
            "debug_dir": capture_config.debug_dir,
            "save_failures": str(capture_config.save_failures)
        }
        
        # OCR section
        ocr_config = OCRConfig()
        self.config["OCR"] = {
            "tesseract_path": str(ocr_config.tesseract_path or ""),
            "language": ocr_config.language,
            "psm_mode": str(ocr_config.psm_mode),
            "oem_mode": str(ocr_config.oem_mode),
            "char_whitelist": ocr_config.char_whitelist
        }
        
        # Pattern section
        pattern_config = PatternConfig()
        self.config["Pattern"] = {
            "template_dir": pattern_config.template_dir,
            "confidence_threshold": str(pattern_config.confidence_threshold),
            "save_matches": str(pattern_config.save_matches)
        }
        
        # Sound section
        sound_config = SoundConfig()
        self.config["Sound"] = {
            "enabled": str(sound_config.enabled),
            "cooldown": str(sound_config.cooldown),
            "sounds_dir": sound_config.sounds_dir
        }
        
        # Debug section
        debug_config = DebugConfig()
        self.config["Debug"] = {
            "enabled": str(debug_config.enabled),
            "log_level": debug_config.log_level,
            "log_dir": debug_config.log_dir,
            "update_interval": str(debug_config.update_interval)
        }
        
        # Pattern Matching Overlay section
        overlay_config = PatternMatchingOverlayConfig()
        self.config["PatternMatchingOverlay"] = overlay_config.to_dict()
        
        # Save default config
        self.save_config()
        logger.info("Created default configuration")
    
    def get_pattern_matching_overlay_config(self) -> PatternMatchingOverlayConfig:
        """Get pattern matching overlay configuration."""
        try:
            section = self.config["PatternMatchingOverlay"]
            return PatternMatchingOverlayConfig.from_dict(dict(section))
        except Exception as e:
            logger.error(f"Error loading overlay config: {e}")
            return PatternMatchingOverlayConfig()  # Return defaults
    
    def update_section(self, section: str, values: Dict[str, Any]) -> None:
        """Update configuration section."""
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
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            self.config.read(self.config_path, encoding="utf-8")
            logger.info(f"Loaded configuration from {self.config_path}")
            
            # Validate and update all sections
            required_sections = {
                "Window": WindowConfig(),
                "Capture": CaptureConfig(),
                "OCR": OCRConfig(),
                "Pattern": PatternConfig(),
                "Sound": SoundConfig(),
                "Debug": DebugConfig(),
                "PatternMatchingOverlay": PatternMatchingOverlayConfig()
            }
            
            config_updated = False
            for section_name, default_config in required_sections.items():
                if section_name not in self.config:
                    if hasattr(default_config, "to_dict"):
                        self.config[section_name] = default_config.to_dict()
                    else:
                        self.config[section_name] = {
                            k: str(v) for k, v in asdict(default_config).items()
                        }
                    config_updated = True
                    logger.debug(f"Added missing section: {section_name}")
            
            if config_updated:
                self.save_config()
                logger.info("Updated configuration with missing sections")
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.create_default_config()
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)
            logger.info(f"Saved configuration to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def get_debug_info(self) -> Dict[str, Any]:
        """Get configuration state for debugging."""
        return {
            section: dict(self.config[section])
            for section in self.config.sections()
        }

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