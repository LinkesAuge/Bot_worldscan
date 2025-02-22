"""Screen region selection widget."""

from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPaintEvent, QMouseEvent, QKeyEvent
import logging
import win32gui
import win32con
import ctypes
from ctypes.wintypes import RECT, POINT

logger = logging.getLogger(__name__)

class SelectorWidget(QWidget):
    """
    A widget for selecting a region of the screen.
    
    This widget creates a transparent overlay over the entire screen space
    and allows users to click and drag to select a rectangular region.
    It provides visual feedback during selection and confirms the selection
    with the user before finalizing.
    
    The widget handles:
    - Screen region selection via click and drag
    - Visual feedback during selection
    - DPI scaling awareness
    - Client area coordinate adjustment
    - Multi-monitor support
    
    Signals:
        region_selected: Emits a dict containing the selected region coordinates
        selection_cancelled: Emits when selection is cancelled
    """
    
    region_selected = pyqtSignal(dict)  # Emits region as dict (left, top, width, height)
    selection_cancelled = pyqtSignal()  # Emits when selection is cancelled
    
    def __init__(self, instruction_text: str = "Click and drag to select a region") -> None:
        """
        Initialize the selector widget.
        
        Args:
            instruction_text: Text to display as instructions for the user
        """
        super().__init__()
        logger.info("Initializing selector widget")
        
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
        
        # Track screen DPI scales
        self.screen_dpi_scales = {}
        for screen in QApplication.screens():
            screen_geom = screen.geometry()
            dpi_scale = screen.devicePixelRatio()
            self.screen_dpi_scales[screen] = dpi_scale
            logger.debug(f"Found screen with geometry: {screen_geom}, DPI scale: {dpi_scale}")
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
        
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle key press events.
        
        Args:
            event: Key event containing key information
        """
        if event.key() == Qt.Key.Key_Escape:
            logger.debug("Selection cancelled by Escape key")
            self.selection_cancelled.emit()
            self.close()
        else:
            super().keyPressEvent(event)
        
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Draw the selection overlay.
        
        This method handles drawing:
        - Semi-transparent background
        - Selection rectangle
        - Size information
        """
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
        """
        Handle mouse press event to start selection.
        
        Args:
            event: Mouse event containing position information
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.is_selecting = True
            logger.debug(f"Started selection at: ({event.pos().x()}, {event.pos().y()})")
            
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move event to update selection.
        
        Args:
            event: Mouse event containing position information
        """
        if self.is_selecting:
            self.current_pos = event.pos()
            logger.debug(f"Updated selection to: ({event.pos().x()}, {event.pos().y()})")
            self.update()  # Trigger repaint
            
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse release event to complete selection.
        
        This method:
        1. Calculates final selection coordinates
        2. Adjusts for DPI scaling
        3. Adjusts for client area if game window found
        4. Emits the selection result
        
        Args:
            event: Mouse event containing position information
        """
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            if self.start_pos and self.current_pos:
                # Calculate region in logical coordinates
                x1, y1 = self.start_pos.x(), self.start_pos.y()
                x2, y2 = self.current_pos.x(), self.current_pos.y()
                left = min(x1, x2)
                top = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                # Get screen info and DPI scale
                screen = QApplication.screenAt(event.pos())
                if not screen:
                    logger.warning("Could not determine screen for selection")
                    screen = QApplication.primaryScreen()
                
                dpi_scale = screen.devicePixelRatio()
                logger.debug(f"Selection on screen with DPI scale: {dpi_scale}")
                
                # Get screen geometry
                screen_geom = screen.geometry()
                logger.debug(f"Screen geometry: {screen_geom}")
                
                # Get window handle and client area
                def find_game_window(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if "Total Battle" in title:
                            game_windows.append(hwnd)
                    return True
                
                game_windows = []
                win32gui.EnumWindows(find_game_window, None)
                
                if not game_windows:
                    logger.warning("Could not find game window, using raw coordinates")
                    hwnd = None
                else:
                    hwnd = game_windows[0]
                    logger.debug(f"Found game window: {win32gui.GetWindowText(hwnd)}")
                
                # Convert to physical pixels first
                physical_left = int(left * dpi_scale)
                physical_top = int(top * dpi_scale)
                physical_width = int(width * dpi_scale)
                physical_height = int(height * dpi_scale)
                
                # If we found the game window, adjust for client area
                if hwnd:
                    try:
                        # Get window rect
                        window_rect = win32gui.GetWindowRect(hwnd)
                        
                        # Get client rect
                        client_rect = RECT()
                        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
                        
                        # Get client area position
                        client_point = POINT(0, 0)
                        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(client_point))
                        
                        # Calculate client area offset
                        client_offset_x = client_point.x - window_rect[0]
                        client_offset_y = client_point.y - window_rect[1]
                        
                        logger.debug(f"Window rect: {window_rect}")
                        logger.debug(f"Client point: ({client_point.x}, {client_point.y})")
                        logger.debug(f"Client offset: ({client_offset_x}, {client_offset_y})")
                        
                        # Adjust physical coordinates for client area
                        physical_left -= int(client_offset_x * dpi_scale)
                        physical_top -= int(client_offset_y * dpi_scale)
                        
                        logger.debug("Adjusted coordinates for client area")
                    except Exception as e:
                        logger.error(f"Error adjusting for client area: {e}")
                
                logger.debug(f"Coordinate conversion:")
                logger.debug(f"Original coords: ({x1}, {y1}) -> ({x2}, {y2})")
                logger.debug(f"Final physical coords: ({physical_left}, {physical_top}) {physical_width}x{physical_height}")
                
                region = {
                    'left': physical_left,
                    'top': physical_top,
                    'width': physical_width,
                    'height': physical_height,
                    'dpi_scale': dpi_scale,
                    'logical_coords': {
                        'left': left,
                        'top': top,
                        'width': width,
                        'height': height
                    }
                }
                
                logger.info(f"Selection completed: Physical={region}, Logical={region['logical_coords']}")
                
                # Emit the region
                self.region_selected.emit(region)
            else:
                logger.warning("Invalid selection - missing start or end position")
                self.selection_cancelled.emit()
            self.close()
        elif event.button() == Qt.MouseButton.RightButton:
            logger.info("Selection cancelled by right click")
            self.selection_cancelled.emit()
            self.close() 