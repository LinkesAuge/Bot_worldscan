"""
Update Dialog

This module provides a dialog for checking, downloading, and installing application updates.
"""

import os
import logging
import datetime
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextBrowser, QDialogButtonBox, QMessageBox,
    QCheckBox, QGroupBox, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon

from scout.core.updater.update_checker import get_update_checker
from scout.core.updater.settings import get_update_settings
from scout.ui.utils.language_manager import tr

# Set up logging
logger = logging.getLogger(__name__)


class DownloadThread(QThread):
    """Thread for downloading updates in the background."""
    
    # Signals
    progress_updated = pyqtSignal(int)  # Download progress percentage
    download_complete = pyqtSignal(str)  # Path to downloaded file
    download_error = pyqtSignal(str)     # Error message
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the download thread.
        
        Args:
            output_dir: Directory to save the downloaded file.
                If None, a temporary directory will be used.
        """
        super().__init__()
        self.output_dir = output_dir
        self.update_checker = get_update_checker()
    
    def run(self):
        """Run the download process."""
        try:
            # Download the update
            file_path = self.update_checker.download_update(self.output_dir)
            
            if file_path:
                # Download succeeded
                self.download_complete.emit(file_path)
            else:
                # Download failed
                self.download_error.emit(tr("Failed to download update. Please try again later."))
                
        except Exception as e:
            logger.error(f"Error in download thread: {e}")
            self.download_error.emit(str(e))


class UpdateDialog(QDialog):
    """
    Dialog for checking, downloading, and installing application updates.
    
    This dialog provides the user interface for:
    - Checking for application updates
    - Viewing update details and release notes
    - Downloading updates
    - Installing updates
    """
    
    def __init__(self, parent=None, check_automatically: bool = True):
        """
        Initialize the update dialog.
        
        Args:
            parent: Parent widget
            check_automatically: Whether to check for updates automatically on startup
        """
        super().__init__(parent)
        
        # Get update checker and settings
        self.update_checker = get_update_checker()
        self.update_settings = get_update_settings()
        
        # Initialize state
        self.download_thread = None
        self.downloaded_file_path = None
        self.update_info = None
        
        # Set up dialog
        self.setWindowTitle(tr("Check for Updates"))
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        
        # Create UI
        self._create_ui()
        
        # Load settings into UI
        self._load_settings_to_ui()
        
        # Check for updates if requested
        if check_automatically:
            self.check_for_updates()
    
    def _create_ui(self):
        """Create the dialog UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Logo/icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        # Set a default icon - replace with your app icon
        self.icon_label.setPixmap(QIcon.fromTheme("system-software-update").pixmap(QSize(64, 64)))
        header_layout.addWidget(self.icon_label)
        
        # Title and status
        title_layout = QVBoxLayout()
        
        self.title_label = QLabel(tr("Scout Update"))
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        self.status_label = QLabel(tr("Checking for updates..."))
        title_layout.addWidget(self.status_label)
        
        self.version_label = QLabel("")
        self.version_label.setVisible(False)
        title_layout.addWidget(self.version_label)
        
        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Check button
        self.check_button = QPushButton(tr("Check for Updates"))
        self.check_button.clicked.connect(self.check_for_updates)
        header_layout.addWidget(self.check_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addLayout(header_layout)
        
        # Add separator line
        separator = QLabel()
        separator.setFrameShape(QLabel.Shape.HLine)
        separator.setFrameShadow(QLabel.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Update information
        self.info_browser = QTextBrowser()
        self.info_browser.setMinimumHeight(150)
        self.info_browser.setReadOnly(True)
        self.info_browser.setOpenExternalLinks(True)
        layout.addWidget(self.info_browser)
        
        # Progress bar
        self.progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel(tr("Downloading update..."))
        self.progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_layout.addWidget(self.progress_bar)
        
        # Hide progress initially
        self.progress_label.setVisible(False)
        self.progress_bar.setVisible(False)
        
        layout.addLayout(self.progress_layout)
        
        # Settings section
        self.settings_group = QGroupBox(tr("Update Settings"))
        settings_layout = QFormLayout()
        
        # Auto-check checkbox
        self.auto_check_checkbox = QCheckBox(tr("Check for updates on startup"))
        settings_layout.addRow("", self.auto_check_checkbox)
        
        # Auto-download checkbox
        self.auto_download_checkbox = QCheckBox(tr("Automatically download updates"))
        settings_layout.addRow("", self.auto_download_checkbox)
        
        # Notification checkbox
        self.notify_checkbox = QCheckBox(tr("Show notification when updates are available"))
        settings_layout.addRow("", self.notify_checkbox)
        
        # Check frequency
        self.check_frequency_combo = QComboBox()
        self.check_frequency_combo.addItem(tr("Daily"), 1)
        self.check_frequency_combo.addItem(tr("Weekly"), 7)
        self.check_frequency_combo.addItem(tr("Monthly"), 30)
        settings_layout.addRow(tr("Check frequency:"), self.check_frequency_combo)
        
        # Update channel
        self.update_channel_combo = QComboBox()
        self.update_channel_combo.addItem(tr("Stable"), "stable")
        self.update_channel_combo.addItem(tr("Beta"), "beta")
        settings_layout.addRow(tr("Update channel:"), self.update_channel_combo)
        
        self.settings_group.setLayout(settings_layout)
        layout.addWidget(self.settings_group)
        
        # Buttons
        self.button_box = QDialogButtonBox()
        
        self.download_button = QPushButton(tr("Download"))
        self.download_button.clicked.connect(self.download_update)
        self.button_box.addButton(self.download_button, QDialogButtonBox.ButtonRole.ActionRole)
        
        self.install_button = QPushButton(tr("Install Now"))
        self.install_button.clicked.connect(self.install_update)
        self.button_box.addButton(self.install_button, QDialogButtonBox.ButtonRole.ActionRole)
        
        self.close_button = QPushButton(tr("Close"))
        self.close_button.clicked.connect(self.accept)
        self.button_box.addButton(self.close_button, QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(self.button_box)
        
        # Set initial button states
        self.download_button.setEnabled(False)
        self.install_button.setEnabled(False)
        
        # Connect settings change signals
        self.auto_check_checkbox.stateChanged.connect(self.save_update_preferences)
        self.auto_download_checkbox.stateChanged.connect(self.save_update_preferences)
        self.notify_checkbox.stateChanged.connect(self.save_update_preferences)
        self.check_frequency_combo.currentIndexChanged.connect(self.save_update_preferences)
        self.update_channel_combo.currentIndexChanged.connect(self.save_update_preferences)
        
        # Set dialog layout
        self.setLayout(layout)
    
    def _load_settings_to_ui(self):
        """Load settings into UI components."""
        # Auto-check checkbox
        self.auto_check_checkbox.setChecked(
            self.update_settings.should_check_updates_on_startup()
        )
        
        # Auto-download checkbox
        self.auto_download_checkbox.setChecked(
            self.update_settings.should_auto_download_updates()
        )
        
        # Notification checkbox
        self.notify_checkbox.setChecked(
            self.update_settings.should_notify_on_update()
        )
        
        # Check frequency
        frequency_days = self.update_settings.get_setting("check_frequency_days", 1)
        index = 0  # Default to daily
        for i in range(self.check_frequency_combo.count()):
            if self.check_frequency_combo.itemData(i) == frequency_days:
                index = i
                break
        self.check_frequency_combo.setCurrentIndex(index)
        
        # Update channel
        channel = self.update_settings.get_setting("update_channel", "stable")
        index = 0  # Default to stable
        for i in range(self.update_channel_combo.count()):
            if self.update_channel_combo.itemData(i) == channel:
                index = i
                break
        self.update_channel_combo.setCurrentIndex(index)
    
    def check_for_updates(self):
        """Check for available updates."""
        # Update UI
        self.status_label.setText(tr("Checking for updates..."))
        self.info_browser.clear()
        self.download_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.check_button.setEnabled(False)
        
        try:
            # Check for updates
            update_available = self.update_checker.check_for_updates()
            
            # Update last check time
            now = datetime.datetime.now().isoformat()
            self.update_settings.update_last_check_time(now)
            
            # Get update info
            self.update_info = self.update_checker.get_update_info()
            
            if update_available:
                # Update found
                self.status_label.setText(tr("Update available!"))
                self.version_label.setText(
                    tr("Current version: {current} — New version: {new}").format(
                        current=self.update_info["current_version"],
                        new=self.update_info["latest_version"]
                    )
                )
                self.version_label.setVisible(True)
                
                # Enable download button
                self.download_button.setEnabled(True)
                
                # Auto-download if enabled
                if self.update_settings.should_auto_download_updates():
                    self.download_update()
                
                # Display update info
                self._display_update_info()
            else:
                # No update found
                self.status_label.setText(tr("You have the latest version!"))
                self.version_label.setText(
                    tr("Current version: {version}").format(
                        version=self.update_info["current_version"]
                    )
                )
                self.version_label.setVisible(True)
                
                # Display "no update" message
                self.info_browser.setHtml(
                    f"<h3>{tr('No Update Available')}</h3>"
                    f"<p>{tr('You are using the latest version of Scout.')}</p>"
                    f"<p>{tr('Check back later for new updates and features.')}</p>"
                )
            
        except Exception as e:
            # Error checking for updates
            logger.error(f"Error checking for updates: {e}")
            self.status_label.setText(tr("Error checking for updates"))
            self.info_browser.setHtml(
                f"<h3>{tr('Error')}</h3>"
                f"<p>{tr('An error occurred while checking for updates:')}</p>"
                f"<p><code>{str(e)}</code></p>"
                f"<p>{tr('Please try again later or check your internet connection.')}</p>"
            )
        
        # Re-enable check button
        self.check_button.setEnabled(True)
    
    def _display_update_info(self):
        """Display update information in the info browser."""
        if not self.update_info:
            return
        
        # Format update information as HTML
        html = f"<h3>{tr('Update Available')}: {self.update_info['latest_version']}</h3>"
        
        # Add update description if available
        if self.update_info.get("update_info"):
            html += f"<p>{self.update_info['update_info']}</p>"
        
        # Add changelog if available
        if self.update_info.get("changelog"):
            html += f"<h4>{tr('What\'s New:')}</h4>"
            html += f"<div>{self.update_info['changelog']}</div>"
        
        # Set HTML in browser
        self.info_browser.setHtml(html)
    
    def download_update(self):
        """Download the available update."""
        # Make sure we have update info
        if not self.update_info or not self.update_info.get("download_url"):
            QMessageBox.warning(
                self,
                tr("Download Error"),
                tr("No download URL available. Please check for updates again.")
            )
            return
        
        # Show progress UI
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Disable buttons during download
        self.download_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.check_button.setEnabled(False)
        
        # Update status
        self.status_label.setText(tr("Downloading update..."))
        
        # Create download directory if needed
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Scout")
        os.makedirs(download_dir, exist_ok=True)
        
        # Create and start download thread
        self.download_thread = DownloadThread(download_dir)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.download_error.connect(self.download_failed)
        self.download_thread.start()
    
    def update_progress(self, percentage: int):
        """
        Update the progress bar.
        
        Args:
            percentage: Download progress percentage (0-100)
        """
        self.progress_bar.setValue(percentage)
    
    def download_finished(self, file_path: str):
        """
        Handle download completion.
        
        Args:
            file_path: Path to the downloaded file
        """
        # Store downloaded file path
        self.downloaded_file_path = file_path
        
        # Update UI
        self.status_label.setText(tr("Download complete!"))
        self.progress_bar.setValue(100)
        
        # Enable install button
        self.install_button.setEnabled(True)
        self.check_button.setEnabled(True)
        
        # Show message
        self.info_browser.append(
            f"<p><b>{tr('Download complete!')}</b> "
            f"{tr('Click \"Install Now\" to install the update.')}</p>"
        )
        
        # Clean up thread
        self.download_thread = None
    
    def download_failed(self, error_message: str):
        """
        Handle download failure.
        
        Args:
            error_message: Error message
        """
        # Update UI
        self.status_label.setText(tr("Download failed"))
        self.progress_label.setVisible(False)
        self.progress_bar.setVisible(False)
        
        # Re-enable buttons
        self.download_button.setEnabled(True)
        self.check_button.setEnabled(True)
        
        # Show error message
        self.info_browser.append(
            f"<p><b>{tr('Error:')}</b> {error_message}</p>"
            f"<p>{tr('Please try again later.')}</p>"
        )
        
        # Clean up thread
        self.download_thread = None
    
    def install_update(self):
        """Install the downloaded update."""
        # Make sure we have a downloaded file
        if not self.downloaded_file_path or not os.path.exists(self.downloaded_file_path):
            QMessageBox.warning(
                self,
                tr("Installation Error"),
                tr("Update file not found. Please download the update again.")
            )
            return
        
        # Confirm installation
        response = QMessageBox.question(
            self,
            tr("Install Update"),
            tr("The application will close and the update will be installed. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if response == QMessageBox.StandardButton.Yes:
            # Install the update
            silent = False  # Show the installer UI
            success = self.update_checker.install_update(self.downloaded_file_path, silent)
            
            if success:
                # Installation started successfully
                QMessageBox.information(
                    self,
                    tr("Update Started"),
                    tr("The update is being installed. The application will now close.")
                )
                
                # Close the dialog and signal the application to exit
                self.accept()
                
                # Exit the application with update code
                from scout.core.utils.codes import Codes
                import sys
                sys.exit(Codes.UPDATE_CODE)
            else:
                # Installation failed
                QMessageBox.critical(
                    self,
                    tr("Installation Error"),
                    tr("Failed to start the update installation. Please try running the installer manually.")
                )
    
    def save_update_preferences(self):
        """Save update preferences to settings."""
        try:
            # Get values from UI
            check_on_startup = self.auto_check_checkbox.isChecked()
            auto_download = self.auto_download_checkbox.isChecked()
            notify_on_update = self.notify_checkbox.isChecked()
            check_frequency = self.check_frequency_combo.currentData()
            update_channel = self.update_channel_combo.currentData()
            
            # Update settings
            self.update_settings.set_setting("check_updates_on_startup", check_on_startup)
            self.update_settings.set_setting("auto_download_updates", auto_download)
            self.update_settings.set_setting("notify_on_update", notify_on_update)
            self.update_settings.set_setting("check_frequency_days", check_frequency)
            self.update_settings.set_setting("update_channel", update_channel)
            
            # Save settings
            self.update_settings.save_settings()
            
            logger.debug("Update preferences saved")
        except Exception as e:
            logger.error(f"Error saving update preferences: {e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Cancel download if running
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        
        # Save preferences
        self.save_update_preferences()
        
        # Accept the event
        event.accept()


def show_update_dialog(parent=None, check_automatically: bool = True) -> int:
    """
    Show the update dialog.
    
    Args:
        parent: Parent widget
        check_automatically: Whether to check for updates automatically
        
    Returns:
        Dialog execution result code
    """
    dialog = UpdateDialog(parent, check_automatically)
    return dialog.exec()


def check_for_updates_in_background(parent=None) -> bool:
    """
    Check for updates in the background and notify if available.
    
    Args:
        parent: Parent widget for notification dialogs
        
    Returns:
        True if update is available, False otherwise
    """
    try:
        # Get update checker and settings
        update_checker = get_update_checker()
        update_settings = get_update_settings()
        
        # Check if we should notify about updates
        if not update_settings.should_notify_on_update():
            return False
        
        # Check for updates
        update_available = update_checker.check_for_updates()
        
        # Update last check time
        now = datetime.datetime.now().isoformat()
        update_settings.update_last_check_time(now)
        
        if update_available:
            # Get update info
            update_info = update_checker.get_update_info()
            
            # Show notification
            response = QMessageBox.information(
                parent,
                tr("Update Available"),
                tr("A new version of Scout is available: {version}\n\nWould you like to update now?").format(
                    version=update_info["latest_version"]
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if response == QMessageBox.StandardButton.Yes:
                # Show update dialog
                show_update_dialog(parent, False)
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking for updates in background: {e}")
        return False 