"""
Main Window

This module provides the main application window for the Scout application.
It integrates all UI components and connects to the core services.
"""

import sys
import os
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QToolBar, QStatusBar, 
    QMenuBar, QMenu, QMessageBox, QDialog, QFileDialog, 
    QDockWidget, QSplitter
)
from PyQt6.QtGui import (
    QIcon, QFont, QPixmap, QKeySequence, QCloseEvent, QAction, 
    QPainter, QPen, QBrush, QColor, QFontMetrics
)
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer, pyqtSignal, QEvent, QThread, QRect

# Import service interfaces from the centralized interfaces module
from scout.core.interfaces.service_interfaces import (
    DetectionServiceInterface,
    AutomationServiceInterface,
    WindowServiceInterface
)

# Update the import path for the game service interface
from scout.core.game.game_service_interface import GameServiceInterface

# Import service implementations (or mock implementations for now)
from scout.core.detection.detection_service import DetectionService
from scout.core.automation.automation_service import AutomationService
from scout.core.game.game_service import GameService
from scout.core.game.game_state_service_interface import GameStateServiceInterface
from scout.core.window.window_service import WindowService
from scout.core.events.event_bus import EventBus

# Import the ServiceLocator from the UI module
from scout.ui.service_locator_ui import ServiceLocator

# Import UI components
from scout.ui.views.detection_tab import DetectionTab
from scout.ui.views.automation_tab import AutomationTab
from scout.ui.views.game_tab import GameTab
from scout.ui.views.settings_tab import SettingsTab
from scout.ui.widgets.detection_result_widget import DetectionResultWidget
from scout.ui.widgets.control_panel_widget import ControlPanelWidget

# Import language manager
from scout.ui.utils.language_manager import get_language_manager, tr

# Import updater components
from scout.core.updater import (
    get_update_settings, check_for_updates_in_background, show_update_dialog
)

# Set up logging
logger = logging.getLogger(__name__)


