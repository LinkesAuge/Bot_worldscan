"""
Game World Search Tab

This module provides the main tab for game world search functionality,
integrating the game world coordinator and search functionality.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
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
from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition
from scout.game_world_search import GameWorldSearch, SearchResult
from scout.automation.search_patterns import create_search_sequence

from scout.gui.game_world_search_controls import SearchControlsWidget
from scout.gui.game_world_search_results import SearchResultsWidget
from scout.gui.game_world_search_preview import SearchPreviewWidget
from scout.gui.game_world_search_settings import SearchSettingsWidget
from scout.gui.game_world_coord_widget import CoordinateDisplayWidget

logger = logging.getLogger(__name__)

class GameWorldSearchTab(QWidget):
    """
    Main tab for game world search functionality.
    
    This tab integrates:
    - Game world coordinate system
    - Template search functionality
    - Search pattern generation
    - Results visualization
    """
    
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
        self.game_coordinator = GameWorldCoordinator(window_manager, text_ocr, game_state)
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
        self._connect_signals()
        
        # Initialize state
        self.is_searching = False
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self._update_search_status)
        
        # Load settings
        self._load_settings()
        
    def _create_ui(self):
        """Create the tab UI."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create splitter for main sections
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side - Controls and settings
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # Coordinate display
        self.coord_widget = CoordinateDisplayWidget(self.game_coordinator)
        left_layout.addWidget(self.coord_widget)
        
        # Search controls
        self.search_controls = SearchControlsWidget(
            self.template_matcher,
            self.game_coordinator
        )
        left_layout.addWidget(self.search_controls)
        
        # Search settings
        self.search_settings = SearchSettingsWidget(self.game_search)
        left_layout.addWidget(self.search_settings)
        
        splitter.addWidget(left_widget)
        
        # Right side - Results and preview
        right_widget = QTabWidget()
        
        # Results tab
        self.results_widget = SearchResultsWidget()
        right_widget.addTab(self.results_widget, "Search Results")
        
        # Preview tab
        self.preview_widget = SearchPreviewWidget()
        right_widget.addTab(self.preview_widget, "Preview")
        
        splitter.addWidget(right_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([400, 600])
        
        # Add status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(status_layout)
        
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Connect search controls signals
        self.search_controls.search_requested.connect(self._start_search)
        self.search_controls.stop_requested.connect(self._stop_search)
        
        # Connect results widget signals
        self.results_widget.result_selected.connect(self._on_result_selected)
        
        # Connect coordinates updated signal from TextOCR
        self.text_ocr.coordinates_updated.connect(self._on_coordinates_updated)
        
    def _load_settings(self):
        """Load settings from config."""
        try:
            # Load settings from config file if it exists
            config_path = Path('config/game_world_search.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    settings = json.load(f)
                    
                # Apply settings
                if 'min_confidence' in settings:
                    self.game_search.min_confidence = settings['min_confidence']
                    self.search_settings.confidence_spin.setValue(settings['min_confidence'])
                    
                if 'max_positions' in settings:
                    self.game_search.max_positions = settings['max_positions']
                    self.search_settings.max_positions_spin.setValue(settings['max_positions'])
                    
                if 'save_screenshots' in settings:
                    self.game_search.save_screenshots = settings['save_screenshots']
                    self.search_settings.save_screenshots_check.setChecked(settings['save_screenshots'])
                    
                logger.info("Loaded game world search settings")
                
        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
            
    def _save_settings(self):
        """Save settings to config."""
        try:
            settings = {
                'min_confidence': self.game_search.min_confidence,
                'max_positions': self.game_search.max_positions,
                'save_screenshots': self.game_search.save_screenshots
            }
            
            # Save to config file
            config_path = Path('config/game_world_search.json')
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(settings, f, indent=4)
                
            logger.info("Saved game world search settings")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            
    def _start_search(self):
        """Start a template search."""
        if self.is_searching:
            logger.warning("Search already in progress")
            return
            
        # Get search parameters from controls
        template_names = self.search_controls.get_selected_templates()
        if not template_names:
            QMessageBox.warning(
                self,
                "No Templates Selected",
                "Please select at least one template to search for."
            )
            return
            
        pattern = self.search_controls.get_search_pattern()
        pattern_params = self.search_controls.get_pattern_params()
        
        # Update search settings
        self.game_search.min_confidence = self.search_settings.get_min_confidence()
        self.game_search.max_positions = self.search_settings.get_max_positions()
        self.game_search.save_screenshots = self.search_settings.get_save_screenshots()
        
        # Save settings
        self._save_settings()
        
        # Clear previous results
        self.results_widget.clear_results()
        
        # Update UI
        self.is_searching = True
        self.search_controls.set_searching(True)
        self.status_label.setText("Searching...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Start search in a separate thread
        import threading
        self.search_thread = threading.Thread(
            target=self._search_thread,
            args=(template_names, pattern, pattern_params)
        )
        self.search_thread.daemon = True
        self.search_thread.start()
        
        # Start timer to update UI
        self.search_timer.start(100)  # Update every 100ms
        
    def _search_thread(self, template_names, pattern, pattern_params):
        """
        Thread function for template search.
        
        Args:
            template_names: List of template names to search for
            pattern: Search pattern to use
            pattern_params: Parameters for the search pattern
        """
        try:
            # Start search
            result = self.game_search.search_templates(
                template_names,
                pattern=pattern,
                pattern_params=pattern_params,
                callback=self._search_callback
            )
            
            # Process final result
            self._process_search_result(result)
            
        except Exception as e:
            logger.error(f"Error in search thread: {e}", exc_info=True)
            
        finally:
            # Update UI
            self.is_searching = False
            
    def _search_callback(self, result: SearchResult):
        """
        Callback function for search progress updates.
        
        Args:
            result: Current search result
        """
        # This is called from the search thread, so we just store the result
        # The UI will be updated by the timer
        self._current_result = result
        
    def _update_search_status(self):
        """Update the UI with current search status."""
        if not hasattr(self, '_current_result'):
            return
            
        result = self._current_result
        
        # Update progress bar
        if self.game_search.max_positions > 0:
            progress = min(100, int(result.positions_checked / self.game_search.max_positions * 100))
            self.progress_bar.setValue(progress)
            
        # Update status label
        self.status_label.setText(
            f"Searching... Checked {result.positions_checked} positions "
            f"({result.search_time:.1f}s elapsed)"
        )
        
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
        self.search_controls.set_searching(False)
        self.progress_bar.setVisible(False)
        
        if result.success:
            self.status_label.setText(
                f"Found template {result.template_name} with confidence {result.confidence:.2f} "
                f"after checking {result.positions_checked} positions "
                f"({result.search_time:.1f}s)"
            )
            
            # Add result to results widget
            self.results_widget.add_result(result)
            
            # Show preview
            if result.screenshot_path:
                self.preview_widget.set_image(result.screenshot_path)
                
        else:
            self.status_label.setText(
                f"No matches found after checking {result.positions_checked} positions "
                f"({result.search_time:.1f}s)"
            )
            
    def _stop_search(self):
        """Stop the current search."""
        if not self.is_searching:
            return
            
        # Set flag to stop search
        self.game_search.max_positions = 0
        
        # Update UI
        self.status_label.setText("Stopping search...")
        
    def _on_result_selected(self, result: SearchResult):
        """
        Handle result selection.
        
        Args:
            result: Selected search result
        """
        # Show preview
        if result.screenshot_path:
            self.preview_widget.set_image(result.screenshot_path)
            
        # Update status
        self.status_label.setText(
            f"Selected: {result.template_name} at {result.game_position} "
            f"with confidence {result.confidence:.2f}"
        )
        
    def _on_coordinates_updated(self, coords):
        """
        Handle coordinates updated signal from TextOCR.
        
        Args:
            coords: Updated coordinates
        """
        # Update the coordinate display widget with the latest coordinates
        # This ensures the game world search tab always shows the most recent coordinates
        # from the OCR process, which are centered and consistent
        self.coord_widget._update_coordinates()
        
        # Log the updated coordinates for debugging
        if hasattr(coords, 'k') and hasattr(coords, 'x') and hasattr(coords, 'y'):
            k_str = f"{coords.k:03d}" if coords.k is not None else "---"
            x_str = f"{coords.x:03d}" if coords.x is not None else "---"
            y_str = f"{coords.y:03d}" if coords.y is not None else "---"
            logger.info(f"Game World Search Tab received coordinates update: K: {k_str}, X: {x_str}, Y: {y_str}")
        
        # Also update the status label with the current coordinates
        if hasattr(coords, 'k') and hasattr(coords, 'x') and hasattr(coords, 'y'):
            k_str = f"{coords.k:03d}" if coords.k is not None else "---"
            x_str = f"{coords.x:03d}" if coords.x is not None else "---"
            y_str = f"{coords.y:03d}" if coords.y is not None else "---"
            self.status_label.setText(f"Current position: K: {k_str}, X: {x_str}, Y: {y_str}")
            
        # Force the coordinate display widget to update immediately
        self.coord_widget.update()