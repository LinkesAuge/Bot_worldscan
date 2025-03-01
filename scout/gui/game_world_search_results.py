"""
Game World Search Results Widget

This module provides a widget for displaying and managing search results.
It shows:
- List of found templates
- Result details (confidence, position, etc.)
- Screenshot preview
"""

from typing import Optional
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from scout.game_world_search import SearchResult

logger = logging.getLogger(__name__)

class SearchResultsWidget(QWidget):
    """
    Widget for displaying and managing search results.
    
    This widget shows:
    - List of found templates
    - Result details (confidence, position, etc.)
    - Screenshot preview
    """
    
    # Signals
    result_selected = pyqtSignal(SearchResult)  # Emitted when a result is selected
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the search results widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create UI
        self._create_ui()
        
        # Initialize state
        self.results = []
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Results list
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        results_group.setLayout(results_layout)
        
        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_selected)
        results_layout.addWidget(self.results_list)
        
        # Result details
        details_group = QGroupBox("Result Details")
        details_layout = QFormLayout()
        details_group.setLayout(details_layout)
        
        self.template_label = QLabel()
        details_layout.addRow("Template:", self.template_label)
        
        self.confidence_label = QLabel()
        details_layout.addRow("Confidence:", self.confidence_label)
        
        self.screen_pos_label = QLabel()
        details_layout.addRow("Screen Position:", self.screen_pos_label)
        
        self.game_pos_label = QLabel()
        details_layout.addRow("Game Position:", self.game_pos_label)
        
        self.positions_label = QLabel()
        details_layout.addRow("Positions Checked:", self.positions_label)
        
        self.time_label = QLabel()
        details_layout.addRow("Search Time:", self.time_label)
        
        # Add groups to layout
        layout.addWidget(results_group)
        layout.addWidget(details_group)
        
        # Add stretch at bottom
        layout.addStretch()
        
    def add_result(self, result: SearchResult):
        """
        Add a search result.
        
        Args:
            result: Search result to add
        """
        try:
            # Create list item
            item = QListWidgetItem(
                f"{result.template_name} ({result.confidence:.2f})"
            )
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Add to list
            self.results_list.addItem(item)
            self.results.append(result)
            
            # Select if first result
            if self.results_list.count() == 1:
                self.results_list.setCurrentItem(item)
                
        except Exception as e:
            logger.error(f"Error adding result: {e}")
            
    def clear_results(self):
        """Clear all results."""
        self.results_list.clear()
        self.results.clear()
        self._clear_details()
        
    def _on_result_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """
        Handle result selection.
        
        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if not current:
            self._clear_details()
            return
            
        try:
            # Get result from item
            result = current.data(Qt.ItemDataRole.UserRole)
            
            # Update details
            self.template_label.setText(result.template_name)
            self.confidence_label.setText(f"{result.confidence:.2f}")
            self.screen_pos_label.setText(f"({result.screen_position[0]}, {result.screen_position[1]})")
            
            if result.game_position:
                self.game_pos_label.setText(str(result.game_position))
            else:
                self.game_pos_label.setText("Unknown")
                
            self.positions_label.setText(str(result.positions_checked))
            self.time_label.setText(f"{result.search_time:.1f}s")
            
            # Emit signal
            self.result_selected.emit(result)
            
        except Exception as e:
            logger.error(f"Error displaying result: {e}")
            self._clear_details()
            
    def _clear_details(self):
        """Clear result details."""
        self.template_label.clear()
        self.confidence_label.clear()
        self.screen_pos_label.clear()
        self.game_pos_label.clear()
        self.positions_label.clear()
        self.time_label.clear() 