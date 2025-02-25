# Scout Codebase Architecture Report

## Overview

This document provides a comprehensive overview of the Scout application's architecture, design patterns, code organization, and component interactions. It serves as a technical reference for developers working on maintaining or extending the application.

## Application Purpose

Scout is a desktop automation tool designed for the Total Battle game that provides:
- Window detection and screen capture
- Computer vision detection (template matching, OCR, YOLO)
- Automation sequence creation and execution
- Game state tracking and visualization
- Multi-language support (English and German)
- Theme customization (Light, Dark, System)

## Architectural Design

### Architecture Pattern

Scout implements a service-oriented architecture with the following characteristics:

1. **Core Services Layer**: Contains the business logic and domain-specific functionality
2. **UI Layer**: Presents the user interface and handles user interactions
3. **Event System**: Facilitates loose coupling between components
4. **Service Locator**: Provides centralized service access and dependency management

This layered architecture allows for:
- Separation of concerns
- Testability of individual components
- Modularity and extensibility
- Platform independence in the core layer

### Directory Structure

```
scout/
├── core/                  # Core functionality
│   ├── automation/        # Automation system
│   ├── detection/         # Detection system
│   ├── design/            # Design patterns
│   ├── events/            # Event system
│   ├── game/              # Game state system
│   ├── interfaces/        # Service interfaces
│   ├── services/          # Base services
│   ├── updater/           # Update system
│   ├── utils/             # Utilities
│   └── window/            # Window management
├── ui/                    # User interface
│   ├── controllers/       # UI controllers
│   ├── dialogs/           # Application dialogs
│   ├── models/            # UI data models
│   ├── styles/            # UI styling
│   ├── utils/             # UI utilities
│   ├── views/             # Main views
│   └── widgets/           # Reusable widgets
├── translations/          # Language files
├── tests/                 # Test suite
│   ├── core/              # Core tests
│   ├── ui/                # UI tests
│   ├── integration/       # Integration tests
│   ├── cross_platform/    # Platform tests
│   └── performance/       # Performance benchmarks
├── resources/             # Resources
└── main.py                # App entry point
```

## Design Patterns

Scout implements several design patterns to solve common software design problems:

### 1. Singleton Pattern

**Implementation**: `scout/core/design/singleton.py`

The Singleton pattern ensures that only one instance of a class exists in the application. Scout implements this as a metaclass for flexibility:

```python
class Singleton(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
```

**Usage**:
- Service classes like `WindowService`, `GameService`, `AutomationService`
- Manager classes like `LanguageManager`, `ThemeManager`

### 2. Service Locator Pattern

**Implementation**: `scout/ui/service_locator_ui.py`

The Service Locator pattern provides a centralized registry for accessing services:

```python
class ServiceLocator:
    _services = {}  # Static dictionary of services
    
    @classmethod
    def register(cls, interface_class, implementation):
        cls._services[interface_class] = implementation
    
    @classmethod
    def get(cls, interface_class):
        return cls._services.get(interface_class)
```

**Usage**:
- UI components use this to access core services
- Facilitates dependency injection for testing
- Centralizes service lifecycle management

### 3. Observer Pattern

**Implementation**: `scout/core/events/`

The Observer pattern allows components to observe and react to events without direct coupling. Scout implements this through the `EventBus`:

```python
class EventBus:
    def subscribe(self, event_type, callback):
        # Add callback to subscribers for this event type
    
    def publish(self, event_type, data=None):
        # Notify all subscribers for this event type
```

**Usage**:
- Service components publish events when their state changes
- UI components subscribe to events to update the display
- Loose coupling between components

### 4. Strategy Pattern

**Implementation**: `scout/core/detection/`

The Strategy pattern defines a family of algorithms and makes them interchangeable:

```python
class DetectionStrategy(ABC):
    @abstractmethod
    def detect(self, image, config):
        pass

class TemplateMatchingStrategy(DetectionStrategy):
    def detect(self, image, config):
        # Implement template matching
```

**Usage**:
- Different detection strategies (Template, OCR, YOLO)
- Window capture strategies for different platforms
- Theme strategies for different appearances

### 5. Command Pattern

**Implementation**: `scout/core/automation/task.py`

