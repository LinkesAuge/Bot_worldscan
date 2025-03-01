"""
Direction Definition Widget

This module provides a widget for defining and managing cardinal directions
in the game world. It handles:
- Direction definition UI
- Direction testing
- Direction-based calibration
"""

from typing import Optional, Tuple, Dict, Any
import logging
from pathlib import Path
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

from scout.window_manager import WindowManager
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.game_world_direction import GameWorldDirection
from scout.automation.gui.position_marker import PositionMarker

logger = logging.getLogger(__name__)

class DirectionWidget(QWidget):
    """
    Widget for defining and managing cardinal directions.
    
    This widget provides UI for:
    - Defining North and East directions
    - Testing direction movements
    - Performing direction-based calibration
    """
    
    # Signals
    direction_defined = pyqtSignal(str)  # Emitted when a direction is defined
    calibration_complete = pyqtSignal()  # Emitted when calibration is complete
    
    def __init__(
        self,
        window_manager: WindowManager,
        text_ocr: TextOCR,
        game_actions: GameActions,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the direction widget.
        
        Args:
            window_manager: For capturing screenshots and window info
            text_ocr: For reading game coordinates
            game_actions: For performing mouse actions
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.window_manager = window_manager
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        
        # Create direction manager
        self.direction_manager = GameWorldDirection(
            window_manager=window_manager,
            text_ocr=text_ocr,
            game_actions=game_actions
        )
        
        # Create position marker
        self.position_marker = PositionMarker(window_manager)
        self.position_marker.position_marked.connect(self._on_position_marked)
        self.position_marker.marking_cancelled.connect(self._on_marking_cancelled)
        
        # Initialize state
        self._current_direction = None  # Direction being defined
        self._current_position_type = None  # "start" or "end"
        
        # Initialize position storage
        self.north_start = None
        self.north_end = None
        self.east_start = None
        self.east_end = None
        
        # Create UI
        self._create_ui()
        
        # Load saved positions
        self._load_positions()
        
        # Update UI state
        self._update_ui_state()
    
    def _create_ui(self) -> None:
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Direction definition group
        direction_group = QGroupBox("Direction Definition")
        direction_layout = QVBoxLayout()
        direction_group.setLayout(direction_layout)
        
        # North direction
        north_group = QGroupBox("North Direction")
        north_layout = QVBoxLayout()
        
        # North start
        north_start_layout = QHBoxLayout()
        self.north_start_btn = QPushButton("Set Start Point")
        self.north_start_btn.clicked.connect(lambda: self._start_position_marking("North", "start"))
        self.north_start_label = QLabel("Not set")
        north_start_layout.addWidget(self.north_start_btn)
        north_start_layout.addWidget(self.north_start_label)
        north_layout.addLayout(north_start_layout)
        
        # North end
        north_end_layout = QHBoxLayout()
        self.north_end_btn = QPushButton("Set End Point")
        self.north_end_btn.clicked.connect(lambda: self._start_position_marking("North", "end"))
        self.north_end_label = QLabel("Not set")
        north_end_layout.addWidget(self.north_end_btn)
        north_end_layout.addWidget(self.north_end_label)
        north_layout.addLayout(north_end_layout)
        
        # North reset
        north_reset_layout = QHBoxLayout()
        self.north_reset_btn = QPushButton("Reset North")
        self.north_reset_btn.clicked.connect(lambda: self._reset_direction("North"))
        north_reset_layout.addWidget(self.north_reset_btn)
        north_layout.addLayout(north_reset_layout)
        
        north_group.setLayout(north_layout)
        direction_layout.addWidget(north_group)
        
        # East direction
        east_group = QGroupBox("East Direction")
        east_layout = QVBoxLayout()
        
        # East start
        east_start_layout = QHBoxLayout()
        self.east_start_btn = QPushButton("Set Start Point")
        self.east_start_btn.clicked.connect(lambda: self._start_position_marking("East", "start"))
        self.east_start_label = QLabel("Not set")
        east_start_layout.addWidget(self.east_start_btn)
        east_start_layout.addWidget(self.east_start_label)
        east_layout.addLayout(east_start_layout)
        
        # East end
        east_end_layout = QHBoxLayout()
        self.east_end_btn = QPushButton("Set End Point")
        self.east_end_btn.clicked.connect(lambda: self._start_position_marking("East", "end"))
        self.east_end_label = QLabel("Not set")
        east_end_layout.addWidget(self.east_end_btn)
        east_end_layout.addWidget(self.east_end_label)
        east_layout.addLayout(east_end_layout)
        
        # East reset
        east_reset_layout = QHBoxLayout()
        self.east_reset_btn = QPushButton("Reset East")
        self.east_reset_btn.clicked.connect(lambda: self._reset_direction("East"))
        east_reset_layout.addWidget(self.east_reset_btn)
        east_layout.addLayout(east_reset_layout)
        
        east_group.setLayout(east_layout)
        direction_layout.addWidget(east_group)
        
        # Testing group
        test_group = QGroupBox("Direction Testing")
        test_layout = QFormLayout()
        test_group.setLayout(test_layout)
        
        # Number of test runs
        self.test_runs_spin = QSpinBox()
        self.test_runs_spin.setRange(1, 10)
        self.test_runs_spin.setValue(3)
        test_layout.addRow("Test Runs:", self.test_runs_spin)
        
        # Test buttons
        test_buttons_layout = QHBoxLayout()
        self.test_north_btn = QPushButton("Test North")
        self.test_north_btn.clicked.connect(lambda: self._test_direction("North"))
        self.test_east_btn = QPushButton("Test East")
        self.test_east_btn.clicked.connect(lambda: self._test_direction("East"))
        test_buttons_layout.addWidget(self.test_north_btn)
        test_buttons_layout.addWidget(self.test_east_btn)
        test_layout.addRow("Test:", test_buttons_layout)
        
        # Add groups to main layout
        layout.addWidget(direction_group)
        layout.addWidget(test_group)
        
        # Calibration group
        calibration_group = QGroupBox("Direction Calibration")
        calibration_layout = QFormLayout()
        calibration_group.setLayout(calibration_layout)
        
        # Number of calibration runs
        self.calibration_runs_spin = QSpinBox()
        self.calibration_runs_spin.setRange(1, 10)
        self.calibration_runs_spin.setValue(3)
        calibration_layout.addRow("Calibration Runs:", self.calibration_runs_spin)
        
        # Calibration status
        self.calibration_status_label = QLabel("Not calibrated")
        calibration_layout.addRow("Status:", self.calibration_status_label)
        
        # Calibration values
        self.x_ratio_label = QLabel("0.0")
        self.y_ratio_label = QLabel("0.0")
        calibration_layout.addRow("X Ratio:", self.x_ratio_label)
        calibration_layout.addRow("Y Ratio:", self.y_ratio_label)
        
        # Calibration buttons
        calibration_buttons_layout = QHBoxLayout()
        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.clicked.connect(self._start_calibration)
        calibration_buttons_layout.addWidget(self.calibrate_btn)
        calibration_layout.addRow("Actions:", calibration_buttons_layout)
        
        layout.addWidget(calibration_group)
        
        # Add stretch at the bottom
        layout.addStretch()
    
    def _update_ui_state(self) -> None:
        """Update UI state based on current definitions."""
        # Update North position labels
        if self.north_start:
            self.north_start_label.setText(f"({self.north_start[0]}, {self.north_start[1]})")
            self.north_start_label.setStyleSheet("color: green")
        else:
            self.north_start_label.setText("Not set")
            self.north_start_label.setStyleSheet("")
            
        if self.north_end:
            self.north_end_label.setText(f"({self.north_end[0]}, {self.north_end[1]})")
            self.north_end_label.setStyleSheet("color: green")
        else:
            self.north_end_label.setText("Not set")
            self.north_end_label.setStyleSheet("")
            
        # Update East position labels
        if self.east_start:
            self.east_start_label.setText(f"({self.east_start[0]}, {self.east_start[1]})")
            self.east_start_label.setStyleSheet("color: green")
        else:
            self.east_start_label.setText("Not set")
            self.east_start_label.setStyleSheet("")
            
        if self.east_end:
            self.east_end_label.setText(f"({self.east_end[0]}, {self.east_end[1]})")
            self.east_end_label.setStyleSheet("color: green")
        else:
            self.east_end_label.setText("Not set")
            self.east_end_label.setStyleSheet("")
        
        # Update test buttons
        north_defined = bool(self.north_start and self.north_end)
        east_defined = bool(self.east_start and self.east_end)
        
        self.test_north_btn.setEnabled(north_defined)
        self.test_east_btn.setEnabled(east_defined)
        
        # Update calibration button
        self.calibrate_btn.setEnabled(north_defined and east_defined)
        
        # Update calibration values
        self.x_ratio_label.setText(f"{self.direction_manager.pixels_per_game_unit_x:.2f}")
        self.y_ratio_label.setText(f"{self.direction_manager.pixels_per_game_unit_y:.2f}")
        
        if self.direction_manager.pixels_per_game_unit_x > 0 and self.direction_manager.pixels_per_game_unit_y > 0:
            self.calibration_status_label.setText("Calibrated")
            self.calibration_status_label.setStyleSheet("color: green")
        else:
            self.calibration_status_label.setText("Not calibrated")
            self.calibration_status_label.setStyleSheet("")
            
        # Update direction definitions if we have both points
        if north_defined and not self.direction_manager.north_definition:
            self.direction_manager.define_direction("North", self.north_start, self.north_end)
            
        if east_defined and not self.direction_manager.east_definition:
            self.direction_manager.define_direction("East", self.east_start, self.east_end)
    
    def _start_position_marking(self, direction: str, position_type: str) -> None:
        """
        Start the position marking process.
        
        Args:
            direction: Direction name ("North" or "East")
            position_type: Type of position ("start" or "end")
        """
        try:
            # First check if we can find the game window
            if not self.window_manager.find_window():
                logger.error("Could not find game window - aborting position marking")
                QMessageBox.warning(self, "Error", "Could not find game window")
                return
                
            # Get window position to verify we can get coordinates
            if not self.window_manager.get_window_position():
                logger.error("Could not get window position - aborting position marking")
                QMessageBox.warning(self, "Error", "Could not get window position")
                return
                
            # Show instructions before starting marking mode
            msg = QMessageBox(self)
            msg.setWindowTitle(f"Set {direction} {position_type.title()} Point")
            msg.setText(
                f"Click to set the {position_type} point for {direction} direction.\n\n"
                "For North: Start at top, end at bottom\n"
                "For East: Start at left, end at right\n\n"
                "Press ESC to cancel marking."
            )
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            
            # Show message box and wait for response
            response = msg.exec()
            
            if response == QMessageBox.StandardButton.Ok:
                # Store what we're marking
                self._current_direction = direction
                self._current_position_type = position_type
                # Start marking mode
                self.position_marker.start_marking()
            
        except Exception as e:
            logger.error(f"Error starting position marking: {e}", exc_info=True)
            self.position_marker.stop_marking()  # Ensure overlay is cleaned up
            QMessageBox.critical(self, "Error", f"Failed to start position marking: {str(e)}")
            
    def _on_position_marked(self, point) -> None:
        """
        Handle new position being marked.
        
        Args:
            point: QPoint with the marked position
        """
        try:
            position = (point.x(), point.y())
            
            # Store position based on direction and type
            if self._current_direction == "North":
                if self._current_position_type == "start":
                    self.north_start = position
                else:
                    self.north_end = position
            else:  # East
                if self._current_position_type == "start":
                    self.east_start = position
                else:
                    self.east_end = position
                    
            # Save positions
            self._save_positions()
            
            # Update UI
            self._update_ui_state()
            
            logger.info(f"Saved {self._current_direction} {self._current_position_type} position at ({position[0]}, {position[1]})")
            
            # Clear state
            self._current_direction = None
            self._current_position_type = None
            
        except Exception as e:
            logger.error(f"Error handling position marked: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to handle position marked: {str(e)}")
            # Clear state on error
            self._current_direction = None
            self._current_position_type = None
            
    def _on_marking_cancelled(self) -> None:
        """Handle position marking being cancelled."""
        logger.debug("Position marking cancelled")
        # Clear state
        self._current_direction = None
        self._current_position_type = None
        
    def _reset_direction(self, direction: str) -> None:
        """
        Reset a direction's positions.
        
        Args:
            direction: Direction to reset ("North" or "East")
        """
        if direction == "North":
            self.north_start = None
            self.north_end = None
        else:  # East
            self.east_start = None
            self.east_end = None
            
        # Save positions
        self._save_positions()
        
        # Update UI
        self._update_ui_state()
        
    def _save_positions(self) -> None:
        """Save positions to config."""
        try:
            positions = {
                'north_start': self.north_start,
                'north_end': self.north_end,
                'east_start': self.east_start,
                'east_end': self.east_end
            }
            with open('scout/config/direction_positions.json', 'w') as f:
                json.dump(positions, f)
            logger.info("Saved direction positions to config")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
            
    def _load_positions(self) -> None:
        """Load positions from config."""
        try:
            if Path('scout/config/direction_positions.json').exists():
                with open('scout/config/direction_positions.json', 'r') as f:
                    positions = json.load(f)
                    
                self.north_start = positions.get('north_start')
                self.north_end = positions.get('north_end')
                self.east_start = positions.get('east_start')
                self.east_end = positions.get('east_end')
                
                logger.info("Loaded direction positions from config")
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
    
    def _test_direction(self, direction: str) -> None:
        """
        Test a direction definition.
        
        Args:
            direction: Direction name ("North" or "East")
        """
        try:
            num_runs = self.test_runs_spin.value()
            
            # Show progress dialog
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(f"Testing {direction} direction...")
            msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            msg.show()
            
            # Run test
            success = self.direction_manager.test_direction(direction, num_runs)
            
            # Close progress dialog
            msg.close()
            
            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"{direction} direction test successful!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to test {direction} direction"
                )
                
        except Exception as e:
            logger.error(f"Error testing direction: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error testing direction: {str(e)}"
            )
    
    def _start_calibration(self) -> None:
        """Start the calibration process."""
        try:
            # Get number of runs from spinbox
            num_runs = self.calibration_runs_spin.value()
            
            # Show progress message
            self.calibration_status_label.setText("Calibrating...")
            self.calibration_status_label.setStyleSheet("color: orange")
            QApplication.processEvents()  # Update UI
            
            # Perform calibration
            if self.direction_manager.calibrate(num_runs):
                # Update UI
                self._update_ui_state()
                self.calibration_complete.emit()
                
                # Get screen distances
                north_screen_dy = abs(self.direction_manager.north_definition.screen_end[1] - 
                                    self.direction_manager.north_definition.screen_start[1])
                east_screen_dx = abs(self.direction_manager.east_definition.screen_end[0] - 
                                   self.direction_manager.east_definition.screen_start[0])
                
                # Get game units moved (with wrapping)
                north_game_dy = 0
                east_game_dx = 0
                
                if (self.direction_manager.north_definition.game_start and 
                    self.direction_manager.north_definition.game_end):
                    # Calculate wrapped distance considering direction
                    y_diff = self.direction_manager.north_definition.game_end.y - self.direction_manager.north_definition.game_start.y
                    north_game_dy = y_diff % 1000
                    # If the wrapped distance is more than half the world size, it's shorter to go the other way
                    if north_game_dy > 500:
                        north_game_dy = -(1000 - north_game_dy)
                
                if (self.direction_manager.east_definition.game_start and 
                    self.direction_manager.east_definition.game_end):
                    # Calculate wrapped distance considering direction
                    x_diff = self.direction_manager.east_definition.game_end.x - self.direction_manager.east_definition.game_start.x
                    east_game_dx = x_diff % 1000
                    # If the wrapped distance is more than half the world size, it's shorter to go the other way
                    if east_game_dx > 500:
                        east_game_dx = -(1000 - east_game_dx)
                
                # Show detailed results
                QMessageBox.information(
                    self,
                    "Calibration Successful",
                    f"Calibration completed successfully!\n\n"
                    f"Ratios (pixels per game unit):\n"
                    f"X Ratio: {self.direction_manager.pixels_per_game_unit_x:.2f}\n"
                    f"Y Ratio: {self.direction_manager.pixels_per_game_unit_y:.2f}\n\n"
                    f"Map to Pixel Translation:\n"
                    f"North: {north_screen_dy} pixels = {abs(north_game_dy)} game units (ratio: {north_screen_dy/abs(north_game_dy):.2f})\n"
                    f"East: {east_screen_dx} pixels = {abs(east_game_dx)} game units (ratio: {east_screen_dx/abs(east_game_dx):.2f})"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Calibration Failed",
                    "Failed to complete calibration. Please ensure:\n"
                    "1. Both directions are defined\n"
                    "2. OCR is working correctly\n"
                    "3. Points are far enough apart"
                )
                
        except Exception as e:
            logger.error(f"Error during calibration: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Calibration Error",
                f"An error occurred during calibration: {str(e)}"
            ) 