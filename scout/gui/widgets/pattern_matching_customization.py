from typing import Optional, Tuple
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QPushButton,
    QColorDialog, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ...config import ConfigManager, PatternMatchingOverlayConfig

logger = logging.getLogger(__name__)

class ColorButton(QPushButton):
    """Button that opens a color picker and displays the current color."""
    
    color_changed = pyqtSignal(tuple)  # BGR color tuple
    
    def __init__(self, color: Tuple[int, int, int], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.clicked.connect(self._pick_color)
        self._update_style()
    
    def _update_style(self) -> None:
        """Update button background to show current color."""
        # Convert BGR to RGB for Qt
        r, g, b = self._color[2], self._color[1], self._color[0]
        self.setStyleSheet(f"background-color: rgb({r}, {g}, {b})")
    
    def _pick_color(self) -> None:
        """Open color picker dialog."""
        # Convert BGR to RGB for Qt
        r, g, b = self._color[2], self._color[1], self._color[0]
        color = QColorDialog.getColor(QColor(r, g, b), self)
        
        if color.isValid():
            # Convert RGB back to BGR for OpenCV
            self._color = (color.blue(), color.green(), color.red())
            self._update_style()
            self.color_changed.emit(self._color)
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Get current color in BGR format."""
        return self._color

class PatternMatchingCustomizationWidget(QWidget):
    """Widget for customizing pattern matching overlay visualization.
    
    This widget provides controls for:
    - Update rate
    - Rectangle properties (color, thickness, scale)
    - Crosshair properties (color, size, thickness)
    - Label properties (color, size, format)
    
    All changes are immediately applied and saved to configuration.
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(
        self,
        config: ConfigManager,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        
        self.config = config
        self.settings = config.get_pattern_matching_overlay_config()
        
        self._setup_ui()
        self._load_settings()
        
        logger.debug("Pattern matching customization widget initialized")
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout()
        form = QFormLayout()
        
        # Update rate
        self.update_rate = QDoubleSpinBox()
        self.update_rate.setRange(0.1, 30.0)
        self.update_rate.setSingleStep(0.1)
        self.update_rate.setValue(self.settings.update_rate)
        self.update_rate.valueChanged.connect(self._on_setting_changed)
        form.addRow("Update Rate (fps):", self.update_rate)
        
        # Rectangle settings
        self.rect_color = ColorButton(self.settings.rect_color)
        self.rect_color.color_changed.connect(self._on_setting_changed)
        form.addRow("Rectangle Color:", self.rect_color)
        
        self.rect_thickness = QSpinBox()
        self.rect_thickness.setRange(1, 10)
        self.rect_thickness.setValue(self.settings.rect_thickness)
        self.rect_thickness.valueChanged.connect(self._on_setting_changed)
        form.addRow("Rectangle Thickness:", self.rect_thickness)
        
        self.rect_scale = QDoubleSpinBox()
        self.rect_scale.setRange(0.1, 5.0)
        self.rect_scale.setSingleStep(0.1)
        self.rect_scale.setValue(self.settings.rect_scale)
        self.rect_scale.valueChanged.connect(self._on_setting_changed)
        form.addRow("Rectangle Scale:", self.rect_scale)
        
        # Crosshair settings
        self.crosshair_color = ColorButton(self.settings.crosshair_color)
        self.crosshair_color.color_changed.connect(self._on_setting_changed)
        form.addRow("Crosshair Color:", self.crosshair_color)
        
        self.crosshair_size = QSpinBox()
        self.crosshair_size.setRange(5, 100)
        self.crosshair_size.setValue(self.settings.crosshair_size)
        self.crosshair_size.valueChanged.connect(self._on_setting_changed)
        form.addRow("Crosshair Size:", self.crosshair_size)
        
        self.crosshair_thickness = QSpinBox()
        self.crosshair_thickness.setRange(1, 10)
        self.crosshair_thickness.setValue(self.settings.crosshair_thickness)
        self.crosshair_thickness.valueChanged.connect(self._on_setting_changed)
        form.addRow("Crosshair Thickness:", self.crosshair_thickness)
        
        # Label settings
        self.label_color = ColorButton(self.settings.label_color)
        self.label_color.color_changed.connect(self._on_setting_changed)
        form.addRow("Label Color:", self.label_color)
        
        self.label_size = QDoubleSpinBox()
        self.label_size.setRange(0.1, 5.0)
        self.label_size.setSingleStep(0.1)
        self.label_size.setValue(self.settings.label_size)
        self.label_size.valueChanged.connect(self._on_setting_changed)
        form.addRow("Label Size:", self.label_size)
        
        self.label_thickness = QSpinBox()
        self.label_thickness.setRange(1, 10)
        self.label_thickness.setValue(self.settings.label_thickness)
        self.label_thickness.valueChanged.connect(self._on_setting_changed)
        form.addRow("Label Thickness:", self.label_thickness)
        
        self.label_format = QLineEdit(self.settings.label_format)
        self.label_format.textChanged.connect(self._on_setting_changed)
        form.addRow("Label Format:", self.label_format)
        
        layout.addLayout(form)
        self.setLayout(layout)
    
    def _load_settings(self) -> None:
        """Load settings from config."""
        self.settings = self.config.get_pattern_matching_overlay_config()
        
        # Update UI controls
        self.update_rate.setValue(self.settings.update_rate)
        self.rect_color._color = self.settings.rect_color
        self.rect_color._update_style()
        self.rect_thickness.setValue(self.settings.rect_thickness)
        self.rect_scale.setValue(self.settings.rect_scale)
        self.crosshair_color._color = self.settings.crosshair_color
        self.crosshair_color._update_style()
        self.crosshair_size.setValue(self.settings.crosshair_size)
        self.crosshair_thickness.setValue(self.settings.crosshair_thickness)
        self.label_color._color = self.settings.label_color
        self.label_color._update_style()
        self.label_size.setValue(self.settings.label_size)
        self.label_thickness.setValue(self.settings.label_thickness)
        self.label_format.setText(self.settings.label_format)
    
    def _save_settings(self) -> None:
        """Save current settings to config."""
        settings = PatternMatchingOverlayConfig(
            update_rate=self.update_rate.value(),
            rect_color=self.rect_color.color,
            rect_thickness=self.rect_thickness.value(),
            rect_scale=self.rect_scale.value(),
            rect_min_size=self.settings.rect_min_size,
            rect_max_size=self.settings.rect_max_size,
            crosshair_color=self.crosshair_color.color,
            crosshair_size=self.crosshair_size.value(),
            crosshair_thickness=self.crosshair_thickness.value(),
            label_color=self.label_color.color,
            label_size=self.label_size.value(),
            label_thickness=self.label_thickness.value(),
            label_format=self.label_format.text()
        )
        
        # Update config
        self.config.update_section("PatternMatchingOverlay", settings.to_dict())
        self.settings = settings
        
        # Notify of changes
        self.settings_changed.emit()
        logger.debug("Pattern matching overlay settings saved")
    
    def _on_setting_changed(self, *args) -> None:
        """Handle any setting change."""
        self._save_settings() 