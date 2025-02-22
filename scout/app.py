from typing import Optional, Dict, Any
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from .core import WindowTracker, CoordinateManager
from .capture import CaptureManager, PatternMatcher, OCRProcessor
from .visualization import DebugVisualizer
from .gui.main_window import MainWindow

logger = logging.getLogger(__name__)

class TBScoutApp(QObject):
    """
    Main application class for TB Scout.
    
    This class provides:
    - Core component initialization and management
    - GUI setup and event handling
    - Configuration management
    - Error handling and logging
    """
    
    # Signals
    error_occurred = pyqtSignal(str)  # Error message
    status_changed = pyqtSignal(str)  # Status message
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        debug: bool = False
    ) -> None:
        """
        Initialize TB Scout application.
        
        Args:
            config_path: Optional path to config file
            debug: Whether to enable debug mode
        """
        super().__init__()
        
        # Setup logging
        self._setup_logging(debug)
        
        # Create Qt application
        self.app = QApplication(sys.argv)
        
        try:
            # Initialize core components
            self.window_tracker = WindowTracker()
            self.coordinate_manager = CoordinateManager(
                self.window_tracker
            )
            
            # Initialize capture components
            self.capture_manager = CaptureManager(
                self.window_tracker,
                self.coordinate_manager
            )
            
            self.pattern_matcher = PatternMatcher(
                self.capture_manager
            )
            
            self.ocr_processor = OCRProcessor(
                self.capture_manager
            )
            
            # Initialize debug visualizer
            self.debug_visualizer = DebugVisualizer(
                self.window_tracker,
                self.coordinate_manager,
                self.capture_manager,
                self.pattern_matcher,
                self.ocr_processor
            )
            
            # Create main window
            self.main_window = MainWindow(
                self.window_tracker,
                self.coordinate_manager,
                self.capture_manager,
                self.pattern_matcher,
                self.ocr_processor,
                self.debug_visualizer
            )
            
            # Connect error signals
            self._connect_error_signals()
            
            logger.info("TB Scout initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing TB Scout: {e}")
            raise
            
    def _setup_logging(self, debug: bool) -> None:
        """Setup logging configuration."""
        try:
            # Create logs directory
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Set log level
            level = logging.DEBUG if debug else logging.INFO
            
            # Configure logging
            logging.basicConfig(
                level=level,
                format=(
                    "%(asctime)s [%(levelname)s] "
                    "%(name)s: %(message)s"
                ),
                handlers=[
                    # File handler
                    logging.FileHandler(
                        log_dir / "tb_scout.log",
                        encoding="utf-8"
                    ),
                    # Console handler
                    logging.StreamHandler()
                ]
            )
            
        except Exception as e:
            print(f"Error setting up logging: {e}")
            sys.exit(1)
            
    def _connect_error_signals(self) -> None:
        """Connect component error signals."""
        try:
            # Window tracker errors
            self.window_tracker.error_occurred.connect(
                self._handle_error
            )
            
            # Capture errors
            self.capture_manager.capture_failed.connect(
                lambda _, msg: self._handle_error(msg)
            )
            
            # Pattern matcher errors
            self.pattern_matcher.match_failed.connect(
                lambda _, msg: self._handle_error(msg)
            )
            
            # OCR errors
            self.ocr_processor.text_failed.connect(
                lambda _, msg: self._handle_error(msg)
            )
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            
    def _handle_error(self, error_msg: str) -> None:
        """Handle component errors."""
        try:
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.status_changed.emit("Error occurred")
            
        except Exception as e:
            logger.error(f"Error handling error: {e}")
            
    def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Application exit code
        """
        try:
            # Show main window
            self.main_window.show()
            
            # Start debug visualizer if enabled
            if logger.getEffectiveLevel() <= logging.DEBUG:
                self.debug_visualizer.start()
                
            # Run event loop
            return self.app.exec()
            
        except Exception as e:
            logger.error(f"Error running application: {e}")
            return 1
            
    def get_debug_info(self) -> Dict[str, Any]:
        """Get application debug information."""
        return {
            "window": self.window_tracker.get_debug_info(),
            "capture": self.capture_manager.get_debug_info(),
            "pattern": {
                "templates": self.pattern_matcher.get_template_info()
            },
            "ocr": self.ocr_processor.get_debug_info()
        }
        
def main() -> None:
    """Application entry point."""
    try:
        # Create and run application
        app = TBScoutApp(debug=True)
        sys.exit(app.run())
        
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 