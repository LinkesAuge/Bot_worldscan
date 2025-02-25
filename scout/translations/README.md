# Scout Translation System

This directory contains the translation resources for the Scout application. The translation system allows the application to be used in multiple languages, currently supporting English and German.

## Overview

The Scout translation system is based on Qt's internationalization (i18n) framework, with some additional tools and utilities to simplify working with translations.

### Key Components

1. **LanguageManager**: Centralized manager for language switching and translation loading.
2. **Translation Files**:
   - `.ts` files: XML-based source files containing translatable strings and translations.
   - `.qm` files: Compiled binary files used at runtime.
3. **Utility Scripts**: Tools for creating, compiling, and verifying translations.

## Translation Files

### Structure

- `scout_en.ts`: English translations (source language)
- `scout_de.ts`: German translations
- `scout_*.qm`: Compiled translation files

The `.ts` files are structured as XML files with contexts, messages, sources, and translations.

Example structure:
```xml
<context>
    <name>MainWindow</name>
    <message>
        <source>File</source>
        <translation>Datei</translation>
    </message>
</context>
```

## Using Translations in Code

### Marking Strings for Translation

Use the `tr()` function to mark strings for translation:

```python
from scout.ui.utils.language_manager import tr

# Simple translation
label = QLabel(tr("Settings"))

# Translation with context
button = QPushButton(tr("Save", "MainWindow"))

# Translation with plurals
message = tr("Found %n item(s)", n=count)
```

### Contexts

Contexts help organize translations and resolve ambiguities. Each UI class or module should use its own context.

Common contexts include:
- `MainWindow`: Main window UI
- `DetectionTab`: Detection tab UI
- `SettingsTab`: Settings tab UI
- `AutomationTab`: Automation tab UI
- `GameStateTab`: Game state tab UI

### Special Cases

#### Plurals

For strings that need to handle both singular and plural forms:

```python
count = 5
message = tr("%n file(s) found", n=count)
```

#### Variables in Strings

For strings with variables, use Qt's placeholder syntax:

```python
filename = "data.csv"
message = tr("Exported to %1").replace("%1", filename)
```

## Adding New Translations

### Process

1. Add the translatable string in code using `tr()`.
2. Run `create_ts_files.py` to update the translation files.
3. Edit the translation files to add translations for the new strings.
4. Run `compile_translations.py` to generate the `.qm` files.
5. Test the translations in the application.

### Adding a New Language

To add support for a new language:

1. Duplicate an existing `.ts` file (e.g., `scout_en.ts`) and rename it for the new language (e.g., `scout_fr.ts` for French).
2. Edit the language and sourcelanguage attributes in the `<TS>` tag.
3. Translate all strings in the file.
4. Add the new language to the `Language` enum in `language_manager.py`.
5. Update the language selection dropdown in the settings UI.
6. Compile the translations.

## Utility Scripts

### create_ts_files.py

Creates initial translation files or updates them with new strings found in the codebase.

Usage:
```bash
python create_ts_files.py
```

### compile_translations.py

Compiles `.ts` files to binary `.qm` format using Qt's `lrelease` tool.

Usage:
```bash
python compile_translations.py
```

### create_qm_files.py

Alternative to `compile_translations.py` when Qt's `lrelease` tool is not available. Creates minimal `.qm` files.

Usage:
```bash
python create_qm_files.py
```

### verify_translations.py

Checks translation files for issues such as missing translations or inconsistencies.

Usage:
```bash
python verify_translations.py
```

## Testing Translations

### Manual Testing

To test translations visually, run the language test application:

```bash
python -m tests.ui.test_language_ui
```

This application shows a UI with various elements that should be properly translated when changing the language.

### Automated Testing

Unit tests for the translation system are available in:

```bash
python -m unittest tests.ui.test_language_manager
```

## Best Practices

1. **Always use `tr()` for user-visible strings**: All text that will be displayed to users should be marked for translation.

2. **Use appropriate contexts**: Organize translations by UI component or functionality.

3. **Be careful with string formatting**: Use Qt's placeholder syntax instead of Python's format methods.

4. **Keep translations consistent**: Use the same terminology across the application.

5. **Test translations thoroughly**: Ensure that all UI components display correctly with different languages.

6. **Account for text length changes**: Some translations may be longer or shorter than the original text, so UI designs should be flexible.

7. **Document special cases**: If a string has special handling or context, document it.

## Known Issues

- Text expansion: Some languages may require more space than others, which can cause layout issues.
- Right-to-left languages are not fully supported yet.
- Some contexts in the translation files use `<n>` instead of `<name>` due to manual editing.

## Future Improvements

- Add support for more languages.
- Implement better handling of plurals.
- Improve the translation verification tool to check for missing contexts or strings.
- Add support for right-to-left languages. 