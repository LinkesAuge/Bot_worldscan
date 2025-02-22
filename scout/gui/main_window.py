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
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent

from ..core import WindowTracker, CoordinateManager
from ..capture import CaptureManager, PatternMatcher, OCRProcessor
from ..visualization import DebugVisualizer
from .widgets.pattern_matching import PatternMatchingWidget
from .widgets.ocr import OCRWidget
from .widgets.coordinates import CoordinateWidget
from .widgets.debug import DebugWidget

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
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Start window tracking
        self._start_tracking()
        
        logger.debug("Main window initialized")
        
    def _setup_ui(self) -> None:
        """Setup user interface."""
        try:
            # Set window properties
            self.setWindowTitle("TB Scout")
            self.resize(1200, 800)
            
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
            self.pattern_widget = PatternMatchingWidget(
                self.pattern_matcher,
                self.coordinate_manager
            )
            self.tab_widget.addTab(
                self.pattern_widget,
                "Pattern Matching"
            )
            
        except Exception as e:
            logger.error(f"Error creating pattern matching tab: {e}")
            
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
            self.window_tracker.window_found.connect(
                self._on_window_found
            )
            self.window_tracker.window_lost.connect(
                self._on_window_lost
            )
            
            # Capture manager signals
            self.capture_manager.capture_complete.connect(
                lambda *_: self._update_status("Capture: Active")
            )
            self.capture_manager.capture_failed.connect(
                lambda *_: self._update_status("Capture: Failed")
            )
            
            # Error signals
            self.window_tracker.error_occurred.connect(
                self._show_error
            )
            self.pattern_matcher.match_failed.connect(
                lambda _, msg: self._show_error(msg)
            )
            self.ocr_processor.text_failed.connect(
                lambda _, msg: self._show_error(msg)
            )
            
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
        try:
            self.window_status_label.setText("Window: Found")
            self.status_bar.showMessage(
                "Game window found",
                3000
            )
            
        except Exception as e:
            logger.error(f"Error handling window found: {e}")
            
    def _on_window_lost(self) -> None:
        """Handle window lost event."""
        try:
            self.window_status_label.setText("Window: Not found")
            self.status_bar.showMessage(
                "Game window lost",
                3000
            )
            
        except Exception as e:
            logger.error(f"Error handling window lost: {e}")
            
    def _update_status(self, message: str) -> None:
        """Update status bar message."""
        try:
            self.status_bar.showMessage(message, 3000)
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            
    def _show_error(self, message: str) -> None:
        """Show error message."""
        try:
            QMessageBox.critical(
                self,
                "Error",
                message
            )
            
        except Exception as e:
            logger.error(f"Error showing error message: {e}")
            
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        try:
            # Stop tracking
            if hasattr(self, "tracking_timer"):
                self.tracking_timer.stop()
                
            # Stop debug visualizer
            self.debug_visualizer.stop()
            
            # Accept close event
            event.accept()
            
            logger.debug("Main window closed")
            
        except Exception as e:
            logger.error(f"Error closing window: {e}")
            event.accept() 