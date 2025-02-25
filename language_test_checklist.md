# Scout Internationalization Test Checklist

This checklist helps verify that internationalization is working correctly throughout the Scout application.

## Setup

1. Run the application with different languages:
   ```bash
   # Run with English
   python test_language_switching.py --language en
   
   # Run with German
   python test_language_switching.py --language de
   
   # Run with language tester
   python test_language_switching.py --tester
   ```

2. Open the Settings tab and verify that language can be changed from the UI.

## Component Testing

### Main Window

| Component | English Display | German Display | Layout Issues |
|-----------|----------------|---------------|---------------|
| Title bar | | | |
| File menu | | | |
| Edit menu | | | |
| View menu | | | |
| Tools menu | | | |
| Help menu | | | |
| Toolbar buttons | | | |
| Status bar | | | |

### Settings Tab

| Component | English Display | German Display | Layout Issues |
|-----------|----------------|---------------|---------------|
| UI tab dropdown options | | | |
| Language selection | | | |
| Theme selection | | | |
| Path input labels | | | |
| OCR options | | | |
| Window configuration | | | |
| Advanced settings | | | |
| Notification settings | | | |
| Dialog titles and messages | | | |

### Detection Tab

| Component | English Display | German Display | Layout Issues |
|-----------|----------------|---------------|---------------|
| Strategy dropdown | | | |
| Parameter labels | | | |
| Template list | | | |
| Results table headers | | | |
| Dialog messages | | | |

### Automation Tab

| Component | English Display | German Display | Layout Issues |
|-----------|----------------|---------------|---------------|
| Sequence controls | | | |
| Action type dropdown | | | |
| Parameter forms | | | |
| Execution options | | | |
| Dialog messages | | | |

### Game State Tab 

| Component | English Display | German Display | Layout Issues |
|-----------|----------------|---------------|---------------|
| Tab sections | | | |
| Resource labels | | | |
| Status indicators | | | |
| Map controls | | | |
| Dialog messages | | | |

### Dialogs

| Dialog | English Display | German Display | Layout Issues |
|--------|----------------|---------------|---------------|
| Keyboard Shortcuts | | | |
| About Dialog | | | |
| Error Messages | | | |
| Warning Messages | | | |
| Information Messages | | | |
| Export Dialogs | | | |

## Layout Adaptability Testing

Check the following for layout issues when switching between languages:

1. **Truncated text**: Any text getting cut off?
2. **Overlapping controls**: Any UI elements overlapping?
3. **Misaligned controls**: Any alignment issues?
4. **Scrollbars appearing**: Any unexpected scrollbars?
5. **Expanding dialogs**: Do dialogs resize appropriately?
6. **Button sizes**: Do buttons accommodate longer text?
7. **Form layouts**: Do form labels and fields align properly?

## Translation Consistency

Check for:

1. **Untranslated strings**: Any strings still showing in English when German is selected?
2. **Mixed languages**: Any mix of English and German in a single screen?
3. **Placeholder text**: Are input placeholders translated?
4. **Dynamic content**: Are dynamically generated messages translated?
5. **Error messages**: Are all error messages translated?

## Functional Testing

1. Switch between languages multiple times and verify the application remains stable.
2. Perform regular operations in each language (detection, automation, etc.).
3. Verify that changing the language persists after restarting the application.

## Issues Log

Record any issues found during testing:

| Issue Description | Component | Priority | Screenshot |
|-------------------|-----------|----------|------------|
| | | | |
| | | | |

## Notes

- For German text, expect approximately 30% longer strings than English.
- Pay particular attention to dropdown menus, as they often have width constraints.
- Dialog buttons may need special attention for layout issues. 