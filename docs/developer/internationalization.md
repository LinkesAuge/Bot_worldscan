# Internationalization

Scout is designed with multilanguage support from the ground up. This guide explains how the internationalization (i18n) system works, how to use it effectively, and how to extend it with additional languages.

## Architecture Overview

The internationalization system in Scout consists of the following key components:

1. **LanguageManager**: A singleton class that manages language switching and persistence.
2. **Translation Files**: XML-based `.ts` files and compiled binary `.qm` files.
3. **Translation Functions**: Utility functions for marking strings for translation.
4. **Layout Helper Utilities**: Functions to handle UI layout adaptability for different languages.

### Directory Structure

```
scout/
├── ui/
│   ├── utils/
│   │   ├── language_manager.py   # Main language management
│   │   └── layout_helper.py      # UI layout adaptability helpers
├── translations/
│   ├── scout_en.ts     # English translation source
│   ├── scout_en.qm     # Compiled English translation
│   ├── scout_de.ts     # German translation source
│   ├── scout_de.qm     # Compiled German translation
│   ├── config.py       # Translation configuration
│   ├── create_ts_files.py  # Tool to extract strings
│   ├── compile_translations.py  # Tool to compile .ts to .qm
│   └── verify_translations.py   # Tool to verify translations
```

## Language Manager

The `LanguageManager` (in `scout/ui/utils/language_manager.py`) is the central component of the i18n system:

```python
class LanguageManager:
    """
    Centralized language manager for the Scout application.
    """
    
    def get_current_language(self) -> Language:
        """Get the current language."""
        # ...
    
    def set_language(self, language: Language) -> bool:
        """Set the application language."""
        # ...
```

Key features:
- Singleton pattern ensures consistent language state throughout the application
- Handles loading translation files
- Manages language preferences using QSettings
- Provides methods for switching languages at runtime
- System language detection and fallback

### Using the Language Manager

To get the language manager instance:

```python
from scout.ui.utils.language_manager import get_language_manager

# Get the language manager instance
language_manager = get_language_manager()

# Get current language
current_language = language_manager.get_current_language()

# Change language
language_manager.set_language(Language.GERMAN)
```

## Marking Strings for Translation

There are two main ways to mark strings for translation:

### 1. tr() Function

For static text outside of QObject-derived classes:

```python
from scout.ui.utils.language_manager import tr

# Simple translation
label_text = tr("Settings")

# Translation with context
button_text = tr("Save", "MainWindow")

# Translation with plural form
message = tr("%n file(s) found", n=count)
```

### 2. QObject.tr() Method

For classes derived from QObject (most Qt classes):

```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Use self.tr() for translations in QObject-derived classes
        label = QLabel(self.tr("Settings"))
        
        # With context
        button = QPushButton(self.tr("Save", "Button"))
        
        # With plural form
        status = self.tr("%n item(s) selected", "", count)
```

## Translation Files

Scout uses Qt's translation system with `.ts` (translation source) and `.qm` (compiled binary) files.

### TS File Structure

Translation files are XML-based and organized by context:

```xml
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en_US">
<context>
    <name>MainWindow</name>
    <message>
        <source>File</source>
        <translation>Datei</translation>
    </message>
    <message>
        <source>Edit</source>
        <translation>Bearbeiten</translation>
    </message>
</context>
<context>
    <name>SettingsTab</name>
    <message>
        <source>Language</source>
        <translation>Sprache</translation>
    </message>
</context>
</TS>
```

## Translation Workflow

### 1. Mark Strings for Translation

Use `tr()` or `self.tr()` for all user-visible strings:

```python
# Before
label = QLabel("Settings")

# After
label = QLabel(tr("Settings"))
```

### 2. Extract Strings to TS Files

Use the `create_ts_files.py` tool:

```bash
python scout/translations/create_ts_files.py
```

This scans the codebase for calls to `tr()` and extracts them to `.ts` files.

### 3. Translate Strings

Edit the `.ts` files manually or use Qt Linguist:

```bash
linguist scout/translations/scout_de.ts
```

### 4. Compile TS Files to QM

Use the `compile_translations.py` tool:

```bash
python scout/translations/compile_translations.py
```

This compiles the `.ts` files to binary `.qm` files that can be loaded at runtime.

## Layout Adaptability

Different languages require different amounts of space. German text is typically 30% longer than English. Scout provides utilities to handle this:

### Layout Helper Utilities

