# Scout API Reference

## Overview

This API Reference provides detailed documentation for all the public APIs in the Scout application. It is intended for developers who want to integrate with Scout, extend its functionality, or understand its internal structure.

## Core APIs

### Window Module

The Window module provides APIs for detecting, capturing, and interacting with game windows.

- [WindowServiceInterface](window/window_service_interface.md)
- [WindowService](window/window_service.md)
- [WindowCapture](window/window_capture.md)
- [CaptureStrategies](window/capture_strategies.md)

### Detection Module

The Detection module provides APIs for finding and analyzing game elements.

- [DetectionServiceInterface](detection/detection_service_interface.md)
- [DetectionService](detection/detection_service.md)
- [DetectionStrategy](detection/strategy.md)
- [TemplateStrategy](detection/template_strategy.md)
- [OCRStrategy](detection/ocr_strategy.md)
- [YOLOStrategy](detection/yolo_strategy.md)

### Game State Module

The Game State module provides APIs for tracking and analyzing game state.

- [GameServiceInterface](game/game_service_interface.md)
- [GameService](game/game_service.md)
- [GameState](game/game_state.md)

### Automation Module

The Automation module provides APIs for creating and executing automation sequences.

- [AutomationServiceInterface](automation/automation_service_interface.md)
- [AutomationService](automation/automation_service.md)
- [Task](automation/task.md)
- [TaskTypes](automation/task_types.md)

### Service Locator

The Service Locator provides a central registry for accessing core services.

- [ServiceLocator](core/service_locator.md)

## Event System

The Event System provides a way for components to communicate through events.

- [Event](events/event.md)
- [EventBus](events/event_bus.md)
- [EventTypes](events/event_types.md)

## UI Components

The UI Components provide APIs for creating and extending the user interface.

- [MainWindow](ui/main_window.md)
- [DetectionTab](ui/detection_tab.md)
- [AutomationTab](ui/automation_tab.md)
- [GameStateTab](ui/game_state_tab.md)
- [SettingsTab](ui/settings_tab.md)

## Utility APIs

Various utility APIs that provide helper functionality.

- [LanguageManager](utils/language_manager.md)
- [ThemeManager](utils/theme_manager.md)
- [ShortcutManager](utils/shortcut_manager.md)
- [LayoutHelper](utils/layout_helper.md)

## Using the API Documentation

Each API documentation page follows a consistent format:

1. **Overview**: A brief description of the API and its purpose.
2. **Class/Interface Definition**: Detailed description of the class or interface.
3. **Properties**: Description of public properties.
4. **Methods**: Description of public methods, including parameters and return types.
5. **Events**: Description of events emitted by the API (if applicable).
6. **Examples**: Code samples showing how to use the API.
7. **Related APIs**: Links to related APIs.

## Contributing to the API Documentation

This API documentation is generated from docstrings in the source code. To improve the documentation:

1. Update the docstrings in the source code.
2. Follow the [Documentation Standards](../developer/contributing.md#documentation-standards) guide.

## Versioning

The API documentation is versioned to match the Scout application version. Breaking changes to the API are noted in the [Changelog](../developer/changelog.md).

## API Stability

APIs are marked with stability indicators:

- **Stable**: Well-tested and unlikely to change significantly.
- **Experimental**: May change in future versions.
- **Deprecated**: Planned for removal in a future version, with alternative provided. 