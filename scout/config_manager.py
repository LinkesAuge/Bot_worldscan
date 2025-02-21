from pathlib import Path
from configparser import ConfigParser
import logging
from PyQt6.QtGui import QColor
from typing import Tuple, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration settings using an INI file.
    
    This class handles all persistent settings for the application, including:
    - Overlay appearance (colors, sizes, positions)
    - Pattern matching parameters (confidence levels, FPS)
    - Scanner settings (regions, coordinates)
    - Sound settings
    
    The settings are stored in a INI file that can be manually
    edited if needed. If no config file exists, default settings are created.
    """
    
    def __init__(self, config_path: str = None) -> None:
        """
        Initialize the configuration manager and load or create settings.
        
        This constructor will:
        1. Check if the config file exists
        2. Create it with default settings if it doesn't
        3. Load the settings into memory
        
        Args:
            config_path: Path to the configuration file (default: "scout/config.ini")
        """
        if config_path is None:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            config_path = current_dir / "config.ini"
            
        self.config_path = Path(config_path)
        self.config = ConfigParser()
        
        # Create default config if file doesn't exist
        if not self.config_path.exists():
            logger.info("No configuration file found - creating with default settings")
            self.create_default_config()
        
        # Load existing config
        self.config.read(self.config_path)
        logger.debug("Configuration loaded successfully")

    def create_default_config(self) -> None:
        """
        Create a new configuration file with default settings.
        
        This method sets up initial values for all application settings:
        - Overlay: Visual appearance settings for the detection overlay
        - Pattern Matching: Detection sensitivity and performance settings
        - Scanner: World scanning parameters
        - Debug: Debug mode settings
        
        The default values are chosen to provide a good starting experience
        for new users while maintaining reliable detection.
        """
        self.config["Overlay"] = {
            "active": "true",  # Default to ON
            "rect_color_r": "170",
            "rect_color_g": "0",
            "rect_color_b": "255",
            "rect_thickness": "8",  # Updated
            "rect_scale": "2.0",  # Updated
            "font_color_r": "255",
            "font_color_g": "0",
            "font_color_b": "0",
            "font_size": "24",  # Updated
            "text_thickness": "2",  # Updated
            "cross_color_r": "255",
            "cross_color_g": "85",
            "cross_color_b": "127",
            "cross_size": "28",
            "cross_thickness": "5",  # Updated
            "cross_scale": "1.0"  # Updated
        }
        
        self.config["PatternMatching"] = {
            "active": "true",  # Default to ON
            "confidence": "0.90",  # Updated (90%)
            "target_fps": "1",  # Updated
            "grouping_threshold": "10",
            "sound_enabled": "true",  # Default to ON
            "sound_cooldown": "5.0"
        }
        
        self.config["Debug"] = {
            "enabled": "false",  # Default to OFF
            "save_screenshots": "true",
            "save_templates": "true"
        }
        
        self.save_config()
        logger.info("Default configuration created")

    def save_config(self) -> None:
        """Save the current configuration to file."""
        with open(self.config_path, 'w') as f:
            self.config.write(f)
        logger.debug("Configuration saved")

    def get_overlay_settings(self) -> Dict[str, Any]:
        """Get overlay window settings from config."""
        settings = {
            "active": self.config.getboolean("Overlay", "active", fallback=False),
            "rect_color": QColor(
                self.config.getint("Overlay", "rect_color_r", fallback=170),
                self.config.getint("Overlay", "rect_color_g", fallback=0),
                self.config.getint("Overlay", "rect_color_b", fallback=255)
            ),
            "rect_thickness": self.config.getint("Overlay", "rect_thickness", fallback=7),
            "rect_scale": self.config.getfloat("Overlay", "rect_scale", fallback=2.0),
            "font_color": QColor(
                self.config.getint("Overlay", "font_color_r", fallback=255),
                self.config.getint("Overlay", "font_color_g", fallback=0),
                self.config.getint("Overlay", "font_color_b", fallback=0)
            ),
            "font_size": self.config.getint("Overlay", "font_size", fallback=33),
            "text_thickness": self.config.getint("Overlay", "text_thickness", fallback=2),
            "cross_color": QColor(
                self.config.getint("Overlay", "cross_color_r", fallback=255),
                self.config.getint("Overlay", "cross_color_g", fallback=85),
                self.config.getint("Overlay", "cross_color_b", fallback=127)
            ),
            "cross_size": self.config.getint("Overlay", "cross_size", fallback=28),
            "cross_thickness": self.config.getint("Overlay", "cross_thickness", fallback=5),
            "cross_scale": self.config.getfloat("Overlay", "cross_scale", fallback=1.0)
        }
        logger.debug(f"Loaded overlay settings: {settings}")
        return settings

    def get_pattern_matching_settings(self) -> Dict[str, Any]:
        """Get pattern matching settings from config."""
        settings = {
            "active": self.config.getboolean("PatternMatching", "active", fallback=False),
            "confidence": self.config.getfloat("PatternMatching", "confidence", fallback=0.81),
            "target_fps": self.config.getfloat("PatternMatching", "target_fps", fallback=5.0),
            "grouping_threshold": self.config.getint("PatternMatching", "grouping_threshold", fallback=10),
            "sound_enabled": self.config.getboolean("PatternMatching", "sound_enabled", fallback=False),
            "sound_cooldown": self.config.getfloat("PatternMatching", "sound_cooldown", fallback=5.0)
        }
        logger.debug(f"Loaded pattern matching settings: {settings}")
        return settings

    def get_debug_settings(self) -> Dict[str, Any]:
        """Get debug settings from config."""
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            self.config["Debug"] = {
                "enabled": "false",
                "save_screenshots": "true",
                "save_templates": "true"
            }
            self.save_config()
            
        settings = {
            "enabled": self.config.getboolean("Debug", "enabled", fallback=False),
            "save_screenshots": self.config.getboolean("Debug", "save_screenshots", fallback=True),
            "save_templates": self.config.getboolean("Debug", "save_templates", fallback=True)
        }
        logger.debug(f"Loaded debug settings: {settings}")
        return settings

    def update_debug_settings(self, enabled: bool, save_screenshots: bool = True, save_templates: bool = True) -> None:
        """Update debug settings in config."""
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            
        self.config["Debug"]["enabled"] = str(enabled).lower()
        self.config["Debug"]["save_screenshots"] = str(save_screenshots).lower()
        self.config["Debug"]["save_templates"] = str(save_templates).lower()
        
        self.save_config()
        logger.debug(f"Updated debug settings: enabled={enabled}, screenshots={save_screenshots}, templates={save_templates}")

    def update_overlay_settings(self, active: bool, rect_color: QColor, 
                              rect_thickness: int, rect_scale: float,
                              font_color: QColor, font_size: int,
                              text_thickness: int,
                              cross_color: QColor, cross_size: int,
                              cross_thickness: int, cross_scale: float) -> None:
        """Update overlay settings in config."""
        if "Overlay" not in self.config:
            self.config.add_section("Overlay")
            
        self.config["Overlay"]["active"] = str(active).lower()
        self.config["Overlay"]["rect_color_r"] = str(rect_color.red())
        self.config["Overlay"]["rect_color_g"] = str(rect_color.green())
        self.config["Overlay"]["rect_color_b"] = str(rect_color.blue())
        self.config["Overlay"]["rect_thickness"] = str(rect_thickness)
        self.config["Overlay"]["rect_scale"] = str(rect_scale)
        self.config["Overlay"]["font_color_r"] = str(font_color.red())
        self.config["Overlay"]["font_color_g"] = str(font_color.green())
        self.config["Overlay"]["font_color_b"] = str(font_color.blue())
        self.config["Overlay"]["font_size"] = str(font_size)
        self.config["Overlay"]["text_thickness"] = str(text_thickness)
        self.config["Overlay"]["cross_color_r"] = str(cross_color.red())
        self.config["Overlay"]["cross_color_g"] = str(cross_color.green())
        self.config["Overlay"]["cross_color_b"] = str(cross_color.blue())
        self.config["Overlay"]["cross_size"] = str(cross_size)
        self.config["Overlay"]["cross_thickness"] = str(cross_thickness)
        self.config["Overlay"]["cross_scale"] = str(cross_scale)
        
        self.save_config()

    def update_pattern_matching_settings(self, active: bool, confidence: float, 
                                      target_fps: float, sound_enabled: bool) -> None:
        """Update pattern matching settings in config."""
        if "PatternMatching" not in self.config:
            self.config.add_section("PatternMatching")
            
        self.config["PatternMatching"]["active"] = str(active).lower()
        self.config["PatternMatching"]["confidence"] = str(confidence)
        self.config["PatternMatching"]["target_fps"] = str(target_fps)
        self.config["PatternMatching"]["sound_enabled"] = str(sound_enabled).lower()
        
        self.save_config()

    def update_scanner_settings(self, settings: Dict[str, int]) -> None:
        """Update scanner settings in config."""
        if not self.config.has_section("Scanner"):
            self.config.add_section("Scanner")
            
        for key, value in settings.items():
            self.config["Scanner"][key] = str(value)
            
        self.save_config()

    def get_scanner_settings(self) -> Dict[str, int]:
        """Get current scanner settings from config."""
        if not self.config.has_section("Scanner"):
            return {}
            
        return {
            "minimap_left": self.config.getint("Scanner", "minimap_left", fallback=0),
            "minimap_top": self.config.getint("Scanner", "minimap_top", fallback=0),
            "minimap_width": self.config.getint("Scanner", "minimap_width", fallback=0),
            "minimap_height": self.config.getint("Scanner", "minimap_height", fallback=0)
        } 