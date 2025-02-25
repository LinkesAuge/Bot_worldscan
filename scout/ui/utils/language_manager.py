"""
Language Manager

This module provides centralized language management for the Scout application.
It supports multiple languages and provides methods to apply translations across
the application.
"""

import os
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QTranslator, QLocale, QCoreApplication, QSettings, QLibraryInfo

# Set up logging
logger = logging.getLogger(__name__)

class Language(Enum):
    """Enumeration of supported languages."""
    SYSTEM = "system"  # Use system language
    ENGLISH = "en"     # English
    GERMAN = "de"      # German

class LanguageManager:
    """
    Centralized language manager for the Scout application.
    
    This class handles:
    - Switching between different languages
    - Loading translations from files
    - Applying translations to the application
    - Persisting language preferences
    
    The LanguageManager ensures consistent localization throughout the
    application, allowing users to switch between supported languages
    at runtime.
    """
    
    # Default translation paths
    TRANSLATIONS_DIR = Path("scout/translations")
    
    def __init__(self):
        """Initialize the language manager."""
        # Create necessary directories
        if not self.TRANSLATIONS_DIR.exists():
            self.TRANSLATIONS_DIR.mkdir(parents=True)
            logger.info(f"Created translations directory: {self.TRANSLATIONS_DIR}")
        
        # Initialize translators
        self._application_translator = QTranslator()
        self._qt_translator = QTranslator()
        
        # Current language setting
        self._current_language = Language.SYSTEM
        
        # Load saved language settings
        self._load_settings()
        
        # Apply current language
        self._apply_current_language()
        
        logger.info(f"LanguageManager initialized with language: {self._current_language.value}")
    
    def _load_settings(self) -> None:
        """Load language settings from QSettings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Load language
        language_str = settings.value("language/current", Language.SYSTEM.value)
        try:
            self._current_language = Language(language_str)
        except ValueError:
            logger.warning(f"Invalid language: {language_str}, using system language")
            self._current_language = Language.SYSTEM
            
        logger.debug(f"Loaded language setting: {self._current_language.value}")
    
    def _save_settings(self) -> None:
        """Save language settings to QSettings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Save language
        settings.setValue("language/current", self._current_language.value)
            
        logger.debug(f"Saved language setting: {self._current_language.value}")
    
    def get_current_language(self) -> Language:
        """
        Get the current language.
        
        Returns:
            Current language
        """
        return self._current_language
    
    def set_language(self, language: Language) -> bool:
        """
        Set the application language.
        
        Args:
            language: Language to set
            
        Returns:
            True if language was set successfully, False otherwise
        """
        # Store language setting
        self._current_language = language
        
        # Apply language
        success = self._apply_current_language()
        
        # Save settings if successful
        if success:
            self._save_settings()
            logger.info(f"Language changed to: {language.value}")
        else:
            logger.error(f"Failed to apply language: {language.value}")
            
        return success
    
    def _apply_current_language(self) -> bool:
        """
        Apply the current language to the application.
        
        Returns:
            True if language was applied successfully, False otherwise
        """
        # Get application instance
        app = QCoreApplication.instance()
        if not app:
            logger.error("No QCoreApplication instance found")
            return False
        
        # Remove existing translators
        app.removeTranslator(self._application_translator)
        app.removeTranslator(self._qt_translator)
        
        try:
            # Determine locale to use
            if self._current_language == Language.SYSTEM:
                # Use system locale
                locale = QLocale.system()
                logger.debug(f"Using system locale: {locale.name()}")
            else:
                # Use specified language
                locale = QLocale(self._current_language.value)
                logger.debug(f"Using specified locale: {locale.name()}")
            
            # Install Qt translations
            self._qt_translator = QTranslator()
            qt_translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
            if self._qt_translator.load(locale, "qtbase", "_", qt_translations_path):
                app.installTranslator(self._qt_translator)
                logger.debug(f"Loaded Qt translations for {locale.name()}")
            else:
                logger.warning(f"Failed to load Qt translations for {locale.name()}")
            
            # Install application translations
            self._application_translator = QTranslator()
            if self._current_language != Language.ENGLISH:  # English is the base language
                translation_file = self.TRANSLATIONS_DIR / f"scout_{locale.name()}"
                if self._application_translator.load(str(translation_file)):
                    app.installTranslator(self._application_translator)
                    logger.info(f"Loaded application translations for {locale.name()}")
                else:
                    logger.warning(f"Failed to load application translations for {locale.name()}")
                    # We don't return False here since we may be missing translations
                    # but want to continue with partial translation
            
            # Success
            logger.info(f"Applied language: {locale.name()}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying language: {str(e)}")
            return False
    
    def refresh_translations(self) -> None:
        """
        Refresh all translations.
        
        This forces a reload of translation files and reapplication of translations.
        """
        self._apply_current_language()

# Singleton instance
_language_manager = None

def get_language_manager() -> LanguageManager:
    """
    Get the singleton language manager instance.
    
    Returns:
        Language manager instance
    """
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager

def tr(source_text: str, context: str = None, n: int = -1) -> str:
    """
    Translate a string.
    
    This is a convenience function for translating strings outside of a QObject context.
    It's similar to the tr() method in Qt classes.
    
    Args:
        source_text: Text to translate
        context: Optional context for the translation
        n: Number for plural forms, -1 if not a plural form
        
    Returns:
        Translated string, or source string if no translation is available
    """
    app = QCoreApplication.instance()
    if app:
        if context:
            return app.translate(context, source_text, None, n)
        else:
            return app.translate("", source_text, None, n)
    return source_text 