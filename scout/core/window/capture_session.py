"""
Capture Session

This module provides the CaptureSession class for managing media capture sessions
in the Qt-based window capture implementation.
"""

import logging
from typing import Optional, Union

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage, QScreen
from PyQt6.QtMultimedia import (QCapturableWindow, QMediaCaptureSession,
                               QScreenCapture, QWindowCapture, QImageCapture)
from PyQt6.QtMultimediaWidgets import QVideoWidget

from .source_type import SourceType

# Set up logging
logger = logging.getLogger(__name__)


class CaptureSession(QObject):
    """
    Manager for media capture sessions.
    
    This class manages the capture process for different sources (windows or screens)
    using Qt's media capture API. It provides a unified interface for capturing frames
    from both windows and screens, as well as handling errors and events.
    """
    
    # Signals for session events
    frame_ready = pyqtSignal(QImage)  # Emitted when a new frame is ready
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    source_changed = pyqtSignal(object, SourceType)  # Emitted when source changes (source, type)
    
    def __init__(self, parent=None):
        """
        Initialize the capture session.
        
        Args:
            parent: Parent QObject for memory management
        """
        super().__init__(parent)
        
        # Create capture objects
        self._window_capture = QWindowCapture(self)
        self._screen_capture = QScreenCapture(self)
        self._media_session = QMediaCaptureSession(self)
        
        # Current source information
        self._current_source_type = None
        self._current_source = None
        self._is_active = False
        
        # Connect error signals
        self._window_capture.errorOccurred.connect(self._on_window_error)
        self._screen_capture.errorOccurred.connect(self._on_screen_error)
        
        # Initialize video sink for frame access
        self._video_widget = None
        
        logger.info("Capture session initialized")
    
    def set_capture_source(self, source_type: SourceType, 
                          source: Union[QCapturableWindow, QScreen]) -> bool:
        """
        Set the source for capture (window or screen).
        
        Args:
            source_type: Type of source (Window or Screen)
            source: The source object (QCapturableWindow or QScreen)
            
        Returns:
            bool: True if source was set successfully, False otherwise
        """
        # Validate input
        if source_type == SourceType.Window and not isinstance(source, QCapturableWindow):
            logger.error("Invalid source for window capture")
            self.error_occurred.emit("Invalid source for window capture")
            return False
            
        if source_type == SourceType.Screen and not isinstance(source, QScreen):
            logger.error("Invalid source for screen capture")
            self.error_occurred.emit("Invalid source for screen capture")
            return False
        
        # Store source information
        self._current_source_type = source_type
        self._current_source = source
        
        # Stop current capture if active
        was_active = self._is_active
        if was_active:
            self.stop()
        
        try:
            # Configure media session based on source type
            if source_type == SourceType.Window:
                logger.info(f"Setting window capture source: {source.description()}")
                self._window_capture.setWindow(source)
                self._media_session.setWindowCapture(self._window_capture)
                self._screen_capture.setActive(False)
            elif source_type == SourceType.Screen:
                logger.info(f"Setting screen capture source: {source.name()}")
                self._screen_capture.setScreen(source)
                self._media_session.setScreenCapture(self._screen_capture)
                self._window_capture.setActive(False)
                
            # Emit signal for source change
            self.source_changed.emit(source, source_type)
            
            # Restart if it was active before
            if was_active:
                return self.start()
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting capture source: {e}")
            self.error_occurred.emit(f"Error setting capture source: {str(e)}")
            return False
    
    def start(self) -> bool:
        """
        Start the capture session.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self._is_active:
            logger.debug("Capture already active, stopping first")
            self.stop()
            
        if not self._current_source_type or not self._current_source:
            logger.error("Cannot start capture: No source set")
            self.error_occurred.emit("Cannot start capture: No source set")
            return False
            
        try:
            logger.info(f"Starting {self._current_source_type.name} capture")
            
            if self._current_source_type == SourceType.Window:
                # Check if window is still valid
                if not self._current_source.isValid():
                    logger.error("Cannot start capture: Window is no longer valid")
                    self.error_occurred.emit("Cannot start capture: Window is no longer valid")
                    return False
                
                # Start window capture
                self._window_capture.setActive(True)
                self._is_active = self._window_capture.isActive()
                
            elif self._current_source_type == SourceType.Screen:
                # Start screen capture
                self._screen_capture.setActive(True)
                self._is_active = self._screen_capture.isActive()
                
            logger.info(f"Capture started: {self._is_active}")
            return self._is_active
            
        except Exception as e:
            logger.error(f"Error starting capture: {e}")
            self.error_occurred.emit(f"Error starting capture: {str(e)}")
            return False
    
    def stop(self) -> None:
        """Stop the capture session."""
        try:
            logger.info("Stopping capture")
            
            # Stop both capture types to be safe
            self._window_capture.setActive(False)
            self._screen_capture.setActive(False)
            
            self._is_active = False
            
        except Exception as e:
            logger.error(f"Error stopping capture: {e}")
            self.error_occurred.emit(f"Error stopping capture: {str(e)}")
    
    def is_active(self) -> bool:
        """
        Check if capture is currently active.
        
        Returns:
            bool: True if capture is active, False otherwise
        """
        return self._is_active
    
    def take_screenshot(self) -> Optional[QImage]:
        """
        Take a screenshot of the current source.
        
        Returns:
            Optional[QImage]: Screenshot as QImage, or None if failed
        """
        if not self._is_active:
            logger.warning("Cannot take screenshot: Capture not active")
            return None
            
        if not self._video_widget or not self._video_widget.videoSink():
            logger.warning("Cannot take screenshot: No video sink available")
            return None
            
        try:
            # Get the current frame from the video sink
            video_frame = self._video_widget.videoSink().videoFrame()
            
            if not video_frame.isValid():
                logger.warning("Cannot take screenshot: Invalid video frame")
                return None
                
            # Convert to QImage
            image = video_frame.toImage()
            
            logger.debug(f"Screenshot taken: {image.width()}x{image.height()}")
            return image
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            self.error_occurred.emit(f"Error taking screenshot: {str(e)}")
            return None
    
    def set_video_output(self, video_widget: QVideoWidget) -> None:
        """
        Set video widget to display captured frames.
        
        Args:
            video_widget: QVideoWidget to display frames
        """
        if not video_widget:
            logger.warning("Invalid video widget provided")
            return
            
        try:
            logger.debug("Setting video output")
            
            # Store reference to video widget
            self._video_widget = video_widget
            
            # Set the video output
            self._media_session.setVideoOutput(video_widget)
            
            # Connect to frame signal if available
            if video_widget.videoSink():
                video_widget.videoSink().videoFrameChanged.connect(self._on_frame_changed)
                logger.debug("Connected to video frame signals")
                
        except Exception as e:
            logger.error(f"Error setting video output: {e}")
            self.error_occurred.emit(f"Error setting video output: {str(e)}")
    
    def _on_frame_changed(self) -> None:
        """Handle new video frame from the sink."""
        if not self._video_widget or not self._video_widget.videoSink():
            return
            
        try:
            # Get the current frame
            video_frame = self._video_widget.videoSink().videoFrame()
            
            if video_frame.isValid():
                # Convert to QImage
                image = video_frame.toImage()
                
                # Emit signal with the frame
                self.frame_ready.emit(image)
                
        except Exception as e:
            logger.error(f"Error handling frame change: {e}")
    
    def _on_window_error(self, error: QWindowCapture.Error, error_string: str) -> None:
        """
        Handle window capture errors.
        
        Args:
            error: Error code
            error_string: Error description
        """
        logger.error(f"Window capture error ({error}): {error_string}")
        self.error_occurred.emit(f"Window capture error: {error_string}")
        
        # Auto-stop on critical errors
        if error in [QWindowCapture.Error.AccessDenied, QWindowCapture.Error.CaptureFailed]:
            logger.warning("Critical window capture error, stopping capture")
            self.stop()
    
    def _on_screen_error(self, error: QScreenCapture.Error, error_string: str) -> None:
        """
        Handle screen capture errors.
        
        Args:
            error: Error code
            error_string: Error description
        """
        logger.error(f"Screen capture error ({error}): {error_string}")
        self.error_occurred.emit(f"Screen capture error: {error_string}")
        
        # Auto-stop on critical errors
        if error in [QScreenCapture.Error.AccessDenied, QScreenCapture.Error.CaptureFailed]:
            logger.warning("Critical screen capture error, stopping capture")
            self.stop() 