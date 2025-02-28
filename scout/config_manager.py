from pathlib import Path
from configparser import ConfigParser
import logging
from PyQt6.QtGui import QColor
from typing import Dict, Any, Optional
import os
import json

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration settings using an INI file.
    
    This class handles all persistent settings for the application, including:
    - Overlay appearance (colors, sizes, positions)
    - Template matching parameters (confidence levels, FPS)
    - Scanner settings (regions, coordinates)
    - OCR settings (region, frequency)
    - Sound settings
    
    The settings are stored in an INI file that can be manually
    edited if needed. If no config file exists, default settings are created.
    """
    
    # Default Overlay Settings
    DEFAULT_OVERLAY_SETTINGS = {
        "active": "true",
        "rect_color_r": "255",
        "rect_color_g": "0",
        "rect_color_b": "0",
        "rect_thickness": "6",
        "rect_scale": "3.0",
        "font_color_r": "85",
        "font_color_g": "255",
        "font_color_b": "255",
        "font_size": "26",
        "text_thickness": "2",
        "cross_color_r": "255",
        "cross_color_g": "0",
        "cross_color_b": "127",
        "cross_size": "10",
        "cross_thickness": "4",
        "cross_scale": "4.0"
    }

    # Default Template Matching Settings
    DEFAULT_TEMPLATE_SETTINGS = {
        "active": "false",
        "confidence": "0.9",
        "target_frequency": "1.0",
        "sound_enabled": "true",
        "templates_dir": "scout/templates",
        "grouping_threshold": "20",
        "match_persistence": "5",
        "distance_threshold": "200",
        "overlay_enabled": "true",
        "duration": "30.0",
        "update_frequency": "1.0",
        "min_confidence": "0.9",
        "use_all_templates": "true",
        "templates": ""
    }

    # Default Scanner Settings
    DEFAULT_SCANNER_SETTINGS = {
        "minimap_left": "0",
        "minimap_top": "0",
        "minimap_width": "0",
        "minimap_height": "0",
        "input_field_x": "0",
        "input_field_y": "0"
    }

    # Default OCR Settings
    DEFAULT_OCR_SETTINGS = {
        "active": "false",
        "frequency": "0.5",
        "region_left": "0",
        "region_top": "0",
        "region_width": "0",
        "region_height": "0",
        "dpi_scale": "1.0"
    }

    # Default Debug Settings
    DEFAULT_DEBUG_SETTINGS = {
        "enabled": "false",
        "save_screenshots": "true",
        "save_templates": "true",
        "debug_screenshots_dir": "scout/debug_screenshots"
    }

    # Default Template Search Settings
    DEFAULT_TEMPLATE_SEARCH_SETTINGS = {
        "overlay_enabled": "true",
        "sound_enabled": "true",
        "duration": "30.0",
        "update_frequency": "1.0",
        "min_confidence": "0.9",
        "use_all_templates": "true",
        "templates": ""
    }
    
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
        # Create default section with combined settings
        self.config.add_section("default")
        
        # Add overlay defaults
        for key, value in self.DEFAULT_OVERLAY_SETTINGS.items():
            self.config.set("default", key, value)
            
        # Add template matching defaults
        for key, value in self.DEFAULT_TEMPLATE_SETTINGS.items():
            self.config.set("default", f"template_{key}", value)
        
        # Create sections with their respective defaults
        self.config.add_section("Overlay")
        for key, value in self.DEFAULT_OVERLAY_SETTINGS.items():
            self.config.set("Overlay", key, value)
        
        self.config.add_section("template_matching")
        for key, value in self.DEFAULT_TEMPLATE_SETTINGS.items():
            self.config.set("template_matching", key, value)
        
        self.config.add_section("Scanner")
        for key, value in self.DEFAULT_SCANNER_SETTINGS.items():
            self.config.set("Scanner", key, value)
        
        self.config.add_section("OCR")
        for key, value in self.DEFAULT_OCR_SETTINGS.items():
            self.config.set("OCR", key, value)
        
        self.config.add_section("Debug")
        for key, value in self.DEFAULT_DEBUG_SETTINGS.items():
            self.config.set("Debug", key, value)
        
        self.config.add_section("TemplateSearch")
        for key, value in self.DEFAULT_TEMPLATE_SEARCH_SETTINGS.items():
            self.config.set("TemplateSearch", key, value)
        
        self.save_config()
        logger.info("Default configuration created")

    def save_config(self) -> None:
        """Save the current configuration to file."""
        with open(self.config_path, 'w') as f:
            self.config.write(f)
        logger.debug("Configuration saved")

    def get_ocr_settings(self) -> Dict[str, Any]:
        """Get OCR settings from config."""
        if not self.config.has_section("OCR"):
            self.config.add_section("OCR")
            for key, value in self.DEFAULT_OCR_SETTINGS.items():
                self.config.set("OCR", key, value)
            
        return {
            "active": self.config.getboolean("OCR", "active"),
            "frequency": self.config.getfloat("OCR", "frequency"),
            "region": {
                "left": self.config.getint("OCR", "region_left"),
                "top": self.config.getint("OCR", "region_top"),
                "width": self.config.getint("OCR", "region_width"),
                "height": self.config.getint("OCR", "region_height"),
                "dpi_scale": self.config.getfloat("OCR", "dpi_scale")
            }
        }

    def update_ocr_settings(self, settings: Dict[str, Any]) -> None:
        """Update OCR settings."""
        if not self.config.has_section("OCR"):
            self.config.add_section("OCR")
            
        # Use defaults from class constant
        defaults = self.DEFAULT_OCR_SETTINGS
        
        self.config["OCR"]["active"] = str(settings.get("active", defaults["active"])).lower()
        self.config["OCR"]["frequency"] = str(settings.get("frequency", defaults["frequency"]))
        
        region = settings.get("region", {})
        self.config["OCR"]["region_left"] = str(region.get("left", defaults["region_left"]))
        self.config["OCR"]["region_top"] = str(region.get("top", defaults["region_top"]))
        self.config["OCR"]["region_width"] = str(region.get("width", defaults["region_width"]))
        self.config["OCR"]["region_height"] = str(region.get("height", defaults["region_height"]))
        self.config["OCR"]["dpi_scale"] = str(region.get("dpi_scale", defaults["dpi_scale"]))
        
        self.save_config()
        logger.debug("Updated OCR settings")

    def get_template_matching_settings(self) -> Dict[str, Any]:
        """Get template matching settings from config."""
        if not self.config.has_section("template_matching"):
            self.config.add_section("template_matching")
            for key, value in self.DEFAULT_TEMPLATE_SETTINGS.items():
                self.config.set("template_matching", key, value)
            
        return {
            "active": self.config.getboolean("template_matching", "active"),
            "confidence": self.config.getfloat("template_matching", "confidence"),
            "target_frequency": self.config.getfloat("template_matching", "target_frequency"),
            "sound_enabled": self.config.getboolean("template_matching", "sound_enabled"),
            "templates_dir": self.config.get("template_matching", "templates_dir"),
            "grouping_threshold": self.config.getint("template_matching", "grouping_threshold"),
            "match_persistence": self.config.getint("template_matching", "match_persistence"),
            "distance_threshold": self.config.getint("template_matching", "distance_threshold"),
            "overlay_enabled": self.config.getboolean("template_matching", "overlay_enabled"),
            "duration": self.config.getfloat("template_matching", "duration"),
            "update_frequency": self.config.getfloat("template_matching", "update_frequency"),
            "min_confidence": self.config.getfloat("template_matching", "min_confidence"),
            "use_all_templates": self.config.getboolean("template_matching", "use_all_templates"),
            "templates": self.config.get("template_matching", "templates").split(",") if self.config.get("template_matching", "templates") else []
        }

    def update_template_matching_settings(self, settings: Dict[str, Any]) -> None:
        """Update template matching settings."""
        if not self.config.has_section("template_matching"):
            self.config.add_section("template_matching")
            
        # Update all template matching settings
        for key, default_value in self.DEFAULT_TEMPLATE_SETTINGS.items():
            value = settings.get(key, default_value)
            # Handle templates list specially
            if key == "templates" and isinstance(value, list):
                value = ",".join(value)
            self.config.set("template_matching", key, str(value))
        
        self.save_config()
        logger.debug("Updated template matching settings")

    def get_overlay_settings(self) -> Dict[str, Any]:
        """Get overlay settings from config."""
        if not self.config.has_section("Overlay"):
            self.config.add_section("Overlay")
            for key, value in self.DEFAULT_OVERLAY_SETTINGS.items():
                self.config.set("Overlay", key, value)
            
        return {
            "active": self.config.getboolean("Overlay", "active"),
            "rect_color": QColor(
                self.config.getint("Overlay", "rect_color_r"),
                self.config.getint("Overlay", "rect_color_g"),
                self.config.getint("Overlay", "rect_color_b")
            ),
            "rect_thickness": self.config.getint("Overlay", "rect_thickness"),
            "rect_scale": self.config.getfloat("Overlay", "rect_scale"),
            "font_color": QColor(
                self.config.getint("Overlay", "font_color_r"),
                self.config.getint("Overlay", "font_color_g"),
                self.config.getint("Overlay", "font_color_b")
            ),
            "font_size": self.config.getint("Overlay", "font_size"),
            "text_thickness": self.config.getint("Overlay", "text_thickness"),
            "cross_color": QColor(
                self.config.getint("Overlay", "cross_color_r"),
                self.config.getint("Overlay", "cross_color_g"),
                self.config.getint("Overlay", "cross_color_b")
            ),
            "cross_size": self.config.getint("Overlay", "cross_size"),
            "cross_thickness": self.config.getint("Overlay", "cross_thickness"),
            "cross_scale": self.config.getfloat("Overlay", "cross_scale")
        }

    def update_overlay_settings(self, settings: Dict[str, Any]) -> None:
        """Update overlay settings."""
        if not self.config.has_section("Overlay"):
            self.config.add_section("Overlay")
            
        # Use defaults from class constant
        defaults = self.DEFAULT_OVERLAY_SETTINGS
            
        self.config["Overlay"]["active"] = str(settings.get("active", defaults["active"])).lower()
        
        rect_color = settings.get("rect_color", QColor(
            int(defaults["rect_color_r"]),
            int(defaults["rect_color_g"]),
            int(defaults["rect_color_b"])
        ))
        self.config["Overlay"]["rect_color_r"] = str(rect_color.red())
        self.config["Overlay"]["rect_color_g"] = str(rect_color.green())
        self.config["Overlay"]["rect_color_b"] = str(rect_color.blue())
        
        self.config["Overlay"]["rect_thickness"] = str(settings.get("rect_thickness", defaults["rect_thickness"]))
        self.config["Overlay"]["rect_scale"] = str(settings.get("rect_scale", defaults["rect_scale"]))
        
        font_color = settings.get("font_color", QColor(
            int(defaults["font_color_r"]),
            int(defaults["font_color_g"]),
            int(defaults["font_color_b"])
        ))
        self.config["Overlay"]["font_color_r"] = str(font_color.red())
        self.config["Overlay"]["font_color_g"] = str(font_color.green())
        self.config["Overlay"]["font_color_b"] = str(font_color.blue())
        
        self.config["Overlay"]["font_size"] = str(settings.get("font_size", defaults["font_size"]))
        self.config["Overlay"]["text_thickness"] = str(settings.get("text_thickness", defaults["text_thickness"]))
        
        cross_color = settings.get("cross_color", QColor(
            int(defaults["cross_color_r"]),
            int(defaults["cross_color_g"]),
            int(defaults["cross_color_b"])
        ))
        self.config["Overlay"]["cross_color_r"] = str(cross_color.red())
        self.config["Overlay"]["cross_color_g"] = str(cross_color.green())
        self.config["Overlay"]["cross_color_b"] = str(cross_color.blue())
        
        self.config["Overlay"]["cross_size"] = str(settings.get("cross_size", defaults["cross_size"]))
        self.config["Overlay"]["cross_thickness"] = str(settings.get("cross_thickness", defaults["cross_thickness"]))
        self.config["Overlay"]["cross_scale"] = str(settings.get("cross_scale", defaults["cross_scale"]))
        
        self.save_config()
        logger.debug("Updated overlay settings")

    def get_scanner_settings(self) -> Dict[str, Any]:
        """Get scanner settings from config."""
        if not self.config.has_section("Scanner"):
            self.config.add_section("Scanner")
            for key, value in self.DEFAULT_SCANNER_SETTINGS.items():
                self.config.set("Scanner", key, value)
            
        return {
            "minimap_left": self.config.getint("Scanner", "minimap_left"),
            "minimap_top": self.config.getint("Scanner", "minimap_top"),
            "minimap_width": self.config.getint("Scanner", "minimap_width"),
            "minimap_height": self.config.getint("Scanner", "minimap_height"),
            "input_field_x": self.config.getint("Scanner", "input_field_x"),
            "input_field_y": self.config.getint("Scanner", "input_field_y")
        }

    def update_scanner_settings(self, settings: Dict[str, Any]) -> None:
        """Update scanner settings."""
        if not self.config.has_section("Scanner"):
            self.config.add_section("Scanner")
            
        # Use defaults from class constant
        defaults = self.DEFAULT_SCANNER_SETTINGS
        
        for key in defaults:
            self.config["Scanner"][key] = str(settings.get(key, defaults[key]))
            
        self.save_config()
        logger.debug("Updated scanner settings")

    def get_debug_settings(self) -> Dict[str, Any]:
        """Get debug settings from config."""
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            for key, value in self.DEFAULT_DEBUG_SETTINGS.items():
                self.config.set("Debug", key, value)
            
        return {
            "enabled": self.config.getboolean("Debug", "enabled"),
            "save_screenshots": self.config.getboolean("Debug", "save_screenshots"),
            "save_templates": self.config.getboolean("Debug", "save_templates"),
            "debug_screenshots_dir": self.config.get("Debug", "debug_screenshots_dir")
        }

    def update_debug_settings(self, settings: Dict[str, bool]) -> None:
        """Update debug settings."""
        if not self.config.has_section("Debug"):
            self.config.add_section("Debug")
            
        # Use defaults from class constant
        defaults = self.DEFAULT_DEBUG_SETTINGS
        
        for key in defaults:
            self.config["Debug"][key] = str(settings.get(key, defaults[key])).lower()
            
        self.save_config()
        logger.debug("Updated debug settings")

    def get_template_search_settings(self) -> Dict[str, Any]:
        """Get template search settings."""
        if not self.config.has_section("TemplateSearch"):
            self.config.add_section("TemplateSearch")
            for key, value in self.DEFAULT_TEMPLATE_SEARCH_SETTINGS.items():
                self.config.set("TemplateSearch", key, value)
            
        return {
            "overlay_enabled": self.config.getboolean("TemplateSearch", "overlay_enabled"),
            "sound_enabled": self.config.getboolean("TemplateSearch", "sound_enabled"),
            "duration": self.config.getfloat("TemplateSearch", "duration"),
            "update_frequency": self.config.getfloat("TemplateSearch", "update_frequency"),
            "min_confidence": self.config.getfloat("TemplateSearch", "min_confidence"),
            "use_all_templates": self.config.getboolean("TemplateSearch", "use_all_templates"),
            "templates": self.config.get("TemplateSearch", "templates").split(",") if self.config.get("TemplateSearch", "templates") else []
        }

    def update_template_search_settings(self, settings: Dict[str, Any]) -> None:
        """Update template search settings."""
        if not self.config.has_section("TemplateSearch"):
            self.config.add_section("TemplateSearch")
            
        # Use defaults from class constant
        defaults = self.DEFAULT_TEMPLATE_SEARCH_SETTINGS
        
        # Update all template search settings
        for key, default_value in defaults.items():
            value = settings.get(key, default_value)
            # Handle templates list specially
            if key == "templates" and isinstance(value, list):
                value = ",".join(value)
            self.config.set("TemplateSearch", key, str(value))
        
        self.save_config()
        logger.debug("Updated template search settings")

    def _load_config(self):
        """Load the configuration file."""
        return self.config

    def _save_config(self, config):
        """Save the configuration file."""
        with open(self.config_path, 'w') as f:
            config.write(f)
        logger.debug("Configuration saved")

    def revert_to_defaults(self) -> Dict[str, Any]:
        """
        Revert all settings to defaults.
        
        Returns:
            Dict containing the default settings that were applied
        """
        # Revert each section to its defaults
        sections_and_defaults = [
            ("Overlay", self.DEFAULT_OVERLAY_SETTINGS),
            ("template_matching", self.DEFAULT_TEMPLATE_SETTINGS),
            ("Scanner", self.DEFAULT_SCANNER_SETTINGS),
            ("OCR", self.DEFAULT_OCR_SETTINGS),
            ("Debug", self.DEFAULT_DEBUG_SETTINGS),
            ("TemplateSearch", self.DEFAULT_TEMPLATE_SEARCH_SETTINGS)
        ]
        
        for section_name, defaults in sections_and_defaults:
            if self.config.has_section(section_name):
                self.config.remove_section(section_name)
            self.config.add_section(section_name)
            for key, value in defaults.items():
                self.config.set(section_name, key, value)
        
        # Save changes
        self.save_config()
        logger.info("Settings reverted to defaults")
        
        # Return settings in the format expected by the GUI
        return {
            "overlay": {
                "active": True,  # Convert from string "true"
                "rect_color": QColor(
                    int(self.DEFAULT_OVERLAY_SETTINGS["rect_color_r"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["rect_color_g"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["rect_color_b"])
                ),
                "rect_thickness": int(self.DEFAULT_OVERLAY_SETTINGS["rect_thickness"]),
                "rect_scale": float(self.DEFAULT_OVERLAY_SETTINGS["rect_scale"]),
                "font_color": QColor(
                    int(self.DEFAULT_OVERLAY_SETTINGS["font_color_r"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["font_color_g"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["font_color_b"])
                ),
                "font_size": int(self.DEFAULT_OVERLAY_SETTINGS["font_size"]),
                "text_thickness": int(self.DEFAULT_OVERLAY_SETTINGS["text_thickness"]),
                "cross_color": QColor(
                    int(self.DEFAULT_OVERLAY_SETTINGS["cross_color_r"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["cross_color_g"]),
                    int(self.DEFAULT_OVERLAY_SETTINGS["cross_color_b"])
                ),
                "cross_size": int(self.DEFAULT_OVERLAY_SETTINGS["cross_size"]),
                "cross_thickness": int(self.DEFAULT_OVERLAY_SETTINGS["cross_thickness"]),
                "cross_scale": float(self.DEFAULT_OVERLAY_SETTINGS["cross_scale"])
            },
            "template_matching": {
                "active": self.DEFAULT_TEMPLATE_SETTINGS["active"].lower() == "true",
                "confidence": float(self.DEFAULT_TEMPLATE_SETTINGS["confidence"]),
                "target_frequency": float(self.DEFAULT_TEMPLATE_SETTINGS["target_frequency"]),
                "sound_enabled": self.DEFAULT_TEMPLATE_SETTINGS["sound_enabled"].lower() == "true",
                "templates_dir": self.DEFAULT_TEMPLATE_SETTINGS["templates_dir"],
                "grouping_threshold": int(self.DEFAULT_TEMPLATE_SETTINGS["grouping_threshold"]),
                "match_persistence": int(self.DEFAULT_TEMPLATE_SETTINGS["match_persistence"]),
                "distance_threshold": int(self.DEFAULT_TEMPLATE_SETTINGS["distance_threshold"]),
                "overlay_enabled": self.DEFAULT_TEMPLATE_SETTINGS["overlay_enabled"].lower() == "true",
                "duration": float(self.DEFAULT_TEMPLATE_SETTINGS["duration"]),
                "update_frequency": float(self.DEFAULT_TEMPLATE_SETTINGS["update_frequency"]),
                "min_confidence": float(self.DEFAULT_TEMPLATE_SETTINGS["min_confidence"]),
                "use_all_templates": self.DEFAULT_TEMPLATE_SETTINGS["use_all_templates"].lower() == "true",
                "templates": self.DEFAULT_TEMPLATE_SETTINGS["templates"].split(",") if self.DEFAULT_TEMPLATE_SETTINGS["templates"] else []
            },
            "scanner": {
                "minimap_left": int(self.DEFAULT_SCANNER_SETTINGS["minimap_left"]),
                "minimap_top": int(self.DEFAULT_SCANNER_SETTINGS["minimap_top"]),
                "minimap_width": int(self.DEFAULT_SCANNER_SETTINGS["minimap_width"]),
                "minimap_height": int(self.DEFAULT_SCANNER_SETTINGS["minimap_height"]),
                "input_field_x": int(self.DEFAULT_SCANNER_SETTINGS["input_field_x"]),
                "input_field_y": int(self.DEFAULT_SCANNER_SETTINGS["input_field_y"])
            },
            "ocr": {
                "active": self.DEFAULT_OCR_SETTINGS["active"].lower() == "true",
                "frequency": float(self.DEFAULT_OCR_SETTINGS["frequency"]),
                "region": {
                    "left": int(self.DEFAULT_OCR_SETTINGS["region_left"]),
                    "top": int(self.DEFAULT_OCR_SETTINGS["region_top"]),
                    "width": int(self.DEFAULT_OCR_SETTINGS["region_width"]),
                    "height": int(self.DEFAULT_OCR_SETTINGS["region_height"]),
                    "dpi_scale": float(self.DEFAULT_OCR_SETTINGS["dpi_scale"])
                }
            },
            "debug": {
                "enabled": self.DEFAULT_DEBUG_SETTINGS["enabled"].lower() == "true",
                "save_screenshots": self.DEFAULT_DEBUG_SETTINGS["save_screenshots"].lower() == "true",
                "save_templates": self.DEFAULT_DEBUG_SETTINGS["save_templates"].lower() == "true",
                "debug_screenshots_dir": self.DEFAULT_DEBUG_SETTINGS["debug_screenshots_dir"]
            },
            "template_search": {
                "overlay_enabled": self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["overlay_enabled"].lower() == "true",
                "sound_enabled": self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["sound_enabled"].lower() == "true",
                "duration": float(self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["duration"]),
                "update_frequency": float(self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["update_frequency"]),
                "min_confidence": float(self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["min_confidence"]),
                "use_all_templates": self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["use_all_templates"].lower() == "true",
                "templates": self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["templates"].split(",") if self.DEFAULT_TEMPLATE_SEARCH_SETTINGS["templates"] else []
            }
        } 