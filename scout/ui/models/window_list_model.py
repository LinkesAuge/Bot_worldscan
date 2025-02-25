"""
Window List Model

This module provides the WindowListModel class, which is a model for displaying
available windows in a list view for the Qt-based window capture implementation.
"""

import logging
from typing import Optional, List

from PyQt6.QtCore import QAbstractListModel, Qt, QModelIndex
from PyQt6.QtMultimedia import QWindowCapture, QCapturableWindow

# Set up logging
logger = logging.getLogger(__name__)


class WindowListModel(QAbstractListModel):
    """
    List model for displaying available windows that can be captured.
    
    This model provides a list of available windows that can be selected
    for capturing using QWindowCapture. It is used in the window selection UI.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the window list model.
        
        Args:
            parent: Parent QObject for memory management
        """
        super().__init__(parent)
        self._windows: List[QCapturableWindow] = []
        self.populate()
        
        logger.info("Window list model initialized")
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """
        Get the number of rows in the model.
        
        Args:
            parent: Parent model index
            
        Returns:
            int: Number of windows in the list
        """
        return len(self._windows)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Optional[str]:
        """
        Get data for the specified index and role.
        
        Args:
            index: Index to get data for
            role: Data role (e.g., display role, decoration role)
            
        Returns:
            Optional[str]: Window description for display role, or None for other roles
        """
        if not index.isValid() or index.row() >= len(self._windows):
            return None
            
        window = self._windows[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Return window description for display
            return window.description()
        elif role == Qt.ItemDataRole.ToolTipRole:
            # Return window native ID as tooltip for debugging
            return f"Window ID: {window.nativeId()}"
            
        return None
    
    def window(self, index: QModelIndex) -> Optional[QCapturableWindow]:
        """
        Get the window at the specified index.
        
        Args:
            index: Index to get window for
            
        Returns:
            Optional[QCapturableWindow]: Window at the specified index, or None if invalid
        """
        if not index.isValid() or index.row() >= len(self._windows):
            return None
            
        return self._windows[index.row()]
    
    def populate(self) -> None:
        """
        Refresh the list of available windows.
        
        This method updates the model with the current list of available 
        windows from QWindowCapture.
        """
        logger.debug("Refreshing window list")
        
        try:
            # Notify views that we're about to change data
            self.beginResetModel()
            
            # Get the list of capturable windows
            self._windows = QWindowCapture.capturableWindows()
            
            # Filter out empty/invalid windows
            self._windows = [w for w in self._windows if w.isValid() and w.description()]
            
            # Sort windows by description for easier browsing
            self._windows.sort(key=lambda w: w.description() or "")
            
            # Finish model reset
            self.endResetModel()
            
            logger.info(f"Window list updated with {len(self._windows)} windows")
            
        except Exception as e:
            logger.error(f"Error populating window list: {e}")
    
    def get_window_by_title(self, title: str) -> Optional[QCapturableWindow]:
        """
        Find a window by its title or description.
        
        Args:
            title: Window title or part of description to search for
            
        Returns:
            Optional[QCapturableWindow]: Matching window or None if not found
        """
        title_lower = title.lower()
        
        for window in self._windows:
            description = window.description() or ""
            if title_lower in description.lower():
                logger.debug(f"Found window matching '{title}': {description}")
                return window
                
        logger.warning(f"No window found matching '{title}'")
        return None 