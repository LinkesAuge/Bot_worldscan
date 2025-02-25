"""
Capture Preview Widget

This module provides the CapturePreviewWidget for displaying captured frames
in the Qt-based window capture implementation.
"""

import logging
import os
import time
from typing import Optional

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy, QCheckBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt6.QtMultimediaWidgets import QVideoWidget

from scout.ui.utils.language_manager import tr
from scout.core.window.capture_session import CaptureSession
from scout.core.window.image_utils import qimage_to_numpy, resize_image

# Set up logging
logger = logging.getLogger(__name__)


class CapturePreviewWidget(QWidget):
    """
    Widget for displaying captured frames from windows or screens.
    
    This widget uses a QVideoWidget to display real-time captures from the
    selected window or screen. It also provides controls for taking screenshots
    and enabling/disabling auto-screenshot mode.
    """
    
    # Signals
    screenshot_captured = pyqtSignal(QImage)  # Emitted when a screenshot is captured
    frame_captured = pyqtSignal(QImage)       # Emitted when a frame is captured (for detection)
    
    def __init__(self, parent=None):
        """
        Initialize the capture preview widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize state
        self._capture_session = None
        self._is_auto_screenshot = False
        self._current_frame = None
        self._frame_count = 0
        self._fps = 0
        self._last_fps_update = time.time()
        self._screenshots_dir = self._get_screenshots_dir()
        
        # Create UI components
        self._create_ui()
        
        # Start FPS counter
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)  # Update every second
        
        logger.info("Capture preview widget initialized")
    
    def _create_ui(self):
        """Create the user interface."""
        # Set layout
        layout = QVBoxLayout(self)
        
        # Create video widget for display
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.video_widget)
        
        # Create overlay label for status information
        self.overlay_label = QLabel()
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.overlay_label.setStyleSheet("color: yellow; background-color: rgba(0, 0, 0, 128); padding: 5px;")
        self.overlay_label.setText("No Capture Active")
        
        # Create controls layout
        controls_layout = QHBoxLayout()
        
        # Create screenshot button
        self.screenshot_button = QPushButton(tr("Take Screenshot"))
        self.screenshot_button.clicked.connect(self._take_screenshot)
        self.screenshot_button.setEnabled(False)
        controls_layout.addWidget(self.screenshot_button)
        
        # Create auto screenshot checkbox
        self.auto_screenshot_checkbox = QCheckBox(tr("Auto Screenshot"))
        self.auto_screenshot_checkbox.toggled.connect(self._toggle_auto_screenshot)
        self.auto_screenshot_checkbox.setEnabled(False)
        controls_layout.addWidget(self.auto_screenshot_checkbox)
        
        # Add FPS label
        self.fps_label = QLabel(tr("0 FPS"))
        controls_layout.addWidget(self.fps_label)
        
        # Add stretch to push controls to the left
        controls_layout.addStretch()
        
        # Add controls to main layout
        layout.addLayout(controls_layout)
        
        # Install event filter to handle resize events for the overlay label
        self.video_widget.installEventFilter(self)
    
    def set_capture_session(self, session: CaptureSession):
        """
        Set the capture session for preview.
        
        Args:
            session: Capture session to use
        """
        if not session:
            logger.warning("Null capture session provided")
            return
            
        # Store reference to the session
        self._capture_session = session
        
        # Set video output
        session.set_video_output(self.video_widget)
        
        # Connect to frame ready signal
        session.frame_ready.connect(self._on_frame_ready)
        
        # Connect to error signal
        session.error_occurred.connect(self._on_capture_error)
        
        # Enable controls
        self.screenshot_button.setEnabled(True)
        self.auto_screenshot_checkbox.setEnabled(True)
        
        logger.info("Capture session set for preview")
    
    def _get_screenshots_dir(self) -> str:
        """
        Get the directory for saving screenshots.
        
        Returns:
            str: Path to screenshots directory
        """
        # Create screenshots directory in user documents
        screenshots_dir = os.path.join(os.path.expanduser("~"), "Documents", "Scout", "Screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        logger.debug(f"Screenshots directory: {screenshots_dir}")
        return screenshots_dir
    
    def _take_screenshot(self):
        """Take a screenshot of the current frame."""
        if not self._capture_session or not self._capture_session.is_active():
            logger.warning("Cannot take screenshot: No active capture session")
            return
            
        # Take screenshot using the capture session
        screenshot = self._capture_session.take_screenshot()
        
        if screenshot and not screenshot.isNull():
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            default_path = os.path.join(self._screenshots_dir, f"screenshot-{timestamp}.png")
            
            # Open save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                tr("Save Screenshot"),
                default_path,
                tr("PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)")
            )
            
            if file_path:
                # Save the screenshot
                if screenshot.save(file_path):
                    logger.info(f"Screenshot saved to {file_path}")
                    
                    # Emit signal
                    self.screenshot_captured.emit(screenshot)
                else:
                    logger.error(f"Failed to save screenshot to {file_path}")
        else:
            logger.warning("Failed to take screenshot: No valid frame")
    
    def _toggle_auto_screenshot(self, enabled: bool):
        """
        Toggle automatic screenshot mode.
        
        Args:
            enabled: Whether to enable auto screenshot mode
        """
        self._is_auto_screenshot = enabled
        logger.info(f"Auto screenshot mode {'enabled' if enabled else 'disabled'}")
        
        # When disabled, clear the current frame to stop sending
        if not enabled:
            self._current_frame = None
    
    def _on_frame_ready(self, frame: QImage):
        """
        Handle new frame from capture session.
        
        Args:
            frame: New frame as QImage
        """
        if frame.isNull():
            return
            
        # Store the current frame
        self._current_frame = frame
        
        # Increment frame counter for FPS calculation
        self._frame_count += 1
        
        # Resize image if it's large
        resized_frame = resize_image(frame, 1280, 720)
        
        # If auto screenshot is enabled, emit the frame for detection
        if self._is_auto_screenshot:
            self.frame_captured.emit(resized_frame)
    
    def _update_fps(self):
        """Update FPS counter."""
        # Calculate FPS
        current_time = time.time()
        elapsed = current_time - self._last_fps_update
        
        if elapsed > 0:
            self._fps = self._frame_count / elapsed
            
        # Reset counter
        self._frame_count = 0
        self._last_fps_update = current_time
        
        # Update label
        self.fps_label.setText(f"{self._fps:.1f} FPS")
        
        # Update overlay label
        if self._capture_session and self._capture_session.is_active():
            if self._current_frame:
                width = self._current_frame.width()
                height = self._current_frame.height()
                self.overlay_label.setText(f"Capture Active: {width}x{height} @ {self._fps:.1f} FPS")
            else:
                self.overlay_label.setText(f"Capture Active: {self._fps:.1f} FPS")
        else:
            self.overlay_label.setText("No Capture Active")
    
    def _on_capture_error(self, error_msg: str):
        """
        Handle capture error.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Capture error: {error_msg}")
        
        # Update overlay label
        self.overlay_label.setText(f"Error: {error_msg}")
        self.overlay_label.setStyleSheet("color: red; background-color: rgba(0, 0, 0, 128); padding: 5px;")
    
    def eventFilter(self, obj, event):
        """
        Handle widget events.
        
        Args:
            obj: Object that triggered the event
            event: Event to handle
            
        Returns:
            bool: True if event was handled, False otherwise
        """
        if obj == self.video_widget and event.type() == event.Type.Resize:
            # Update overlay label position to stay at the top-right corner
            self.overlay_label.setParent(self.video_widget)
            self.overlay_label.move(
                self.video_widget.width() - self.overlay_label.width() - 10,
                10
            )
            
        return super().eventFilter(obj, event)
    
    def get_current_frame(self) -> Optional[QImage]:
        """
        Get the current frame.
        
        Returns:
            Optional[QImage]: Current frame, or None if no frame is available
        """
        return self._current_frame
    
    def get_current_frame_as_numpy(self):
        """
        Get the current frame as a numpy array.
        
        Returns:
            Optional[np.ndarray]: Current frame as a numpy array, or None if no frame
        """
        if self._current_frame is None:
            return None
            
        return qimage_to_numpy(self._current_frame) 