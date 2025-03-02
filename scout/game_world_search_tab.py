"""
Game World Search Tab

This module provides the main tab for game world search functionality.
It integrates:
- Direction-based movement
- Grid search pattern based on drag movements
- Game world coordinate visualization
- Results management
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import json
import time
import cv2
import win32api
import win32con
import win32gui
from ctypes import windll, wintypes
import ctypes

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QTabWidget, QSplitter, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QTextEdit, QProgressBar
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QObject, QEvent, QAbstractNativeEventFilter,
    QThread, pyqtSlot
)
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent
from PyQt6.QtWidgets import QApplication

from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_coordinator import GameWorldCoordinator
from scout.game_world_search import GameWorldSearch, SearchResult
from scout.game_world_direction import GameWorldDirection
from scout.config_manager import ConfigManager
from scout.game_world_position import GameWorldPosition

from scout.gui.direction_widget import DirectionWidget
from scout.gui.search_grid_widget import SearchGridWidget
from scout.gui.game_world_search_results import SearchResultsWidget
from scout.gui.game_world_search_preview import SearchPreviewWidget
from scout.gui.game_world_grid import GameWorldGrid

logger = logging.getLogger(__name__)

class SearchWorker(QObject):
    """Worker class that runs the search process in a separate thread."""
    
    # Signals for communication with main thread
    progress = pyqtSignal(int, int)  # positions_checked, total_cells
    position_updated = pyqtSignal(tuple, object)  # current_pos, game_pos
    matches_found = pyqtSignal(tuple, list)  # current_pos, matches
    search_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    screenshot_ready = pyqtSignal(object)  # screenshot data
    
    def __init__(
        self,
        game_search: GameWorldSearch,
        window_manager: WindowManager,
        text_ocr: TextOCR,
        game_coordinator: GameWorldCoordinator
    ):
        """Initialize the search worker."""
        super().__init__()
        self.game_search = game_search
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_coordinator = game_coordinator
        self.stop_requested = False

    def run_search(self):
        """Run the search process in the worker thread."""
        try:
            # Start OCR for coordinate tracking
            self.text_ocr._cancellation_requested = False
            self.text_ocr.start()

            # Start the actual search
            self.game_search.start()

            # Process search steps
            while not self.stop_requested and self.game_search.is_searching:
                # Get current position and game position
                current_pos = self.game_search.current_position
                game_pos = self.game_search.get_game_position(current_pos[0], current_pos[1])

                # Update progress
                self.progress.emit(self.game_search.positions_checked, self.game_search.total_cells)

                # Update position
                if game_pos:
                    self.position_updated.emit(current_pos, game_pos)

                # Check for matches
                if self.game_search.matches:
                    self.matches_found.emit(current_pos, self.game_search.matches)

                # Take screenshot for preview
                screenshot = self.window_manager.capture_screenshot()
                if screenshot is not None:
                    self.screenshot_ready.emit(screenshot)

                # Process a single search step
                self.game_search._search_at_position(game_pos)

                # Small delay to prevent CPU overload
                time.sleep(0.1)

            # Signal completion
            self.search_complete.emit()

        except Exception as e:
            logger.error(f"Error in search worker: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            # Stop OCR
            self.text_ocr._cancellation_requested = True
            self.text_ocr.stop()

class GameWorldSearchTab(QWidget):
    """
    Main tab for game world search functionality.
    
    This tab integrates:
    - Direction-based movement
    - Grid search pattern based on drag movements
    - Game world coordinate visualization
    - Results management
    """
    
    # View area ratio (width:height)
    VIEW_RATIO = 2.0
    
    # Overlap percentage between moves (to ensure we don't miss anything)
    OVERLAP_PERCENT = 20
    
    # World size (999x999)
    WORLD_SIZE = 999
    
    # Add constants for hotkeys
    STOP_VKEY = win32con.VK_ESCAPE  # Use Escape key
    ALT_STOP_VKEY = ord('Q')        # Use Q key as alternative
    
    def __init__(
        self,
        window_manager: WindowManager,
        template_matcher: TemplateMatcher,
        text_ocr: TextOCR,
        game_actions: GameActions,
        config_manager: ConfigManager,
        game_state=None
    ):
        """
        Initialize the game world search tab.
        
        Args:
            window_manager: The window manager instance
            template_matcher: The template matcher instance
            text_ocr: The text OCR instance
            game_actions: The game actions instance
            config_manager: The configuration manager instance
            game_state: Optional GameState instance for coordinate tracking
        """
        # Initialize QWidget
        super().__init__()
        
        # Initialize state variables for key checking
        self.last_key_check_time = time.time()
        self.key_check_interval = 0.05  # Check every 50ms for more responsiveness
        self.stop_requested = False
        
        # Store components
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.config_manager = config_manager
        self.game_state = game_state
        
        # Create key check timer with higher frequency
        self.key_check_timer = QTimer()
        self.key_check_timer.timeout.connect(self._check_stop_keys)
        self.key_check_timer.setInterval(50)  # Check every 50ms
        
        # Create direction system first
        self.direction_system = GameWorldDirection(
            window_manager=window_manager,
            text_ocr=text_ocr,
            game_actions=game_actions,
            config_manager=config_manager
        )
        
        # Create game world coordinator and set direction system
        self.game_coordinator = GameWorldCoordinator(window_manager, text_ocr, game_state, game_actions)
        self.game_coordinator.direction_system = self.direction_system
        
        # Create game world search
        self.game_search = GameWorldSearch(
            window_manager,
            template_matcher,
            text_ocr,
            game_actions,
            self.game_coordinator,
            game_state
        )
        
        # Create UI
        self._create_ui()
        
        # Initialize state
        self.is_searching = False
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self._update_search_status)
        
        # Load settings
        self._load_settings()
        
        # Calibration state tracking
        self.last_calibration_state = {
            'position': None,
            'drag_distances': (0, 0)
        }
        
        # Initialize update timer but don't start it
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._check_calibration)
        self.is_calibration_check_active = False
        
        # Connect direction widget to grid
        self.direction_widget.direction_manager = self.direction_system
        
        # Initialize grid with default size and empty state
        self._initialize_grid()
        
        # Update drag info label
        self._update_drag_info()
        
        # Enable key events for the whole tab
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Store last screenshot for preview
        self.last_screenshot = None
        
        # Ensure OCR is stopped initially
        self.text_ocr._cancellation_requested = True
        self.text_ocr.stop()
        
    def __del__(self):
        """Clean up registered hotkeys."""
        try:
            win32api.UnregisterHotKey(None, 1)  # Unregister Escape
            win32api.UnregisterHotKey(None, 2)  # Unregister Q
        except:
            pass
            
    def _load_settings(self):
        """Load search settings from config."""
        settings = self.config_manager.get_search_settings()
        
        # Update UI with loaded settings
        self.use_all_templates_check.setChecked(settings['use_all_templates'])
        self.confidence_spin.setValue(settings['min_confidence'])
        self.save_screenshots_check.setChecked(settings['save_screenshots'])
        
        # Update template selection based on use_all_templates setting
        if settings['use_all_templates']:
            self.template_list.selectAll()
            
    def _save_settings(self):
        """Save search settings to config."""
        settings = {
            'use_all_templates': self.use_all_templates_check.isChecked(),
            'min_confidence': self.confidence_spin.value(),
            'save_screenshots': self.save_screenshots_check.isChecked()
        }
        self.config_manager.update_search_settings(settings)
        
    def _on_use_all_templates_changed(self, state):
        """Handle changes to the 'Use All Templates' checkbox."""
        if state == Qt.CheckState.Checked.value:
            self.template_list.selectAll()
        else:
            self.template_list.clearSelection()
            
        # Save settings when changed
        self._save_settings()
        
    def _on_confidence_changed(self, value):
        """Handle changes to the confidence spinbox."""
        self._save_settings()
        
    def _on_save_screenshots_changed(self, state):
        """Handle changes to the save screenshots checkbox."""
        self._save_settings()
        
    def _create_ui(self):
        """Create the tab UI."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tab widget for Search and Results
        tab_widget = QTabWidget()
        
        # Search tab
        search_tab = QWidget()
        search_layout = QHBoxLayout()
        search_tab.setLayout(search_layout)
        
        # Left side - Direction and settings
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # Direction widget
        self.direction_widget = DirectionWidget(
            window_manager=self.window_manager,
            text_ocr=self.text_ocr,
            game_actions=self.game_actions,
            config_manager=self.config_manager,
            parent=left_widget  # Pass the parent widget
        )
        left_layout.addWidget(self.direction_widget)
        
        # Search settings
        settings_group = QGroupBox("Search Settings")
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)
        
        # Add ratio info label
        ratio_label = QLabel(f"View area has {self.VIEW_RATIO}:1 ratio (width:height)\n"
                           f"with {self.OVERLAP_PERCENT}% overlap between moves")
        ratio_label.setWordWrap(True)
        settings_layout.addRow("", ratio_label)
        
        # Use all templates checkbox
        self.use_all_templates_check = QCheckBox("Use All Templates")
        self.use_all_templates_check.setChecked(True)  # Default to checked
        self.use_all_templates_check.stateChanged.connect(self._on_use_all_templates_changed)
        settings_layout.addRow("", self.use_all_templates_check)
        
        # Template selection
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        settings_layout.addRow("Templates:", self.template_list)
        
        # Min confidence
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.valueChanged.connect(self._on_confidence_changed)
        settings_layout.addRow("Min Confidence:", self.confidence_spin)
        
        # Save screenshots
        self.save_screenshots_check = QCheckBox("Save Screenshots")
        self.save_screenshots_check.stateChanged.connect(self._on_save_screenshots_changed)
        settings_layout.addRow("", self.save_screenshots_check)
        
        left_layout.addWidget(settings_group)
        
        # Search controls
        controls_layout = QHBoxLayout()
        self.start_search_btn = QPushButton("Start Search")
        self.start_search_btn.clicked.connect(self._start_search)
        self.stop_search_btn = QPushButton("Stop Search")
        self.stop_search_btn.clicked.connect(self._stop_search)
        self.stop_search_btn.setEnabled(False)
        controls_layout.addWidget(self.start_search_btn)
        controls_layout.addWidget(self.stop_search_btn)
        left_layout.addLayout(controls_layout)
        
        # Add stretch at bottom
        left_layout.addStretch()
        
        # Right side - Grid and preview
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # Create splitter for grid and preview
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Grid visualization
        grid_container = QWidget()
        grid_layout = QVBoxLayout()
        grid_container.setLayout(grid_layout)
        
        self.grid_widget = GameWorldGrid()
        grid_layout.addWidget(self.grid_widget)
        
        # Add status label for grid
        self.grid_status_label = QLabel()
        self.grid_status_label.setWordWrap(True)
        grid_layout.addWidget(self.grid_status_label)
        
        # Add info label for drag distances
        self.drag_info_label = QLabel()
        self.drag_info_label.setWordWrap(True)
        grid_layout.addWidget(self.drag_info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        grid_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(grid_container)
        
        # Preview widget
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_container.setLayout(preview_layout)
        
        preview_label = QLabel("Live Preview")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_label)
        
        self.preview_widget = SearchPreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        
        splitter.addWidget(preview_container)
        
        # Set initial sizes (60% grid, 40% preview)
        splitter.setSizes([600, 400])
        
        right_layout.addWidget(splitter)
        
        # Add widgets to search layout
        search_layout.addWidget(left_widget, stretch=1)
        search_layout.addWidget(right_widget, stretch=2)
        
        # Results tab
        results_tab = QWidget()
        results_layout = QVBoxLayout()
        results_tab.setLayout(results_layout)
        
        # Results list and preview
        results_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Results list
        self.results_widget = SearchResultsWidget()
        results_splitter.addWidget(self.results_widget)
        
        # Preview
        self.results_preview_widget = SearchPreviewWidget()
        results_splitter.addWidget(self.results_preview_widget)
        
        results_layout.addWidget(results_splitter)
        
        # Add tabs
        tab_widget.addTab(search_tab, "Search")
        tab_widget.addTab(results_tab, "Results")
        
        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)
        
        # Load templates
        self._load_templates()
        
    def _load_templates(self):
        """Load available templates into the list."""
        self.template_list.clear()
        for name in sorted(self.template_matcher.templates.keys()):
            self.template_list.addItem(name)
        
        # Select all templates if the checkbox is checked
        if self.use_all_templates_check.isChecked():
            self.template_list.selectAll()
            
    def _initialize_grid(self) -> None:
        """Initialize grid with default size and empty state."""
        # Set initial grid size (can be adjusted based on screen size)
        initial_grid_size = (10, 5)  # Default 10x5 grid
        
        # Get drag distances from direction system if available
        drag_distances = (0, 0)
        if self.direction_system:
            drag_distances = self.direction_system.get_drag_distances()
            if not all(drag_distances):
                drag_distances = (100, 50)  # Default distances if not calibrated
        
        # Create empty game position for initial state
        empty_pos = GameWorldPosition(k=0, x=0, y=0)
        
        # Initialize grid with these parameters
        self.grid_widget.set_grid_parameters(
            grid_size=initial_grid_size,
            start_pos=empty_pos,
            drag_distances=drag_distances,
            current_cell=(0, 0)
        )
        
        # Connect grid status signal
        self.grid_widget.status_updated.connect(self._on_grid_status_updated)
        
        # Connect grid to game state
        if self.game_state:
            self.grid_widget.set_game_state(self.game_state)
        
        # Update grid status
        self.grid_widget._update_status()
        
        # Force initial update and repaint
        self.grid_widget.update()
        self.grid_widget.repaint()
        
    def _on_grid_status_updated(self, status: str) -> None:
        """Handle grid status updates."""
        try:
            # Update status label
            self.grid_status_label.setText(status)
            
            # Force grid to repaint
            self.grid_widget.update()
            
        except Exception as e:
            logger.error(f"Error updating grid status: {e}")
            
    def _update_grid_calibration(self):
        """Update grid with current calibration data."""
        try:
            if not self.direction_system or not self.game_state:
                logger.warning("Missing direction system or game state for grid calibration")
                return
                
            # Get current position from GameState
            coords = self.game_state.get_coordinates()
            if not coords:
                logger.warning("No current position available for grid")
                return
                
            # Convert coordinates to GameWorldPosition
            current_pos = GameWorldPosition(
                k=coords.k,
                x=coords.x,
                y=coords.y
            )
            logger.debug(f"Current game position for calibration: {current_pos}")
                
            # Get drag distances
            drag_distances = self.direction_system.get_drag_distances()
            if not all(drag_distances):
                logger.warning("Invalid drag distances")
                return
                
            logger.debug(f"Current drag distances: {drag_distances}")
                
            # Calculate grid size
            east_distance, south_distance = drag_distances
            
            grid_width = (self.WORLD_SIZE + 1) // east_distance
            if (self.WORLD_SIZE + 1) % east_distance:
                grid_width += 1
                
            grid_height = (self.WORLD_SIZE + 1) // south_distance
            if (self.WORLD_SIZE + 1) % south_distance:
                grid_height += 1
                
            # Calculate current cell based on position
            current_cell_x = current_pos.x // east_distance
            current_cell_y = current_pos.y // south_distance
            
            logger.info(f"Updating grid calibration: size={grid_width}x{grid_height}, "
                       f"current_pos={current_pos}, current_cell=({current_cell_x}, {current_cell_y})")
            
            # Update grid widget
            self.grid_widget.set_grid_parameters(
                grid_size=(grid_width, grid_height),
                start_pos=current_pos,
                drag_distances=drag_distances,
                current_cell=(current_cell_x, current_cell_y)
            )
            
            # Force immediate update
            self.grid_widget.update()
            
            # Force repaint
            self.grid_widget.repaint()
            
            # Update drag info label
            self._update_drag_info()
            
            logger.debug("Grid calibration update completed")
            
        except Exception as e:
            logger.error(f"Error updating grid calibration: {e}", exc_info=True)

    def _start_search(self):
        """Start the search process."""
        try:
            # First ensure OCR is stopped
            logger.info("Ensuring OCR is stopped...")
            self.text_ocr._cancellation_requested = True
            self.text_ocr.stop()
            time.sleep(0.5)  # Give it time to fully stop

            # Reset stop flags
            self.stop_requested = False
            self.game_search.stop_requested = False

            # Start key check timer with high frequency
            self.key_check_timer.start()

            # Take a screenshot of the OCR region
            if not self.text_ocr.region:
                logger.error("No OCR region set")
                QMessageBox.warning(self, "Error", "No OCR region set. Please set an OCR region in the Overlay tab.")
                return

            # Capture and process the region directly
            screenshot = self.window_manager.capture_region(self.text_ocr.region)
            if screenshot is None:
                logger.error("Failed to capture screenshot of OCR region")
                QMessageBox.warning(self, "Error", "Failed to capture OCR region. Please ensure the game window is visible.")
                return

            # Extract text from screenshot
            text = self.text_ocr.extract_text(screenshot)
            if not text:
                logger.error("No text extracted from OCR region")
                QMessageBox.warning(self, "Error", "Could not read coordinates. Please ensure:\n\n1. The game window is visible\n2. OCR region is correctly positioned\n3. Coordinates are visible in game")
                return

            # Extract coordinates from text
            coords = self.text_ocr._extract_coordinates(text)
            if not coords or not coords.is_valid():
                logger.error("Failed to get valid coordinates")
                QMessageBox.warning(self, "Error", "Could not get valid coordinates. Please ensure:\n\n1. The game window is visible\n2. OCR region is correctly positioned\n3. Coordinates are visible in game")
                return

            logger.info(f"Got valid coordinates: K:{coords.k} X:{coords.x} Y:{coords.y}")

            # Get direction definitions
            direction_manager = self.direction_widget.direction_manager
            if not direction_manager:
                logger.error("No direction manager available")
                self._stop_search()
                return

            # Convert coordinates to GameWorldPosition
            current_pos = GameWorldPosition(
                k=coords.k,
                x=coords.x,
                y=coords.y
            )
            logger.info(f"Got initial position: {current_pos}")

            # Update game coordinator with initial position
            self.game_coordinator.update_position(current_pos)

            # Get drag distances
            drag_distances = direction_manager.get_drag_distances()
            if not all(drag_distances):
                logger.warning("Invalid drag distances")
                QMessageBox.warning(self, "Error", "Invalid drag distances. Please calibrate the directions first.")
                self._stop_search()
                return

            # Calculate grid size based on game world dimensions
            east_distance, south_distance = drag_distances

            # Calculate cells needed for each axis independently
            grid_width = (self.WORLD_SIZE + 1) // east_distance
            if (self.WORLD_SIZE + 1) % east_distance:
                grid_width += 1

            grid_height = (self.WORLD_SIZE + 1) // south_distance
            if (self.WORLD_SIZE + 1) % south_distance:
                grid_height += 1

            logger.info(f"Calculated grid size: {grid_width}x{grid_height} based on drag distances: {drag_distances}")

            # Calculate starting cell based on current position
            start_cell_x = current_pos.x // east_distance
            start_cell_y = current_pos.y // south_distance

            logger.info(f"Starting at cell ({start_cell_x}, {start_cell_y}) based on position {current_pos}")

            # Get selected templates
            selected_templates = [item.text() for item in self.template_list.selectedItems()]
            if not selected_templates:
                logger.error("No templates selected")
                self._stop_search()
                return

            # Configure search
            self.game_search.configure(
                templates=selected_templates,
                min_confidence=self.confidence_spin.value(),
                save_screenshots=self.save_screenshots_check.isChecked(),
                grid_size=(grid_width, grid_height),
                start_pos=current_pos,
                start_cell=(start_cell_x, start_cell_y),
                drag_distances=drag_distances
            )

            # Clear previous search data
            self.grid_widget.clear_search_data()
            self.results_widget.clear_results()
            self.results_preview_widget.clear_preview()

            # Initialize grid with search parameters
            self.grid_widget.set_grid_parameters(
                grid_size=(grid_width, grid_height),
                start_pos=current_pos,
                drag_distances=drag_distances,
                current_cell=(start_cell_x, start_cell_y)
            )

            # Set search in progress
            self.grid_widget.set_search_in_progress(True)

            # Update UI state
            self.start_search_btn.setEnabled(False)
            self.stop_search_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, grid_width * grid_height)
            self.progress_bar.setValue(0)

            # Create worker thread
            self.search_thread = QThread()
            self.search_worker = SearchWorker(
                self.game_search,
                self.window_manager,
                self.text_ocr,
                self.game_coordinator
            )

            # Move worker to thread
            self.search_worker.moveToThread(self.search_thread)

            # Connect signals
            self.search_thread.started.connect(self.search_worker.run_search)
            self.search_worker.progress.connect(self._update_progress)
            self.search_worker.position_updated.connect(self._update_position)
            self.search_worker.matches_found.connect(self._update_matches)
            self.search_worker.search_complete.connect(self._on_search_complete)
            self.search_worker.error_occurred.connect(self._on_search_error)
            self.search_worker.screenshot_ready.connect(self._update_preview)

            # Start OCR for continuous updates during search
            self.text_ocr._cancellation_requested = False
            self.text_ocr.start()

            # Start search
            self.is_searching = True

            # Start the thread
            self.search_thread.start()

            # Ensure our window stays visible but doesn't steal focus
            if self.window():
                self.window().show()
                self.window().raise_()

        except Exception as e:
            logger.error(f"Error starting search: {e}", exc_info=True)
            self._stop_search()  # Ensure cleanup happens
            QMessageBox.critical(self, "Error", f"Failed to start search: {str(e)}")

    def _update_search_status(self):
        """Update the UI with current search status."""
        try:
            if not self.is_searching:
                return
                
            # Check for stop request
            if self._check_stop_keys():
                return
                
            # Get current search state
            positions_checked = self.game_search.positions_checked
            total_cells = self.game_search.total_cells
            current_pos = self.game_search.current_position
            matches = self.game_search.matches
            
            logger.debug(f"Search status - Checked: {positions_checked}/{total_cells}, "
                        f"Current position: {current_pos}, Matches: {len(matches) if matches else 0}")
            
            # Update progress bar
            if total_cells > 0:
                progress = min(100, int((positions_checked / total_cells) * 100))
                self.progress_bar.setValue(progress)
                logger.debug(f"Progress updated: {progress}%")
            
            # Update grid visualization
            if current_pos is not None:
                # Get current game position
                game_pos = self.game_search.get_game_position(current_pos[0], current_pos[1])
                logger.debug(f"Current game position: {game_pos}")
                
                if game_pos:
                    # Update game coordinator position
                    logger.debug("Updating game coordinator position")
                    self.game_coordinator.update_position(game_pos)
                    
                    # Update current position in grid
                    logger.debug(f"Updating grid position to: {current_pos}")
                    self.grid_widget.set_current_position(current_pos[0], current_pos[1])
                    
                    # Add to searched positions
                    logger.debug(f"Adding searched position: {current_pos}")
                    self.grid_widget.add_searched_position(current_pos[0], current_pos[1])
                    
                    # Add to path
                    logger.debug(f"Adding path point: {current_pos}")
                    self.grid_widget.add_path_point(current_pos[0], current_pos[1])
                    
                    # Update matches
                    if matches:
                        logger.debug(f"Processing {len(matches)} matches")
                        for match in matches:
                            if match.game_position:
                                logger.debug(f"Adding match at {current_pos} with game position: {match.game_position}")
                                self.grid_widget.set_cell_matches(
                                    current_pos[0], current_pos[1],
                                    1,  # Count of matches in cell
                                    match.game_position
                                )
                                
                                # Add match to results
                                self.results_widget.add_result(match)
                    
                    # Single update for all grid changes
                    self.grid_widget.update()
                    self.grid_widget.repaint()
                else:
                    logger.warning(f"Failed to get game position for grid coordinates: {current_pos}")
            
            # Update preview with current screenshot
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is not None:
                logger.debug("Updating preview with new screenshot")
                # Update preview directly with OpenCV image
                self.preview_widget.set_preview(screenshot)
                
                # Store last screenshot
                self.last_screenshot = screenshot
            else:
                logger.warning("Failed to capture screenshot for preview")
            
            # Check if search is complete
            if not self.game_search.is_searching or self.stop_requested:
                logger.info("Search completion detected")
                self._stop_search()
                
        except Exception as e:
            logger.error(f"Error updating search status: {e}", exc_info=True)
            self._stop_search()
            
    def _stop_search(self):
        """Stop the search process."""
        try:
            # Set stop flags first
            self.stop_requested = True
            if hasattr(self, 'search_worker'):
                self.search_worker.stop_requested = True
            if hasattr(self, 'game_search'):
                self.game_search.stop_requested = True

            # Stop key check timer
            if hasattr(self, 'key_check_timer'):
                self.key_check_timer.stop()

            # Stop calibration check when search stops
            self._check_calibration()

            if not self.is_searching:
                return

            logger.info("Stopping search...")

            # Stop OCR
            if hasattr(self, 'text_ocr'):
                self.text_ocr._cancellation_requested = True
                self.text_ocr.stop()

            # Clean up thread if it exists
            if hasattr(self, 'search_thread') and self.search_thread.isRunning():
                # Give the thread a chance to finish cleanly
                self.search_thread.quit()
                if not self.search_thread.wait(1000):  # Wait up to 1 second
                    logger.warning("Search thread did not stop cleanly, forcing termination")
                    self.search_thread.terminate()
                    self.search_thread.wait()

            # Update UI in a separate timer to avoid lockup
            QTimer.singleShot(0, self._update_ui_after_stop)

            logger.info("Search stopped")

        except Exception as e:
            logger.error(f"Error stopping search: {e}")
            # Try to ensure UI is in a good state
            QTimer.singleShot(0, self._update_ui_after_stop)

    def _update_ui_after_stop(self):
        """Update UI elements after search is stopped."""
        try:
            # Update UI state
            self.is_searching = False
            if hasattr(self, 'start_search_btn'):
                self.start_search_btn.setEnabled(True)
            if hasattr(self, 'stop_search_btn'):
                self.stop_search_btn.setEnabled(False)
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'grid_widget'):
                self.grid_widget.set_search_in_progress(False)
            if hasattr(self, 'search_timer'):
                self.search_timer.stop()

            # Show final screenshot in preview if available
            if hasattr(self, 'preview_widget') and self.last_screenshot is not None:
                self.preview_widget.set_preview(self.last_screenshot)

            # Ensure our window is visible but don't force focus
            if self.window():
                self.window().show()
                self.window().raise_()

        except Exception as e:
            logger.error(f"Error updating UI after stop: {e}")

    def _update_drag_info(self):
        """Update the drag distances info label."""
        try:
            if not self.direction_system:
                return
                
            drag_distances = self.direction_system.get_drag_distances()
            if not all(drag_distances):
                return
                
            east_distance, south_distance = drag_distances
            
            # Calculate grid size
            grid_width = (self.WORLD_SIZE + 1) // east_distance
            if (self.WORLD_SIZE + 1) % east_distance:
                grid_width += 1
                
            grid_height = (self.WORLD_SIZE + 1) // south_distance
            if (self.WORLD_SIZE + 1) % south_distance:
                grid_height += 1
                
            # Update label
            self.drag_info_label.setText(
                f"Each drag covers:\n"
                f"East: {east_distance} game units\n"
                f"South: {south_distance} game units\n"
                f"Grid size: {grid_width}x{grid_height} cells"
            )
            
        except Exception as e:
            logger.error(f"Error updating drag info: {e}")

    def _check_calibration(self):
        """Check if calibration has changed and update grid if needed."""
        try:
            # Only check calibration if we're actively searching
            if not self.is_searching:
                return

            if not self.direction_widget or not self.direction_widget.direction_manager:
                return
            
            direction_manager = self.direction_widget.direction_manager
            
            # Get current calibration state
            current_pos = direction_manager.get_current_position()
            drag_distances = direction_manager.get_drag_distances()
            
            # Get current coordinates from game state
            coords = None
            if self.game_state:
                coords = self.game_state.get_coordinates()
                if coords and coords.is_valid():
                    logger.debug(f"Valid coordinates from game state: K:{coords.k} X:{coords.x} Y:{coords.y}")
            
            # Check if calibration state has changed or we have new coordinates
            state_changed = (
                current_pos != self.last_calibration_state['position'] or
                drag_distances != self.last_calibration_state['drag_distances'] or
                (coords and coords.is_valid() and coords != self.last_calibration_state.get('coords'))
            )
            
            if state_changed:
                logger.info("Calibration state change detected")
                logger.debug(f"Old state - Position: {self.last_calibration_state['position']}, "
                           f"Distances: {self.last_calibration_state['drag_distances']}")
                logger.debug(f"New state - Position: {current_pos}, Distances: {drag_distances}")
                
                # Update calibration state
                self.last_calibration_state['position'] = current_pos
                self.last_calibration_state['drag_distances'] = drag_distances
                if coords and coords.is_valid():
                    self.last_calibration_state['coords'] = coords
                
                # Update grid calibration
                self._update_grid_calibration()
                
                # Update drag info label
                self._update_drag_info()
                
        except Exception as e:
            logger.error(f"Error checking calibration: {e}", exc_info=True)

    def _check_stop_keys(self) -> bool:
        """Check if any stop keys are pressed.
        
        Returns:
            bool: True if stop keys are pressed
        """
        try:
            # Check if enough time has passed since last check
            current_time = time.time()
            if current_time - self.last_key_check_time < self.key_check_interval:
                return False

            # Update last check time
            self.last_key_check_time = current_time

            # Check for Escape key
            escape_pressed = win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000
            # Check for Q key
            q_pressed = win32api.GetAsyncKeyState(ord('Q')) & 0x8000

            if escape_pressed or q_pressed:
                logger.info(f"Stop key detected: {'Escape' if escape_pressed else 'Q'}")
                # Use QTimer.singleShot to stop search in a non-blocking way
                QTimer.singleShot(0, self._stop_search)
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking stop keys: {e}")
            return False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        try:
            # Check for Escape or Q key
            if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
                logger.info(f"Stop key pressed: {event.key()}")
                # Use QTimer.singleShot to stop search in a non-blocking way
                QTimer.singleShot(0, self._stop_search)
                event.accept()
                return

            super().keyPressEvent(event)

        except Exception as e:
            logger.error(f"Error in keyPressEvent: {e}")
            event.ignore()

    def showEvent(self, event) -> None:
        """Handle show events."""
        super().showEvent(event)
        # Ensure we have focus when shown
        self.setFocus()
        
    def hideEvent(self, event) -> None:
        """Handle hide events."""
        super().hideEvent(event)
        # Release keyboard when hidden
        self.releaseKeyboard()

    @pyqtSlot(int, int)
    def _update_progress(self, positions_checked: int, total_cells: int):
        """Update progress bar with search progress."""
        if total_cells > 0:
            progress = min(100, int((positions_checked / total_cells) * 100))
            self.progress_bar.setValue(progress)

    @pyqtSlot(tuple, object)
    def _update_position(self, current_pos: tuple, game_pos: GameWorldPosition):
        """Update grid with current position."""
        try:
            # Update game coordinator position
            self.game_coordinator.update_position(game_pos)
            
            # Update grid
            self.grid_widget.set_current_position(current_pos[0], current_pos[1])
            self.grid_widget.add_searched_position(current_pos[0], current_pos[1])
            self.grid_widget.add_path_point(current_pos[0], current_pos[1])
            
            # Single update for all grid changes
            self.grid_widget.update()
            self.grid_widget.repaint()
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")

    @pyqtSlot(tuple, list)
    def _update_matches(self, current_pos: tuple, matches: List[SearchResult]):
        """Update grid and results with matches."""
        try:
            for match in matches:
                if match.game_position:
                    self.grid_widget.set_cell_matches(
                        current_pos[0], current_pos[1],
                        1,  # Count of matches in cell
                        match.game_position
                    )
                    self.results_widget.add_result(match)
        except Exception as e:
            logger.error(f"Error updating matches: {e}")

    @pyqtSlot(object)
    def _update_preview(self, screenshot):
        """Update preview with new screenshot."""
        try:
            self.preview_widget.set_preview(screenshot)
            self.last_screenshot = screenshot
        except Exception as e:
            logger.error(f"Error updating preview: {e}")

    @pyqtSlot()
    def _on_search_complete(self):
        """Handle search completion."""
        logger.info("Search completed")
        self._stop_search()

    @pyqtSlot(str)
    def _on_search_error(self, error_msg: str):
        """Handle search errors."""
        logger.error(f"Search error: {error_msg}")
        QMessageBox.critical(self, "Error", f"Search error: {error_msg}")
        self._stop_search()