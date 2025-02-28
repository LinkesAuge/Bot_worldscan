"""
Game World Coordinate Display

This module provides the widget for displaying and updating game world coordinates.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer

from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition

logger = logging.getLogger(__name__)

class CoordinateDisplayWidget(QWidget):
    """
    Widget for displaying and updating game world coordinates.
    
    This widget provides:
    - Display of current game world coordinates
    - Manual and automatic coordinate updates
    - Calibration controls
    """
    
    def __init__(self, game_coordinator: GameWorldCoordinator):
        """
        Initialize the coordinate display widget.
        
        Args:
            game_coordinator: The game world coordinator instance
        """
        super().__init__()
        
        self.game_coordinator = game_coordinator
        
        self._create_ui()
        
        # Initialize update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_coordinates)
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create coordinate display group
        coord_group = QGroupBox("Game World Coordinates")
        coord_layout = QFormLayout()
        
        # K coordinate (world)
        self.k_label = QLabel("0")
        self.k_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        coord_layout.addRow("K:", self.k_label)
        
        # X coordinate
        self.x_label = QLabel("0")
        self.x_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        coord_layout.addRow("X:", self.x_label)
        
        # Y coordinate
        self.y_label = QLabel("0")
        self.y_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        coord_layout.addRow("Y:", self.y_label)
        
        # Last update time
        self.update_time_label = QLabel("Never")
        coord_layout.addRow("Last Update:", self.update_time_label)
        
        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        self.update_btn = QPushButton("Update Now")
        self.update_btn.clicked.connect(self._update_coordinates)
        button_layout.addWidget(self.update_btn)
        
        self.auto_update_btn = QPushButton("Auto Update: Off")
        self.auto_update_btn.setCheckable(True)
        self.auto_update_btn.clicked.connect(self._toggle_auto_update)
        button_layout.addWidget(self.auto_update_btn)
        
        layout.addLayout(button_layout)
        
        # Create calibration group
        calib_group = QGroupBox("Coordinate Calibration")
        calib_layout = QVBoxLayout()
        
        # Calibration instructions
        calib_layout.addWidget(QLabel("Calibration helps improve coordinate conversion accuracy."))
        calib_layout.addWidget(QLabel("Add calibration points by capturing coordinates at different positions."))
        
        # Calibration button
        self.add_calib_btn = QPushButton("Add Calibration Point")
        self.add_calib_btn.clicked.connect(self._add_calibration_point)
        calib_layout.addWidget(self.add_calib_btn)
        
        # Calibration status
        self.calib_status_label = QLabel("No calibration points")
        calib_layout.addWidget(self.calib_status_label)
        
        calib_group.setLayout(calib_layout)
        layout.addWidget(calib_group)
        
    def _update_coordinates(self):
        """Update the coordinate display from OCR."""
        try:
            # Update coordinates from OCR
            if self.game_coordinator.update_current_position_from_ocr():
                pos = self.game_coordinator.current_position
                
                # Format coordinates with a maximum of 3 digits
                k_str = f"{pos.k:03d}" if pos.k is not None else "---"
                x_str = f"{pos.x:03d}" if pos.x is not None else "---"
                y_str = f"{pos.y:03d}" if pos.y is not None else "---"
                
                # Update labels
                self.k_label.setText(k_str)
                self.x_label.setText(x_str)
                self.y_label.setText(y_str)
                
                # Update time
                current_time = time.strftime("%H:%M:%S")
                self.update_time_label.setText(current_time)
                
                logger.info(f"Updated coordinates: {pos}")
                return True
            else:
                logger.warning("Failed to update coordinates from OCR")
                return False
                
        except Exception as e:
            logger.error(f"Error updating coordinates: {e}", exc_info=True)
            return False
            
    def _toggle_auto_update(self, checked: bool):
        """
        Toggle automatic coordinate updates.
        
        Args:
            checked: Whether auto-update is enabled
        """
        if checked:
            # Start timer
            self.update_timer.start(1000)  # Update every second
            self.auto_update_btn.setText("Auto Update: On")
            logger.info("Started automatic coordinate updates")
        else:
            # Stop timer
            self.update_timer.stop()
            self.auto_update_btn.setText("Auto Update: Off")
            logger.info("Stopped automatic coordinate updates")
            
    def _add_calibration_point(self):
        """Add a calibration point using the current position."""
        try:
            # Update coordinates from OCR
            if not self._update_coordinates():
                return
                
            # Get current position
            pos = self.game_coordinator.current_position
            
            # Get screen center
            window_pos = self.game_coordinator.window_manager.get_window_position()
            if not window_pos:
                logger.error("Failed to get window position")
                return
                
            screen_x = window_pos[0] + window_pos[2] // 2
            screen_y = window_pos[1] + window_pos[3] // 2
            
            # Add calibration point
            self.game_coordinator.add_calibration_point(
                (screen_x, screen_y),
                (pos.x, pos.y)
            )
            
            # Update calibration status
            calib_count = len(self.game_coordinator.calibration_points)
            self.calib_status_label.setText(f"{calib_count} calibration points")
            
            logger.info(f"Added calibration point: screen ({screen_x}, {screen_y}) -> game ({pos.x}, {pos.y})")
            
        except Exception as e:
            logger.error(f"Error adding calibration point: {e}", exc_info=True)
            
    def set_coord_region(self, x: int, y: int, width: int, height: int):
        """
        Set the region where coordinates are displayed.
        
        Args:
            x: X coordinate of the region
            y: Y coordinate of the region
            width: Width of the region
            height: Height of the region
        """
        self.game_coordinator.set_coord_region(x, y, width, height)
        logger.info(f"Set coordinate region to: ({x}, {y}, {width}, {height})")
        
    def get_current_position(self) -> Optional[GameWorldPosition]:
        """
        Get the current game world position.
        
        Returns:
            Current game world position, or None if not available
        """
        # Update coordinates from OCR
        if self._update_coordinates():
            return self.game_coordinator.current_position
        return None 