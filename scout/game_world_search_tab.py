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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QTabWidget, QSplitter, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QTextEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent

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
        super().__init__()
        
        # Store components
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.config_manager = config_manager
        self.game_state = game_state
        
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
        self.stop_requested = False
        
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
        
        # Start periodic grid updates only when searching
        self.grid_update_timer = QTimer()
        self.grid_update_timer.timeout.connect(self._check_calibration)
        
        # Update drag info label
        self._update_drag_info()
        
        # Enable key events for the whole tab
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Create a timer to check for stop keys
        self.key_check_timer = QTimer()
        self.key_check_timer.timeout.connect(self._check_stop_keys)
        self.key_check_timer.setInterval(100)  # Check every 100ms
        
        # Update search timer interval for smoother updates
        self.search_timer.setInterval(100)  # Update every 100ms
        
        # Store last screenshot for preview
        self.last_screenshot = None
        
        # Ensure OCR is stopped initially
        self.text_ocr._cancellation_requested = True
        self.text_ocr.stop()
        
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
            
    def start_calibration_check(self):
        """Start the calibration check timer."""
        if not self.is_calibration_check_active:
            self.update_timer.start(1000)  # Check every second
            self.is_calibration_check_active = True
            logger.info("Started calibration check timer")

    def stop_calibration_check(self):
        """Stop the calibration check timer."""
        if self.is_calibration_check_active:
            self.update_timer.stop()
            self.is_calibration_check_active = False
            logger.info("Stopped calibration check timer")

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
        
        # Update grid status
        self.grid_widget._update_status()
        
    def _start_search(self):
        """Start the search process."""
        try:
            # First ensure OCR is stopped
            logger.info("Ensuring OCR is stopped...")
            self.text_ocr._cancellation_requested = True
            self.text_ocr.stop()
            time.sleep(0.5)  # Give it time to fully stop
            
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
            
            # Start key check timer when search starts
            self.key_check_timer.start()
            
            # Start calibration check
            self.start_calibration_check()
            
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
            
            # Get drag distances from direction manager
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
            
            # Update UI state
            self.start_search_btn.setEnabled(False)
            self.stop_search_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, grid_width * grid_height)
            self.progress_bar.setValue(0)
            
            # Start OCR for continuous updates during search
            self.text_ocr._cancellation_requested = False
            self.text_ocr.start()
            
            # Start search
            self.is_searching = True
            self.stop_requested = False
            self.search_timer.start()
            
            # Start grid updates
            self.grid_update_timer.start(500)  # Update every 500ms
            
            # Start search in background
            self.game_search.start()
            
        except Exception as e:
            logger.error(f"Error starting search: {e}", exc_info=True)
            self._stop_search()  # Ensure cleanup happens
            QMessageBox.critical(self, "Error", f"Failed to start search: {str(e)}")
            
    def _update_search_status(self):
        """Update the UI with current search status."""
        try:
            if not self.is_searching:
                return
                
            # Get current search state
            positions_checked = self.game_search.positions_checked
            total_cells = self.game_search.total_cells
            current_pos = self.game_search.current_position
            matches = self.game_search.matches
            
            # Update progress bar
            if total_cells > 0:
                progress = min(100, int((positions_checked / total_cells) * 100))
                self.progress_bar.setValue(progress)
            
            # Update grid visualization
            if current_pos is not None:
                # Get current game position
                game_pos = self.game_search.get_game_position(current_pos[0], current_pos[1])
                if game_pos:
                    # Update current position in grid
                    self.grid_widget.set_current_position(current_pos[0], current_pos[1])
                    
                    # Add to searched positions
                    self.grid_widget.add_searched_position(current_pos[0], current_pos[1])
                    
                    # Add to path
                    self.grid_widget.add_path_point(current_pos[0], current_pos[1])
                    
                    # Update grid status with current position
                    self.grid_widget._update_status()
                    
                    # Force grid to update
                    self.grid_widget.update()
                    
                    # Update matches
                    if matches:
                        for match in matches:
                            if match.game_position:
                                self.grid_widget.set_cell_matches(
                                    current_pos[0], current_pos[1],
                                    1,  # Count of matches in cell
                                    match.game_position
                                )
                                
                                # Add match to results
                                self.results_widget.add_result(match)
            
            # Update preview with current screenshot
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is not None:
                # Update preview directly with OpenCV image
                self.preview_widget.set_preview(screenshot)
                
                # Store last screenshot
                self.last_screenshot = screenshot
            
            # Check if search is complete
            if not self.game_search.is_searching or self.stop_requested:
                self._stop_search()
                
        except Exception as e:
            logger.error(f"Error updating search status: {e}", exc_info=True)
            self._stop_search()
            
    def _stop_search(self):
        """Stop the search process."""
        try:
            # Stop key check timer
            self.key_check_timer.stop()
            
            # Stop calibration check when search stops
            self.stop_calibration_check()
            
            # Stop grid updates
            self.grid_update_timer.stop()
            
            if not self.is_searching:
                return
            
            logger.info("Stopping search...")
            
            # Set flag to stop search
            self.stop_requested = True
            self.game_search.stop_requested = True
            
            # Stop OCR
            self.text_ocr._cancellation_requested = True
            self.text_ocr.stop()
            
            # Update UI
            self.is_searching = False
            self.start_search_btn.setEnabled(True)
            self.stop_search_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.grid_widget.set_search_in_progress(False)
            self.search_timer.stop()
            
            # Show final screenshot in preview if available
            if self.last_screenshot is not None:
                self.preview_widget.set_preview(self.last_screenshot)
            
            logger.info("Search stopped")
            
        except Exception as e:
            logger.error(f"Error stopping search: {e}")
            # Try to ensure UI is in a good state
            self.start_search_btn.setEnabled(True)
            self.stop_search_btn.setEnabled(False)
            self.progress_bar.setVisible(False)

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

    def _update_grid_calibration(self):
        """Update grid with current calibration data."""
        try:
            if not self.direction_system or not self.game_state:
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
                
            # Get drag distances
            drag_distances = self.direction_system.get_drag_distances()
            if not all(drag_distances):
                logger.warning("Invalid drag distances")
                return
                
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
            
            # Update drag info label
            self._update_drag_info()
            
        except Exception as e:
            logger.error(f"Error updating grid calibration: {e}")

    def _check_calibration(self):
        """Check if calibration has changed and update grid if needed."""
        try:
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
            
            # Check if calibration state has changed or we have new coordinates
            if (current_pos != self.last_calibration_state['position'] or
                drag_distances != self.last_calibration_state['drag_distances'] or
                (coords and coords.is_valid())):
                
                # Update calibration state
                self.last_calibration_state['position'] = current_pos
                self.last_calibration_state['drag_distances'] = drag_distances
                
                # Update grid calibration
                self._update_grid_calibration()
                
                # Force grid to update
                self.grid_widget.update()
                
        except Exception as e:
            logger.error(f"Error checking calibration: {e}")

    def _check_stop_keys(self):
        """Check if Q or Escape is pressed, even when game window has focus."""
        try:
            if not self.is_searching:
                return
                
            # Check for Q or Escape using GetAsyncKeyState
            q_pressed = win32api.GetAsyncKeyState(ord('Q')) & 0x8000
            esc_pressed = win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000
            
            if q_pressed or esc_pressed:
                logger.info("Stop key detected (Q/Escape)")
                self._stop_search()
                
        except Exception as e:
            logger.error(f"Error checking stop keys: {e}")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        try:
            if self.is_searching and (event.key() == Qt.Key.Key_Q or event.key() == Qt.Key.Key_Escape):
                logger.info("Search stop requested via keyboard (Q/Escape)")
                self._stop_search()
            else:
                super().keyPressEvent(event)
        except Exception as e:
            logger.error(f"Error handling key press: {e}")
            
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