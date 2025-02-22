"""Tests for OCR widget."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt, QRect
from scout.gui.widgets.ocr import OCRWidget
from scout.capture import OCRProcessor
from scout.core import CoordinateManager, CoordinateSpace

@pytest.fixture
def mock_ocr_processor():
    """Create mock OCR processor."""
    processor = MagicMock(spec=OCRProcessor)
    processor.lang = "eng"
    processor.text_found = MagicMock()
    processor.text_failed = MagicMock()
    processor.get_supported_languages.return_value = ["eng", "deu", "fra"]
    processor.get_debug_info.return_value = {
        "metrics": {
            "total_extractions": 10,
            "failed_extractions": 1,
            "avg_processing_time": 0.1,
            "last_extraction": None
        }
    }
    return processor

@pytest.fixture
def mock_coordinate_manager():
    """Create mock coordinate manager."""
    manager = MagicMock(spec=CoordinateManager)
    manager.regions = {}
    return manager

@pytest.fixture
def ocr_widget(qtbot, mock_ocr_processor, mock_coordinate_manager):
    """Create OCRWidget instance."""
    widget = OCRWidget(
        mock_ocr_processor,
        mock_coordinate_manager
    )
    qtbot.addWidget(widget)
    return widget

def test_ocr_widget_initialization(ocr_widget, mock_ocr_processor):
    """Test OCRWidget initialization."""
    assert not ocr_widget.active
    assert ocr_widget.update_interval == 1000
    
    # Check controls
    assert ocr_widget.active_checkbox is not None
    assert ocr_widget.interval_spinbox is not None
    assert ocr_widget.language_combo is not None
    assert ocr_widget.region_name is not None
    assert ocr_widget.region_list is not None
    assert ocr_widget.results_list is not None
    
    # Check initial values
    assert ocr_widget.interval_spinbox.value() == 1000
    assert ocr_widget.language_combo.currentText() == "eng"
    assert ocr_widget.language_combo.count() == 3

def test_ocr_widget_activation(ocr_widget, mock_ocr_processor, qtbot):
    """Test activating and deactivating the OCR widget."""
    # Initially inactive
    assert not ocr_widget.active
    
    # Activate
    ocr_widget.active_checkbox.setChecked(True)
    assert ocr_widget.active
    assert ocr_widget.update_timer.isActive()
    
    # Deactivate
    ocr_widget.active_checkbox.setChecked(False)
    assert not ocr_widget.active
    assert not ocr_widget.update_timer.isActive()

def test_ocr_widget_interval_change(ocr_widget, mock_ocr_processor):
    """Test changing OCR interval."""
    # Change interval
    ocr_widget.interval_spinbox.setValue(2000)
    
    # Verify interval was updated
    assert ocr_widget.update_timer.interval() == 2000

def test_ocr_widget_language_change(ocr_widget, mock_ocr_processor, qtbot):
    """Test changing OCR language."""
    # Setup mock languages
    mock_ocr_processor.get_supported_languages.return_value = ["eng", "deu", "fra"]
    ocr_widget._update_languages()
    
    # Track language change
    language_changed = False
    def on_language_changed(lang):
        nonlocal language_changed
        language_changed = True
        mock_ocr_processor.lang = lang
    
    # Connect to language change
    ocr_widget.language_combo.currentTextChanged.connect(on_language_changed)
    
    # Select language
    ocr_widget.language_combo.setCurrentText("deu")
    qtbot.wait(100)  # Wait for signal processing
    
    # Verify language was updated
    assert language_changed
    assert mock_ocr_processor.lang == "deu"

def test_ocr_widget_add_region(ocr_widget, mock_coordinate_manager, qtbot):
    """Test adding OCR region."""
    # Enter region name
    qtbot.keyClicks(ocr_widget.region_name, "test_region")
    
    # Click add button
    qtbot.mouseClick(ocr_widget.add_region, Qt.MouseButton.LeftButton)
    
    # Check region was added
    mock_coordinate_manager.add_region.assert_called_once_with(
        "ocr_test_region",
        QRect(0, 0, 100, 30),
        CoordinateSpace.CLIENT
    )
    assert ocr_widget.region_list.count() == 1
    assert ocr_widget.region_list.item(0).text() == "test_region"

def test_ocr_widget_remove_region(ocr_widget, mock_coordinate_manager, qtbot):
    """Test removing a region from the OCR widget."""
    # Add test region first
    test_rect = QRect(0, 0, 100, 100)
    mock_coordinate_manager.add_region("test_region", test_rect, CoordinateSpace.SCREEN)
    ocr_widget._update_regions()
    
    # Select the region
    ocr_widget.region_list.setCurrentRow(0)
    
    # Click remove button
    qtbot.mouseClick(ocr_widget.remove_button, Qt.MouseButton.LeftButton)
    
    # Verify region was removed
    assert ocr_widget.region_list.count() == 0
    assert "test_region" not in mock_coordinate_manager.regions

def test_ocr_widget_update_regions(ocr_widget, mock_ocr_processor, qtbot):
    """Test updating OCR regions."""
    # Setup
    mock_ocr_processor.process_region = MagicMock(return_value="123")
    
    # Add test region
    ocr_widget.coordinate_manager.add_region(
        "test_region",
        {"left": 0, "top": 0, "width": 100, "height": 100},
        CoordinateSpace.CLIENT
    )
    ocr_widget.region_list.addItem("test_region")
    
    # Update regions
    ocr_widget._update_regions()
    
    # Verify
    mock_ocr_processor.process_region.assert_called_once()
    assert ocr_widget.results_list.item(0).text() == "test_region: 123"

def test_ocr_widget_text_events(ocr_widget, mock_ocr_processor, qtbot):
    """Test OCR text event handling."""
    # Setup signal tracking
    text_received = False
    received_text = None
    
    def on_text_received(text):
        nonlocal text_received, received_text
        text_received = True
        received_text = text
    
    ocr_widget.text_event.connect(on_text_received)
    
    # Emit text event
    test_text = "Test OCR Text"
    ocr_widget._handle_text_event("test_region", test_text)
    
    assert text_received
    assert received_text == test_text
    assert ocr_widget.results_list.count() > 0
    assert test_text in ocr_widget.results_list.item(0).text()

def test_ocr_widget_metrics(ocr_widget, mock_ocr_processor):
    """Test OCR widget metrics display."""
    # Update metrics
    ocr_widget._update_metrics({
        "total_extractions": 10,
        "failed_extractions": 2,
        "last_extraction_time": 0.5
    })
    
    # Verify metrics display
    metrics_text = ocr_widget.metrics_label.text()
    assert "Total Extractions: 10" in metrics_text
    assert "Failed Extractions: 2" in metrics_text
    assert "Last Extraction Time: 0.5s" in metrics_text 