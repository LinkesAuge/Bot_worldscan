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
    QGroupBox, QFormLayout, QComboBox, QCheckBox, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from scout.game_world_coordinator import GameWorldCoordinator, GameWorldPosition
from scout.automation.gui.position_marker import PositionMarker

logger = logging.getLogger(__name__)

class CoordinateDisplayWidget(QWidget):
    """
    Widget for displaying and updating game world coordinates.
    
    This widget shows the current position in the game world and provides
    controls for updating coordinates and managing calibration.
    """
    
    def __init__(self, game_world_coordinator: GameWorldCoordinator, window_manager, parent=None):
        """
        Initialize the coordinate display widget.
        
        Args:
            game_world_coordinator: The game world coordinator instance
            window_manager: The window manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.game_world_coordinator = game_world_coordinator
        self.window_manager = window_manager
        self.auto_update_timer = None
        self.auto_update_interval = 5000  # 5 seconds
        
        # Create position marker for calibration
        self.position_marker = PositionMarker(window_manager)
        self.position_marker.position_marked.connect(self._on_position_marked)
        self.position_marker.marking_cancelled.connect(self._on_marking_cancelled)
        
        # Store which point we're currently marking
        self.marking_start_point = True
        
        self._create_ui()
        self._connect_signals()
        
        # Initialize calibration display with loaded data
        self._update_calibration_display()
        
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
        
        # Calibration results display
        self.calibration_results_label = QLabel("")
        self.calibration_results_label.setWordWrap(True)
        calibration_layout.addWidget(self.calibration_results_label)
        
        # Drag count setting
        drag_count_layout = QHBoxLayout()
        drag_count_label = QLabel("Number of drags:")
        self.drag_count_spinbox = QSpinBox()
        self.drag_count_spinbox.setMinimum(1)
        self.drag_count_spinbox.setMaximum(10)
        self.drag_count_spinbox.setValue(3)  # Default to 3 drags
        self.drag_count_spinbox.setToolTip("More drags increase calibration accuracy but take longer")
        drag_count_layout.addWidget(drag_count_label)
        drag_count_layout.addWidget(self.drag_count_spinbox)
        drag_count_layout.addStretch()
        calibration_layout.addLayout(drag_count_layout)
        
        # Point selection buttons
        point_btn_layout = QHBoxLayout()
        self.mark_start_btn = QPushButton("Select Start Point")
        self.mark_end_btn = QPushButton("Select End Point")
        point_btn_layout.addWidget(self.mark_start_btn)
        point_btn_layout.addWidget(self.mark_end_btn)
        calibration_layout.addLayout(point_btn_layout)
        
        # Point coordinates display
        point_coord_layout = QFormLayout()
        self.start_point_label = QLabel("Not selected")
        self.end_point_label = QLabel("Not selected")
        point_coord_layout.addRow("Start Point:", self.start_point_label)
        point_coord_layout.addRow("End Point:", self.end_point_label)
        calibration_layout.addLayout(point_coord_layout)
        
        # Calibration control buttons
        control_btn_layout = QHBoxLayout()
        self.start_calibration_btn = QPushButton("Start Calibration")
        self.reset_btn = QPushButton("Reset")
        control_btn_layout.addWidget(self.start_calibration_btn)
        control_btn_layout.addWidget(self.reset_btn)
        calibration_layout.addLayout(control_btn_layout)
        
        # Initially disable buttons
        self.mark_end_btn.setEnabled(False)
        self.start_calibration_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
        # Calibration instructions
        instructions_text = (
            "1. Click 'Select Start Point' and mark your first position\n"
            "2. Click 'Select End Point' and mark your second position\n"
            "3. Click 'Start Calibration' to perform the calibration\n"
            "Note: Choose points that are far apart for better accuracy"
        )
        instructions_label = QLabel(instructions_text)
        instructions_label.setWordWrap(True)
        calibration_layout.addWidget(instructions_label)
        
        # Set the layout for the calibration group
        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)
        
        # Set the main layout
        self.setLayout(layout)
        
    def _update_calibration_display(self):
        """Update the calibration display with current calibration data."""
        # Update calibration status and results
        if self.game_world_coordinator.pixels_per_game_unit_x != 10.0 or self.game_world_coordinator.pixels_per_game_unit_y != 10.0:
            self.calibration_status_label.setText("Calibration: Calibrated")
            self.calibration_status_label.setStyleSheet("color: green;")
            
            # Show calibration results
            x_ratio = self.game_world_coordinator.pixels_per_game_unit_x
            y_ratio = self.game_world_coordinator.pixels_per_game_unit_y
            self.calibration_results_label.setText(
                f"Calibration Results:\n"
                f"X-axis: {x_ratio:.2f} pixels per game unit\n"
                f"Y-axis: {y_ratio:.2f} pixels per game unit"
            )
            
            # Update point labels if available
            if self.game_world_coordinator.start_point:
                start = self.game_world_coordinator.start_point
                self.start_point_label.setText(
                    f"Screen: ({start.screen_x}, {start.screen_y})\n"
                    f"Game: ({start.game_x:.2f}, {start.game_y:.2f})"
                )
                
            if self.game_world_coordinator.end_point:
                end = self.game_world_coordinator.end_point
                self.end_point_label.setText(
                    f"Screen: ({end.screen_x}, {end.screen_y})\n"
                    f"Game: ({end.game_x:.2f}, {end.game_y:.2f})"
                )
                
            # Enable reset button since we have calibration data
            self.reset_btn.setEnabled(True)
        else:
            self.calibration_status_label.setText("Calibration: Not calibrated")
            self.calibration_status_label.setStyleSheet("color: black;")
            self.calibration_results_label.setText("")
            
    def _connect_signals(self):
        """Connect signals to slots."""
        # Update button
        self.update_btn.clicked.connect(self._update_coordinates)
        
        # Auto update checkbox
        self.auto_update_cb.stateChanged.connect(self._toggle_auto_update)
        
        # Calibration buttons
        self.mark_start_btn.clicked.connect(lambda: self._start_marking_point(True))
        self.mark_end_btn.clicked.connect(lambda: self._start_marking_point(False))
        self.start_calibration_btn.clicked.connect(self._start_calibration)
        self.reset_btn.clicked.connect(self._reset_calibration)
        
    def _start_marking_point(self, is_start: bool):
        """
        Start marking a calibration point.
        
        Args:
            is_start: True if marking start point, False if marking end point
        """
        self.marking_start_point = is_start
        
        # Start calibration if this is the first point
        if is_start:
            self.game_world_coordinator.start_calibration()
        
        # Show instructions
        QMessageBox.information(
            self,
            "Mark Position",
            "Click anywhere on the game window to mark a position.\n"
            "The overlay will show with a slight tint to help you see it.\n\n"
            "Press ESC to cancel marking."
        )
        
        # Start position marking
        self.position_marker.start_marking()
        self.mark_start_btn.setEnabled(False)
        self.mark_end_btn.setEnabled(False)
        
    def _on_position_marked(self, point):
        """Handle a position being marked."""
        # Get current mouse position
        screen_x, screen_y = point.x(), point.y()
        
        # Set the calibration point
        self.game_world_coordinator.set_calibration_point(screen_x, screen_y, self.marking_start_point)
        
        # Update UI
        if self.marking_start_point:
            self.start_point_label.setText(f"({screen_x}, {screen_y})")
            self.mark_start_btn.setEnabled(True)
            self.mark_end_btn.setEnabled(True)
            self.calibration_status_label.setText("Start point marked - select end point...")
        else:
            self.end_point_label.setText(f"({screen_x}, {screen_y})")
            self.mark_start_btn.setEnabled(True)
            self.mark_end_btn.setEnabled(True)
            self.start_calibration_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            self.calibration_status_label.setText("Both points marked - click Start Calibration to proceed")
            
    def _on_marking_cancelled(self):
        """Handle position marking being cancelled."""
        self.mark_start_btn.setEnabled(True)
        if self.game_world_coordinator.start_point is not None:
            self.mark_end_btn.setEnabled(True)
            
    def _start_calibration(self):
        """Start the calibration process."""
        # Get the number of drags from the spinbox
        num_drags = self.drag_count_spinbox.value()
        
        # Show a progress message
        self.calibration_status_label.setText(f"Calibrating with {num_drags} drags...")
        self.calibration_status_label.setStyleSheet("color: orange;")
        QApplication.processEvents()  # Ensure UI updates
        
        # Perform calibration with the specified number of drags
        success = self.game_world_coordinator.complete_calibration(num_drags)
        if success:
            # Update UI state
            self.mark_start_btn.setEnabled(True)
            self.mark_end_btn.setEnabled(False)
            self.start_calibration_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            
            # Update status and results
            self.calibration_status_label.setText("Calibration completed successfully")
            self.calibration_status_label.setStyleSheet("color: green;")
            
            # Show calibration results
            x_ratio = self.game_world_coordinator.pixels_per_game_unit_x
            y_ratio = self.game_world_coordinator.pixels_per_game_unit_y
            self.calibration_results_label.setText(
                f"Calibration Results (averaged over {num_drags} drags):\n"
                f"X-axis: {x_ratio:.2f} pixels per game unit\n"
                f"Y-axis: {y_ratio:.2f} pixels per game unit"
            )
            
            # Show success message
            QMessageBox.information(
                self,
                "Calibration Complete",
                f"Calibration completed successfully using {num_drags} drags.\n\n"
                f"X-axis: {x_ratio:.2f} pixels per game unit\n"
                f"Y-axis: {y_ratio:.2f} pixels per game unit"
            )
        else:
            QMessageBox.warning(
                self,
                "Calibration Failed",
                "Failed to complete calibration. Make sure you've marked two points far enough apart "
                "and coordinates can be read at both points."
            )
            
    def _reset_calibration(self):
        """Reset the calibration process."""
        self.game_world_coordinator.cancel_calibration()
        
        # Reset UI state
        self.mark_start_btn.setEnabled(True)
        self.mark_end_btn.setEnabled(False)
        self.start_calibration_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
        # Reset point labels
        self.start_point_label.setText("Not selected")
        self.end_point_label.setText("Not selected")
        
        # Reset calibration status and results
        self.calibration_status_label.setText("Calibration: Not calibrated")
        self.calibration_status_label.setStyleSheet("color: black;")
        self.calibration_results_label.setText("")
        
    def _update_coordinates(self):
        """Update the coordinate display from OCR."""
        try:
            # Create a timer for timeout
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_reached = [False]  # Use list to allow modification in lambda
            
            def on_timeout():
                timeout_reached[0] = True
                self.coord_label.setText("OCR operation timed out")
                self.coord_label.setStyleSheet("color: red;")
                logger.warning("OCR operation timed out")
                # Stop auto-update if OCR times out
                self._stop_auto_update()
                self.auto_update_cb.setChecked(False)
                
            # Set timeout to 10 seconds
            timeout_timer.timeout.connect(on_timeout)
            timeout_timer.start(10000)  # 10 second timeout
            
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
            
    def get_current_position(self):
        """Get the current game world position."""
        return self.game_world_coordinator.current_position
        
    def update_calibration_status(self):
        """Update the calibration status display."""
        status = self.game_world_coordinator.get_calibration_status()
        self.calibration_status_label.setText(status)
        
        # Update button states based on calibration status
        is_calibrating = self.game_world_coordinator.calibration_in_progress
        self.mark_start_btn.setEnabled(not is_calibrating)
        self.mark_end_btn.setEnabled(not is_calibrating and self.game_world_coordinator.start_point is not None)
        self.start_calibration_btn.setEnabled(not is_calibrating and self.game_world_coordinator.start_point is not None and self.game_world_coordinator.end_point is not None)
        self.reset_btn.setEnabled(not is_calibrating and (self.game_world_coordinator.start_point is not None or self.game_world_coordinator.end_point is not None)) 