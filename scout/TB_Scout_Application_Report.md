# TB Scout Application Report
This file needs to be kept updated at all times. Please add/update/remove any new relevant information regarding the app like it's features, core components, file structure, code flow etc.

## Application Overview

TB Scout is a Python application designed for automating interactions with the "Total Battle" browser game. It works with both browser-based and standalone versions of the game. The application leverages computer vision and automation techniques to extract information from the game world and control in-game actions.

The application provides a powerful set of tools for game automation, including:
- Window detection and tracking
- Screenshot capture and analysis
- Pattern matching for game elements
- OCR text extraction
- Mouse and keyboard automation
- Transparent overlay visualization
- Game world coordinate tracking and navigation
- Automated sequence execution

## Key Features

### 1. Window Management
- Detects and tracks the "Total Battle" game window
- Works with both browser and standalone versions
- Captures screenshots for analysis
- Manages window focus and positioning

### 2. Pattern Matching
- Uses OpenCV for template matching
- Detects game elements (cities, monsters, resources, etc.)
- Visualizes matches with bounding boxes and confidence levels
- Supports confidence thresholds and match grouping
- Tracks match frequency for performance optimization

### 3. OCR Text Extraction
- Uses Tesseract OCR to extract text from the game
- Focuses on specific regions for coordinate extraction
- Parses game world coordinates in K, X, Y order (where K is the kingdom/world number)
- Provides real-time text updates

### 4. Game World Coordination
- Maps between screen coordinates and game world coordinates
- Tracks current position in the game world using K, X, Y coordinate system
  - K: Kingdom/world number
  - X: Horizontal position within the kingdom
  - Y: Vertical position within the kingdom
- Calculates drag vectors for navigation
- Updates position from OCR readings
- Supports different coordinate regions and calibration
- **Coordinate Calibration System**:
  - Uses a drag distance calibration approach to establish accurate mapping between screen pixels and game world units
  - Calibration process:
    1. Start calibration at current position
    2. Drag/scroll the map to a different location
    3. Complete calibration to calculate pixels-per-game-unit ratio
  - Automatically saves calibration data to disk for persistence between sessions
  - Provides visual feedback and instructions during the calibration process
  - Improves accuracy of coordinate conversion, navigation, and automation

### 5. Automation
- Builds and executes sequences of actions
- Supports various action types (click, drag, wait, etc.)
- Manages marked positions for consistent interaction
- Provides simulation mode for testing
- Includes debugging tools for sequence execution

### 6. Overlay Visualization
- Creates a transparent overlay on top of the game
- Visualizes detected elements and matches
- Provides click-through functionality
- Automatically repositions with the game window
- Configurable visual elements (colors, sizes, etc.)

### 7. Game World Search
- Implements intelligent search strategies
- Combines search patterns with game world coordination
- Supports various search patterns (spiral, grid, circles, quadtree)
- Tracks search history and statistics
- Provides visual feedback during searches

## Enhanced Calibration System

The TB Scout application now features an improved calibration system that provides more accurate and consistent coordinate mapping between screen pixels and game world units. This enhancement ensures better navigation, position tracking, and automation capabilities.

### Key Features

1. **Point-Based Calibration**
   - Visual overlay for marking calibration points
   - Clear step-by-step instructions
   - Automated drag operation between points
   - Consistent measurement process

2. **Improved Accuracy**
   - Uses fixed points for consistent measurements
   - Automated drag operation eliminates manual inconsistencies
   - Better validation of calibration results
   - Enhanced error handling and feedback

3. **User-Friendly Interface**
   - Visual overlay for point selection
   - Clear status updates and instructions
   - Intuitive workflow with step-by-step guidance
   - Easy cancellation and retry options

### Technical Implementation

1. **Calibration Process**
   - Two-point calibration system for accurate measurements
   - Automated drag operation between points
   - OCR readings at both start and end points
   - Calculation of pixels-per-game-unit ratios

2. **Coordinate Conversion**
   - Accurate mapping between screen and game coordinates
   - Consistent drag vector calculations
   - Reliable position tracking
   - Improved handling of coordinate system changes

3. **Error Handling**
   - Validation of point distances
   - OCR reading verification
   - Clear error messages and recovery options
   - Graceful handling of cancellation

### Benefits

1. **Improved Navigation**
   - More accurate coordinate conversion
   - Better drag vector calculations
   - Consistent position tracking
   - Reliable automation sequences

