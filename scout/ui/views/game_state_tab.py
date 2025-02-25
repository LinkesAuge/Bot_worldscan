"""
Game State Tab

This module provides a tab interface for viewing the current game state.
It visualizes game resources, map entities, buildings, and army units.
"""

import logging
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QSplitter, QComboBox, QToolBar, QFrame,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal

from scout.core.game.game_service_interface import GameServiceInterface
from scout.ui.widgets.game_state_visualization_widget import GameStateVisualizationWidget

# Set up logging
logger = logging.getLogger(__name__)

class GameStateTab(QWidget):
    """
    Game State Tab for visualizing the current game state.
    
    This tab provides:
    - Real-time monitoring of game resources
    - Visualization of the game map and entities
    - Information about buildings and army units
    - Synchronization with the game client
    """
    
    # Signals
    refresh_requested = pyqtSignal()
    entity_selected = pyqtSignal(dict)  # Entity data
    
    def __init__(self, game_service: GameServiceInterface):
        """
        Initialize the game state tab.
        
        Args:
            game_service: Service for accessing game state
        """
        super().__init__()
        
        self.game_service = game_service
        
        # Initialize state
        self._current_view = "resources"
        self._is_connected = False
        
        # Create UI layout
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Game state tab initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar = QToolBar()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        toolbar.addWidget(self.refresh_btn)
        
        # Add spacer
        toolbar.addSeparator()
        
        # Connection status
        toolbar.addWidget(QLabel("Connection Status:"))
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        toolbar.addWidget(self.status_label)
        
        # Add toolbar to layout
        main_layout.addWidget(toolbar)
        
        # Create main content
        self.visualization_widget = GameStateVisualizationWidget(self.game_service)
        main_layout.addWidget(self.visualization_widget)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Refresh button
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        
        # Game state visualization widget signals
        self.visualization_widget.entity_selected.connect(self.entity_selected)
    
    def _on_refresh_clicked(self) -> None:
        """Handle refresh button click."""
        self._refresh_game_state()
        self.refresh_requested.emit()
    
    def _refresh_game_state(self) -> None:
        """Refresh the game state visualization."""
        try:
            logger.debug("Refreshing game state...")
            
            # Check connection
            connected = self.game_service.is_game_running()
            self._update_connection_status(connected)
            
            if not connected:
                logger.warning("Cannot refresh game state: game is not running")
                return
            
            # Refresh visualization
            self.visualization_widget.refresh()
            
            logger.debug("Game state refreshed successfully")
            
        except Exception as e:
            logger.error(f"Error refreshing game state: {e}")
    
    def _update_connection_status(self, is_connected: bool) -> None:
        """
        Update the connection status label.
        
        Args:
            is_connected: Whether connected to the game
        """
        self._is_connected = is_connected
        
        if is_connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red;")
    
    def set_game_data(self, game_data: Dict[str, Any]) -> None:
        """
        Set game data for visualization.
        
        Args:
            game_data: Game state data
        """
        self.visualization_widget.set_game_data(game_data)
    
    def on_tab_activated(self) -> None:
        """Handle tab activation."""
        # Refresh game state when tab becomes active
        self._refresh_game_state() 