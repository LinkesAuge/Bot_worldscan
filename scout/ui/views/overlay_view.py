"""
Overlay View

This module provides a transparent overlay window that can be positioned 
over the game window to display real-time visualization of detection results,
automation targets, and game state information.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsLineItem, QStyleOptionGraphicsItem,
    QSlider, QApplication
)
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QFont, QPainter, QPainterPath, 
    QPolygonF, QTransform, QIcon, QPixmap
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QSizeF, QRect, QPoint, QTimer, 
    pyqtSignal, QPropertyAnimation, QEasingCurve
)

from scout.core.window.window_service_interface import WindowServiceInterface
from scout.core.detection.detection_service_interface import DetectionServiceInterface

# Set up logging
logger = logging.getLogger(__name__)

class VisualizationStyle:
    """
    Visualization style constants and utilities.
    
    This class provides predefined styles for different visualization types
    and helper methods for creating pens, brushes, and other visual elements.
    """
    
    # Color schemes
    DETECTION_COLOR = QColor(0, 255, 0, 128)      # Green semi-transparent
    MATCH_COLOR = QColor(255, 165, 0, 160)        # Orange semi-transparent
    AUTOMATION_COLOR = QColor(0, 120, 255, 160)   # Blue semi-transparent
    ERROR_COLOR = QColor(255, 0, 0, 160)          # Red semi-transparent
    INFO_COLOR = QColor(255, 255, 255, 200)       # White semi-transparent
    
    # Strategy-specific colors
    TEMPLATE_COLOR = QColor(0, 200, 100, 160)     # Green-blue for template matching
    OCR_COLOR = QColor(200, 100, 0, 160)          # Orange-red for OCR
    YOLO_COLOR = QColor(100, 0, 200, 160)         # Purple for YOLO
    
    # Line styles
    DETECTION_PEN = QPen(DETECTION_COLOR, 2, Qt.PenStyle.SolidLine)
    MATCH_PEN = QPen(MATCH_COLOR, 2, Qt.PenStyle.SolidLine)
    AUTOMATION_PEN = QPen(AUTOMATION_COLOR, 2, Qt.PenStyle.DashLine)
    ERROR_PEN = QPen(ERROR_COLOR, 2, Qt.PenStyle.DashDotLine)
    
    # Strategy-specific pens
    TEMPLATE_PEN = QPen(TEMPLATE_COLOR, 2, Qt.PenStyle.SolidLine)
    OCR_PEN = QPen(OCR_COLOR, 2, Qt.PenStyle.SolidLine)
    YOLO_PEN = QPen(YOLO_COLOR, 2, Qt.PenStyle.SolidLine)
    
    # Fill styles
    DETECTION_BRUSH = QBrush(QColor(0, 255, 0, 40))  # Very transparent green
    MATCH_BRUSH = QBrush(QColor(255, 165, 0, 40))    # Very transparent orange
    AUTOMATION_BRUSH = QBrush(QColor(0, 120, 255, 40))  # Very transparent blue
    
    # Strategy-specific brushes
    TEMPLATE_BRUSH = QBrush(QColor(0, 200, 100, 40))
    OCR_BRUSH = QBrush(QColor(200, 100, 0, 40))
    YOLO_BRUSH = QBrush(QColor(100, 0, 200, 40))
    
    # Text styles
    LABEL_FONT = QFont("Arial", 10, QFont.Weight.Bold)
    INFO_FONT = QFont("Arial", 12)
    
    @staticmethod
    def get_confidence_color(confidence: float) -> QColor:
        """
        Get color based on confidence level.
        
        Args:
            confidence: Confidence value (0.0 to 1.0)
            
        Returns:
            QColor representing the confidence level (red->yellow->green)
        """
        if confidence < 0 or confidence > 1:
            return QColor(200, 200, 200, 160)  # Gray for invalid values
            
        if confidence < 0.5:
            # Red (255,0,0) to Yellow (255,255,0)
            return QColor(255, int(confidence * 2 * 255), 0, 160)
        else:
            # Yellow (255,255,0) to Green (0,255,0)
            return QColor(int(255 * (1 - confidence) * 2), 255, 0, 160)
    
    @staticmethod
    def get_strategy_color(strategy: str) -> QColor:
        """
        Get color based on detection strategy.
        
        Args:
            strategy: Detection strategy name ('template', 'ocr', 'yolo')
            
        Returns:
            QColor representing the strategy
        """
        strategy_lower = strategy.lower()
        if strategy_lower == 'template':
            return VisualizationStyle.TEMPLATE_COLOR
        elif strategy_lower == 'ocr':
            return VisualizationStyle.OCR_COLOR
        elif strategy_lower == 'yolo':
            return VisualizationStyle.YOLO_COLOR
        else:
            return VisualizationStyle.DETECTION_COLOR
    
    @staticmethod
    def get_strategy_pen(strategy: str) -> QPen:
        """
        Get pen based on detection strategy.
        
        Args:
            strategy: Detection strategy name ('template', 'ocr', 'yolo')
            
        Returns:
            QPen for the specified strategy
        """
        strategy_lower = strategy.lower()
        if strategy_lower == 'template':
            return VisualizationStyle.TEMPLATE_PEN
        elif strategy_lower == 'ocr':
            return VisualizationStyle.OCR_PEN
        elif strategy_lower == 'yolo':
            return VisualizationStyle.YOLO_PEN
        else:
            return VisualizationStyle.DETECTION_PEN
    
    @staticmethod
    def get_strategy_brush(strategy: str) -> QBrush:
        """
        Get brush based on detection strategy.
        
        Args:
            strategy: Detection strategy name ('template', 'ocr', 'yolo')
            
        Returns:
            QBrush for the specified strategy
        """
        strategy_lower = strategy.lower()
        if strategy_lower == 'template':
            return VisualizationStyle.TEMPLATE_BRUSH
        elif strategy_lower == 'ocr':
            return VisualizationStyle.OCR_BRUSH
        elif strategy_lower == 'yolo':
            return VisualizationStyle.YOLO_BRUSH
        else:
            return VisualizationStyle.DETECTION_BRUSH

class DetectionMarker(QGraphicsRectItem):
    """
    Graphics item for visualizing a detection result.
    
    This class represents a detection result on the overlay view.
    It includes the bounding box, label, and confidence visualization.
    The appearance varies based on detection strategy and confidence.
    """
    
    def __init__(
        self, 
        x: int, 
        y: int, 
        width: int, 
        height: int, 
        label: str, 
        confidence: float,
        strategy: str = 'template',
        parent: Optional[QGraphicsRectItem] = None
    ):
        """
        Initialize a detection marker.
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of the bounding box
            height: Height of the bounding box
            label: Label text
            confidence: Confidence value (0.0 to 1.0)
            strategy: Detection strategy used ('template', 'ocr', 'yolo')
            parent: Parent graphics item
        """
        super().__init__(0, 0, width, height, parent)
        self.setPos(x, y)
        
        self.label = label
        self.confidence = confidence
        self.strategy = strategy.lower()
        self.selected = False
        
        # Set visual appearance based on strategy and confidence
        self._apply_style()
        
        # Add label text
        self._create_label()
        
        # Make item selectable and hoverable for interaction
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        # Add animation
        self._setup_animation()
    
    def _apply_style(self) -> None:
        """Apply visual style based on strategy and confidence."""
        # Get base color from strategy
        base_color = VisualizationStyle.get_strategy_color(self.strategy)
        
        # Adjust color based on confidence
        if self.confidence >= 0 and self.confidence <= 1:
            confidence_factor = 0.5 + (self.confidence * 0.5)  # Scale to 0.5-1.0 range
            color = QColor(
                int(base_color.red() * confidence_factor),
                int(base_color.green() * confidence_factor),
                int(base_color.blue() * confidence_factor),
                base_color.alpha()
            )
        else:
            color = base_color
        
        # Apply to pen and brush
        self.setPen(QPen(color, 2))
        self.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 40)))
    
    def _create_label(self) -> None:
        """Create and position the label for this marker."""
        # Create text item for label with strategy indicator
        self.text_item = QGraphicsTextItem(self)
        
        # Include strategy in the label
        strategy_prefix = f"[{self.strategy.upper()}] " if self.strategy else ""
        self.text_item.setPlainText(f"{strategy_prefix}{self.label} ({self.confidence:.2f})")
        self.text_item.setFont(VisualizationStyle.LABEL_FONT)
        
        # Set color based on strategy
        self.text_item.setDefaultTextColor(VisualizationStyle.get_strategy_color(self.strategy))
        
        # Create background for better readability
        text_rect = self.text_item.boundingRect()
        self.text_bg = QGraphicsRectItem(self)
        self.text_bg.setRect(text_rect)
        self.text_bg.setBrush(QColor(0, 0, 0, 160))
        self.text_bg.setPen(Qt.PenStyle.NoPen)
        
        # Position text at top of marker
        self.text_item.setPos(0, -text_rect.height())
        self.text_bg.setPos(0, -text_rect.height())
        
        # Ensure text is above background in z-order
        self.text_bg.setZValue(1)
        self.text_item.setZValue(2)
    
    def _setup_animation(self) -> None:
        """Set up pulsing animation for the marker."""
        self.opacity = 1.0
        self.pulse_direction = -0.02
        
        # Timer for animation
        self.timer = QTimer(self.scene())
        self.timer.timeout.connect(self._animate_pulse)
        self.timer.start(50)  # 20 fps
    
    def _animate_pulse(self) -> None:
        """Animate the marker with a subtle pulse effect."""
        self.opacity += self.pulse_direction
        
        # Reverse direction at limits
        if self.opacity <= 0.6 or self.opacity >= 1.0:
            self.pulse_direction *= -1
            
        # Apply opacity to pen
        pen = self.pen()
        color = pen.color()
        color.setAlpha(int(255 * self.opacity))
        pen.setColor(color)
        self.setPen(pen)
        
        # Apply to brush as well
        brush = self.brush()
        color = brush.color()
        color.setAlpha(int(100 * self.opacity))
        brush.setColor(color)
        self.setBrush(brush)
    
    def hoverEnterEvent(self, event):
        """
        Handle mouse hover enter events for the detection marker.
        
        Enhances the marker's visual appearance when the mouse hovers over it.
        
        Args:
            event: The hover event
        """
        # Enhance border width
        pen = self.pen()
        pen.setWidth(3)  # Thicker border on hover
        self.setPen(pen)
        
        # Make label more prominent
        self.text_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """
        Handle mouse hover leave events for the detection marker.
        
        Restores the marker's normal appearance when the mouse leaves.
        
        Args:
            event: The hover event
        """
        # Restore normal border width
        pen = self.pen()
        pen.setWidth(2)
        self.setPen(pen)
        
        # Restore normal label
        self.text_item.setFont(VisualizationStyle.LABEL_FONT)
        
        super().hoverLeaveEvent(event)
    
    def cleanup(self) -> None:
        """Clean up resources when marker is removed."""
        # Stop the animation timer
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
    
    def mousePressEvent(self, event):
        """
        Handle mouse press events.
        
        Allows the marker to be selected for interaction.
        
        Args:
            event: The mouse event
        """
        self.selected = True
        
        # Create selection indicator
        pen = self.pen()
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        
        # Pass the event to parent item handlers
        if self.scene():
            # Find parent OverlayView and emit selection signal
            view = self.scene().views()[0].parent()
            if hasattr(view, 'marker_selected'):
                result_data = {
                    'x': self.x(),
                    'y': self.y(),
                    'width': self.rect().width(),
                    'height': self.rect().height(),
                    'label': self.label,
                    'confidence': self.confidence,
                    'strategy': self.strategy
                }
                view.marker_selected.emit(result_data)
        
        super().mousePressEvent(event)

class OverlayView(QWidget):
    """
    Transparent overlay view for real-time visualization.
    
    This widget provides a transparent window that can be positioned over
    the game window to display real-time information such as:
    - Detection results (bounding boxes, labels)
    - Automation targets and actions
    - Game state information
    - Debugging information
    
    The overlay supports different visualization styles and modes.
    """
    
    # Signals
    position_updated = pyqtSignal(int, int)  # x, y
    closed = pyqtSignal()
    marker_selected = pyqtSignal(dict)  # Emitted when a marker is selected
    marker_activated = pyqtSignal(dict)  # Emitted when a marker is double-clicked
    
    def __init__(
        self, 
        window_service: WindowServiceInterface,
        detection_service: Optional[DetectionServiceInterface] = None
    ):
        """
        Initialize overlay view.
        
        Args:
            window_service: Window service for positioning and screenshots
            detection_service: Detection service for running detection operations
        """
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        # Services
        self.window_service = window_service
        self.detection_service = detection_service
        
        # State
        self._active = False
        self._last_game_rect = None
        self._markers = []
        self._visible_strategies = {'template': True, 'ocr': True, 'yolo': True}
        self._min_confidence = 0.0  # Display all results by default
        self._selected_marker = None
        
        # Performance optimization
        self._batch_size = 10  # Add markers in batches for better performance
        self._update_throttle_ms = 100  # Throttle updates to avoid overwhelming the UI
        self._last_update_time = 0
        self._pending_results = []
        self._is_updating = False
        
        # Setup UI
        self._setup_ui()
        
        # Setup timers
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._on_update_timer)
        
        self._batch_timer = QTimer(self)
        self._batch_timer.timeout.connect(self._process_pending_results)
        self._batch_timer.setSingleShot(True)
        
        # Set window properties
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.85)
        
        # Add keyboard shortcut handler
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        logger.debug("Overlay view initialized")
    
    def _setup_ui(self) -> None:
        """Set up the overlay UI components."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create graphics view for visualizations
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent;")
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        
        # Create control bar (initially hidden)
        self.control_bar = self._create_control_bar()
        self.control_bar.setVisible(False)
        
        # Create debug info label
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.info_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 120); color: white; padding: 5px;"
        )
        self.info_label.setVisible(False)
        
        # Add widgets to layout
        self.main_layout.addWidget(self.control_bar)
        self.main_layout.addWidget(self.view, 1)  # Stretches to fill space
        self.main_layout.addWidget(self.info_label)
        
        # Set transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
    
    def _create_control_bar(self) -> QWidget:
        """
        Create the overlay control bar.
        
        Returns:
            Widget containing overlay controls
        """
        control_bar = QWidget(self)
        control_bar.setMaximumHeight(40)
        control_bar.setStyleSheet(
            "background-color: rgba(40, 40, 40, 180); border-radius: 5px; margin: 5px;"
        )
        
        # Create layout
        layout = QHBoxLayout(control_bar)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # Create strategy toggle buttons
        self.template_btn = QPushButton("Template", control_bar)
        self.template_btn.setCheckable(True)
        self.template_btn.setChecked(self._visible_strategies.get('template', True))
        self.template_btn.clicked.connect(lambda checked: self.set_strategy_visibility('template', checked))
        self.template_btn.setStyleSheet(
            "QPushButton { color: white; background-color: rgba(0, 200, 100, 180); padding: 5px; border-radius: 3px; }"
            "QPushButton:checked { background-color: rgba(0, 200, 100, 255); }"
            "QPushButton:!checked { background-color: rgba(100, 100, 100, 180); }"
        )
        
        self.ocr_btn = QPushButton("OCR", control_bar)
        self.ocr_btn.setCheckable(True)
        self.ocr_btn.setChecked(self._visible_strategies.get('ocr', True))
        self.ocr_btn.clicked.connect(lambda checked: self.set_strategy_visibility('ocr', checked))
        self.ocr_btn.setStyleSheet(
            "QPushButton { color: white; background-color: rgba(200, 100, 0, 180); padding: 5px; border-radius: 3px; }"
            "QPushButton:checked { background-color: rgba(200, 100, 0, 255); }"
            "QPushButton:!checked { background-color: rgba(100, 100, 100, 180); }"
        )
        
        self.yolo_btn = QPushButton("YOLO", control_bar)
        self.yolo_btn.setCheckable(True)
        self.yolo_btn.setChecked(self._visible_strategies.get('yolo', True))
        self.yolo_btn.clicked.connect(lambda checked: self.set_strategy_visibility('yolo', checked))
        self.yolo_btn.setStyleSheet(
            "QPushButton { color: white; background-color: rgba(100, 0, 200, 180); padding: 5px; border-radius: 3px; }"
            "QPushButton:checked { background-color: rgba(100, 0, 200, 255); }"
            "QPushButton:!checked { background-color: rgba(100, 100, 100, 180); }"
        )
        
        # Create confidence slider with label
        confidence_label = QLabel("Min Confidence:", control_bar)
        confidence_label.setStyleSheet("color: white;")
        
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal, control_bar)
        self.confidence_slider.setMinimum(0)
        self.confidence_slider.setMaximum(100)
        self.confidence_slider.setValue(int(self._min_confidence * 100))
        self.confidence_slider.setFixedWidth(100)
        self.confidence_slider.valueChanged.connect(
            lambda value: self.set_min_confidence(value / 100.0)
        )
        
        self.confidence_value = QLabel(f"{self._min_confidence:.2f}", control_bar)
        self.confidence_value.setStyleSheet("color: white;")
        self.confidence_value.setFixedWidth(40)
        
        # Create toggle button for debug info
        self.debug_btn = QPushButton("Debug", control_bar)
        self.debug_btn.setCheckable(True)
        self.debug_btn.setChecked(False)
        self.debug_btn.clicked.connect(self.show_debug_info)
        self.debug_btn.setStyleSheet(
            "QPushButton { color: white; background-color: rgba(100, 100, 100, 180); padding: 5px; border-radius: 3px; }"
            "QPushButton:checked { background-color: rgba(200, 200, 0, 255); }"
            "QPushButton:!checked { background-color: rgba(100, 100, 100, 180); }"
        )
        
        # Create close button
        self.close_btn = QPushButton("×", control_bar)
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.hide_overlay)
        self.close_btn.setStyleSheet(
            "QPushButton { color: white; background-color: rgba(200, 0, 0, 180); font-size: 16px; "
            "font-weight: bold; border-radius: 15px; }"
            "QPushButton:hover { background-color: rgba(255, 0, 0, 255); }"
        )
        
        # Add controls to layout
        layout.addWidget(self.template_btn)
        layout.addWidget(self.ocr_btn)
        layout.addWidget(self.yolo_btn)
        layout.addWidget(confidence_label)
        layout.addWidget(self.confidence_slider)
        layout.addWidget(self.confidence_value)
        layout.addStretch(1)  # Take up remaining space
        layout.addWidget(self.debug_btn)
        layout.addWidget(self.close_btn)
        
        return control_bar
    
    def show_over_game(self) -> bool:
        """
        Show the overlay positioned over the game window.
        
        Returns:
            True if successful, False if game window not found
        """
        # Get game window rectangle
        game_rect = self.window_service.get_window_rect()
        if not game_rect:
            logger.warning("Cannot show overlay: Game window not found")
            return False
            
        # Store for update checks
        self._last_game_rect = game_rect
        
        # Position overlay
        self.setGeometry(game_rect)
        
        # Setup graphics view
        self.scene.setSceneRect(0, 0, game_rect.width(), game_rect.height())
        self.view.setFixedSize(game_rect.width(), game_rect.height())
        
        # Make overlay visible
        self.show()
        self.activateWindow()
        
        # Start update timer
        self._active = True
        self._update_timer.start(100)  # 10 fps
        
        logger.info(f"Overlay shown over game window at {game_rect.x()},{game_rect.y()} ({game_rect.width()}x{game_rect.height()})")
        return True
    
    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self._active = False
        self._update_timer.stop()
        self.hide()
        logger.info("Overlay hidden")
    
    def toggle_visibility(self) -> bool:
        """
        Toggle overlay visibility.
        
        Returns:
            New visibility state (True if visible)
        """
        if self._active:
            self.hide_overlay()
            return False
        else:
            return self.show_over_game()
    
    def set_detection_results(self, results: List[Dict[str, Any]], strategy: str = "template") -> None:
        """
        Display detection results on the overlay.
        
        Args:
            results: List of detection results with coordinates and metadata
            strategy: Detection strategy used (affects visualization style)
        """
        if not results:
            logger.debug(f"No detection results to display for {strategy} strategy")
            return
        
        # Add to pending results for batched processing
        self._pending_results.append((results, strategy))
        
        # Start batch processing if not already running
        if not self._is_updating and not self._batch_timer.isActive():
            self._process_pending_results()
    
    def _process_pending_results(self) -> None:
        """Process pending detection results in batches."""
        if not self._pending_results:
            self._is_updating = False
            return
            
        self._is_updating = True
        
        # Get next batch of results
        results, strategy = self._pending_results[0]
        
        # Clear existing markers for this strategy
        self.clear_markers(strategy)
        
        logger.debug(f"Processing {len(results)} {strategy} detection results")
        
        # Process a batch of results
        batch_start = 0
        while batch_start < len(results):
            # Get batch
            batch_end = min(batch_start + self._batch_size, len(results))
            batch = results[batch_start:batch_end]
            
            # Process batch
            num_added = 0
            for result in batch:
                # Check if this strategy is visible
                if not self._visible_strategies.get(strategy.lower(), True):
                    continue
                    
                # Check confidence threshold
                confidence = result.get('confidence', 0.0)
                if confidence < self._min_confidence:
                    continue
                    
                self._add_detection_marker(result, strategy)
                num_added += 1
                
            # Update batch position
            batch_start = batch_end
            
            # Yield to event loop to keep UI responsive
            QApplication.processEvents()
        
        # Remove the processed results
        self._pending_results.pop(0)
        
        logger.debug(f"Added {num_added} markers to overlay (filtered from {len(results)} results)")
        
        # If more results are pending, schedule next batch
        if self._pending_results:
            self._batch_timer.start(50)  # 50ms delay before next batch
        else:
            self._is_updating = False
    
    def optimize_performance(self) -> None:
        """
        Optimize overlay performance based on number of markers.
        
        Adjusts animation and update rates depending on the number of active markers.
        """
        marker_count = len(self._markers)
        
        # Adjust batch size based on marker count
        if marker_count < 20:
            self._batch_size = 10
        elif marker_count < 50:
            self._batch_size = 5
        else:
            self._batch_size = 3
            
        # Adjust update rate based on marker count
        if marker_count < 20:
            self._update_throttle_ms = 100  # 10 fps
        elif marker_count < 50:
            self._update_throttle_ms = 200  # 5 fps
        else:
            self._update_throttle_ms = 300  # ~3 fps
            
        # Disable animation for very large numbers of markers
        animation_enabled = marker_count < 100
        
        # Apply animation setting to markers
        for marker in self._markers:
            if isinstance(marker, DetectionMarker) and hasattr(marker, 'timer'):
                if animation_enabled:
                    if not marker.timer.isActive():
                        marker.timer.start(50)
                else:
                    marker.timer.stop()
        
        logger.debug(f"Performance optimized for {marker_count} markers: " +
                    f"batch_size={self._batch_size}, update_rate={self._update_throttle_ms}ms, " +
                    f"animation={'enabled' if animation_enabled else 'disabled'}")
    
    def _add_detection_marker(self, result: Dict[str, Any], strategy: str) -> None:
        """
        Add a detection marker to the overlay.
        
        Args:
            result: Detection result data
            strategy: Detection strategy
        """
        # Extract result data
        try:
            x = result.get('x', 0)
            y = result.get('y', 0)
            width = result.get('width', 10)
            height = result.get('height', 10)
            
            # Get label and confidence
            label = result.get('label', '')
            if not label and 'template_name' in result:
                label = result['template_name']
            
            confidence = result.get('confidence', 0.0)
            
            # Create marker
            marker = DetectionMarker(x, y, width, height, label, confidence, strategy)
            self.scene.addItem(marker)
            self._markers.append(marker)
            
        except Exception as e:
            logger.error(f"Error adding detection marker: {e}")
    
    def add_targeting_marker(self, x: int, y: int, width: int, height: int, label: str) -> None:
        """
        Add a targeting marker for automation.
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of target
            height: Height of target
            label: Label for the target
        """
        try:
            # Create rectangular marker
            rect = QGraphicsRectItem(0, 0, width, height)
            rect.setPos(x, y)
            rect.setPen(VisualizationStyle.AUTOMATION_PEN)
            rect.setBrush(VisualizationStyle.AUTOMATION_BRUSH)
            
            # Add crosshair
            center_x = width / 2
            center_y = height / 2
            
            # Horizontal line
            h_line = QGraphicsLineItem(-10 + center_x, center_y, 10 + center_x, center_y, rect)
            h_line.setPen(VisualizationStyle.AUTOMATION_PEN)
            
            # Vertical line
            v_line = QGraphicsLineItem(center_x, -10 + center_y, center_x, 10 + center_y, rect)
            v_line.setPen(VisualizationStyle.AUTOMATION_PEN)
            
            # Add label
            text = QGraphicsTextItem(rect)
            text.setPlainText(label)
            text.setDefaultTextColor(VisualizationStyle.AUTOMATION_COLOR)
            text.setFont(VisualizationStyle.LABEL_FONT)
            text.setPos(0, -text.boundingRect().height())
            
            # Add to scene
            self.scene.addItem(rect)
            self._markers.append(rect)
            
            logger.debug(f"Added targeting marker at {x},{y} for '{label}'")
            
        except Exception as e:
            logger.error(f"Error adding targeting marker: {e}")
    
    def add_info_text(self, text: str, x: int, y: int) -> None:
        """
        Add informational text to the overlay.
        
        Args:
            text: Text to display
            x: X coordinate
            y: Y coordinate
        """
        try:
            # Create text background for readability
            text_item = QGraphicsTextItem()
            text_item.setPlainText(text)
            text_item.setDefaultTextColor(VisualizationStyle.INFO_COLOR)
            text_item.setFont(VisualizationStyle.INFO_FONT)
            
            # Create background
            bg_rect = text_item.boundingRect()
            bg_item = QGraphicsRectItem(bg_rect)
            bg_item.setBrush(QColor(0, 0, 0, 120))
            bg_item.setPen(Qt.PenStyle.NoPen)
            
            # Position items
            bg_item.setPos(x, y)
            text_item.setPos(x, y)
            
            # Add to scene
            self.scene.addItem(bg_item)
            self.scene.addItem(text_item)
            
            # Add to markers for cleanup
            self._markers.append(bg_item)
            self._markers.append(text_item)
            
        except Exception as e:
            logger.error(f"Error adding info text: {e}")
    
    def clear_markers(self, strategy: Optional[str] = None) -> None:
        """
        Clear visualization markers from the overlay.
        
        Args:
            strategy: Optional detection strategy to clear only those markers
                     If None, all markers are cleared
        """
        # Cancel any pending updates for the specified strategy
        if strategy:
            self._pending_results = [(r, s) for r, s in self._pending_results if s != strategy]
        else:
            self._pending_results = []
            
        # Use the existing implementation to clear markers
        if strategy:
            # Remove only markers of the specified strategy
            markers_to_remove = [marker for marker in self._markers 
                               if isinstance(marker, DetectionMarker) and 
                               marker.strategy == strategy.lower()]
        else:
            # Remove all markers
            markers_to_remove = self._markers.copy()
            
        for marker in markers_to_remove:
            # Call cleanup if available
            if hasattr(marker, 'cleanup') and callable(marker.cleanup):
                marker.cleanup()
                
            # Remove from scene
            self.scene.removeItem(marker)
            
            # Remove from list
            if marker in self._markers:
                self._markers.remove(marker)
                
        if strategy:
            logger.debug(f"Cleared {len(markers_to_remove)} {strategy} markers from overlay")
        else:
            self._markers = []
            logger.debug("Cleared all overlay markers")
            
        # Run performance optimization after clearing markers
        self.optimize_performance()
    
    def show_debug_info(self, show: bool) -> None:
        """
        Show or hide the debug information label.
        
        Args:
            show: Whether to show debug info
        """
        self.info_label.setVisible(show)
    
    def set_debug_info(self, text: str) -> None:
        """
        Set the debug information text.
        
        Args:
            text: Debug text
        """
        self.info_label.setText(text)
    
    def _on_update_timer(self) -> None:
        """Handle update timer tick."""
        # Check if game window moved
        if self._active and self._last_game_rect:
            current_rect = self.window_service.get_window_rect()
            if current_rect and (
                current_rect.x() != self._last_game_rect.x() or 
                current_rect.y() != self._last_game_rect.y() or
                current_rect.width() != self._last_game_rect.width() or
                current_rect.height() != self._last_game_rect.height()
            ):
                # Game window moved or resized, update overlay
                self.setGeometry(current_rect)
                self.scene.setSceneRect(0, 0, current_rect.width(), current_rect.height())
                self.view.setFixedSize(current_rect.width(), current_rect.height())
                self._last_game_rect = current_rect
                self.position_updated.emit(current_rect.x(), current_rect.y())
    
    def keyPressEvent(self, event):
        """
        Handle key press events.
        
        Args:
            event: Key event
        """
        # ESC key to close overlay
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay()
            self.closed.emit()
        # Ctrl+B to toggle control bar
        elif event.key() == Qt.Key.Key_B and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_control_bar()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """
        Handle close event.
        
        Args:
            event: Close event
        """
        self._active = False
        self._update_timer.stop()
        self.closed.emit()
        super().closeEvent(event)
    
    # Configuration methods
    def set_strategy_visibility(self, strategy: str, visible: bool) -> None:
        """
        Set visibility for a detection strategy.
        
        Args:
            strategy: Detection strategy ('template', 'ocr', 'yolo')
            visible: Whether markers of this strategy should be visible
        """
        strategy_lower = strategy.lower()
        self._visible_strategies[strategy_lower] = visible
        
        # Update existing markers
        for marker in self._markers:
            if isinstance(marker, DetectionMarker) and marker.strategy == strategy_lower:
                marker.setVisible(visible)
        
        logger.debug(f"Set {strategy} visibility to {visible}")
    
    def set_min_confidence(self, min_confidence: float) -> None:
        """
        Set minimum confidence threshold for displayed detections.
        
        Args:
            min_confidence: Minimum confidence value (0.0 to 1.0)
        """
        if 0.0 <= min_confidence <= 1.0:
            self._min_confidence = min_confidence
            
            # Update slider and label if they exist
            if hasattr(self, 'confidence_slider'):
                self.confidence_slider.setValue(int(min_confidence * 100))
                
            if hasattr(self, 'confidence_value'):
                self.confidence_value.setText(f"{min_confidence:.2f}")
                
            logger.debug(f"Set minimum confidence threshold to {min_confidence}")
        else:
            logger.warning(f"Invalid confidence threshold: {min_confidence}, must be between 0.0 and 1.0")
    
    def toggle_control_bar(self) -> None:
        """Toggle the visibility of the control bar."""
        if hasattr(self, 'control_bar'):
            self.control_bar.setVisible(not self.control_bar.isVisible())
    
    def mousePressEvent(self, event):
        """
        Handle mouse press on the overlay.
        
        If no item is clicked, deselect the current marker.
        
        Args:
            event: Mouse event
        """
        # Deselect any previously selected marker if clicking on empty space
        if self._selected_marker and not self.view.itemAt(event.pos()):
            self._deselect_marker()
            
        super().mousePressEvent(event)
    
    def _deselect_marker(self):
        """Deselect the currently selected marker."""
        if self._selected_marker and self._selected_marker in self._markers:
            # Reset visual appearance
            self._selected_marker.selected = False
            pen = self._selected_marker.pen()
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            self._selected_marker.setPen(pen)
            
        self._selected_marker = None
    
    def get_marker_details(self, marker_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific marker.
        
        Args:
            marker_id: Index of the marker in the markers list
            
        Returns:
            Dictionary with marker details or None if not found
        """
        if 0 <= marker_id < len(self._markers):
            marker = self._markers[marker_id]
            if isinstance(marker, DetectionMarker):
                return {
                    'x': marker.x(),
                    'y': marker.y(),
                    'width': marker.rect().width(),
                    'height': marker.rect().height(),
                    'label': marker.label,
                    'confidence': marker.confidence,
                    'strategy': marker.strategy,
                    'center_x': marker.x() + marker.rect().width() / 2,
                    'center_y': marker.y() + marker.rect().height() / 2
                }
        return None