2. **Enhanced User Experience**
   - Clear visual feedback
   - Step-by-step guidance
   - Easy error recovery
   - Consistent results

3. **Increased Reliability**
   - Automated measurements
   - Validated calibration results
   - Better error handling
   - Consistent coordinate mapping

## File Structure and Class Descriptions

### Core Components

#### 1. `main.py`
The application entry point that initializes all components and sets up the main event loop.

**Key Functions:**
- `main()`: Initializes the application, components, and starts the event loop
- `is_key_pressed()`: Utility function to check if a key is pressed

#### 2. `window_manager.py` - `WindowManager` Class
Manages finding, tracking, and interacting with the game window.

**Key Methods:**
- `find_window()`: Locates the game window by title
- `get_window_position()`: Returns the position and size of the game window
- `capture_screenshot()`: Takes a screenshot of the game window
- `get_client_rect()`: Gets the client area of the window
- `get_window_frame_offset()`: Calculates the window frame offset

#### 3. `overlay.py` - `Overlay` Class
Creates and manages the transparent overlay window for visualizing game information.

**Key Methods:**
- `create_overlay_window()`: Creates the transparent overlay window
- `_draw_empty_overlay()`: Clears the overlay
- `_update_window_position()`: Updates the overlay position to match the game window
- `start_template_matching()`: Starts the template matching process
- `toggle()`: Toggles the overlay visibility

#### 4. `gui_controller.py` - `OverlayController` Class
Manages the user interface for controlling the overlay and application features.

**Key Methods:**
- `_toggle_pattern_matching()`: Toggles the pattern matching process
- `_toggle_ocr()`: Toggles the OCR process
- `_toggle_game_world_search()`: Toggles the game world search process
- `keyPressEvent()`: Handles keyboard shortcuts (Escape/Q to stop processes)
- `_update_ocr_button_state()`: Updates the OCR button state

#### 5. `template_matcher.py` - `TemplateMatcher` Class
Implements pattern matching logic to detect game elements in screenshots.

**Key Methods:**
- `find_matches()`: Finds matches for specified templates in a screenshot
- `_find_template()`: Finds a single template in a screenshot
- `start_template_matching()`: Starts continuous template matching
- `group_similar_matches()`: Groups similar matches to avoid duplicates
- `track_match_frequency()`: Tracks match frequency for performance optimization

#### 6. `text_ocr.py` - `TextOCR` Class
Handles OCR processing to extract text from the game window.

**Key Methods:**
- `set_region()`: Sets the region for OCR processing
- `set_frequency()`: Adjusts the update frequency
- `extract_text()`: Extracts text from a screenshot
- `_extract_coordinates()`: Extracts coordinates from OCR text (K, X, Y)
- `_process_region()`: Processes the OCR region

#### 7. `game_world_coordinator.py` - `GameWorldCoordinator` Class
Coordinates between screen coordinates and game world coordinates.

**Key Methods:**
- `update_current_position_from_ocr()`: Updates the current position from OCR
- `screen_to_game_coords()`: Converts screen coordinates to game world coordinates
- `game_to_screen_coords()`: Converts game world coordinates to screen coordinates
- `calculate_drag_vector()`: Calculates drag vector to move to target coordinates
- `is_position_on_screen()`: Checks if a game world position is visible on screen
- `start_calibration()`: Starts the drag distance calibration process
- `complete_calibration()`: Completes the calibration and calculates pixels per game unit
- `cancel_calibration()`: Cancels the current calibration process
- `get_calibration_status()`: Gets the current calibration status

#### 8. `game_world_search.py` - `GameWorldSearch` Class
Implements intelligent search strategies for finding templates in the game world.

**Key Methods:**
- `search_templates()`: Searches for templates using a specified pattern
- `_check_for_templates()`: Checks for templates at the current position
- `_move_to_position()`: Moves the view to a specific game world position
- `get_search_statistics()`: Gets statistics about the search history

#### 9. `automation/gui/automation_tab.py` - `AutomationTab` Class
Provides the main automation tab in the GUI.

**Key Methods:**
- `is_sequence_running()`: Checks if a sequence is currently running
- `_toggle_sequence()`: Toggles sequence execution
- `_toggle_ocr()`: Toggles OCR functionality
- `_on_position_marked()`: Handles new position being marked
- `_on_sequence_execution()`: Handles sequence execution request

### Supporting Classes

