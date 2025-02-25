"""
Test Detection History Widget

This module contains tests for the DetectionHistoryWidget class, which
provides visualization of historical detection results.
"""

import unittest
from unittest.mock import MagicMock, patch
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QTableWidgetItem
from PyQt6.QtCore import Qt, QDateTime

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface
from scout.ui.widgets.detection_history_widget import DetectionHistoryWidget, TimelineView


class TestDetectionHistoryWidget(unittest.TestCase):
    """
    Test suite for the DetectionHistoryWidget class.
    
    This class tests functionality such as:
    - Adding detection results to history
    - Clearing history
    - Exporting history to file
    - Timeline visualization
    - Table display of detection results
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        # Create mock services
        self.window_service = MagicMock(spec=WindowServiceInterface)
        self.detection_service = MagicMock(spec=DetectionServiceInterface)
        
        # Create widget
        self.widget = DetectionHistoryWidget(self.window_service, self.detection_service)
        
        # Sample detection result
        self.sample_result = [
            {
                'x': 100,
                'y': 100,
                'width': 50,
                'height': 50,
                'confidence': 0.85,
                'template_name': 'test_template'
            }
        ]
    
    def tearDown(self):
        """Clean up after each test."""
        self.widget.deleteLater()
    
    def test_initialization(self):
        """Test widget initialization."""
        # Check initial state
        self.assertEqual(len(self.widget._history), 0)
        self.assertIsNotNone(self.widget._timeline)
        self.assertIsNotNone(self.widget._table)
        
        # Check that timeline exists
        self.assertTrue(hasattr(self.widget, '_timeline'))
        self.assertIsInstance(self.widget._timeline, TimelineView)
        
        # Check that export button exists
        self.assertTrue(hasattr(self.widget, 'export_btn'))
        
        # Check that clear button exists
        self.assertTrue(hasattr(self.widget, 'clear_btn'))
    
    def test_add_detection_result(self):
        """Test adding a detection result to history."""
        # Initial state
        self.assertEqual(len(self.widget._history), 0)
        
        # Add result
        self.widget.add_detection_result(self.sample_result, 'template')
        
        # Check history was updated
        self.assertEqual(len(self.widget._history), 1)
        
        # Check that history entry has expected fields
        entry = self.widget._history[0]
        self.assertIn('timestamp', entry)
        self.assertIn('strategy', entry)
        self.assertIn('results', entry)
        self.assertEqual(entry['strategy'], 'template')
        self.assertEqual(entry['results'], self.sample_result)
        
        # Add another result
        second_result = [{
            'x': 200,
            'y': 200,
            'width': 30,
            'height': 30,
            'confidence': 0.75,
            'template_name': 'another_template'
        }]
        self.widget.add_detection_result(second_result, 'template')
        
        # Check history size increased
        self.assertEqual(len(self.widget._history), 2)
    
    def test_clear_history(self):
        """Test clearing the detection history."""
        # Add some results
        self.widget.add_detection_result(self.sample_result, 'template')
        self.widget.add_detection_result(self.sample_result, 'template')
        
        # Check history has entries
        self.assertEqual(len(self.widget._history), 2)
        
        # Clear history
        self.widget.clear_history()
        
        # Check history is empty
        self.assertEqual(len(self.widget._history), 0)
    
    def test_export_history(self):
        """Test exporting detection history to a file."""
        # Add some results
        self.widget.add_detection_result(self.sample_result, 'template')
        
        # Create temporary file for export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Mock file dialog to return our temp file
            with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', 
                      return_value=(temp_filename, 'JSON Files (*.json)')):
                # Export history
                self.widget.export_history()
                
                # Check file exists
                self.assertTrue(os.path.exists(temp_filename))
                
                # Check file content
                with open(temp_filename, 'r') as f:
                    exported_data = json.load(f)
                
                # Verify exported data
                self.assertEqual(len(exported_data), 1)
                self.assertIn('timestamp', exported_data[0])
                self.assertIn('strategy', exported_data[0])
                self.assertIn('results', exported_data[0])
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_select_history_entry(self):
        """Test selecting a history entry."""
        # Add results
        self.widget.add_detection_result(self.sample_result, 'template')
        
        # Mock the table selection
        self.widget._table.currentRow = MagicMock(return_value=0)
        
        # Select entry
        self.widget._on_table_selection_changed()
        
        # Check that selected entry is shown in details
        self.assertIsNotNone(self.widget._selected_entry)
        self.assertEqual(self.widget._selected_entry['results'], self.sample_result)
    
    def test_table_display(self):
        """Test that the table correctly displays history entries."""
        # Add a result
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp,
            'strategy': 'template',
            'results': self.sample_result
        }
        self.widget._history.append(entry)
        
        # Force table update
        self.widget._update_table()
        
        # Check table content
        self.assertEqual(self.widget._table.rowCount(), 1)
        
        # Check first column (timestamp)
        timestamp_item = self.widget._table.item(0, 0)
        self.assertIsNotNone(timestamp_item)
        # Format should match: timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        self.assertEqual(timestamp_item.text(), timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Check second column (strategy)
        strategy_item = self.widget._table.item(0, 1)
        self.assertIsNotNone(strategy_item)
        self.assertEqual(strategy_item.text(), 'template')
        
        # Check third column (count)
        count_item = self.widget._table.item(0, 2)
        self.assertIsNotNone(count_item)
        self.assertEqual(count_item.text(), str(len(self.sample_result)))
    
    def test_timeline_visualization(self):
        """Test timeline visualization of detection history."""
        # Add several results at different times
        for i in range(5):
            self.widget.add_detection_result(self.sample_result, 'template')
        
        # Timeline should have visualization for each entry
        self.assertEqual(self.widget._timeline.entry_count(), 5)
    
    def test_filter_by_strategy(self):
        """Test filtering history by detection strategy."""
        # Add different types of results
        self.widget.add_detection_result(self.sample_result, 'template')
        
        ocr_result = [{
            'x': 150,
            'y': 150,
            'width': 100,
            'height': 30,
            'confidence': 0.9,
            'text': 'test text'
        }]
        self.widget.add_detection_result(ocr_result, 'ocr')
        
        # Set filter
        self.widget._filter_combo.setCurrentText('template')
        self.widget._on_filter_changed()
        
        # Check filtered table
        self.assertEqual(self.widget._table.rowCount(), 1)
        
        # Set filter to show all
        self.widget._filter_combo.setCurrentText('All')
        self.widget._on_filter_changed()
        
        # Check unfiltered table
        self.assertEqual(self.widget._table.rowCount(), 2)


class TestTimelineView(unittest.TestCase):
    """
    Test suite for the TimelineView class.
    
    This class tests the timeline visualization component of the
    DetectionHistoryWidget, including its rendering of detection
    events over time.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up the application for all tests."""
        # Create QApplication instance if not already created
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        self.timeline = TimelineView()
    
    def tearDown(self):
        """Clean up after each test."""
        self.timeline.deleteLater()
    
    def test_initialization(self):
        """Test timeline initialization."""
        self.assertEqual(self.timeline.entry_count(), 0)
        self.assertEqual(len(self.timeline._entries), 0)
    
    def test_add_entry(self):
        """Test adding an entry to the timeline."""
        # Create entry
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp,
            'strategy': 'template',
            'results': [{'confidence': 0.85}]
        }
        
        # Add entry
        self.timeline.add_entry(entry)
        
        # Check entry was added
        self.assertEqual(self.timeline.entry_count(), 1)
        self.assertEqual(len(self.timeline._entries), 1)
    
    def test_clear_entries(self):
        """Test clearing timeline entries."""
        # Add entries
        for i in range(3):
            entry = {
                'timestamp': datetime.now(),
                'strategy': 'template',
                'results': [{'confidence': 0.85}]
            }
            self.timeline.add_entry(entry)
        
        # Check entries were added
        self.assertEqual(self.timeline.entry_count(), 3)
        
        # Clear entries
        self.timeline.clear()
        
        # Check entries were cleared
        self.assertEqual(self.timeline.entry_count(), 0)
    
    def test_entry_selection(self):
        """Test selecting an entry on the timeline."""
        # Add entries
        timestamps = []
        for i in range(3):
            timestamp = datetime.now()
            timestamps.append(timestamp)
            entry = {
                'timestamp': timestamp,
                'strategy': 'template',
                'results': [{'confidence': 0.85}]
            }
            self.timeline.add_entry(entry)
        
        # Create a mocked slot
        mock_slot = MagicMock()
        self.timeline.entry_selected.connect(mock_slot)
        
        # Simulate entry selection
        self.timeline._entries[1]['selected'] = True
        self.timeline.update()
        
        # Check if signal was emitted
        self.timeline.select_entry(1)
        mock_slot.assert_called_with(1)


if __name__ == '__main__':
    unittest.main()