The Command pattern encapsulates requests as objects, allowing for parameterization, queueing, and logging of requests:

```python
class Task(ABC):
    def __init__(self, name, priority=TaskPriority.NORMAL):
        self.name = name
        self.priority = priority
        
    @abstractmethod
    def execute(self, context):
        pass
```

**Usage**:
- Automation tasks encapsulate different actions
- Tasks can be queued, scheduled, and prioritized
- Enables complex sequences of operations

## Core Components

### 1. Window Service

**Purpose**: Manages interaction with the game window

**Key Features**:
- Window detection by title or process
- Screenshot capture with optimized strategies
- Coordinate conversion between screen and client
- Window state tracking (moved, resized, etc.)

**Key Classes**:
- `WindowService`: Implements window operations
- `WindowServiceInterface`: Defines the window service API
- `CaptureStrategy`: Strategy for different capture methods

### 2. Detection Service

**Purpose**: Analyzes screenshots to identify game elements

**Key Features**:
- Multiple detection strategies (Template, OCR, YOLO)
- Configuration of detection parameters
- Result filtering and post-processing
- Result visualization

**Key Classes**:
- `DetectionService`: Manages detection operations
- `DetectionStrategy`: Abstract base for detection algorithms
- `TemplateMatchingStrategy`: Finds patterns in images
- `OCRStrategy`: Extracts text from images
- `YOLOStrategy`: Deep learning-based detection

### 3. Game Service

**Purpose**: Tracks and updates the game state

**Key Features**:
- Resource tracking (gold, wood, etc.)
- Building and unit information
- Map and territory data
- State history and serialization

**Key Classes**:
- `GameService`: Implements game state operations
- `GameState`: Data model for game state
- `GameStateSerializer`: Handles state persistence
- `ResourceTracker`: Monitors game resources

### 4. Automation Service

**Purpose**: Executes automation sequences

**Key Features**:
- Task scheduling and prioritization
- Execution control (start, pause, stop)
- Error handling and recovery
- Event notification for task status

**Key Classes**:
- `AutomationService`: Manages automation execution
- `Task`: Base class for automation tasks
- `TaskExecutor`: Executes tasks in a controlled manner
- `TaskScheduler`: Schedules tasks for execution

## UI Components

### 1. Main Window

**Purpose**: Provides the main application frame

**Key Features**:
- Tabbed interface for different functions
- Menu system for application commands
- Toolbar for common operations
- Status bar for application state
- Overlay for game window visualization

**Implementation**: `scout/ui/main_window.py`

### 2. Detection Tab

**Purpose**: Interface for detection operations

**Key Features**:
- Template management (add, edit, delete)
- Detection configuration
- Result visualization
- History tracking and heatmap

**Implementation**: `scout/ui/views/detection_tab.py`

### 3. Automation Tab

**Purpose**: Interface for automation operations

**Key Features**:
- Sequence management (create, open, save)
- Action editing and configuration
- Position management for clicks
- Execution controls (run, stop, pause)

**Implementation**: `scout/ui/views/automation_tab.py`

### 4. Game State Tab

**Purpose**: Interface for game state visualization

**Key Features**:
- Resource display
- Map visualization
- State variable management
- State history visualization

**Implementation**: `scout/ui/views/game_state_tab.py`

### 5. Settings Tab

**Purpose**: Interface for application configuration

**Key Features**:
- UI settings (language, theme)
- Detection settings
- Automation settings
- Path configuration
- Update settings

**Implementation**: `scout/ui/views/settings_tab.py`

## Cross-Cutting Features

### 1. Internationalization

**Purpose**: Provides multi-language support

**Key Features**:
- Language management (English, German)
- String translation
- Layout adaptation for different text lengths
- Runtime language switching

**Key Components**:
- `LanguageManager` in `scout/ui/utils/language_manager.py`
- Translation files in `scout/translations/`
- `tr()` function for string translation
- Layout helpers in `scout/ui/utils/layout_helper.py`

### 2. Theme System

**Purpose**: Provides visual customization

**Key Features**:
- Theme management (Light, Dark, System)
- Runtime theme switching
- Theme persistence
- Custom styling

