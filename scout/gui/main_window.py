from typing import Optional, Dict, Any
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QStatusBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QObject
from PyQt6.QtGui import QCloseEvent

from ..core import WindowTracker, CoordinateManager
from ..capture import CaptureManager, PatternMatcher, OCRProcessor
from ..visualization import DebugVisualizer, PatternMatchingOverlay
from ..config import ConfigManager
from .widgets.pattern_matching import PatternMatchingWidget
from .widgets.ocr import OCRWidget
from .widgets.coordinates import CoordinateWidget
from .widgets.debug import DebugWidget
from .widgets.pattern_matching_customization import PatternMatchingCustomizationWidget

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Main application window.
    
    This class provides:
    - Tab-based interface for different functionalities
    - Status bar for messages and errors
    - Component management and coordination
    - Window state persistence
    """
    
    def __init__(
        self,
        window_tracker: WindowTracker,
        coordinate_manager: CoordinateManager,
        capture_manager: CaptureManager,
        pattern_matcher: PatternMatcher,
        ocr_processor: OCRProcessor,
        debug_visualizer: DebugVisualizer,
        config: ConfigManager,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize main window.
        
        Args:
            window_tracker: Window tracker instance
            coordinate_manager: Coordinate manager instance
            capture_manager: Capture manager instance
            pattern_matcher: Pattern matcher instance
            ocr_processor: OCR processor instance
            debug_visualizer: Debug visualizer instance
            config: Configuration manager
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Store components
        self.window_tracker = window_tracker
        self.coordinate_manager = coordinate_manager
        self.capture_manager = capture_manager
        self.pattern_matcher = pattern_matcher
        self.ocr_processor = ocr_processor
        self.debug_visualizer = debug_visualizer
        self.config = config
        
        # Create pattern matching overlay
        logger.info("Creating pattern matching overlay")
        self.pattern_overlay = PatternMatchingOverlay(
            window_tracker=self.window_tracker,
            pattern_matcher=self.pattern_matcher,
            config=self.config
        )
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Start window tracking
        self._start_tracking()
        
        # Start pattern matching overlay
        logger.info("Starting pattern matching overlay")
        self.pattern_overlay.start()
        
        logger.debug("Main window initialized")
        
    def _setup_ui(self) -> None:
        """Setup user interface."""
        try:
            # Set window properties
            self.setWindowTitle("TB Scout")
            self.resize(1200, 800)
            
            # Create menu bar
            menubar = self.menuBar()
            view_menu = menubar.addMenu("View")
            
            # Add overlay toggle action
            self.overlay_action = view_menu.addAction("Show Overlay")
            self.overlay_action.setCheckable(True)
            self.overlay_action.setChecked(True)  # Enabled by default
            self.overlay_action.triggered.connect(self._toggle_overlay)
            
            # Create central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Create main layout
            main_layout = QVBoxLayout(central_widget)
            
            # Create tab widget
            self.tab_widget = QTabWidget()
            main_layout.addWidget(self.tab_widget)
            
            # Create tabs
            self._create_pattern_matching_tab()
            self._create_ocr_tab()
            self._create_coordinate_tab()
            self._create_customization_tab()
            self._create_debug_tab()
            
            # Create status bar
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            
            # Add permanent widgets to status bar
            self.window_status_label = QLabel("Window: Not found")
            self.status_bar.addPermanentWidget(self.window_status_label)
            
            self.capture_status_label = QLabel("Capture: Inactive")
            self.status_bar.addPermanentWidget(self.capture_status_label)
            
            logger.debug("UI setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            raise
            
    def _create_pattern_matching_tab(self) -> None:
        """Create pattern matching tab."""
        try:
            # Create pattern matching widget
            self.pattern_widget = PatternMatchingWidget(
                pattern_matcher=self.pattern_matcher,
                coordinate_manager=self.coordinate_manager,
                config=self.config  # Pass config to widget
            )
            
            # Add to tab widget
            self.tab_widget.addTab(
                self.pattern_widget,
                "Pattern Matching"
            )
            
            logger.debug("Pattern matching tab created")
            
        except Exception as e:
            logger.error(f"Error creating pattern matching tab: {e}")
            raise
            
    def _create_ocr_tab(self) -> None:
        """Create OCR tab."""
        try:
            self.ocr_widget = OCRWidget(
                self.ocr_processor,
                self.coordinate_manager
            )
            self.tab_widget.addTab(self.ocr_widget, "OCR")
            
        except Exception as e:
            logger.error(f"Error creating OCR tab: {e}")
            
    def _create_coordinate_tab(self) -> None:
        """Create coordinate system tab."""
        try:
            self.coordinate_widget = CoordinateWidget(
                self.window_tracker,
                self.coordinate_manager
            )
            self.tab_widget.addTab(
                self.coordinate_widget,
                "Coordinates"
            )
            
        except Exception as e:
            logger.error(f"Error creating coordinate tab: {e}")
            
    def _create_customization_tab(self) -> None:
        """Create the customization tab for pattern matching overlay."""
        self.customization_widget = PatternMatchingCustomizationWidget(
            config=self.config
        )
        
        # Connect settings changed signal to update overlay
        self.customization_widget.settings_changed.connect(
            self._on_overlay_settings_changed
        )
        
        self.tab_widget.addTab(
            self.customization_widget,
            "Customization"
        )
        
        logger.debug("Customization tab created")
            
    def _create_debug_tab(self) -> None:
        """Create debug tab."""
        try:
            self.debug_widget = DebugWidget(
                self.debug_visualizer
            )
            self.tab_widget.addTab(self.debug_widget, "Debug")
            
        except Exception as e:
            logger.error(f"Error creating debug tab: {e}")
            
    def _connect_signals(self) -> None:
        """Connect component signals."""
        try:
            # Window tracker signals
            self.window_tracker.window_found.connect(self._on_window_found)
            self.window_tracker.window_lost.connect(self._on_window_lost)
            self.window_tracker.error_occurred.connect(self._on_error)
            
            # Capture manager signals
            self.capture_manager.capture_complete.connect(
                lambda *_: self._update_status("Capture: Active")
            )
            self.capture_manager.capture_failed.connect(
                lambda *_: self._update_status("Capture: Failed")
            )
            
            # Pattern matcher signals
            self.pattern_matcher.match_found.connect(self._on_match_found)
            self.pattern_matcher.match_failed.connect(self._on_match_failed)
            self.pattern_matcher.error_occurred.connect(self._on_error)
            
            # Pattern overlay signals
            self.pattern_overlay.error_occurred.connect(self._on_error)
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _start_tracking(self) -> None:
        """Start window tracking."""
        try:
            # Create tracking timer
            self.tracking_timer = QTimer()
            self.tracking_timer.timeout.connect(
                self.window_tracker.find_window
            )
            
            # Start timer
            self.tracking_timer.start(1000)  # Check every second
            logger.debug("Window tracking started")
            
        except Exception as e:
            logger.error(f"Error starting tracking: {e}")
            
    def _on_window_found(self, hwnd: int) -> None:
        """Handle window found event."""
        logger.info(f"Game window found: {hwnd}")
        self.statusBar().showMessage("Game window found")
        
    def _on_window_lost(self) -> None:
        """Handle window lost event."""
        logger.info("Game window lost")
        self.statusBar().showMessage("Game window lost")
        
    def _on_match_found(self, template: str, confidence: float, position: QPoint) -> None:
        """Handle pattern match found."""
        logger.info(f"Match found: {template} (conf={confidence:.2f}, pos={position})")
        self.statusBar().showMessage(f"Match found: {template}")
        
    def _on_match_failed(self, template: str, error: str) -> None:
        """Handle pattern match failure."""
        logger.warning(f"Match failed: {template} - {error}")
        self.statusBar().showMessage(f"Match failed: {template}")
        
    def _on_error(self, error: str) -> None:
        """Handle component errors."""
        logger.error(f"Component error: {error}")
        self.statusBar().showMessage(f"Error: {error}")
        
    def _update_status(self, message: str) -> None:
        """Update status bar message."""
        try:
            self.status_bar.showMessage(message, 3000)
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        try:
            # Stop tracking
            if hasattr(self, "tracking_timer"):
                self.tracking_timer.stop()
                
            # Stop overlays
            self.pattern_overlay.stop()
            self.debug_visualizer.stop()
            
            # Accept close event
            event.accept()
            
            logger.debug("Main window closed")
            
        except Exception as e:
            logger.error(f"Error closing window: {e}")
            event.accept()
            
    def _toggle_overlay(self, checked: bool) -> None:
        """Toggle overlay visibility.
        
        Args:
            checked: Whether overlay should be shown
        """
        try:
            if checked:
                self.pattern_overlay.start()
                logger.debug("Pattern matching overlay enabled")
            else:
                self.pattern_overlay.stop()
                logger.debug("Pattern matching overlay disabled")
        except Exception as e:
            logger.error(f"Error toggling overlay: {e}")
            
    def _on_overlay_settings_changed(self) -> None:
        """Handle overlay settings changes."""
        logger.info("Updating overlay settings")
        settings = self.config.get_pattern_matching_overlay_config()
        self.pattern_overlay.update_settings(settings)
        logger.debug("Overlay settings updated") 