"""
Game World Search Settings

This module provides the widget for configuring search settings.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QSlider
)
from PyQt6.QtCore import Qt

from scout.game_world_search import GameWorldSearch

logger = logging.getLogger(__name__)

class SearchSettingsWidget(QWidget):
    """
    Widget for configuring search settings.
    
    This widget provides:
    - Confidence threshold setting
    - Maximum positions to check
    - Screenshot saving options
    """
    
    def __init__(self, game_search: GameWorldSearch):
        """
        Initialize the search settings widget.
        
        Args:
            game_search: The game world search instance
        """
        super().__init__()
        
        self.game_search = game_search
        
        self._create_ui()
        self._load_settings()
        
    def _create_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create settings group
        settings_group = QGroupBox("Search Settings")
        settings_layout = QFormLayout()
        
        # Confidence threshold
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.setDecimals(2)
        settings_layout.addRow("Min Confidence:", self.confidence_spin)
        
        # Maximum positions
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 1000)
        self.max_positions_spin.setValue(100)
        settings_layout.addRow("Max Positions:", self.max_positions_spin)
        
        # Save screenshots
        self.save_screenshots_check = QCheckBox()
        self.save_screenshots_check.setChecked(False)
        settings_layout.addRow("Save Screenshots:", self.save_screenshots_check)
        
        # Position visit radius
        self.visit_radius_spin = QSpinBox()
        self.visit_radius_spin.setRange(10, 1000)
        self.visit_radius_spin.setValue(50)
        settings_layout.addRow("Position Visit Radius:", self.visit_radius_spin)
        
        # Drag delay
        self.drag_delay_spin = QDoubleSpinBox()
        self.drag_delay_spin.setRange(0.1, 10.0)
        self.drag_delay_spin.setSingleStep(0.1)
        self.drag_delay_spin.setValue(1.0)
        self.drag_delay_spin.setDecimals(1)
        settings_layout.addRow("Drag Delay (s):", self.drag_delay_spin)
        
        # Template search delay
        self.search_delay_spin = QDoubleSpinBox()
        self.search_delay_spin.setRange(0.1, 10.0)
        self.search_delay_spin.setSingleStep(0.1)
        self.search_delay_spin.setValue(0.5)
        self.search_delay_spin.setDecimals(1)
        settings_layout.addRow("Search Delay (s):", self.search_delay_spin)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Create OCR settings group
        ocr_group = QGroupBox("OCR Settings")
        ocr_layout = QFormLayout()
        
        # OCR update frequency
        self.ocr_freq_spin = QDoubleSpinBox()
        self.ocr_freq_spin.setRange(0.1, 10.0)
        self.ocr_freq_spin.setSingleStep(0.1)
        self.ocr_freq_spin.setValue(1.0)
        self.ocr_freq_spin.setDecimals(1)
        ocr_layout.addRow("OCR Frequency (Hz):", self.ocr_freq_spin)
        
        # OCR enabled
        self.ocr_enabled_check = QCheckBox()
        self.ocr_enabled_check.setChecked(True)
        ocr_layout.addRow("OCR Enabled:", self.ocr_enabled_check)
        
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)
        
        # Add apply button
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.clicked.connect(self._apply_settings)
        layout.addWidget(self.apply_btn)
        
        # Add spacer
        layout.addStretch()
        
    def _load_settings(self):
        """Load settings from the game search instance."""
        # Set values from game search
        self.confidence_spin.setValue(self.game_search.min_confidence)
        self.max_positions_spin.setValue(self.game_search.max_positions)
        self.save_screenshots_check.setChecked(self.game_search.save_screenshots)
        self.visit_radius_spin.setValue(self.game_search.position_visit_radius)
        self.drag_delay_spin.setValue(self.game_search.drag_delay)
        self.search_delay_spin.setValue(self.game_search.template_search_delay)
        
    def _apply_settings(self):
        """Apply settings to the game search instance."""
        # Update game search settings
        self.game_search.min_confidence = self.confidence_spin.value()
        self.game_search.max_positions = self.max_positions_spin.value()
        self.game_search.save_screenshots = self.save_screenshots_check.isChecked()
        self.game_search.position_visit_radius = self.visit_radius_spin.value()
        self.game_search.drag_delay = self.drag_delay_spin.value()
        self.game_search.template_search_delay = self.search_delay_spin.value()
        
        logger.info("Applied search settings")
        
    def get_min_confidence(self) -> float:
        """
        Get the minimum confidence threshold.
        
        Returns:
            Minimum confidence threshold
        """
        return self.confidence_spin.value()
        
    def get_max_positions(self) -> int:
        """
        Get the maximum positions to check.
        
        Returns:
            Maximum positions to check
        """
        return self.max_positions_spin.value()
        
    def get_save_screenshots(self) -> bool:
        """
        Get whether to save screenshots.
        
        Returns:
            Whether to save screenshots
        """
        return self.save_screenshots_check.isChecked()
        
    def get_ocr_enabled(self) -> bool:
        """
        Get whether OCR is enabled.
        
        Returns:
            Whether OCR is enabled
        """
        return self.ocr_enabled_check.isChecked()
        
    def get_ocr_frequency(self) -> float:
        """
        Get the OCR update frequency.
        
        Returns:
            OCR update frequency in Hz
        """
        return self.ocr_freq_spin.value() 