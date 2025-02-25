"""
Screen List Model

This module provides the ScreenListModel class, which is a model for displaying
available screens in a list view for the Qt-based window capture implementation.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, Qt, QModelIndex
from PyQt6.QtGui import QGuiApplication, QScreen

# Set up logging
logger = logging.getLogger(__name__)


class ScreenListModel(QAbstractListModel):
    """
    List model for displaying available screens that can be captured.
    
    This model provides a list of available screens that can be selected
    for capturing using QScreenCapture. It automatically updates when screens
    are added or removed from the system.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the screen list model.
        
        Args:
            parent: Parent QObject for memory management
        """
        super().__init__(parent)
        
        # Connect to screen change signals
        app = QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)
            app.primaryScreenChanged.connect(self._on_screens_changed)
            
        logger.info("Screen list model initialized")
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """
        Get the number of rows in the model.
        
        Args:
            parent: Parent model index
            
        Returns:
            int: Number of screens in the list
        """
        return len(QGuiApplication.screens())
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Optional[str]:
        """
        Get data for the specified index and role.
        
        Args:
            index: Index to get data for
            role: Data role (e.g., display role, decoration role)
            
        Returns:
            Optional[str]: Screen description for display role, or None for other roles
        """
        if not index.isValid() or index.row() >= len(QGuiApplication.screens()):
            return None
            
        screen = QGuiApplication.screens()[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Format screen information for display
            size = screen.size()
            dpi = screen.logicalDotsPerInch()
            primary = " (Primary)" if screen == QGuiApplication.primaryScreen() else ""
            
            return f"{screen.name()}{primary}: {size.width()}x{size.height()}, {dpi:.0f} DPI"
            
        elif role == Qt.ItemDataRole.ToolTipRole:
            # Show more detailed information in tooltip
            geometry = screen.geometry()
            screen_info = [
                f"Name: {screen.name()}",
                f"Geometry: {geometry.x()},{geometry.y()} {geometry.width()}x{geometry.height()}",
                f"DPI: {screen.logicalDotsPerInch():.1f}",
                f"Scale Factor: {screen.devicePixelRatio():.2f}",
                f"Color Depth: {screen.depth()} bits"
            ]
            return "\n".join(screen_info)
            
        return None
    
    def screen(self, index: QModelIndex) -> Optional[QScreen]:
        """
        Get the screen at the specified index.
        
        Args:
            index: Index to get screen for
            
        Returns:
            Optional[QScreen]: Screen at the specified index, or None if invalid
        """
        if not index.isValid() or index.row() >= len(QGuiApplication.screens()):
            return None
            
        return QGuiApplication.screens()[index.row()]
    
    def _on_screens_changed(self) -> None:
        """Handle changes to the screen configuration."""
        logger.debug("Screen configuration changed")
        
        # Reset the model to update the view
        self.beginResetModel()
        self.endResetModel()
        
        screens = QGuiApplication.screens()
        logger.info(f"Screen list updated: {len(screens)} screens available")
        
        # Log screen information for debugging
        for i, screen in enumerate(screens):
            primary = " (Primary)" if screen == QGuiApplication.primaryScreen() else ""
            size = screen.size()
            dpi = screen.logicalDotsPerInch()
            logger.debug(f"Screen {i}: {screen.name()}{primary}, "
                        f"{size.width()}x{size.height()}, {dpi:.0f} DPI") 