#### 1. `automation/gui/automation_tab.py` - `PositionList` Class
Widget for managing marked positions.

**Key Methods:**
- `update_positions()`: Updates the position list with new positions
- `_on_position_selected()`: Handles position selection
- `_on_add_clicked()`: Handles add button click
- `_on_remove_clicked()`: Handles remove button click
- `_on_details_changed()`: Handles changes to position details

#### 2. `automation/gui/automation_tab.py` - `SequenceBuilder` Class
Widget for building and editing action sequences.

**Key Methods:**
- `_new_sequence()`: Creates a new empty sequence
- `update_positions()`: Updates available positions
- `_on_sequence_changed()`: Handles sequence changes
- `_on_action_selected()`: Handles action selection
- `_on_add_clicked()`: Handles add action button click

#### 3. `game_world_search.py` - `SearchResult` Class
Result of a template search operation.

**Key Methods:**
- `to_dict()`: Converts to dictionary for storage
- `from_dict()`: Creates from dictionary
- `__str__()`: String representation of the search result

#### 4. `game_world_coordinator.py` - `GameWorldPosition` Class
Represents a position in the game world.

**Key Methods:**
- `__str__()`: String representation of the position (K, X, Y format)

#### 5. `gui/game_world_coord_widget.py` - `CoordinateDisplayWidget` Class
Widget for displaying and updating game world coordinates and managing calibration.

**Key Methods:**
- `_update_coordinates()`: Updates the coordinate display from OCR
- `_toggle_auto_update()`: Toggles automatic coordinate updates
- `_start_auto_update()`: Starts automatic coordinate updates
- `_stop_auto_update()`: Stops automatic coordinate updates
- `_start_calibration()`: Starts the drag distance calibration process
- `_complete_calibration()`: Completes the calibration process with the second point
- `_cancel_calibration()`: Cancels the current calibration process
- `update_calibration_status()`: Updates the calibration status display
- `get_current_position()`: Gets the current game world position

## File Structure Diagram

```
tb-scout/
├── scout/                           # Main package directory
│   ├── __init__.py                  # Package initialization
│   ├── main.py                      # Application entry point
│   ├── overlay.py                   # Overlay visualization
│   ├── gui_controller.py            # Main GUI controller
│   ├── window_manager.py            # Game window management
│   ├── template_matcher.py          # Pattern matching
│   ├── text_ocr.py                  # OCR text extraction
│   ├── game_world_coordinator.py    # Coordinate system management
│   ├── game_world_search.py         # Search strategies
│   ├── game_state.py                # Game state tracking
│   ├── actions.py                   # Game actions
│   ├── config_manager.py            # Configuration management
│   ├── sound_manager.py             # Sound notifications
│   ├── debug_window.py              # Debug visualization
│   ├── selector_tool.py             # Region selection tool
│   ├── window_capture.py            # Window capture utilities
│   ├── world_scanner.py             # World scanning functionality
│   ├── config.ini                   # Configuration file
│   ├── memory.mdc                   # Memory documentation
│   ├── bugfixing.mdc                # Bug fixing documentation
│   ├── automation/                  # Automation functionality
│   │   ├── __init__.py
│   │   ├── core.py                  # Core automation classes
│   │   ├── actions.py               # Action definitions
│   │   ├── executor.py              # Sequence execution
│   │   ├── search_patterns.py       # Search pattern generators
│   │   ├── gui/                     # Automation GUI components
│   │       ├── __init__.py
│   │       ├── automation_tab.py    # Main automation tab
│   │       ├── position_marker.py   # Position marking tool
│   │       ├── action_params.py     # Action parameter widgets
│   │       ├── debug_window.py      # Automation debug window
│   │       └── search_pattern_dialog.py # Search pattern configuration
│   ├── gui/                         # GUI components
│   │   ├── __init__.py
│   │   └── overlay_controller.py    # Overlay controller
│   ├── templates/                   # Template images
│   │   ├── buildings/               # Building templates
│   │   ├── resources/               # Resource templates
│   │   ├── monsters/                # Monster templates
│   │   └── ui/                      # UI element templates
│   ├── sounds/                      # Sound files
│   │   ├── notification.wav
│   │   ├── success.wav
│   │   └── error.wav
│   └── debug_screenshots/           # Debug screenshots
├── tests/                           # Test directory
│   ├── __init__.py
│   ├── test_window_manager.py
│   ├── test_template_matcher.py
│   ├── test_text_ocr.py
│   └── ...
├── pyproject.toml                   # Project configuration
├── uv.lock                          # Dependency lock file
└── README.md                        # Project documentation
```

