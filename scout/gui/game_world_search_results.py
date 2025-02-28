"""
Game World Search Results

This module provides the widget for displaying and managing search results.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import json
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QFileDialog, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QContextMenuEvent

from scout.game_world_search import SearchResult

logger = logging.getLogger(__name__)

class SearchResultItem(QListWidgetItem):
    """List item representing a search result."""
    
    def __init__(self, result: SearchResult):
        """
        Initialize a search result item.
        
        Args:
            result: The search result to represent
        """
        super().__init__()
        self.result = result
        self._update_text()
        
    def _update_text(self):
        """Update the item's display text."""
        if not self.result.success:
            self.setText("No match found")
            return
            
        # Format text with template name, position, and confidence
        text = f"{self.result.template_name} at "
        
        if self.result.game_position:
            text += f"({self.result.game_position.x}, {self.result.game_position.y})"
        elif self.result.screen_position:
            text += f"screen ({self.result.screen_position[0]}, {self.result.screen_position[1]})"
        else:
            text += "unknown position"
            
        text += f" - {self.result.confidence:.2f}"
        
        self.setText(text)


class SearchResultsWidget(QWidget):
    """
    Widget for displaying and managing search results.
    
    This widget provides:
    - List of search results
    - Details of selected result
    - Export/import functionality
    """
    
    # Signals
    result_selected = pyqtSignal(object)  # Emits SearchResult
    
    def __init__(self):
        """Initialize the search results widget."""
        super().__init__()
        
        self.results: List[SearchResult] = []
        
        self._create_ui()
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create results list
        list_group = QGroupBox("Search Results")
        list_layout = QVBoxLayout()
        
        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_selected)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_context_menu)
        list_layout.addWidget(self.results_list)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self._export_results)
        button_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("Import Results")
        self.import_btn.clicked.connect(self._import_results)
        button_layout.addWidget(self.import_btn)
        
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Create details view
        details_group = QGroupBox("Result Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
    def add_result(self, result: SearchResult):
        """
        Add a search result to the list.
        
        Args:
            result: The search result to add
        """
        # Add to results list
        self.results.append(result)
        
        # Add to UI
        item = SearchResultItem(result)
        self.results_list.addItem(item)
        self.results_list.setCurrentItem(item)
        
        logger.info(f"Added search result: {result}")
        
    def clear_results(self):
        """Clear all search results."""
        self.results = []
        self.results_list.clear()
        self.details_text.clear()
        
        logger.info("Cleared search results")
        
    def _on_result_selected(self, current: SearchResultItem, previous: SearchResultItem):
        """
        Handle result selection.
        
        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if not current:
            self.details_text.clear()
            return
            
        # Update details view
        self._update_details(current.result)
        
        # Emit signal
        self.result_selected.emit(current.result)
        
    def _update_details(self, result: SearchResult):
        """
        Update the details view with the selected result.
        
        Args:
            result: The search result to display
        """
        if not result:
            self.details_text.clear()
            return
            
        # Format details text
        details = []
        
        if result.success:
            details.append(f"<h3>Template: {result.template_name}</h3>")
            
            if result.game_position:
                details.append(f"<p><b>Game Position:</b> ({result.game_position.x}, {result.game_position.y})</p>")
                if hasattr(result.game_position, 'k') and result.game_position.k:
                    details.append(f"<p><b>World:</b> K{result.game_position.k}</p>")
                    
            if result.screen_position:
                details.append(f"<p><b>Screen Position:</b> ({result.screen_position[0]}, {result.screen_position[1]})</p>")
                
            details.append(f"<p><b>Confidence:</b> {result.confidence:.4f}</p>")
        else:
            details.append("<h3>No Match Found</h3>")
            
        details.append(f"<p><b>Search Time:</b> {result.search_time:.2f} seconds</p>")
        details.append(f"<p><b>Positions Checked:</b> {result.positions_checked}</p>")
        
        if result.screenshot_path:
            details.append(f"<p><b>Screenshot:</b> {result.screenshot_path}</p>")
            
        # Set details text
        self.details_text.setHtml("".join(details))
        
    def _show_context_menu(self, position):
        """
        Show context menu for results list.
        
        Args:
            position: Position where the menu should be shown
        """
        item = self.results_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        # Add actions
        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self._on_result_selected(item, None))
        menu.addAction(view_action)
        
        if item.result.screenshot_path:
            open_screenshot_action = QAction("Open Screenshot", self)
            open_screenshot_action.triggered.connect(lambda: self._open_screenshot(item.result))
            menu.addAction(open_screenshot_action)
            
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._remove_result(item))
        menu.addAction(remove_action)
        
        # Show menu
        menu.exec(self.results_list.mapToGlobal(position))
        
    def _remove_result(self, item: SearchResultItem):
        """
        Remove a result from the list.
        
        Args:
            item: The item to remove
        """
        # Remove from results list
        row = self.results_list.row(item)
        self.results.pop(row)
        
        # Remove from UI
        self.results_list.takeItem(row)
        
        logger.info(f"Removed search result: {item.result}")
        
    def _open_screenshot(self, result: SearchResult):
        """
        Open the screenshot for a result.
        
        Args:
            result: The result whose screenshot to open
        """
        if not result.screenshot_path:
            return
            
        try:
            # Use system default application to open the image
            import os
            import subprocess
            import platform
            
            path = result.screenshot_path
            
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', path))
            else:  # Linux
                subprocess.call(('xdg-open', path))
                
            logger.info(f"Opened screenshot: {path}")
            
        except Exception as e:
            logger.error(f"Error opening screenshot: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open screenshot: {str(e)}"
            )
            
    def _export_results(self):
        """Export search results to a file."""
        if not self.results:
            QMessageBox.information(
                self,
                "No Results",
                "There are no results to export."
            )
            return
            
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Search Results",
            f"search_results_{int(time.time())}.json",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Convert results to dictionaries
            results_data = [result.to_dict() for result in self.results]
            
            # Add metadata
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'count': len(results_data),
                'results': results_data
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=4)
                
            logger.info(f"Exported {len(self.results)} search results to {file_path}")
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(self.results)} search results to {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Export Error",
                f"Failed to export results: {str(e)}"
            )
            
    def _import_results(self):
        """Import search results from a file."""
        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Search Results",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Read from file
            with open(file_path, 'r') as f:
                import_data = json.load(f)
                
            # Check format
            if 'results' not in import_data:
                raise ValueError("Invalid file format: missing 'results' key")
                
            # Convert dictionaries to SearchResult objects
            imported_results = []
            for result_data in import_data['results']:
                result = SearchResult.from_dict(result_data)
                imported_results.append(result)
                
            # Ask user if they want to replace or append
            if self.results:
                reply = QMessageBox.question(
                    self,
                    "Import Results",
                    "Do you want to replace existing results or append new ones?",
                    QMessageBox.StandardButton.Replace | QMessageBox.StandardButton.Append | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                elif reply == QMessageBox.StandardButton.Replace:
                    self.clear_results()
            
            # Add imported results
            for result in imported_results:
                self.add_result(result)
                
            logger.info(f"Imported {len(imported_results)} search results from {file_path}")
            
            QMessageBox.information(
                self,
                "Import Successful",
                f"Imported {len(imported_results)} search results from {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error importing results: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Import Error",
                f"Failed to import results: {str(e)}"
            ) 