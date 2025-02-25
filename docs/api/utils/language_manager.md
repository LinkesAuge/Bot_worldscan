# LanguageManager API

**Module**: `scout.ui.utils.language_manager`  
**Stability**: Stable  
**Version**: 1.0  

## Overview

The LanguageManager API provides centralized control over the application's language settings. It handles loading translations, switching between languages at runtime, and persisting language preferences between application sessions.

## Class Definition

### Language (Enum)

An enumeration of supported languages.

```python
class Language(Enum):
    SYSTEM = "system"  # Use system language
    ENGLISH = "en"     # English
    GERMAN = "de"      # German
```

### LanguageManager

A singleton class that manages application language settings.

```python
class LanguageManager:
    """
    Centralized language manager for the Scout application.
    
    This class handles:
    - Switching between different languages
    - Loading translations from files
    - Applying translations to the application
    - Persisting language preferences
    """
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| translations_dir | Path | Path to the directory containing translation files. |
| _current_language | Language | The currently selected language (private). |

## Methods

### Constructor

```python
def __init__(self)
```

Initializes the LanguageManager with default settings and loads the saved language preference.

### get_current_language

```python
def get_current_language(self) -> Language
```

Gets the currently selected language.

**Returns**:
- The current language setting (a `Language` enum value).

### set_language

```python
def set_language(self, language: Language) -> bool
```

Sets the application language and applies translations.

**Parameters**:
- `language`: A `Language` enum value specifying the language to use.

**Returns**:
- `True` if the language was set successfully, `False` otherwise.

### _load_settings

```python
def _load_settings(self) -> None
```

Loads the language setting from QSettings.

**Note**: This is a private method used internally.

### _save_settings

```python
def _save_settings(self) -> None
```

Saves the current language setting to QSettings.

**Note**: This is a private method used internally.

### _apply_current_language

```python
def _apply_current_language(self) -> bool
```

Applies the current language to the application.

**Returns**:
- `True` if the language was applied successfully, `False` otherwise.

**Note**: This is a private method used internally.

### refresh_translations

```python
def refresh_translations(self) -> None
```

Forces a reload of translation files and reapplication of translations.

## Functions

### get_language_manager

```python
def get_language_manager() -> LanguageManager
```

Gets the singleton instance of the LanguageManager.

**Returns**:
- The LanguageManager instance.

### tr

```python
def tr(source_text: str, context: str = None, n: int = -1) -> str
```

Translates a string to the current language.

**Parameters**:
- `source_text`: The text to translate.
- `context`: Optional context for the translation (helps disambiguate).
- `n`: Number for plural forms, -1 if not a plural form.

**Returns**:
- The translated string, or the source string if no translation is available.

## Usage Examples

### Getting the Language Manager

```python
from scout.ui.utils.language_manager import get_language_manager

# Get the language manager instance
language_manager = get_language_manager()
```

### Checking Current Language

```python
from scout.ui.utils.language_manager import get_language_manager, Language

language_manager = get_language_manager()
current_language = language_manager.get_current_language()

if current_language == Language.GERMAN:
    print("Die Anwendung ist auf Deutsch eingestellt.")
else:
    print("The application is set to English.")
```

### Changing Language

```python
from scout.ui.utils.language_manager import get_language_manager, Language

language_manager = get_language_manager()

# Switch to German
success = language_manager.set_language(Language.GERMAN)
if success:
    print("Language changed to German")
else:
    print("Failed to change language")
```

### Translating Text

```python
from scout.ui.utils.language_manager import tr

# Simple translation
button_text = tr("Save")

# Translation with context (for disambiguation)
menu_text = tr("Open", "FileMenu")

# Translation with plural form
file_count = 5
status_text = tr("%n file(s) found", n=file_count)
```

## Events

The LanguageManager does not emit events directly. Language changes are applied immediately and reflected in the UI through Qt's translation mechanism.

## Notes

- Language changes take effect immediately for most UI elements, but some elements may require a restart of the application to fully update.
- When set to `Language.SYSTEM`, the LanguageManager attempts to use the operating system's language if it is supported, or falls back to English.
- Language preferences are stored in the application settings and persist between sessions.

## Related APIs

- [LayoutHelper](layout_helper.md) - For handling layout adaptability with different languages 