**Key Components**:
- Theme stylesheets in `scout/ui/styles/`
- Theme application in `scout/ui/main_window.py`
- Theme settings in the Settings Tab

### 3. Update System

**Purpose**: Manages application updates

**Key Features**:
- Update checking (automatic or manual)
- Update downloading
- Update installation
- Update settings

**Key Components**:
- `UpdateChecker` in `scout/core/updater/update_checker.py`
- `UpdateDialog` in `scout/ui/dialogs/update_dialog.py`
- Update settings in the Settings Tab

### 4. Error Handling

**Purpose**: Provides robust error recovery

**Key Features**:
- Comprehensive exception handling
- Error logging
- Recovery strategies
- User notification

**Key Components**:
- Try/except blocks throughout the codebase
- Logging configuration in `main.py`
- Error dialogs for user notification
- Recovery strategies in service classes

## Component Interactions

### Service Initialization Flow

1. `main.py` initializes core services:
   ```python
   window_service = WindowService("Total Battle")
   detection_service = DetectionService(window_service)
   game_service = GameService(window_service, detection_service)
   automation_service = AutomationService()
   ```

2. Services are registered with the `ServiceLocator`:
   ```python
   ServiceLocator.register(WindowServiceInterface, window_service)
   ServiceLocator.register(DetectionServiceInterface, detection_service)
   ServiceLocator.register(GameServiceInterface, game_service)
   ServiceLocator.register(AutomationServiceInterface, automation_service)
   ```

3. UI components retrieve services as needed:
   ```python
   window_service = ServiceLocator.get(WindowServiceInterface)
   ```

### Event Flow

1. Services publish events when their state changes:
   ```python
   event_data = {"results": results, "strategy": strategy}
   event_bus.publish(EventType.DETECTION_COMPLETED, event_data)
   ```

2. UI components subscribe to events:
   ```python
   event_bus.subscribe(EventType.DETECTION_COMPLETED, self._on_detection_completed)
   ```

3. Event handlers update the UI:
   ```python
   def _on_detection_completed(self, event_data):
       self._update_results_display(event_data["results"])
   ```

### Detection Flow

1. User configures detection parameters in the Detection Tab
2. User initiates detection, which calls `detection_service.detect()`
3. `DetectionService` captures a screenshot using `window_service`
4. `DetectionService` applies the selected strategy to the screenshot
5. Results are returned to the UI for visualization
6. Results are published as an event for other components

### Automation Flow

1. User creates a sequence of actions in the Automation Tab
2. User initiates execution, which calls `automation_service.start_execution()`
3. `AutomationService` executes tasks in order, handling priorities
4. Tasks may interact with other services (e.g., waiting for detection results)
5. Task status updates are published as events
6. UI updates to show current execution status

## Code Quality

### Testing Approach

1. **Unit Tests**: Test individual components in isolation
   - Service tests with mocked dependencies
   - UI component tests with Qt Test framework
   
2. **Integration Tests**: Test component interactions
   - Service integration tests
   - UI-to-service integration tests
   
3. **Cross-Platform Tests**: Verify platform-specific behavior
   - Window management
   - File paths
   - UI rendering
   
4. **Performance Tests**: Benchmark critical operations
   - Detection strategies
   - Window capture methods
   - Image processing operations

### Coding Standards

1. **Type Hints**: Used throughout the codebase for static type checking

2. **Documentation**:
   - Module docstrings explain purpose and content
   - Class docstrings describe functionality and usage
   - Method docstrings detail parameters and return values

3. **Error Handling**:
   - Comprehensive try/except blocks
   - Appropriate error messages
   - Recovery strategies where possible

4. **Naming Conventions**:
   - CamelCase for classes
   - snake_case for methods and variables
   - UPPER_CASE for constants
   - _leading_underscore for private members

## Conclusion

The Scout application is designed with modularity, extensibility, and testability in mind. Its service-oriented architecture with loose coupling through events allows for easy maintenance and extension. The comprehensive testing suite and documentation provide a solid foundation for ongoing development.

For future development, developers should:
1. Follow the established design patterns and architecture
2. Ensure proper event communication between components
3. Maintain thorough testing of new functionality
4. Update documentation as the codebase evolves 