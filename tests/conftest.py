"""Shared test fixtures and configuration."""

import os
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Generator, Any

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
    datefmt="%Y-%m-%d %H:%M:%S"
)

@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Create QApplication instance for the test session.
    
    Yields:
        QApplication: The application instance.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def mock_qapp() -> Generator[MagicMock, None, None]:
    """Create a mock QApplication instance.
    
    Yields:
        MagicMock: Mock QApplication instance.
    """
    with patch("PyQt6.QtWidgets.QApplication") as mock:
        instance = mock.return_value
        instance.exec.return_value = 0
        yield instance

@pytest.fixture
def mock_window() -> Generator[MagicMock, None, None]:
    """Create a mock MainWindow instance.
    
    Yields:
        MagicMock: Mock MainWindow instance.
    """
    with patch("scout.gui.main_window.MainWindow") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_config() -> Generator[MagicMock, None, None]:
    """Create a mock ConfigManager instance.
    
    Yields:
        MagicMock: Mock ConfigManager instance.
    """
    with patch("scout.core.config.ConfigManager") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Create a mock QSettings instance.
    
    Yields:
        MagicMock: Mock QSettings instance.
    """
    with patch("PyQt6.QtCore.QSettings") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_window_tracker() -> Generator[MagicMock, None, None]:
    """Create a mock WindowTracker instance.
    
    Yields:
        MagicMock: Mock WindowTracker instance.
    """
    with patch("scout.core.window_tracker.WindowTracker") as mock:
        instance = mock.return_value
        instance.get_window_rect.return_value = QRect(100, 100, 800, 600)
        instance.get_client_rect.return_value = QRect(110, 120, 780, 580)
        yield instance

@pytest.fixture
def mock_capture_manager() -> Generator[MagicMock, None, None]:
    """Create a mock CaptureManager instance.
    
    Yields:
        MagicMock: Mock CaptureManager instance.
    """
    with patch("scout.capture.capture_manager.CaptureManager") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_pattern_matcher() -> Generator[MagicMock, None, None]:
    """Create a mock PatternMatcher instance.
    
    Yields:
        MagicMock: Mock PatternMatcher instance.
    """
    with patch("scout.capture.pattern_matcher.PatternMatcher") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_ocr_processor() -> Generator[MagicMock, None, None]:
    """Create a mock OCRProcessor instance.
    
    Yields:
        MagicMock: Mock OCRProcessor instance.
    """
    with patch("scout.capture.ocr_processor.OCRProcessor") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_debug_visualizer() -> Generator[MagicMock, None, None]:
    """Create a mock DebugVisualizer instance.
    
    Yields:
        MagicMock: Mock DebugVisualizer instance.
    """
    with patch("scout.visualization.debug_visualizer.DebugVisualizer") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_coordinate_visualizer() -> Generator[MagicMock, None, None]:
    """Create a mock CoordinateVisualizer instance.
    
    Yields:
        MagicMock: Mock CoordinateVisualizer instance.
    """
    with patch("scout.visualization.coordinate_visualizer.CoordinateVisualizer") as mock:
        instance = mock.return_value
        yield instance

@pytest.fixture
def mock_win32gui() -> Generator[dict[str, MagicMock], None, None]:
    """Mock win32gui functions.
    
    Yields:
        dict[str, MagicMock]: Dictionary of mock functions.
    """
    with patch("win32gui.FindWindow") as mock_find, \
         patch("win32gui.GetWindowRect") as mock_rect, \
         patch("win32gui.GetClientRect") as mock_client, \
         patch("win32gui.ClientToScreen") as mock_screen:
        
        mock_find.return_value = 12345
        mock_rect.return_value = (100, 100, 900, 700)
        mock_client.return_value = (0, 0, 780, 580)
        mock_screen.return_value = (110, 120)
        
        yield {
            "find": mock_find,
            "rect": mock_rect,
            "client": mock_client,
            "screen": mock_screen
        }

@pytest.fixture
def mock_mss() -> Generator[MagicMock, None, None]:
    """Mock mss screen capture.
    
    Yields:
        MagicMock: Mock mss instance.
    """
    with patch("mss.mss") as mock:
        instance = mock.return_value
        instance.grab.return_value = MagicMock(
            size=(800, 600),
            rgb=bytearray(800 * 600 * 4)
        )
        yield instance

@pytest.fixture
def mock_tesseract() -> Generator[MagicMock, None, None]:
    """Mock pytesseract.
    
    Yields:
        MagicMock: Mock pytesseract instance.
    """
    with patch("pytesseract.pytesseract") as mock:
        mock.image_to_string.return_value = "123"
        mock.get_languages.return_value = ["eng"]
        yield mock

@pytest.fixture
def mock_pygame() -> Generator[MagicMock, None, None]:
    """Mock pygame.
    
    Yields:
        MagicMock: Mock pygame.mixer instance.
    """
    with patch("pygame.mixer") as mock_mixer:
        mock_mixer.Sound.return_value = MagicMock()
        yield mock_mixer

@pytest.fixture
def mock_cv2() -> Generator[dict[str, MagicMock], None, None]:
    """Mock cv2 functions.
    
    Yields:
        dict[str, MagicMock]: Dictionary of mock functions.
    """
    with patch("cv2.matchTemplate") as mock_match, \
         patch("cv2.minMaxLoc") as mock_minmax:
        
        mock_match.return_value = MagicMock()
        mock_minmax.return_value = (0.0, 0.9, (0, 0), (100, 100))
        
        yield {
            "match": mock_match,
            "minmax": mock_minmax
        }

def pytest_configure(config: Any) -> None:
    """Configure pytest.
    
    Args:
        config: Pytest configuration object.
    """
    # Register custom markers
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "gui: mark test as requiring GUI")
    config.addinivalue_line("markers", "ocr: mark test as requiring Tesseract OCR")
    config.addinivalue_line("markers", "capture: mark test as requiring screen capture")
    config.addinivalue_line("markers", "pattern: mark test as requiring pattern matching")
    config.addinivalue_line("markers", "window: mark test as requiring window management")
    config.addinivalue_line("markers", "config: mark test as requiring configuration management")
    config.addinivalue_line("markers", "visualization: mark test as requiring visualization") 