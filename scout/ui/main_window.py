"""
Main Window

This module provides the main application window for the Scout application.
It integrates all UI components and connects to the core services.
"""

import sys
import os
import logging
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTabWidget, QToolBar, QStatusBar, 
    QMenuBar, QMenu, QMessageBox, QDialog, QFileDialog, QAction,
    QDockWidget, QSplitter
)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QKeySequence, QCloseEvent
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer, pyqtSignal, QEvent, QThread

# Import service interfaces
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.core.game.game_state_service_interface import GameStateServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface

# Import service implementations (or mock implementations for now)
from scout.core.detection.detection_service import DetectionService
from scout.core.automation.automation_service import AutomationService
from scout.core.game.game_state_service import GameStateService
from scout.core.window.window_service import WindowService

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


class ServiceLocator:
    """
    Service locator for managing application services.
    
    This class provides access to core services needed by the UI components,
    ensuring type-safe access and proper initialization/shutdown.
    """
    
    _services = {}  # Static dictionary of services
    
    @classmethod
    def register(cls, interface_class, implementation):
        """
        Register a service implementation for a given interface.
        
        Args:
            interface_class: Interface class that the implementation implements
            implementation: Service implementation instance
        """
        cls._services[interface_class] = implementation
        logger.debug(f"Registered service: {interface_class.__name__}")
    
    @classmethod
    def get(cls, interface_class):
        """
        Get a service by its interface.
        
        Args:
            interface_class: Interface class to look up
            
        Returns:
            Implementation instance or None if not found
        """
        if interface_class in cls._services:
            return cls._services[interface_class]
        
        logger.error(f"Service not found: {interface_class.__name__}")
        return None
    
    @classmethod
    def shutdown(cls):
        """Shutdown all registered services."""
        for service_class, service in cls._services.items():
            try:
                if hasattr(service, 'shutdown'):
                    service.shutdown()
                    logger.debug(f"Shut down service: {service_class.__name__}")
            except Exception as e:
                logger.error(f"Error shutting down service {service_class.__name__}: {str(e)}")
        
        cls._services.clear()


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
        
        # Configure window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        
        # Create update timer
        self._create_update_timer()
        
        logger.info("Overlay view initialized")
    
    def _create_update_timer(self):
        """Create timer for updating overlay position and content."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_position)
        self.update_timer.start(100)  # 10 fps
    
    def _update_position(self):
        """Update overlay position to match target window."""
        if self._visible:
            # Get target window position and size
            target_rect = self.window_service.get_window_rect()
            
            if target_rect != self._target_window_rect:
                # Update overlay position and size
                self.setGeometry(target_rect)
                self._target_window_rect = target_rect
                self.update()
    
    def set_results(self, results: List[Dict[str, Any]]):
        """
        Set detection results to display.
        
        Args:
            results: List of detection result dictionaries
        """
        self._results = results
        self.update()
    
    def show_overlay(self, show: bool):
        """
        Show or hide the overlay.
        
        Args:
            show: Whether to show the overlay
        """
        self._visible = show
        
        if show:
            # Update position before showing
            self._update_position()
            self.show()
        else:
            self.hide()
    
    def paintEvent(self, event):
        """
        Handle paint event.
        
        Args:
            event: Paint event
        """
        if not self._visible or not self._results:
            return
        
        # Create painter
        painter = self.window_service.create_overlay_painter(self)
        
        # Draw results
        self.window_service.draw_detection_results(painter, self._results)


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
        # Create service instances
        window_service = WindowService()
        detection_service = DetectionService(window_service)
        automation_service = AutomationService(window_service)
        game_state_service = GameStateService()
        
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
            window_info = self.window_service.get_window_info()
            self._on_window_selected(window_info)
        else:
            self._on_window_lost()
            
            # Show error message
            QMessageBox.warning(
                self,
                "Window Not Found",
                "Could not find the game window. Please make sure the game is running."
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
        self.detection_tab = DetectionTab(self.detection_service, self.window_service)
        self.tab_widget.addTab(self.detection_tab, tr("Detection"))
        
        # Create automation tab
        self.automation_tab = AutomationTab(
            self.automation_service, self.detection_service, self.window_service)
        self.tab_widget.addTab(self.automation_tab, tr("Automation"))
        
        # Create game state tab
        self.game_tab = GameTab(self.game_state_service, self.detection_service)
        self.tab_widget.addTab(self.game_tab, tr("Game State"))
        
        # Create settings tab
        self.settings_tab = SettingsTab()
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
        """Create the overlay window."""
        self.overlay = OverlayView(self.window_service)
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Connect detection tab signals
        self.detection_tab.detection_results_ready.connect(self._on_detection_results)
        
        # Connect settings tab signals
        self.settings_tab.settings_changed.connect(self._on_settings_changed)
        
        # Connect window service signals
        self.window_service.window_selected.connect(self._on_window_selected)
        self.window_service.window_lost.connect(self._on_window_lost)
    
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
        # Save settings
        self._save_settings()
        
        # Hide overlay
        if self.overlay:
            self.overlay.hide()
        
        # Shut down services
        ServiceLocator.shutdown()
        
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
        # Update status bar
        window_title = window_info.get("title", "Unknown")
        self.window_status_label.setText(f"Target: {window_title}")
        
        # Enable actions that require a target window
        self.overlay_action.setEnabled(True)
    
    def _on_window_lost(self):
        """Handle window loss event."""
        # Update status bar
        self.window_status_label.setText("No target window")
        
        # Disable overlay
        self.overlay_action.setChecked(False)
        self._on_toggle_overlay(False)
        
        # Disable actions that require a target window
        self.overlay_action.setEnabled(False)
    
    def _on_toggle_overlay(self, checked: bool):
        """
        Handle overlay toggle.
        
        Args:
            checked: Whether the overlay should be shown
        """
        if self.overlay:
            self.overlay.show_overlay(checked)
    
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
               "Version: 0.1.0\n"
               "Copyright © 2023")
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