## Code Flow

### 1. Application Startup
1. `main.py` initializes the application
2. Creates `WindowManager` to find and track the game window
3. Initializes `ConfigManager` to load settings
4. Creates `TemplateMatcher` for pattern detection
5. Creates `TextOCR` for text extraction
6. Creates `GameActions` for mouse and keyboard control
7. Creates `Overlay` for visualization
8. Creates `OverlayController` for the user interface
9. Starts the PyQt6 event loop

### 1. Application Startup Flow Diagram

```
┌─────────────┐     ┌─────────────────┐     ┌───────────────┐     ┌─────────────────┐
│   main.py   │────▶│ WindowManager   │────▶│ ConfigManager │────▶│ TemplateMatcher │
└─────────────┘     └─────────────────┘     └───────────────┘     └─────────────────┘
       │                                                                   │
       │                                                                   ▼
       │                ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
       └───────────────▶│   TextOCR   │◀───▶│ GameActions │◀───▶│ GameCoordinator │
                        └─────────────┘     └─────────────┘     └─────────────────┘
                              │                                         ▲
                              ▼                                         │
                        ┌─────────────┐     ┌─────────────────┐        │
                        │   Overlay   │────▶│ OverlayController│───────┘
                        └─────────────┘     └─────────────────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ PyQt6 Event │
                                              │    Loop     │
                                              └─────────────┘
```

### 2. Pattern Matching Process
1. User toggles pattern matching via the UI or keyboard shortcut
2. `OverlayController._toggle_pattern_matching()` is called
3. Updates button state and calls `overlay.start_template_matching()`
4. `Overlay` starts a timer to periodically capture screenshots
5. For each screenshot, `TemplateMatcher.find_matches()` is called
6. Matches are visualized on the overlay
7. Process continues until stopped by user

### 2. Pattern Matching Process Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ User Interface  │────▶│ OverlayController│────▶│ Overlay.start_  │
│  (Button/Key)   │     │ _toggle_pattern_ │     │template_matching│
└─────────────────┘     │    matching()    │     └─────────────────┘
                        └─────────────────┘              │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Overlay.draw_   │◀────│TemplateMatcher. │◀────│ WindowManager.  │
│   matches()     │     │ find_matches()  │     │capture_screenshot│
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 3. OCR Process
1. User toggles OCR via the UI or keyboard shortcut
2. `OverlayController._toggle_ocr()` is called
3. Updates button state and calls `_start_ocr()` or `_stop_ocr()`
4. `TextOCR` starts processing the specified region
5. Extracted text is processed to find coordinates
6. Coordinates are updated in `GameWorldCoordinator`
7. Process continues until stopped by user

### 3. OCR Process Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ User Interface  │────▶│ OverlayController│────▶│ _start_ocr() or │
│  (Button/Key)   │     │   _toggle_ocr()  │     │   _stop_ocr()   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│GameCoordinator. │◀────│ TextOCR._extract_│◀────│ TextOCR._process│
│update_current_  │     │  coordinates()   │     │    _region()    │
│position_from_ocr│     └─────────────────┘     └─────────────────┘
└─────────────────┘
```

### 4. Game World Search
1. User initiates a search via the UI
2. `GameWorldSearch.search_templates()` is called
3. Current position is updated from OCR
4. Search pattern is generated (spiral, grid, etc.)
5. For each position in the pattern:
   - If position is on screen, check for templates
   - If position is not on screen, move to it and then check
6. If a match is found, search result is returned
7. Search statistics are updated

### 4. Game World Search Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ User Interface  │────▶│ GameWorldSearch.│────▶│GameCoordinator. │
│  (Search Button)│     │search_templates()│     │update_current_  │
└─────────────────┘     └─────────────────┘     │position_from_ocr│
                                                └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Search Pattern  │────▶│For each position│────▶│ Is position on  │
│   Generation    │     │   in pattern    │     │     screen?     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                    ┌──────┴──────┐
                                                    ▼             ▼
                                          ┌─────────────┐  ┌─────────────┐
                                          │ Check for   │  │ Move to     │
                                          │ templates   │  │ position    │
                                          └─────────────┘  └─────────────┘
                                                    │             │
                                                    └──────┬──────┘
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Return search   │
                                                  │    result       │
                                                  └─────────────────┘
```

