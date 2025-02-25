"""
Template List Widget

This module provides a widget for managing and selecting template images for
detection operations in the Scout application.
"""

import os
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path
from PyQt6.QtWidgets import (
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QMenu, QMessageBox
)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize

# Set up logging
logger = logging.getLogger(__name__)

class TemplateListWidget(QWidget):
    """
    Widget for managing and selecting template images.
    
    This widget provides:
    - Display of available template images
    - Selection of templates for detection
    - Import and export of templates
    - Management of template files (add, remove, rename)
    """
    
    # Signals
    template_added = pyqtSignal(str)  # Template name
    template_removed = pyqtSignal(str)  # Template name
    template_selected = pyqtSignal(str)  # Template name
    templates_changed = pyqtSignal()  # Any change to templates
    
    def __init__(self, template_dir: str):
        """
        Initialize the template list widget.
        
        Args:
            template_dir: Directory containing template images
        """
        super().__init__()
        
        self.template_dir = Path(template_dir)
        self._templates: Dict[str, str] = {}  # name -> path
        self._selected_templates: Set[str] = set()
        
        # Create UI layout
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Ensure template directory exists
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Template list widget initialized with directory: {template_dir}")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create header with title and controls
        header_layout = QHBoxLayout()
        
        # Title label
        header_layout.addWidget(QLabel("Templates"))
        
        # Add spacer to push buttons to the right
        header_layout.addStretch()
        
        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.setToolTip("Add new template")
        header_layout.addWidget(self.add_button)
        
        # Delete button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Delete selected template")
        self.delete_button.setEnabled(False)  # Disabled until selection
        header_layout.addWidget(self.delete_button)
        
        layout.addLayout(header_layout)
        
        # Create template list
        self.template_list = QListWidget()
        self.template_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.template_list.setIconSize(QSize(48, 48))
        self.template_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.template_list)
    
    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # Button actions
        self.add_button.clicked.connect(self._on_add_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        
        # List actions
        self.template_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.template_list.customContextMenuRequested.connect(self._on_context_menu)
        self.template_list.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def load_templates(self) -> None:
        """Load templates from the template directory."""
        # Clear current templates
        self.template_list.clear()
        self._templates.clear()
        self._selected_templates.clear()
        
        # Ensure directory exists
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all image files from directory
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        
        try:
            for file_path in self.template_dir.glob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    template_name = file_path.stem
                    template_path = str(file_path)
                    
                    # Add to internal dict
                    self._templates[template_name] = template_path
                    
                    # Create list item
                    self._add_template_item(template_name, template_path)
            
            logger.info(f"Loaded {len(self._templates)} templates from {self.template_dir}")
        
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def _add_template_item(self, name: str, path: str) -> None:
        """
        Add a template to the list widget.
        
        Args:
            name: Template name
            path: Path to template image
        """
        try:
            # Create icon from template image
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Scale down to reasonable size if needed
                if pixmap.width() > 200 or pixmap.height() > 200:
                    pixmap = pixmap.scaled(
                        48, 48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                
                # Create item with icon
                item = QListWidgetItem(QIcon(pixmap), name)
            else:
                # Create item without icon if image couldn't be loaded
                item = QListWidgetItem(name)
                logger.warning(f"Could not load image for template: {path}")
            
            # Add metadata
            item.setData(Qt.ItemDataRole.UserRole, path)
            
            # Add to list
            self.template_list.addItem(item)
        
        except Exception as e:
            logger.error(f"Error adding template item {name}: {e}")
    
    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        # Open file dialog to select images
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.tiff)")
        file_dialog.setDirectory(str(self.template_dir))
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            
            # Import each selected file
            for file_path in file_paths:
                self._import_template(file_path)
            
            # Signal change
            self.templates_changed.emit()
    
    def _import_template(self, source_path: str) -> None:
        """
        Import a template image.
        
        Args:
            source_path: Path to template image
        """
        try:
            # Get file info
            source_file = Path(source_path)
            template_name = source_file.stem
            
            # Construct destination path
            dest_path = self.template_dir / source_file.name
            
            # Check if template with this name already exists
            if dest_path.exists():
                # Generate unique name by adding number
                counter = 1
                while True:
                    new_name = f"{template_name}_{counter}"
                    new_path = self.template_dir / f"{new_name}{source_file.suffix}"
                    if not new_path.exists():
                        dest_path = new_path
                        template_name = new_name
                        break
                    counter += 1
            
            # Copy file to template directory
            import shutil
            shutil.copy2(source_path, str(dest_path))
            
            # Add to templates
            self._templates[template_name] = str(dest_path)
            
            # Add to list
            self._add_template_item(template_name, str(dest_path))
            
            # Emit signal
            self.template_added.emit(template_name)
            
            logger.info(f"Imported template: {template_name}")
        
        except Exception as e:
            logger.error(f"Error importing template from {source_path}: {e}")
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import template: {e}"
            )
    
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        # Get selected items
        selected_items = self.template_list.selectedItems()
        
        if not selected_items:
            return
        
        # Confirm deletion
        if len(selected_items) == 1:
            message = f"Are you sure you want to delete the template '{selected_items[0].text()}'?"
        else:
            message = f"Are you sure you want to delete {len(selected_items)} templates?"
        
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        # Delete each selected item
        for item in selected_items:
            template_name = item.text()
            self._delete_template(template_name)
        
        # Update button state
        self.delete_button.setEnabled(False)
        
        # Signal change
        self.templates_changed.emit()
    
    def _delete_template(self, template_name: str) -> None:
        """
        Delete a template.
        
        Args:
            template_name: Name of the template to delete
        """
        if template_name not in self._templates:
            return
        
        try:
            # Get template path
            template_path = self._templates[template_name]
            
            # Delete file
            file_path = Path(template_path)
            if file_path.exists():
                file_path.unlink()
            
            # Remove from templates dict
            del self._templates[template_name]
            
            # Remove from selected templates
            if template_name in self._selected_templates:
                self._selected_templates.remove(template_name)
            
            # Remove from list widget (find and remove the matching item)
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                if item.text() == template_name:
                    self.template_list.takeItem(i)
                    break
            
            # Emit signal
            self.template_removed.emit(template_name)
            
            logger.info(f"Deleted template: {template_name}")
        
        except Exception as e:
            logger.error(f"Error deleting template {template_name}: {e}")
            QMessageBox.critical(
                self,
                "Delete Error",
                f"Failed to delete template: {e}"
            )
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in the template list."""
        # Update button state
        selected_items = self.template_list.selectedItems()
        self.delete_button.setEnabled(len(selected_items) > 0)
        
        # Update selected templates
        self._selected_templates.clear()
        for item in selected_items:
            self._selected_templates.add(item.text())
    
    def _on_context_menu(self, position) -> None:
        """
        Show context menu for the template list.
        
        Args:
            position: Position where the menu should be shown
        """
        # Get item at position
        item = self.template_list.itemAt(position)
        
        if not item:
            # Click on empty area
            menu = QMenu(self)
            add_action = menu.addAction("Add Template")
            add_action.triggered.connect(self._on_add_clicked)
            menu.exec(self.template_list.mapToGlobal(position))
            return
        
        # Click on item
        menu = QMenu(self)
        
        # Single selection actions
        if len(self.template_list.selectedItems()) == 1:
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._on_rename_clicked(item))
            
            view_action = menu.addAction("View Full Size")
            view_action.triggered.connect(lambda: self._on_view_clicked(item))
            
            menu.addSeparator()
        
        # Multi-selection actions
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._on_delete_clicked)
        
        # Show menu
        menu.exec(self.template_list.mapToGlobal(position))
    
    def _on_rename_clicked(self, item: QListWidgetItem) -> None:
        """
        Handle rename action.
        
        Args:
            item: The list item to rename
        """
        # Get current name
        current_name = item.text()
        
        # Get original file path
        file_path = Path(self._templates[current_name])
        
        # Prompt for new name
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Template",
            "New name:",
            text=current_name
        )
        
        if not ok or not new_name or new_name == current_name:
            return
        
        # Check if new name already exists
        if new_name in self._templates:
            QMessageBox.warning(
                self,
                "Rename Error",
                f"A template with the name '{new_name}' already exists."
            )
            return
        
        try:
            # Create new file path
            new_file_path = file_path.with_stem(new_name)
            
            # Rename file
            file_path.rename(new_file_path)
            
            # Update templates dict
            del self._templates[current_name]
            self._templates[new_name] = str(new_file_path)
            
            # Update selected templates
            if current_name in self._selected_templates:
                self._selected_templates.remove(current_name)
                self._selected_templates.add(new_name)
            
            # Update list item
            item.setText(new_name)
            item.setData(Qt.ItemDataRole.UserRole, str(new_file_path))
            
            # Signal change
            self.templates_changed.emit()
            
            logger.info(f"Renamed template from '{current_name}' to '{new_name}'")
        
        except Exception as e:
            logger.error(f"Error renaming template {current_name}: {e}")
            QMessageBox.critical(
                self,
                "Rename Error",
                f"Failed to rename template: {e}"
            )
    
    def _on_view_clicked(self, item: QListWidgetItem) -> None:
        """
        Handle view action.
        
        Args:
            item: The list item to view
        """
        # Get template path
        template_path = item.data(Qt.ItemDataRole.UserRole)
        
        # Open in external viewer (platform-dependent)
        try:
            import os
            import subprocess
            import sys
            
            if sys.platform == 'win32':
                os.startfile(template_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', template_path])
            else:  # Linux
                subprocess.run(['xdg-open', template_path])
        
        except Exception as e:
            logger.error(f"Error opening template for viewing: {e}")
            QMessageBox.critical(
                self,
                "View Error",
                f"Failed to open template for viewing: {e}"
            )
    
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """
        Handle double-click on a template item.
        
        Args:
            item: The item that was double-clicked
        """
        # Get template name
        template_name = item.text()
        
        # Emit selected signal
        self.template_selected.emit(template_name)
    
    def get_selected_templates(self) -> List[str]:
        """
        Get the names of selected templates.
        
        Returns:
            List of selected template names
        """
        return list(self._selected_templates)
    
    def get_template_path(self, template_name: str) -> Optional[str]:
        """
        Get the file path for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            File path or None if not found
        """
        return self._templates.get(template_name)
    
    def count(self) -> int:
        """
        Get the number of templates.
        
        Returns:
            Number of templates
        """
        return len(self._templates) 