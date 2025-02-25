"""
Window Selector Widget

This module provides the WindowSelectorWidget for selecting windows or screens to capture
in the Qt-based window capture implementation.
"""

import logging
from typing import Optional, Callable, List

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QListView, QPushButton, QTabWidget, 
                            QSplitter, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QItemSelection, QTimer
from PyQt6.QtGui import QIcon, QScreen
from PyQt6.QtMultimedia import QCapturableWindow

from scout.ui.models.window_list_model import WindowListModel
from scout.ui.models.screen_list_model import ScreenListModel
from scout.ui.utils.language_manager import tr
from scout.core.window.source_type import SourceType

# Set up logging
logger = logging.getLogger(__name__)


class WindowSelectorWidget(QWidget):
    """
    Widget for selecting a window or screen to capture.
    
    This widget provides a tabbed interface to select either a window or screen
    for capturing using the Qt-based window capture system. It includes list views
    for both windows and screens, as well as controls for refreshing the lists and
    searching for specific windows.
    """
    
    # Signals for selection changes
    window_selected = pyqtSignal(QCapturableWindow)  # Emitted when a window is selected
    screen_selected = pyqtSignal(QScreen)           # Emitted when a screen is selected
    source_type_changed = pyqtSignal(SourceType)     # Emitted when source type changes
    
    def __init__(self, parent=None):
        """
        Initialize the window selector widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize models
        self._window_model = WindowListModel(self)
        self._screen_model = ScreenListModel(self)
        
        # Initialize state
        self._current_source_type = SourceType.Window
        self._current_window = None
        self._current_screen = None
        
        # Create UI components
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.info("Window selector widget initialized")
    
    def _create_ui(self):
        """Create the user interface."""
        # Set layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create window tab
        window_tab = QWidget()
        window_layout = QVBoxLayout(window_tab)
        
        # Add window list view
        window_layout.addWidget(QLabel(tr("Select window to capture:")))
        
        # Add search box for windows
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(tr("Search:")))
        self.window_search = QLineEdit()
        self.window_search.setPlaceholderText(tr("Enter window title..."))
        search_layout.addWidget(self.window_search)
        
        self.search_button = QPushButton(tr("Search"))
        search_layout.addWidget(self.search_button)
        window_layout.addLayout(search_layout)
        
        # Add window list
        self.window_list_view = QListView()
        self.window_list_view.setModel(self._window_model)
        self.window_list_view.setSelectionMode(QListView.SelectionMode.SingleSelection)
        window_layout.addWidget(self.window_list_view)
        
        # Add refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        self.refresh_windows_button = QPushButton(tr("Refresh Window List"))
        refresh_layout.addWidget(self.refresh_windows_button)
        window_layout.addLayout(refresh_layout)
        
        # Add to tab widget
        self.tab_widget.addTab(window_tab, tr("Window"))
        
        # Create screen tab
        screen_tab = QWidget()
        screen_layout = QVBoxLayout(screen_tab)
        
        # Add screen list view
        screen_layout.addWidget(QLabel(tr("Select screen to capture:")))
        self.screen_list_view = QListView()
        self.screen_list_view.setModel(self._screen_model)
        self.screen_list_view.setSelectionMode(QListView.SelectionMode.SingleSelection)
        screen_layout.addWidget(self.screen_list_view)
        
        # Add screen info
        screen_info_label = QLabel(tr("Available screens will update automatically when connected or disconnected."))
        screen_info_label.setWordWrap(True)
        screen_layout.addWidget(screen_info_label)
        
        # Add to tab widget
        self.tab_widget.addTab(screen_tab, tr("Screen"))
        
        # Select the first tab as default
        self.tab_widget.setCurrentIndex(0)
        
        # Select primary screen by default
        self._select_primary_screen()
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Tab widget signals
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Window list signals
        self.window_list_view.selectionModel().selectionChanged.connect(
            self._on_window_selection_changed)
        self.refresh_windows_button.clicked.connect(self._refresh_windows)
        self.window_search.returnPressed.connect(self._on_search)
        self.search_button.clicked.connect(self._on_search)
        
        # Screen list signals
        self.screen_list_view.selectionModel().selectionChanged.connect(
            self._on_screen_selection_changed)
    
    def _on_tab_changed(self, index):
        """
        Handle tab change events.
        
        Args:
            index: New tab index
        """
        if index == 0:  # Window tab
            self._current_source_type = SourceType.Window
            # If we have a selected window, emit the signal
            if self._current_window and self._current_window.isValid():
                self.window_selected.emit(self._current_window)
        else:  # Screen tab
            self._current_source_type = SourceType.Screen
            # If we have a selected screen, emit the signal
            if self._current_screen:
                self.screen_selected.emit(self._current_screen)
                
        # Emit source type changed signal
        self.source_type_changed.emit(self._current_source_type)
        
        logger.debug(f"Source type changed to: {self._current_source_type}")
    
    def _on_window_selection_changed(self, selection):
        """
        Handle window selection changes.
        
        Args:
            selection: Selected items
        """
        indexes = selection.indexes()
        if not indexes:
            logger.debug("No window selected")
            self._current_window = None
            return
            
        # Get the window from the model
        index = indexes[0]
        window = self._window_model.window(index)
        
        if not window or not window.isValid():
            logger.warning("Selected window is no longer valid")
            QMessageBox.warning(
                self,
                tr("Invalid Window"),
                tr("The selected window is no longer valid. Please refresh the list and select another window."),
                QMessageBox.StandardButton.Ok
            )
            return
            
        # Store the selected window
        self._current_window = window
        logger.info(f"Window selected: {window.description()}")
        
        # Only emit signal if we're on the window tab
        if self.tab_widget.currentIndex() == 0:
            self.window_selected.emit(window)
    
    def _on_screen_selection_changed(self, selection):
        """
        Handle screen selection changes.
        
        Args:
            selection: Selected items
        """
        indexes = selection.indexes()
        if not indexes:
            logger.debug("No screen selected")
            self._current_screen = None
            return
            
        # Get the screen from the model
        index = indexes[0]
        screen = self._screen_model.screen(index)
        
        if not screen:
            logger.warning("Selected screen is no longer valid")
            return
            
        # Store the selected screen
        self._current_screen = screen
        logger.info(f"Screen selected: {screen.name()}")
        
        # Only emit signal if we're on the screen tab
        if self.tab_widget.currentIndex() == 1:
            self.screen_selected.emit(screen)
    
    def _refresh_windows(self):
        """Refresh the window list."""
        logger.debug("Refreshing window list")
        self._window_model.populate()
        
        # If we had a selected window, try to reselect it
        if self._current_window:
            self._try_select_window(self._current_window.description())
    
    def _on_search(self):
        """Handle window search."""
        search_text = self.window_search.text().strip()
        if not search_text:
            logger.debug("Empty search, no action taken")
            return
            
        logger.debug(f"Searching for window: '{search_text}'")
        
        # Refresh the window list first to ensure we have the latest windows
        self._window_model.populate()
        
        # Try to find a matching window
        self._try_select_window(search_text)
    
    def _try_select_window(self, title):
        """
        Try to select a window by title.
        
        Args:
            title: Window title to search for
        """
        # Find the window in the model
        window = self._window_model.get_window_by_title(title)
        
        if not window:
            logger.warning(f"No window found matching '{title}'")
            return False
            
        # Find the index in the model
        for i in range(self._window_model.rowCount()):
            index = self._window_model.index(i, 0)
            if self._window_model.window(index) == window:
                # Select this index
                self.window_list_view.setCurrentIndex(index)
                return True
                
        return False
    
    def _select_primary_screen(self):
        """Select the primary screen in the screen list view."""
        primary_screen = QGuiApplication.primaryScreen()
        if not primary_screen:
            return
            
        # Find the index of the primary screen
        for i in range(self._screen_model.rowCount()):
            index = self._screen_model.index(i, 0)
            screen = self._screen_model.screen(index)
            if screen == primary_screen:
                # Select this index
                self.screen_list_view.setCurrentIndex(index)
                break
    
    def get_selected_source(self):
        """
        Get the currently selected source.
        
        Returns:
            tuple: (SourceType, source object)
        """
        if self._current_source_type == SourceType.Window:
            return (SourceType.Window, self._current_window)
        else:
            return (SourceType.Screen, self._current_screen)
    
    def select_window_by_title(self, title):
        """
        Select a window by its title.
        
        Args:
            title: Window title to search for
            
        Returns:
            bool: True if window was found and selected, False otherwise
        """
        # Switch to window tab
        self.tab_widget.setCurrentIndex(0)
        
        # Try to select the window
        return self._try_select_window(title) 