### 5. Automation Sequence Execution
1. User builds a sequence using `SequenceBuilder`
2. User clicks "Run" to execute the sequence
3. `SequenceExecutor` is created with the current context
4. For each action in the sequence:
   - Action is executed based on its type
   - Progress is updated in the UI
   - Debug information is displayed
5. Sequence completes or is stopped by user

### 5. Automation Sequence Execution Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ SequenceBuilder │────▶│ _on_run_clicked()│────▶│ SequenceExecutor│
│  (Run Button)   │     │                  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Update progress │◀────│ For each action │◀────│ Create execution│
│    in UI        │     │  in sequence    │     │     context     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │
        │                        ▼
        │               ┌─────────────────┐
        │               │ Execute action  │
        │               │ based on type   │
        │               └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│ Update debug    │◀────│ Sequence        │
│   window        │     │ completed/stopped│
└─────────────────┘     └─────────────────┘
```

## Libraries Used

### Core Libraries
- **PyQt6**: GUI framework for the application interface
- **OpenCV (cv2)**: Computer vision library for pattern matching
- **pytesseract**: OCR engine wrapper for text extraction
- **numpy**: Numerical computing library for data handling
- **mss**: Fast screen capture library

### Automation Libraries
- **pynput**: Library for monitoring and controlling input devices
- **pydirectinput**: Library for simulating input events
- **pyautogui**: Library for GUI automation

### System Integration
- **win32api**: Windows API for window management
- **ctypes**: Foreign function library for calling Windows functions

### Utility Libraries
- **logging**: Standard library for logging
- **json**: Standard library for JSON handling
- **pathlib**: Object-oriented filesystem paths
- **time**: Time access and conversions
- **re**: Regular expression operations

## Recent Updates

### OCR Process Performance Improvements

The OCR process has been optimized to improve performance and stability:

1. **Reduced Temporary Files**: Modified the OCR process to minimize the creation of temporary PNG files in the system temp folder.
2. **Rate Limiting**: Implemented a rate limiter to prevent excessive OCR operations that could cause the application to hang.
3. **Optimized Method Selection**: Enhanced the OCR method selection to only process the preferred method when not in auto mode.
4. **Standardized Configuration**: Standardized OCR configuration parameters to reduce redundancy and improve performance.
5. **Improved Error Handling**: Enhanced timeout mechanisms and error handling to prevent the application from becoming unresponsive.

These improvements ensure the application remains responsive during OCR operations, especially when used with the drag calibration system, and significantly reduces the number of temporary files created.

### OCR Process and Key Handling Improvements

The OCR process and key handling have been improved to enhance reliability and user experience:

1. **Coordinate Display Enhancement**: Modified the coordinate display to show partial coordinates with placeholders for missing values, using color coding to indicate full, partial, or missing coordinates.
2. **Improved Key Handling**: Fixed the Q/Escape key handling to properly stop the OCR process by checking button state instead of internal OCR state.
3. **Consistent State Tracking**: Enhanced the TextOCR class with a proper active property to ensure consistent state tracking between the UI and backend.
4. **Robust Error Handling**: Added comprehensive error handling throughout the OCR process to prevent crashes and provide better feedback.
5. **Detailed Logging**: Implemented more detailed logging to help diagnose coordinate display issues.

These improvements ensure that coordinates are displayed in the GUI even when some values are missing, and that the OCR process can be reliably stopped using keyboard shortcuts.

### OCR Frequency Limit Implementation

A configurable OCR frequency limit has been implemented to improve application stability and performance:

1. **Maximum Frequency Setting**: Added a `max_frequency` setting in the configuration with a default value of 2.0 updates per second.
2. **Dynamic UI Controls**: Updated the OCR frequency controls in the GUI to respect the maximum frequency limit.
3. **Frequency Validation**: Enhanced the `TextOCR` class to validate and enforce the maximum frequency.
4. **Configuration Management**: Improved the `ConfigManager` to handle the new setting across application restarts.
5. **User Feedback**: Updated the UI to display the current maximum frequency limit to users.

This implementation prevents excessive OCR updates that could cause performance issues or crashes, particularly on less powerful systems or when dealing with complex game states.

### Coordinate System and OCR Process Improvements

The coordinate system and OCR process have been improved to enhance stability and user experience:

1. **Error Handling**: Added robust error handling to prevent application crashes and freezes during coordinate updates.
2. **Timeout Mechanisms**: Implemented timeout mechanisms in both the UI and backend to prevent the application from hanging during OCR operations.
3. **Fallback Strategies**: Enhanced the system to use existing coordinates when OCR fails, ensuring continuous operation.
4. **User Feedback**: Improved error messages and visual indicators to provide better feedback when coordinate reading fails.
5. **Auto-Update Safety**: Modified the auto-update feature to safely stop when errors occur, preventing cascading failures.

These improvements make the application more robust and responsive, particularly when dealing with challenging game states where OCR might struggle to read coordinates accurately.

### OCR Process Cancellation Improvements

The OCR process cancellation mechanism has been significantly improved to enhance responsiveness and prevent the application from getting stuck:

1. **Comprehensive Cancellation System**: Implemented a cancellation flag system throughout the OCR process to allow immediate stopping at any point.
2. **Multiple Cancellation Check Points**: Added cancellation checks at key points in the OCR process to ensure timely response to stop requests.
3. **Improved Key Press Handling**: Enhanced the Escape/Q key handling to immediately set cancellation flags before stopping the OCR process.
4. **Integrated Timeout and Cancellation**: Connected timeout mechanisms with the cancellation system to ensure proper cleanup when operations take too long.
5. **Enhanced UI Feedback**: Added clear visual feedback when OCR operations are cancelled, including status messages and color-coded indicators.

These improvements ensure that the application remains responsive even during intensive OCR operations, and that users can reliably stop the OCR process at any time using the Escape or Q keys without the application becoming unresponsive.

### OCR Performance and Responsiveness Enhancements

The OCR process has been further optimized to improve performance, reduce resource usage, and enhance responsiveness:

1. **Improved Rate Limiting**: Increased the minimum time between OCR updates from 0.5 to 2.0 seconds to prevent excessive processing.
2. **Optimized Auto-Update**: Increased the coordinate auto-update interval from 2 to 5 seconds and ensured it's disabled by default.
3. **Enhanced Cancellation Verification**: Added multiple verification steps to ensure OCR is fully stopped when requested.
4. **More Frequent Timeout Checks**: Increased the frequency of timeout checks from every 500ms to every 200ms for faster response to cancellation.
5. **Reduced Mouse Centering**: Optimized the mouse centering process to occur less frequently, improving user experience.
6. **Coordinated Component Shutdown**: Ensured that all OCR-related processes (including auto-update) are properly stopped when OCR is cancelled.

These enhancements significantly improve the application's responsiveness and stability during OCR operations, reduce resource usage, and provide a better user experience by minimizing disruptions to mouse position and ensuring the application remains responsive at all times.

### OCR Region Unification

The coordinate reading system has been simplified and improved by unifying the OCR region handling:

1. **Single OCR Region**: Removed the separate coordinate region selection system and now exclusively use the OCR region selected in the overlay tab for all coordinate reading operations.
2. **Simplified User Interface**: Removed the coordinate region dropdown from the Game World Coordinates widget, replacing it with a clear note explaining that coordinates are read from the OCR region selected in the Overlay tab.
3. **Improved Calibration Process**: Updated the calibration process to use the OCR region from the overlay tab, ensuring consistent coordinate reading during calibration.
4. **Enhanced Error Messaging**: Added clearer error messages when no OCR region is set, guiding users to select an OCR region in the overlay tab.
5. **Reduced Configuration Complexity**: Eliminated redundant configuration options, making the application more intuitive and reducing potential for confusion.

This unification simplifies the user experience, reduces code complexity, and ensures consistent coordinate reading across all application features. Users now only need to select the OCR region once in the overlay tab, and that region will be used for all coordinate-related operations including calibration.

## Conclusion

TB Scout is a sophisticated application that combines computer vision, automation, and GUI technologies to provide a powerful tool for interacting with the Total Battle game. Its modular design allows for easy extension and maintenance, while its feature set provides comprehensive capabilities for game automation.

The application's strengths lie in its:
- Robust pattern matching system
- Accurate OCR text extraction
- Sophisticated game world coordinate system (K, X, Y)
- Flexible automation capabilities
- Intuitive user interface
- Comprehensive debugging tools

These features make TB Scout an effective tool for automating repetitive tasks in the Total Battle game, enhancing the player experience by reducing manual effort and providing valuable information about the game world. 