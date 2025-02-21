from pathlib import Path
from configparser import ConfigParser
import logging
from PyQt6.QtGui import QColor
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration settings using an INI file.
    
    This class handles all persistent settings for the application, including:
    - Overlay appearance (colors, sizes, positions)
    - Pattern matching parameters (confidence levels, FPS)
    - Scanner settings (regions, coordinates)
    - OCR settings (region, frequency)
    - Sound settings
    
    The settings are stored in an INI file that can be manually
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
        """Create a new configuration file with default settings."""
        # Overlay settings
        self.config["Overlay"] = {
            "active": "false",
            "rect_color_r": "0",
            "rect_color_g": "255",
            "rect_color_b": "0",
            "rect_thickness": "2",
            "rect_scale": "1.0",
            "font_color_r": "255",
            "font_color_g": "255",
            "font_color_b": "255",
            "font_size": "12",
            "text_thickness": "1",
            "cross_color_r": "255",
            "cross_color_g": "0",
            "cross_color_b": "0",
            "cross_size": "10",
            "cross_thickness": "1",
            "cross_scale": "1.0"
        }
        
        # Pattern matching settings
        self.config["PatternMatching"] = {
            "active": "false",
            "confidence": "0.8",
            "target_frequency": "1.0",
            "sound_enabled": "false"
        }
        
        # Scanner settings
        self.config["Scanner"] = {
            "minimap_left": "0",
            "minimap_top": "0",
            "minimap_width": "0",
            "minimap_height": "0",
            "input_field_x": "0",
            "input_field_y": "0"
        }
        
        # OCR settings
        self.config["OCR"] = {
            "active": "false",
            "frequency": "0.5",
            "region_left": "0",
            "region_top": "0",
            "region_width": "0",
            "region_height": "0",
            "dpi_scale": "1.0"
        }
        
        # Debug settings
        self.config["Debug"] = {
            "enabled": "false",
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

    def get_ocr_settings(self) -> Dict[str, Any]:
        """Get current OCR settings."""
        if not self.config.has_section("OCR"):
            self.config.add_section("OCR")
            
        return {
            "active": self.config.getboolean("OCR", "active", fallback=False),
            "frequency": self.config.getfloat("OCR", "frequency", fallback=0.5),
            "region": {
                "left": self.config.getint("OCR", "region_left", fallback=0),
                "top": self.config.getint("OCR", "region_top", fallback=0),
                "width": self.config.getint("OCR", "region_width", fallback=0),
                "height": self.config.getint("OCR", "region_height", fallback=0),
                "dpi_scale": self.config.getfloat("OCR", "dpi_scale", fallback=1.0)
            }
        }

    def update_ocr_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update OCR settings.
        
        Args:
            settings: Dictionary containing OCR settings
        """
        if not self.config.has_section("OCR"):
            self.config.add_section("OCR")
            
        self.config["OCR"]["active"] = str(settings.get("active", False)).lower()
        self.config["OCR"]["frequency"] = str(settings.get("frequency", 0.5))
        
        region = settings.get("region", {})
        self.config["OCR"]["region_left"] = str(region.get("left", 0))
        self.config["OCR"]["region_top"] = str(region.get("top", 0))
        self.config["OCR"]["region_width"] = str(region.get("width", 0))
        self.config["OCR"]["region_height"] = str(region.get("height", 0))
        self.config["OCR"]["dpi_scale"] = str(region.get("dpi_scale", 1.0))
        
        self.save_config()
        logger.debug(f"Updated OCR settings: {settings}")

    def get_pattern_matching_settings(self) -> Dict[str, Any]:
        """
        Get pattern matching settings from config.
        
        Returns:
            Dictionary containing pattern matching settings:
            - active: Whether pattern matching is active
            - confidence: Match confidence threshold
            - target_frequency: Target updates per second
            - sound_enabled: Whether sound alerts are enabled
            - templates_dir: Directory containing template images
            - grouping_threshold: Pixel distance for grouping matches
        """
        config = self._load_config()
        
        return {
            "active": config.getboolean("pattern_matching", "active", fallback=False),
            "confidence": config.getfloat("pattern_matching", "confidence", fallback=0.8),
            "target_frequency": config.getfloat("pattern_matching", "target_frequency", fallback=1.0),
            "sound_enabled": config.getboolean("pattern_matching", "sound_enabled", fallback=False),
            "templates_dir": config.get("pattern_matching", "templates_dir", fallback="scout/templates"),
            "grouping_threshold": config.getint("pattern_matching", "grouping_threshold", fallback=10)
        }

    def update_pattern_matching_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update pattern matching settings in config.
        
        Args:
            settings: Dictionary containing pattern matching settings:
                - active: Whether pattern matching is active
                - confidence: Match confidence threshold
                - target_frequency: Target updates per second
                - sound_enabled: Whether sound alerts are enabled
                - templates_dir: Directory containing template images
                - grouping_threshold: Pixel distance for grouping matches
        """
        config = self._load_config()
        
        if not config.has_section("pattern_matching"):
            config.add_section("pattern_matching")
            
        config.set("pattern_matching", "active", str(settings.get("active", False)))
        config.set("pattern_matching", "confidence", str(settings.get("confidence", 0.8)))
        config.set("pattern_matching", "target_frequency", str(settings.get("target_frequency", 1.0)))
        config.set("pattern_matching", "sound_enabled", str(settings.get("sound_enabled", False)))
        config.set("pattern_matching", "templates_dir", str(settings.get("templates_dir", "scout/templates")))
        config.set("pattern_matching", "grouping_threshold", str(settings.get("grouping_threshold", 10)))
        
        self._save_config(config)
        logger.debug(f"Updated pattern matching settings: {settings}")

    def get_overlay_settings(self) -> Dict[str, Any]:
        """Get overlay settings from config."""
        if not self.config.has_section("Overlay"):
            self.config.add_section("Overlay")
            
        return {
            "active": self.config.getboolean("Overlay", "active", fallback=False),
            "rect_color": QColor(
                self.config.getint("Overlay", "rect_color_r", fallback=0),
                self.config.getint("Overlay", "rect_color_g", fallback=255),
                self.config.getint("Overlay", "rect_color_b", fallback=0)
            ),
            "rect_thickness": self.config.getint("Overlay", "rect_thickness", fallback=2),
            "rect_scale": self.config.getfloat("Overlay", "rect_scale", fallback=1.0),
            "font_color": QColor(
                self.config.getint("Overlay", "font_color_r", fallback=255),
                self.config.getint("Overlay", "font_color_g", fallback=255),
                self.config.getint("Overlay", "font_color_b", fallback=255)
            ),
            "font_size": self.config.getint("Overlay", "font_size", fallback=12),
            "text_thickness": self.config.getint("Overlay", "text_thickness", fallback=1),
            "cross_color": QColor(
                self.config.getint("Overlay", "cross_color_r", fallback=255),
                self.config.getint("Overlay", "cross_color_g", fallback=0),
                self.config.getint("Overlay", "cross_color_b", fallback=0)
            ),
            "cross_size": self.config.getint("Overlay", "cross_size", fallback=10),
            "cross_thickness": self.config.getint("Overlay", "cross_thickness", fallback=1),
            "cross_scale": self.config.getfloat("Overlay", "cross_scale", fallback=1.0)
        }

    def update_overlay_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update overlay settings.
        
        Args:
            settings: Dictionary containing overlay settings
        """
        if not self.config.has_section("Overlay"):
            self.config.add_section("Overlay")
            
        self.config["Overlay"]["active"] = str(settings.get("active", False)).lower()
        
        rect_color = settings.get("rect_color", QColor(0, 255, 0))
        self.config["Overlay"]["rect_color_r"] = str(rect_color.red())
        self.config["Overlay"]["rect_color_g"] = str(rect_color.green())
        self.config["Overlay"]["rect_color_b"] = str(rect_color.blue())
        
        self.config["Overlay"]["rect_thickness"] = str(settings.get("rect_thickness", 2))
        self.config["Overlay"]["rect_scale"] = str(settings.get("rect_scale", 1.0))
        
        font_color = settings.get("font_color", QColor(255, 255, 255))
        self.config["Overlay"]["font_color_r"] = str(font_color.red())
        self.config["Overlay"]["font_color_g"] = str(font_color.green())
        self.config["Overlay"]["font_color_b"] = str(font_color.blue())
        
        self.config["Overlay"]["font_size"] = str(settings.get("font_size", 12))
        self.config["Overlay"]["text_thickness"] = str(settings.get("text_thickness", 1))
        
        cross_color = settings.get("cross_color", QColor(255, 0, 0))
        self.config["Overlay"]["cross_color_r"] = str(cross_color.red())
        self.config["Overlay"]["cross_color_g"] = str(cross_color.green())
        self.config["Overlay"]["cross_color_b"] = str(cross_color.blue())
        
        self.config["Overlay"]["cross_size"] = str(settings.get("cross_size", 10))
        self.config["Overlay"]["cross_thickness"] = str(settings.get("cross_thickness", 1))
        self.config["Overlay"]["cross_scale"] = str(settings.get("cross_scale", 1.0))
        
        self.save_config()
        logger.debug("Updated overlay settings")

    def get_scanner_settings(self) -> Dict[str, Any]:
        """Get scanner settings from config."""
        if not self.config.has_section("Scanner"):
            self.config.add_section("Scanner")
            
        return {
            "minimap_left": self.config.getint("Scanner", "minimap_left", fallback=0),
            "minimap_top": self.config.getint("Scanner", "minimap_top", fallback=0),
            "minimap_width": self.config.getint("Scanner", "minimap_width", fallback=0),
            "minimap_height": self.config.getint("Scanner", "minimap_height", fallback=0),
            "input_field_x": self.config.getint("Scanner", "input_field_x", fallback=0),
            "input_field_y": self.config.getint("Scanner", "input_field_y", fallback=0)
        }

    def update_scanner_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update scanner settings.
        
        Args:
            settings: Dictionary containing scanner settings
        """
        if not self.config.has_section("Scanner"):
            self.config.add_section("Scanner")
            
        for key, value in settings.items():
            self.config["Scanner"][key] = str(value)
            
        self.save_config()
        logger.debug(f"Updated scanner settings: {settings}")

    def get_debug_settings(self) -> Dict[str, bool]:
        """Get debug settings from config."""
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            
        return {
            "enabled": self.config.getboolean("Debug", "enabled", fallback=False),
            "save_screenshots": self.config.getboolean("Debug", "save_screenshots", fallback=True),
            "save_templates": self.config.getboolean("Debug", "save_templates", fallback=True)
        }

    def update_debug_settings(self, settings: Dict[str, bool]) -> None:
        """
        Update debug settings.
        
        Args:
            settings: Dictionary containing debug settings with keys:
                     - enabled: Whether debug mode is enabled
                     - save_screenshots: Whether to save debug screenshots
                     - save_templates: Whether to save template debug images
        """
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            
        for key, value in settings.items():
            self.config["Debug"][key] = str(value).lower()
            
        self.save_config()
        logger.debug(f"Updated debug settings: {settings}")

    def _load_config(self):
        """Load the configuration file."""
        return self.config

    def _save_config(self, config):
        """Save the configuration file."""
        with open(self.config_path, 'w') as f:
            config.write(f)
        logger.debug("Configuration saved") 