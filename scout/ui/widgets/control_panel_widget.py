"""
Control Panel Widget

This module provides a flexible control panel widget that can be used throughout the application.
The control panel offers:
1. Main application controls for core application functions
2. Quick access toolbar for frequently used actions
3. Context-sensitive action panel that changes based on the current application state

The control panel is designed to be used as a dockable widget or embedded in various parts of the application.
"""

import logging
from typing import Dict, List, Optional, Any, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QToolBar, QSizePolicy, QFrame, QStackedWidget, QScrollArea,
    QGroupBox, QGridLayout, QToolButton, QButtonGroup, QRadioButton
)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot

# Import service interfaces
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.core.automation.automation_service_interface import AutomationServiceInterface
from scout.core.game.game_state_service_interface import GameStateServiceInterface
from scout.core.window.window_service_interface import WindowServiceInterface

# Import service locator
from scout.ui.main_window import ServiceLocator

# Set up logging
logger = logging.getLogger(__name__)


class ControlPanelWidget(QWidget):
    """
    A flexible control panel widget that provides context-sensitive controls.
    
    This widget offers three main components:
    1. Main application controls - Core functions like start/stop/pause
    2. Quick access toolbar - Frequently used actions
    3. Context panel - Context-sensitive controls that change based on application state
    
    Signals:
        action_triggered(str): Emitted when an action is triggered, with the action ID
    """
    
    # Signal emitted when an action is triggered
    action_triggered = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        Initialize the control panel widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Get services
        self.detection_service = ServiceLocator.get(DetectionServiceInterface)
        self.automation_service = ServiceLocator.get(AutomationServiceInterface)
        self.game_state_service = ServiceLocator.get(GameStateServiceInterface)
        self.window_service = ServiceLocator.get(WindowServiceInterface)
        
        # Track current context
        self.current_context = "default"
        
        # Track registered actions
        self.actions: Dict[str, QAction] = {}
        
        # Track context panels
        self.context_panels: Dict[str, QWidget] = {}
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main controls section
        self._create_main_controls(layout)
        
        # Create quick access toolbar
        self._create_quick_access_toolbar(layout)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Create context panel
        self._create_context_panel(layout)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    
    def _create_main_controls(self, layout):
        """
        Create the main controls section.
        
        Args:
            layout: Parent layout to add controls to
        """
        # Create frame for main controls
        main_controls_frame = QFrame()
        main_controls_frame.setFrameShape(QFrame.Shape.NoFrame)
        main_controls_layout = QHBoxLayout(main_controls_frame)
        main_controls_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create start button
        self.start_button = QPushButton("Start")
        self.start_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_button.setToolTip("Start the current operation")
        self.start_button.clicked.connect(lambda: self._on_action_triggered("start"))
        main_controls_layout.addWidget(self.start_button)
        
        # Create stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_button.setToolTip("Stop the current operation")
        self.stop_button.clicked.connect(lambda: self._on_action_triggered("stop"))
        main_controls_layout.addWidget(self.stop_button)
        
        # Create pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_button.setToolTip("Pause the current operation")
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(lambda checked: self._on_action_triggered("pause" if checked else "resume"))
        main_controls_layout.addWidget(self.pause_button)
        
        # Add spacer
        main_controls_layout.addStretch()
        
        # Create operation status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        main_controls_layout.addWidget(self.status_label)
        
        # Add to main layout
        layout.addWidget(main_controls_frame)
    
    def _create_quick_access_toolbar(self, layout):
        """
        Create the quick access toolbar.
        
        Args:
            layout: Parent layout to add toolbar to
        """
        # Create toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        
        # Add screenshot action
        screenshot_action = QAction(QIcon.fromTheme("camera-photo"), "Screenshot", self)
        screenshot_action.setToolTip("Capture a screenshot of the target window")
        screenshot_action.triggered.connect(lambda: self._on_action_triggered("screenshot"))
        toolbar.addAction(screenshot_action)
        self.actions["screenshot"] = screenshot_action
        
        # Add template detection action
        template_action = QAction(QIcon.fromTheme("edit-find"), "Template", self)
        template_action.setToolTip("Run template detection")
        template_action.triggered.connect(lambda: self._on_action_triggered("template_detection"))
        toolbar.addAction(template_action)
        self.actions["template_detection"] = template_action
        
        # Add OCR action
        ocr_action = QAction(QIcon.fromTheme("format-text-bold"), "OCR", self)
        ocr_action.setToolTip("Run OCR text recognition")
        ocr_action.triggered.connect(lambda: self._on_action_triggered("ocr_detection"))
        toolbar.addAction(ocr_action)
        self.actions["ocr_detection"] = ocr_action
        
        # Add separator
        toolbar.addSeparator()
        
        # Add overlay action
        overlay_action = QAction(QIcon.fromTheme("view-fullscreen"), "Overlay", self)
        overlay_action.setToolTip("Show/hide detection overlay")
        overlay_action.setCheckable(True)
        overlay_action.triggered.connect(lambda checked: self._on_action_triggered("toggle_overlay"))
        toolbar.addAction(overlay_action)
        self.actions["toggle_overlay"] = overlay_action
        
        # Add template editor action
        template_editor_action = QAction(QIcon.fromTheme("document-edit"), "Templates", self)
        template_editor_action.setToolTip("Open template editor")
        template_editor_action.triggered.connect(lambda: self._on_action_triggered("template_editor"))
        toolbar.addAction(template_editor_action)
        self.actions["template_editor"] = template_editor_action
        
        # Add sequence editor action
        sequence_editor_action = QAction(QIcon.fromTheme("view-list-details"), "Sequences", self)
        sequence_editor_action.setToolTip("Open sequence editor")
        sequence_editor_action.triggered.connect(lambda: self._on_action_triggered("sequence_editor"))
        toolbar.addAction(sequence_editor_action)
        self.actions["sequence_editor"] = sequence_editor_action
        
        # Add to main layout
        layout.addWidget(toolbar)
    
    def _create_context_panel(self, layout):
        """
        Create the context-sensitive panel.
        
        Args:
            layout: Parent layout to add panel to
        """
        # Create stacked widget for different context panels
        self.context_stack = QStackedWidget()
        
        # Create default context panel
        default_panel = self._create_default_context_panel()
        self.context_stack.addWidget(default_panel)
        self.context_panels["default"] = default_panel
        
        # Create detection context panel
        detection_panel = self._create_detection_context_panel()
        self.context_stack.addWidget(detection_panel)
        self.context_panels["detection"] = detection_panel
        
        # Create automation context panel
        automation_panel = self._create_automation_context_panel()
        self.context_stack.addWidget(automation_panel)
        self.context_panels["automation"] = automation_panel
        
        # Create game state context panel
        game_state_panel = self._create_game_state_context_panel()
        self.context_stack.addWidget(game_state_panel)
        self.context_panels["game_state"] = game_state_panel
        
        # Set default panel
        self.set_context("default")
        
        # Add to main layout
        layout.addWidget(self.context_stack)
    
    def _create_default_context_panel(self):
        """
        Create the default context panel.
        
        Returns:
            QWidget: The default context panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Add a label
        label = QLabel("Select an operation from the tabs above")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Add common actions
        actions_group = QGroupBox("Common Actions")
        actions_layout = QGridLayout()
        
        # Capture window button
        capture_window_btn = QPushButton("Capture Window")
        capture_window_btn.clicked.connect(lambda: self._on_action_triggered("capture_window"))
        actions_layout.addWidget(capture_window_btn, 0, 0)
        
        # Create template button
        create_template_btn = QPushButton("Create Template")
        create_template_btn.clicked.connect(lambda: self._on_action_triggered("create_template"))
        actions_layout.addWidget(create_template_btn, 0, 1)
        
        # Record sequence button
        record_sequence_btn = QPushButton("Record Sequence")
        record_sequence_btn.clicked.connect(lambda: self._on_action_triggered("record_sequence"))
        actions_layout.addWidget(record_sequence_btn, 1, 0)
        
        # Edit settings button
        edit_settings_btn = QPushButton("Edit Settings")
        edit_settings_btn.clicked.connect(lambda: self._on_action_triggered("edit_settings"))
        actions_layout.addWidget(edit_settings_btn, 1, 1)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Add stretch
        layout.addStretch()
        
        return panel
    
    def _create_detection_context_panel(self):
        """
        Create the detection context panel.
        
        Returns:
            QWidget: The detection context panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Add detection settings group
        settings_group = QGroupBox("Detection Settings")
        settings_layout = QGridLayout()
        
        # Detection type radio buttons
        type_label = QLabel("Detection Type:")
        settings_layout.addWidget(type_label, 0, 0)
        
        # Button group for detection types
        type_group = QButtonGroup(panel)
        
        template_radio = QRadioButton("Template")
        template_radio.setChecked(True)
        template_radio.toggled.connect(lambda checked: self._on_action_triggered("set_detection_type", {"type": "template"}) if checked else None)
        type_group.addButton(template_radio)
        settings_layout.addWidget(template_radio, 0, 1)
        
        ocr_radio = QRadioButton("OCR")
        ocr_radio.toggled.connect(lambda checked: self._on_action_triggered("set_detection_type", {"type": "ocr"}) if checked else None)
        type_group.addButton(ocr_radio)
        settings_layout.addWidget(ocr_radio, 0, 2)
        
        yolo_radio = QRadioButton("YOLO")
        yolo_radio.toggled.connect(lambda checked: self._on_action_triggered("set_detection_type", {"type": "yolo"}) if checked else None)
        type_group.addButton(yolo_radio)
        settings_layout.addWidget(yolo_radio, 0, 3)
        
        # Add region selection button
        region_btn = QPushButton("Select Region")
        region_btn.clicked.connect(lambda: self._on_action_triggered("select_detection_region"))
        settings_layout.addWidget(region_btn, 1, 0, 1, 2)
        
        # Add template selection button
        template_btn = QPushButton("Select Templates")
        template_btn.clicked.connect(lambda: self._on_action_triggered("select_templates"))
        settings_layout.addWidget(template_btn, 1, 2, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Add detection actions group
        actions_group = QGroupBox("Detection Actions")
        actions_layout = QGridLayout()
        
        # Run once button
        run_once_btn = QPushButton("Run Once")
        run_once_btn.clicked.connect(lambda: self._on_action_triggered("run_detection_once"))
        actions_layout.addWidget(run_once_btn, 0, 0)
        
        # Run continuous button
        run_continuous_btn = QPushButton("Run Continuous")
        run_continuous_btn.setCheckable(True)
        run_continuous_btn.toggled.connect(lambda checked: self._on_action_triggered("run_detection_continuous", {"enabled": checked}))
        actions_layout.addWidget(run_continuous_btn, 0, 1)
        
        # Save results button
        save_results_btn = QPushButton("Save Results")
        save_results_btn.clicked.connect(lambda: self._on_action_triggered("save_detection_results"))
        actions_layout.addWidget(save_results_btn, 1, 0)
        
        # Clear results button
        clear_results_btn = QPushButton("Clear Results")
        clear_results_btn.clicked.connect(lambda: self._on_action_triggered("clear_detection_results"))
        actions_layout.addWidget(clear_results_btn, 1, 1)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Add stretch
        layout.addStretch()
        
        return panel
    
    def _create_automation_context_panel(self):
        """
        Create the automation context panel.
        
        Returns:
            QWidget: The automation context panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Add sequence selection group
        sequence_group = QGroupBox("Sequence Selection")
        sequence_layout = QGridLayout()
        
        # Load sequence button
        load_sequence_btn = QPushButton("Load Sequence")
        load_sequence_btn.clicked.connect(lambda: self._on_action_triggered("load_sequence"))
        sequence_layout.addWidget(load_sequence_btn, 0, 0)
        
        # Create new sequence button
        new_sequence_btn = QPushButton("New Sequence")
        new_sequence_btn.clicked.connect(lambda: self._on_action_triggered("new_sequence"))
        sequence_layout.addWidget(new_sequence_btn, 0, 1)
        
        # Edit sequence button
        edit_sequence_btn = QPushButton("Edit Sequence")
        edit_sequence_btn.clicked.connect(lambda: self._on_action_triggered("edit_sequence"))
        sequence_layout.addWidget(edit_sequence_btn, 1, 0)
        
        # Delete sequence button
        delete_sequence_btn = QPushButton("Delete Sequence")
        delete_sequence_btn.clicked.connect(lambda: self._on_action_triggered("delete_sequence"))
        sequence_layout.addWidget(delete_sequence_btn, 1, 1)
        
        sequence_group.setLayout(sequence_layout)
        layout.addWidget(sequence_group)
        
        # Add execution control group
        execution_group = QGroupBox("Execution Control")
        execution_layout = QGridLayout()
        
        # Run sequence button
        run_sequence_btn = QPushButton("Run Sequence")
        run_sequence_btn.clicked.connect(lambda: self._on_action_triggered("run_sequence"))
        execution_layout.addWidget(run_sequence_btn, 0, 0)
        
        # Run with simulation button
        simulation_btn = QPushButton("Run Simulation")
        simulation_btn.clicked.connect(lambda: self._on_action_triggered("run_sequence_simulation"))
        execution_layout.addWidget(simulation_btn, 0, 1)
        
        # Record sequence button
        record_btn = QPushButton("Record Sequence")
        record_btn.clicked.connect(lambda: self._on_action_triggered("record_sequence"))
        execution_layout.addWidget(record_btn, 1, 0)
        
        # Stop button
        stop_btn = QPushButton("Stop Execution")
        stop_btn.clicked.connect(lambda: self._on_action_triggered("stop_sequence"))
        execution_layout.addWidget(stop_btn, 1, 1)
        
        execution_group.setLayout(execution_layout)
        layout.addWidget(execution_group)
        
        # Add stretch
        layout.addStretch()
        
        return panel
    
    def _create_game_state_context_panel(self):
        """
        Create the game state context panel.
        
        Returns:
            QWidget: The game state context panel
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Add state tracking group
        tracking_group = QGroupBox("State Tracking")
        tracking_layout = QGridLayout()
        
        # Update state button
        update_state_btn = QPushButton("Update State")
        update_state_btn.clicked.connect(lambda: self._on_action_triggered("update_game_state"))
        tracking_layout.addWidget(update_state_btn, 0, 0)
        
        # Reset state button
        reset_state_btn = QPushButton("Reset State")
        reset_state_btn.clicked.connect(lambda: self._on_action_triggered("reset_game_state"))
        tracking_layout.addWidget(reset_state_btn, 0, 1)
        
        # Import state button
        import_state_btn = QPushButton("Import State")
        import_state_btn.clicked.connect(lambda: self._on_action_triggered("import_game_state"))
        tracking_layout.addWidget(import_state_btn, 1, 0)
        
        # Export state button
        export_state_btn = QPushButton("Export State")
        export_state_btn.clicked.connect(lambda: self._on_action_triggered("export_game_state"))
        tracking_layout.addWidget(export_state_btn, 1, 1)
        
        tracking_group.setLayout(tracking_layout)
        layout.addWidget(tracking_group)
        
        # Add analysis group
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QGridLayout()
        
        # Resource analysis button
        resource_btn = QPushButton("Resource Analysis")
        resource_btn.clicked.connect(lambda: self._on_action_triggered("analyze_resources"))
        analysis_layout.addWidget(resource_btn, 0, 0)
        
        # Building analysis button
        building_btn = QPushButton("Building Analysis")
        building_btn.clicked.connect(lambda: self._on_action_triggered("analyze_buildings"))
        analysis_layout.addWidget(building_btn, 0, 1)
        
        # Map analysis button
        map_btn = QPushButton("Map Analysis")
        map_btn.clicked.connect(lambda: self._on_action_triggered("analyze_map"))
        analysis_layout.addWidget(map_btn, 1, 0)
        
        # Army analysis button
        army_btn = QPushButton("Army Analysis")
        army_btn.clicked.connect(lambda: self._on_action_triggered("analyze_army"))
        analysis_layout.addWidget(army_btn, 1, 1)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        # Add stretch
        layout.addStretch()
        
        return panel
    
    @pyqtSlot(str)
    def set_context(self, context: str):
        """
        Set the current context and show the appropriate panel.
        
        Args:
            context: Context identifier
        """
        if context in self.context_panels:
            self.current_context = context
            self.context_stack.setCurrentWidget(self.context_panels[context])
            logger.debug(f"Set control panel context to: {context}")
        else:
            logger.warning(f"Unknown context: {context}")
    
    @pyqtSlot(str)
    def set_status(self, status: str):
        """
        Update the status label.
        
        Args:
            status: Status text
        """
        self.status_label.setText(status)
    
    @pyqtSlot(str, bool)
    def set_action_enabled(self, action_id: str, enabled: bool):
        """
        Enable or disable an action.
        
        Args:
            action_id: Action identifier
            enabled: Whether the action should be enabled
        """
        if action_id in self.actions:
            self.actions[action_id].setEnabled(enabled)
        else:
            logger.warning(f"Unknown action: {action_id}")
    
    @pyqtSlot(str, bool)
    def set_action_checked(self, action_id: str, checked: bool):
        """
        Set the checked state of an action.
        
        Args:
            action_id: Action identifier
            checked: Whether the action should be checked
        """
        if action_id in self.actions:
            action = self.actions[action_id]
            if action.isCheckable():
                action.setChecked(checked)
        else:
            logger.warning(f"Unknown action: {action_id}")
    
    def register_action_handler(self, action_id: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Register a handler for an action.
        
        Args:
            action_id: Action identifier
            handler: Handler function
        """
        self.action_triggered.connect(
            lambda action_id_param, params=None, handler=handler, action_id_check=action_id:
            handler(params) if action_id_param == action_id_check else None
        )
    
    def _on_action_triggered(self, action_id: str, params: Optional[Dict[str, Any]] = None):
        """
        Handle action triggers from UI components.
        
        Args:
            action_id: Action identifier
            params: Optional parameters for the action
        """
        logger.debug(f"Action triggered: {action_id}, params: {params}")
        self.action_triggered.emit(action_id) 