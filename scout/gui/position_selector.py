"""
Position Selector

This module provides a widget for selecting screen positions.
It handles:
- Mouse click position capture
- Visual feedback during selection
- Position validation
"""

from typing import Optional, Tuple
import logging
import win32gui
import win32con
import win32api
import ctypes

from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QLabel
from PyQt6.QtCore import Qt, QPoint, QTimer, QEvent, QObject
from PyQt6.QtGui import QCursor, QKeyEvent

from scout.window_manager import WindowManager

logger = logging.getLogger(__name__)

class InstructionLabel(QLabel):
    """Floating label for showing selection instructions."""
    
    def __init__(self, text: str):
        """Initialize the instruction label."""
        super().__init__(text)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.setWordWrap(True)
        self.setMinimumWidth(200)

class PositionSelector(QObject):
    """
    Tool for selecting screen positions.
    
    This class provides functionality to:
    - Capture mouse click positions
    - Validate positions are within game window
    - Provide visual feedback during selection
    """
    
    def __init__(self, window_manager: WindowManager, parent: Optional[QObject] = None):
        """
        Initialize the position selector.
        
        Args:
            window_manager: For getting window position and state
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.window_manager = window_manager
        self.instruction_label = None
        self.selection_active = False
        self.old_cursor = None
        
    def _set_cursor(self, cursor_type: int) -> None:
        """
        Set the cursor type.
        
        Args:
            cursor_type: Win32 cursor type constant
        """
        try:
            cursor = win32gui.LoadCursor(0, cursor_type)
            win32api.SetCursor(cursor)
        except Exception as e:
            logger.error(f"Failed to set cursor: {e}")
            
    def _get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the game window rectangle.
        
        Returns:
            Tuple of (left, top, right, bottom) or None if window not found
        """
        try:
            hwnd = self.window_manager.get_window_handle()
            if not hwnd:
                return None
                
            rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)
            
            # Get frame size
            frame_x = (rect[2] - rect[0] - client_rect[2]) // 2
            frame_y = rect[3] - rect[1] - client_rect[3] - frame_x
            
            # Return client area
            return (
                rect[0] + frame_x,
                rect[1] + frame_y,
                rect[2] - frame_x,
                rect[3] - frame_y
            )
            
        except Exception as e:
            logger.error(f"Failed to get window rect: {e}")
            return None
        
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter application events to catch Escape key."""
        if event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key.Key_Escape and self.selection_active:
                logger.info("Position selection cancelled with Escape key")
                self.selection_active = False
                return True
        return False
        
    def get_position(self, prompt: str = "Select position") -> Optional[Tuple[int, int]]:
        """
        Get a screen position from user click.
        
        Args:
            prompt: Message to show during selection
            
        Returns:
            Tuple of (x, y) screen coordinates or None if cancelled
        """
        try:
            logger.info(f"Starting position selection: {prompt}")
            
            # Set crosshair cursor
            self._set_cursor(win32con.IDC_CROSS)
            
            # Create and show instruction label
            self.instruction_label = InstructionLabel(
                f"{prompt}\n\nClick to select position\nPress Escape to cancel"
            )
            
            # Position label near cursor but not under it
            cursor_pos = QCursor.pos()
            self.instruction_label.show()
            self.instruction_label.adjustSize()
            self.instruction_label.move(
                cursor_pos.x() + 20,
                cursor_pos.y() + 20
            )
            
            # Set selection active flag
            self.selection_active = True
            
            # Install event filter
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
            
            # Wait for click
            while self.selection_active:
                # Process events
                QApplication.processEvents()
                
                # Update instruction label position to follow cursor
                if self.instruction_label:
                    cursor_pos = QCursor.pos()
                    self.instruction_label.move(
                        cursor_pos.x() + 20,
                        cursor_pos.y() + 20
                    )
                    
                # Keep cursor set (Windows might reset it)
                self._set_cursor(win32con.IDC_CROSS)
                
                # Check for left click
                if QApplication.mouseButtons() == Qt.MouseButton.LeftButton:
                    # Get cursor position
                    pos = QCursor.pos()
                    
                    # Validate position is in game window
                    window_rect = self._get_window_rect()
                    if not window_rect:
                        logger.error("Failed to get game window position")
                        return None
                        
                    left, top, right, bottom = window_rect
                    if not (left <= pos.x() <= right and top <= pos.y() <= bottom):
                        logger.warning("Selected position is outside game window")
                        # Show warning but don't block
                        label = InstructionLabel("Please select a position inside the game window")
                        label.show()
                        label.move(pos.x() + 20, pos.y() + 20)
                        QTimer.singleShot(2000, label.deleteLater)  # Hide after 2 seconds
                        continue
                        
                    # Convert to window-relative coordinates
                    x = pos.x() - left
                    y = pos.y() - top
                    
                    logger.info(f"Position selected: ({x}, {y})")
                    return (x, y)
                    
        except Exception as e:
            logger.error(f"Error during position selection: {e}")
            return None
            
        finally:
            # Clean up
            self.selection_active = False
            if self.instruction_label:
                self.instruction_label.deleteLater()
                self.instruction_label = None
            
            # Reset cursor
            self._set_cursor(win32con.IDC_ARROW)
            
            # Remove event filter
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self) 