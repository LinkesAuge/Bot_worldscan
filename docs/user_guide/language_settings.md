# Language Settings

Scout is available in multiple languages, allowing you to use the application in your preferred language. This guide explains how to change the language settings and what to expect when switching languages.

## Available Languages

Scout currently supports the following languages:

- **English**: The default language for Scout.
- **German (Deutsch)**: A full German translation of the user interface.

We plan to add support for additional languages in future updates.

## Changing the Application Language

You can change the language through the Settings tab:

1. Open Scout and click on the **Settings** tab.
2. Select the **UI** section from the tabs on the left.
3. Find the **Language** dropdown menu in the UI settings.
4. Select your preferred language from the dropdown:
   - **System** - Uses your operating system's language if supported, or falls back to English.
   - **English** - Forces English language.
   - **German (Deutsch)** - Forces German language.
5. The changes will take effect immediately for most UI elements.

![Language Settings in UI Tab](../images/language_settings.png)

## Immediate Language Changes

When you change the language, most UI elements will update immediately:

- Menu items and labels
- Button text
- Tab titles
- Settings descriptions
- Status messages

## Application Restart Elements

Some UI elements may require an application restart to fully update:

- Dialog boxes that were already open
- Complex widgets with cached text
- Some tooltips and status bar messages

If you notice any elements still displaying text in the previous language, simply restart Scout to ensure all elements are properly translated.

## Language Persistence

Your language preference is automatically saved and will persist between application sessions. The next time you start Scout, it will use the language you previously selected.

Scout stores these settings in the following location:
- **Windows**: `%APPDATA%\ScoutTeam\Scout.ini`

## System Language Fallback

When set to "System", Scout attempts to use your operating system's language settings:

1. Scout checks your operating system's language setting.
2. If the OS language is supported (currently English or German), Scout uses that language.
3. If the OS language is not supported, Scout falls back to English.

## Text Length and Layout Considerations

Different languages require different amounts of space to express the same content. For example, German text is typically about 30% longer than the equivalent English text. Scout's interface is designed to automatically adapt to these differences, but in rare cases you might notice:

- Text wrapping to multiple lines in some languages
- Scrollbars appearing in some components
- Slight alignment differences

These behaviors are normal and should not affect functionality.

## Troubleshooting Language Issues

### Missing Translations

If you notice any untranslated text in the application:

1. Check that you've selected the correct language in the settings.
2. Restart the application to ensure all components are refreshed.
3. If the issue persists, it may be that this particular text doesn't have a translation yet.

### Garbled or Incorrect Text

If text appears garbled or obviously incorrect:

1. Ensure your system has the necessary fonts installed for the selected language.
2. For German, ensure your system has good Unicode font support for umlauts and other special characters.
3. Try switching to another language and then back again.
4. If the problem persists, try reinstalling the application.

### Language Setting Not Saving

If your language preference is not being saved between sessions:

1. Ensure you have write permissions to the Scout application settings directory.
2. Check if your antivirus or security software might be blocking the application from saving settings.
3. Try running Scout as an administrator (right-click → Run as administrator).

## Adding New Languages (For Developers)

Scout is designed for easy addition of new languages. If you're a developer interested in contributing translations, please see the [Developer Documentation](../developer/README.md) for information on how to add support for additional languages.

## Related Resources

- [Settings Guide](settings.md) - More information about application settings
- [Developer Guide to Internationalization](../developer/internationalization.md) - How Scout's internationalization system works 