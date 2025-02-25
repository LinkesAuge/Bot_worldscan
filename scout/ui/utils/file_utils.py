"""
File Utilities

Utility functions for file operations with platform-aware behavior,
ensuring consistent file handling across different operating systems.
"""

import os
import sys
from typing import Tuple, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QWidget
from PyQt6.QtCore import QDir, QStandardPaths


def get_open_filename(
    title: str,
    directory: str = "",
    filter_str: str = "",
    parent: Optional[QWidget] = None
) -> Tuple[str, str]:
    """
    Display an open file dialog with platform-appropriate behavior.
    
    Args:
        title: Dialog title
        directory: Starting directory, empty for default
        filter_str: File filter string (e.g. "Images (*.png *.jpg);;All Files (*)")
        parent: Parent widget, or None
        
    Returns:
        Tuple of (selected_file_path, selected_filter)
    """
    # Use appropriate default directory based on platform
    if not directory:
        directory = get_documents_directory()
    
    # Normalize directory path for the platform
    directory = str(Path(directory))
    
    # Show dialog
    return QFileDialog.getOpenFileName(
        parent,
        title,
        directory,
        filter_str
    )


def get_save_filename(
    title: str,
    directory: str = "",
    filter_str: str = "",
    default_suffix: str = "",
    parent: Optional[QWidget] = None
) -> Tuple[str, str]:
    """
    Display a save file dialog with platform-appropriate behavior.
    
    Args:
        title: Dialog title
        directory: Starting directory, empty for default
        filter_str: File filter string (e.g. "Images (*.png *.jpg);;All Files (*)")
        default_suffix: Default file extension (without dot)
        parent: Parent widget, or None
        
    Returns:
        Tuple of (selected_file_path, selected_filter)
    """
    # Use appropriate default directory based on platform
    if not directory:
        directory = get_documents_directory()
    
    # Normalize directory path for the platform
    directory = str(Path(directory))
    
    # Show dialog
    options = QFileDialog.Option.DontConfirmOverwrite
    
    dialog = QFileDialog(parent, title, directory, filter_str)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    
    if default_suffix:
        dialog.setDefaultSuffix(default_suffix)
    
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        if files:
            selected_filter = dialog.selectedNameFilter()
            return (files[0], selected_filter)
    
    return ("", "")


def get_existing_directory(
    title: str,
    directory: str = "",
    parent: Optional[QWidget] = None
) -> str:
    """
    Display a directory selection dialog with platform-appropriate behavior.
    
    Args:
        title: Dialog title
        directory: Starting directory, empty for default
        parent: Parent widget, or None
        
    Returns:
        Selected directory path, or empty string if canceled
    """
    # Use appropriate default directory based on platform
    if not directory:
        directory = get_documents_directory()
    
    # Normalize directory path for the platform
    directory = str(Path(directory))
    
    # Show dialog
    return QFileDialog.getExistingDirectory(
        parent,
        title,
        directory,
        QFileDialog.Option.ShowDirsOnly
    )


def get_open_filenames(
    title: str,
    directory: str = "",
    filter_str: str = "",
    parent: Optional[QWidget] = None
) -> Tuple[List[str], str]:
    """
    Display a dialog to select multiple files with platform-appropriate behavior.
    
    Args:
        title: Dialog title
        directory: Starting directory, empty for default
        filter_str: File filter string (e.g. "Images (*.png *.jpg);;All Files (*)")
        parent: Parent widget, or None
        
    Returns:
        Tuple of (list_of_selected_files, selected_filter)
    """
    # Use appropriate default directory based on platform
    if not directory:
        directory = get_documents_directory()
    
    # Normalize directory path for the platform
    directory = str(Path(directory))
    
    # Show dialog
    return QFileDialog.getOpenFileNames(
        parent,
        title,
        directory,
        filter_str
    )


def get_app_data_directory() -> str:
    """
    Get the platform-appropriate application data directory.
    
    Returns:
        Path to application data directory
    """
    app_data_location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    
    # Ensure it exists
    Path(app_data_location).mkdir(parents=True, exist_ok=True)
    
    return app_data_location


def get_documents_directory() -> str:
    """
    Get the platform-appropriate documents directory.
    
    Returns:
        Path to documents directory
    """
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)


def normalize_path(path: str) -> str:
    """
    Normalize a path for the current platform.
    
    Args:
        path: Path to normalize
    
    Returns:
        Normalized path
    """
    return str(Path(path))


def get_platform_path_separator() -> str:
    """
    Get the platform-specific path separator.
    
    Returns:
        Path separator character ('/' or '\')
    """
    return os.path.sep 