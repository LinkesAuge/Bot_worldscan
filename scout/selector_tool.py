from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPaintEvent, QMouseEvent
import logging

logger = logging.getLogger(__name__)

class SelectorTool(QWidget):
    """
    A widget for selecting a region of the screen.
    
    This tool creates a transparent overlay over the entire screen space
    and allows users to click and drag to select a rectangular region.
    It provides visual feedback during selection and confirms the selection
    with the user before finalizing.
    
    Signals:
        region_selected: Emits a dict containing the selected region coordinates
        selection_cancelled: Emits when selection is cancelled
    """
    
    region_selected = pyqtSignal(dict)  # Emits region as dict (left, top, width, height)
    selection_cancelled = pyqtSignal()  # Emits when selection is cancelled
    
    def __init__(self, instruction_text: str = "Click and drag to select a region") -> None:
        """
        Initialize the selector tool.
        
        Args:
            instruction_text: Text to display as instructions for the user
        """
        super().__init__()
        logger.info("Initializing selector tool")
        
        # Set window flags for a fullscreen overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Initialize selection variables
        self.start_pos = None
        self.current_pos = None
        self.is_selecting = False
        
        # Get the geometry that covers all screens
        total_rect = QApplication.primaryScreen().virtualGeometry()
        logger.debug(f"Primary screen geometry: {total_rect}")
        
        for screen in QApplication.screens():
            screen_geom = screen.geometry()
            logger.debug(f"Found screen with geometry: {screen_geom}")
            total_rect = total_rect.united(screen_geom)
        
        logger.debug(f"Setting selector to cover all screens: {total_rect}")
        self.setGeometry(total_rect)
        
        # Add instruction label
        self.instruction_label = QLabel(instruction_text, self)
        self.instruction_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                padding: 10px;
                border-radius: 5px;
            }
        """)
        self.instruction_label.adjustSize()
        self.instruction_label.move(20, 20)
        logger.debug("Instruction label created and positioned")
        
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the selection overlay."""
        painter = QPainter(self)
        
        # Draw semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))  # Almost transparent black
        
        if self.is_selecting and self.start_pos and self.current_pos:
            # Draw selection rectangle
            painter.setPen(QPen(QColor(0, 255, 0), 2))  # Green border
            color = QColor(0, 255, 0, 50)  # Green with 50/255 alpha
            painter.setBrush(QBrush(color))
            
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            painter.drawRect(x, y, width, height)
            
            # Draw size info
            size_text = f"{width}x{height}"
            painter.setPen(QPen(QColor(255, 255, 255)))  # White text
            painter.drawText(x + 5, y - 5, size_text)
            logger.debug(f"Drawing selection rectangle: pos=({x}, {y}), size={width}x{height}")
            
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.is_selecting = True
            logger.debug(f"Started selection at position: ({self.start_pos.x()}, {self.start_pos.y()})")
            
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement to update selection."""
        if self.is_selecting:
            self.current_pos = event.pos()
            # Log every 10 pixels moved to avoid spam
            if self.current_pos.x() % 10 == 0 and self.current_pos.y() % 10 == 0:
                logger.debug(f"Selection updated to: ({self.current_pos.x()}, {self.current_pos.y()})")
            self.update()
            
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to finish selection."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            
            # If mouse was released without moving, use the start position
            if self.current_pos is None:
                self.current_pos = self.start_pos
                logger.debug("Using start position as no movement detected")
            
            try:
                # Calculate region
                x = min(self.start_pos.x(), self.current_pos.x())
                y = min(self.start_pos.y(), self.current_pos.y())
                width = abs(self.current_pos.x() - self.start_pos.x())
                height = abs(self.current_pos.y() - self.start_pos.y())
                
                # Ensure minimum size
                if width < 10 or height < 10:
                    logger.warning(f"Selection too small (width={width}, height={height}), ignoring")
                    # Reset and show selector again
                    self.start_pos = None
                    self.current_pos = None
                    self.is_selecting = False
                    QTimer.singleShot(100, self.show)
                    QTimer.singleShot(100, self.update)
                    return
                
                region = {
                    'left': x,
                    'top': y,
                    'width': width,
                    'height': height
                }
                
                logger.info(f"Selection completed: {region}")
                
                # Hide the selector window before showing dialog
                self.hide()
                
                # Show confirmation dialog
                msg = QMessageBox()
                msg.setWindowTitle("Confirm Selection")
                msg.setText(f"Use this region?\nPosition: ({x}, {y})\nSize: {width}x{height}")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
                
                result = msg.exec()
                if result == QMessageBox.StandardButton.Yes:
                    logger.info("Selection confirmed by user")
                    self.region_selected.emit(region)
                    self.close()
                else:
                    logger.info("Selection cancelled by user")
                    self.selection_cancelled.emit()
                    self.close()
                    
            except Exception as e:
                logger.error(f"Error during selection: {e}", exc_info=True)
                self.selection_cancelled.emit()
                self.close() 