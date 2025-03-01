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
from scout.config_manager import ConfigManager

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

    def _start_search(self):
        """Start the search process."""
        try:
            # Start calibration check when search starts
            self.start_calibration_check()
            
            # Get direction definitions
            direction_manager = self.direction_widget.direction_manager
            if not direction_manager:
                logger.error("No direction manager available")
                return
                
            # Get current game position
            current_pos = direction_manager.get_current_position()
            if not current_pos:
                logger.error("Could not get current position")
                return
                
            # Get drag distances from direction manager
            drag_distances = direction_manager.get_drag_distances()
            if not all(drag_distances):
                logger.warning("Invalid drag distances")
                return
                
            # Calculate grid size based on game world dimensions and screen ratio
            east_distance, south_distance = drag_distances
            
            # Calculate how many drags needed to cover the world (999x999)
            grid_width = (self.WORLD_SIZE + 1) // east_distance
            if (self.WORLD_SIZE + 1) % east_distance:
                grid_width += 1
                
            # Height should maintain 2:1 ratio with width
            grid_height = grid_width // 2
            if grid_width % 2:
                grid_height += 1
                
            logger.info(f"Calculated grid size: {grid_width}x{grid_height} based on drag distances: {drag_distances}")
            
            # Get selected templates
            selected_templates = [item.text() for item in self.template_list.selectedItems()]
            if not selected_templates:
                logger.error("No templates selected")
                return
                
            # Configure search
            self.game_search.configure(
                templates=selected_templates,
                min_confidence=self.confidence_spin.value(),
                save_screenshots=self.save_screenshots_check.isChecked(),
                grid_size=(grid_width, grid_height),
                start_pos=current_pos,
                drag_distances=drag_distances
            )
            
            # Clear previous search data
            self.grid_widget.clear_search_data()
            self.results_widget.clear_results()
            
            # Update UI state
            self.start_search_btn.setEnabled(False)
            self.stop_search_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, grid_width * grid_height)
            self.progress_bar.setValue(0)
            
            # Start search
            self.is_searching = True
            self.stop_requested = False
            self.search_timer.start(100)  # Update every 100ms
            
            # Start search in background
            self.game_search.start()
            
        except Exception as e:
            logger.error(f"Error starting search: {e}", exc_info=True)
            self.stop_calibration_check()  # Stop calibration check if search fails
            
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
            
            # Update grid
            self.grid_widget.set_current_position(*current_pos)
            self.grid_widget.add_searched_position(*current_pos)
            
            # Add path point
            self.grid_widget.add_path_point(*current_pos)
            
            # Update matches
            if matches:
                for match in matches:
                    if match.game_position:
                        self.grid_widget.set_cell_matches(
                            current_pos[0], current_pos[1],
                            1,  # Count of matches in cell
                            match.game_position
                        )
            
            # Check if search is complete
            if not self.game_search.is_searching:
                self._stop_search()
                
        except Exception as e:
            logger.error(f"Error updating search status: {e}", exc_info=True)
            self._stop_search()
            
    def _stop_search(self):
        """Stop the search process."""
        try:
            # Stop calibration check when search stops
            self.stop_calibration_check()
            
            if not self.is_searching:
                return
            
            # Set flag to stop search
            self.stop_requested = True
            self.game_search.stop_requested = True
            
            # Update UI
            self.is_searching = False
            self.start_search_btn.setEnabled(True)
            self.stop_search_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.grid_widget.set_search_in_progress(False)
            self.search_timer.stop()
            
        except Exception as e:
            logger.error(f"Error stopping search: {e}")

    def _check_calibration(self):
        """Check if calibration has changed and update grid if needed."""
        try:
            if not self.direction_widget or not self.direction_widget.direction_manager:
                return
                
            direction_manager = self.direction_widget.direction_manager
            
            # Get current calibration state
            current_pos = direction_manager.get_current_position()
            drag_distances = direction_manager.get_drag_distances()
            
            # Check if calibration state has changed
            if (current_pos != self.last_calibration_state['position'] or
                drag_distances != self.last_calibration_state['drag_distances']):
                
                # Update calibration state
                self.last_calibration_state['position'] = current_pos
                self.last_calibration_state['drag_distances'] = drag_distances
                
                # Only update grid if we have valid calibration
                if current_pos and all(drag_distances):
                    east_distance, south_distance = drag_distances
                    
                    # Calculate grid size
                    grid_width = (self.WORLD_SIZE + 1) // east_distance
                    if (self.WORLD_SIZE + 1) % east_distance:
                        grid_width += 1
                        
                    # Height should maintain 2:1 ratio with width
                    grid_height = grid_width // 2
                    if grid_width % 2:
                        grid_height += 1
                        
                    # Update grid widget
                    self.grid_widget.set_grid_parameters(
                        (grid_width, grid_height),
                        current_pos,
                        drag_distances
                    )
                    
                    # Update drag info label
                    self.drag_info_label.setText(
                        f"Each drag covers:\n"
                        f"East: {east_distance} game units\n"
                        f"South: {south_distance} game units\n"
                        f"Grid size: {grid_width}x{grid_height} cells"
                    )
                    
        except Exception as e:
            logger.error(f"Error checking calibration: {e}")