In `scout/ui/utils/layout_helper.py`:

```python
def set_min_width_for_text(widget: QWidget, text: str) -> None:
    """Set the minimum width of a widget based on the text it contains."""
    # ...

def adjust_button_sizes(buttons: List[QPushButton]) -> None:
    """Adjust a group of buttons to have consistent sizes."""
    # ...

def create_form_layout() -> QFormLayout:
    """Create a form layout with proper settings for internationalization."""
    # ...
```

### Using Layout Helpers

```python
from scout.ui.utils.layout_helper import set_min_width_for_text, adjust_button_sizes

# Set minimum width for a combo box based on its longest item
combo_box = QComboBox()
combo_box.addItems(["English", "Deutsch"])
set_min_width_for_text(combo_box, "Deutsch")  # Use the longest text

# Adjust a group of buttons to have consistent widths
buttons = [ok_button, cancel_button, apply_button]
adjust_button_sizes(buttons)
```

## Adding a New Language

To add support for a new language:

### 1. Update the Language Enum

In `scout/ui/utils/language_manager.py`:

```python
class Language(Enum):
    SYSTEM = "system"
    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"  # New language
```

### 2. Create Initial Translation Files

Duplicate an existing `.ts` file and update the language attributes:

```bash
cp scout/translations/scout_en.ts scout/translations/scout_fr.ts
```

Edit the TS file to update the language attribute:

```xml
<TS version="2.1" language="fr_FR" sourcelanguage="en_US">
```

### 3. Translate Strings

Translate all strings in the new `.ts` file.

### 4. Update the UI

Add the new language to the language selection dropdown in the settings tab.

### 5. Compile Translations

Compile the new translation file:

```bash
python scout/translations/compile_translations.py
```

## Translation Configuration

The `scout/translations/config.py` file contains settings for the translation system:

```python
# Language expansion factors relative to English
LANGUAGE_EXPANSION_FACTORS = {
    'en': 1.0,    # English (base)
    'de': 1.3,    # German (~30% longer)
    'fr': 1.2,    # French (~20% longer)
}

# Minimum width in pixels for common UI elements
MIN_WIDTHS = {
    'button': 100,
    'label': 80,
    'combobox': 120,
}
```

Update this file when adding new languages.

## Best Practices

1. **Always use tr() for user-visible strings**: Any text that will be displayed to users should be marked for translation.

2. **Use appropriate contexts**: Organize translations by UI component or functionality to avoid ambiguity.

3. **Be careful with string formatting**: Use Qt's placeholders instead of Python's format method:
   ```python
   # Good
   tr("Selected: %1").replace("%1", item_name)
   
   # Avoid
   tr("Selected: {}").format(item_name)  # Can break in translation
   ```

4. **Test with all supported languages**: Ensure your UI looks good in all languages.

5. **Remember text expansion**: Some languages need more space. Test with German to ensure your UI can handle longer text.

6. **Add comments for translators**: For ambiguous strings, add comments to help translators:
   ```python
   # Translators: This refers to a file format, not a verb
   tr("Open")
   ```

## Testing Translations

Scout provides several tools for testing translations:

### 1. Visual Language Test

The `visual_language_test.py` tool provides visual testing of UI components:

```bash
python visual_language_test.py
```

### 2. Language Switching Test

The `test_language_switching.py` script tests language switching:

```bash
python test_language_switching.py --language de
```

### 3. Component Tests

The `test_ui_components.py` script tests individual UI components:

```bash
python test_ui_components.py
```

## Common Issues and Solutions

1. **Missing translations**: Strings appear in English despite switching to another language.
   - Solution: Ensure the string is marked with `tr()` and the translation file is up to date.

2. **Layout issues**: UI elements overlap or get cut off in some languages.
   - Solution: Use layout helpers and test with different languages.

3. **Plurals not working correctly**: Plural forms don't change based on count.
   - Solution: Use the `n` parameter correctly: `tr("%n item(s)", n=count)`.

4. **Context confusion**: Same string translated differently in different parts of the UI.
   - Solution: Use context parameters to disambiguate: `tr("Open", "FileMenu")`.

## Resources

- [Qt Internationalization Guide](https://doc.qt.io/qt-6/internationalization.html)
- [Qt Linguist Manual](https://doc.qt.io/qt-6/linguist-translators.html)
- [Translation Best Practices](https://phrase.com/blog/posts/10-tips-to-make-your-software-translatable/) 