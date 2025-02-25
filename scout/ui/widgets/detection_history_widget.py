"""
Detection History Widget

This module provides a widget for displaying and managing detection history.
It shows a chronological list of detections with timestamps and details.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox,
    QApplication
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer

from scout.ui.utils.language_manager import tr

# Set up logging
logger = logging.getLogger(__name__)

class DetectionHistoryWidget(QWidget):
    """
    Widget for displaying and managing detection history.
    
    This widget shows a chronological list of detection results,
    allowing users to view, filter, and manage historical detection data.
    It provides functionality to:
    - View detection results with timestamps
    - Filter results by detection type or date range
    - Clear history or individual entries
    - Export history to various formats
    """
    
    # Signals
    result_selected = pyqtSignal(dict)  # Selected history entry
    
    def __init__(self, parent=None):
        """
        Initialize the detection history widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize state
        self._history_entries = []
        self._current_filter = None
        
        # Create UI
        self._create_ui()
        
        logger.debug("DetectionHistoryWidget initialized")
    
    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # History table
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels([
            tr("Time"), tr("Type"), tr("Strategy"), tr("Count"), tr("Duration (ms)")
        ])
        
        # Set up header
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Add to layout
        main_layout.addWidget(self.history_table)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Add buttons
        self.clear_btn = QPushButton(tr("Clear History"))
        self.export_btn = QPushButton(tr("Export History"))
        self.refresh_btn = QPushButton(tr("Refresh"))
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.history_table.itemDoubleClicked.connect(self._on_history_item_double_clicked)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        
        # Context menu setup
        self.history_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self._show_context_menu)
    
    def add_history_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add a new detection history entry.
        
        Args:
            entry: Detection history entry data
        """
        # Add to internal list
        self._history_entries.append(entry)
        
        # Add to table
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        # Create timestamp item
        timestamp = entry.get('timestamp', datetime.now())
        time_str = timestamp.strftime('%H:%M:%S')
        self.history_table.setItem(row, 0, QTableWidgetItem(time_str))
        
        # Detection type
        detection_type = entry.get('type', 'Unknown')
        self.history_table.setItem(row, 1, QTableWidgetItem(detection_type))
        
        # Strategy
        strategy = entry.get('strategy', '-')
        self.history_table.setItem(row, 2, QTableWidgetItem(strategy))
        
        # Count
        count = entry.get('count', 0)
        count_item = QTableWidgetItem(str(count))
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_table.setItem(row, 3, count_item)
        
        # Duration
        duration = entry.get('duration', 0)
        duration_ms = int(duration * 1000) if isinstance(duration, float) else duration
        duration_item = QTableWidgetItem(f"{duration_ms}")
        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.history_table.setItem(row, 4, duration_item)
        
        # Store entry data in the first item
        self.history_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, entry)
        
        # Scroll to bottom
        self.history_table.scrollToBottom()
        
        logger.debug(f"Added history entry: {detection_type}, {count} items, {duration_ms}ms")
    
    def clear_history(self) -> None:
        """Clear the detection history."""
        self._history_entries = []
        self.history_table.setRowCount(0)
    
    def load_sample_data(self) -> None:
        """Load sample data for testing purposes."""
        import datetime
        import random
        
        # Generate some sample history entries
        detection_types = ["template", "ocr", "yolo"]
        templates = ["resource_gold", "resource_wood", "resource_stone", "city", "monster"]
        
        # Add 10 random entries
        for i in range(10):
            # Create a timestamp from the last 24 hours
            hours_ago = random.randint(0, 24)
            minutes_ago = random.randint(0, 59)
            seconds_ago = random.randint(0, 59)
            timestamp = datetime.datetime.now() - datetime.timedelta(
                hours=hours_ago, minutes=minutes_ago, seconds=seconds_ago
            )
            
            # Create a random entry
            entry = {
                "id": f"entry_{i}",
                "timestamp": timestamp,
                "type": random.choice(detection_types),
                "strategy": random.choice(detection_types),
                "results_count": random.randint(0, 10),
                "duration_ms": random.randint(50, 500),
                "results": [
                    {
                        "template": random.choice(templates),
                        "confidence": random.uniform(0.7, 1.0),
                        "position": (random.randint(0, 1000), random.randint(0, 800))
                    }
                    for _ in range(random.randint(1, 5))
                ]
            }
            
            # Add the entry
            self.add_history_entry(entry)
        
        logger.debug("Loaded sample detection history data")
    
    def _on_history_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """
        Handle double click on history item.
        
        Args:
            item: The clicked table item
        """
        # Get row and entry data
        row = item.row()
        entry_data = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if entry_data:
            # Emit signal with the entry data
            self.result_selected.emit(entry_data)
            logger.debug(f"Selected history entry: {entry_data.get('type')}")
    
    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            tr("Clear History"),
            tr("Are you sure you want to clear all detection history?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.clear_history()
    
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        # This would be implemented to export history to CSV or other formats
        QMessageBox.information(
            self,
            tr("Export History"),
            tr("History export feature is not yet implemented.")
        )
    
    def _on_refresh_clicked(self) -> None:
        """Handle refresh button click."""
        # This would be implemented to refresh the history from storage
        # For now, just redraw the table
        self.history_table.viewport().update()
        logger.debug("Refreshed detection history view")
    
    def _show_context_menu(self, position) -> None:
        """
        Show context menu for history items.
        
        Args:
            position: Position where to show the menu
        """
        # Create menu
        menu = QMenu(self)
        
        # Get selected item
        selected_row = self.history_table.currentRow()
        
        if selected_row >= 0:
            # Add actions for selected item
            view_action = QAction(tr("View Details"), self)
            delete_action = QAction(tr("Delete Entry"), self)
            
            menu.addAction(view_action)
            menu.addAction(delete_action)
            
            # Connect actions
            view_action.triggered.connect(
                lambda: self._on_view_details(selected_row)
            )
            delete_action.triggered.connect(
                lambda: self._on_delete_entry(selected_row)
            )
        
        # Add global actions
        menu.addSeparator()
        export_action = QAction(tr("Export History"), self)
        clear_action = QAction(tr("Clear All"), self)
        
        menu.addAction(export_action)
        menu.addAction(clear_action)
        
        # Connect global actions
        export_action.triggered.connect(self._on_export_clicked)
        clear_action.triggered.connect(self._on_clear_clicked)
        
        # Show menu
        menu.exec(self.history_table.viewport().mapToGlobal(position))
    
    def _on_view_details(self, row: int) -> None:
        """
        View details of history entry.
        
        Args:
            row: Table row index
        """
        # Get entry data
        entry_data = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if entry_data:
            # Emit signal with the entry data
            self.result_selected.emit(entry_data)
            logger.debug(f"Viewing details for history entry at row {row}")
    
    def _on_delete_entry(self, row: int) -> None:
        """
        Delete history entry.
        
        Args:
            row: Table row index
        """
        # Get entry data
        entry_data = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if entry_data:
            # Confirm with user
            confirm = QMessageBox.question(
                self,
                tr("Delete Entry"),
                tr("Are you sure you want to delete this history entry?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                # Remove from list
                if entry_data in self._history_entries:
                    self._history_entries.remove(entry_data)
                
                # Remove from table
                self.history_table.removeRow(row)
                logger.debug(f"Deleted history entry at row {row}")
