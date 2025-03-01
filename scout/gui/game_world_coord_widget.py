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
    QGroupBox, QFormLayout, QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition

logger = logging.getLogger(__name__)

class CoordinateDisplayWidget(QWidget):
    """
    Widget for displaying and updating game world coordinates.
    
    This widget shows the current position in the game world and provides
    controls for updating coordinates and managing calibration.
    """
    
    def __init__(self, game_world_coordinator: GameWorldCoordinator, parent=None):
        """
        Initialize the coordinate display widget.
        
        Args:
            game_world_coordinator: The game world coordinator instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.game_world_coordinator = game_world_coordinator
        self.auto_update_timer = None
        self.auto_update_interval = 5000  # 5 seconds
        
        self._create_ui()
        self._connect_signals()
        
        # Ensure auto-update is disabled by default
        self.auto_update_cb.setChecked(False)
        
    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        layout = QVBoxLayout()
        
        # Coordinate display group
        coord_group = QGroupBox("Game World Coordinates")
        coord_layout = QVBoxLayout()
        
        # Coordinate labels
        self.coord_label = QLabel("K: 0, X: 0, Y: 0")
        self.coord_label.setFont(QFont("Monospace", 10))
        coord_layout.addWidget(self.coord_label)
        
        # Update button
        update_layout = QHBoxLayout()
        self.update_btn = QPushButton("Update Coordinates")
        self.auto_update_cb = QCheckBox("Auto Update")
        update_layout.addWidget(self.update_btn)
        update_layout.addWidget(self.auto_update_cb)
        coord_layout.addLayout(update_layout)
        
        # OCR region info label
        ocr_info_label = QLabel("Note: Coordinates are read from the OCR region selected in the Overlay tab")
        ocr_info_label.setStyleSheet("QLabel { color: gray; font-style: italic; }")
        ocr_info_label.setWordWrap(True)
        coord_layout.addWidget(ocr_info_label)
        
        # Set the layout for the coordinate group
        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)
        
        # Calibration group
        calibration_group = QGroupBox("Coordinate Calibration")
        calibration_layout = QVBoxLayout()
        
        # Calibration status
        self.calibration_status_label = QLabel("Calibration: Not calibrated")
        calibration_layout.addWidget(self.calibration_status_label)
        
        # Calibration buttons
        calibration_btn_layout = QHBoxLayout()
        self.start_calibration_btn = QPushButton("Start Calibration")
        self.complete_calibration_btn = QPushButton("Complete Calibration")
        self.cancel_calibration_btn = QPushButton("Cancel")
        
        # Initially disable complete and cancel buttons
        self.complete_calibration_btn.setEnabled(False)
        self.cancel_calibration_btn.setEnabled(False)
        
        calibration_btn_layout.addWidget(self.start_calibration_btn)
        calibration_btn_layout.addWidget(self.complete_calibration_btn)
        calibration_btn_layout.addWidget(self.cancel_calibration_btn)
        calibration_layout.addLayout(calibration_btn_layout)
        
        # Calibration instructions
        instructions_text = (
            "1. Click 'Start Calibration' to begin\n"
            "2. Drag/scroll the map to a different location\n"
            "3. Click 'Complete Calibration' to finish\n"
            "Note: Drag further for better accuracy"
        )
        instructions_label = QLabel(instructions_text)
        instructions_label.setWordWrap(True)
        calibration_layout.addWidget(instructions_label)
        
        # Set the layout for the calibration group
        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)
        
        # Set the main layout
        self.setLayout(layout)
        
    def _connect_signals(self):
        """Connect signals to slots."""
        # Update button
        self.update_btn.clicked.connect(self._update_coordinates)
        
        # Auto update checkbox
        self.auto_update_cb.stateChanged.connect(self._toggle_auto_update)
        
        # Calibration buttons
        self.start_calibration_btn.clicked.connect(self._start_calibration)
        self.complete_calibration_btn.clicked.connect(self._complete_calibration)
        self.cancel_calibration_btn.clicked.connect(self._cancel_calibration)
        
    def _update_coordinates(self):
        """Update the coordinate display from OCR."""
        try:
            # Check if OCR has been cancelled
            if hasattr(self.game_world_coordinator.text_ocr, '_cancellation_requested') and self.game_world_coordinator.text_ocr._cancellation_requested:
                logger.info("Coordinate update cancelled due to OCR cancellation request")
                self.coord_label.setText("OCR operation cancelled")
                self.coord_label.setStyleSheet("color: orange;")
                # Stop auto-update if OCR has been cancelled
                self._stop_auto_update()
                self.auto_update_cb.setChecked(False)
                return False
                
            # Set a timeout for the OCR process
            max_wait_time = 3  # Reduced from 5 to 3 seconds
            start_time = time.time()
            
            # Create a timer to check if the operation is taking too long
            timeout_timer = QTimer()
            timeout_reached = [False]  # Using a list to allow modification in the inner function
            cancellation_check_interval = 200  # Check every 200ms
            
            def check_timeout():
                # Check for cancellation first
                if hasattr(self.game_world_coordinator.text_ocr, '_cancellation_requested') and self.game_world_coordinator.text_ocr._cancellation_requested:
                    logger.info("Coordinate update cancelled during timeout check")
                    timeout_timer.stop()
                    timeout_reached[0] = True
                    self.coord_label.setText("OCR operation cancelled")
                    self.coord_label.setStyleSheet("color: orange;")
                    # Stop auto-update
                    self._stop_auto_update()
                    self.auto_update_cb.setChecked(False)
                    return
                
                # Then check for timeout
                if time.time() - start_time > max_wait_time:
                    timeout_reached[0] = True
                    timeout_timer.stop()
                    logger.warning(f"OCR operation timed out after {max_wait_time} seconds")
                    self.coord_label.setText("OCR operation timed out")
                    self.coord_label.setStyleSheet("color: red;")
                    # Stop auto-update if there's a timeout to prevent continuous timeouts
                    self._stop_auto_update()
                    self.auto_update_cb.setChecked(False)
                    
                    # Set cancellation flag if timeout is reached
                    if hasattr(self.game_world_coordinator.text_ocr, '_cancellation_requested'):
                        self.game_world_coordinator.text_ocr._cancellation_requested = True
                        logger.info("Setting cancellation flag due to timeout")
            
            # Start the timeout timer - check more frequently (200ms instead of 500ms)
            timeout_timer.timeout.connect(check_timeout)
            timeout_timer.start(cancellation_check_interval)
            
            # Perform the OCR operation
            success = self.game_world_coordinator.update_current_position_from_ocr()
            
            # Stop the timeout timer
            timeout_timer.stop()
            
            # If timeout was reached, return early
            if timeout_reached[0]:
                return False
                
            # Check if OCR was cancelled during the operation
            if hasattr(self.game_world_coordinator.text_ocr, '_cancellation_requested') and self.game_world_coordinator.text_ocr._cancellation_requested:
                logger.info("Coordinate update cancelled during OCR operation")
                self.coord_label.setText("OCR operation cancelled")
                self.coord_label.setStyleSheet("color: orange;")
                # Stop auto-update if OCR has been cancelled
                self._stop_auto_update()
                self.auto_update_cb.setChecked(False)
                return False
            
            # Get the current position regardless of OCR success
            pos = self.game_world_coordinator.current_position
            
            # Check if we have any valid coordinate values
            if pos and (pos.k is not None or pos.x is not None or pos.y is not None):
                # Format coordinates with placeholders for missing values
                k_str = str(pos.k) if pos.k is not None else "?"
                x_str = str(pos.x) if pos.x is not None else "?"
                y_str = str(pos.y) if pos.y is not None else "?"
                self.coord_label.setText(f"K: {k_str}, X: {x_str}, Y: {y_str}")
                
                # Use black color for success, but orange if some values are missing
                if pos.k is not None and pos.x is not None and pos.y is not None:
                    self.coord_label.setStyleSheet("color: black;")
                else:
                    self.coord_label.setStyleSheet("color: orange;")
                    logger.warning(f"Partial coordinates displayed: K: {k_str}, X: {x_str}, Y: {y_str}")
            else:
                # No valid coordinates at all
                self.coord_label.setText("No valid coordinates")
                self.coord_label.setStyleSheet("color: red;")
                logger.warning("No valid coordinates available to display")
        except Exception as e:
            logger.error(f"Error updating coordinates: {str(e)}")
            self.coord_label.setText("Error updating coordinates")
            self.coord_label.setStyleSheet("color: red;")
            # Stop auto-update if there's an error to prevent continuous errors
            self._stop_auto_update()
            self.auto_update_cb.setChecked(False)
            
    def _toggle_auto_update(self, state):
        """Toggle automatic coordinate updates."""
        if state == 2:  # 2 is the value for Checked state in Qt
            self._start_auto_update()
        else:
            self._stop_auto_update()
            
    def _start_auto_update(self):
        """Start automatic coordinate updates."""
        if not self.auto_update_timer:
            self.auto_update_timer = QTimer()
            self.auto_update_timer.timeout.connect(self._update_coordinates)
            self.auto_update_timer.start(self.auto_update_interval)
            
    def _stop_auto_update(self):
        """Stop automatic coordinate updates."""
        if self.auto_update_timer:
            self.auto_update_timer.stop()
            self.auto_update_timer = None
            
    def _start_calibration(self):
        """Start the calibration process."""
        success = self.game_world_coordinator.start_calibration()
        if success:
            # Update UI state
            self.start_calibration_btn.setEnabled(False)
            self.complete_calibration_btn.setEnabled(True)
            self.cancel_calibration_btn.setEnabled(True)
            
            # Update status
            self.calibration_status_label.setText("Calibration in progress...")
            self.calibration_status_label.setStyleSheet("color: blue;")
            
            # Show message box with instructions
            QMessageBox.information(
                self,
                "Calibration Started",
                "Calibration has started. Please drag/scroll the map to a different location, "
                "then click 'Complete Calibration'.\n\n"
                "For best results, drag the map a significant distance."
            )
        else:
            QMessageBox.warning(
                self,
                "Calibration Failed",
                "Failed to start calibration. Make sure coordinates are visible and can be read."
            )
            
    def _complete_calibration(self):
        """Complete the calibration process."""
        success = self.game_world_coordinator.complete_calibration()
        if success:
            # Update UI state
            self.start_calibration_btn.setEnabled(True)
            self.complete_calibration_btn.setEnabled(False)
            self.cancel_calibration_btn.setEnabled(False)
            
            # Update status
            status = self.game_world_coordinator.get_calibration_status()
            self.calibration_status_label.setText(status)
            self.calibration_status_label.setStyleSheet("color: green;")
            
            # Show success message
            QMessageBox.information(
                self,
                "Calibration Complete",
                "Calibration completed successfully. The coordinate system has been calibrated."
            )
        else:
            QMessageBox.warning(
                self,
                "Calibration Failed",
                "Failed to complete calibration. Make sure you've dragged the map far enough "
                "and coordinates can be read."
            )
            
    def _cancel_calibration(self):
        """Cancel the calibration process."""
        self.game_world_coordinator.cancel_calibration()
        
        # Update UI state
        self.start_calibration_btn.setEnabled(True)
        self.complete_calibration_btn.setEnabled(False)
        self.cancel_calibration_btn.setEnabled(False)
        
        # Update status
        status = self.game_world_coordinator.get_calibration_status()
        self.calibration_status_label.setText(status)
        self.calibration_status_label.setStyleSheet("color: black;")
        
    def get_current_position(self):
        """Get the current game world position."""
        return self.game_world_coordinator.current_position
        
    def update_calibration_status(self):
        """Update the calibration status display."""
        status = self.game_world_coordinator.get_calibration_status()
        self.calibration_status_label.setText(status)
        
        # Update button states based on calibration status
        is_calibrating = self.game_world_coordinator.is_calibration_in_progress()
        self.start_calibration_btn.setEnabled(not is_calibrating)
        self.complete_calibration_btn.setEnabled(is_calibrating)
        self.cancel_calibration_btn.setEnabled(is_calibrating) 