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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QTabWidget, QSplitter, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QTextEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage

from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_coordinator import GameWorldCoordinator
from scout.game_world_search import GameWorldSearch, SearchResult
from scout.game_world_direction import GameWorldDirection

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
    
    def __init__(
        self,
        window_manager: WindowManager,
        template_matcher: TemplateMatcher,
        text_ocr: TextOCR,
        game_actions: GameActions,
        game_state=None
    ):
        """
        Initialize the game world search tab.
        
        Args:
            window_manager: The window manager instance
            template_matcher: The template matcher instance
            text_ocr: The text OCR instance
            game_actions: The game actions instance
            game_state: Optional GameState instance for coordinate tracking
        """
        super().__init__()
        
        # Store components
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.game_state = game_state
        
        # Create game world coordinator and search
        self.game_coordinator = GameWorldCoordinator(window_manager, text_ocr, game_state, game_actions)
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
            self.window_manager,
            self.text_ocr,
            self.game_actions
        )
        left_layout.addWidget(self.direction_widget)
        
        # Search settings
        settings_group = QGroupBox("Search Settings")
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)
        
        # Grid size
        grid_layout = QHBoxLayout()
        self.grid_width_spin = QSpinBox()
        self.grid_width_spin.setRange(1, 100)
        self.grid_width_spin.setValue(10)
        self.grid_width_spin.valueChanged.connect(self._on_grid_size_changed)
        self.grid_height_spin = QSpinBox()
        self.grid_height_spin.setRange(1, 100)
        self.grid_height_spin.setValue(5)  # Default to half the width due to 2:1 ratio
        self.grid_height_spin.valueChanged.connect(self._on_grid_size_changed)
        grid_layout.addWidget(QLabel("Width:"))
        grid_layout.addWidget(self.grid_width_spin)
        grid_layout.addWidget(QLabel("Height:"))
        grid_layout.addWidget(self.grid_height_spin)
        settings_layout.addRow("Grid Size:", grid_layout)
        
        # Add ratio info label
        ratio_label = QLabel(f"View area has {self.VIEW_RATIO}:1 ratio (width:height)\n"
                           f"with {self.OVERLAP_PERCENT}% overlap between moves")
        ratio_label.setWordWrap(True)
        settings_layout.addRow("", ratio_label)
        
        # Template selection
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        settings_layout.addRow("Templates:", self.template_list)
        
        # Min confidence
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.8)
        settings_layout.addRow("Min Confidence:", self.confidence_spin)
        
        # Save screenshots
        self.save_screenshots_check = QCheckBox("Save Screenshots")
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
        
        # Right side - Grid visualization
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # Grid visualization
        self.grid_widget = GameWorldGrid()
        right_layout.addWidget(self.grid_widget)
        
        # Add info label for drag distances
        self.drag_info_label = QLabel()
        self.drag_info_label.setWordWrap(True)
        right_layout.addWidget(self.drag_info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
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
        self.preview_widget = SearchPreviewWidget()
        results_splitter.addWidget(self.preview_widget)
        
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
            
    def _on_grid_size_changed(self):
        """Handle grid size changes."""
        width = self.grid_width_spin.value()
        height = self.grid_height_spin.value()
        
        # Update grid visualization
        self.grid_widget.set_grid_size(width, height)
        
        # Log the effective search area
        east_moves = max(1, int(width * (100 - self.OVERLAP_PERCENT) / 100))
        south_moves = max(1, int(height * (100 - self.OVERLAP_PERCENT) / 100 / self.VIEW_RATIO))
        logger.info(f"Grid size changed to {width}x{height} with {east_moves} east moves and {south_moves} south moves")
        
    def _start_search(self):
        """Start the search process."""
        if self.is_searching:
            logger.warning("Search already in progress")
            return
            
        # Verify we have direction definitions
        if not (self.direction_widget.direction_manager.north_definition and 
                self.direction_widget.direction_manager.east_definition):
            QMessageBox.warning(
                self,
                "No Direction Definitions",
                "Please define North and East directions before starting search."
            )
            return
            
        # Get current game position
        start_pos = self.game_coordinator.current_position
        if not start_pos:
            QMessageBox.warning(
                self,
                "No Position",
                "Please ensure OCR is active and current position is available."
            )
            return
            
        # Calculate drag distances in game units
        east_def = self.direction_widget.direction_manager.east_definition
        north_def = self.direction_widget.direction_manager.north_definition
        
        if not (east_def.game_start and east_def.game_end and 
                north_def.game_start and north_def.game_end):
            QMessageBox.warning(
                self,
                "Incomplete Direction Data",
                "Please test directions to establish game unit distances."
            )
            return
            
        # Calculate distances with wrapping
        east_distance = (east_def.game_end.x - east_def.game_start.x) % (GameWorldGrid.WORLD_SIZE + 1)
        south_distance = (north_def.game_end.y - north_def.game_start.y) % (GameWorldGrid.WORLD_SIZE + 1)
        
        # Update grid parameters
        width = self.grid_width_spin.value()
        height = self.grid_height_spin.value()
        self.grid_widget.set_grid_parameters(
            grid_size=(width, height),
            start_pos=start_pos,
            drag_distances=(east_distance, south_distance)
        )
        
        # Update drag info label
        self.drag_info_label.setText(
            f"Each drag covers:\n"
            f"East: {east_distance} game units\n"
            f"South: {south_distance} game units"
        )
        
        # Reset stop flag
        self.stop_requested = False
        
        # Get selected templates
        template_names = [item.text() for item in self.template_list.selectedItems()]
        if not template_names:
            QMessageBox.warning(
                self,
                "No Templates Selected",
                "Please select at least one template to search for."
            )
            return
            
        # Update search settings
        self.game_search.min_confidence = self.confidence_spin.value()
        self.game_search.save_screenshots = self.save_screenshots_check.isChecked()
        
        # Clear previous results
        self.results_widget.clear_results()
        self.grid_widget.clear_searched_positions()
        
        # Update UI
        self.is_searching = True
        self.start_search_btn.setEnabled(False)
        self.stop_search_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.grid_widget.set_search_in_progress(True)
        
        # Start search in a separate thread
        import threading
        self.search_thread = threading.Thread(
            target=self._search_thread,
            args=(template_names,)
        )
        self.search_thread.daemon = True
        self.search_thread.start()
        
        # Start timer to update UI
        self.search_timer.start(100)  # Update every 100ms
        
    def _search_thread(self, template_names: List[str]):
        """
        Thread function for template search.
        
        The search pattern is based on actual drag movements and accounts for:
        1. Game world coordinate system (0-999 with wrapping)
        2. Actual distances covered by drag movements
        3. Efficient movement pattern to minimize travel distance
        
        Args:
            template_names: List of template names to search for
        """
        try:
            width = self.grid_width_spin.value()
            height = self.grid_height_spin.value()
            total_cells = width * height
            cells_checked = 0
            start_time = time.time()
            
            # Get current position as reference
            start_pos = self.game_coordinator.current_position
            if not start_pos:
                logger.error("No current position available")
                return
                
            # Get direction definitions
            east_def = self.direction_widget.direction_manager.east_definition
            north_def = self.direction_widget.direction_manager.north_definition
            if not (east_def and north_def):
                logger.error("Missing direction definitions")
                return
                
            # Search each cell in the grid
            for y in range(height):
                for x in range(width):
                    # Check if stop was requested
                    if self.stop_requested:
                        return
                        
                    # Update current position in visualization
                    self.grid_widget.set_current_position(x, y)
                    
                    # Get expected game world position
                    game_pos = self.grid_widget.get_game_position(x, y)
                    if game_pos:
                        logger.info(f"Searching at game position: ({game_pos.x}, {game_pos.y})")
                    
                    # Check for templates at this position
                    result = self.game_search._check_for_templates(template_names)
                    cells_checked += 1
                    
                    # Mark position as searched
                    self.grid_widget.add_searched_position(x, y)
                    
                    # Update progress
                    self._current_result = SearchResult(
                        template_name="",
                        screen_position=(0, 0),
                        game_position=game_pos,  # Include game position in result
                        confidence=0.0,
                        positions_checked=cells_checked,
                        search_time=time.time() - start_time,
                        success=False
                    )
                    
                    if result:
                        # Found a match
                        result.positions_checked = cells_checked
                        result.search_time = time.time() - start_time
                        result.game_position = game_pos  # Add game position to result
                        self._current_result = result
                        return
                        
                    # Move to next position if not at the end of row
                    if x < width - 1:
                        # Move East
                        if not self.game_search._perform_drag(east_def.screen_start, east_def.screen_end):
                            logger.error("Failed to move East")
                            return
                            
                    # Move to start of next row if at end of row
                    elif y < height - 1:
                        # Move South (inverse of North)
                        south_start, south_end = self.direction_widget.direction_manager.get_inverse_direction("North")
                        if not self.game_search._perform_drag(south_start, south_end):
                            logger.error("Failed to move South")
                            return
                            
                        # Move back to start of row
                        for _ in range(width - 1):
                            # Move West (inverse of East)
                            west_start, west_end = self.direction_widget.direction_manager.get_inverse_direction("East")
                            if not self.game_search._perform_drag(west_start, west_end):
                                logger.error("Failed to move West")
                                return
                            
        except Exception as e:
            logger.error(f"Error in search thread: {e}", exc_info=True)
            
        finally:
            # Update UI
            self.is_searching = False
            
    def _update_search_status(self):
        """Update the UI with current search status."""
        if not hasattr(self, '_current_result'):
            return
            
        result = self._current_result
        
        # Update progress bar
        total_cells = self.grid_width_spin.value() * self.grid_height_spin.value()
        progress = min(100, int(result.positions_checked / total_cells * 100))
        self.progress_bar.setValue(progress)
        
        # If search is complete, process the result
        if not self.is_searching:
            self._process_search_result(result)
            self.search_timer.stop()
            
    def _process_search_result(self, result: SearchResult):
        """
        Process the final search result.
        
        Args:
            result: Final search result
        """
        # Update UI
        self.start_search_btn.setEnabled(True)
        self.stop_search_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.grid_widget.set_search_in_progress(False)
        
        if result.success:
            # Add result to results widget
            self.results_widget.add_result(result)
            
            # Show preview
            if result.screenshot_path:
                self.preview_widget.set_image(result.screenshot_path)
                
    def _stop_search(self):
        """Stop the current search."""
        if not self.is_searching:
            return
            
        # Set flag to stop search
        self.stop_requested = True