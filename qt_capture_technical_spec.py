"""
Qt Window Capture Technical Specification

This document provides detailed technical specifications for the new Qt-based
window capture implementation that will replace the current WindowService.

Author: Scout Development Team
Date: Current
Status: Draft
"""

# ===============================================================
# 1. OVERVIEW
# ===============================================================

"""
The Qt Window Capture module will replace the current window detection and
capture system in Scout to address issues with overlay visibility for certain
applications like Total Battle. The new implementation will use Qt's native
QWindowCapture and QScreenCapture classes to provide a more reliable way to
capture windows and screens for use in detection and automation.

Key advantages:
1. More reliable window detection and capture
2. Better handling of DirectX/game windows
3. Eliminates overlay visibility issues
4. Provides integrated window/screen selection UI
5. Supports both real-time and on-demand captures
"""

# ===============================================================
# 2. ARCHITECTURE
# ===============================================================

"""
2.1 Key Components

1. QtWindowService - Core window capture service
2. CaptureSession - Media session management
3. SourceType - Enumeration of capture source types
4. WindowListModel - Model for available windows
5. ScreenListModel - Model for available screens 
6. WindowSelectorWidget - UI component for window selection
7. CapturePreviewWidget - UI component for displaying captures

2.2 Dependencies

Core Dependencies:
- PyQt6.QtMultimedia (QWindowCapture, QScreenCapture, QMediaCaptureSession)
- PyQt6.QtMultimediaWidgets (QVideoWidget)
- PyQt6.QtWidgets (UI components)
- numpy (for image processing)
- cv2 (for conversion between QImage and numpy arrays)

2.3 Component Interactions

1. MainWindow → QtWindowService: Initializes and manages service
2. WindowSelectorWidget → QtWindowService: Selects capture source
3. QtWindowService → CaptureSession: Manages capture process
4. CaptureSession → DetectionService: Provides frames for detection
5. WindowSelectorWidget ↔ WindowListModel: Displays available windows
"""

# ===============================================================
# 3. CORE SERVICES
# ===============================================================

"""
3.1 Source Type Enumeration

class SourceType(enum.Enum):
    Screen = auto()
    Window = auto()

3.2 QtWindowService Class

Implements the WindowServiceInterface, providing compatibility with existing code
while adding new functionality for Qt-based window capture.

class QtWindowService(QObject, WindowServiceInterface):
    # Signals
    window_selected = pyqtSignal(object)  # QCapturableWindow or QScreen
    window_lost = pyqtSignal()
    frame_captured = pyqtSignal(object)   # QImage
    capture_error = pyqtSignal(str)       # Error message
    
    def __init__(self, window_title: Optional[str] = None, event_bus: Optional[EventBus] = None):
        # Initialize with optional window title for backward compatibility
        # Initialize capture objects and media session
        
    # Methods implementing WindowServiceInterface
    def find_window(self) -> bool:
        # Find window by title (backward compatibility)
        # Returns True if found, False otherwise
        
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        # Get window position and size
        # Returns (x, y, width, height) tuple
        
    def capture_screenshot(self) -> Optional[np.ndarray]:
        # Capture screenshot and convert to numpy array
        # Returns BGR image as numpy array
        
    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        # Convert client coordinates to screen coordinates
        
    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        # Convert screen coordinates to client coordinates
        
    # New methods for Qt-based window capture
    def get_available_windows(self) -> List[QCapturableWindow]:
        # Get list of available windows for capture
        
    def get_available_screens(self) -> List[QScreen]:
        # Get list of available screens for capture
        
    def select_window(self, window: QCapturableWindow) -> bool:
        # Select window for capture
        # Returns True if successful
        
    def select_screen(self, screen: QScreen) -> bool:
        # Select screen for capture
        # Returns True if successful
        
    def start_capture(self) -> bool:
        # Start continuous capture
        # Returns True if successful
        
    def stop_capture(self) -> None:
        # Stop continuous capture
        
    # Helper methods
    def _qimage_to_numpy(self, image: QImage) -> np.ndarray:
        # Convert QImage to numpy array
        
    def _numpy_to_qimage(self, array: np.ndarray) -> QImage:
        # Convert numpy array to QImage
        
    def _on_frame_changed(self):
        # Handle frame update from video sink
        
3.3 CaptureSession Class

Manages the media capture session, including window/screen capture and video output.

class CaptureSession(QObject):
    # Signals
    frame_ready = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        # Initialize media capture session, window and screen capture objects
        
    def set_capture_source(self, source_type: SourceType, source: Union[QCapturableWindow, QScreen]) -> bool:
        # Set the capture source (window or screen)
        # Returns True if successful
        
    def start(self) -> bool:
        # Start capturing frames
        # Returns True if successful
        
    def stop(self) -> None:
        # Stop capturing frames
        
    def is_active(self) -> bool:
        # Check if capture is active
        # Returns True if active
        
    def take_screenshot(self) -> Optional[QImage]:
        # Take a single screenshot
        # Returns QImage or None if failed
        
    def set_video_output(self, video_widget: QVideoWidget) -> None:
        # Set video widget to display captured frames
        
    # Helper methods
    def _on_window_error(self, error: int, error_string: str) -> None:
        # Handle window capture error
        
    def _on_screen_error(self, error: int, error_string: str) -> None:
        # Handle screen capture error
"""

# ===============================================================
# 4. UI MODELS
# ===============================================================

"""
4.1 WindowListModel Class

Model for displaying available windows in a list view.

class WindowListModel(QAbstractListModel):
    def __init__(self, parent=None):
        # Initialize model with list of capturable windows
        
    def rowCount(self, index) -> int:
        # Return number of available windows
        
    def data(self, index, role) -> Optional[str]:
        # Return window description for DisplayRole
        
    def window(self, index) -> QCapturableWindow:
        # Return window at the given index
        
    def populate(self) -> None:
        # Refresh the list of available windows
        
4.2 ScreenListModel Class

Model for displaying available screens in a list view.

class ScreenListModel(QAbstractListModel):
    def __init__(self, parent=None):
        # Initialize model with list of screens
        
    def rowCount(self, index) -> int:
        # Return number of available screens
        
    def data(self, index, role) -> Optional[str]:
        # Return screen description for DisplayRole
        
    def screen(self, index) -> QScreen:
        # Return screen at the given index
        
    def screens_changed(self) -> None:
        # Handle screen changes (added/removed)
"""

# ===============================================================
# 5. UI COMPONENTS
# ===============================================================

"""
5.1 WindowSelectorWidget Class

Widget for selecting a window or screen to capture.

class WindowSelectorWidget(QWidget):
    # Signals
    window_selected = pyqtSignal(QCapturableWindow)
    screen_selected = pyqtSignal(QScreen)
    
    def __init__(self, parent=None):
        # Initialize widget with list views for windows and screens
        
    def _create_ui(self) -> None:
        # Create UI components
        
    def _on_window_selection_changed(self, selection) -> None:
        # Handle window selection change
        
    def _on_screen_selection_changed(self, selection) -> None:
        # Handle screen selection change
        
    def populate(self) -> None:
        # Refresh window and screen lists
        
5.2 CapturePreviewWidget Class

Widget for displaying captured frames.

class CapturePreviewWidget(QWidget):
    # Signals
    screenshot_taken = pyqtSignal(QImage)
    
    def __init__(self, parent=None):
        # Initialize widget with video widget for display
        
    def _create_ui(self) -> None:
        # Create UI components
        
    def set_capture_session(self, session: CaptureSession) -> None:
        # Set capture session for preview
        
    def take_screenshot(self) -> None:
        # Take screenshot and emit signal
        
    def toggle_auto_screenshot(self, enabled: bool) -> None:
        # Toggle automatic screenshot mode
"""

# ===============================================================
# 6. INTEGRATION POINTS
# ===============================================================

"""
6.1 Service Integration

- Update ServiceLocator to register QtWindowService
- Modify MainWindow to use QtWindowService
- Update DetectionService to work with QImage captures

6.2 UI Integration

- Add WindowSelectorWidget to DetectionTab
- Add CapturePreviewWidget to DetectionTab for preview
- Connect signals between components

6.3 Compatibility Layer

Ensure compatibility with existing code by:
- Maintaining the same WindowServiceInterface implementation
- Converting between QImage and numpy arrays seamlessly
- Providing backward-compatible methods for window selection
"""

# ===============================================================
# 7. TESTING PLAN
# ===============================================================

"""
7.1 Unit Tests

- Test QtWindowService methods
- Test CaptureSession functionality
- Test model data handling
- Test QImage/numpy conversion

7.2 Integration Tests

- Test service integration with detection
- Test UI component integration
- Test window/screen selection
- Test capture performance

7.3 Manual Tests

- Test with various window types (standard, DirectX, browser)
- Test with different screen configurations
- Test performance with various capture resolutions
- Test compatibility with existing features
"""

# ===============================================================
# 8. IMPLEMENTATION PHASES
# ===============================================================

"""
8.1 Phase 1: Core Services (2 days)

- Implement QtWindowService
- Implement CaptureSession
- Implement QImage/numpy conversion
- Create basic tests

8.2 Phase 2: Models and UI Components (3 days)

- Implement WindowListModel and ScreenListModel
- Implement WindowSelectorWidget
- Implement CapturePreviewWidget
- Connect signals and slots

8.3 Phase 3: Integration and Testing (3 days)

- Integrate with main application
- Update DetectionTab UI
- Run comprehensive tests
- Fix any issues

8.4 Phase 4: Documentation and Finalization (2 days)

- Update developer documentation
- Add user documentation
- Finalize implementation
- Prepare for release
"""

# ===============================================================
# 9. KNOWN LIMITATIONS AND CHALLENGES
# ===============================================================

"""
9.1 Potential Issues

- Admin rights may be required for capturing certain windows
- High DPI scaling may affect capture quality
- Performance impact of continuous capture
- Compatibility with existing detection code

9.2 Mitigation Strategies

- Clear user messaging for permission requirements
- DPI-aware capture options
- Configurable capture rates and quality
- Thorough testing with existing code
"""

# ===============================================================
# 10. APPENDIX
# ===============================================================

"""
10.1 Class Diagram

QtWindowService
├── CaptureSession
│   ├── QWindowCapture
│   └── QScreenCapture
├── WindowListModel
└── ScreenListModel

UI Components
├── WindowSelectorWidget
│   ├── QListView (Windows)
│   └── QListView (Screens)
└── CapturePreviewWidget
    └── QVideoWidget

10.2 References

- Qt Documentation: QWindowCapture
  https://doc.qt.io/qt-6/qwindowcapture.html
  
- Qt Documentation: QScreenCapture
  https://doc.qt.io/qt-6/qscreencapture.html
  
- Qt Documentation: QMediaCaptureSession
  https://doc.qt.io/qt-6/qmediacapturesession.html
""" 