class OverlayView(QWidget):
    """
    Transparent window for visualizing detection results in real-time.
    
    This window is overlaid on top of the target application window
    and shows detection results as they occur.
    """
    
    def __init__(self, window_service: WindowServiceInterface):
        """
        Initialize the overlay view.
        
        Args:
            window_service: Service for window management
        """
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        # Store services
        self.window_service = window_service
        
        # Initialize state
        self._results = []
        self._target_window_rect = None
        self._visible = False
        self._update_failures = 0  # Track consecutive failures
        self._last_update_time = 0  # Track last successful update time
        
        # Configure window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        
        # Create update timer
        self._create_update_timer()
        
        logger.info("Overlay view initialized with flags: FramelessWindowHint | WindowStaysOnTopHint | Tool")
    
    def _create_update_timer(self):
        """Create timer for updating overlay position and content."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_position)
        # Use shorter interval for more responsive updates
        update_interval = 100  # 10 fps
        self.update_timer.start(update_interval)
        logger.debug(f"Overlay position update timer started with interval: {update_interval}ms")
    
    def _update_position(self):
        """Update overlay position to match target window."""
        if not self._visible:
            return
            
        try:
            # Get target window position and size
            target_rect = self.window_service.get_window_position()
            current_time = time.time()
            
            # Debug log window position
            if target_rect:
                x, y, width, height = target_rect
                logger.debug(f"Target window position: x={x}, y={y}, width={width}, height={height}")
            else:
                logger.debug("Target window position: None (window not found)")
            
            # Check if target_rect is not None
            if target_rect is not None:
                # Reset failure counter on success
                self._update_failures = 0
                self._last_update_time = current_time
                
                # Always update position even if it seems the same (minor differences might not be detected)
                old_rect = self._target_window_rect
                self._target_window_rect = target_rect
                
                # Update overlay position and size
                self.setGeometry(*target_rect)
                
                # Only log if position actually changed significantly
                if old_rect is None or abs(old_rect[0] - target_rect[0]) > 1 or abs(old_rect[1] - target_rect[1]) > 1:
                    logger.debug(f"Overlay position updated from {old_rect} to {target_rect}")
                
                # Ensure overlay is visible and stays on top
                if not self.isVisible():
                    logger.warning("Overlay should be visible but isn't - showing it again")
                    self.show()
                
                # Always force the overlay to the top to ensure it's visible
                self.raise_()
                
                # Force a repaint if we have results to show
                if self._results:
                    self.update()
            else:
                # Increment failure counter
                self._update_failures += 1
                
                if self._update_failures == 1:
                    logger.warning("Target window not found, but overlay is visible")
                
                # If we've had multiple consecutive failures, hide the overlay
                if self._update_failures >= 5:  # Hide after 5 consecutive failures (500ms)
                    logger.warning("Multiple failures finding target window, hiding overlay")
                    self._visible = False
                    self.hide()
                    
                # If it's been too long since a successful update
                elapsed_time = current_time - self._last_update_time
                if elapsed_time > 2.0:  # 2 seconds with no updates
                    logger.warning(f"No window updates for {elapsed_time:.1f}s, hiding overlay")
                    self._visible = False
                    self.hide()
                    
        except Exception as e:
            logger.error(f"Error updating overlay position: {e}", exc_info=True)
            # If there's an exception, hide the overlay to be safe
            self._visible = False
            self.hide()
    
    def set_results(self, results: List[Dict[str, Any]]):
        """
        Set detection results to display.
        
        Args:
            results: List of detection result dictionaries
        """
        logger.debug(f"Setting overlay results: {len(results)} items")
        self._results = results
        self.update()
    
    def show_overlay(self, show: bool):
        """
        Show or hide the overlay.
        
        Args:
            show: Whether to show the overlay
        """
        logger.info(f"Setting overlay visibility to: {show}")
        self._visible = show
        
        if show:
            # Reset failure counters
            self._update_failures = 0
            self._last_update_time = time.time()
            
            # Make sure we have the right window flags
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                              Qt.WindowType.WindowStaysOnTopHint | 
                              Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            
            # Update position before showing
            target_rect = self.window_service.get_window_position()
            if target_rect:
                logger.info(f"Target window found at position: {target_rect}")
                self._target_window_rect = target_rect
                self.setGeometry(*target_rect)
                
                # Need to show after setting flags and geometry
                self.show()
                
                # Force the window to stay on top and not take focus
                self.raise_()
                self.activateWindow()
                
                # Force a repaint
                self.update()
                
                logger.debug("Overlay visibility set to true and shown")
            else:
                logger.warning("Cannot show overlay - target window not found")
                self._visible = False
        else:
            logger.debug("Hiding overlay")
            self.hide()
    
    def paintEvent(self, event):
        """
        Handle paint event.
        
        Args:
            event: Paint event
        """
        if not self._visible or not self._results:
            return
        
        try:
            # Create painter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Set up styles
            bounding_box_pen = QPen(QColor(0, 255, 0))
            bounding_box_pen.setWidth(2)
            
            text_box_brush = QBrush(QColor(0, 0, 0, 180))
            text_pen = QPen(QColor(255, 255, 255))
            
            # Draw each result
            for result in self._results:
                # Get bounding box
                if 'bbox' in result:
                    x, y, w, h = result['bbox']
                    
                    # Draw bounding box
                    painter.setPen(bounding_box_pen)
                    painter.drawRect(x, y, w, h)
                    
                    # Draw label if available
                    if 'label' in result:
                        label = result['label']
                        
                        # Get confidence if available
                        if 'confidence' in result:
                            confidence = result['confidence']
                            label = f"{label} ({confidence:.2f})"
                        
                        # Draw text background
                        font = painter.font()
                        font_metrics = QFontMetrics(font)
                        text_width = font_metrics.horizontalAdvance(label)
                        text_height = font_metrics.height()
                        
                        text_rect = QRect(x, y - text_height - 4, text_width + 6, text_height + 4)
                        painter.setBrush(text_box_brush)
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(text_rect)
                        
                        # Draw text
                        painter.setPen(text_pen)
                        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
                elif 'x' in result and 'y' in result and 'template_name' in result:
                    # Handle template match results
                    x, y = result['x'], result['y']
                    width = result.get('width', 50)  # Default if not provided
                    height = result.get('height', 50)  # Default if not provided
                    
                    # Draw bounding box
                    painter.setPen(bounding_box_pen)
                    painter.drawRect(x, y, width, height)
                    
                    # Draw template name and confidence
                    template_name = result['template_name']
                    confidence = result.get('confidence', 0.0)
                    label = f"{template_name} ({confidence:.2f})"
                    
                    # Draw text background
                    font = painter.font()
                    font_metrics = QFontMetrics(font)
                    text_width = font_metrics.horizontalAdvance(label)
                    text_height = font_metrics.height()
                    
                    text_rect = QRect(x, y - text_height - 4, text_width + 6, text_height + 4)
                    painter.setBrush(text_box_brush)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(text_rect)
                    
                    # Draw text
                    painter.setPen(text_pen)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
        except Exception as e:
            logger.error(f"Error in overlay paintEvent: {e}", exc_info=True)


class MainWindow(QMainWindow):
    """
    Main application window for Scout.
    
    This window integrates all UI components and connects to core services.
    It provides a tabbed interface for detection, automation, game state,
    and settings, as well as menus and toolbars for common actions.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize services and register with locator
        self._initialize_services()
        
        # Create UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Load settings
        self._load_settings()
        
        # Create overlay
        self._create_overlay()
        
        logger.info("Main window initialized")
    
    def _initialize_services(self):
        """Initialize and register core services."""
        # Create event bus
        event_bus = EventBus()
        
        # Create service instances
        window_service = WindowService(window_title="Total Battle", event_bus=event_bus)
        detection_service = DetectionService(event_bus=event_bus, window_service=window_service)
        automation_service = AutomationService(event_bus=event_bus)
        game_state_service = GameService(window_service=window_service, detection_service=detection_service, event_bus=event_bus)
        
        # Register detection strategies
        try:
            from scout.core.detection.strategies.template_strategy import TemplateMatchingStrategy as TemplateStrategy
            from scout.core.detection.strategies.ocr_strategy import OCRStrategy
            
            # Register template strategy
            template_strategy = TemplateStrategy()
            detection_service.register_strategy("template", template_strategy)
            
            # Verify template directory exists
            template_dir = template_strategy.templates_dir
            if not os.path.exists(template_dir):
                logger.warning(f"Template directory not found: {template_dir}")
                try:
                    os.makedirs(template_dir, exist_ok=True)
                    logger.info(f"Created template directory: {template_dir}")
                    
                    # Create a README file in the templates directory to help users
                    readme_path = os.path.join(template_dir, "README.txt")
                    with open(readme_path, "w") as f:
                        f.write("Place PNG template images in this directory for detection.\n")
                        f.write("Templates should be transparent PNGs with the target object clearly visible.\n")
                        f.write("The filename (without extension) will be used as the template name.\n")
                    
                    logger.info("Created README file in templates directory")
                except Exception as e:
                    logger.error(f"Failed to create template directory: {e}")
                    QMessageBox.warning(
                        self,
                        tr("Template Directory Missing"),
                        tr("Could not create template directory at {0}. Template detection may not work correctly.").format(template_dir)
                    )
            
            # Register OCR strategy
            detection_service.register_strategy("ocr", OCRStrategy())
            
            # Try to register YOLO strategy if possible
            try:
                from scout.core.detection.strategies.yolo_strategy import YOLOStrategy
                
                # Look for YOLO model in resources/models directory
                yolo_model_path = os.path.join(os.getcwd(), "resources", "models", "yolov5n.pt")
                
                # Check if model file exists
                if os.path.exists(yolo_model_path):
                    # Initialize with model path
                    detection_service.register_strategy("yolo", YOLOStrategy(model_path=yolo_model_path))
                    logger.info(f"YOLO strategy registered with model: {yolo_model_path}")
                else:
                    logger.warning(f"YOLO model not found at {yolo_model_path}, YOLO detection will not be available")
            except (ImportError, Exception) as e:
                logger.warning(f"YOLO strategy not registered: {e}")
        except ImportError as e:
            logger.error(f"Error registering detection strategies: {e}")
        
        # Register with locator
        ServiceLocator.register(WindowServiceInterface, window_service)
        ServiceLocator.register(DetectionServiceInterface, detection_service)
        ServiceLocator.register(AutomationServiceInterface, automation_service)
        ServiceLocator.register(GameStateServiceInterface, game_state_service)
        
        # Store references
        self.window_service = window_service
        self.detection_service = detection_service
        self.automation_service = automation_service
        self.game_state_service = game_state_service
        
        logger.info("Services initialized and registered")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle(tr("Scout"))
        self.resize(1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create control panel
        self._create_control_panel(main_layout)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_tabs()
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbar
        self._create_toolbar()
        
        # Create status bar
        self._create_status_bar()
    
    def _create_control_panel(self, layout):
        """
        Create the control panel widget.
        
        Args:
            layout: Layout to add the control panel to
        """
        # Create control panel
        self.control_panel = ControlPanelWidget()
        
        # Connect control panel signals
        self.control_panel.action_triggered.connect(self._on_control_panel_action)
        
        # Add to main layout
        layout.addWidget(self.control_panel)
    
    def _on_control_panel_action(self, action_id, params=None):
        """
        Handle action from control panel.
        
        Args:
            action_id: ID of the action
            params: Optional parameters for the action
        """
        logger.debug(f"Control panel action: {action_id}, params: {params}")
        
        # Handle common actions
        if action_id == "start":
            self._on_run()
        elif action_id == "stop":
            self._on_stop()
        elif action_id == "pause":
            self._on_pause()
        elif action_id == "resume":
            self._on_resume()
        elif action_id == "refresh":
            self._on_refresh()
        elif action_id == "screenshot":
            self._on_capture_screenshot()
        elif action_id == "toggle_overlay":
            self._on_toggle_overlay(params.get("checked", False) if params else None)
        else:
            # Handle tab-specific actions
            current_tab = self.tab_widget.currentWidget()
            
            if current_tab == self.detection_tab:
                if action_id == "run_template_detection":
                    self._run_template_detection()
                elif action_id == "run_ocr_detection":
                    self._run_ocr_detection()
            elif current_tab == self.automation_tab:
                # Automation-specific actions
                pass
            elif current_tab == self.game_tab:
                # Game state-specific actions
                pass
                
        # Update status
        self.control_panel.set_status(tr("Ready"))
    
    def _run_template_detection(self):
        """Run template detection."""
        # Make sure detection tab is current
        self.tab_widget.setCurrentWidget(self.detection_tab)
        
        # Run detection
        self.detection_tab.run_template_detection()
    
    def _run_ocr_detection(self):
        """Run OCR detection."""
        # Make sure detection tab is current
        self.tab_widget.setCurrentWidget(self.detection_tab)
        
        # Run detection
        self.detection_tab.run_ocr_detection()
    
    def _on_capture_window(self):
        """Handle capture window action."""
        # Update the window service to find the game window
        success = self.window_service.find_window()
        
        if success:
            # Get window position and create info dictionary
            position = self.window_service.get_window_position()
            if position:
                x, y, width, height = position
                window_info = {
                    "title": "Total Battle",
                    "position": (x, y),
                    "size": (width, height),
                    "state": self.window_service.get_window_state()
                }
                self._on_window_selected(window_info)
            else:
                success = False
        
        if not success:
            self._on_window_lost()
            
            # Show error message
            QMessageBox.warning(
                self,
                tr("Window Not Found"),
                tr("Could not find the game window. Please make sure the game is running.")
            )
    
    def _on_tab_changed(self, index):
        """
        Handle tab changes.
        
        Args:
            index: New tab index
        """
        # Get current tab widget
        current_tab = self.tab_widget.widget(index)
        
        # Update control panel context based on tab type
        if isinstance(current_tab, DetectionTab):
            self.control_panel.set_context("detection")
        elif isinstance(current_tab, AutomationTab):
            self.control_panel.set_context("automation")
        elif isinstance(current_tab, GameTab):
            self.control_panel.set_context("game_state")
        elif isinstance(current_tab, SettingsTab):
            self.control_panel.set_context("default")
        else:
            self.control_panel.set_context("default")
        
        # Update status
        self.control_panel.set_status("Ready")
    
    def _create_tabs(self):
        """Create the tab widget and individual tabs."""
        # Create detection tab
        self.detection_tab = DetectionTab(self.window_service, self.detection_service)
        self.tab_widget.addTab(self.detection_tab, tr("Detection"))
        
        # Create automation tab
        self.automation_tab = AutomationTab(
            self.automation_service, self.detection_service, self.window_service)
        self.tab_widget.addTab(self.automation_tab, tr("Automation"))
        
        # Create game state tab
        self.game_tab = GameTab(self.game_state_service, self.detection_service)
        self.tab_widget.addTab(self.game_tab, tr("Game State"))
        
        # Create settings tab
        self.settings_tab = SettingsTab(ServiceLocator)
        self.tab_widget.addTab(self.settings_tab, tr("Settings"))
        
        # Connect tab changed signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Set initial tab context
        self._on_tab_changed(self.tab_widget.currentIndex())
    
    def _create_menu_bar(self):
        """Create the application menu bar."""
        logger.debug("Creating menu bar")
        
        # Create menu bar
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu(tr("&File"))
        
        # New action
        new_action = QAction(QIcon.fromTheme("document-new"), tr("&New"), self)
        new_action.setShortcut("Ctrl+N")
        new_action.setStatusTip(tr("Create a new configuration"))
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)
        
        # Open action
        open_action = QAction(QIcon.fromTheme("document-open"), tr("&Open..."), self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip(tr("Open a configuration file"))
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)
        
        # Save action
        save_action = QAction(QIcon.fromTheme("document-save"), tr("&Save"), self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip(tr("Save the current configuration"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)
        
        # Save As action
        save_as_action = QAction(QIcon.fromTheme("document-save-as"), tr("Save &As..."), self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setStatusTip(tr("Save the configuration to a new file"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)
        
        # Separator
        file_menu.addSeparator()
        
        # Check for Updates action
        check_updates_action = QAction(QIcon.fromTheme("system-software-update"), tr("Check for &Updates..."), self)
        check_updates_action.setStatusTip(tr("Check for application updates"))
        check_updates_action.triggered.connect(self._on_check_for_updates)
        file_menu.addAction(check_updates_action)
        
        # Preferences action
        preferences_action = QAction(QIcon.fromTheme("preferences-system"), tr("&Preferences..."), self)
        preferences_action.setShortcut("Ctrl+P")
        preferences_action.setStatusTip(tr("Configure application preferences"))
        preferences_action.triggered.connect(self._on_preferences)
        file_menu.addAction(preferences_action)
        
        # Separator
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction(QIcon.fromTheme("application-exit"), tr("E&xit"), self)
        exit_action.setShortcut("Alt+F4")
        exit_action.setStatusTip(tr("Exit the application"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Window menu
        window_menu = menu_bar.addMenu(tr("&Window"))
        
        # Capture Window action
        capture_window_action = QAction(QIcon.fromTheme("view-fullscreen"), tr("&Select Window..."), self)
        capture_window_action.setStatusTip(tr("Select a window to capture"))
        capture_window_action.triggered.connect(self._on_capture_window)
        window_menu.addAction(capture_window_action)
        
        # Refresh action
        refresh_action = QAction(QIcon.fromTheme("view-refresh"), tr("&Refresh"), self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip(tr("Refresh the current view"))
        refresh_action.triggered.connect(self._on_refresh)
        window_menu.addAction(refresh_action)
        
        # Capture Screenshot action
        screenshot_action = QAction(QIcon.fromTheme("camera-photo"), tr("Capture &Screenshot"), self)
        screenshot_action.setShortcut("F9")
        screenshot_action.setStatusTip(tr("Capture a screenshot of the game window"))
        screenshot_action.triggered.connect(self._on_capture_screenshot)
        window_menu.addAction(screenshot_action)
        
        # Separator
        window_menu.addSeparator()
        
        # Toggle Overlay action
        self.overlay_action = QAction(QIcon.fromTheme("view-preview"), tr("Show &Overlay"), self)
        self.overlay_action.setCheckable(True)
        self.overlay_action.setStatusTip(tr("Toggle detection overlay"))
        self.overlay_action.triggered.connect(self._on_toggle_overlay)
        window_menu.addAction(self.overlay_action)
        
        # Debug Overlay action
        self.debug_overlay_action = QAction(QIcon.fromTheme("debug-step-into"), tr("Debug &Mode Overlay"), self)
        self.debug_overlay_action.setCheckable(True)
        self.debug_overlay_action.setStatusTip(tr("Toggle debug mode for overlay (very visible)"))
        self.debug_overlay_action.triggered.connect(self._on_toggle_debug_overlay)
        window_menu.addAction(self.debug_overlay_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu(tr("&Tools"))
        
        # Template Creator action
        template_creator_action = QAction(QIcon.fromTheme("document-new"), tr("&Template Creator..."), self)
        template_creator_action.setStatusTip(tr("Create detection templates"))
        template_creator_action.triggered.connect(self._on_template_creator)
        tools_menu.addAction(template_creator_action)
        
        # Sequence Recorder action
        sequence_recorder_action = QAction(QIcon.fromTheme("media-record"), tr("&Sequence Recorder..."), self)
        sequence_recorder_action.setStatusTip(tr("Record automation sequences"))
        sequence_recorder_action.triggered.connect(self._on_sequence_recorder)
        tools_menu.addAction(sequence_recorder_action)
        
        # Help menu
        help_menu = menu_bar.addMenu(tr("&Help"))
        
        # Documentation action
        documentation_action = QAction(QIcon.fromTheme("help-browser"), tr("&Documentation"), self)
        documentation_action.setShortcut("F1")
        documentation_action.setStatusTip(tr("View documentation"))
        documentation_action.triggered.connect(self._on_documentation)
        help_menu.addAction(documentation_action)
        
        # About action
        about_action = QAction(QIcon.fromTheme("help-about"), tr("&About"), self)
        about_action.setStatusTip(tr("About this application"))
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
        
        logger.debug("Menu bar created")
    
    def _create_toolbar(self):
        """Create the toolbar."""
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Add actions
        # TODO: Replace with actual icons
        
        # New action
        new_action = QAction("New", self)
        new_action.triggered.connect(self._on_new)
        toolbar.addAction(new_action)
        
        # Open action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self._on_open)
        toolbar.addAction(open_action)
        
        # Save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self._on_save)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Screenshot action
        screenshot_action = QAction("Screenshot", self)
        screenshot_action.triggered.connect(self._on_capture_screenshot)
        toolbar.addAction(screenshot_action)
        
        # Overlay action
        overlay_action = QAction("Overlay", self)
        overlay_action.setCheckable(True)
        overlay_action.setChecked(False)
        overlay_action.triggered.connect(self._on_toggle_overlay)
        toolbar.addAction(overlay_action)
        
        toolbar.addSeparator()
        
        # Run action
        run_action = QAction("Run", self)
        run_action.triggered.connect(self._on_run)
        toolbar.addAction(run_action)
        
        # Stop action
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self._on_stop)
        toolbar.addAction(stop_action)
        
        # Store reference
        self.toolbar = toolbar
    
    def _create_status_bar(self):
        """Create the status bar."""
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create status labels
        self.status_label = QLabel(tr("Ready"))
        self.status_bar.addWidget(self.status_label)
        
        # Add window status label
        self.window_status_label = QLabel(tr("No Window Selected"))
        self.window_status_label.setStyleSheet("color: red;")
        self.status_bar.addPermanentWidget(self.window_status_label)
        
        # Add detection status label
        self.detection_status_label = QLabel(tr("Detection: Idle"))
        self.status_bar.addPermanentWidget(self.detection_status_label)
    
    def _create_overlay(self):
        """
        Create the overlay window that displays detection results on top of the target window.
        
        Returns:
            bool: True if overlay was created successfully, False otherwise
        """
        try:
            logger.info("Creating overlay window...")
            
            # First check if we have an existing overlay and clean it up
            if hasattr(self, 'overlay') and self.overlay is not None:
                try:
                    logger.info("Cleaning up existing overlay before creating a new one")
                    if hasattr(self, 'overlay_timer') and self.overlay_timer is not None:
                        self.overlay_timer.stop()
                    self.overlay.hide()
                    self.overlay.deleteLater()
                    self.overlay = None
                except Exception as e:
                    logger.warning(f"Error cleaning up existing overlay: {e}")
            
            # Make sure we have a target window first
            if not self.window_service.find_window():
                logger.warning("Cannot create overlay: No target window selected")
                return False
                
            # Get window position to confirm we can track it
            window_position = self.window_service.get_window_position()
            if not window_position:
                logger.warning("Cannot create overlay: Unable to get window position")
                return False
                
            # Log target window info for debugging
            x, y, width, height = window_position
            target_info = f"Target window position: ({x}, {y}), size: {width}x{height}"
            logger.info(target_info)
            
            # Create the overlay view with the parent window reference
            logger.debug("Creating OverlayView instance with self as parent")
            self.overlay = OverlayView(self)
            
            # Set initial position to match the target window
            self.overlay.setGeometry(x, y, width, height)
            
            # Set up the overlay timer - use shorter interval for more responsive updates
            logger.debug("Setting up overlay update timer")
            self.overlay_timer = QTimer()
            self.overlay_timer.timeout.connect(self.overlay._update_position)
            self.overlay_timer.start(50)  # Update position every 50ms (20 fps) for more responsive tracking
            
            # Force initial position update
            self.overlay._target_window_rect = QRect(x, y, width, height)
            
            logger.info("Overlay created successfully")
            
            # Force debug mode
            self.overlay.debug_mode = True
            
            # Inform user that debug mode is enabled
            QMessageBox.information(
                self,
                tr("Debug Mode"),
                tr("The overlay has been created in debug mode. You should see a red tinted overlay with debug information on top of the Total Battle window. If you don't see the overlay, please try the 'Debug Mode Overlay' option in the Window menu.")
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create overlay: {str(e)}", exc_info=True)
            return False
    
    def _connect_signals(self):
        """Connect signals between components."""
        try:
            # Connect detection tab signals if available
            if hasattr(self.detection_tab, 'detection_results_ready'):
                self.detection_tab.detection_results_ready.connect(self._on_detection_results)
            
            # Connect settings tab signals if available
            if hasattr(self.settings_tab, 'settings_changed'):
                self.settings_tab.settings_changed.connect(self._on_settings_changed)
            
            # Connect window service signals
            if hasattr(self.window_service, 'window_selected'):
                self.window_service.window_selected.connect(self._on_window_selected)
            if hasattr(self.window_service, 'window_lost'):
                self.window_service.window_lost.connect(self._on_window_lost)
            
            # Connect other available window service signals
            if hasattr(self.window_service, 'window_moved'):
                self.window_service.window_moved.connect(self._on_window_moved)
            if hasattr(self.window_service, 'window_state_changed'):
                self.window_service.window_state_changed.connect(self._on_window_state_changed)
        except Exception as e:
            logger.error(f"Error connecting signals: {str(e)}")
    
    def _load_settings(self):
        """Load application settings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Load window geometry
        if settings.contains("mainwindow/geometry"):
            self.restoreGeometry(settings.value("mainwindow/geometry"))
        
        # Load window state
        if settings.contains("mainwindow/state"):
            self.restoreState(settings.value("mainwindow/state"))
        
        # Load last active tab
        if settings.contains("mainwindow/active_tab"):
            active_tab = int(settings.value("mainwindow/active_tab", 0))
            self.tab_widget.setCurrentIndex(active_tab)
    
    def _save_settings(self):
        """Save application settings."""
        settings = QSettings("ScoutTeam", "Scout")
        
        # Save window geometry
        settings.setValue("mainwindow/geometry", self.saveGeometry())
        
        # Save window state
        settings.setValue("mainwindow/state", self.saveState())
        
        # Save active tab
        settings.setValue("mainwindow/active_tab", self.tab_widget.currentIndex())
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        try:
            # Save settings
            self._save_settings()
            
            # Hide overlay if it exists
            if hasattr(self, 'overlay') and self.overlay is not None:
                try:
                    self.overlay.hide()
                    logger.debug("Overlay hidden during application close")
                except Exception as e:
                    logger.warning(f"Error hiding overlay during close: {e}")
            
            # Shut down services
            ServiceLocator.shutdown()
            logger.info("Services shut down during application close")
            
        except Exception as e:
            logger.error(f"Error during application close: {e}")
            
        # Accept event
        event.accept()
    
    def _on_detection_results(self, results: List[Dict[str, Any]]):
        """
        Handle detection results from the detection tab.
        
        Args:
            results: List of detection result dictionaries
        """
        # Update overlay with results
        if self.overlay and self.overlay._visible:
            self.overlay.set_results(results)
    
    def _on_settings_changed(self, settings: Dict[str, Any]):
        """
        Handle settings changes.
        
        Args:
            settings: Updated settings dictionary
        """
        # Apply settings to services
        # This is a simplified version - in a real app, we'd need to
        # update each service with its specific settings
        
        # Update window service settings
        window_settings = settings.get("window", {})
        if window_settings:
            self.window_service.apply_settings(window_settings)
        
        # Update detection service settings
        detection_settings = settings.get("detection", {})
        if detection_settings:
            self.detection_service.apply_settings(detection_settings)
        
        # Update automation service settings
        automation_settings = settings.get("automation", {})
        if automation_settings:
            self.automation_service.apply_settings(automation_settings)
        
        # Update UI settings
        ui_settings = settings.get("ui", {})
        if ui_settings:
            self._apply_ui_settings(ui_settings)
    
    def _apply_ui_settings(self, ui_settings: Dict[str, Any]):
        """
        Apply UI settings.
        
        Args:
            ui_settings: UI settings dictionary
        """
        # Apply theme
        theme = ui_settings.get("theme", "system")
        # TODO: Implement theme switching
        
        # Apply font size
        font_size = ui_settings.get("font_size", 10)
        font = QFont()
        font.setPointSize(font_size)
        QApplication.setFont(font)
        
        # Apply other UI settings as needed
    
    def _on_window_selected(self, window_info: Dict[str, Any]):
        """
        Handle window selection event.
        
        Args:
            window_info: Window information dictionary
        """
        try:
            # Update status bar
            window_title = window_info.get("title", "Unknown")
            self.window_status_label.setText(f"Target: {window_title}")
            
            logger.info(f"Window selected: {window_title}")
            
            # Check if overlay exists and initialize it if needed
            overlay_existed = hasattr(self, 'overlay') and self.overlay is not None
            
            if not overlay_existed:
                logger.info("Initializing overlay for the first time")
                self._create_overlay()
                if hasattr(self, 'overlay') and self.overlay is not None:
                    logger.debug("Overlay successfully created")
                else:
                    logger.error("Failed to create overlay - check the create_overlay method")
            else:
                logger.debug("Overlay already exists, ensuring it's properly positioned")
                # Force a position update if overlay is visible
                if self.overlay._visible:
                    self.overlay._update_position()
            
            # Enable actions that require a target window
            if hasattr(self, 'overlay_action'):
                self.overlay_action.setEnabled(True)
            
            # Check user settings for auto-showing overlay
            show_overlay = False
            try:
                if hasattr(self, 'settings_tab') and hasattr(self.settings_tab, 'settings_model'):
                    settings = self.settings_tab.settings_model.get_all_settings()
                    appearance_settings = settings.get('appearance', {})
                    show_overlay = appearance_settings.get('show_overlay', True)  # Default to True if not specified
                    logger.info(f"Auto-show overlay setting: {show_overlay}")
                else:
                    logger.debug("Settings model not available, defaulting to show overlay")
                    show_overlay = True
            except Exception as e:
                logger.warning(f"Error accessing overlay settings: {e}")
                show_overlay = True  # Default to showing overlay if settings can't be accessed
            
            # Auto-show overlay based on settings
            if show_overlay:
                logger.info("Auto-showing overlay based on settings")
                if hasattr(self, 'overlay_action'):
                    self.overlay_action.setChecked(True)
                self._on_toggle_overlay(True)
            else:
                logger.debug("Not auto-showing overlay based on settings")
                
        except Exception as e:
            logger.error(f"Error handling window selection: {e}", exc_info=True)
    
    def _on_window_lost(self):
        """Handle window loss event."""
        logger.info("Target window lost")
        
        # Update status bar
        self.window_status_label.setText("No target window")
        
        # Disable overlay
        if hasattr(self, 'overlay_action') and self.overlay_action is not None:
            self.overlay_action.setChecked(False)
            self._on_toggle_overlay(False)
            self.overlay_action.setEnabled(False)
        else:
            logger.warning("overlay_action not initialized in _on_window_lost")
    
    def _on_toggle_overlay(self, checked: bool):
        """
        Handle overlay toggle.
        
        Args:
            checked: Whether the overlay should be shown
        """
        logger.info(f"Toggling overlay visibility to: {checked}")
        
        try:
            # Verify window service state first
            window_active = self.window_service.find_window()
            if not window_active:
                logger.warning("Cannot toggle overlay: No target window found")
                QMessageBox.warning(
                    self,
                    tr("No Target Window"),
                    tr("Cannot show overlay because no target window is active. Please select a target window first.")
                )
                
                # Uncheck the overlay action to reflect state
                if hasattr(self, 'overlay_action'):
                    self.overlay_action.setChecked(False)
                return
                
            # Initialize overlay if it doesn't exist
            if not hasattr(self, 'overlay') or self.overlay is None:
                logger.warning("Overlay not initialized, creating it now")
                success = self._create_overlay()
                
                if not success or not hasattr(self, 'overlay') or self.overlay is None:
                    logger.error("Failed to create overlay - window service may not be initialized")
                    
                    # Show error message
                    QMessageBox.critical(
                        self,
                        tr("Overlay Creation Failed"),
                        tr("Failed to create the overlay window. Please try selecting the window again.")
                    )
                    
                    # Uncheck the overlay action to reflect state
                    if hasattr(self, 'overlay_action'):
                        self.overlay_action.setChecked(False)
                    return
                
                logger.info("Overlay created successfully for toggle")
            
            # Save the setting if we have a settings tab with a settings model
            try:
                if hasattr(self, 'settings_tab') and hasattr(self.settings_tab, 'settings_model'):
                    logger.debug(f"Saving overlay visibility setting: {checked}")
                    self.settings_tab.settings_model.set_setting('appearance', 'show_overlay', checked)
                    self.settings_tab.settings_model.save_settings()
            except Exception as e:
                logger.warning(f"Error saving overlay visibility setting: {e}")
            
            # Get the current window position to verify
            position = self.window_service.get_window_position()
            if position:
                logger.debug(f"Current window position: {position}")
            else:
                logger.warning("Could not get window position, overlay may not appear in the correct location")
            
            # Show or hide the overlay
            logger.debug(f"Calling show_overlay({checked}) on overlay instance")
            self.overlay.show_overlay(checked)
            
            # Make sure the toolbar button state matches
            if hasattr(self, 'overlay_action') and self.overlay_action.isChecked() != checked:
                logger.debug(f"Updating overlay action checked state to {checked}")
                self.overlay_action.setChecked(checked)
            
            # Verify the overlay visibility state
            if checked:
                # Give a short delay for the overlay to appear
                logger.debug("Setting timer to check overlay visibility")
                QTimer.singleShot(100, self._check_overlay_visibility)
                
                # Update debug overlay action to match overlay debug mode
                if hasattr(self, 'debug_overlay_action') and hasattr(self.overlay, 'debug_mode'):
                    self.debug_overlay_action.setChecked(self.overlay.debug_mode)
                    
            logger.info(f"Overlay visibility toggled to: {checked}")
            
            # If turning on the overlay, alert user about debug mode
            if checked and hasattr(self.overlay, 'debug_mode') and self.overlay.debug_mode:
                logger.info("Overlay is in debug mode")
                
                # Prompt the user to look for the red tinted overlay
                QTimer.singleShot(500, lambda: QMessageBox.information(
                    self,
                    tr("Overlay Debug Mode"),
                    tr("The overlay is now visible in debug mode. You should see a red-tinted overlay with debug information on top of the Total Battle window. If you don't see it, please check if the Total Battle window is visible and not minimized.")
                ))
                
        except Exception as e:
            logger.error(f"Error toggling overlay: {e}", exc_info=True)
            
            # Show error message
            QMessageBox.critical(
                self,
                tr("Overlay Error"),
                tr("An error occurred while toggling the overlay: {0}").format(str(e))
            )
            
            # Uncheck the overlay action to reflect state
            if hasattr(self, 'overlay_action'):
                self.overlay_action.setChecked(False)
    
    def _check_overlay_visibility(self):
        """Check if the overlay is visible as expected and try to fix if not."""
        if not hasattr(self, 'overlay') or self.overlay is None:
            return
            
        if self.overlay._visible and not self.overlay.isVisible():
            logger.warning("Overlay should be visible but isn't - attempting to fix")
            
            try:
                # Try to force it visible with explicit flags
                self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                                          Qt.WindowType.WindowStaysOnTopHint | 
                                          Qt.WindowType.Tool)
                self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                self.overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                
                # Update position
                position = self.window_service.get_window_position()
                if position:
                    x, y, width, height = position
                    self.overlay.setGeometry(x, y, width, height)
                
                # Show and raise
                self.overlay.show()
                self.overlay.raise_()
                
                logger.info("Fixed overlay visibility")
            except Exception as e:
                logger.error(f"Failed to fix overlay visibility: {e}")
    
    def _on_new(self):
        """Handle new action."""
        # This depends on what "new" means in your application
        # It could be a new configuration, a new automation sequence, etc.
        
        # For now, just show a message
        QMessageBox.information(
            self,
            "New",
            "New action not yet implemented."
        )
    
    def _on_open(self):
        """Handle open action."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Scout Files (*.scout);;All Files (*)"
        )
        
        if file_path:
            # Load file
            # TODO: Implement file loading
            
            # Show message
            QMessageBox.information(
                self,
                "Open",
                f"File opened: {file_path}"
            )
    
    def _on_save(self):
        """Handle save action."""
        # This depends on what you're saving
        # It could be the current configuration, the current automation sequence, etc.
        
        # For now, just show a message
        QMessageBox.information(
            self,
            "Save",
            "Save action not yet implemented."
        )
    
    def _on_save_as(self):
        """Handle save as action."""
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Scout Files (*.scout);;All Files (*)"
        )
        
        if file_path:
            # Save file
            # TODO: Implement file saving
            
            # Show message
            QMessageBox.information(
                self,
                "Save As",
                f"File saved: {file_path}"
            )
    
    def _on_preferences(self):
        """Handle preferences action."""
        # Switch to settings tab
        self.tab_widget.setCurrentWidget(self.settings_tab)
    
    def _on_refresh(self):
        """Handle refresh action."""
        # Refresh current tab
        current_tab = self.tab_widget.currentWidget()
        
        if hasattr(current_tab, 'refresh'):
            current_tab.refresh()
    
    def _on_capture_screenshot(self):
        """Handle capture screenshot action."""
        # Capture screenshot
        screenshot = self.window_service.capture_screenshot()
        
        if screenshot is not None:
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Screenshot",
                "",
                "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)"
            )
            
            if file_path:
                # Save screenshot
                import cv2
                cv2.imwrite(file_path, screenshot)
                
                # Show message
                QMessageBox.information(
                    self,
                    "Screenshot",
                    f"Screenshot saved to {file_path}"
                )
        else:
            # Show error message
            QMessageBox.warning(
                self,
                "Screenshot",
                "Failed to capture screenshot. No target window selected."
            )
    
    def _on_template_creator(self):
        """Handle template creator action."""
        # TODO: Implement template creator dialog
        
        # For now, just show a message
        QMessageBox.information(
            self,
            "Template Creator",
            "Template creator not yet implemented."
        )
    
    def _on_sequence_recorder(self):
        """Handle sequence recorder action."""
        # TODO: Implement sequence recorder dialog
        
        # For now, just show a message
        QMessageBox.information(
            self,
            "Sequence Recorder",
            "Sequence recorder not yet implemented."
        )
    
    def _on_documentation(self):
        """Handle documentation action."""
        # Show documentation dialog or open web browser
        QMessageBox.information(
            self,
            tr("Documentation"),
            tr("Documentation not yet implemented.")
        )
    
    def _on_about(self):
        """Handle about action."""
        # Show about dialog
        QMessageBox.about(
            self,
            tr("About Scout"),
            tr("Scout - Game Automation and Detection Tool\n\n"
               "Version: 1.0.0\n"
               "Copyright © 2025")
        )
    
    def _on_run(self):
        """Handle run action."""
        # Get current tab
        current_tab = self.tab_widget.currentWidget()
        
        # Run appropriate action based on current tab
        if current_tab == self.detection_tab:
            self.detection_tab.run_detection()
            self.control_panel.set_status("Detection running")
        elif current_tab == self.automation_tab:
            self.automation_tab.run_sequence()
            self.control_panel.set_status("Automation running")
        elif current_tab == self.game_tab:
            self.game_tab.update_state()
            self.control_panel.set_status("Game state updated")
    
    def _on_stop(self):
        """Handle stop action."""
        # Get current tab
        current_tab = self.tab_widget.currentWidget()
        
        # Stop appropriate action based on current tab
        if current_tab == self.detection_tab:
            self.detection_tab.stop_detection()
            self.control_panel.set_status("Detection stopped")
        elif current_tab == self.automation_tab:
            self.automation_tab.stop_sequence()
            self.control_panel.set_status("Automation stopped")
        elif current_tab == self.game_tab:
            # Not applicable
            pass
    
    def _on_pause(self):
        """Handle pause action."""
        # Get current tab
        current_tab = self.tab_widget.currentWidget()
        
        # Pause appropriate action based on current tab
        if current_tab == self.detection_tab:
            self.detection_tab.pause_detection()
            self.control_panel.set_status("Detection paused")
        elif current_tab == self.automation_tab:
            self.automation_tab.pause_sequence()
            self.control_panel.set_status("Automation paused")
        elif current_tab == self.game_tab:
            # Not applicable
            pass
    
    def _on_resume(self):
        """Handle resume action."""
        # Get current tab
        current_tab = self.tab_widget.currentWidget()
        
        # Resume appropriate action based on current tab
        if current_tab == self.detection_tab:
            self.detection_tab.resume_detection()
            self.control_panel.set_status("Detection resumed")
        elif current_tab == self.automation_tab:
            self.automation_tab.resume_sequence()
            self.control_panel.set_status("Automation resumed")
        elif current_tab == self.game_tab:
            # Not applicable
            pass
    
    def _on_check_for_updates(self):
        """Handle Check for Updates action."""
        logger.debug("Check for Updates action triggered")
        show_update_dialog(self)
    
    def _on_window_moved(self, x, y, width, height):
        """Handle window moved event."""
        # Update overlay position if needed
        if hasattr(self, 'overlay') and self.overlay is not None:
            self.overlay._update_position()
            
    def _on_window_state_changed(self, state):
        """
        Handle window state changed event.
        
        Args:
            state: The new window state ('normal', 'minimized', 'maximized', or 'unknown')
        """
        logger.debug(f"Window state changed to: {state}")
        
        # Update overlay if it exists and is visible
        if hasattr(self, 'overlay') and self.overlay is not None and self.overlay._visible:
            if state == 'minimized':
                # Hide overlay if window is minimized
                logger.info("Target window minimized, hiding overlay")
                self.overlay.hide()
            elif state in ['normal', 'maximized']:
                # Ensure overlay is visible and correctly positioned
                logger.debug("Target window state changed to normal/maximized, updating overlay")
                self.overlay._update_position()
                self.overlay.raise_()
                self.overlay.update()
            else:
                # Unknown state, force position update to be safe
                logger.warning(f"Unknown window state: {state}, forcing overlay position update")
                self.overlay._update_position()
    
    def _on_toggle_debug_overlay(self, checked: bool):
        """
        Toggle debug mode for overlay.
        
        Args:
            checked: Whether debug mode should be enabled
        """
        logger.info(f"Toggling overlay debug mode to: {checked}")
        
        # Ensure overlay exists
        if not hasattr(self, 'overlay') or self.overlay is None:
            logger.warning("Cannot toggle debug mode - overlay not initialized")
            if checked:
                QMessageBox.warning(
                    self,
                    tr("Overlay Not Initialized"),
                    tr("Cannot enable debug mode because the overlay is not initialized. Please select a target window first.")
                )
            self.debug_overlay_action.setChecked(False)
            return
        
        # Store debug mode
        self.overlay.debug_mode = checked
        
        # If debug mode enabled, make sure overlay is visible
        if checked and not self.overlay._visible:
            logger.info("Enabling overlay because debug mode was turned on")
            self.overlay_action.setChecked(True)
            self._on_toggle_overlay(True)
        
        # Force refresh of the overlay
        self.overlay.update()
        
        # Show message if debug mode enabled
        if checked:
            QMessageBox.information(
                self,
                tr("Debug Mode Enabled"),
                tr("Overlay debug mode is now ON. The overlay will be very visible with a red tint and debug information.")
            )
        
        logger.info(f"Overlay debug mode is now: {'ON' if checked else 'OFF'}")


def check_updates_if_needed(main_window, force_check=False, skip_check=False):
    """
    Check for updates in the background if needed.
    
    Args:
        main_window: The main window instance
        force_check: Whether to force checking for updates even if disabled in settings
        skip_check: Whether to skip checking for updates even if enabled in settings
    """
    if skip_check:
        logger.debug("Update check skipped (command-line override)")
        return
    
    # Get update settings
    update_settings = get_update_settings()
    
    # Check if updates should be checked on startup
    if force_check or update_settings.should_check_updates_on_startup():
        logger.info("Checking for updates in background")
        # Use a small delay to ensure the UI is fully loaded before checking
        QThread.msleep(1000)
        # Run check in a separate thread to avoid blocking the UI
        threading.Thread(
            target=check_for_updates_in_background,
            args=(main_window,),
            daemon=True
        ).start()
    else:
        logger.debug("Update check on startup is disabled")


def run_application(force_check=False, skip_check=False):
    """
    Run the application.
    
    This function:
    1. Creates the QApplication instance
    2. Initializes the language manager
    3. Creates and shows the main window
    4. Checks for updates if needed
    5. Enters the application event loop
    
    Args:
        force_check: Whether to force checking for updates even if disabled in settings
        skip_check: Whether to skip checking for updates even if enabled in settings
    
    Returns:
        Application exit code
    """
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Scout")
    app.setApplicationVersion("1.0.0")
    
    # Initialize language manager
    language_manager = get_language_manager()
    
    # Create main window
    main_window = MainWindow()
    main_window.show()
    
    # Check for updates if needed
    check_updates_if_needed(main_window, force_check, skip_check)
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run application
    run_application() 