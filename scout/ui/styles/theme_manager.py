"""
Theme Manager

This module provides centralized theme management for the Scout application.
It supports light, dark, system, and custom themes, and provides methods
to apply these themes consistently across the application.
"""

import os
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, QSettings

# Set up logging
logger = logging.getLogger(__name__)

class ThemeType(Enum):
    """Enumeration of supported theme types."""
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"


class ThemeManager:
    """
    Centralized theme manager for the Scout application.
    
    This class handles:
    - Switching between light, dark, and system themes
    - Loading custom themes from QSS stylesheets
    - Applying consistent styling to all application widgets
    - Persisting theme preferences
    
    It ensures a consistent look and feel across the entire application
    and allows for easy theming customization.
    """
    
    # Default stylesheet paths
    STYLESHEET_DIR = Path("scout/ui/styles")
    LIGHT_STYLESHEET = STYLESHEET_DIR / "light.qss"
    DARK_STYLESHEET = STYLESHEET_DIR / "dark.qss"
    
    # Color schemes for different themes
    COLOR_SCHEMES = {
        ThemeType.LIGHT: {
            # Background colors
            "background": "#F5F5F5",
            "background_alt": "#EBEBEB",
            "background_highlight": "#FFFFFF",
            
            # Foreground colors
            "foreground": "#333333",
            "foreground_alt": "#666666",
            "foreground_inactive": "#999999",
            
            # Accent colors
            "accent_primary": "#0078D7",
            "accent_secondary": "#00B0FF",
            "accent_tertiary": "#60CDFF",
            
            # Status colors
            "success": "#0BA545",
            "warning": "#FFB74D",
            "error": "#EF5350",
            "info": "#29B6F6"
        },
        ThemeType.DARK: {
            # Background colors
            "background": "#2D2D2D",
            "background_alt": "#363636",
            "background_highlight": "#444444",
            
            # Foreground colors
            "foreground": "#E0E0E0",
            "foreground_alt": "#B0B0B0",
            "foreground_inactive": "#808080",
            
            # Accent colors
            "accent_primary": "#60CDFF",
            "accent_secondary": "#00B0FF",
            "accent_tertiary": "#0078D7",
            
            # Status colors
            "success": "#4CAF50",
            "warning": "#FFA726",
            "error": "#F44336",
            "info": "#29B6F6"
        }
    }
    
    def __init__(self):
        """Initialize the theme manager."""
        # Create necessary directories
        if not self.STYLESHEET_DIR.exists():
            self.STYLESHEET_DIR.mkdir(parents=True)
            logger.info(f"Created stylesheet directory: {self.STYLESHEET_DIR}")
        
        # Current theme settings
        self._current_theme_type = ThemeType.SYSTEM
        self._custom_stylesheet_path = None
        
        # Create default stylesheets if they don't exist
        self._ensure_default_stylesheets()
        
        # Load saved theme settings
        self._load_settings()
    
    def _ensure_default_stylesheets(self) -> None:
        """Create default stylesheet files if they don't exist."""
        # Ensure light theme stylesheet exists
        if not self.LIGHT_STYLESHEET.exists():
            self._create_default_light_stylesheet()
        
        # Ensure dark theme stylesheet exists
        if not self.DARK_STYLESHEET.exists():
            self._create_default_dark_stylesheet()
            
    def _create_default_light_stylesheet(self) -> None:
        """Create default light theme stylesheet."""
        stylesheet = """
        /* Light Theme Stylesheet for Scout */
        
        /* Global Styles */
        QWidget {
            background-color: #F5F5F5;
            color: #333333;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        
        /* Main Window */
        QMainWindow {
            background-color: #F5F5F5;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: #FFFFFF;
            border-bottom: 1px solid #E0E0E0;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 10px;
        }
        
        QMenuBar::item:selected {
            background-color: #E0E0E0;
        }
        
        QMenu {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
        }
        
        QMenu::item {
            padding: 6px 20px;
        }
        
        QMenu::item:selected {
            background-color: #E0E0E0;
        }
        
        /* Tool Bar */
        QToolBar {
            background-color: #FFFFFF;
            border-bottom: 1px solid #E0E0E0;
            spacing: 3px;
        }
        
        QToolButton {
            border: none;
            padding: 4px;
            border-radius: 4px;
        }
        
        QToolButton:hover {
            background-color: #E0E0E0;
        }
        
        QToolButton:pressed {
            background-color: #D0D0D0;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #FFFFFF;
            border-top: 1px solid #E0E0E0;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #E0E0E0;
            border-top: none;
        }
        
        QTabBar::tab {
            background-color: #EBEBEB;
            border: 1px solid #E0E0E0;
            border-bottom: none;
            padding: 6px 12px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #FFFFFF;
            border-bottom: none;
        }
        
        /* Group Box */
        QGroupBox {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 3px;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #F0F0F0;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 6px 12px;
        }
        
        QPushButton:hover {
            background-color: #E0E0E0;
        }
        
        QPushButton:pressed {
            background-color: #D0D0D0;
        }
        
        QPushButton:disabled {
            background-color: #F5F5F5;
            color: #999999;
            border-color: #DDDDDD;
        }
        
        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #FFFFFF;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 4px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #0078D7;
        }
        
        /* Lists and Trees */
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #FFFFFF;
            alternate-background-color: #F9F9F9;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        
        QListWidget::item, QTreeWidget::item, QTableWidget::item {
            padding: 4px;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
            background-color: #E0E0E0;
            color: #333333;
        }
        
        QTableWidget QHeaderView::section {
            background-color: #F0F0F0;
            padding: 4px;
            border: 1px solid #E0E0E0;
            border-bottom: none;
        }
        
        /* Sliders and Progress Bars */
        QSlider::groove:horizontal {
            height: 8px;
            background-color: #E0E0E0;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background-color: #0078D7;
            width: 16px;
            margin: -4px 0;
            border-radius: 8px;
        }
        
        QProgressBar {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            background-color: #FFFFFF;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #0078D7;
            width: 1px;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            border: none;
            background-color: #F0F0F0;
            width: 12px;
            margin: 12px 0 12px 0;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #CCCCCC;
            min-height: 20px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #BBBBBB;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 12px;
        }
        
        QScrollBar:horizontal {
            border: none;
            background-color: #F0F0F0;
            height: 12px;
            margin: 0 12px 0 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #CCCCCC;
            min-width: 20px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #BBBBBB;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 12px;
        }
        """
        
        # Write stylesheet to file
        with open(self.LIGHT_STYLESHEET, 'w') as f:
            f.write(stylesheet)
            
        logger.info(f"Created default light stylesheet at: {self.LIGHT_STYLESHEET}")
    
    def _create_default_dark_stylesheet(self) -> None:
        """Create default dark theme stylesheet."""
        stylesheet = """
        /* Dark Theme Stylesheet for Scout */
        
        /* Global Styles */
        QWidget {
            background-color: #2D2D2D;
            color: #E0E0E0;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        
        /* Main Window */
        QMainWindow {
            background-color: #2D2D2D;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: #363636;
            border-bottom: 1px solid #222222;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 10px;
        }
        
        QMenuBar::item:selected {
            background-color: #404040;
        }
        
        QMenu {
            background-color: #363636;
            border: 1px solid #222222;
        }
        
        QMenu::item {
            padding: 6px 20px;
        }
        
        QMenu::item:selected {
            background-color: #404040;
        }
        
        /* Tool Bar */
        QToolBar {
            background-color: #363636;
            border-bottom: 1px solid #222222;
            spacing: 3px;
        }
        
        QToolButton {
            border: none;
            padding: 4px;
            border-radius: 4px;
        }
        
        QToolButton:hover {
            background-color: #404040;
        }
        
        QToolButton:pressed {
            background-color: #505050;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #363636;
            border-top: 1px solid #222222;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #222222;
            border-top: none;
        }
        
        QTabBar::tab {
            background-color: #363636;
            border: 1px solid #222222;
            border-bottom: none;
            padding: 6px 12px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #404040;
            border-bottom: none;
        }
        
        /* Group Box */
        QGroupBox {
            border: 1px solid #222222;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 3px;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #444444;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 6px 12px;
            color: #E0E0E0;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #606060;
        }
        
        QPushButton:disabled {
            background-color: #2D2D2D;
            color: #666666;
            border-color: #333333;
        }
        
        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #363636;
            border: 1px solid #222222;
            border-radius: 4px;
            padding: 4px;
            color: #E0E0E0;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #60CDFF;
        }
        
        /* Lists and Trees */
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #363636;
            alternate-background-color: #404040;
            border: 1px solid #222222;
            border-radius: 4px;
            color: #E0E0E0;
        }
        
        QListWidget::item, QTreeWidget::item, QTableWidget::item {
            padding: 4px;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
            background-color: #505050;
            color: #FFFFFF;
        }
        
        QTableWidget QHeaderView::section {
            background-color: #444444;
            padding: 4px;
            border: 1px solid #222222;
            border-bottom: none;
        }
        
        /* Sliders and Progress Bars */
        QSlider::groove:horizontal {
            height: 8px;
            background-color: #222222;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background-color: #60CDFF;
            width: 16px;
            margin: -4px 0;
            border-radius: 8px;
        }
        
        QProgressBar {
            border: 1px solid #222222;
            border-radius: 4px;
            background-color: #363636;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #60CDFF;
            width: 1px;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            border: none;
            background-color: #2D2D2D;
            width: 12px;
            margin: 12px 0 12px 0;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #505050;
            min-height: 20px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #606060;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 12px;
        }
        
        QScrollBar:horizontal {
            border: none;
            background-color: #2D2D2D;
            height: 12px;
            margin: 0 12px 0 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #505050;
            min-width: 20px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #606060;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 12px;
        }
        """
        
        # Write stylesheet to file
        with open(self.DARK_STYLESHEET, 'w') as f:
            f.write(stylesheet)
            
        logger.info(f"Created default dark stylesheet at: {self.DARK_STYLESHEET}")
    
    def _load_settings(self) -> None:
        """Load theme settings from QSettings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Load theme type
        theme_str = settings.value("theme/type", ThemeType.SYSTEM.value)
        try:
            self._current_theme_type = ThemeType(theme_str)
        except ValueError:
            logger.warning(f"Invalid theme type: {theme_str}, using system theme")
            self._current_theme_type = ThemeType.SYSTEM
        
        # Load custom stylesheet path
        custom_path = settings.value("theme/custom_path", "")
        if custom_path and os.path.exists(custom_path):
            self._custom_stylesheet_path = custom_path
        else:
            self._custom_stylesheet_path = None
            
        logger.debug(f"Loaded theme settings: {self._current_theme_type.value}, custom: {self._custom_stylesheet_path}")
    
    def _save_settings(self) -> None:
        """Save theme settings to QSettings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Save theme type
        settings.setValue("theme/type", self._current_theme_type.value)
        
        # Save custom stylesheet path
        if self._custom_stylesheet_path:
            settings.setValue("theme/custom_path", self._custom_stylesheet_path)
        else:
            settings.remove("theme/custom_path")
            
        logger.debug(f"Saved theme settings: {self._current_theme_type.value}, custom: {self._custom_stylesheet_path}")
    
    def get_current_theme(self) -> ThemeType:
        """
        Get the current theme type.
        
        Returns:
            Current theme type
        """
        return self._current_theme_type
    
    def set_theme(self, theme_type: ThemeType, custom_path: Optional[str] = None) -> bool:
        """
        Set the application theme.
        
        Args:
            theme_type: Type of theme to set
            custom_path: Path to custom QSS file (only for ThemeType.CUSTOM)
            
        Returns:
            True if theme was set successfully, False otherwise
        """
        # Validate inputs
        if theme_type == ThemeType.CUSTOM and not custom_path:
            logger.error("Custom theme requires stylesheet path")
            return False
            
        if custom_path and not os.path.exists(custom_path):
            logger.error(f"Custom stylesheet not found: {custom_path}")
            return False
        
        # Store theme settings
        self._current_theme_type = theme_type
        self._custom_stylesheet_path = custom_path if theme_type == ThemeType.CUSTOM else None
        
        # Apply theme
        success = self._apply_current_theme()
        
        # Save settings if successful
        if success:
            self._save_settings()
            
        return success
    
    def _apply_current_theme(self) -> bool:
        """
        Apply the current theme to the application.
        
        Returns:
            True if theme was applied successfully, False otherwise
        """
        app = QApplication.instance()
        if not app:
            logger.error("No QApplication instance found")
            return False
        
        try:
            # Apply theme based on type
            if self._current_theme_type == ThemeType.SYSTEM:
                # Use system default style
                app.setStyleSheet("")
                palette = app.style().standardPalette()
                app.setPalette(palette)
                logger.info("Applied system theme")
                
            elif self._current_theme_type == ThemeType.LIGHT:
                # Apply light theme
                self._apply_palette(ThemeType.LIGHT)
                self._apply_stylesheet(self.LIGHT_STYLESHEET)
                logger.info("Applied light theme")
                
            elif self._current_theme_type == ThemeType.DARK:
                # Apply dark theme
                self._apply_palette(ThemeType.DARK)
                self._apply_stylesheet(self.DARK_STYLESHEET)
                logger.info("Applied dark theme")
                
            elif self._current_theme_type == ThemeType.CUSTOM:
                # Apply custom theme
                if not self._custom_stylesheet_path:
                    logger.error("No custom stylesheet path set")
                    return False
                    
                self._apply_stylesheet(self._custom_stylesheet_path)
                logger.info(f"Applied custom theme: {self._custom_stylesheet_path}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error applying theme: {str(e)}")
            return False
    
    def _apply_palette(self, theme_type: ThemeType) -> None:
        """
        Apply color palette for the given theme type.
        
        Args:
            theme_type: Theme type to apply palette for
        """
        app = QApplication.instance()
        if not app:
            return
            
        # Get color scheme
        colors = self.COLOR_SCHEMES.get(theme_type)
        if not colors:
            return
            
        # Create palette
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["foreground"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["background_highlight"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["background_alt"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["background_highlight"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["foreground"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["foreground"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["background_alt"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["foreground"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["foreground_alt"]))
        
        # Set highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent_primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["background_highlight"]))
        
        # Set disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(colors["foreground_inactive"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors["foreground_inactive"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors["foreground_inactive"]))
        
        # Apply palette
        app.setPalette(palette)
    
    def _apply_stylesheet(self, stylesheet_path: str) -> None:
        """
        Apply stylesheet from file.
        
        Args:
            stylesheet_path: Path to QSS stylesheet file
        """
        app = QApplication.instance()
        if not app:
            return
            
        try:
            # Read stylesheet file
            with open(stylesheet_path, 'r') as f:
                stylesheet = f.read()
                
            # Apply stylesheet
            app.setStyleSheet(stylesheet)
            
        except Exception as e:
            logger.error(f"Error applying stylesheet from {stylesheet_path}: {str(e)}")
    
    def get_theme_colors(self) -> Dict[str, str]:
        """
        Get color scheme for current theme.
        
        Returns:
            Dictionary of color names to hex color values
        """
        # Determine theme type to use
        theme_type = self._current_theme_type
        
        # Default to system theme based on application palette
        if theme_type == ThemeType.SYSTEM:
            app = QApplication.instance()
            if not app:
                return {}
                
            palette = app.palette()
            is_dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
            theme_type = ThemeType.DARK if is_dark else ThemeType.LIGHT
            
        # Return color scheme for theme type
        return self.COLOR_SCHEMES.get(theme_type, {})
    
    def is_dark_theme(self) -> bool:
        """
        Check if current theme is dark.
        
        Returns:
            True if using dark theme, False otherwise
        """
        if self._current_theme_type == ThemeType.DARK:
            return True
            
        if self._current_theme_type == ThemeType.SYSTEM:
            app = QApplication.instance()
            if not app:
                return False
                
            palette = app.palette()
            return palette.color(QPalette.ColorRole.Window).lightness() < 128
            
        return False


# Singleton instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """
    Get the singleton theme manager instance.
    
    Returns:
        Theme manager instance
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager 